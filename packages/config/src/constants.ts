export const PLATFORM = {
  NAME: 'AI Digital Workforce Platform',
  VERSION: '1.0.0',
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  JWT_ACCESS_EXPIRY_DEFAULT: '15m',
  JWT_REFRESH_EXPIRY_DEFAULT: '7d',
} as const;

export const RETRY = {
  MAX_RETRIES: 3,
  BASE_DELAY_MS: 1000,
  MAX_DELAY_MS: 30000,
} as const;

export const CIRCUIT_BREAKER = {
  FAILURE_THRESHOLD: 5,
  RESET_TIMEOUT_MS: 30000,
} as const;

export const KAFKA_TOPICS = {
  TENANT_PROVISIONED: 'tenant.provisioned',
  TENANT_STATUS_CHANGED: 'tenant.status.changed',
  TENANT_CONFIG_UPDATED: 'tenant.config.updated',
  AGENT_SUBSCRIBED: 'agent.subscribed',
  AGENT_ACTIVATED: 'agent.activated',
  AGENT_STATUS_CHANGED: 'agent.status.changed',
  WORKFLOW_EXECUTION_STARTED: 'workflow.execution.started',
  WORKFLOW_STEP_COMPLETED: 'workflow.step.completed',
  WORKFLOW_EXECUTION_COMPLETED: 'workflow.execution.completed',
  WORKFLOW_EXECUTION_FAILED: 'workflow.execution.failed',
  ESCALATION_CREATED: 'escalation.created',
  ESCALATION_SLA_BREACHED: 'escalation.sla.breached',
  HUMAN_TASK_CREATED: 'human.task.created',
  HUMAN_TASK_RESOLVED: 'human.task.resolved',
  INTEGRATION_CONNECTED: 'integration.connected',
  INTEGRATION_CONNECTION_FAILED: 'integration.connection.failed',
  BILLING_SUBSCRIPTION_ACTIVATED: 'billing.subscription.activated',
  BILLING_PAYMENT_FAILED: 'billing.payment.failed',
  BILLING_USAGE_RECORDED: 'billing.usage.recorded',
  AGENT_COLLABORATION_REQUESTED: 'agent.collaboration.requested',
  NOTIFICATION_REQUESTED: 'notification.requested',
  NOTIFICATION_DELIVERED: 'notification.delivered',
  AUDIT_EVENT_RECORDED: 'audit.event.recorded',
} as const;

export const SERVICE_PORTS = {
  AUTH: 3001,
  TENANT: 3002,
  AGENT_REGISTRY: 3003,
  WORKFLOW: 3004,
  SUBSCRIPTION: 3005,
  INTEGRATION_HUB: 3006,
  ANALYTICS: 3007,
  NOTIFICATION: 3008,
  AI_RUNTIME: 8000,
  PORTAL: 3000,
} as const;
