'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  BarChart3,
  Activity,
  Clock,
  TrendingUp,
  DollarSign,
  Filter,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAgentPerformance } from '@/lib/api/analytics.api';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import type { AgentPerformance, DailyBreakdown } from '@/lib/types/analytics.types';
import { BarChart } from '@/components/charts/BarChart';
import { LineChart } from '@/components/charts/LineChart';
import { AreaChart } from '@/components/charts/AreaChart';
import { PieChart } from '@/components/charts/PieChart';

/* ------------------------------------------------------------------ */
/*  Mock data for charts (used until real API returns data)            */
/* ------------------------------------------------------------------ */

const MOCK_DAILY_BREAKDOWN: DailyBreakdown[] = Array.from({ length: 14 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (13 - i));
  const completed = Math.floor(Math.random() * 40) + 20;
  const escalated = Math.floor(Math.random() * 8);
  const failed = Math.floor(Math.random() * 4);
  return {
    date: d.toISOString().split('T')[0],
    tasksCompleted: completed,
    tasksEscalated: escalated,
    tasksFailed: failed,
    costUsd: parseFloat((Math.random() * 12 + 2).toFixed(2)),
  };
});

const MOCK_PERFORMANCE: AgentPerformance = {
  taskCount: MOCK_DAILY_BREAKDOWN.reduce(
    (s, d) => s + d.tasksCompleted + d.tasksEscalated + d.tasksFailed,
    0,
  ),
  stpRate: 0.87,
  escalationRate: 0.06,
  avgDurationMs: 34500,
  totalCostUsd: MOCK_DAILY_BREAKDOWN.reduce((s, d) => s + d.costUsd, 0),
  dailyBreakdown: MOCK_DAILY_BREAKDOWN,
};

/** Mock top escalation/issue data for the Top Issues Table (P7 Screen 8). */
const MOCK_TOP_ISSUES = [
  { issue: 'No PO found', count: 38, pctOfTotal: 2.1, avgResolutionMs: 15120000 },
  { issue: 'Price variance exceeded', count: 28, pctOfTotal: 1.5, avgResolutionMs: 6480000 },
  { issue: 'New vendor hold', count: 22, pctOfTotal: 1.2, avgResolutionMs: 23040000 },
  { issue: 'Duplicate invoice flagged', count: 14, pctOfTotal: 0.8, avgResolutionMs: 3600000 },
  { issue: 'Bank detail change detected', count: 9, pctOfTotal: 0.5, avgResolutionMs: 28800000 },
];

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

function formatDuration(ms: number): string {
  if (!ms || ms <= 0) return '--';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
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

export default function AnalyticsPerformancePage() {
  const defaultRange = getDefaultDateRange();
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [fromDate, setFromDate] = useState(defaultRange.from);
  const [toDate, setToDate] = useState(defaultRange.to);

  // Fetch subscribed agents for the dropdown
  const { data: subscribedAgents = [] } = useQuery({
    queryKey: ['subscribedAgents'],
    queryFn: getSubscribedAgents,
  });

  // Auto-select first agent if none selected
  const effectiveAgentId = selectedAgentId || subscribedAgents[0]?.agentId || '';

  // Fetch performance data
  const {
    data: apiPerformance,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['agentPerformance', effectiveAgentId, fromDate, toDate],
    queryFn: () => getAgentPerformance(effectiveAgentId, { from: fromDate, to: toDate }),
    enabled: !!effectiveAgentId,
  });

  // Use API data when available, fallback to mock data for visualization
  const performance = useMemo(() => {
    if (apiPerformance && apiPerformance.dailyBreakdown.length > 0) {
      return apiPerformance;
    }
    // When no real data, use mock data so charts render
    return MOCK_PERFORMANCE;
  }, [apiPerformance]);

  // Whether we're using mock data
  const usingMockData = !apiPerformance || apiPerformance.dailyBreakdown.length === 0;

  // Prepare chart data
  const dailyChartData = useMemo(() => {
    return performance.dailyBreakdown.map((day) => ({
      date: formatDate(day.date),
      Completed: day.tasksCompleted,
      Escalated: day.tasksEscalated,
      Failed: day.tasksFailed,
      costUsd: day.costUsd,
    }));
  }, [performance]);

  // Status distribution for pie chart
  const statusDistribution = useMemo(() => {
    const totals = performance.dailyBreakdown.reduce(
      (acc, day) => ({
        completed: acc.completed + day.tasksCompleted,
        escalated: acc.escalated + day.tasksEscalated,
        failed: acc.failed + day.tasksFailed,
      }),
      { completed: 0, escalated: 0, failed: 0 },
    );
    return [
      { name: 'Completed', value: totals.completed, color: '#10b981' },
      { name: 'Escalated', value: totals.escalated, color: '#f59e0b' },
      { name: 'Failed', value: totals.failed, color: '#ef4444' },
    ];
  }, [performance]);

  // Agent name lookup
  const agentNameMap = useMemo(() => {
    const map: Record<string, string> = {};
    subscribedAgents.forEach((sa) => {
      map[sa.agentId] = sa.agent?.name || sa.agentId;
    });
    return map;
  }, [subscribedAgents]);

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
                tab.href === '/analytics/performance'
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
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Agent Selector */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            <option value="">
              {subscribedAgents.length > 0 ? 'Select Agent' : 'No agents available'}
            </option>
            {subscribedAgents.map((sa) => (
              <option key={sa.agentId} value={sa.agentId}>
                {sa.agent?.name || sa.agentId}
              </option>
            ))}
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

      {/* No agent selected */}
      {!effectiveAgentId && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
            <BarChart3 className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-sm font-medium text-gray-600">Select an agent to view performance</p>
          <p className="text-xs text-gray-400 mt-1">
            Subscribe to agents from the workforce catalog to get started.
          </p>
        </div>
      )}

      {/* Loading */}
      {effectiveAgentId && isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading performance data...</p>
        </div>
      )}

      {/* Error */}
      {effectiveAgentId && isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load performance data</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Performance Data */}
      {effectiveAgentId && performance && (
        <>
          {/* Mock data banner */}
          {usingMockData && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
              <p className="text-xs text-blue-700">
                Showing sample data for visualization preview. Charts will update automatically when
                live data is available.
              </p>
            </div>
          )}

          {/* Headline KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Total Tasks */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Total Tasks
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {performance.taskCount.toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
                  <Activity className="w-5 h-5 text-blue-600" />
                </div>
              </div>
            </div>

            {/* STP Rate */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    STP Rate
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatPercent(performance.stpRate)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-50">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                </div>
              </div>
            </div>

            {/* Escalation Rate */}
            <div
              className={cn(
                'bg-white rounded-lg border shadow-sm p-5',
                performance.escalationRate > 0.1 ? 'border-amber-400' : 'border-gray-200',
              )}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Escalation Rate
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatPercent(performance.escalationRate)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-50">
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                </div>
              </div>
            </div>

            {/* Avg Duration */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Avg Duration
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatDuration(performance.avgDurationMs)}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50">
                  <Clock className="w-5 h-5 text-purple-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Charts Row: Task Execution Trend + Status Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Task Execution Trend (stacked bar) */}
            <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Task Execution by Day</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Daily breakdown of completed, escalated, and failed tasks
                </p>
              </div>
              <div className="p-6">
                <BarChart
                  data={dailyChartData}
                  xAxisKey="date"
                  series={[
                    {
                      dataKey: 'Completed',
                      label: 'Completed',
                      color: '#10b981',
                      stackId: 'tasks',
                    },
                    {
                      dataKey: 'Escalated',
                      label: 'Escalated',
                      color: '#f59e0b',
                      stackId: 'tasks',
                    },
                    { dataKey: 'Failed', label: 'Failed', color: '#ef4444', stackId: 'tasks' },
                  ]}
                  height={300}
                  yAxisLabel="Tasks"
                  barRadius={2}
                />
              </div>
            </div>

            {/* Status Distribution (donut) */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Status Distribution</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Overall task outcome breakdown</p>
              </div>
              <div className="p-6">
                <PieChart
                  data={statusDistribution}
                  height={300}
                  innerRadius={60}
                  outerRadius={95}
                  showLabels
                  centerLabel="Total"
                  centerValue={performance.taskCount.toLocaleString()}
                />
              </div>
            </div>
          </div>

          {/* Execution Trend Line Chart */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Completion Trend</h2>
              </div>
              <p className="text-xs text-gray-400 mt-1">Completed tasks over time</p>
            </div>
            <div className="p-6">
              <LineChart
                data={dailyChartData}
                xAxisKey="date"
                series={[
                  { dataKey: 'Completed', label: 'Completed', color: '#10b981' },
                  { dataKey: 'Escalated', label: 'Escalated', color: '#f59e0b', dashed: true },
                ]}
                height={280}
                yAxisLabel="Tasks"
              />
            </div>
          </div>

          {/* Cost Trend Area Chart */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Cost Trend</h2>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  Total: {formatCurrency(performance.totalCostUsd)}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1">Daily LLM cost over the selected period</p>
            </div>
            <div className="p-6">
              <AreaChart
                data={dailyChartData}
                xAxisKey="date"
                series={[{ dataKey: 'costUsd', label: 'Cost (USD)', color: '#8b5cf6' }]}
                height={280}
                yAxisLabel="USD"
                valueFormatter={(v) => formatCurrency(v)}
              />
            </div>
          </div>

          {/* Top Issues Table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Filter className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Top Issues</h2>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Most common escalation reasons and their resolution times
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                      Issue
                    </th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                      Count
                    </th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                      % of Total
                    </th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                      Avg Resolution Time
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_TOP_ISSUES.map((issue) => (
                    <tr
                      key={issue.issue}
                      className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                    >
                      <td className="px-6 py-3 text-sm font-medium text-gray-900">{issue.issue}</td>
                      <td className="px-6 py-3 text-sm text-gray-700 text-right">{issue.count}</td>
                      <td className="px-6 py-3 text-sm text-gray-700 text-right">
                        {issue.pctOfTotal}%
                      </td>
                      <td className="px-6 py-3 text-sm text-gray-700 text-right">
                        {formatDuration(issue.avgResolutionMs)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
