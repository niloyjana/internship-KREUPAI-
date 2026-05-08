import { apiClient } from './client';

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  responseTimeMs: number;
  lastChecked: string;
  details?: string;
}

export interface HealthStatus {
  overall: 'healthy' | 'degraded' | 'down';
  services: ServiceHealth[];
  kafka: { status: string; brokers: number; topics: number };
  redis: { status: string; memoryUsage: string; connectedClients: number };
  database: { status: string; activeConnections: number; poolSize: number };
}

export interface DlqEntry {
  id: string;
  topic: string;
  partition: number;
  offset: number;
  key: string;
  payload: Record<string, any>;
  error: string;
  failedAt: string;
  retryCount: number;
  status: 'pending' | 'retried' | 'dismissed';
}

export interface DlqParams {
  status?: string;
  topic?: string;
  page?: number;
  pageSize?: number;
}

export async function getHealthStatus(): Promise<HealthStatus> {
  const response = await apiClient.get('/admin/system/health');
  return response.data;
}

export async function getDlqEntries(params?: DlqParams): Promise<{ data: DlqEntry[]; total: number }> {
  const response = await apiClient.get('/admin/system/dlq', { params });
  return response.data;
}

export async function retryDlqEntry(entryId: string): Promise<void> {
  await apiClient.post(`/admin/system/dlq/${entryId}/retry`);
}

export async function dismissDlqEntry(entryId: string): Promise<void> {
  await apiClient.post(`/admin/system/dlq/${entryId}/dismiss`);
}
