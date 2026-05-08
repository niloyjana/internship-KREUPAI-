# ADR-003: Row-Level Security for Multi-Tenant Data Isolation

| Field      | Value                                                       |
|------------|-------------------------------------------------------------|
| **Status** | Accepted                                                    |
| **Date**   | 2025-03-01                                                  |
| **Authors**| Platform Architecture Team                                  |
| **Deciders**| CTO, VP Engineering, Security Lead                         |

## Context

The AI Digital Workforce Platform is a SaaS product serving multiple companies (tenants) from a shared infrastructure. Each tenant subscribes to a set of AI agents, configures integration connections, stores sensitive business data (invoices, employee records, customer interactions, contracts), and generates audit logs.

The platform must guarantee **zero cross-tenant data leakage** -- a tenant must never see, modify, or receive AI analysis that references another tenant's data. This is a non-negotiable security requirement for enterprise customers and regulatory compliance (SOC 2, GDPR).

Three primary isolation strategies were evaluated:

| Strategy                | Pros                                              | Cons                                               |
|-------------------------|---------------------------------------------------|-----------------------------------------------------|
| Database per tenant     | Strong isolation, easy to reason about             | Operational complexity, expensive at scale           |
| Schema per tenant       | Good isolation, single cluster                     | Migration complexity, connection pooling challenges  |
| Shared schema with RLS  | Single schema, simple operations, automatic filter | Requires discipline, slight query overhead           |

## Decision

Implement **PostgreSQL Row-Level Security (RLS)** with a `tenantId` column on all tenant-scoped tables, combined with application-layer tenant context injection.

### Database Design

Every tenant-scoped table includes a `tenantId` foreign key referencing the `tenants` table. The Prisma schema enforces this at the model level:

```prisma
model WorkflowExecution {
  id         String @id @default(cuid())
  tenantId   String
  // ... other fields
  tenant     Tenant @relation(fields: [tenantId], references: [id])

  @@index([tenantId, agentId])
  @@index([tenantId, status])
  @@map("workflow_executions")
}
```

Tables with tenant-scoped data include (non-exhaustive):

| Domain                   | Tables                                                              |
|--------------------------|---------------------------------------------------------------------|
| Tenant & Identity        | `tenant_users`, `user_sessions`, `api_keys`                        |
| Agent Registry           | `agent_subscriptions`, `agent_configs`, `agent_instances`           |
| Workflow Engine          | `workflow_definitions`, `workflow_executions`, `workflow_steps`      |
| Escalation               | `escalation_tickets`, `human_tasks`                                |
| Integration Hub          | `integration_connections`, `integration_logs`, `integration_webhooks` |
| AI Memory                | `agent_working_memory`, `agent_episodic_memory`, `agent_semantic_memory` |
| Audit & Compliance       | `audit_logs`, `agent_actions`                                      |
| Notifications            | `notification_preferences`, `notification_logs`                    |
| Billing                  | `billing_events`, `invoices`, `usage_metrics`                      |
| Customer Operations      | `support_interactions`                                             |
| Sales & Marketing        | `lead_records`, `outreach_activities`, `opportunity_summaries`     |
| HR & People Ops          | `onboarding_records`, `payroll_validation_runs`, `payroll_exceptions` |
| Finance & Procurement    | `finance_invoices`, `receivable_invoices`, `purchase_requisitions`  |
| Governance & Risk        | `compliance_violations`, `risk_register_items`, `contract_records` |
| Knowledge Base           | `knowledge_articles`                                               |

### Row-Level Security Policies

RLS policies are applied at the PostgreSQL level to enforce that queries can only access rows matching the current session's tenant:

```sql
-- Enable RLS on table
ALTER TABLE workflow_executions ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see their tenant's rows
CREATE POLICY tenant_isolation ON workflow_executions
  USING (tenant_id = current_setting('app.current_tenant_id')::text);

-- Force RLS even for table owners
ALTER TABLE workflow_executions FORCE ROW LEVEL SECURITY;
```

### Application-Layer Tenant Context

Each NestJS microservice uses a `TenantContextInterceptor` that:

1. Extracts the `tenantId` from the authenticated JWT token.
2. Sets the PostgreSQL session variable before any database query:

```typescript
// Simplified TenantContextInterceptor
@Injectable()
export class TenantContextInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler) {
    const request = context.switchToHttp().getRequest();
    const tenantId = request.user?.tenantId;

    if (tenantId) {
      // Set the session variable that RLS policies reference
      return from(
        this.prisma.$executeRawUnsafe(
          `SET LOCAL app.current_tenant_id = '${tenantId}'`
        )
      ).pipe(switchMap(() => next.handle()));
    }

    return next.handle();
  }
}
```

3. All subsequent Prisma queries within the request automatically filter by the tenant via RLS -- no `WHERE tenantId = ?` clause needed in application code (though Prisma queries include it for defense-in-depth).

### AI Runtime Tenant Context

The AI runtime (Python/FastAPI) receives `tenantId` in the execution context and passes it through the orchestration pipeline:

```python
# OrchestrationEngine.execute()
tenant_id = context.get("tenantId", "default")

# All database operations include tenant_id
await create_execution(
    execution_id=execution_id,
    agent_type=agent_id,
    tenant_id=tenant_id,
    input_data=redacted_payload,
)
```

### Kubernetes Configuration

The platform-wide tenant isolation mode is set in the Kubernetes ConfigMap:

```yaml
data:
  TENANT_ISOLATION_MODE: "rls"
```

### Defense-in-Depth Layers

The tenant isolation strategy employs multiple layers:

```
Layer 1: JWT Authentication
  |-- tenantId embedded in access token
  |
Layer 2: Application Interceptor
  |-- Sets PostgreSQL session variable per request
  |
Layer 3: PostgreSQL RLS Policies
  |-- Automatic row filtering at database level
  |
Layer 4: Application Query Filters
  |-- Prisma queries include tenantId for explicit filtering
  |
Layer 5: Audit Logging
  |-- All data access is logged with tenantId for compliance
```

## Consequences

### Positive

- **Strong isolation at the database layer** -- Even if application code omits a tenant filter, RLS policies prevent cross-tenant data access.
- **Single database cluster** -- Simplified operations, backups, migrations, and monitoring compared to database-per-tenant.
- **Transparent to application code** -- Once the session variable is set, developers write normal queries without worrying about tenant filtering.
- **Audit-friendly** -- The `audit_logs` table records all data access with `tenantId`, `actorType`, `actorId`, and `action` for compliance reporting.
- **Scalable** -- PostgreSQL RLS handles thousands of tenants efficiently with proper indexing on `tenantId`.

### Negative

- **Slight performance overhead** -- RLS policy evaluation adds a small cost to every query. Mitigated by indexing `tenantId` on all tenant-scoped tables.
- **Migration complexity** -- Adding RLS policies must be coordinated with Prisma schema migrations. New tables must have RLS enabled explicitly.
- **Developer discipline required** -- New tables must include `tenantId` and have RLS policies applied. Code review checklists and CI checks enforce this.
- **Session variable management** -- The interceptor must correctly set the session variable for every request. Connection pooling must not leak session state between requests (PostgreSQL `SET LOCAL` is transaction-scoped).

### Testing Strategy

| Test Type          | Approach                                                       |
|--------------------|----------------------------------------------------------------|
| Unit tests         | Mock Prisma client with tenantId assertions                    |
| Integration tests  | Create two test tenants, verify cross-tenant queries return empty |
| Security tests     | Attempt direct SQL without session variable, verify RLS blocks   |
| Load tests         | Measure query latency with RLS enabled vs disabled              |

## Related

- `database/prisma/schema.prisma` -- Prisma schema with tenantId on all models
- `infrastructure/k8s/configmap.yaml` -- `TENANT_ISOLATION_MODE: "rls"`
- `services/auth-service/` -- JWT token issuance with tenantId claim
- ADR-004: Event-Driven Kafka (events include tenantId for routing)
