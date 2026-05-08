import { apiClient } from './client';
import type {
  AgentExecuteRequest,
  AgentExecuteResponse,
  AgentRuntimeStatus,
  RuntimeHealthResponse,
  EscalationRequest,
  EscalationResponse,
} from '../types/runtime.types';

/**
 * Execute a task on a specific AI agent via the runtime engine.
 */
export async function executeAgent(
  params: Omit<AgentExecuteRequest, 'executionId' | 'stepId'> & {
    executionId?: string;
    stepId?: string;
  },
): Promise<AgentExecuteResponse> {
  const request: AgentExecuteRequest = {
    executionId:
      params.executionId || `exec-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    stepId: params.stepId || 'step-1',
    tenantId: params.tenantId,
    agentId: params.agentId,
    taskPayload: params.taskPayload,
    contextJson: params.contextJson,
    tenantConfig: params.tenantConfig,
    agentPolicy: params.agentPolicy,
  };

  try {
    const { data } = await apiClient.post<AgentExecuteResponse>(
      '/v1/runtime/agent/execute',
      request,
      { timeout: 130_000 },
    );
    return data;
  } catch (error) {
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosErr = error as { response?: { status: number; data?: unknown } };
      const status = axiosErr.response?.status;
      const detail =
        axiosErr.response?.data && typeof axiosErr.response.data === 'object'
          ? JSON.stringify(axiosErr.response.data)
          : '';
      throw new Error(`Agent execution failed (HTTP ${status})${detail ? `: ${detail}` : ''}`);
    }
    throw error;
  }
}

/**
 * Get the registration status and capabilities of an agent.
 */
export async function getAgentRuntimeStatus(agentId: string): Promise<AgentRuntimeStatus> {
  try {
    const { data } = await apiClient.get<AgentRuntimeStatus>(
      `/v1/runtime/agent/${agentId}/status`,
      { timeout: 10_000 },
    );
    return data;
  } catch (error) {
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosErr = error as { response?: { status: number } };
      if (axiosErr.response?.status === 404) {
        throw new Error(`Agent '${agentId}' not registered in runtime`);
      }
    }
    throw error;
  }
}

/**
 * Check AI runtime health (agent count, persistence status).
 */
export async function getRuntimeHealth(): Promise<RuntimeHealthResponse> {
  const { data } = await apiClient.get<RuntimeHealthResponse>('/v1/runtime/health', {
    timeout: 5_000,
  });
  return data;
}

/**
 * Escalate an agent execution to human review.
 */
export async function escalateExecution(params: EscalationRequest): Promise<EscalationResponse> {
  const { data } = await apiClient.post<EscalationResponse>('/v1/runtime/agent/escalate', params, {
    timeout: 10_000,
  });
  return data;
}
