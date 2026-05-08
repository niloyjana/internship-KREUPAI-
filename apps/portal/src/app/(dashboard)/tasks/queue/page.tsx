'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Filter,
  Loader2,
  AlertCircle,
  Clock,
  ListTodo,
  ChevronLeft,
  ChevronRight,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getHumanTasks } from '@/lib/api/workflows.api';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import type { HumanTask, TaskStatus } from '@/lib/types/workflow.types';

/* ------------------------------------------------------------------ */
/*  Color maps                                                         */
/* ------------------------------------------------------------------ */

const priorityColors: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800',
  MEDIUM: 'bg-amber-100 text-amber-800',
  HIGH: 'bg-red-100 text-red-800',
  CRITICAL: 'bg-red-200 text-red-900',
};

const taskStatusColors: Record<TaskStatus, string> = {
  PENDING: 'bg-gray-100 text-gray-800',
  IN_PROGRESS: 'bg-blue-100 text-blue-800',
  COMPLETED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  EXPIRED: 'bg-amber-100 text-amber-800',
};

const PRIORITY_OPTIONS = [
  { value: '', label: 'All Priorities' },
  { value: 'CRITICAL', label: 'Critical' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '--';
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return 'Overdue';
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `in ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24) return `in ${hours}h ${remainingMinutes}m`;
  const days = Math.floor(hours / 24);
  return `in ${days}d`;
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function TaskQueuePage() {
  const [priorityFilter, setPriorityFilter] = useState('');
  const [agentFilter, setAgentFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Fetch pending/in-progress tasks
  const {
    data: tasks = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['humanTasks', 'queue', agentFilter, page],
    queryFn: () =>
      getHumanTasks({
        status: 'PENDING' as TaskStatus,
        ...(agentFilter ? { agentId: agentFilter } : {}),
        page,
        pageSize,
      }),
    refetchInterval: 15000,
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

  // Client-side priority filter
  const filteredTasks = useMemo(() => {
    if (!priorityFilter) return tasks;
    return tasks.filter((t) => t.priority === priorityFilter);
  }, [tasks, priorityFilter]);

  // Summary counts
  const summaryCounts = useMemo(() => {
    const critical = tasks.filter((t) => t.priority === 'CRITICAL').length;
    const high = tasks.filter((t) => t.priority === 'HIGH').length;
    const medium = tasks.filter((t) => t.priority === 'MEDIUM').length;
    const low = tasks.filter((t) => t.priority === 'LOW').length;
    return { critical, high, medium, low };
  }, [tasks]);

  const totalPages = Math.max(1, Math.ceil(filteredTasks.length / pageSize));

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Task Queue</h1>
        <p className="text-sm text-gray-500 mt-1">
          View and manage pending tasks awaiting human review.
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

        {/* Priority Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
              setPage(1);
            }}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            {PRIORITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary Pills */}
      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 text-gray-700 text-xs font-medium">
          <ListTodo className="w-3 h-3" />
          {tasks.length} Pending
        </span>
        {summaryCounts.critical > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 text-red-700 text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
            </span>
            {summaryCounts.critical} Critical
          </span>
        )}
        {summaryCounts.high > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 text-red-700 text-xs font-medium">
            {summaryCounts.high} High
          </span>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading task queue...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load task queue</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && filteredTasks.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <ListTodo className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No pending tasks</p>
            <p className="text-xs text-gray-400 mt-1">
              {priorityFilter || agentFilter
                ? 'Try adjusting your filters.'
                : 'All tasks have been processed.'}
            </p>
          </div>
        </div>
      )}

      {/* Task Table */}
      {!isLoading && !isError && filteredTasks.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Title</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Agent</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Priority</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Due</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Created</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredTasks.map((task) => (
                  <tr
                    key={task.id}
                    className="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors"
                  >
                    <td className="py-3 px-4 font-medium text-gray-900 max-w-[240px] truncate">
                      {task.title}
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {task.agentId ? agentNameMap[task.agentId] || task.agentId : '--'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                          priorityColors[task.priority] || 'bg-gray-100 text-gray-800',
                        )}
                      >
                        {task.priority === 'CRITICAL' && (
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                          </span>
                        )}
                        {task.priority}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                          taskStatusColors[task.status],
                        )}
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {formatRelativeTime(task.dueAt)}
                    </td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {formatTimeAgo(task.createdAt)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <a
                        href={`/tasks/human-tasks/${task.id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Review
                      </a>
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
                Page {page} of {totalPages} ({filteredTasks.length} tasks)
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
