import { apiClient } from './client';
import type {
  AgentDefinition,
  AgentDepartment,
  AgentCapability,
  AgentIntegration,
  AgentPricing,
  SubscribedAgent,
  AgentConfig,
  UpdateAgentConfigPayload,
} from '../types/agent.types';

/* ------------------------------------------------------------------ */
/*  Helpers: transform backend → portal types                          */
/* ------------------------------------------------------------------ */

/** Map backend department enum to portal lowercase department. */
const DEPARTMENT_MAP: Record<string, AgentDepartment> = {
  CUSTOMER_OPERATIONS: 'support',
  SALES_MARKETING: 'sales',
  HR_PEOPLE_OPS: 'hr',
  FINANCE_PROCUREMENT: 'finance',
  DELIVERY_OPS: 'operations',
  GOVERNANCE_RISK_CONTROL: 'legal',
};

function mapDepartment(dept: string): AgentDepartment {
  return DEPARTMENT_MAP[dept] || 'operations';
}

/** Convert a snake_case / kebab-case capability string into a readable name. */
function prettifyName(raw: string): string {
  return raw.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Transform a string[] of capabilities into AgentCapability objects. */
function mapCapabilities(caps: string[]): AgentCapability[] {
  return (caps || []).map((c) => ({
    id: c,
    name: prettifyName(c),
    description: '',
  }));
}

/** Transform a string[] of integrations into AgentIntegration objects. */
function mapIntegrations(integrations: string[]): AgentIntegration[] {
  return (integrations || []).map((i) => ({
    id: i,
    name: prettifyName(i),
    type: 'external',
    required: true,
    connected: false,
  }));
}

/** Build an AgentPricing object from the flat monthlyPricingUsd field. */
function mapPricing(monthlyPricingUsd: string | number): AgentPricing {
  return {
    monthlyFeeUsd: Number(monthlyPricingUsd) || 0,
    perTaskFeeUsd: 0,
    includedTasksPerMonth: 1000,
  };
}

/** Derive a short description from the full description (first sentence). */
function deriveShortDescription(description: string): string {
  if (!description) return '';
  const firstSentence = description.split(/(?<=[.!?])\s/)[0];
  return firstSentence.length <= 120 ? firstSentence : description.slice(0, 117) + '...';
}

/** Shape of a raw agent item from the backend catalog API. */
interface RawCatalogAgent {
  id: string;
  agentId: string;
  name: string;
  department: string;
  description: string;
  version: string;
  monthlyPricingUsd: string | number;
  capabilities: string[];
  requiredIntegrations: string[];
  isActive: boolean;
  iconUrl?: string;
  createdAt?: string;
  updatedAt?: string;
}

function transformCatalogAgent(raw: RawCatalogAgent): AgentDefinition {
  return {
    id: raw.agentId,
    name: raw.name,
    department: mapDepartment(raw.department),
    description: raw.description,
    shortDescription: deriveShortDescription(raw.description),
    version: raw.version || '1.0.0',
    capabilities: mapCapabilities(raw.capabilities),
    requiredIntegrations: mapIntegrations(raw.requiredIntegrations),
    pricing: mapPricing(raw.monthlyPricingUsd),
    iconUrl: raw.iconUrl,
    isActive: raw.isActive ?? true,
    createdAt: raw.createdAt || '',
    updatedAt: raw.updatedAt || '',
  };
}

/** Shape of a raw subscribed agent item from the backend. */
interface RawSubscribedAgent {
  agentId: string;
  name: string;
  displayName: string;
  department: string;
  description?: string;
  capabilities?: string[];
  status: string;
  subscriptionStatus: string | null;
  integrationIds: string[];
  isEnabled: boolean;
  lastActiveAt: string | null;
  todayTaskCount: number;
  pendingEscalations: number;
}

/** Map backend agent status to portal AgentStatus type. */
function mapAgentStatus(status: string): 'active' | 'paused' | 'pending' | 'error' {
  const s = (status || '').toUpperCase();
  if (s === 'ACTIVE' || s === 'WORKING') return 'active';
  if (s === 'PAUSED') return 'paused';
  if (s === 'ERROR' || s === 'FAILED') return 'error';
  return 'pending';
}

/* ------------------------------------------------------------------ */
/*  API Functions                                                      */
/* ------------------------------------------------------------------ */

/**
 * Fetch the full agent catalog from agent-registry (port 3003).
 */
export async function getAgentCatalog(params?: {
  department?: string;
  isActive?: boolean;
}): Promise<AgentDefinition[]> {
  // Backend expects uppercase department enum for filtering
  const queryParams: Record<string, unknown> = {};
  if (params?.isActive !== undefined) queryParams.isActive = params.isActive;
  if (params?.department) {
    // Reverse-map portal lowercase department back to backend enum
    const reverseMap: Record<string, string> = {};
    for (const [backend, portal] of Object.entries(DEPARTMENT_MAP)) {
      reverseMap[portal] = backend;
    }
    queryParams.department = reverseMap[params.department] || params.department;
  }
  // Request all agents (backend defaults to 20 per page)
  queryParams.limit = 100;

  const { data } = await apiClient.get('/v1/agents/catalog', { params: queryParams });
  // Interceptor unwraps { success, data } → data is the items array
  const items = Array.isArray(data) ? data : [];
  return items.map(transformCatalogAgent);
}

/**
 * Fetch a single agent's details by ID.
 */
export async function getAgentDetails(agentId: string): Promise<AgentDefinition> {
  const { data } = await apiClient.get(`/v1/agents/catalog/${agentId}`);
  return transformCatalogAgent(data as RawCatalogAgent);
}

/**
 * Fetch agents that the current tenant is subscribed to.
 */
export async function getSubscribedAgents(): Promise<SubscribedAgent[]> {
  const { data } = await apiClient.get('/v1/agents/subscribed');
  const items = Array.isArray(data) ? data : [];

  return items.map((raw: RawSubscribedAgent) => {
    const agentId = raw.agentId;
    const dept = mapDepartment(raw.department);

    // Build a partial AgentDefinition from the flat backend data
    const agent: AgentDefinition = {
      id: agentId,
      name: raw.name || raw.displayName || agentId,
      department: dept,
      description: raw.description || '',
      shortDescription: '',
      version: '1.0.0',
      capabilities: mapCapabilities(raw.capabilities || []),
      requiredIntegrations: [],
      pricing: { monthlyFeeUsd: 0, perTaskFeeUsd: 0, includedTasksPerMonth: 1000 },
      isActive: raw.isEnabled ?? true,
      createdAt: '',
      updatedAt: '',
    };

    const config: AgentConfig = {
      agentId,
      displayName: raw.displayName || raw.name || agentId,
      policyJson: '',
      isEnabled: raw.isEnabled ?? true,
      updatedAt: '',
    };

    return {
      id: agentId,
      agentId,
      agent,
      config,
      status: mapAgentStatus(raw.status),
      subscribedAt: '',
      stats: {
        tasksToday: raw.todayTaskCount || 0,
        tasksThisMonth: 0,
        successRate: 100,
      },
    } satisfies SubscribedAgent;
  });
}

/**
 * Update an agent's configuration (display name, policy JSON).
 */
export async function updateAgentConfig(
  agentId: string,
  config: UpdateAgentConfigPayload,
): Promise<AgentConfig> {
  const { data: raw } = await apiClient.put(`/v1/agents/${agentId}/config`, config);
  const d = raw as Record<string, unknown>;
  return {
    agentId: (d.agentId as string) || agentId,
    displayName: (d.displayName as string) || '',
    policyJson:
      typeof d.policyJson === 'string' ? d.policyJson : JSON.stringify(d.policyJson || {}),
    isEnabled: (d.isEnabled as boolean) ?? true,
    updatedAt: (d.updatedAt as string) || '',
  };
}

/**
 * Enable a paused or pending agent.
 */
export async function enableAgent(agentId: string): Promise<void> {
  await apiClient.post(`/v1/agents/${agentId}/enable`);
}

/**
 * Pause an active agent.
 */
export async function pauseAgent(agentId: string): Promise<void> {
  await apiClient.post(`/v1/agents/${agentId}/pause`);
}
