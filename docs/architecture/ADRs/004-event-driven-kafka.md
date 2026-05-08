# ADR-004: Apache Kafka for Asynchronous Event Streaming

| Field      | Value                                                       |
|------------|-------------------------------------------------------------|
| **Status** | Accepted                                                    |
| **Date**   | 2025-03-01                                                  |
| **Authors**| Platform Architecture Team                                  |
| **Deciders**| CTO, VP Engineering                                        |

## Context

The ADWP platform consists of 8 NestJS microservices (auth, tenant, subscription, agent-registry, workflow, integration-hub, notification, analytics) plus a Python-based AI runtime. These services need to:

1. **Communicate asynchronously** -- Workflows span multiple services and agents. Synchronous HTTP calls create tight coupling and cascading failures.
2. **Maintain an audit trail** -- Enterprise customers require a complete record of all system events for compliance (SOC 2, GDPR).
3. **Support event sourcing** -- Agent actions, workflow transitions, and billing events must be replayable for debugging and reconciliation.
4. **Enable real-time notifications** -- Escalations, task completions, and SLA breaches must trigger notifications within seconds.

Three messaging options were evaluated:

| Option          | Pros                                           | Cons                                    |
|-----------------|------------------------------------------------|-----------------------------------------|
| RabbitMQ        | Simple, mature, flexible routing               | No replay, limited throughput at scale  |
| Apache Kafka    | Durable log, replay, high throughput, ordering | Operational complexity, latency floor   |
| AWS SQS/SNS     | Managed, low ops                              | Vendor lock-in, no replay, ordering limits |

## Decision

Adopt **Apache Kafka** as the platform's event streaming backbone, using typed topics with a standardized event envelope.

### Topic Architecture

The platform defines 24 topics across 8 domains in `packages/kafka/src/events/topics.ts`:

```typescript
export const TOPICS = {
  // Tenant domain
  TENANT_PROVISIONED:              'tenant.provisioned',
  TENANT_STATUS_CHANGED:           'tenant.status.changed',
  TENANT_CONFIG_UPDATED:           'tenant.config.updated',

  // Agent domain
  AGENT_SUBSCRIBED:                'agent.subscribed',
  AGENT_ACTIVATED:                 'agent.activated',
  AGENT_STATUS_CHANGED:            'agent.status.changed',

  // Workflow domain
  WORKFLOW_EXECUTION_STARTED:      'workflow.execution.started',
  WORKFLOW_STEP_COMPLETED:         'workflow.step.completed',
  WORKFLOW_EXECUTION_COMPLETED:    'workflow.execution.completed',
  WORKFLOW_EXECUTION_FAILED:       'workflow.execution.failed',

  // Escalation / Human task domain
  ESCALATION_CREATED:              'escalation.created',
  ESCALATION_SLA_BREACHED:         'escalation.sla.breached',
  HUMAN_TASK_CREATED:              'human.task.created',
  HUMAN_TASK_RESOLVED:             'human.task.resolved',

  // Integration domain
  INTEGRATION_CONNECTED:           'integration.connected',
  INTEGRATION_CONNECTION_FAILED:   'integration.connection.failed',
  INTEGRATION_TOKEN_REFRESHED:     'integration.token.refreshed',

  // Billing domain
  BILLING_SUBSCRIPTION_ACTIVATED:  'billing.subscription.activated',
  BILLING_PAYMENT_FAILED:          'billing.payment.failed',
  BILLING_USAGE_RECORDED:          'billing.usage.recorded',

  // Cross-agent collaboration
  AGENT_COLLABORATION_REQUESTED:   'agent.collaboration.requested',

  // Notification domain
  NOTIFICATION_REQUESTED:          'notification.requested',
  NOTIFICATION_DELIVERED:           'notification.delivered',

  // Audit domain
  AUDIT_EVENT_RECORDED:            'audit.event.recorded',
} as const;
```

### Topic Naming Convention

Topics follow the pattern: `<domain>.<entity>.<action>`

- `tenant.provisioned` -- A new tenant was created
- `workflow.execution.completed` -- A workflow run finished
- `escalation.sla.breached` -- An escalation passed its SLA deadline

### Event Envelope

All events implement the `BaseEvent` interface:

```typescript
interface BaseEvent {
  eventId: string;       // UUID, globally unique
  eventType: string;     // matches the topic name
  tenantId: string;      // tenant context for routing and filtering
  timestamp: string;     // ISO 8601
  version: string;       // event schema version
  source: string;        // producing service name
  correlationId?: string; // for tracing across services
  payload: unknown;      // domain-specific data
}
```

### Shared Kafka Package

The `@adwp/kafka` package (`packages/kafka/`) provides reusable infrastructure:

| Export                 | Purpose                                                    |
|------------------------|------------------------------------------------------------|
| `KafkaModule`          | NestJS dynamic module for Kafka configuration              |
| `KafkaProducerService` | Type-safe event publishing with serialization              |
| `AuditService`         | Convenience wrapper for publishing audit events            |
| `TOPICS`               | Typed topic name constants                                 |
| Event payloads         | TypeScript interfaces for all event types                  |

### Producer Pattern

Services publish events via the `KafkaProducerService`:

```typescript
@Injectable()
export class WorkflowService {
  constructor(
    private kafkaProducer: KafkaProducerService,
    private auditService: AuditService,
  ) {}

  async completeExecution(executionId: string, result: any) {
    // ... business logic ...

    // Publish domain event
    await this.kafkaProducer.publish(TOPICS.WORKFLOW_EXECUTION_COMPLETED, {
      eventId: uuid(),
      eventType: TOPICS.WORKFLOW_EXECUTION_COMPLETED,
      tenantId: execution.tenantId,
      timestamp: new Date().toISOString(),
      version: '1.0',
      source: 'workflow-service',
      payload: {
        executionId,
        definitionId: execution.definitionId,
        agentId: execution.agentId,
        status: 'completed',
        durationMs: execution.durationMs,
        tokensUsed: execution.tokenUsed,
      },
    });

    // Publish audit event
    await this.auditService.publish({
      tenantId: execution.tenantId,
      actorType: 'AI_AGENT',
      actorId: execution.agentId,
      action: 'workflow.completed',
      entityType: 'WorkflowExecution',
      entityId: executionId,
    });
  }
}
```

### Consumer Pattern

Services consume events using NestJS Kafka consumer groups:

```typescript
@Controller()
export class NotificationConsumer {
  @EventPattern(TOPICS.ESCALATION_CREATED)
  async handleEscalation(event: BaseEvent<EscalationCreatedPayload>) {
    // Send notification to assigned team
    await this.notificationService.sendEscalationAlert(event.payload);
  }

  @EventPattern(TOPICS.WORKFLOW_EXECUTION_FAILED)
  async handleWorkflowFailure(event: BaseEvent<WorkflowExecutionFailedPayload>) {
    // Notify tenant admin of failure
    await this.notificationService.sendFailureAlert(event.payload);
  }
}
```

### Event Flow Examples

**Agent Execution Flow:**

```
workflow-service                ai-runtime              notification-service
     |                              |                         |
     |--WORKFLOW_EXECUTION_STARTED->|                         |
     |                              |                         |
     |                         [agent runs]                   |
     |                              |                         |
     |                              |--ESCALATION_CREATED---->|
     |                              |                    [send alert]
     |<-WORKFLOW_STEP_COMPLETED-----|                         |
     |<-WORKFLOW_EXECUTION_COMPLETED|                         |
     |                              |                         |
     |--AUDIT_EVENT_RECORDED------->audit-service             |
```

**Billing Flow:**

```
subscription-service          analytics-service         notification-service
     |                              |                         |
     |--BILLING_SUBSCRIPTION_ACTIVATED-->                      |
     |                              |                         |
     |--BILLING_USAGE_RECORDED----->|                         |
     |                         [aggregate metrics]            |
     |                              |                         |
     |--BILLING_PAYMENT_FAILED----->|-------------------->    |
     |                              |              [send payment alert]
```

### Dead Letter Queue

Failed messages are routed to the `dlq_entries` table in PostgreSQL:

```prisma
model DlqEntry {
  id          String   @id @default(uuid())
  topic       String
  partition   Int
  offset      String
  key         String?
  value       Json
  headers     Json     @default("{}")
  error       String
  retryCount  Int      @default(0)
  maxRetries  Int      @default(3)
  status      String   @default("pending")
  createdAt   DateTime @default(now())
  processedAt DateTime?

  @@index([topic, status])
  @@map("dlq_entries")
}
```

DLQ entries can be retried manually or by an automated job that re-publishes them to the original topic.

### Infrastructure

Local development uses the Confluent Kafka Docker image:

```yaml
# docker-compose.yml
kafka:
  image: confluentinc/cp-kafka:7.5.0
  ports:
    - "9092:9092"
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
    KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
```

Production uses a 3-broker cluster (configured in `configmap.yaml`):

```yaml
KAFKA_BROKERS: "adwp-kafka-0.adwp-kafka:9092,adwp-kafka-1.adwp-kafka:9092,adwp-kafka-2.adwp-kafka:9092"
```

A Kafka UI is available for local debugging at `localhost:8085`.

## Consequences

### Positive

- **Decoupled services** -- Services communicate through events without direct HTTP dependencies. A service can be restarted or deployed independently.
- **Reliable delivery** -- Kafka's durable log ensures events are not lost even if a consumer is temporarily down.
- **Replayability** -- Events can be replayed from any offset for debugging, reprocessing, or onboarding new consumers.
- **Audit trail** -- The `AUDIT_EVENT_RECORDED` topic and `AuditService` provide a complete compliance audit stream.
- **Scalable** -- Kafka handles high-throughput event streams. Partitioning by `tenantId` enables parallel processing.
- **Type safety** -- TypeScript event payload interfaces catch schema mismatches at compile time.

### Negative

- **Operational complexity** -- Running a Kafka cluster (ZooKeeper + brokers) requires monitoring, capacity planning, and operational expertise.
- **Eventual consistency** -- Consumers process events asynchronously. UI state may briefly be stale after an action.
- **Schema evolution** -- Changing event payloads requires backward-compatible changes and versioning discipline.
- **Debugging complexity** -- Tracing a request across multiple services through event chains requires correlation IDs and centralized logging.

### Topic Governance

| Rule                                                          | Enforcement                    |
|---------------------------------------------------------------|--------------------------------|
| All topics defined in `TOPICS` constant                       | Code review, lint rule         |
| All events include `tenantId`                                 | BaseEvent interface            |
| New topic requires ADR amendment or design review             | PR template checklist          |
| Payload interfaces must be backward compatible                | Compile-time checks            |

## Related

- `packages/kafka/` -- Shared Kafka module, producer, audit service, topics, event payloads
- `infrastructure/docker/docker-compose.yml` -- Local Kafka setup
- `infrastructure/k8s/configmap.yaml` -- Production Kafka broker configuration
- `database/prisma/schema.prisma` -- DlqEntry model
- ADR-003: Multi-Tenancy RLS (events include tenantId)
