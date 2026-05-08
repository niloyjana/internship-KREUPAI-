import { apiClient } from './client';
import type {
  WorkflowExecution,
  ExecutionDetail,
  WorkflowStep,
  HumanTask,
  EscalationTicket,
  ResolveTaskPayload,
  ReassignTaskPayload,
  UpdateEscalationPayload,
  WorkflowStatus,
  TaskStatus,
  EscalationSeverity,
  EscalationStatus,
} from '../types/workflow.types';

/**
 * Fetch workflow executions with optional filters.
 */
export async function getExecutions(params?: {
  agentId?: string;
  status?: WorkflowStatus;
  page?: number;
  pageSize?: number;
}): Promise<WorkflowExecution[]> {
  const { data } = await apiClient.get<WorkflowExecution[]>('/v1/workflows/executions', {
    params,
  });
  return data;
}

/**
 * Fetch a single execution with full detail.
 */
export async function getExecution(executionId: string): Promise<ExecutionDetail> {
  const { data } = await apiClient.get<ExecutionDetail>(
    `/v1/workflows/executions/${executionId}`,
  );
  return data;
}

/**
 * Fetch steps for a specific execution.
 */
export async function getExecutionSteps(executionId: string): Promise<WorkflowStep[]> {
  const { data } = await apiClient.get<WorkflowStep[]>(
    `/v1/workflows/executions/${executionId}/steps`,
  );
  return data;
}

/**
 * Cancel a running or pending execution.
 */
export async function cancelExecution(executionId: string): Promise<void> {
  await apiClient.post(`/v1/workflows/executions/${executionId}/cancel`);
}

/**
 * Fetch human tasks with optional filters.
 */
export async function getHumanTasks(params?: {
  status?: TaskStatus;
  agentId?: string;
  page?: number;
  pageSize?: number;
}): Promise<HumanTask[]> {
  const { data } = await apiClient.get<HumanTask[]>('/v1/workflows/human-tasks', {
    params,
  });
  return data;
}

/**
 * Fetch a single human task by ID.
 */
export async function getHumanTask(taskId: string): Promise<HumanTask> {
  const { data } = await apiClient.get<HumanTask>(`/v1/workflows/human-tasks/${taskId}`);
  return data;
}

/**
 * Resolve a human task with a decision.
 */
export async function resolveHumanTask(
  taskId: string,
  payload: ResolveTaskPayload,
): Promise<void> {
  await apiClient.post(`/v1/workflows/human-tasks/${taskId}/resolve`, payload);
}

/**
 * Reassign a human task to a different user or team.
 */
export async function reassignHumanTask(
  taskId: string,
  payload: ReassignTaskPayload,
): Promise<HumanTask> {
  const { data } = await apiClient.patch<HumanTask>(
    `/v1/workflows/human-tasks/${taskId}`,
    payload,
  );
  return data;
}

/**
 * Fetch escalation tickets with optional filters.
 */
export async function getEscalations(params?: {
  severity?: EscalationSeverity;
  status?: EscalationStatus;
  agentId?: string;
  page?: number;
  pageSize?: number;
}): Promise<EscalationTicket[]> {
  const { data } = await apiClient.get<EscalationTicket[]>('/v1/workflows/escalations', {
    params,
  });
  return data;
}

/**
 * Fetch a single escalation ticket by ID.
 */
export async function getEscalation(escalationId: string): Promise<EscalationTicket> {
  const { data } = await apiClient.get<EscalationTicket>(
    `/v1/workflows/escalations/${escalationId}`,
  );
  return data;
}

/**
 * Update an escalation ticket (assign, change status, add resolution note).
 */
export async function updateEscalation(
  escalationId: string,
  payload: UpdateEscalationPayload,
): Promise<EscalationTicket> {
  const { data } = await apiClient.patch<EscalationTicket>(
    `/v1/workflows/escalations/${escalationId}`,
    payload,
  );
  return data;
}
