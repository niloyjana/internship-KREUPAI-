/**
 * Types for subscription, billing, and usage data.
 */

export interface AgentSubscriptionLine {
  agentId: string;
  agentName: string;
  department: string;
  monthlyFeeUsd: number;
  status: 'active' | 'paused' | 'cancelled';
  subscribedAt: string;
}

export interface SubscriptionOverview {
  tenantId: string;
  plan: string;
  platformFeeUsd: number;
  agentSubscriptions: AgentSubscriptionLine[];
  totalMonthlyUsd: number;
  discountPercent: number;
  discountAmountUsd: number;
  netTotalUsd: number;
  billingCycleStart: string;
  billingCycleEnd: string;
  nextInvoiceDate: string;
}

export interface AgentUsageLine {
  agentId: string;
  agentName: string;
  taskCount: number;
  tokenCount: number;
  llmCostUsd: number;
}

export interface UsageData {
  periodStart: string;
  periodEnd: string;
  agents: AgentUsageLine[];
  totalTasks: number;
  totalTokens: number;
  totalLlmCostUsd: number;
}

export type InvoiceStatus = 'paid' | 'pending' | 'overdue' | 'draft';

export interface Invoice {
  id: string;
  invoiceNumber: string;
  date: string;
  dueDate: string;
  amountUsd: number;
  status: InvoiceStatus;
  downloadUrl: string;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}
