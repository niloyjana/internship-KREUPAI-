import { apiClient } from './client';
import type {
  AgentFullConfig,
  AgentConfigHistoryEntry,
  UpdateAgentFullConfigPayload,
} from '../types/agent.types';

/**
 * Fetch the full configuration for an agent.
 */
export async function getAgentConfig(agentId: string): Promise<AgentFullConfig> {
  const { data } = await apiClient.get<AgentFullConfig>(`/v1/agents/${agentId}/config`);
  return data;
}

/**
 * Update an agent's configuration (supports partial updates).
 */
export async function updateAgentFullConfig(
  agentId: string,
  config: UpdateAgentFullConfigPayload,
): Promise<AgentFullConfig> {
  const { data } = await apiClient.put<AgentFullConfig>(`/v1/agents/${agentId}/config`, config);
  return data;
}

/**
 * Fetch config change history for an agent.
 */
export async function getAgentConfigHistory(
  agentId: string,
  params?: { page?: number; pageSize?: number },
): Promise<{
  entries: AgentConfigHistoryEntry[];
  meta: { page: number; pageSize: number; totalItems: number; totalPages: number };
}> {
  const { data } = await apiClient.get<{
    entries: AgentConfigHistoryEntry[];
    meta: { page: number; pageSize: number; totalItems: number; totalPages: number };
  }>(`/v1/agents/${agentId}/config/history`, { params });
  return data;
}
