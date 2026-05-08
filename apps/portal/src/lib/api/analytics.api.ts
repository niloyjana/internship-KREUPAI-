import { apiClient } from './client';
import type {
  DashboardData,
  AgentPerformance,
  CostBreakdown,
  AuditLogEntry,
} from '../types/analytics.types';
import type { WorkflowExecution } from '../types/workflow.types';

/**
 * Fetch the main dashboard summary data.
 */
export async function getDashboard(): Promise<DashboardData> {
  const { data } = await apiClient.get<DashboardData>('/v1/analytics/dashboard');
  return data;
}

/**
 * Fetch performance data for a specific agent.
 */
export async function getAgentPerformance(
  agentId: string,
  params?: {
    from?: string;
    to?: string;
  },
): Promise<AgentPerformance> {
  const { data } = await apiClient.get<AgentPerformance>(
    `/v1/analytics/agents/${agentId}/performance`,
    { params },
  );
  return data;
}

/**
 * Fetch task executions for a specific agent.
 */
export async function getAgentTasks(
  agentId: string,
  params?: {
    from?: string;
    to?: string;
    page?: number;
    pageSize?: number;
  },
): Promise<WorkflowExecution[]> {
  const { data } = await apiClient.get<WorkflowExecution[]>(
    `/v1/analytics/agents/${agentId}/tasks`,
    { params },
  );
  return data;
}

/**
 * Fetch escalation trend data.
 */
export async function getEscalationTrends(params?: {
  from?: string;
  to?: string;
  agentId?: string;
}): Promise<any> {
  const { data } = await apiClient.get('/v1/analytics/escalations', { params });
  return data;
}

/**
 * Fetch cost breakdown data.
 */
export async function getCostBreakdown(params?: {
  groupBy?: 'agent' | 'model';
  period?: 'daily' | 'weekly' | 'monthly';
  from?: string;
  to?: string;
}): Promise<CostBreakdown> {
  const { data } = await apiClient.get<CostBreakdown>('/v1/analytics/cost', { params });
  return data;
}

/**
 * Fetch audit log entries.
 */
export async function getAuditLog(params?: {
  from?: string;
  to?: string;
  actorType?: 'USER' | 'AI_AGENT' | 'SYSTEM';
  entityType?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ entries: AuditLogEntry[]; meta: { page: number; pageSize: number; totalItems: number; totalPages: number } }> {
  const { data } = await apiClient.get<{ entries: AuditLogEntry[]; meta: { page: number; pageSize: number; totalItems: number; totalPages: number } }>(
    '/v1/analytics/audit',
    { params },
  );
  return data;
}
