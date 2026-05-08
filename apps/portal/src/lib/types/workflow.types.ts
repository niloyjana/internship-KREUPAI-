/**
 * Types for workflow executions, human tasks, and escalations.
 */

export type WorkflowStatus = 'PENDING' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type StepType = 'AI_TASK' | 'HUMAN_REVIEW' | 'INTEGRATION_CALL' | 'CONDITIONAL' | 'NOTIFICATION';
export type StepStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';
export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'REJECTED' | 'EXPIRED';
export type EscalationSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type EscalationStatus = 'OPEN' | 'IN_REVIEW' | 'RESOLVED' | 'ESCALATED_FURTHER';

export interface WorkflowExecution {
  id: string;
  agentId: string;
  status: WorkflowStatus;
  triggerSource: string | null;
  currentStep: string | null;
  startedAt: string | null;
  durationMs: number | null;
  stepCount: number;
  completedSteps: number;
  createdAt: string;
}

export interface WorkflowStep {
  id: string;
  stepKey: string;
  stepType: StepType;
  status: StepStatus;
  sequence: number;
  inputJson: any;
  outputJson: any;
  toolCalled: string | null;
  durationMs: number | null;
  retryCount: number;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
}

export interface ExecutionDetail extends WorkflowExecution {
  definitionId: string;
  triggerPayload: any;
  contextJson: any;
  completedAt: string | null;
  failedAt: string | null;
  failureReason: string | null;
  tokenUsed: number | null;
  llmCostUsd: number | null;
  steps: WorkflowStep[];
}

export interface HumanTask {
  id: string;
  executionId: string;
  title: string;
  description: string | null;
  contextJson: any;
  assignedToId: string | null;
  assignedTeam: string | null;
  status: TaskStatus;
  priority: string;
  dueAt: string | null;
  completedAt: string | null;
  decision: string | null;
  decisionNote: string | null;
  createdAt: string;
  // Joined from execution
  agentId?: string;
}

export interface EscalationTicket {
  id: string;
  executionId: string | null;
  agentId: string;
  reason: string;
  severity: EscalationSeverity;
  status: EscalationStatus;
  contextJson: any;
  recommendedAction: string | null;
  assignedToId: string | null;
  resolvedAt: string | null;
  resolutionNote: string | null;
  slaDeadlineAt: string | null;
  slaBreachedAt: string | null;
  createdAt: string;
}

export interface ResolveTaskPayload {
  decision: 'approve' | 'reject' | 'modify';
  decisionNote?: string;
  modifiedPayload?: any;
}

export interface ReassignTaskPayload {
  assignedTo: string;
  reassignReason?: string;
}

export interface UpdateEscalationPayload {
  assignedToUserId?: string;
  status?: EscalationStatus;
  resolutionNote?: string;
}
