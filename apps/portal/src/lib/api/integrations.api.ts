import { apiClient } from './client';
import type {
  CatalogProvider,
  IntegrationConnection,
  ConnectionTestResult,
  CreateConnectionPayload,
  CreateConnectionResponse,
  ConnectionLogsParams,
  ConnectionLogsResponse,
} from '../types/integration.types';

/**
 * Fetch the integration catalog (available providers).
 */
export async function getIntegrationCatalog(): Promise<CatalogProvider[]> {
  const { data } = await apiClient.get<CatalogProvider[]>('/v1/integrations/catalog');
  return Array.isArray(data) ? data : [];
}

/**
 * Fetch all integration connections for the current tenant.
 */
export async function getConnections(): Promise<IntegrationConnection[]> {
  const { data } = await apiClient.get<IntegrationConnection[]>('/v1/integrations/connections');
  return Array.isArray(data) ? data : [];
}

/**
 * Create a new integration connection.
 */
export async function createConnection(
  payload: CreateConnectionPayload,
): Promise<CreateConnectionResponse> {
  const { data } = await apiClient.post<CreateConnectionResponse>(
    '/v1/integrations/connections',
    payload,
  );
  return data;
}

/**
 * Fetch a single integration connection by ID.
 */
export async function getConnection(connectionId: string): Promise<IntegrationConnection> {
  const { data } = await apiClient.get<IntegrationConnection>(
    `/v1/integrations/connections/${connectionId}`,
  );
  return data;
}

/**
 * Delete (disconnect) an integration connection.
 */
export async function deleteConnection(connectionId: string): Promise<void> {
  await apiClient.delete(`/v1/integrations/connections/${connectionId}`);
}

/**
 * Fetch activity logs for a connection.
 */
export async function getConnectionLogs(
  connectionId: string,
  params?: ConnectionLogsParams,
): Promise<ConnectionLogsResponse> {
  const { data } = await apiClient.get<ConnectionLogsResponse>(
    `/v1/integrations/connections/${connectionId}/logs`,
    { params },
  );
  return data;
}

/**
 * Test an integration connection's health.
 */
export async function testConnection(connectionId: string): Promise<ConnectionTestResult> {
  const { data } = await apiClient.post<ConnectionTestResult>(
    `/v1/integrations/connections/${connectionId}/test`,
  );
  return data;
}
