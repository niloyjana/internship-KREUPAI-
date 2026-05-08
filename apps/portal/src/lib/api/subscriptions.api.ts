import { apiClient } from './client';
import type {
  SubscriptionOverview,
  UsageData,
  Invoice,
  PaginationMeta,
} from '../types/subscription.types';

/**
 * Fetch the current tenant's subscription overview from subscription-service (port 3005).
 */
export async function getSubscriptions(): Promise<SubscriptionOverview> {
  const { data } = await apiClient.get<SubscriptionOverview>('/v1/subscriptions');
  return data;
}

/**
 * Subscribe the current tenant to an agent.
 */
export async function subscribeToAgent(agentId: string): Promise<void> {
  await apiClient.post('/v1/subscriptions/agents', { agentId });
}

/**
 * Unsubscribe from an agent. Returns the effective cancellation date.
 */
export async function unsubscribeFromAgent(
  agentId: string,
): Promise<{ effectiveCancellationDate: string }> {
  const { data } = await apiClient.delete<{ effectiveCancellationDate: string }>(
    `/v1/subscriptions/agents/${agentId}`,
  );
  return data;
}

/**
 * Fetch usage data, optionally filtered by agent and date range.
 */
export async function getUsage(params?: {
  agentId?: string;
  from?: string;
  to?: string;
}): Promise<UsageData> {
  const { data } = await apiClient.get<UsageData>('/v1/subscriptions/usage', {
    params,
  });
  return data;
}

/**
 * Fetch paginated invoice history.
 */
export async function getInvoices(params?: {
  page?: number;
  pageSize?: number;
}): Promise<{ invoices: Invoice[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<{ invoices: Invoice[]; meta: PaginationMeta }>(
    '/v1/subscriptions/invoices',
    { params },
  );
  return data;
}
