/**
 * Types for the AI Runtime API (FastAPI service on port 8000).
 */

export interface AgentExecuteRequest {
  executionId: string;
  tenantId: string;
  agentId: string;
  stepId: string;
  taskPayload: Record<string, unknown>;
  contextJson?: Record<string, unknown>;
  tenantConfig?: Record<string, unknown>;
  agentPolicy?: Record<string, unknown>;
}

export interface AgentExecuteResponse {
  executionId: string;
  stepId: string;
  status: 'completed' | 'failed' | 'escalated';
  output: Record<string, unknown>;
  durationMs: number;
  tokenUsed: number | null;
  costUsd: number | null;
  nextAction: string | null;
}

export interface AgentRuntimeStatus {
  agentId: string;
  registered: boolean;
  capabilities: string[];
  status: string;
}

export interface RuntimeHealthResponse {
  status: string;
  service: string;
  timestamp: string;
  agentsLoaded: number;
  persistence: {
    postgres: boolean;
    redis: boolean;
  };
}

export interface EscalationRequest {
  executionId: string;
  stepId: string;
  tenantId: string;
  agentId: string;
  reason: string;
  output?: Record<string, unknown>;
}

export interface EscalationResponse {
  executionId: string;
  stepId: string;
  status: string;
  escalationId: string;
  message: string;
}
