'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  DollarSign,
  Filter,
  TrendingUp,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getCostBreakdown } from '@/lib/api/analytics.api';
import { BarChart } from '@/components/charts/BarChart';
import { PieChart } from '@/components/charts/PieChart';
import { AreaChart } from '@/components/charts/AreaChart';

/* ------------------------------------------------------------------ */
/*  Mock data for charts (used until real API returns data)            */
/* ------------------------------------------------------------------ */

const MOCK_COST_BREAKDOWN = {
  totalCostUsd: 347.82,
  breakdown: [
    { key: 'agent-invoice', label: 'Invoice Processor', costUsd: 124.50, taskCount: 1820, tokenCount: 2450000 },
    { key: 'agent-support', label: 'Support Agent', costUsd: 89.25, taskCount: 945, tokenCount: 1680000 },
    { key: 'agent-analytics', label: 'Analytics Agent', costUsd: 67.30, taskCount: 412, tokenCount: 980000 },
    { key: 'agent-compliance', label: 'Compliance Agent', costUsd: 42.18, taskCount: 287, tokenCount: 620000 },
    { key: 'agent-scheduler', label: 'Scheduler Agent', costUsd: 24.59, taskCount: 156, tokenCount: 340000 },
  ],
};

const MOCK_COST_TREND = Array.from({ length: 14 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (13 - i));
  return {
    date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    cost: parseFloat((Math.random() * 35 + 10).toFixed(2)),
    tokens: Math.floor(Math.random() * 200000 + 80000),
  };
});

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

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

function formatCompactNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
}

function getDefaultDateRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return {
    from: from.toISOString().split('T')[0],
    to: to.toISOString().split('T')[0],
  };
}

/* ------------------------------------------------------------------ */
/*  Sub-navigation Tabs                                                */
/* ------------------------------------------------------------------ */

const analyticsTabs = [
  { label: 'Performance', href: '/analytics/performance' },
  { label: 'Cost', href: '/analytics/cost' },
  { label: 'Compliance', href: '/analytics/compliance' },
];

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function AnalyticsCostPage() {
  const defaultRange = getDefaultDateRange();
  const [groupBy, setGroupBy] = useState<'agent' | 'model'>('agent');
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [fromDate, setFromDate] = useState(defaultRange.from);
  const [toDate, setToDate] = useState(defaultRange.to);

  // Fetch cost breakdown
  const {
    data: apiCostData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['costBreakdown', groupBy, period, fromDate, toDate],
    queryFn: () => getCostBreakdown({ groupBy, period, from: fromDate, to: toDate }),
  });

  // Use API data when available, fallback to mock data for visualization
  const costData = useMemo(() => {
    if (apiCostData && apiCostData.breakdown.length > 0) {
      return apiCostData;
    }
    return MOCK_COST_BREAKDOWN;
  }, [apiCostData]);

  const usingMockData = !apiCostData || apiCostData.breakdown.length === 0;

  // Pie chart data from breakdown
  const pieData = useMemo(() => {
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899', '#ef4444'];
    return costData.breakdown.map((item, idx) => ({
      name: item.label,
      value: item.costUsd,
      color: colors[idx % colors.length],
    }));
  }, [costData]);

  // Bar chart data from breakdown
  const barData = useMemo(() => {
    return costData.breakdown.map((item) => ({
      label: item.label,
      cost: item.costUsd,
      tasks: item.taskCount,
      tokens: item.tokenCount,
    }));
  }, [costData]);

  // Summary KPIs
  const kpis = useMemo(() => {
    const totalTasks = costData.breakdown.reduce((s, b) => s + b.taskCount, 0);
    const totalTokens = costData.breakdown.reduce((s, b) => s + b.tokenCount, 0);
    const avgCostPerTask = totalTasks > 0 ? costData.totalCostUsd / totalTasks : 0;
    return { totalTasks, totalTokens, avgCostPerTask };
  }, [costData]);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">
          Monitor agent performance, costs, and system activity.
        </p>
      </div>

      {/* Sub-navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {analyticsTabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                tab.href === '/analytics/cost'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
        {/* Group By */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as 'agent' | 'model')}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            <option value="agent">Group by Agent</option>
            <option value="model">Group by Model</option>
          </select>
        </div>

        {/* Period */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as 'daily' | 'weekly' | 'monthly')}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        {/* Date Range */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
          <span className="text-sm text-gray-400">to</span>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading cost data...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load cost data</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Cost Data */}
      {costData && (
        <>
          {/* Mock data banner */}
          {usingMockData && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
              <p className="text-xs text-blue-700">
                Showing sample data for visualization preview. Charts will update automatically when live data is available.
              </p>
            </div>
          )}

          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Total Cost
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatCurrency(costData.totalCostUsd)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50">
                  <DollarSign className="w-5 h-5 text-purple-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Total Tasks
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatNumber(kpis.totalTasks)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
                  <Layers className="w-5 h-5 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Avg Cost / Task
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatCurrency(kpis.avgCostPerTask)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-50">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Total Tokens
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatCompactNumber(kpis.totalTokens)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-50">
                  <DollarSign className="w-5 h-5 text-amber-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Charts Row: Cost by Agent Bar + Cost Distribution Pie */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Cost by Agent Bar Chart */}
            <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Cost by {groupBy === 'agent' ? 'Agent' : 'Model'}</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Comparing cost across {groupBy === 'agent' ? 'agents' : 'models'}</p>
              </div>
              <div className="p-6">
                <BarChart
                  data={barData}
                  xAxisKey="label"
                  series={[
                    { dataKey: 'cost', label: 'Cost (USD)', color: '#8b5cf6' },
                  ]}
                  height={300}
                  yAxisLabel="USD"
                  valueFormatter={(v) => formatCurrency(v)}
                />
              </div>
            </div>

            {/* Cost Distribution Donut */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <Layers className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Cost Distribution</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Share of total cost per {groupBy === 'agent' ? 'agent' : 'model'}</p>
              </div>
              <div className="p-6">
                <PieChart
                  data={pieData}
                  height={300}
                  innerRadius={55}
                  outerRadius={90}
                  showLabels
                  centerLabel="Total"
                  centerValue={formatCurrency(costData.totalCostUsd)}
                  valueFormatter={(v) => formatCurrency(v)}
                />
              </div>
            </div>
          </div>

          {/* Cost Trend Area Chart */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Cost Over Time</h2>
              </div>
              <p className="text-xs text-gray-400 mt-1">Daily cost trend across the selected period</p>
            </div>
            <div className="p-6">
              <AreaChart
                data={MOCK_COST_TREND}
                xAxisKey="date"
                series={[
                  { dataKey: 'cost', label: 'Cost (USD)', color: '#8b5cf6' },
                ]}
                height={280}
                yAxisLabel="USD"
                valueFormatter={(v) => formatCurrency(v)}
              />
            </div>
          </div>

          {/* Token Usage Bar Chart */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Token Usage by {groupBy === 'agent' ? 'Agent' : 'Model'}</h2>
              </div>
              <p className="text-xs text-gray-400 mt-1">Token consumption across {groupBy === 'agent' ? 'agents' : 'models'}</p>
            </div>
            <div className="p-6">
              <BarChart
                data={barData}
                xAxisKey="label"
                series={[
                  { dataKey: 'tokens', label: 'Tokens', color: '#06b6d4' },
                ]}
                height={280}
                yAxisLabel="Tokens"
                valueFormatter={(v) => formatCompactNumber(v)}
              />
            </div>
          </div>

          {/* Detailed Breakdown Table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Detailed Breakdown</h2>
              </div>
            </div>

            {costData.breakdown.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <DollarSign className="w-8 h-8 text-gray-300 mb-2" />
                <p className="text-sm text-gray-500">No cost data available for this period.</p>
              </div>
            ) : (
              <div className="p-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Label</th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Cost (USD)
                        </th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Task Count
                        </th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Token Count
                        </th>
                        <th className="text-right py-2.5 font-medium text-gray-500">% of Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costData.breakdown.map((item) => {
                        const percentage =
                          costData.totalCostUsd > 0
                            ? ((item.costUsd / costData.totalCostUsd) * 100).toFixed(1)
                            : '0.0';

                        return (
                          <tr
                            key={item.key}
                            className="border-b border-gray-50 last:border-0"
                          >
                            <td className="py-3 pr-4 font-medium text-gray-900">{item.label}</td>
                            <td className="py-3 pr-4 text-right text-gray-900">
                              {formatCurrency(item.costUsd)}
                            </td>
                            <td className="py-3 pr-4 text-right text-gray-600">
                              {formatNumber(item.taskCount)}
                            </td>
                            <td className="py-3 pr-4 text-right text-gray-600">
                              {formatNumber(item.tokenCount)}
                            </td>
                            <td className="py-3 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <div className="w-16 h-2 rounded-full bg-gray-100 overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-primary-500"
                                    style={{ width: `${Math.min(parseFloat(percentage), 100)}%` }}
                                  />
                                </div>
                                <span className="text-gray-600 text-xs w-12 text-right">
                                  {percentage}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
