'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import {
  Activity,
  Calendar,
  Loader2,
  AlertCircle,
  TrendingUp,
  DollarSign,
  Zap,
  Bot,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Sub-navigation                                                      */
/* ------------------------------------------------------------------ */

const billingTabs = [
  { label: 'Overview', href: '/billing' },
  { label: 'Invoices', href: '/billing/invoices' },
  { label: 'Usage', href: '/billing/usage' },
  { label: 'Plans', href: '/billing/plans' },
];

/* ------------------------------------------------------------------ */
/*  Types & Mock Data                                                   */
/* ------------------------------------------------------------------ */

interface AgentUsage {
  agentId: string;
  agentName: string;
  tasks: number;
  tokens: number;
  cost: number;
}

interface DailyUsage {
  date: string;
  tasks: number;
  tokens: number;
  cost: number;
}

const MOCK_AGENT_USAGE: AgentUsage[] = [
  { agentId: '1', agentName: 'Customer Support Agent', tasks: 1240, tokens: 2850000, cost: 342.50 },
  { agentId: '2', agentName: 'Invoice Processing Agent', tasks: 860, tokens: 1920000, cost: 230.40 },
  { agentId: '3', agentName: 'HR Onboarding Agent', tasks: 320, tokens: 780000, cost: 93.60 },
  { agentId: '4', agentName: 'IT Helpdesk Agent', tasks: 540, tokens: 1100000, cost: 132.00 },
  { agentId: '5', agentName: 'Sales Lead Qualifier', tasks: 180, tokens: 450000, cost: 54.00 },
];

function generateDailyData(days: number): DailyUsage[] {
  const data: DailyUsage[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    data.push({
      date: d.toISOString().split('T')[0],
      tasks: Math.floor(Math.random() * 200) + 50,
      tokens: Math.floor(Math.random() * 500000) + 100000,
      cost: parseFloat((Math.random() * 80 + 20).toFixed(2)),
    });
  }
  return data;
}

const MOCK_DAILY_USAGE = generateDailyData(30);

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function BillingUsagePage() {
  const [dateRange, setDateRange] = useState<'7d' | '14d' | '30d'>('30d');

  const daysMap = { '7d': 7, '14d': 14, '30d': 30 };
  const displayDays = daysMap[dateRange];

  const filteredDaily = useMemo(
    () => MOCK_DAILY_USAGE.slice(-displayDays),
    [displayDays],
  );

  const chartData = useMemo(
    () =>
      filteredDaily.map((d) => ({
        date: formatDate(d.date),
        Tasks: d.tasks,
        Cost: d.cost,
      })),
    [filteredDaily],
  );

  const totalTasks = MOCK_AGENT_USAGE.reduce((s, a) => s + a.tasks, 0);
  const totalTokens = MOCK_AGENT_USAGE.reduce((s, a) => s + a.tokens, 0);
  const totalCost = MOCK_AGENT_USAGE.reduce((s, a) => s + a.cost, 0);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track usage breakdown by agent, tasks, tokens, and cost.
        </p>
      </div>

      {/* Sub-navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {billingTabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                tab.href === '/billing/usage'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Tasks</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatNumber(totalTasks)}</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
              <Zap className="w-5 h-5 text-blue-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Tokens</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatNumber(totalTokens)}</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50">
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Cost</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(totalCost)}</p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-50">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Daily Usage Chart */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Daily Usage</h2>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            {(['7d', '14d', '30d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  dateRange === range
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
                )}
              >
                {range === '7d' ? '7 Days' : range === '14d' ? '14 Days' : '30 Days'}
              </button>
            ))}
          </div>
        </div>
        <div className="p-6">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                label={{ value: 'Tasks', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#9ca3af' } }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                label={{ value: 'Cost ($)', angle: 90, position: 'insideRight', style: { fontSize: 11, fill: '#9ca3af' } }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar yAxisId="left" dataKey="Tasks" fill="#3b82f6" radius={[3, 3, 0, 0]} />
              <Bar yAxisId="right" dataKey="Cost" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Per-Agent Usage Table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Usage by Agent</h2>
          </div>
          <p className="text-xs text-gray-400 mt-1">Current billing period breakdown</p>
        </div>

        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Agent</th>
                  <th className="text-right py-2.5 pr-4 font-medium text-gray-500">Tasks</th>
                  <th className="text-right py-2.5 pr-4 font-medium text-gray-500">Tokens</th>
                  <th className="text-right py-2.5 pr-4 font-medium text-gray-500">Cost</th>
                  <th className="text-right py-2.5 font-medium text-gray-500">% of Total</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_AGENT_USAGE.map((agent) => {
                  const costPercent = totalCost > 0 ? (agent.cost / totalCost) * 100 : 0;
                  return (
                    <tr key={agent.agentId} className="border-b border-gray-50 last:border-0">
                      <td className="py-3 pr-4 font-medium text-gray-900">{agent.agentName}</td>
                      <td className="py-3 pr-4 text-right text-gray-600">{formatNumber(agent.tasks)}</td>
                      <td className="py-3 pr-4 text-right text-gray-600">{formatNumber(agent.tokens)}</td>
                      <td className="py-3 pr-4 text-right font-medium text-gray-900">{formatCurrency(agent.cost)}</td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-2 rounded-full bg-gray-100 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-primary-500"
                              style={{ width: `${costPercent}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500 w-10 text-right">
                            {costPercent.toFixed(1)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-gray-200">
                  <td className="py-3 pr-4 font-semibold text-gray-900">Total</td>
                  <td className="py-3 pr-4 text-right font-semibold text-gray-900">{formatNumber(totalTasks)}</td>
                  <td className="py-3 pr-4 text-right font-semibold text-gray-900">{formatNumber(totalTokens)}</td>
                  <td className="py-3 pr-4 text-right font-semibold text-gray-900">{formatCurrency(totalCost)}</td>
                  <td className="py-3 text-right font-semibold text-gray-900">100%</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
