// ─── Enums ────────────────────────────────────────────────────────────────────

export enum BillingEventType {
  SUBSCRIPTION_CREATED = 'subscription_created',
  SUBSCRIPTION_UPGRADED = 'subscription_upgraded',
  SUBSCRIPTION_DOWNGRADED = 'subscription_downgraded',
  SUBSCRIPTION_CANCELLED = 'subscription_cancelled',
  PAYMENT_SUCCEEDED = 'payment_succeeded',
  PAYMENT_FAILED = 'payment_failed',
  INVOICE_GENERATED = 'invoice_generated',
  USAGE_RECORDED = 'usage_recorded',
  REFUND_ISSUED = 'refund_issued',
}

export enum InvoiceStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  PAID = 'paid',
  OVERDUE = 'overdue',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded',
}

// ─── Interfaces ───────────────────────────────────────────────────────────────

export interface BillingEvent {
  id: string;
  tenantId: string;
  type: BillingEventType;
  amount?: number;
  currency: string;
  description: string;
  stripeEventId?: string;
  metadata: Record<string, unknown>;
  createdAt: Date;
}

export interface Invoice {
  id: string;
  tenantId: string;
  status: InvoiceStatus;
  periodStart: Date;
  periodEnd: Date;
  subtotal: number;
  tax: number;
  total: number;
  currency: string;
  lineItems: InvoiceLineItem[];
  stripeInvoiceId?: string;
  paidAt?: Date;
  dueAt: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unitPrice: number;
  amount: number;
  agentDefinitionId?: string;
  metricType?: string;
}

export interface UsageMetric {
  id: string;
  tenantId: string;
  agentDefinitionId: string;
  metricType: string; // e.g., 'api_calls', 'tokens_used', 'workflow_executions'
  value: number;
  periodStart: Date;
  periodEnd: Date;
  metadata: Record<string, unknown>;
  createdAt: Date;
}
