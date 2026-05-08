/**
 * Types for AI agent definitions and configuration.
 */

export type AgentDepartment =
  | 'finance'
  | 'hr'
  | 'sales'
  | 'marketing'
  | 'operations'
  | 'engineering'
  | 'legal'
  | 'support';

export type AgentStatus = 'active' | 'paused' | 'pending' | 'error';

export interface AgentCapability {
  id: string;
  name: string;
  description: string;
}

export interface AgentIntegration {
  id: string;
  name: string;
  type: string;
  required: boolean;
  connected: boolean;
}

export interface AgentPricing {
  monthlyFeeUsd: number;
  perTaskFeeUsd: number;
  includedTasksPerMonth: number;
}

export interface AgentDefinition {
  id: string;
  name: string;
  department: AgentDepartment;
  description: string;
  shortDescription: string;
  version: string;
  capabilities: AgentCapability[];
  requiredIntegrations: AgentIntegration[];
  pricing: AgentPricing;
  iconUrl?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AgentConfig {
  agentId: string;
  displayName: string;
  policyJson: string;
  isEnabled: boolean;
  updatedAt: string;
}

export interface SubscribedAgent {
  id: string;
  agentId: string;
  agent: AgentDefinition;
  config: AgentConfig;
  status: AgentStatus;
  subscribedAt: string;
  stats: {
    tasksToday: number;
    tasksThisMonth: number;
    successRate: number;
  };
}

export interface UpdateAgentConfigPayload {
  displayName?: string;
  policyJson?: string;
}

/* ------------------------------------------------------------------ */
/*  Agent Config (dedicated config page)                               */
/* ------------------------------------------------------------------ */

export interface AgentFullConfig {
  agentId: string;
  displayName: string;
  description: string;
  department: AgentDepartment;
  avatarUrl: string | null;
  policyJson: string;
  executionLimits: {
    maxTasksPerDay: number;
    maxTasksPerHour: number;
    maxConcurrentTasks: number;
  };
  autoApproveThresholds: {
    costLimitUsd: number;
    riskScoreMax: number;
    enabled: boolean;
  };
  escalation: {
    rules: EscalationRule[];
    slaMinutes: number;
    contacts: EscalationContact[];
  };
  integrations: AgentIntegrationConfig[];
  isEnabled: boolean;
  updatedAt: string;
}

export interface EscalationRule {
  id: string;
  condition: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  action: 'notify' | 'escalate' | 'pause_agent';
  description: string;
}

export interface EscalationContact {
  id: string;
  name: string;
  email: string;
  role: string;
  isPrimary: boolean;
}

export interface AgentIntegrationConfig {
  id: string;
  integrationId: string;
  name: string;
  provider: string;
  status: 'connected' | 'disconnected' | 'error';
  enabled: boolean;
  lastSyncAt: string | null;
}

export interface AgentConfigHistoryEntry {
  id: string;
  version: number;
  changedBy: string;
  changedAt: string;
  changeType: 'identity' | 'policy' | 'escalation' | 'integrations';
  changeSummary: string;
  previousValue: string;
  newValue: string;
}

export interface UpdateAgentFullConfigPayload {
  displayName?: string;
  description?: string;
  department?: AgentDepartment;
  avatarUrl?: string | null;
  policyJson?: string;
  executionLimits?: {
    maxTasksPerDay?: number;
    maxTasksPerHour?: number;
    maxConcurrentTasks?: number;
  };
  autoApproveThresholds?: {
    costLimitUsd?: number;
    riskScoreMax?: number;
    enabled?: boolean;
  };
  escalation?: {
    rules?: EscalationRule[];
    slaMinutes?: number;
    contacts?: EscalationContact[];
  };
  integrations?: {
    integrationId: string;
    enabled: boolean;
  }[];
}
