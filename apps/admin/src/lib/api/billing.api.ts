import { apiClient } from './client';

export interface RevenueData {
  mrr: number;
  totalRevenue: number;
  totalInvoices: number;
  paidInvoices: number;
  pendingInvoices: number;
  overdueInvoices: number;
  revenueByAgent: RevenueByAgent[];
  revenueByMonth: RevenueByMonth[];
}

export interface RevenueByAgent {
  agentId: string;
  agentName: string;
  revenue: number;
  subscriptions: number;
}

export interface RevenueByMonth {
  month: string;
  revenue: number;
}

export interface Invoice {
  id: string;
  tenantId: string;
  tenantName: string;
  amount: number;
  currency: string;
  status: 'paid' | 'pending' | 'overdue' | 'cancelled';
  issuedAt: string;
  dueDate: string;
  paidAt: string | null;
}

export interface InvoicesParams {
  status?: string;
  tenantId?: string;
  page?: number;
  pageSize?: number;
}

export async function getRevenue(): Promise<RevenueData> {
  const response = await apiClient.get('/admin/billing/revenue');
  return response.data;
}

export async function getInvoices(params?: InvoicesParams): Promise<{ data: Invoice[]; total: number }> {
  const response = await apiClient.get('/admin/billing/invoices', { params });
  return response.data;
}
