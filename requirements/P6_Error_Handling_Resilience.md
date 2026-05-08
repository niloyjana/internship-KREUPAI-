# ADWP Error Handling & Resilience Strategy
## Fault Tolerance Architecture — AI Digital Workforce Platform
**File:** `docs/architecture/error-handling-resilience.md`
**Version:** 1.0.0

---

> This document defines exactly what happens when things go wrong.
> The platform makes thousands of external calls daily — integrations fail, LLMs rate-limit,
> workflows stall, and services crash. This spec ensures every failure is handled consistently,
> recoverable, and visible — never silent.

---

## 1. Failure Categories

```
CATEGORY A: TRANSIENT FAILURES (recoverable with retry)
  ├── Network timeout calling Salesforce API
  ├── Redis connection blip
  ├── LLM provider temporary 503
  └── Kafka broker leader election

CATEGORY B: RATE LIMIT FAILURES (recoverable with backoff)
  ├── OpenAI rate limit (429)
  ├── HubSpot API rate limit
  ├── SendGrid send limit
  └── Internal API throttling

CATEGORY C: BUSINESS RULE FAILURES (non-retryable, needs human)
  ├── Invoice has no matching PO
  ├── Refund exceeds policy limit
  ├── Candidate missing mandatory qualification
  └── Budget unavailable for purchase

CATEGORY D: EXTERNAL SYSTEM FAILURES (partial recovery)
  ├── Integration auth expired
  ├── CRM down for maintenance
  ├── ERP returning unexpected schema
  └── Email bounce / delivery failure

CATEGORY E: AI FAILURES (degrade gracefully)
  ├── LLM confidence below threshold
  ├── LLM hallucination detected by guardrail
  ├── Prompt injection attempt detected
  └── Token limit exceeded

CATEGORY F: INFRASTRUCTURE FAILURES (ops response)
  ├── Service pod crash
  ├── Database connection pool exhausted
  ├── Kafka consumer group rebalance
  └── Secret rotation failure
```

---

## 2. Retry Policy Framework

```typescript
// packages/utils/retry.ts
// Shared retry utility used by all services and ai-runtime

interface RetryConfig {
  maxAttempts: number;
  initialDelayMs: number;
  backoffMultiplier: number;
  maxDelayMs: number;
  retryableErrors: string[];   // error codes that trigger retry
  onRetry?: (attempt: number, error: Error) => void;
}

// Standard retry profiles — use these, don't invent custom ones
export const RETRY_PROFILES = {

  // For external integration API calls
  INTEGRATION_CALL: {
    maxAttempts: 3,
    initialDelayMs: 1000,
    backoffMultiplier: 4,
    maxDelayMs: 30000,
    retryableErrors: ['ECONNRESET', 'ETIMEDOUT', 'ENOTFOUND', '503', '502', '504']
  },

  // For LLM API calls (OpenAI, Claude)
  LLM_CALL: {
    maxAttempts: 3,
    initialDelayMs: 2000,
    backoffMultiplier: 2,
    maxDelayMs: 10000,
    retryableErrors: ['503', '529', 'overloaded']
    // 429 rate limit handled separately (with provider-specified retry-after)
  },

  // For internal service calls (NestJS → NestJS)
  INTERNAL_SERVICE: {
    maxAttempts: 3,
    initialDelayMs: 200,
    backoffMultiplier: 2,
    maxDelayMs: 3000,
    retryableErrors: ['ECONNREFUSED', 'ECONNRESET', '503']
  },

  // For Kafka publish (critical events)
  KAFKA_PUBLISH: {
    maxAttempts: 5,
    initialDelayMs: 500,
    backoffMultiplier: 2,
    maxDelayMs: 10000,
    retryableErrors: ['LEADER_NOT_AVAILABLE', 'NOT_LEADER_FOR_PARTITION']
  },

  // For DB operations (transient connection issues)
  DATABASE: {
    maxAttempts: 3,
    initialDelayMs: 100,
    backoffMultiplier: 2,
    maxDelayMs: 1000,
    retryableErrors: ['P1001', 'P1008', 'P1017']  // Prisma error codes
  }
};

// Implementation
export async function withRetry<T>(
  operation: () => Promise<T>,
  config: RetryConfig,
  context: string
): Promise<T> {
  let lastError: Error;

  for (let attempt = 1; attempt <= config.maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      const isRetryable = config.retryableErrors.some(code =>
        error.message.includes(code) || error.code === code
      );

      if (!isRetryable || attempt === config.maxAttempts) {
        logger.error(`[${context}] Non-retryable or max attempts reached`, {
          attempt, error: error.message
        });
        throw error;
      }

      const delay = Math.min(
        config.initialDelayMs * Math.pow(config.backoffMultiplier, attempt - 1),
        config.maxDelayMs
      );

      logger.warn(`[${context}] Retrying (${attempt}/${config.maxAttempts}) after ${delay}ms`, {
        error: error.message
      });

      config.onRetry?.(attempt, error);
      await sleep(delay);
    }
  }

  throw lastError!;
}
```

---

## 3. Circuit Breaker Pattern

```typescript
// packages/utils/circuit-breaker.ts
// Applied to all external integration calls

enum CircuitState {
  CLOSED,    // Normal operation — requests pass through
  OPEN,      // Failing — requests blocked immediately
  HALF_OPEN  // Testing recovery — one request allowed through
}

class CircuitBreaker {
  private state = CircuitState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime: number | null = null;
  private openedAt: number | null = null;

  constructor(
    private readonly name: string,
    private readonly config: {
      failureThreshold: number;    // Open after N failures
      successThreshold: number;   // Close after N successes in HALF_OPEN
      openDurationMs: number;     // How long to stay OPEN
      timeWindowMs: number;       // Failure counting window
    }
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() - this.openedAt! > this.config.openDurationMs) {
        this.state = CircuitState.HALF_OPEN;
        logger.info(`Circuit breaker [${this.name}] → HALF_OPEN`);
      } else {
        throw new CircuitOpenError(`${this.name} circuit is OPEN`);
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess() {
    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= this.config.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.failureCount = 0;
        this.successCount = 0;
        logger.info(`Circuit breaker [${this.name}] → CLOSED`);
      }
    } else {
      this.failureCount = 0;
    }
  }

  private onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    if (this.failureCount >= this.config.failureThreshold) {
      this.state = CircuitState.OPEN;
      this.openedAt = Date.now();
      logger.error(`Circuit breaker [${this.name}] → OPEN after ${this.failureCount} failures`);
      // Emit metric for Grafana alerting
      this.metrics.increment('circuit_breaker.opened', { breaker: this.name });
    }
  }
}

// Standard circuit breaker configs per integration type
export const CIRCUIT_CONFIGS = {
  SALESFORCE:   { failureThreshold: 5, successThreshold: 2, openDurationMs: 60000, timeWindowMs: 120000 },
  SAP:          { failureThreshold: 3, successThreshold: 2, openDurationMs: 120000, timeWindowMs: 120000 },
  OPENAI:       { failureThreshold: 5, successThreshold: 3, openDurationMs: 30000, timeWindowMs: 60000 },
  ANTHROPIC:    { failureThreshold: 5, successThreshold: 3, openDurationMs: 30000, timeWindowMs: 60000 },
  SENDGRID:     { failureThreshold: 5, successThreshold: 2, openDurationMs: 300000, timeWindowMs: 120000 },
  STRIPE:       { failureThreshold: 3, successThreshold: 2, openDurationMs: 60000, timeWindowMs: 60000 },
};
```

---

## 4. Workflow Step Failure Recovery

```python
# ai-runtime/orchestrator/failure_handler.py

class WorkflowFailureHandler:
    """
    Handles step-level failures within workflow executions.
    Every failure category has a defined response.
    """

    def handle_step_failure(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
        error: Exception
    ) -> StepFailureOutcome:

        failure_category = self.classify_failure(error)

        # CATEGORY A: Transient — retry automatically
        if failure_category == FailureCategory.TRANSIENT:
            if step.retry_count < step.max_retries:
                return StepFailureOutcome(
                    action=FailureAction.RETRY,
                    delay_seconds=self.get_backoff_delay(step.retry_count),
                    message=f"Retrying step {step.step_key} (attempt {step.retry_count + 1})"
                )

        # CATEGORY B: Rate limit — backoff using provider's retry-after
        if failure_category == FailureCategory.RATE_LIMITED:
            retry_after = error.retry_after_seconds or 60
            return StepFailureOutcome(
                action=FailureAction.RETRY,
                delay_seconds=retry_after,
                message=f"Rate limited. Retrying after {retry_after}s"
            )

        # CATEGORY C: Business rule — escalate to human
        if failure_category == FailureCategory.BUSINESS_RULE:
            return StepFailureOutcome(
                action=FailureAction.ESCALATE,
                escalation_reason=str(error),
                escalation_severity=EscalationSeverity.MEDIUM,
                context={
                    "step": step.step_key,
                    "input": step.input_json,
                    "error": str(error),
                    "recommended_action": error.recommended_action
                }
            )

        # CATEGORY D: External system down — pause and notify
        if failure_category == FailureCategory.EXTERNAL_SYSTEM:
            return StepFailureOutcome(
                action=FailureAction.PAUSE,
                pause_reason=f"External system unavailable: {error.system}",
                notify_ops=True,
                resume_when="integration_reconnected",
                message=f"Workflow paused. Waiting for {error.system} to recover."
            )

        # CATEGORY E: AI failure — escalate or fallback
        if failure_category == FailureCategory.AI_FAILURE:
            if error.is_confidence_failure:
                return StepFailureOutcome(
                    action=FailureAction.ESCALATE,
                    escalation_reason=f"AI confidence too low: {error.confidence_score}",
                    escalation_severity=EscalationSeverity.LOW,
                    context={"confidence": error.confidence_score, "step": step.step_key}
                )
            # Guardrail violation or injection attempt
            return StepFailureOutcome(
                action=FailureAction.ABORT,
                abort_reason="Guardrail violation — task aborted for safety",
                notify_security=True
            )

        # CATEGORY F: Infrastructure — abort and alert ops
        return StepFailureOutcome(
            action=FailureAction.ABORT,
            abort_reason=f"Infrastructure failure: {str(error)}",
            notify_ops=True,
            alert_pagerduty=True
        )
```

---

## 5. LLM Provider Failover

```python
# ai-runtime/llm/gateway.py
# Multi-provider failover with cost and capability routing

class LLMGateway:

    PROVIDER_PRIORITY = ["openai_gpt4o", "anthropic_claude", "gemini_pro"]

    async def complete(
        self,
        messages: list[Message],
        agent_id: str,
        task_type: str,
        tenant_config: dict
    ) -> LLMResponse:

        # 1. Determine preferred provider (cost + capability routing)
        provider = self.select_provider(task_type, tenant_config)

        # 2. Try preferred provider
        try:
            return await self.call_with_circuit_breaker(provider, messages)

        except RateLimitError as e:
            # Rate limited — move to next provider immediately
            logger.warning(f"[{provider}] rate limited. Failing over.")
            return await self.failover(messages, exclude=[provider])

        except ProviderUnavailableError:
            logger.error(f"[{provider}] unavailable. Failing over.")
            return await self.failover(messages, exclude=[provider])

    async def failover(
        self,
        messages: list[Message],
        exclude: list[str]
    ) -> LLMResponse:
        """Try remaining providers in priority order"""
        for provider in self.PROVIDER_PRIORITY:
            if provider in exclude:
                continue
            try:
                response = await self.call_with_circuit_breaker(provider, messages)
                logger.info(f"Failover succeeded via {provider}")
                self.metrics.increment('llm.failover.success', {'provider': provider})
                return response
            except Exception as e:
                exclude.append(provider)
                continue

        # All providers failed
        raise AllProvidersFailedError("All LLM providers unavailable")

    def select_provider(self, task_type: str, tenant_config: dict) -> str:
        """Route to provider based on task complexity and tenant preferences"""
        preferred = tenant_config.get('llmPreferences', {}).get('preferredProvider')
        if preferred:
            return preferred

        # Cost routing: use cheaper model for simple tasks
        if task_type in ['classify', 'extract', 'summarize_short']:
            return 'openai_gpt4o_mini'

        # Compliance routing: use local/regional model for regulated data
        if tenant_config.get('requiresDataResidency'):
            return 'azure_openai_uae'

        return 'openai_gpt4o'  # Default
```

---

## 6. Dead Letter Queue Handling

```typescript
// services/workflow-service/src/kafka/dlq.handler.ts

@Injectable()
class DLQHandler {
  /**
   * Every Kafka consumer has a corresponding DLQ consumer.
   * DLQ events are logged, alerted, and stored for manual re-processing.
   */

  @KafkaMessagePattern('workflow.execution.started.dlq')
  async handleWorkflowDLQ(message: KafkaMessage): Promise<void> {
    const payload = JSON.parse(message.value.toString());

    // 1. Log the failure
    logger.error('DLQ message received', {
      topic: 'workflow.execution.started',
      executionId: payload.executionId,
      originalError: message.headers['x-error-message'],
      failedAt: message.headers['x-failed-at'],
      attemptCount: message.headers['x-retry-count']
    });

    // 2. Persist for investigation
    await this.db.dlqEntry.create({
      data: {
        topic: 'workflow.execution.started',
        payload: payload,
        errorMessage: message.headers['x-error-message']?.toString(),
        receivedAt: new Date()
      }
    });

    // 3. Alert ops if DLQ growing
    const dlqCount = await this.getDLQCount('workflow.execution.started');
    if (dlqCount > 10) {
      await this.alertOps(`DLQ growing: workflow.execution.started has ${dlqCount} entries`);
    }

    // 4. Attempt auto-recovery for known recoverable patterns
    if (this.isAutoRecoverable(payload, message.headers)) {
      await this.scheduleReplay(payload, delayMs: 300000); // Retry in 5 minutes
    }
  }

  // Ops can trigger manual replay via admin API
  async replayDLQEntry(dlqEntryId: string): Promise<void> {
    const entry = await this.db.dlqEntry.findUnique({ where: { id: dlqEntryId } });
    await this.kafkaProducer.send({
      topic: entry.topic,
      messages: [{ value: JSON.stringify(entry.payload) }]
    });
    await this.db.dlqEntry.update({
      where: { id: dlqEntryId },
      data: { replayedAt: new Date(), status: 'REPLAYED' }
    });
  }
}
```

---

## 7. Partial Failure in Multi-Step Workflows

```
WORKFLOW PARTIAL FAILURE SCENARIOS
════════════════════════════════════

Scenario 1: Step 3 of 6 fails (transient)
  → Retry step 3 (up to maxRetries)
  → If retry succeeds → continue from step 4
  → If retry exhausted → pause execution, create escalation ticket
  → Human resolves → resume from step 3 (idempotent re-execution)

Scenario 2: External write succeeded, next step fails
  Example: Invoice matched (step 4), ERP update failed (step 5)
  → DO NOT re-run step 4 (would create duplicate match)
  → Each step stores idempotency key (executionId + stepKey)
  → On resume, completed steps are SKIPPED based on idempotency key
  → Step 5 retried in isolation

Scenario 3: Parallel steps (fan-out), one branch fails
  → Other branches continue running
  → Failed branch: retry per policy
  → If failed branch is not critical (marked optional=true): log and continue
  → If critical branch fails: pause entire execution, escalate

Scenario 4: Workflow paused for 24+ hours (human task not resolved)
  → SLA breach event published
  → Manager notified
  → Execution remains paused (not failed) — state preserved
  → Resumed immediately when human task is resolved

IDEMPOTENCY IMPLEMENTATION
  Every step that writes to an external system uses:
    idempotency_key = sha256(execution_id + step_key + input_hash)
  External systems called with this key in headers (Stripe, payment APIs).
  Internal writes checked before re-execution.
```

---

## 8. Graceful Degradation

```
DEGRADATION LEVELS
═══════════════════

LEVEL 1 — FULL SERVICE (normal)
  All agents active, all integrations connected, LLM at full capacity

LEVEL 2 — REDUCED INTEGRATION (1+ integrations failing)
  Agent continues working with available integrations
  Missing integration data: flagged in output, human notified
  Example: CRM down → Support Agent answers from KB only, logs ticket locally

LEVEL 3 — LLM FALLBACK (primary LLM failing)
  Failover to secondary LLM provider
  Complex tasks: escalate to human (don't attempt with weaker model)
  Simple tasks: continue with fallback model

LEVEL 4 — AGENT SUSPENDED (agent or Kafka failing)
  Agent paused — no new tasks accepted
  Queued tasks preserved in Kafka (up to retention period)
  Tenant notified with ETA for recovery
  Human team takes over incoming work manually

LEVEL 5 — READ-ONLY MODE (DB write failure)
  Agents stop executing new tasks
  Dashboards and reporting remain available (read replica)
  All new task requests queued (Kafka holds them)
  Recovery: DB issue resolved → replay queue

TRIGGER CONDITIONS FOR EACH LEVEL (auto-detected by health monitor)
  Level 2: Circuit breaker OPEN on any integration
  Level 3: Primary LLM circuit OPEN
  Level 4: Agent crash rate > 20% OR Kafka consumer lag > 50,000
  Level 5: DB write error rate > 5%
```

---

## 9. Health Check Architecture

```typescript
// Health check endpoint: GET /v1/health
// Called by Kubernetes liveness + readiness probes

interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  checks: {
    database: HealthStatus;
    redis: HealthStatus;
    kafka: HealthStatus;
    aiRuntime: HealthStatus;       // workflow-service only
    integrations: {
      [connectionId: string]: HealthStatus;
    };
  };
  version: string;
  timestamp: ISO8601;
}

interface HealthStatus {
  status: 'up' | 'down' | 'degraded';
  latencyMs?: number;
  message?: string;
}

// Kubernetes probe configuration
livenessProbe:
  httpGet:
    path: /v1/health/live      # Simple: returns 200 if process running
    port: 3000
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /v1/health/ready     # Checks DB + Redis + Kafka connectivity
    port: 3000
  initialDelaySeconds: 15
  periodSeconds: 5
  failureThreshold: 2
```

---

## 10. Error Response Standards

```typescript
// All errors returned to clients must follow this format
// No internal stack traces, DB errors, or secret references in responses

// ✓ CORRECT — safe, actionable error
{
  "success": false,
  "error": {
    "code": "INTEGRATION_AUTH_FAILED",
    "message": "The HubSpot connection has expired. Please reconnect in Settings → Integrations.",
    "field": null,
    "traceId": "trc_8f2a91c"     // correlates to internal logs — safe to expose
  }
}

// ✗ WRONG — exposes internal details
{
  "error": "Error: connect ECONNREFUSED 10.0.0.5:5432 — PrismaClientInitializationError..."
}

// Error sanitization middleware
@Catch()
class GlobalExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const traceId = generateTraceId();
    const safeMessage = this.sanitize(exception);

    // Log full error internally (with stack trace)
    logger.error({ traceId, error: exception, stack: exception.stack });

    // Return safe response to client
    return {
      success: false,
      error: {
        code: safeMessage.code,
        message: safeMessage.userMessage,
        traceId
      }
    };
  }
}
```

---

## 11. Monitoring Alerts

```yaml
# Prometheus alerting rules for resilience monitoring
groups:
  - name: adwp-resilience
    rules:
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{state="open"} > 0
        for: 1m
        severity: warning
        message: "Circuit breaker {{ $labels.name }} is OPEN"

      - alert: WorkflowFailureRateHigh
        expr: rate(workflow_executions_failed_total[5m]) > 0.1
        for: 2m
        severity: critical
        message: "Workflow failure rate > 10% for agent {{ $labels.agent_id }}"

      - alert: LLMFallbackActive
        expr: llm_failover_active > 0
        for: 0m
        severity: warning
        message: "LLM failover active — primary provider unavailable"

      - alert: EscalationSLABreach
        expr: escalation_sla_breaches_total > 0
        for: 0m
        severity: critical
        message: "Escalation SLA breached for tenant {{ $labels.tenant_id }}"

      - alert: DLQGrowing
        expr: kafka_consumer_group_lag{topic=~".*\.dlq"} > 50
        for: 5m
        severity: critical
        message: "DLQ growing: {{ $labels.topic }} has {{ $value }} messages"
```

---

*AI Digital Workforce Platform | Error Handling & Resilience Strategy v1.0.0*
*Every failure scenario is defined. No silent failures permitted.*
