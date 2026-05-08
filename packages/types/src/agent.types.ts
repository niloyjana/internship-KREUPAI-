// ─── Enums ────────────────────────────────────────────────────────────────────

export enum AgentDepartment {
  FINANCE = 'finance',
  HR = 'hr',
  SALES = 'sales',
  MARKETING = 'marketing',
  OPERATIONS = 'operations',
  CUSTOMER_SUPPORT = 'customer_support',
  IT = 'it',
  LEGAL = 'legal',
  GENERAL = 'general',
}

export enum AgentStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  DEPRECATED = 'deprecated',
  ARCHIVED = 'archived',
}

export enum SubscriptionStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired',
}

// ─── Interfaces ───────────────────────────────────────────────────────────────

export interface AgentDefinition {
  id: string;
  name: string;
  slug: string;
  description: string;
  department: AgentDepartment;
  status: AgentStatus;
  version: string;
  capabilities: string[];
  defaultConfig: Record<string, unknown>;
  systemPrompt: string;
  modelProvider: string;
  modelId: string;
  tools: string[];
  createdAt: Date;
  updatedAt: Date;
}

export interface AgentSubscription {
  id: string;
  tenantId: string;
  agentDefinitionId: string;
  status: SubscriptionStatus;
  config: AgentConfig;
  subscribedAt: Date;
  cancelledAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface AgentConfig {
  customName?: string;
  customPromptAdditions?: string;
  enabledTools: string[];
  permissions: Record<string, boolean>;
  rateLimit?: {
    maxRequestsPerMinute: number;
    maxTokensPerDay: number;
  };
  escalationRules?: {
    confidenceThreshold: number;
    alwaysEscalateCategories: string[];
  };
}

export interface AgentInstance {
  id: string;
  tenantId: string;
  subscriptionId: string;
  agentDefinitionId: string;
  sessionId: string;
  status: 'running' | 'idle' | 'error' | 'terminated';
  startedAt: Date;
  lastActivityAt: Date;
  metadata: Record<string, unknown>;
}
