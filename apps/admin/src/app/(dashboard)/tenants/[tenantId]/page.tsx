'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  ArrowLeft,
  Building2,
  Users,
  Bot,
  CreditCard,
  ScrollText,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { format } from 'date-fns';
import { getTenant } from '@/lib/api/tenants.api';
import { cn } from '@/lib/utils';

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

const statusColors: Record<string, string> = {
  active: 'bg-green-50 text-green-700',
  suspended: 'bg-red-50 text-red-700',
  trial: 'bg-amber-50 text-amber-700',
};

export default function TenantDetailPage() {
  const params = useParams();
  const tenantId = params.tenantId as string;

  const { data: tenant, isLoading, isError } = useQuery({
    queryKey: ['admin-tenant', tenantId],
    queryFn: () => getTenant(tenantId),
    enabled: !!tenantId,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Loading tenant details...</p>
      </div>
    );
  }

  if (isError || !tenant) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
        <p className="text-sm font-medium text-gray-700">Failed to load tenant</p>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Back link + Header */}
      <div>
        <Link
          href="/tenants"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to tenants
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{tenant.name}</h1>
            <p className="text-sm text-gray-500 mt-1 font-mono">{tenant.slug}</p>
          </div>
          <span className={cn('px-3 py-1 rounded-full text-sm font-medium capitalize', statusColors[tenant.status] || 'bg-gray-100 text-gray-700')}>
            {tenant.status}
          </span>
        </div>
      </div>

      {/* Info Card */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Tenant Information</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500">Plan</p>
            <p className="text-sm font-medium text-gray-900 capitalize">{tenant.plan}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Users</p>
            <p className="text-sm font-medium text-gray-900">{tenant.usersCount}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Agents</p>
            <p className="text-sm font-medium text-gray-900">{tenant.agentsCount}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Created</p>
            <p className="text-sm font-medium text-gray-900">
              {format(new Date(tenant.createdAt), 'MMM d, yyyy')}
            </p>
          </div>
        </div>
      </div>

      {/* Usage Stats */}
      {tenant.usageStats && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Usage Statistics</h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div>
              <p className="text-xs text-gray-500">Total Tasks</p>
              <p className="text-lg font-bold text-gray-900">{tenant.usageStats.totalTasks}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Tasks This Month</p>
              <p className="text-lg font-bold text-gray-900">{tenant.usageStats.tasksThisMonth}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Total LLM Cost</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(tenant.usageStats.totalLlmCost)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">LLM Cost This Month</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(tenant.usageStats.llmCostThisMonth)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Task Duration</p>
              <p className="text-lg font-bold text-gray-900">{Math.round(tenant.usageStats.avgTaskDuration / 1000)}s</p>
            </div>
          </div>
        </div>
      )}

      {/* Two-column: Users + Subscriptions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Users List */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="p-5 border-b border-gray-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Users</h2>
            <span className="ml-auto text-xs text-gray-400">{tenant.users?.length ?? 0}</span>
          </div>
          <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
            {(!tenant.users || tenant.users.length === 0) ? (
              <div className="p-5 text-center text-sm text-gray-500">No users found</div>
            ) : (
              tenant.users.map((user) => (
                <div key={user.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{user.name}</p>
                    <p className="text-xs text-gray-500">{user.email}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-medium text-gray-600 capitalize">{user.role}</span>
                    {user.lastLoginAt && (
                      <p className="text-xs text-gray-400">
                        Last login: {format(new Date(user.lastLoginAt), 'MMM d, HH:mm')}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Subscriptions List */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="p-5 border-b border-gray-100 flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Subscriptions</h2>
            <span className="ml-auto text-xs text-gray-400">{tenant.subscriptions?.length ?? 0}</span>
          </div>
          <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
            {(!tenant.subscriptions || tenant.subscriptions.length === 0) ? (
              <div className="p-5 text-center text-sm text-gray-500">No subscriptions found</div>
            ) : (
              tenant.subscriptions.map((sub) => (
                <div key={sub.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{sub.agentName}</p>
                    <p className="text-xs text-gray-500 capitalize">{sub.plan} plan</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{formatCurrency(sub.monthlyPrice)}/mo</p>
                    <span className={cn(
                      'text-xs font-medium capitalize',
                      sub.status === 'active' ? 'text-green-600' : 'text-gray-500',
                    )}>
                      {sub.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Audit Log */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-5 border-b border-gray-100 flex items-center gap-2">
          <ScrollText className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Audit Log</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Timestamp</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Actor</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Entity</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(!tenant.auditLog || tenant.auditLog.length === 0) ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No audit entries found
                  </td>
                </tr>
              ) : (
                tenant.auditLog.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {format(new Date(entry.timestamp), 'MMM d, HH:mm:ss')}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{entry.actor}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-700">
                        {entry.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{entry.entity}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{entry.details}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
