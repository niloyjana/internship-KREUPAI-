'use client';

import { useState, useMemo, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  Search,
  Filter,
  FileText,
  Download,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAuditLog } from '@/lib/api/analytics.api';
import type { AuditLogEntry } from '@/lib/types/analytics.types';
import { PieChart } from '@/components/charts/PieChart';
import { BarChart } from '@/components/charts/BarChart';
import { AreaChart } from '@/components/charts/AreaChart';

/* ------------------------------------------------------------------ */
/*  Mock data for charts (used until real API returns data)            */
/* ------------------------------------------------------------------ */

const MOCK_ACTOR_DISTRIBUTION = [
  { name: 'User', value: 342, color: '#3b82f6' },
  { name: 'AI Agent', value: 1248, color: '#8b5cf6' },
  { name: 'System', value: 186, color: '#6b7280' },
];

const MOCK_ACTION_BREAKDOWN = [
  { action: 'task.created', count: 485 },
  { action: 'task.completed', count: 412 },
  { action: 'agent.invoked', count: 389 },
  { action: 'workflow.started', count: 234 },
  { action: 'escalation.created', count: 87 },
  { action: 'config.updated', count: 62 },
  { action: 'user.login', count: 54 },
  { action: 'task.failed', count: 38 },
];

const MOCK_ACTIVITY_TIMELINE = Array.from({ length: 14 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (13 - i));
  return {
    date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    userActions: Math.floor(Math.random() * 30) + 10,
    agentActions: Math.floor(Math.random() * 120) + 40,
    systemActions: Math.floor(Math.random() * 20) + 5,
  };
});

const MOCK_ENTITY_DISTRIBUTION = [
  { name: 'Task', value: 892, color: '#3b82f6' },
  { name: 'Workflow', value: 312, color: '#10b981' },
  { name: 'Agent', value: 245, color: '#8b5cf6' },
  { name: 'User', value: 118, color: '#f59e0b' },
  { name: 'Config', value: 62, color: '#06b6d4' },
  { name: 'Integration', value: 47, color: '#f97316' },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatTimestamp(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getDefaultDateRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 7);
  return {
    from: from.toISOString().split('T')[0],
    to: to.toISOString().split('T')[0],
  };
}

const actorTypeBadgeStyles: Record<string, { bg: string; text: string }> = {
  USER: { bg: 'bg-blue-50', text: 'text-blue-700' },
  AI_AGENT: { bg: 'bg-purple-50', text: 'text-purple-700' },
  SYSTEM: { bg: 'bg-gray-100', text: 'text-gray-600' },
};

const ACTOR_TYPE_OPTIONS = [
  { value: '', label: 'All Actor Types' },
  { value: 'USER', label: 'User' },
  { value: 'AI_AGENT', label: 'AI Agent' },
  { value: 'SYSTEM', label: 'System' },
];

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

export default function AnalyticsCompliancePage() {
  const defaultRange = getDefaultDateRange();
  const [fromDate, setFromDate] = useState(defaultRange.from);
  const [toDate, setToDate] = useState(defaultRange.to);
  const [actorType, setActorType] = useState('');
  const [entityType, setEntityType] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  const pageSize = 20;

  // Fetch audit log
  const {
    data: auditData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['auditLog', fromDate, toDate, actorType, entityType, search, page],
    queryFn: () =>
      getAuditLog({
        from: fromDate,
        to: toDate,
        ...(actorType ? { actorType: actorType as 'USER' | 'AI_AGENT' | 'SYSTEM' } : {}),
        ...(entityType ? { entityType } : {}),
        ...(search ? { search } : {}),
        page,
        pageSize,
      }),
  });

  // Derive actor/entity distributions from real data if available,
  // otherwise use mock data
  const actorDistribution = useMemo(() => {
    if (auditData && auditData.entries.length > 0) {
      const counts: Record<string, number> = {};
      auditData.entries.forEach((e) => {
        counts[e.actorType] = (counts[e.actorType] || 0) + 1;
      });
      const colorMap: Record<string, string> = {
        USER: '#3b82f6',
        AI_AGENT: '#8b5cf6',
        SYSTEM: '#6b7280',
      };
      return Object.entries(counts).map(([name, value]) => ({
        name: name === 'AI_AGENT' ? 'AI Agent' : name.charAt(0) + name.slice(1).toLowerCase(),
        value,
        color: colorMap[name] || '#3b82f6',
      }));
    }
    return MOCK_ACTOR_DISTRIBUTION;
  }, [auditData]);

  const usingMockData = !auditData || auditData.entries.length === 0;

  // Summary KPIs from mock data
  const totalEvents = useMemo(() => {
    if (auditData) return auditData.meta.totalItems;
    return MOCK_ACTOR_DISTRIBUTION.reduce((s, d) => s + d.value, 0);
  }, [auditData]);

  function toggleExpand(id: string) {
    setExpandedRow((prev) => (prev === id ? null : id));
  }

  /* ---------------------------------------------------------------- */
  /*  Export handlers                                                   */
  /* ---------------------------------------------------------------- */

  const handleExportCSV = useCallback(() => {
    setExportMenuOpen(false);

    const entries = auditData?.entries || [];
    if (entries.length === 0) {
      alert('No data to export. Adjust your filters and try again.');
      return;
    }

    // Build CSV
    const headers = ['Timestamp', 'Actor Type', 'Actor ID', 'Action', 'Entity Type', 'Entity ID', 'Metadata'];
    const rows = entries.map((entry) => [
      formatTimestamp(entry.timestamp),
      entry.actorType,
      entry.actorId,
      entry.action,
      entry.entityType,
      entry.entityId,
      entry.metadata ? JSON.stringify(entry.metadata) : '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) =>
        row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','),
      ),
    ].join('\n');

    // Trigger download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `compliance-report-${fromDate}-to-${toDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [auditData, fromDate, toDate]);

  const handleExportPDF = useCallback(() => {
    setExportMenuOpen(false);

    // Use window.print() with a print-optimized view
    // Add ?format=pdf to indicate PDF export was triggered
    const url = new URL(window.location.href);
    url.searchParams.set('format', 'pdf');
    window.history.replaceState({}, '', url.toString());

    window.print();

    // Remove the format param after printing
    url.searchParams.delete('format');
    window.history.replaceState({}, '', url.toString());
  }, []);

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
                tab.href === '/analytics/compliance'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
        {/* Date Range */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={fromDate}
            onChange={(e) => {
              setFromDate(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
          <span className="text-sm text-gray-400">to</span>
          <input
            type="date"
            value={toDate}
            onChange={(e) => {
              setToDate(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Actor Type */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={actorType}
            onChange={(e) => {
              setActorType(e.target.value);
              setPage(1);
            }}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            {ACTOR_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Entity Type */}
        <input
          type="text"
          placeholder="Entity type..."
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
        />

        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search compliance log..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Export Dropdown */}
        <div className="relative" ref={exportMenuRef}>
          <button
            onClick={() => setExportMenuOpen((prev) => !prev)}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            <Download className="w-4 h-4" />
            Export
            <ChevronDown className={cn('w-4 h-4 transition-transform', exportMenuOpen && 'rotate-180')} />
          </button>

          {exportMenuOpen && (
            <>
              {/* Click-away overlay */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setExportMenuOpen(false)}
              />
              <div className="absolute right-0 top-full mt-1 z-20 w-40 rounded-lg border border-gray-200 bg-white shadow-lg py-1">
                <button
                  onClick={handleExportCSV}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  <FileText className="w-4 h-4 text-gray-400" />
                  Export as CSV
                </button>
                <button
                  onClick={handleExportPDF}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  <Download className="w-4 h-4 text-gray-400" />
                  Export as PDF
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading compliance log...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load compliance log</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Compliance Visualizations and Table */}
      <>
        {/* Mock data banner */}
        {usingMockData && !isLoading && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
            <p className="text-xs text-blue-700">
              Showing sample data for visualization preview. Charts will update automatically when live data is available.
            </p>
          </div>
        )}

        {/* KPI Cards */}
        {!isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Total Events
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {totalEvents.toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Actor Types
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {actorDistribution.length}
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50">
                  <Users className="w-5 h-5 text-purple-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Compliance Status
                  </p>
                  <p className="text-2xl font-bold text-green-600 mt-1">
                    Healthy
                  </p>
                </div>
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-50">
                  <ShieldCheck className="w-5 h-5 text-green-600" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Charts Row: Activity Timeline + Actor Distribution */}
        {!isLoading && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Activity Timeline Area Chart */}
            <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Activity Timeline</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Daily compliance events by actor type</p>
              </div>
              <div className="p-6">
                <AreaChart
                  data={MOCK_ACTIVITY_TIMELINE}
                  xAxisKey="date"
                  series={[
                    { dataKey: 'agentActions', label: 'AI Agent', color: '#8b5cf6', stackId: 'activity' },
                    { dataKey: 'userActions', label: 'User', color: '#3b82f6', stackId: 'activity' },
                    { dataKey: 'systemActions', label: 'System', color: '#6b7280', stackId: 'activity' },
                  ]}
                  height={300}
                  yAxisLabel="Events"
                />
              </div>
            </div>

            {/* Actor Distribution Donut */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Actor Distribution</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Events by actor type</p>
              </div>
              <div className="p-6">
                <PieChart
                  data={actorDistribution}
                  height={300}
                  innerRadius={55}
                  outerRadius={90}
                  showLabels
                  centerLabel="Events"
                  centerValue={totalEvents.toLocaleString()}
                />
              </div>
            </div>
          </div>
        )}

        {/* Charts Row: Action Breakdown + Entity Distribution */}
        {!isLoading && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Top Actions Bar Chart */}
            <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Top Actions</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Most frequent compliance actions</p>
              </div>
              <div className="p-6">
                <BarChart
                  data={MOCK_ACTION_BREAKDOWN}
                  xAxisKey="action"
                  series={[
                    { dataKey: 'count', label: 'Occurrences', color: '#3b82f6' },
                  ]}
                  height={300}
                  yAxisLabel="Count"
                />
              </div>
            </div>

            {/* Entity Type Distribution */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary-600" />
                  <h2 className="text-base font-semibold text-gray-900">Entity Types</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">Distribution by entity type</p>
              </div>
              <div className="p-6">
                <PieChart
                  data={MOCK_ENTITY_DISTRIBUTION}
                  height={300}
                  innerRadius={55}
                  outerRadius={90}
                  showLabels
                  valueFormatter={(v) => v.toLocaleString()}
                />
              </div>
            </div>
          </div>
        )}

        {/* Compliance Table */}
        {auditData && (
          <>
            {auditData.entries.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                    <FileText className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">No compliance entries found</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Try adjusting your filters or date range.
                  </p>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary-600" />
                    <h2 className="text-base font-semibold text-gray-900">Compliance Log Entries</h2>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 bg-gray-50/50">
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Timestamp</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Actor Type</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Actor ID</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Action</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Entity Type
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Entity ID</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-500">Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditData.entries.map((entry) => {
                        const badgeStyle = actorTypeBadgeStyles[entry.actorType] || {
                          bg: 'bg-gray-100',
                          text: 'text-gray-600',
                        };
                        const isExpanded = expandedRow === entry.id;

                        return (
                          <>
                            <tr
                              key={entry.id}
                              className="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors"
                            >
                              <td className="py-3 px-4 text-gray-600 text-xs whitespace-nowrap">
                                {formatTimestamp(entry.timestamp)}
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={cn(
                                    'inline-block px-2 py-0.5 rounded-full text-xs font-medium',
                                    badgeStyle.bg,
                                    badgeStyle.text,
                                  )}
                                >
                                  {entry.actorType}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-gray-700 font-mono text-xs">
                                {entry.actorId}
                              </td>
                              <td className="py-3 px-4 font-medium text-gray-900">
                                {entry.action}
                              </td>
                              <td className="py-3 px-4 text-gray-600">{entry.entityType}</td>
                              <td className="py-3 px-4 text-gray-600 font-mono text-xs">
                                {entry.entityId}
                              </td>
                              <td className="py-3 px-4 text-right">
                                <button
                                  onClick={() => toggleExpand(entry.id)}
                                  className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                                >
                                  {isExpanded ? (
                                    <>
                                      Hide
                                      <ChevronUp className="w-3.5 h-3.5" />
                                    </>
                                  ) : (
                                    <>
                                      View
                                      <ChevronDown className="w-3.5 h-3.5" />
                                    </>
                                  )}
                                </button>
                              </td>
                            </tr>

                            {/* Expanded details row */}
                            {isExpanded && (
                              <tr key={`${entry.id}-detail`} className="border-b border-gray-50">
                                <td colSpan={7} className="px-4 py-3 bg-gray-50">
                                  <div className="text-xs text-gray-600">
                                    <p className="font-medium text-gray-700 mb-1">Metadata:</p>
                                    <pre className="bg-white border border-gray-200 rounded-lg p-3 overflow-x-auto text-xs text-gray-600 max-h-48">
                                      {entry.metadata
                                        ? JSON.stringify(entry.metadata, null, 2)
                                        : 'No metadata available'}
                                    </pre>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {auditData.meta.totalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                    <p className="text-xs text-gray-400">
                      Page {auditData.meta.page} of {auditData.meta.totalPages} (
                      {auditData.meta.totalItems} entries)
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page <= 1}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                        Previous
                      </button>
                      <button
                        onClick={() =>
                          setPage((p) => Math.min(auditData.meta.totalPages, p + 1))
                        }
                        disabled={page >= auditData.meta.totalPages}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Next
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </>
    </div>
  );
}
