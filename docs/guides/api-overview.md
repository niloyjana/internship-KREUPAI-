# API Overview

This guide covers the API architecture, authentication, rate limiting, error handling, and key endpoints for the AI Digital Workforce Platform (ADWP).

---

## Table of Contents

1. [API Gateway Architecture](#api-gateway-architecture)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Error Response Format](#error-response-format)
5. [Key Endpoints by Service](#key-endpoints-by-service)
6. [WebSocket Events](#websocket-events)
7. [API Versioning](#api-versioning)

---

## API Gateway Architecture

All client requests pass through the API Gateway before reaching backend services:

```
Client (Web / Mobile / SDK)
    |
    v
API Gateway (Kong / AWS API Gateway)
    |-- Rate limiting (per tenant, per endpoint)
    |-- JWT validation
    |-- Request routing
    |-- Request/response logging
    |
    v
Backend Services (NestJS / FastAPI)
```

### Base URLs

| Environment | Base URL                          |
|-------------|-----------------------------------|
| Local       | `http://localhost:8080/api`        |
| Staging     | `https://staging.adwp.io/api`     |
| Production  | `https://app.adwp.io/api`         |

### Service Routing

The API Gateway routes requests to the appropriate backend service based on the URL path:

| Path Prefix                  | Service               | Internal Port |
|------------------------------|-----------------------|---------------|
| `/api/auth/*`                | auth-service          | 3010          |
| `/api/tenants/*`             | tenant-service        | 3011          |
| `/api/subscriptions/*`       | subscription-service  | 3012          |
| `/api/agent-registry/*`      | agent-registry        | 3013          |
| `/api/workflows/*`           | workflow-service      | 3014          |
| `/api/integrations/*`        | integration-hub       | 3015          |
| `/api/notifications/*`       | notification-service  | 3016          |
| `/api/analytics/*`           | analytics-service     | 3017          |
| `/api/ai-runtime/*`          | ai-runtime (FastAPI)  | 8000          |

---

## Authentication

### JWT Bearer Token

All API requests (except `/api/auth/login` and `/api/auth/register`) require a valid JWT Bearer token.

**Request header:**

```
Authorization: Bearer <access_token>
```

### Token Lifecycle

```
1. Login:       POST /api/auth/login → { accessToken, refreshToken }
2. Use:         Authorization: Bearer <accessToken>
3. Refresh:     POST /api/auth/refresh → { accessToken, refreshToken }
4. Logout:      POST /api/auth/logout → invalidates tokens
```

### JWT Claims

The access token contains the following claims:

```json
{
  "sub": "user-uuid",
  "tenantId": "tenant-uuid",
  "email": "user@company.com",
  "role": "tenant_admin",
  "iat": 1710000000,
  "exp": 1710000900
}
```

| Claim      | Description                                |
|------------|--------------------------------------------|
| `sub`      | User ID (UUID)                             |
| `tenantId` | Tenant ID -- used for RLS and data isolation |
| `email`    | User email address                         |
| `role`     | RBAC role (platform_admin, tenant_admin, department_manager, end_user, auditor) |
| `iat`      | Issued at (Unix timestamp)                 |
| `exp`      | Expiry (15 minutes after issuance)         |

### Token Expiry

| Token Type    | Expiry   | Storage Recommendation     |
|---------------|----------|----------------------------|
| Access Token  | 15 min   | Memory only (never persist)|
| Refresh Token | 7 days   | Secure HTTP-only cookie    |

### API Keys (System-to-System)

For service integrations and webhooks, API keys can be used instead of JWT:

```
X-API-Key: <api_key>
```

API keys are scoped to a tenant and have configurable permissions.

---

## Rate Limiting

Rate limits are enforced at the API Gateway level:

| Scope                | Limit              | Window    |
|----------------------|--------------------|-----------|
| Per tenant           | 1000 requests      | 1 minute  |
| Per user             | 100 requests       | 1 minute  |
| Per endpoint         | 50 requests        | 1 minute  |
| Agent execution      | 20 requests        | 1 minute  |
| LLM-intensive routes | 10 requests        | 1 minute  |

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1710001200
```

### Rate Limit Exceeded Response

```json
{
  "statusCode": 429,
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Retry after 23 seconds.",
  "retryAfter": 23
}
```

---

## Error Response Format

All API errors follow a consistent JSON format:

```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "details": [
    {
      "field": "email",
      "message": "must be a valid email address"
    }
  ],
  "requestId": "req_abc123def456",
  "timestamp": "2025-03-15T10:30:00.000Z"
}
```

### Standard Error Codes

| Status Code | Error                | Description                                   |
|-------------|----------------------|-----------------------------------------------|
| 400         | Bad Request          | Invalid input, validation failure              |
| 401         | Unauthorized         | Missing or invalid authentication token        |
| 403         | Forbidden            | Authenticated but insufficient permissions     |
| 404         | Not Found            | Resource does not exist                        |
| 409         | Conflict             | Resource already exists or state conflict      |
| 422         | Unprocessable Entity | Semantically invalid request                   |
| 429         | Too Many Requests    | Rate limit exceeded                            |
| 500         | Internal Server Error| Unexpected server error                        |
| 502         | Bad Gateway          | Upstream service unavailable                   |
| 503         | Service Unavailable  | Service temporarily unavailable                |

---

## Key Endpoints by Service

### Auth Service (`/api/auth`)

| Method | Endpoint                | Description                   | Auth Required |
|--------|-------------------------|-------------------------------|---------------|
| POST   | `/auth/register`        | Register a new user/tenant    | No            |
| POST   | `/auth/login`           | Authenticate and get tokens   | No            |
| POST   | `/auth/refresh`         | Refresh access token          | Refresh Token |
| POST   | `/auth/logout`          | Invalidate tokens             | Yes           |
| GET    | `/auth/me`              | Get current user profile      | Yes           |

### Tenant Service (`/api/tenants`)

| Method | Endpoint                        | Description                        | Auth Required |
|--------|---------------------------------|------------------------------------|---------------|
| GET    | `/tenants/current`              | Get current tenant details         | Yes           |
| PUT    | `/tenants/current`              | Update tenant settings             | Tenant Admin  |
| GET    | `/tenants/current/users`        | List tenant users                  | Tenant Admin  |
| POST   | `/tenants/current/users`        | Invite a user to the tenant        | Tenant Admin  |

### Agent Registry (`/api/agent-registry`)

| Method | Endpoint                                | Description                     | Auth Required |
|--------|-----------------------------------------|---------------------------------|---------------|
| GET    | `/agent-registry/v1/agents`             | List all available agents       | Yes           |
| GET    | `/agent-registry/v1/agents/:id`         | Get agent details               | Yes           |
| GET    | `/agent-registry/v1/agents/:id/config`  | Get agent configuration         | Yes           |
| PUT    | `/agent-registry/v1/agents/:id/config`  | Update agent configuration      | Tenant Admin  |

### Workflow Service (`/api/workflows`)

| Method | Endpoint                                    | Description                   | Auth Required |
|--------|---------------------------------------------|-------------------------------|---------------|
| GET    | `/workflows/v1/executions`                  | List workflow executions       | Yes           |
| GET    | `/workflows/v1/executions/:id`              | Get execution details          | Yes           |
| POST   | `/workflows/v1/executions`                  | Start a new workflow execution | Yes           |
| GET    | `/workflows/v1/escalations`                 | List pending escalations       | Yes           |
| POST   | `/workflows/v1/escalations/:id/resolve`     | Resolve an escalation          | Yes           |

### AI Runtime (`/api/ai-runtime`)

| Method | Endpoint                                        | Description                  | Auth Required |
|--------|--------------------------------------------------|------------------------------|---------------|
| GET    | `/ai-runtime/v1/health`                          | Health check                 | No            |
| GET    | `/ai-runtime/v1/agents`                          | List registered agents       | Yes           |
| POST   | `/ai-runtime/v1/agents/:agentId/execute`         | Execute an agent task        | Yes           |
| GET    | `/ai-runtime/v1/agents/:agentId/status`          | Get agent status             | Yes           |
| GET    | `/ai-runtime/v1/executions/:id`                  | Get execution result         | Yes           |

### Agent Execution Request

```json
POST /api/ai-runtime/v1/agents/ai-customer-support-agent/execute

{
  "task_payload": {
    "message": "I need to return my order #12345",
    "customer_id": "cust-789",
    "channel": "web_chat"
  },
  "context": {
    "tenantId": "tenant-001",
    "sessionId": "session-abc",
    "userId": "user-456"
  }
}
```

### Agent Execution Response

```json
{
  "executionId": "exec-xyz-123",
  "agentId": "ai-customer-support-agent",
  "status": "completed",
  "output": {
    "intent": "return_request",
    "sentiment": "neutral",
    "response": "I can help you with your return for order #12345...",
    "actions_taken": ["order_lookup", "return_eligibility_check"]
  },
  "durationMs": 2340,
  "tokensUsed": 850,
  "costUsd": 0.017,
  "nextAction": null
}
```

### Integration Hub (`/api/integrations`)

| Method | Endpoint                                    | Description                    | Auth Required |
|--------|---------------------------------------------|--------------------------------|---------------|
| GET    | `/integrations/v1/connections`              | List active connections        | Yes           |
| POST   | `/integrations/v1/connections`              | Create a new connection        | Tenant Admin  |
| GET    | `/integrations/v1/connections/:id/health`   | Check connection health        | Yes           |
| DELETE | `/integrations/v1/connections/:id`          | Remove a connection            | Tenant Admin  |

### Analytics Service (`/api/analytics`)

| Method | Endpoint                                    | Description                    | Auth Required |
|--------|---------------------------------------------|--------------------------------|---------------|
| GET    | `/analytics/v1/dashboard`                   | Dashboard summary metrics      | Yes           |
| GET    | `/analytics/v1/agents/:id/performance`      | Agent performance KPIs         | Yes           |
| GET    | `/analytics/v1/usage`                       | Token usage and cost report    | Yes           |
| GET    | `/analytics/v1/audit-logs`                  | Query audit logs               | Auditor+      |

---

## WebSocket Events

The platform uses WebSocket connections for real-time updates to the tenant portal.

### Connection

```javascript
const ws = new WebSocket('wss://app.adwp.io/ws');

// Authenticate after connection
ws.send(JSON.stringify({
  type: 'auth',
  token: '<access_token>'
}));
```

### Event Types

| Event                        | Direction       | Description                                |
|------------------------------|-----------------|--------------------------------------------|
| `agent.task.started`         | Server -> Client | An agent started executing a task          |
| `agent.task.completed`       | Server -> Client | An agent finished a task                   |
| `agent.task.failed`          | Server -> Client | An agent task failed                       |
| `escalation.created`         | Server -> Client | A new escalation requires human action     |
| `escalation.sla.warning`     | Server -> Client | An escalation is approaching SLA deadline  |
| `agent.status.changed`       | Server -> Client | Agent status changed (active/idle/error)   |
| `integration.error`          | Server -> Client | An integration connector encountered error |
| `billing.budget.warning`     | Server -> Client | Tenant approaching monthly budget limit    |

### Event Payload Format

```json
{
  "type": "agent.task.completed",
  "tenantId": "tenant-001",
  "timestamp": "2025-03-15T10:30:00.000Z",
  "data": {
    "executionId": "exec-xyz-123",
    "agentId": "ai-customer-support-agent",
    "status": "completed",
    "durationMs": 2340,
    "tokensUsed": 850
  }
}
```

---

## API Versioning

APIs are versioned using URL path prefixes:

```
/api/agent-registry/v1/agents
/api/workflows/v1/executions
```

### Versioning Policy

- **v1** is the current stable version.
- Breaking changes require a new version (v2).
- Deprecated versions are supported for 6 months after the replacement is released.
- Non-breaking additions (new fields, new endpoints) do not require a version bump.
