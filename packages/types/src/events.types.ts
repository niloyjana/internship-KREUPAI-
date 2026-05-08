import { TenantStatus, TenantPlan } from './tenant.types';
import { AgentDepartment } from './agent.types';
import {
  WorkflowStatus,
  EscalationSeverity,
  EscalationStatus,
  TaskStatus,
} from './workflow.types';

// ─── Base Event Envelope ──────────────────────────────────────────────────────

export interface BaseEvent<T = unknown> {
  schemaVersion: string;
  eventId: string;
  tenantId: string;
  timestamp: string; // ISO 8601
  source: string;
  type: string;
  payload: T;
}

// ─── Event Payloads ───────────────────────────────────────────────────────────

export interface TenantProvisionedPayload {
  tenantId: string;
  name: string;
  slug: string;
  plan: TenantPlan;
  status: TenantStatus;
  ownerId: string;
  ownerEmail: string;
}

export type TenantProvisionedEvent = BaseEvent<TenantProvisionedPayload>;

export interface AgentSubscribedPayload {
  subscriptionId: string;
  tenantId: string;
  agentDefinitionId: string;
  agentName: string;
  department: AgentDepartment;
}

export type AgentSubscribedEvent = BaseEvent<AgentSubscribedPayload>;

export interface WorkflowExecutionStartedPayload {
  executionId: string;
  workflowDefinitionId: string;
  tenantId: string;
  triggerType: 'manual' | 'scheduled' | 'event' | 'webhook';
  input: Record<string, unknown>;
}

export type WorkflowExecutionStartedEvent = BaseEvent<WorkflowExecutionStartedPayload>;

export interface WorkflowExecutionCompletedPayload {
  executionId: string;
  workflowDefinitionId: string;
  tenantId: string;
  status: WorkflowStatus;
  output?: Record<string, unknown>;
  durationMs: number;
}

export type WorkflowExecutionCompletedEvent = BaseEvent<WorkflowExecutionCompletedPayload>;

export interface EscalationCreatedPayload {
  escalationId: string;
  tenantId: string;
  severity: EscalationSeverity;
  status: EscalationStatus;
  title: string;
  category: string;
  workflowExecutionId?: string;
  agentInstanceId?: string;
}

export type EscalationCreatedEvent = BaseEvent<EscalationCreatedPayload>;

export interface HumanTaskCreatedPayload {
  taskId: string;
  tenantId: string;
  workflowExecutionId: string;
  stepId: string;
  title: string;
  assigneeId?: string;
  assigneeRole?: string;
  priority: EscalationSeverity;
  dueAt?: string; // ISO 8601
}

export type HumanTaskCreatedEvent = BaseEvent<HumanTaskCreatedPayload>;

export interface HumanTaskResolvedPayload {
  taskId: string;
  tenantId: string;
  workflowExecutionId: string;
  stepId: string;
  status: TaskStatus;
  resolvedById: string;
  resolution: Record<string, unknown>;
}

export type HumanTaskResolvedEvent = BaseEvent<HumanTaskResolvedPayload>;

export interface NotificationRequestedPayload {
  notificationId: string;
  tenantId: string;
  channel: 'email' | 'in_app' | 'slack' | 'sms' | 'webhook';
  recipientId: string;
  recipientEmail?: string;
  subject: string;
  body: string;
  templateId?: string;
  templateData?: Record<string, unknown>;
  priority: 'low' | 'normal' | 'high' | 'urgent';
}

export type NotificationRequestedEvent = BaseEvent<NotificationRequestedPayload>;

export interface AuditEventRecordedPayload {
  auditEventId: string;
  tenantId: string;
  actorType: string;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  beforeJson?: unknown;
  afterJson?: unknown;
  metadata?: unknown;
  ipAddress?: string;
}

export type AuditEventRecordedEvent = BaseEvent<AuditEventRecordedPayload>;
