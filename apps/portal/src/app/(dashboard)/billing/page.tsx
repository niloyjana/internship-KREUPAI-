'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CreditCard,
  DollarSign,
  Loader2,
  AlertCircle,
  Download,
  Trash2,
  Activity,
  Receipt,
  ChevronLeft,
  ChevronRight,
  Tag,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getSubscriptions,
  getUsage,
  getInvoices,
  unsubscribeFromAgent,
} from '@/lib/api/subscriptions.api';
import type { InvoiceStatus } from '@/lib/types/subscription.types';

const invoiceStatusStyles: Record<InvoiceStatus, { bg: string; text: string }> = {
  paid: { bg: 'bg-green-50', text: 'text-green-700' },
  pending: { bg: 'bg-amber-50', text: 'text-amber-700' },
  overdue: { bg: 'bg-red-50', text: 'text-red-700' },
  draft: { bg: 'bg-gray-50', text: 'text-gray-500' },
};

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export default function BillingPage() {
  const queryClient = useQueryClient();
  const [invoicePage, setInvoicePage] = useState(1);
  const [unsubTarget, setUnsubTarget] = useState<{
    agentId: string;
    agentName: string;
  } | null>(null);

  // Fetch subscription overview
  const {
    data: subscription,
    isLoading: subLoading,
    isError: subError,
  } = useQuery({
    queryKey: ['subscriptionOverview'],
    queryFn: getSubscriptions,
  });

  // Fetch usage data
  const {
    data: usage,
    isLoading: usageLoading,
    isError: usageError,
  } = useQuery({
    queryKey: ['usageData'],
    queryFn: () => getUsage(),
  });

  // Fetch invoices
  const {
    data: invoiceData,
    isLoading: invoicesLoading,
    isError: invoicesError,
  } = useQuery({
    queryKey: ['invoices', invoicePage],
    queryFn: () => getInvoices({ page: invoicePage, pageSize: 10 }),
  });

  // Unsubscribe mutation
  const unsubscribeMutation = useMutation({
    mutationFn: (agentId: string) => unsubscribeFromAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptionOverview'] });
      queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] });
      setUnsubTarget(null);
    },
  });

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your subscription, track usage, and view invoices.
        </p>
      </div>

      {/* Subscription Overview */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Subscription Overview</h2>
          </div>
        </div>

        {subLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
          </div>
        )}

        {subError && (
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
            <p className="text-sm text-gray-500">Failed to load subscription data.</p>
          </div>
        )}

        {subscription && (
          <div className="p-6 space-y-6">
            {/* Summary Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-gray-50">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Plan</p>
                <p className="text-lg font-bold text-gray-900 mt-1">{subscription.plan}</p>
              </div>
              <div className="p-4 rounded-lg bg-gray-50">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Platform Fee
                </p>
                <p className="text-lg font-bold text-gray-900 mt-1">
                  {formatCurrency(subscription.platformFeeUsd)}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-gray-50">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Active Agents
                </p>
                <p className="text-lg font-bold text-gray-900 mt-1">
                  {subscription.agentSubscriptions.filter((a) => a.status === 'active').length}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-primary-50">
                <p className="text-xs font-medium text-primary-600 uppercase tracking-wide">
                  Monthly Total
                </p>
                <p className="text-lg font-bold text-primary-700 mt-1">
                  {formatCurrency(subscription.netTotalUsd)}
                </p>
                {subscription.discountPercent > 0 && (
                  <p className="text-xs text-primary-500 mt-0.5">
                    {subscription.discountPercent}% discount applied
                  </p>
                )}
              </div>
            </div>

            {/* Discount Banner */}
            {subscription.discountPercent > 0 && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-green-50 border border-green-200">
                <Tag className="w-4 h-4 text-green-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-green-800">
                    {subscription.discountPercent}% volume discount active
                  </p>
                  <p className="text-xs text-green-600">
                    You are saving {formatCurrency(subscription.discountAmountUsd)} per month.
                    Original total: {formatCurrency(subscription.totalMonthlyUsd)}.
                  </p>
                </div>
              </div>
            )}

            {/* Per-Agent Breakdown */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Agent Subscriptions</h3>
              {subscription.agentSubscriptions.length === 0 ? (
                <p className="text-sm text-gray-400">No agent subscriptions yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Agent</th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Department
                        </th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Status</th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Monthly Fee
                        </th>
                        <th className="text-right py-2.5 font-medium text-gray-500">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subscription.agentSubscriptions.map((agent) => (
                        <tr
                          key={agent.agentId}
                          className="border-b border-gray-50 last:border-0"
                        >
                          <td className="py-3 pr-4 font-medium text-gray-900">
                            {agent.agentName}
                          </td>
                          <td className="py-3 pr-4 text-gray-500 capitalize">
                            {agent.department}
                          </td>
                          <td className="py-3 pr-4">
                            <span
                              className={cn(
                                'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                                agent.status === 'active'
                                  ? 'bg-green-50 text-green-700'
                                  : agent.status === 'paused'
                                    ? 'bg-amber-50 text-amber-700'
                                    : 'bg-gray-100 text-gray-500',
                              )}
                            >
                              {agent.status}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-right text-gray-900">
                            {formatCurrency(agent.monthlyFeeUsd)}
                          </td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() =>
                                setUnsubTarget({
                                  agentId: agent.agentId,
                                  agentName: agent.agentName,
                                })
                              }
                              className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                              title="Unsubscribe"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Unsubscribe
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Billing Cycle */}
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span>
                Billing cycle: {formatDate(subscription.billingCycleStart)} &ndash;{' '}
                {formatDate(subscription.billingCycleEnd)}
              </span>
              <span>Next invoice: {formatDate(subscription.nextInvoiceDate)}</span>
            </div>
          </div>
        )}
      </div>

      {/* Unsubscribe Confirmation Dialog */}
      {unsubTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Unsubscribe from {unsubTarget.agentName}?
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              This agent will be deactivated at the end of the current billing period. You can
              re-subscribe at any time from the workforce catalog.
            </p>
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setUnsubTarget(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => unsubscribeMutation.mutate(unsubTarget.agentId)}
                disabled={unsubscribeMutation.isPending}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 transition-colors"
              >
                {unsubscribeMutation.isPending ? 'Unsubscribing...' : 'Confirm Unsubscribe'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Usage Section */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Current Period Usage</h2>
          </div>
        </div>

        {usageLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
          </div>
        )}

        {usageError && (
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
            <p className="text-sm text-gray-500">Failed to load usage data.</p>
          </div>
        )}

        {usage && (
          <div className="p-6 space-y-4">
            {/* Usage Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <div className="p-4 rounded-lg bg-gray-50 text-center">
                <p className="text-2xl font-bold text-gray-900">{formatNumber(usage.totalTasks)}</p>
                <p className="text-xs text-gray-500 mt-1">Total Tasks</p>
              </div>
              <div className="p-4 rounded-lg bg-gray-50 text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {formatNumber(usage.totalTokens)}
                </p>
                <p className="text-xs text-gray-500 mt-1">Total Tokens</p>
              </div>
              <div className="p-4 rounded-lg bg-gray-50 text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(usage.totalLlmCostUsd)}
                </p>
                <p className="text-xs text-gray-500 mt-1">LLM Cost</p>
              </div>
            </div>

            {/* Period */}
            <p className="text-xs text-gray-400">
              Period: {formatDate(usage.periodStart)} &ndash; {formatDate(usage.periodEnd)}
            </p>

            {/* Per-Agent Usage Table */}
            {usage.agents.length === 0 ? (
              <p className="text-sm text-gray-400">No usage data for this period.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Agent</th>
                      <th className="text-right py-2.5 pr-4 font-medium text-gray-500">Tasks</th>
                      <th className="text-right py-2.5 pr-4 font-medium text-gray-500">Tokens</th>
                      <th className="text-right py-2.5 font-medium text-gray-500">LLM Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usage.agents.map((agent) => (
                      <tr
                        key={agent.agentId}
                        className="border-b border-gray-50 last:border-0"
                      >
                        <td className="py-3 pr-4 font-medium text-gray-900">{agent.agentName}</td>
                        <td className="py-3 pr-4 text-right text-gray-600">
                          {formatNumber(agent.taskCount)}
                        </td>
                        <td className="py-3 pr-4 text-right text-gray-600">
                          {formatNumber(agent.tokenCount)}
                        </td>
                        <td className="py-3 text-right text-gray-900">
                          {formatCurrency(agent.llmCostUsd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Invoice History */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Receipt className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Invoice History</h2>
          </div>
        </div>

        {invoicesLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
          </div>
        )}

        {invoicesError && (
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
            <p className="text-sm text-gray-500">Failed to load invoices.</p>
          </div>
        )}

        {invoiceData && (
          <div className="p-6 space-y-4">
            {invoiceData.invoices.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Receipt className="w-8 h-8 text-gray-300 mb-2" />
                <p className="text-sm text-gray-400">No invoices yet.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Invoice
                        </th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Date</th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Due Date
                        </th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Amount
                        </th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Status</th>
                        <th className="text-right py-2.5 font-medium text-gray-500">Download</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoiceData.invoices.map((invoice) => {
                        const statusStyle = invoiceStatusStyles[invoice.status] || {
                          bg: 'bg-gray-50',
                          text: 'text-gray-500',
                        };

                        return (
                          <tr
                            key={invoice.id}
                            className="border-b border-gray-50 last:border-0"
                          >
                            <td className="py-3 pr-4 font-medium text-gray-900">
                              {invoice.invoiceNumber}
                            </td>
                            <td className="py-3 pr-4 text-gray-600">{formatDate(invoice.date)}</td>
                            <td className="py-3 pr-4 text-gray-600">
                              {formatDate(invoice.dueDate)}
                            </td>
                            <td className="py-3 pr-4 text-right font-medium text-gray-900">
                              {formatCurrency(invoice.amountUsd)}
                            </td>
                            <td className="py-3 pr-4">
                              <span
                                className={cn(
                                  'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                                  statusStyle.bg,
                                  statusStyle.text,
                                )}
                              >
                                {invoice.status}
                              </span>
                            </td>
                            <td className="py-3 text-right">
                              <button
                                onClick={() => {
                                  // Placeholder: would open download URL
                                  if (invoice.downloadUrl) {
                                    window.open(invoice.downloadUrl, '_blank');
                                  }
                                }}
                                className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                                title="Download invoice"
                              >
                                <Download className="w-3.5 h-3.5" />
                                PDF
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {invoiceData.meta.totalPages > 1 && (
                  <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-gray-400">
                      Page {invoiceData.meta.page} of {invoiceData.meta.totalPages} (
                      {invoiceData.meta.totalItems} invoices)
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setInvoicePage((p) => Math.max(1, p - 1))}
                        disabled={invoicePage <= 1}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                        Previous
                      </button>
                      <button
                        onClick={() =>
                          setInvoicePage((p) => Math.min(invoiceData.meta.totalPages, p + 1))
                        }
                        disabled={invoicePage >= invoiceData.meta.totalPages}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Next
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
