import { apiClient } from './client';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: 'active' | 'suspended' | 'trial';
  usersCount: number;
  agentsCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface TenantDetail extends Tenant {
  users: TenantUser[];
  subscriptions: TenantSubscription[];
  usageStats: TenantUsageStats;
  auditLog: AuditEntry[];
}

export interface TenantUser {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  lastLoginAt: string | null;
}

export interface TenantSubscription {
  id: string;
  agentId: string;
  agentName: string;
  plan: string;
  status: string;
  startDate: string;
  endDate: string | null;
  monthlyPrice: number;
}

export interface TenantUsageStats {
  totalTasks: number;
  tasksThisMonth: number;
  totalLlmCost: number;
  llmCostThisMonth: number;
  avgTaskDuration: number;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  entity: string;
  details: string;
}

export interface TenantsParams {
  search?: string;
  plan?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

export async function getTenants(params?: TenantsParams): Promise<{ data: Tenant[]; total: number }> {
  const response = await apiClient.get('/admin/tenants', { params });
  return response.data;
}

export async function getTenant(tenantId: string): Promise<TenantDetail> {
  const response = await apiClient.get(`/admin/tenants/${tenantId}`);
  return response.data;
}

export async function suspendTenant(tenantId: string): Promise<void> {
  await apiClient.post(`/admin/tenants/${tenantId}/suspend`);
}

export async function reactivateTenant(tenantId: string): Promise<void> {
  await apiClient.post(`/admin/tenants/${tenantId}/reactivate`);
}
