export interface BillingSubscriptionActivatedPayload {
  subscriptionId: string;
  tenantId: string;
  agentId: string;
  plan: string;
  monthlyAmountUsd: number;
  stripeSubItemId: string;
  billingCycleStart: string;
}

export interface BillingPaymentFailedPayload {
  invoiceId: string;
  amountUsd: number;
  failureReason: string;
  attemptCount: number;
  nextRetryAt: string | null;
}

export interface BillingUsageRecordedPayload {
  tenantId: string;
  agentId: string;
  executionId: string;
  taskCount: number;
  tokenCount: number;
  costUsd: number;
  periodStart: string;
  periodEnd: string;
}
