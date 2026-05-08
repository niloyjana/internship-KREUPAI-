export interface AgentSubscribedPayload {
  subscriptionId: string;
  tenantId: string;
  agentId: string;
  agentName: string;
  department: string;
  plan: string;
  monthlyPriceUsd: number;
  startedAt: string;
}

export interface AgentActivatedPayload {
  tenantId: string;
  agentId: string;
  agentConfigId: string;
  integrationIds: string[];
  policyVersion: number;
}

export interface AgentStatusChangedPayload {
  tenantId: string;
  agentId: string;
  instanceId: string;
  previousStatus: string;
  newStatus: string;
  currentTaskId: string | null;
}

export interface AgentCollaborationRequestedPayload {
  requestingAgentId: string;
  targetAgentId: string;
  executionId: string;
  collaborationType: 'delegate' | 'notify' | 'request_data' | 'trigger_workflow' | string;
  taskContext: Record<string, unknown>;
  priority: 'urgent' | 'normal' | 'low';
  callbackTopic: string | null;
}
