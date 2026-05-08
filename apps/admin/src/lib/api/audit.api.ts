import { apiClient } from './client';

export interface AuditLog {
  id: string;
  timestamp: string;
  tenantId: string;
  tenantName: string;
  actor: string;
  action: string;
  entity: string;
  entityId: string;
  details: string;
  metadata: Record<string, any>;
}

export interface AuditLogsParams {
  tenantId?: string;
  actor?: string;
  action?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

export async function getAuditLogs(params?: AuditLogsParams): Promise<{ data: AuditLog[]; total: number }> {
  const response = await apiClient.get('/admin/audit', { params });
  return response.data;
}
