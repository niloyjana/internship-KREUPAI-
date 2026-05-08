# API Overview

This document provides a comprehensive overview of the ADWP platform APIs, including base URLs, authentication, response formats, error handling, pagination, rate limiting, and WebSocket events.

---

## Table of Contents

1. [Base URLs](#base-urls)
2. [Authentication](#authentication)
3. [Standard Response Format](#standard-response-format)
4. [Pagination](#pagination)
5. [Error Codes Reference](#error-codes-reference)
6. [Rate Limiting](#rate-limiting)
7. [Versioning](#versioning)
8. [WebSocket Events Reference](#websocket-events-reference)

---

## Base URLs

All services are accessible via the API gateway. In production, services are routed through a single domain with path-based routing. In local development, each service runs on its own port.

| Service                | Local Development URL                | Production URL                              |
|------------------------|--------------------------------------|---------------------------------------------|
| Auth Service           | `http://localhost:3010`              | `https://app.adwp.io/api/auth`              |
| Tenant Service         | `http://localhost:3011`              | `https://app.adwp.io/api/tenants`           |
| Subscription Service   | `http://localhost:3012`              | `https://app.adwp.io/api/subscriptions`     |
| Agent Registry         | `http://localhost:3013`              | `https://app.adwp.io/api/agent-registry`    |
| Workflow Service       | `http://localhost:3014`              | `https://app.adwp.io/api/workflows`         |
| Integration Hub        | `http://localhost:3015`              | `https://app.adwp.io/api/integrations`      |
| Notification Service   | `http://localhost:3016`              | `https://app.adwp.io/api/notifications`     |
| Analytics Service      | `http://localhost:3017`              | `https://app.adwp.io/api/analytics`         |
| AI Runtime             | `http://localhost:8000`              | `https://app.adwp.io/api/ai-runtime`        |

---

## Authentication

The ADWP platform supports two authentication methods: JWT Bearer tokens and API keys.

### JWT Bearer Token

Used by frontend applications and user-facing integrations.

**Obtain a token:**

```bash
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@company.com",
  "password": "secure_password"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 900,
    "tokenType": "Bearer"
  }
}
```

**Use the token in subsequent requests:**

```bash
GET /v1/agents
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Token claims:**

```json
{
  "sub": "user_cuid",
  "email": "user@company.com",
  "tenantId": "tenant_cuid",
  "role": "TENANT_ADMIN",
  "iat": 1709312400,
  "exp": 1709313300
}
```

**Refresh a token:**

```bash
POST /v1/auth/refresh
Content-Type: application/json

{
  "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Token expiry:**

| Token Type     | Default Expiry |
|----------------|----------------|
| Access token   | 15 minutes     |
| Refresh token  | 7 days         |

### API Keys

Used by server-to-server integrations and third-party applications.

**Create an API key:**

```bash
POST /v1/auth/api-keys
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Production Integration",
  "expiresAt": "2026-12-31T23:59:59Z"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "key_cuid",
    "name": "Production Integration",
    "key": "adwp_live_sk_abc123...",
    "expiresAt": "2026-12-31T23:59:59.000Z"
  }
}
```

**Use the API key:**

```bash
GET /v1/agents
X-API-Key: adwp_live_sk_abc123...
```

**Important:** The API key value is only returned once upon creation. Store it securely. The key hash is stored in the database; the original key cannot be retrieved.

---

## Standard Response Format

All API responses follow a consistent JSON structure.

### Success Response

```json
{
  "success": true,
  "data": {
    "id": "cuid_value",
    "name": "Example Resource",
    "createdAt": "2025-03-01T12:00:00.000Z"
  }
}
```

### Success Response (List)

```json
{
  "success": true,
  "data": [
    { "id": "cuid_1", "name": "Resource 1" },
    { "id": "cuid_2", "name": "Resource 2" }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 42,
    "totalPages": 3
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Agent with ID 'invalid-id' not found.",
    "traceId": "trace_abc123def456"
  }
}
```

### Validation Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "traceId": "trace_abc123def456",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      },
      {
        "field": "name",
        "message": "Must be at least 2 characters"
      }
    ]
  }
}
```

---

## Pagination

List endpoints support cursor-based pagination using `page` and `pageSize` parameters.

### Request Parameters

| Parameter   | Type    | Default | Max  | Description                  |
|-------------|---------|---------|------|------------------------------|
| `page`      | integer | 1       | --   | Page number (1-indexed)      |
| `pageSize`  | integer | 20      | 100  | Number of items per page     |
| `sortBy`    | string  | varies  | --   | Field to sort by             |
| `sortOrder` | string  | `desc`  | --   | Sort order (`asc` or `desc`) |

### Example

```bash
GET /v1/agents?page=2&pageSize=10&sortBy=createdAt&sortOrder=desc
```

### Response

```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 2,
    "pageSize": 10,
    "total": 25,
    "totalPages": 3
  }
}
```

### Pagination Headers

The following HTTP headers are also included in paginated responses:

| Header               | Description                          |
|----------------------|--------------------------------------|
| `X-Total-Count`      | Total number of matching records     |
| `X-Total-Pages`      | Total number of pages                |
| `X-Current-Page`     | Current page number                  |
| `X-Page-Size`        | Number of items per page             |

---

## Error Codes Reference

### HTTP Status Codes

| Status Code | Meaning                                              |
|-------------|------------------------------------------------------|
| `200`       | Success                                              |
| `201`       | Created                                              |
| `204`       | No Content (successful delete)                       |
| `400`       | Bad Request (validation error, malformed input)      |
| `401`       | Unauthorized (missing or invalid authentication)     |
| `403`       | Forbidden (insufficient permissions)                 |
| `404`       | Not Found (resource does not exist)                  |
| `409`       | Conflict (duplicate resource, concurrent update)     |
| `422`       | Unprocessable Entity (semantic validation failure)   |
| `429`       | Too Many Requests (rate limit exceeded)              |
| `500`       | Internal Server Error                                |
| `502`       | Bad Gateway (upstream service unavailable)           |
| `503`       | Service Unavailable (maintenance, overloaded)        |

### Application Error Codes

| Error Code                    | HTTP Status | Description                                           |
|-------------------------------|-------------|-------------------------------------------------------|
| `VALIDATION_ERROR`            | 400         | Request body failed validation                        |
| `INVALID_CREDENTIALS`        | 401         | Email or password is incorrect                        |
| `TOKEN_EXPIRED`               | 401         | JWT access token has expired                          |
| `TOKEN_INVALID`               | 401         | JWT token is malformed or tampered                    |
| `API_KEY_INVALID`             | 401         | API key not found or revoked                          |
| `API_KEY_EXPIRED`             | 401         | API key has passed its expiry date                    |
| `INSUFFICIENT_PERMISSIONS`    | 403         | User role does not allow this action                  |
| `TENANT_SUSPENDED`            | 403         | Tenant account is suspended                           |
| `RESOURCE_NOT_FOUND`          | 404         | Requested resource does not exist                     |
| `AGENT_NOT_FOUND`             | 404         | Agent ID not registered in the runtime                |
| `WORKFLOW_NOT_FOUND`          | 404         | Workflow definition or execution not found            |
| `DUPLICATE_RESOURCE`          | 409         | Resource with same unique key already exists          |
| `SUBSCRIPTION_REQUIRED`       | 403         | Tenant does not have an active subscription for agent |
| `SUBSCRIPTION_EXPIRED`        | 403         | Agent subscription has expired                        |
| `AGENT_EXECUTION_FAILED`      | 500         | Agent execution encountered an unrecoverable error    |
| `LLM_PROVIDER_ERROR`          | 502         | LLM provider returned an error                       |
| `LLM_RATE_LIMITED`            | 429         | LLM provider rate limit exceeded                     |
| `INTEGRATION_ERROR`           | 502         | Third-party integration returned an error            |
| `INTEGRATION_AUTH_EXPIRED`    | 401         | Integration OAuth token has expired                  |
| `RATE_LIMIT_EXCEEDED`         | 429         | Request rate limit exceeded                          |
| `INTERNAL_ERROR`              | 500         | Unexpected server error                               |

### Error Response Examples

**Authentication failure:**

```json
{
  "success": false,
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "Your access token has expired. Please refresh or re-authenticate.",
    "traceId": "trace_789xyz"
  }
}
```

**Rate limiting:**

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "traceId": "trace_456def"
  }
}
```

**Agent execution failure:**

```json
{
  "success": false,
  "error": {
    "code": "AGENT_EXECUTION_FAILED",
    "message": "Agent 'ai-customer-support-agent' failed to execute the task.",
    "traceId": "trace_exec_001",
    "details": {
      "agentId": "ai-customer-support-agent",
      "executionId": "exec_abc123",
      "errorType": "LLMProviderError",
      "durationMs": 5230
    }
  }
}
```

---

## Rate Limiting

API requests are rate-limited per tenant to ensure fair usage and platform stability.

### Default Rate Limits

| Endpoint Category        | Rate Limit           | Window    |
|--------------------------|----------------------|-----------|
| Authentication           | 10 requests          | 1 minute  |
| Agent execution          | 60 requests          | 1 minute  |
| Read operations (GET)    | 300 requests         | 1 minute  |
| Write operations (POST/PUT/DELETE) | 120 requests | 1 minute  |
| Bulk operations          | 10 requests          | 1 minute  |
| Webhook delivery         | 1000 requests        | 1 minute  |

### Rate Limit Headers

Every response includes rate limit information:

| Header                   | Description                              |
|--------------------------|------------------------------------------|
| `X-RateLimit-Limit`      | Maximum requests allowed in the window   |
| `X-RateLimit-Remaining`  | Remaining requests in the current window |
| `X-RateLimit-Reset`      | Unix timestamp when the window resets    |
| `Retry-After`            | Seconds until rate limit resets (on 429) |

### Example Headers

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 247
X-RateLimit-Reset: 1709313300
```

### Handling Rate Limits

When you receive a `429 Too Many Requests` response:

1. Read the `Retry-After` header.
2. Wait the specified number of seconds.
3. Retry the request.
4. Implement exponential backoff for repeated 429s.

```python
import time
import requests

def api_call_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 30))
            time.sleep(retry_after)
            continue
        return response
    raise Exception("Rate limit exceeded after max retries")
```

---

## Versioning

All API endpoints are versioned using a URL prefix.

### Current Version

```
/v1/
```

All endpoints use the `v1` prefix:

```
GET  /v1/agents
POST /v1/agents/ai-customer-support-agent/execute
GET  /v1/workflows/executions
GET  /v1/health
```

### Version Lifecycle

| Phase        | Duration      | Behavior                                             |
|--------------|---------------|------------------------------------------------------|
| Active       | Current       | Fully supported, receives new features               |
| Deprecated   | 6 months      | Works but returns `Deprecation` header               |
| Sunset       | After 6 months| Returns `410 Gone` with migration guidance           |

### Deprecation Header

When a version or endpoint is deprecated:

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: 2026-06-01T00:00:00Z
Link: <https://docs.adwp.io/migration/v1-to-v2>; rel="successor-version"
```

---

## WebSocket Events Reference

The platform provides real-time updates via WebSocket connections for tenant-specific events.

### Connection

```javascript
const ws = new WebSocket('wss://app.adwp.io/ws');

// Authenticate after connection
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: '<jwt_access_token>',
  }));
};

// Listen for events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.payload);
};
```

### Event Types

All WebSocket events follow a consistent structure:

```json
{
  "type": "<event_type>",
  "tenantId": "tenant_cuid",
  "timestamp": "2025-03-01T12:00:00.000Z",
  "payload": { ... }
}
```

### Workflow Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `task.started`                  | Agent begins executing a task            | `executionId`, `agentId`, `definitionId`, `triggerSource`          |
| `task.step.completed`           | A workflow step finishes                 | `executionId`, `stepKey`, `stepType`, `status`, `durationMs`      |
| `task.completed`                | Agent completes task successfully        | `executionId`, `agentId`, `status`, `durationMs`, `tokensUsed`, `costUsd` |
| `task.failed`                   | Agent task fails                         | `executionId`, `agentId`, `error`, `errorType`, `durationMs`      |

### Escalation Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `escalation.created`            | Agent escalates to human review          | `escalationId`, `agentId`, `reason`, `severity`, `assignedToId`   |
| `escalation.sla.breached`       | Escalation SLA deadline passes           | `escalationId`, `agentId`, `severity`, `slaDeadlineAt`            |
| `escalation.resolved`           | Human resolves an escalation             | `escalationId`, `resolvedById`, `resolutionNote`                  |

### Human Task Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `human.task.created`            | Workflow creates a human review task     | `taskId`, `executionId`, `title`, `assignedToId`, `priority`      |
| `human.task.assigned`           | Task is assigned to a user               | `taskId`, `assignedToId`, `assignedTeam`                          |
| `human.task.resolved`           | Human completes the review task          | `taskId`, `decision`, `completedById`                             |

### Agent Status Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `agent.status.changed`          | Agent status transitions                 | `agentId`, `previousStatus`, `newStatus`, `instanceId`            |
| `agent.subscribed`              | Tenant subscribes to a new agent         | `agentId`, `tenantId`, `subscriptionId`                           |

### Integration Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `integration.connected`         | Integration successfully connected       | `connectionId`, `provider`, `status`                              |
| `integration.error`             | Integration connection fails             | `connectionId`, `provider`, `errorMessage`                        |
| `integration.token.refreshed`   | OAuth token refreshed                    | `connectionId`, `provider`, `expiresAt`                           |

### Billing Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `billing.payment.succeeded`     | Payment processed successfully           | `invoiceId`, `amountUsd`, `currency`                              |
| `billing.payment.failed`        | Payment attempt failed                   | `invoiceId`, `amountUsd`, `failureReason`                         |
| `billing.usage.updated`         | Usage metrics updated                    | `agentId`, `taskCount`, `tokenCount`, `costUsd`, `period`         |

### Notification Events

| Event Type                      | Trigger                                  | Payload Fields                                                    |
|---------------------------------|------------------------------------------|-------------------------------------------------------------------|
| `notification.sent`             | Notification delivered                   | `notificationId`, `channel`, `eventType`, `status`                |
| `notification.failed`           | Notification delivery failed             | `notificationId`, `channel`, `errorMsg`                           |

### Subscribing to Specific Events

After authentication, you can subscribe to specific event types:

```javascript
// Subscribe to specific events
ws.send(JSON.stringify({
  type: 'subscribe',
  events: ['task.completed', 'escalation.created', 'task.failed'],
}));

// Unsubscribe
ws.send(JSON.stringify({
  type: 'unsubscribe',
  events: ['task.failed'],
}));
```

### Heartbeat / Keep-Alive

The server sends periodic ping messages. The client should respond with pong to maintain the connection:

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong' }));
    return;
  }
  // Handle other events...
};
```

Connection timeout occurs after 60 seconds of no activity if the client does not respond to pings.
