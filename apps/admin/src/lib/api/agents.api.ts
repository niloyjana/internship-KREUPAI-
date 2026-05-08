import { apiClient } from './client';

export interface AgentDefinition {
  id: string;
  name: string;
  department: string;
  description: string;
  version: string;
  capabilities: string[];
  pricing: AgentPricing;
  configSchema: Record<string, any>;
  subscriptionCount: number;
  status: 'active' | 'deprecated' | 'draft';
  createdAt: string;
  updatedAt: string;
}

export interface AgentPricing {
  monthlyBase: number;
  perTaskFee: number;
  currency: string;
}

export interface AgentsParams {
  department?: string;
  status?: string;
  search?: string;
}

export async function getAgentDefinitions(params?: AgentsParams): Promise<AgentDefinition[]> {
  const response = await apiClient.get('/admin/agents', { params });
  return response.data;
}

export async function getAgentDefinition(agentId: string): Promise<AgentDefinition> {
  const response = await apiClient.get(`/admin/agents/${agentId}`);
  return response.data;
}
