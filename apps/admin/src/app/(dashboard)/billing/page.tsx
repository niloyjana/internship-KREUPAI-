'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  DollarSign,
  FileText,
  Clock,
  AlertTriangle,
  Loader2,
  AlertCircle,
  TrendingUp,
  ArrowRight,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { getRevenue } from '@/lib/api/billing.api';
import { cn } from '@/lib/utils';

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function BillingPage() {
  const { data: revenue, isLoading, isError } = useQuery({
    queryKey: ['admin-revenue'],
    queryFn: getRevenue,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Loading billing data...</p>
      </div>
    );
  }

  if (isError || !revenue) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
        <p className="text-sm font-medium text-gray-700">Failed to load billing data</p>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
          <p className="text-sm text-gray-500 mt-1">Platform revenue overview</p>
        </div>
        <Link
          href="/billing/invoices"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <FileText className="w-4 h-4" />
          View Invoices
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* MRR */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">MRR</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(revenue.mrr)}</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50">
              <TrendingUp className="w-5 h-5 text-purple-600" />
            </div>
          </div>
        </div>

        {/* Total Invoices */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Invoices</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{revenue.totalInvoices}</p>
              <p className="text-xs text-green-600 mt-1">{revenue.paidInvoices} paid</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
          </div>
        </div>

        {/* Pending */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Pending</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{revenue.pendingInvoices}</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-50">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
          </div>
        </div>

        {/* Overdue */}
        <div className={cn(
          'bg-white rounded-lg border shadow-sm p-5',
          revenue.overdueInvoices > 0 ? 'border-red-400' : 'border-gray-200',
        )}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Overdue</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{revenue.overdueInvoices}</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-red-50">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Revenue by Agent Chart */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Revenue by Agent</h2>
        </div>

        {revenue.revenueByAgent.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={revenue.revenueByAgent} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9ca3af" />
              <YAxis
                type="category"
                dataKey="agentName"
                tick={{ fontSize: 12 }}
                stroke="#9ca3af"
                width={140}
              />
              <Tooltip
                formatter={(value: number) => [formatCurrency(value), 'Revenue']}
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
              />
              <Bar dataKey="revenue" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center py-16">
            <p className="text-sm text-gray-500">No revenue data available</p>
          </div>
        )}
      </div>

      {/* Revenue Trend */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Monthly Revenue Trend</h2>
        </div>

        {revenue.revenueByMonth.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={revenue.revenueByMonth}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#9ca3af" />
              <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
              <Tooltip
                formatter={(value: number) => [formatCurrency(value), 'Revenue']}
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
              />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center py-16">
            <p className="text-sm text-gray-500">No monthly data available</p>
          </div>
        )}
      </div>
    </div>
  );
}
