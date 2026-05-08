// ─── Enums ────────────────────────────────────────────────────────────────────

export enum WorkflowStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum StepType {
  AI_TASK = 'ai_task',
  HUMAN_REVIEW = 'human_review',
  CONDITIONAL = 'conditional',
  PARALLEL = 'parallel',
  INTEGRATION = 'integration',
  NOTIFICATION = 'notification',
  DELAY = 'delay',
}

export enum StepStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  WAITING_FOR_HUMAN = 'waiting_for_human',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

export enum TaskStatus {
  PENDING = 'pending',
  ASSIGNED = 'assigned',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  REJECTED = 'rejected',
  EXPIRED = 'expired',
}

export enum EscalationSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum EscalationStatus {
  OPEN = 'open',
  ACKNOWLEDGED = 'acknowledged',
  IN_PROGRESS = 'in_progress',
  RESOLVED = 'resolved',
  CLOSED = 'closed',
}

// ─── Interfaces ───────────────────────────────────────────────────────────────

export interface WorkflowDefinition {
  id: string;
  tenantId: string;
  agentDefinitionId: string;
  name: string;
  description: string;
  version: string;
  steps: WorkflowStep[];
  triggerType: 'manual' | 'scheduled' | 'event' | 'webhook';
  triggerConfig: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

export interface WorkflowExecution {
  id: string;
  tenantId: string;
  workflowDefinitionId: string;
  status: WorkflowStatus;
  currentStepIndex: number;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  startedAt: Date;
  completedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface WorkflowStep {
  id: string;
  name: string;
  type: StepType;
  status: StepStatus;
  config: Record<string, unknown>;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  retryCount: number;
  maxRetries: number;
  timeoutMs?: number;
  startedAt?: Date;
  completedAt?: Date;
}

export interface HumanTask {
  id: string;
  tenantId: string;
  workflowExecutionId: string;
  stepId: string;
  title: string;
  description: string;
  status: TaskStatus;
  assigneeId?: string;
  assigneeRole?: string;
  priority: EscalationSeverity;
  dueAt?: Date;
  context: Record<string, unknown>;
  resolution?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

export interface EscalationTicket {
  id: string;
  tenantId: string;
  workflowExecutionId?: string;
  agentInstanceId?: string;
  severity: EscalationSeverity;
  status: EscalationStatus;
  title: string;
  description: string;
  assigneeId?: string;
  category: string;
  slaDeadline?: Date;
  slaBreached: boolean;
  context: Record<string, unknown>;
  resolution?: string;
  resolvedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}
