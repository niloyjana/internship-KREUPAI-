export interface WorkflowExecutionStartedPayload {
  executionId: string;
  definitionId: string;
  agentId: string;
  triggerSource: string;
  triggerPayload: Record<string, unknown> | null;
  estimatedSteps: number;
}

export interface WorkflowStepCompletedPayload {
  executionId: string;
  stepId: string;
  stepKey: string;
  stepType: string;
  status: 'COMPLETED' | 'FAILED' | 'SKIPPED';
  durationMs: number;
  tokenUsed: number | null;
  outputSummary: string | null;
}

export interface WorkflowExecutionCompletedPayload {
  executionId: string;
  agentId: string;
  status: 'COMPLETED' | 'FAILED' | 'CANCELLED';
  durationMs: number;
  stepCount: number;
  tokenUsed: number;
  costUsd: number;
  escalationTriggered: boolean;
  outcome: string | null;
}

export interface WorkflowExecutionFailedPayload {
  executionId: string;
  agentId: string;
  failedAtStepId: string;
  failureReason: string;
  isRetryable: boolean;
  retryAttempt: number;
  alertOpsTeam: boolean;
}
