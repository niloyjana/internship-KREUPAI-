# ADWP Kafka Event Topology
## Event Streaming Architecture — AI Digital Workforce Platform
**File:** `docs/architecture/kafka-event-topology.md`
**Version:** 1.0.0

---

> This document defines every domain event in the platform — its producer, consumers, payload schema, and routing rules.
> All inter-service and inter-agent communication that is asynchronous MUST use Kafka.
> No service may call another service's database directly. Events are the contract.

---

## 1. Design Principles

1. **Event-first** — State changes are communicated via events, not polling or direct DB reads
2. **Immutable events** — Events are never updated or deleted; produce a new event to correct
3. **Schema-versioned** — Every event carries `schemaVersion` for forward compatibility
4. **Tenant-scoped** — Every event carries `tenantId` in headers and payload
5. **Idempotent consumers** — Every consumer handles duplicate delivery gracefully
6. **At-least-once delivery** — Kafka guarantees delivery; consumers must deduplicate
7. **Dead letter queues** — Every topic has a `.dlq` topic for failed processing

---

## 2. Topic Naming Convention

```
{domain}.{entity}.{action}

Examples:
  workflow.execution.started
  agent.task.completed
  integration.connection.failed
  billing.subscription.activated
  hr.onboarding.day1_arrived
  finance.invoice.matched

DLQ pattern:
  {original.topic}.dlq
  e.g. workflow.execution.started.dlq
```

---

## 3. Topic Configuration

```yaml
# Default topic configuration (override per topic as needed)
default:
  partitions: 6
  replication_factor: 3
  retention_ms: 2592000000       # 30 days
  min_insync_replicas: 2

high_throughput_topics:           # agent.action.*, integration.log.*
  partitions: 12
  retention_ms: 604800000         # 7 days

compliance_topics:                # audit.*, compliance.*
  partitions: 6
  retention_ms: 31536000000       # 1 year (immutable audit)
  cleanup_policy: "delete"        # Never compact audit topics

low_latency_topics:               # escalation.*, notification.*
  partitions: 6
  retention_ms: 86400000          # 24 hours
```

---

## 4. Complete Event Catalog

---

### 4.1 TENANT DOMAIN

#### Topic: `tenant.provisioned`
**Producer:** tenant-service
**Consumers:** auth-service, notification-service, analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,          // UUID
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    tenantId: string,
    name: string,
    slug: string,
    plan: "STARTER" | "GROWTH" | "ENTERPRISE" | "CUSTOM",
    adminUserId: string,
    adminEmail: string,
    countryCode: string,
    timezone: string
  }
}
```

#### Topic: `tenant.status.changed`
**Producer:** tenant-service
**Consumers:** subscription-service, agent-registry, notification-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    tenantId: string,
    previousStatus: TenantStatus,
    newStatus: TenantStatus,
    reason: string,
    changedByUserId: string
  }
}
```

#### Topic: `tenant.config.updated`
**Producer:** tenant-service
**Consumers:** ai-runtime (all agents), integration-hub

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    tenantId: string,
    agentId: string | null,       // null = platform-wide config change
    configSection: string,        // "policy" | "integration" | "branding"
    changedKeys: string[],
    changedByUserId: string
  }
}
```

---

### 4.2 AGENT DOMAIN

#### Topic: `agent.subscribed`
**Producer:** subscription-service
**Consumers:** agent-registry, tenant-service, billing-service, notification-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    subscriptionId: string,
    tenantId: string,
    agentId: string,             // e.g. "ai-recruiter"
    agentName: string,
    department: AgentDepartment,
    plan: string,
    monthlyPriceUsd: number,
    startedAt: ISO8601
  }
}
```

#### Topic: `agent.activated`
**Producer:** agent-registry
**Consumers:** ai-runtime, analytics-service, notification-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    tenantId: string,
    agentId: string,
    agentConfigId: string,
    integrationIds: string[],
    policyVersion: number
  }
}
```

#### Topic: `agent.status.changed`
**Producer:** ai-runtime
**Consumers:** workflow-service, analytics-service, notification-service (for portal real-time)

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    tenantId: string,
    agentId: string,
    instanceId: string,
    previousStatus: AgentStatus,
    newStatus: AgentStatus,
    currentTaskId: string | null
  }
}
```

---

### 4.3 WORKFLOW DOMAIN

#### Topic: `workflow.execution.started`
**Producer:** workflow-service
**Consumers:** ai-runtime, analytics-service, audit-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    executionId: string,
    definitionId: string,
    agentId: string,
    triggerSource: string,
    triggerPayload: object | null,
    estimatedSteps: number
  }
}
```

#### Topic: `workflow.step.completed`
**Producer:** ai-runtime
**Consumers:** workflow-service, analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    executionId: string,
    stepId: string,
    stepKey: string,
    stepType: StepType,
    status: "COMPLETED" | "FAILED" | "SKIPPED",
    durationMs: number,
    tokenUsed: number | null,
    outputSummary: string | null   // non-sensitive summary only
  }
}
```

#### Topic: `workflow.execution.completed`
**Producer:** workflow-service
**Consumers:** analytics-service, audit-service, notification-service, billing-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    executionId: string,
    agentId: string,
    status: "COMPLETED" | "FAILED" | "CANCELLED",
    durationMs: number,
    stepCount: number,
    tokenUsed: number,
    costUsd: number,
    escalationTriggered: boolean,
    outcome: string | null         // human-readable one-liner
  }
}
```

#### Topic: `workflow.execution.failed`
**Producer:** workflow-service
**Consumers:** notification-service, analytics-service, audit-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    executionId: string,
    agentId: string,
    failedAtStepId: string,
    failureReason: string,
    isRetryable: boolean,
    retryAttempt: number,
    alertOpsTeam: boolean
  }
}
```

---

### 4.4 HUMAN TASK & ESCALATION DOMAIN

#### Topic: `escalation.created`
**Producer:** ai-runtime
**Consumers:** workflow-service, notification-service, analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    escalationId: string,
    executionId: string | null,
    agentId: string,
    severity: EscalationSeverity,
    reason: string,
    recommendedAction: string | null,
    slaDeadlineAt: ISO8601,
    assignedToUserId: string | null,
    assignedTeam: string | null,
    contextSummary: string         // 2–3 sentence plain text summary
  }
}
```

#### Topic: `human.task.created`
**Producer:** workflow-service
**Consumers:** notification-service, analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    taskId: string,
    executionId: string,
    stepId: string,
    title: string,
    priority: string,
    assignedToUserId: string | null,
    assignedTeam: string | null,
    dueAt: ISO8601
  }
}
```

#### Topic: `human.task.resolved`
**Producer:** workflow-service (on human decision via API)
**Consumers:** ai-runtime (resume workflow), analytics-service, audit-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    taskId: string,
    executionId: string,
    stepId: string,
    decision: "approve" | "reject" | "reassign" | "modify",
    decisionNote: string | null,
    resolvedByUserId: string,
    durationToResolveMs: number,
    slaBreached: boolean
  }
}
```

#### Topic: `escalation.sla.breached`
**Producer:** workflow-service (SLA monitor job)
**Consumers:** notification-service (alert managers), analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    escalationId: string,
    agentId: string,
    severity: EscalationSeverity,
    slaDeadlineAt: ISO8601,
    minutesOverdue: number,
    escalateToUserId: string | null
  }
}
```

---

### 4.5 INTEGRATION DOMAIN

#### Topic: `integration.connected`
**Producer:** integration-hub
**Consumers:** agent-registry, notification-service, analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    connectionId: string,
    provider: IntegrationProvider,
    name: string,
    status: "CONNECTED",
    scopesGranted: string[]
  }
}
```

#### Topic: `integration.connection.failed`
**Producer:** integration-hub
**Consumers:** notification-service, analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    connectionId: string,
    provider: IntegrationProvider,
    errorType: "auth_expired" | "rate_limited" | "endpoint_unreachable" | "permission_denied",
    errorMessage: string,
    retryAfterSeconds: number | null
  }
}
```

#### Topic: `integration.token.refreshed`
**Producer:** integration-hub
**Consumers:** integration-hub (internal — confirmation logging only)

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    connectionId: string,
    provider: IntegrationProvider,
    expiresAt: ISO8601
  }
}
```

---

### 4.6 BILLING DOMAIN

#### Topic: `billing.subscription.activated`
**Producer:** subscription-service
**Consumers:** tenant-service, agent-registry, analytics-service, notification-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    subscriptionId: string,
    tenantId: string,
    agentId: string,
    plan: string,
    monthlyAmountUsd: number,
    stripeSubItemId: string,
    billingCycleStart: ISO8601
  }
}
```

#### Topic: `billing.payment.failed`
**Producer:** subscription-service (Stripe webhook handler)
**Consumers:** tenant-service (suspend if repeated), notification-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    invoiceId: string,
    amountUsd: number,
    failureReason: string,
    attemptCount: number,
    nextRetryAt: ISO8601 | null
  }
}
```

#### Topic: `billing.usage.recorded`
**Producer:** analytics-service (end of each execution)
**Consumers:** billing-service (for usage-based metering)

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    tenantId: string,
    agentId: string,
    executionId: string,
    taskCount: number,
    tokenCount: number,
    costUsd: number,
    periodStart: ISO8601,
    periodEnd: ISO8601
  }
}
```

---

### 4.7 CROSS-AGENT COLLABORATION EVENTS

These are the events that enable agents to trigger other agents.

#### Topic: `agent.collaboration.requested`
**Producer:** any AI agent (via ai-runtime)
**Consumers:** workflow-service (routes to target agent), analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    requestingAgentId: string,
    targetAgentId: string,
    executionId: string,           // parent execution context
    collaborationType: string,     // "delegate" | "notify" | "request_data" | "trigger_workflow"
    taskContext: object,
    priority: "urgent" | "normal" | "low",
    callbackTopic: string | null   // topic to publish result back to
  }
}
```

**Cross-agent collaboration map:**

| Requesting Agent | Triggers | Reason |
|---|---|---|
| AP Officer | Procurement Officer | Invoice has no matching PO — request PO confirmation |
| AR Officer | Customer Support Agent | Customer disputes invoice — hand off for relationship handling |
| Onboarding Coordinator | IT Service Desk Analyst | New hire needs system access provisioned |
| Compliance Officer | Risk Analyst | New compliance violation elevates risk register |
| Inventory Planner | Procurement Officer | Stock below reorder point — trigger purchase requisition |
| Recruiter | Onboarding Coordinator | Candidate accepted offer — start pre-join onboarding |
| Logistics Coordinator | Customer Support Agent | Shipment exception detected — notify customer |
| Marketing Campaign Coordinator | SDR | Campaign generates hot lead — route for immediate follow-up |
| GL Analyst | Compliance Officer | Unusual journal entry detected — flag for compliance review |
| Cybersecurity Analyst | IT Service Desk Analyst | Security incident requires user access suspension |

---

### 4.8 NOTIFICATION DOMAIN

#### Topic: `notification.requested`
**Producer:** any service
**Consumers:** notification-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    recipientUserId: string | null,
    recipientTeam: string | null,
    channels: NotificationChannel[],
    eventType: string,
    priority: "urgent" | "normal" | "low",
    subject: string,
    body: string,
    deepLinkUrl: string | null,
    metadata: object | null
  }
}
```

#### Topic: `notification.delivered`
**Producer:** notification-service
**Consumers:** analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    notificationId: string,
    channel: NotificationChannel,
    status: "delivered" | "failed" | "bounced",
    providerRef: string | null
  }
}
```

---

### 4.9 AUDIT DOMAIN

#### Topic: `audit.event.recorded`
**Producer:** all services (via shared audit-logger utility)
**Consumers:** audit-service (persists to DB), analytics-service

```typescript
{
  schemaVersion: "1.0",
  eventId: string,
  tenantId: string,
  timestamp: ISO8601,
  payload: {
    actorType: AuditActorType,
    actorId: string,
    action: string,
    entityType: string,
    entityId: string,
    beforeHash: string | null,     // SHA256 of before state
    afterHash: string | null,      // SHA256 of after state
    ipAddress: string | null,
    metadata: object | null
  }
}
```

> **Note:** Full before/after JSON is written directly to the `audit_logs` DB table by the audit-service.
> The Kafka event carries only hashes to keep event size small.

---

## 5. Consumer Group Strategy

```
SERVICE                    CONSUMER GROUP                    TOPICS CONSUMED
─────────────────────────────────────────────────────────────────────────────
ai-runtime                 ai-runtime-consumers              workflow.execution.started
                                                             human.task.resolved
                                                             tenant.config.updated
                                                             agent.collaboration.requested

workflow-service           workflow-consumers                human.task.resolved (resume)
                                                             agent.status.changed
                                                             escalation.sla.breached

integration-hub            integration-consumers             tenant.config.updated
                                                             integration.token.refreshed

notification-service       notification-consumers            notification.requested
                                                             escalation.created
                                                             human.task.created
                                                             billing.payment.failed
                                                             agent.status.changed

analytics-service          analytics-consumers               ALL topics (fan-out)
                                                             workflow.execution.completed
                                                             billing.usage.recorded

audit-service              audit-consumers                   audit.event.recorded
                                                             workflow.execution.completed
                                                             human.task.resolved

billing-service            billing-consumers                 billing.usage.recorded
                                                             billing.subscription.activated
                                                             billing.payment.failed

tenant-service             tenant-consumers                  billing.payment.failed
                                                             billing.subscription.activated
```

---

## 6. Error Handling & Dead Letter Queue

```
RETRY POLICY (per topic class)
═══════════════════════════════

Transient errors (network, timeout):
  Retry: 3 attempts
  Backoff: exponential (1s, 4s, 16s)
  After 3 failures → publish to .dlq topic

Business errors (invalid data, missing entity):
  No retry — publish directly to .dlq
  Alert engineering via PagerDuty if DLQ rate > 1%

DLQ handling:
  Every .dlq topic has a dedicated consumer in each service
  DLQ events: logged, alerted, manually re-processed after fix
  DLQ retention: 7 days
  DLQ monitoring: Grafana alert if DLQ size > 100 events
```

---

## 7. Schema Evolution Rules

```
BACKWARD COMPATIBLE (allowed without version bump):
  ✓ Add optional field to payload
  ✓ Add new enum value
  ✓ Widen a type (int → number)

BREAKING CHANGE (requires schemaVersion increment):
  ✗ Remove or rename a field
  ✗ Change a field type narrowly
  ✗ Change topic name (use new topic, deprecate old)

VERSION TRANSITION:
  Both old and new schema consumers run in parallel for 2 sprints
  Old topic marked deprecated in this doc
  Old topic removed after all consumers migrated
```

---

## 8. Local Development Setup

```bash
# Start Kafka (docker-compose)
docker-compose up kafka zookeeper -d

# Create all topics
./scripts/kafka-create-topics.sh

# Kafka UI (development only)
http://localhost:8085

# Test event publishing
npx ts-node scripts/kafka-test-publish.ts \
  --topic workflow.execution.started \
  --tenantId tenant_test_001

# Consume from topic (debug)
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic workflow.execution.started \
  --from-beginning
```

---

## 9. Monitoring & Alerting

```yaml
grafana_alerts:
  - name: "Consumer Lag High"
    condition: "consumer_lag > 10000"
    severity: WARNING
    notification: slack_ops

  - name: "DLQ Size Growing"
    condition: "dlq_message_count > 100"
    severity: CRITICAL
    notification: pagerduty

  - name: "Producer Error Rate"
    condition: "producer_errors_per_min > 10"
    severity: WARNING
    notification: slack_ops

  - name: "Escalation Not Consumed"
    condition: "escalation.created lag > 60 seconds"
    severity: CRITICAL
    notification: pagerduty
```

---

*AI Digital Workforce Platform | Kafka Event Topology v1.0.0*
*All async inter-service communication defined here — producers and consumers*
