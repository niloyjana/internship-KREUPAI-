export interface EscalationCreatedPayload {
  escalationId: string;
  executionId: string | null;
  agentId: string;
  severity: string;
  reason: string;
  recommendedAction: string | null;
  slaDeadlineAt: string;
  assignedToUserId: string | null;
  assignedTeam: string | null;
  contextSummary: string;
}

export interface EscalationSlaBreachedPayload {
  escalationId: string;
  agentId: string;
  severity: string;
  slaDeadlineAt: string;
  minutesOverdue: number;
  escalateToUserId: string | null;
}

export interface HumanTaskCreatedPayload {
  taskId: string;
  executionId: string;
  stepId: string;
  title: string;
  priority: string;
  assignedToUserId: string | null;
  assignedTeam: string | null;
  dueAt: string;
}

export interface HumanTaskResolvedPayload {
  taskId: string;
  executionId: string;
  stepId: string;
  decision: 'approve' | 'reject' | 'reassign' | 'modify' | string;
  decisionNote: string | null;
  resolvedByUserId: string;
  durationToResolveMs: number;
  slaBreached: boolean;
}
