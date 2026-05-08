# ADWP API Service Contracts
## OpenAPI 3.0 Specifications — All Platform Services
**File:** `docs/api/service-contracts.md`
**Version:** 1.0.0

---

> This document defines the REST API contract for every microservice.
> Frontend, mobile, and AI runtime teams code against these contracts.
> No service endpoint may be built without a corresponding spec here.
> Full OpenAPI YAML lives in `docs/api/{service-name}.openapi.yaml`

---

## 1. API Design Standards

```
BASE URL PATTERN
  Production:   https://api.adwp.io/v1/{service}
  Staging:      https://api-staging.adwp.io/v1/{service}
  Local:        http://localhost:{port}/v1/{service}

AUTHENTICATION
  All endpoints (except /auth/login, /auth/refresh):
    Header: Authorization: Bearer {jwt_access_token}

  API Key (system-to-system):
    Header: X-API-Key: {api_key}

TENANT CONTEXT
  Extracted from JWT claims (preferred)
  Override header: X-Tenant-ID: {tenantId} (platform admin only)

RESPONSE ENVELOPE
  Success:
  {
    "success": true,
    "data": { ... },
    "meta": { "page": 1, "pageSize": 20, "total": 150 }
  }

  Error:
  {
    "success": false,
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested agent was not found",
      "field": null,            // for validation errors
      "traceId": "abc123"
    }
  }

PAGINATION
  Query: ?page=1&pageSize=20&sortBy=createdAt&sortDir=desc

HTTP STATUS CODES
  200 OK             — success (GET, PUT, PATCH)
  201 Created        — success (POST creating resource)
  204 No Content     — success (DELETE)
  400 Bad Request    — validation error
  401 Unauthorized   — missing/invalid token
  403 Forbidden      — valid token, insufficient permissions
  404 Not Found      — resource does not exist
  409 Conflict       — duplicate resource
  422 Unprocessable  — business rule violation
  429 Too Many Req   — rate limit hit
  500 Server Error   — unexpected server error
```

---

## 2. Auth Service API
**Base:** `/v1/auth` | **Port:** 3001

### POST `/v1/auth/login`
Authenticate user and issue tokens.

**Request:**
```json
{
  "email": "user@company.com",
  "password": "string",
  "tenantSlug": "acme-corp"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "expiresIn": 900,
    "user": {
      "id": "usr_01",
      "name": "John Smith",
      "email": "user@company.com",
      "role": "TENANT_ADMIN",
      "tenantId": "tnt_01"
    }
  }
}
```

### POST `/v1/auth/refresh`
Exchange refresh token for new access token.

**Request:**
```json
{ "refreshToken": "eyJ..." }
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "expiresIn": 900
  }
}
```

### POST `/v1/auth/logout`
Revoke current session.
**Auth required.** No body. **Response 204.**

### POST `/v1/auth/mfa/verify`
Verify TOTP MFA code.
```json
{ "code": "123456" }
```

### GET `/v1/auth/me`
Get current user profile.
**Response 200:** Returns user object with roles and tenant info.

### POST `/v1/auth/api-keys`
Create API key for service account.
```json
{
  "name": "Automation Key",
  "expiresAt": "2027-01-01T00:00:00Z"
}
```

### DELETE `/v1/auth/api-keys/{keyId}`
Revoke an API key. **Response 204.**

---

## 3. Tenant Service API
**Base:** `/v1/tenants` | **Port:** 3002

### POST `/v1/tenants`
Create new tenant (platform admin only).
```json
{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "plan": "GROWTH",
  "adminEmail": "admin@acme.com",
  "adminName": "Sarah Johnson",
  "countryCode": "BH",
  "timezone": "Asia/Bahrain"
}
```

### GET `/v1/tenants/{tenantId}`
Get tenant details.
**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": "tnt_01",
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "plan": "GROWTH",
    "status": "ACTIVE",
    "countryCode": "BH",
    "timezone": "Asia/Bahrain",
    "config": {},
    "createdAt": "2026-01-15T09:00:00Z",
    "agentCount": 5,
    "activeUserCount": 12
  }
}
```

### PATCH `/v1/tenants/{tenantId}`
Update tenant configuration.
```json
{
  "name": "Acme Corp",
  "timezone": "Asia/Dubai",
  "config": {
    "logoUrl": "https://...",
    "primaryColor": "#2563EB"
  }
}
```

### GET `/v1/tenants/{tenantId}/users`
List all users in tenant.
**Query:** `?page=1&pageSize=20&role=TENANT_ADMIN&status=ACTIVE`

### POST `/v1/tenants/{tenantId}/users`
Invite user to tenant.
```json
{
  "email": "newuser@acme.com",
  "name": "Ali Hassan",
  "role": "END_USER",
  "department": "Finance"
}
```

### PATCH `/v1/tenants/{tenantId}/users/{userId}`
Update user role or status.
```json
{
  "role": "DEPARTMENT_MANAGER",
  "status": "ACTIVE"
}
```

### DELETE `/v1/tenants/{tenantId}/users/{userId}`
Remove user from tenant. **Response 204.**

---

## 4. Agent Registry API
**Base:** `/v1/agents` | **Port:** 3003

### GET `/v1/agents/catalog`
List all available AI worker definitions.
**Query:** `?department=FINANCE_PROCUREMENT&isActive=true`

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "agentId": "ai-ap-officer",
      "name": "AI Accounts Payable Officer",
      "department": "FINANCE_PROCUREMENT",
      "description": "Processes supplier invoices end-to-end...",
      "version": "1.0.0",
      "monthlyPricingUsd": 300,
      "pricingTier": "standard",
      "capabilities": ["invoice_capture", "po_matching", "duplicate_detection"],
      "requiredIntegrations": ["ERP", "EMAIL"],
      "isActive": true
    }
  ],
  "meta": { "total": 25 }
}
```

### GET `/v1/agents/catalog/{agentId}`
Get full agent definition including default policy.

### GET `/v1/agents/subscribed`
List tenant's subscribed and configured agents.

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "agentId": "ai-ap-officer",
      "name": "AI Accounts Payable Officer",
      "displayName": "Our AP Bot",
      "status": "ACTIVE",
      "subscriptionStatus": "ACTIVE",
      "integrationIds": ["int_01", "int_02"],
      "isEnabled": true,
      "lastActiveAt": "2026-03-10T14:30:00Z",
      "todayTaskCount": 47,
      "pendingEscalations": 2
    }
  ]
}
```

### GET `/v1/agents/{agentId}/config`
Get tenant-specific agent configuration.

### PUT `/v1/agents/{agentId}/config`
Update agent configuration and policy.
```json
{
  "displayName": "Our AP Bot",
  "policyJson": {
    "matching_policy": {
      "price_tolerance_percent": 3,
      "three_way_matching_above_amount": 10000
    }
  },
  "integrationIds": ["int_01", "int_02"]
}
```

### GET `/v1/agents/{agentId}/status`
Get real-time agent status.
```json
{
  "success": true,
  "data": {
    "agentId": "ai-ap-officer",
    "status": "WORKING",
    "currentTaskId": "exec_789",
    "currentTaskSummary": "Processing invoice INV-2024-1234",
    "lastActiveAt": "2026-03-10T14:30:00Z",
    "todayStats": {
      "tasksCompleted": 47,
      "tasksEscalated": 2,
      "avgDurationMs": 12400,
      "tokenCostUsd": 0.89
    }
  }
}
```

### POST `/v1/agents/{agentId}/enable`
Enable a previously paused agent. **Response 200.**

### POST `/v1/agents/{agentId}/pause`
Pause agent (stops accepting new tasks). **Response 200.**

---

## 5. Workflow Service API
**Base:** `/v1/workflows` | **Port:** 3004

### GET `/v1/workflows/definitions`
List workflow definitions for tenant.
**Query:** `?agentId=ai-ap-officer`

### POST `/v1/workflows/definitions`
Create workflow definition.
```json
{
  "agentId": "ai-ap-officer",
  "name": "Invoice Processing Workflow",
  "triggerType": "email",
  "triggerConfig": {
    "inboxId": "int_email_01",
    "subjectFilter": "invoice"
  },
  "stepsJson": [...]
}
```

### GET `/v1/workflows/executions`
List workflow executions.
**Query:** `?agentId=ai-recruiter&status=RUNNING&from=2026-03-01&page=1&pageSize=20`

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "id": "exec_789",
      "agentId": "ai-recruiter",
      "status": "RUNNING",
      "triggerSource": "email:msg_abc",
      "currentStep": "Step 3: Calendar scheduling",
      "startedAt": "2026-03-10T14:28:00Z",
      "durationMs": 142000,
      "stepCount": 5,
      "completedSteps": 2
    }
  ],
  "meta": { "total": 234, "page": 1 }
}
```

### GET `/v1/workflows/executions/{executionId}`
Get full execution detail including all steps.

### GET `/v1/workflows/executions/{executionId}/steps`
Get step-by-step breakdown of an execution.

### POST `/v1/workflows/executions/{executionId}/cancel`
Cancel a running workflow. **Response 200.**

### GET `/v1/workflows/human-tasks`
List pending human tasks for current user.
**Query:** `?status=PENDING&assignedTo=me&priority=HIGH`

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "id": "task_456",
      "title": "Approve refund: $520 for customer@email.com",
      "agentId": "ai-customer-support-agent",
      "priority": "HIGH",
      "dueAt": "2026-03-10T18:00:00Z",
      "slaMinutesRemaining": 210,
      "contextSummary": "Customer requested refund for order ORD-9912...",
      "recommendedAction": "Approve — within policy limit",
      "contextJson": { ... }
    }
  ]
}
```

### POST `/v1/workflows/human-tasks/{taskId}/resolve`
Resolve a human task (approve/reject/modify).
```json
{
  "decision": "approve",
  "decisionNote": "Verified order. Refund approved.",
  "modifiedPayload": null
}
```

### GET `/v1/workflows/escalations`
List escalation tickets.
**Query:** `?status=OPEN&severity=HIGH&agentId=ai-compliance-officer`

### GET `/v1/workflows/escalations/{escalationId}`
Get escalation detail.

### PATCH `/v1/workflows/escalations/{escalationId}`
Update escalation (assign, resolve, escalate further).
```json
{
  "assignedToUserId": "usr_123",
  "status": "IN_REVIEW",
  "resolutionNote": "Under investigation"
}
```

---

## 6. Subscription Service API
**Base:** `/v1/subscriptions` | **Port:** 3005

### GET `/v1/subscriptions`
Get tenant's agent subscriptions.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "platformFeeUsd": 499,
    "agents": [
      {
        "agentId": "ai-recruiter",
        "status": "ACTIVE",
        "monthlyPriceUsd": 250,
        "startedAt": "2026-01-01T00:00:00Z",
        "stripeSubItemId": "si_abc"
      }
    ],
    "totalMonthlyUsd": 1249,
    "discount": 0.15,
    "discountReason": "Department bundle (3+ agents)"
  }
}
```

### POST `/v1/subscriptions/agents`
Subscribe to a new agent.
```json
{
  "agentId": "ai-compliance-officer"
}
```

### DELETE `/v1/subscriptions/agents/{agentId}`
Unsubscribe from an agent. **Response 200** (returns effective cancellation date).

### GET `/v1/subscriptions/usage`
Get usage metering for current billing period.
**Query:** `?agentId=ai-ap-officer&from=2026-03-01&to=2026-03-31`

```json
{
  "success": true,
  "data": {
    "period": { "start": "2026-03-01", "end": "2026-03-31" },
    "agents": [
      {
        "agentId": "ai-ap-officer",
        "taskCount": 1240,
        "tokenCount": 4820000,
        "llmCostUsd": 24.10,
        "escalationCount": 8,
        "avgTaskDurationMs": 14200
      }
    ]
  }
}
```

### GET `/v1/subscriptions/invoices`
List invoices.

### GET `/v1/subscriptions/invoices/{invoiceId}`
Get invoice detail with line items.

---

## 7. Integration Hub API
**Base:** `/v1/integrations` | **Port:** 3006

### GET `/v1/integrations/catalog`
List all available integration providers.

### GET `/v1/integrations/connections`
List tenant's connected integrations.

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "id": "int_01",
      "provider": "HUBSPOT",
      "name": "Our HubSpot CRM",
      "status": "CONNECTED",
      "lastSyncAt": "2026-03-10T14:00:00Z",
      "scopesGranted": ["contacts.read", "contacts.write", "deals.read"],
      "connectedAgents": ["ai-sdr", "ai-account-exec-assistant"]
    }
  ]
}
```

### POST `/v1/integrations/connections`
Initiate new integration connection.
```json
{
  "provider": "HUBSPOT",
  "name": "Our HubSpot CRM",
  "authType": "oauth2"
}
```
**Response 201:**
```json
{
  "success": true,
  "data": {
    "connectionId": "int_02",
    "authUrl": "https://app.hubspot.com/oauth/authorize?client_id=...&redirect_uri=..."
  }
}
```

### GET `/v1/integrations/connections/{connectionId}`
Get connection detail and health.

### DELETE `/v1/integrations/connections/{connectionId}`
Disconnect integration. **Response 204.**

### GET `/v1/integrations/connections/{connectionId}/logs`
Get integration activity logs.
**Query:** `?status=error&from=2026-03-01&page=1&pageSize=50`

### POST `/v1/integrations/connections/{connectionId}/test`
Test connectivity of an integration.
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "responseTimeMs": 234,
    "permissionsValid": true
  }
}
```

### POST `/v1/integrations/webhooks`
Register inbound webhook endpoint.
```json
{
  "name": "Stripe Payment Events",
  "provider": "CUSTOM",
  "secret": "wh_secret_xyz"
}
```

---

## 8. Analytics Service API
**Base:** `/v1/analytics` | **Port:** 3007

### GET `/v1/analytics/dashboard`
Get tenant overview dashboard metrics.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "period": "today",
    "activeAgents": 7,
    "totalTasksToday": 312,
    "tasksCompleted": 298,
    "tasksFailed": 4,
    "pendingEscalations": 5,
    "pendingHumanTasks": 12,
    "avgTaskDurationMs": 13800,
    "totalLlmCostUsdToday": 7.42,
    "topAgentByTasks": "ai-ap-officer",
    "agentBreakdown": [
      {
        "agentId": "ai-ap-officer",
        "tasksCompleted": 92,
        "escalationRate": 0.04
      }
    ]
  }
}
```

### GET `/v1/analytics/agents/{agentId}/performance`
Get detailed KPI report for a specific agent.
**Query:** `?from=2026-03-01&to=2026-03-31&granularity=daily`

### GET `/v1/analytics/agents/{agentId}/tasks`
Task history and outcome breakdown.

### GET `/v1/analytics/escalations`
Escalation trends and resolution times.

### GET `/v1/analytics/compliance`
Audit summary and compliance exception report.
**Query:** `?from=2026-01-01&to=2026-03-31&format=pdf`

### GET `/v1/analytics/cost`
LLM cost and token usage breakdown.
**Query:** `?groupBy=agent&period=monthly`

---

## 9. Notification Service API
**Base:** `/v1/notifications` | **Port:** 3008

### GET `/v1/notifications/preferences`
Get user notification preferences.

### PUT `/v1/notifications/preferences`
Update notification preferences.
```json
{
  "preferences": [
    {
      "eventType": "escalation.created",
      "channels": ["EMAIL", "PUSH"],
      "enabled": true
    },
    {
      "eventType": "human.task.created",
      "channels": ["PUSH"],
      "enabled": true
    }
  ]
}
```

### GET `/v1/notifications/history`
Get notification history for current user.
**Query:** `?channel=EMAIL&from=2026-03-01&page=1&pageSize=20`

---

## 10. AI Runtime API (Internal)
**Base:** `http://ai-runtime:8000/v1` | **Python FastAPI**
**Note:** Not exposed externally. Called only by workflow-service via internal network.

### POST `/v1/agent/execute`
Execute a task on a specific agent.

**Request:**
```json
{
  "executionId": "exec_789",
  "tenantId": "tnt_01",
  "agentId": "ai-recruiter",
  "stepId": "step_01",
  "taskPayload": {
    "type": "screen_resume",
    "resumeUrl": "s3://...",
    "jobDefinitionId": "job_hr_012"
  },
  "contextJson": {
    "tenantConfig": { ... },
    "agentPolicy": { ... },
    "workingMemory": { ... }
  }
}
```

**Response 200:**
```json
{
  "executionId": "exec_789",
  "stepId": "step_01",
  "status": "completed",
  "output": {
    "candidateScore": 87,
    "recommendation": "shortlist",
    "reasoning": "Strong match on required skills...",
    "flaggedItems": []
  },
  "durationMs": 3200,
  "tokenUsed": 1840,
  "costUsd": 0.018,
  "nextAction": "schedule_interview"
}
```

### GET `/v1/agent/{agentId}/status`
Get agent runtime status (is the pod healthy?).

### POST `/v1/agent/escalate`
Trigger escalation from within an execution.

### GET `/v1/health`
Health check endpoint.
```json
{ "status": "healthy", "uptime": 98234, "agentsLoaded": 25 }
```

---

## 11. WebSocket Events (Real-Time Portal)
**Endpoint:** `wss://api.adwp.io/v1/ws`
**Auth:** `?token={accessToken}`

### Event Types (Server → Client)

```typescript
// Agent status changed
{
  type: "agent.status.changed",
  tenantId: string,
  agentId: string,
  status: AgentStatus,
  timestamp: ISO8601
}

// New escalation requiring action
{
  type: "escalation.created",
  escalationId: string,
  agentId: string,
  severity: EscalationSeverity,
  title: string,
  slaDeadlineAt: ISO8601
}

// Task completed
{
  type: "workflow.execution.completed",
  executionId: string,
  agentId: string,
  status: "COMPLETED" | "FAILED",
  summary: string
}

// New human task assigned to user
{
  type: "human.task.assigned",
  taskId: string,
  title: string,
  priority: string,
  dueAt: ISO8601
}

// Cost alert
{
  type: "cost.alert",
  agentId: string,
  dailySpendUsd: number,
  budgetLimitUsd: number,
  percentUsed: number
}
```

---

## 12. Rate Limits

| Endpoint Group | Limit | Window |
|---|---|---|
| Auth endpoints | 20 requests | per minute per IP |
| General API | 1000 requests | per minute per tenant |
| Analytics reports | 60 requests | per minute per tenant |
| AI Runtime execute | 100 requests | per minute per tenant |
| Integration calls | Varies by provider | Per provider limit |
| WebSocket connections | 50 simultaneous | per tenant |

---

## 13. Error Code Reference

| Code | Meaning |
|---|---|
| `AUTH_INVALID_CREDENTIALS` | Wrong email or password |
| `AUTH_TOKEN_EXPIRED` | JWT access token expired |
| `AUTH_INSUFFICIENT_PERMISSION` | Role does not have permission |
| `TENANT_NOT_FOUND` | Tenant ID invalid |
| `TENANT_SUSPENDED` | Tenant account is suspended |
| `AGENT_NOT_SUBSCRIBED` | Agent not in tenant's subscription |
| `AGENT_NOT_CONFIGURED` | Agent subscribed but integrations not set up |
| `WORKFLOW_EXECUTION_NOT_FOUND` | Execution ID invalid |
| `TASK_ALREADY_RESOLVED` | Human task already actioned |
| `INTEGRATION_AUTH_FAILED` | OAuth token invalid or expired |
| `INTEGRATION_RATE_LIMITED` | External provider rate limit hit |
| `GUARDRAIL_VIOLATION` | Action blocked by agent policy |
| `VALIDATION_FAILED` | Request body failed schema validation |
| `RESOURCE_NOT_FOUND` | Generic 404 |
| `DUPLICATE_RESOURCE` | Unique constraint violation |
| `INSUFFICIENT_BUDGET` | PR rejected due to no budget available |
| `LLM_PROVIDER_ERROR` | AI model call failed |

---

*AI Digital Workforce Platform | API Service Contracts v1.0.0*
*Full OpenAPI YAML files: `docs/api/{service-name}.openapi.yaml`*
