'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Building2,
  Bot,
  DollarSign,
  Activity,
  Loader2,
  AlertCircle,
  TrendingUp,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { useAuthStore } from '@/lib/stores/auth.store';
import { getTenants } from '@/lib/api/tenants.api';
import { getAgentDefinitions } from '@/lib/api/agents.api';
import { getRevenue } from '@/lib/api/billing.api';
import { getHealthStatus } from '@/lib/api/system.api';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function AdminDashboardPage() {
  const user = useAuthStore((s) => s.user);

  // Fetch tenants
  const {
    data: tenantsData,
    isLoading: tenantsLoading,
  } = useQuery({
    queryKey: ['admin-tenants'],
    queryFn: () => getTenants({ pageSize: 1 }),
    refetchInterval: 60000,
  });

  // Fetch agent definitions
  const {
    data: agents = [],
    isLoading: agentsLoading,
  } = useQuery({
    queryKey: ['admin-agents'],
    queryFn: () => getAgentDefinitions(),
    refetchInterval: 60000,
  });

  // Fetch revenue
  const {
    data: revenue,
    isLoading: revenueLoading,
  } = useQuery({
    queryKey: ['admin-revenue'],
    queryFn: getRevenue,
    refetchInterval: 60000,
  });

  // Fetch system health
  const {
    data: health,
    isLoading: healthLoading,
  } = useQuery({
    queryKey: ['admin-health'],
    queryFn: getHealthStatus,
    refetchInterval: 30000,
  });

  const isLoading = tenantsLoading || agentsLoading || revenueLoading || healthLoading;

  const totalTenants = tenantsData?.total ?? 0;
  const totalAgentSubscriptions = agents.reduce((sum, a) => sum + a.subscriptionCount, 0);
  const mrr = revenue?.mrr ?? 0;
  const systemStatus = health?.overall ?? 'unknown';

  // Revenue by agent chart data
  const revenueByAgent = revenue?.revenueByAgent ?? [];
  const revenueByMonth = revenue?.revenueByMonth ?? [];

  // System health status color
  const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
    healthy: { bg: 'bg-green-50', text: 'text-green-700', dot: 'bg-green-500' },
    degraded: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
    down: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
    unknown: { bg: 'bg-gray-50', text: 'text-gray-700', dot: 'bg-gray-400' },
  };

  const statusStyle = statusColors[systemStatus] || statusColors.unknown;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Admin Overview
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Welcome back, {user?.name?.split(' ')[0] || 'Admin'}. Here is your platform at a glance.
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading dashboard...</p>
        </div>
      )}

      {!isLoading && (
        <>
          {/* ============================================================ */}
          {/* KPI Cards Row                                                */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Total Tenants */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Total Tenants
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {totalTenants}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
                  <Building2 className="w-5 h-5 text-blue-600" />
                </div>
              </div>
            </div>

            {/* Agent Subscriptions */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Agent Subscriptions
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {totalAgentSubscriptions}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    across {agents.length} agent{agents.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-50">
                  <Bot className="w-5 h-5 text-green-600" />
                </div>
              </div>
            </div>

            {/* MRR */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Monthly Revenue (MRR)
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatCurrency(mrr)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50">
                  <DollarSign className="w-5 h-5 text-purple-600" />
                </div>
              </div>
            </div>

            {/* System Health */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    System Health
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={cn('w-2.5 h-2.5 rounded-full', statusStyle.dot)} />
                    <span className={cn('text-sm font-semibold capitalize', statusStyle.text)}>
                      {systemStatus}
                    </span>
                  </div>
                  {health && (
                    <p className="text-xs text-gray-400 mt-1">
                      {health.services.filter((s) => s.status === 'healthy').length}/{health.services.length} services healthy
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-50">
                  <Activity className="w-5 h-5 text-emerald-600" />
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* Charts Row                                                   */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue by Month Bar Chart */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Revenue Trend</h2>
              </div>

              {revenueByMonth.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={revenueByMonth}>
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
                  <p className="text-sm text-gray-500">No revenue data available</p>
                </div>
              )}
            </div>

            {/* Revenue by Agent Pie Chart */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-4">
                <Bot className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Revenue by Agent</h2>
              </div>

              {revenueByAgent.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={revenueByAgent}
                      dataKey="revenue"
                      nameKey="agentName"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ agentName, percent }) =>
                        `${agentName} (${(percent * 100).toFixed(0)}%)`
                      }
                      labelLine={true}
                    >
                      {revenueByAgent.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => [formatCurrency(value), 'Revenue']}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center py-16">
                  <p className="text-sm text-gray-500">No agent revenue data available</p>
                </div>
              )}
            </div>
          </div>

          {/* ============================================================ */}
          {/* Quick Links                                                  */}
          {/* ============================================================ */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'View Tenants', href: '/tenants', icon: Building2, color: 'bg-blue-50 text-blue-600' },
                { label: 'Manage Agents', href: '/agents', icon: Bot, color: 'bg-green-50 text-green-600' },
                { label: 'View Invoices', href: '/billing/invoices', icon: DollarSign, color: 'bg-purple-50 text-purple-600' },
                { label: 'System Health', href: '/system', icon: Activity, color: 'bg-emerald-50 text-emerald-600' },
              ].map((action) => (
                <a
                  key={action.href}
                  href={action.href}
                  className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  <div className={cn('flex items-center justify-center w-9 h-9 rounded-lg', action.color)}>
                    <action.icon className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-medium text-gray-700">{action.label}</span>
                </a>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
