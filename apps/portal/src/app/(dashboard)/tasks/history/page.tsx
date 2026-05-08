'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Filter,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  History,
  ChevronLeft,
  ChevronRight,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getExecutions } from '@/lib/api/workflows.api';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import type { WorkflowExecution, WorkflowStatus } from '@/lib/types/workflow.types';

/* ------------------------------------------------------------------ */
/*  Color maps                                                         */
/* ------------------------------------------------------------------ */

const workflowStatusColors: Record<WorkflowStatus, string> = {
  PENDING: 'bg-gray-100 text-gray-800',
  RUNNING: 'bg-blue-100 text-blue-800',
  PAUSED: 'bg-amber-100 text-amber-800',
  COMPLETED: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
  CANCELLED: 'bg-gray-100 text-gray-600',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '--';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function formatTimestamp(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function TaskHistoryPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [agentFilter, setAgentFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Fetch completed/failed executions
  const {
    data: executions = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['executions', 'history', statusFilter || 'COMPLETED,FAILED,CANCELLED', agentFilter, page],
    queryFn: () =>
      getExecutions({
        status: (statusFilter || 'COMPLETED') as WorkflowStatus,
        ...(agentFilter ? { agentId: agentFilter } : {}),
        page,
        pageSize,
      }),
  });

  // Fetch subscribed agents for dropdown
  const { data: subscribedAgents = [] } = useQuery({
    queryKey: ['subscribedAgents'],
    queryFn: getSubscribedAgents,
  });

  // Agent name lookup
  const agentNameMap = useMemo(() => {
    const map: Record<string, string> = {};
    subscribedAgents.forEach((sa) => {
      map[sa.agentId] = sa.agent?.name || sa.agentId;
    });
    return map;
  }, [subscribedAgents]);

  // Client-side search filtering
  const filteredExecutions = useMemo(() => {
    if (!searchQuery.trim()) return executions;
    const q = searchQuery.toLowerCase();
    return executions.filter(
      (e) =>
        e.id.toLowerCase().includes(q) ||
        (agentNameMap[e.agentId] || e.agentId).toLowerCase().includes(q) ||
        (e.currentStep || '').toLowerCase().includes(q),
    );
  }, [executions, searchQuery, agentNameMap]);

  // Summary counts
  const summaryCounts = useMemo(() => {
    const completed = executions.filter((e) => e.status === 'COMPLETED').length;
    const failed = executions.filter((e) => e.status === 'FAILED').length;
    const cancelled = executions.filter((e) => e.status === 'CANCELLED').length;
    return { completed, failed, cancelled };
  }, [executions]);

  const totalPages = Math.max(1, Math.ceil(filteredExecutions.length / pageSize));

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Task History</h1>
        <p className="text-sm text-gray-500 mt-1">
          Review completed and failed workflow executions.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Agent Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={agentFilter}
            onChange={(e) => {
              setAgentFilter(e.target.value);
              setPage(1);
            }}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            <option value="">All Agents</option>
            {subscribedAgents.map((sa) => (
              <option key={sa.agentId} value={sa.agentId}>
                {sa.agent?.name || sa.agentId}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by ID, agent, or step..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>
      </div>

      {/* Summary Pills */}
      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 text-green-700 text-xs font-medium">
          <CheckCircle2 className="w-3 h-3" />
          {summaryCounts.completed} Completed
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 text-red-700 text-xs font-medium">
          <XCircle className="w-3 h-3" />
          {summaryCounts.failed} Failed
        </span>
        {summaryCounts.cancelled > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">
            {summaryCounts.cancelled} Cancelled
          </span>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading task history...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load task history</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && filteredExecutions.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <History className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No history found</p>
            <p className="text-xs text-gray-400 mt-1">
              {statusFilter || agentFilter || searchQuery
                ? 'Try adjusting your filters or search.'
                : 'No completed or failed executions yet.'}
            </p>
          </div>
        </div>
      )}

      {/* History Table */}
      {!isLoading && !isError && filteredExecutions.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Execution ID</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Agent</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Last Step</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Steps</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Duration</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Completed</th>
                </tr>
              </thead>
              <tbody>
                {filteredExecutions.map((execution) => (
                  <tr
                    key={execution.id}
                    className="border-b border-gray-50 last:border-0 hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => {
                      window.location.href = `/tasks/${execution.id}`;
                    }}
                  >
                    <td className="py-3 px-4 text-gray-600 font-mono text-xs">
                      {execution.id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 font-medium text-gray-900">
                      {agentNameMap[execution.agentId] || execution.agentId}
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {execution.currentStep || '--'}
                    </td>
                    <td className="py-3 px-4 text-gray-600 text-xs">
                      {execution.completedSteps}/{execution.stepCount} steps
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {formatDuration(execution.durationMs)}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
                          workflowStatusColors[execution.status],
                        )}
                      >
                        {execution.status === 'COMPLETED' && (
                          <CheckCircle2 className="w-3 h-3" />
                        )}
                        {execution.status === 'FAILED' && <XCircle className="w-3 h-3" />}
                        {execution.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {formatTimestamp(execution.startedAt || execution.createdAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-400">
                Page {page} of {totalPages} ({filteredExecutions.length} executions)
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
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
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
    </div>
  );
}
