'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Filter,
  Loader2,
  AlertCircle,
  Clock,
  PlayCircle,
  CheckCircle2,
  XCircle,
  PauseCircle,
  ListTodo,
  AlertTriangle,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getExecutions, getHumanTasks } from '@/lib/api/workflows.api';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import { useTaskQueue } from '@/lib/hooks/useTaskQueue';
import { TaskDrawer } from '@/components/tasks/TaskDrawer';
import type { WorkflowExecution, WorkflowStatus, HumanTask } from '@/lib/types/workflow.types';

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

const priorityColors: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800',
  MEDIUM: 'bg-amber-100 text-amber-800',
  HIGH: 'bg-red-100 text-red-800',
  CRITICAL: 'bg-red-200 text-red-900',
};

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'FAILED', label: 'Failed' },
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

export default function LiveQueuePage() {
  const router = useRouter();

  // WebSocket live updates -- invalidates react-query caches on real-time events
  const { status: wsStatus } = useTaskQueue();

  const [statusFilter, setStatusFilter] = useState('');
  const [agentFilter, setAgentFilter] = useState('');

  // Task drawer state
  const [drawerTaskId, setDrawerTaskId] = useState<string | null>(null);

  // Fetch executions
  const {
    data: executions = [],
    isLoading: executionsLoading,
    isError: executionsError,
  } = useQuery({
    queryKey: ['executions', statusFilter, agentFilter],
    queryFn: () =>
      getExecutions({
        ...(statusFilter ? { status: statusFilter as WorkflowStatus } : {}),
        ...(agentFilter ? { agentId: agentFilter } : {}),
      }),
    refetchInterval: 10000,
  });

  // Fetch human tasks (pending)
  const {
    data: humanTasks = [],
    isLoading: tasksLoading,
    isError: tasksError,
  } = useQuery({
    queryKey: ['humanTasks'],
    queryFn: () => getHumanTasks({ status: 'PENDING' }),
    refetchInterval: 15000,
  });

  // Fetch subscribed agents for agent filter dropdown
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

  // Status summary counts
  const statusCounts = useMemo(() => {
    const running = executions.filter((e) => e.status === 'RUNNING').length;
    const pending = executions.filter((e) => e.status === 'PENDING').length;
    const completed = executions.filter((e) => e.status === 'COMPLETED').length;
    const failed = executions.filter((e) => e.status === 'FAILED').length;
    return { running, pending, completed, failed };
  }, [executions]);

  const isLoading = executionsLoading || tasksLoading;
  const isError = executionsError || tasksError;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Queue</h1>
          <p className="text-sm text-gray-500 mt-1">
            Monitor running workflows and pending human tasks in real-time.
          </p>
        </div>
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium mt-1',
            wsStatus === 'connected'
              ? 'bg-green-50 text-green-700'
              : wsStatus === 'connecting'
                ? 'bg-amber-50 text-amber-700'
                : 'bg-gray-100 text-gray-500',
          )}
        >
          <span className="relative flex h-2 w-2">
            {wsStatus === 'connected' && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            )}
            <span
              className={cn(
                'relative inline-flex rounded-full h-2 w-2',
                wsStatus === 'connected'
                  ? 'bg-green-500'
                  : wsStatus === 'connecting'
                    ? 'bg-amber-500'
                    : 'bg-gray-400',
              )}
            />
          </span>
          {wsStatus === 'connected'
            ? 'Live'
            : wsStatus === 'connecting'
              ? 'Connecting'
              : 'Offline'}
        </span>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Agent Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
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
            onChange={(e) => setStatusFilter(e.target.value)}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Status Summary Pills */}
      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
          </span>
          {statusCounts.running} RUNNING
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 text-gray-700 text-xs font-medium">
          <Clock className="w-3 h-3" />
          {statusCounts.pending} PENDING
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 text-green-700 text-xs font-medium">
          <CheckCircle2 className="w-3 h-3" />
          {statusCounts.completed} COMPLETED
        </span>
        {statusCounts.failed > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 text-red-700 text-xs font-medium">
            <XCircle className="w-3 h-3" />
            {statusCounts.failed} FAILED
          </span>
        )}
      </div>

      {/* Global Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading task queue...</p>
        </div>
      )}

      {/* Global Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load task queue</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* ============================================================ */}
          {/* Running Tasks Table                                          */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <PlayCircle className="w-5 h-5 text-primary-600" />
              <h2 className="text-base font-semibold text-gray-900">Workflow Executions</h2>
              <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                {executions.length}
              </span>
            </div>

            {executions.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                    <PlayCircle className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">No executions found</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {statusFilter
                      ? 'Try adjusting your filters.'
                      : 'No workflow executions are running or queued.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 bg-gray-50/50">
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Agent</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Current Step
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Progress
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Duration
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Started
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {executions.map((execution) => (
                        <tr
                          key={execution.id}
                          onClick={() => router.push(`/tasks/${execution.id}`)}
                          className="border-b border-gray-50 last:border-0 hover:bg-gray-50 cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-4 font-medium text-gray-900">
                            {agentNameMap[execution.agentId] || execution.agentId}
                          </td>
                          <td className="py-3 px-4 text-gray-600">
                            {execution.currentStep || '--'}
                          </td>
                          <td className="py-3 px-4 text-gray-600">
                            <span className="text-xs">
                              {execution.completedSteps}/{execution.stepCount} steps
                            </span>
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
                              {execution.status === 'RUNNING' && (
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                                </span>
                              )}
                              {execution.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-gray-500 text-xs">
                            {execution.startedAt
                              ? formatTimeAgo(execution.startedAt)
                              : formatTimeAgo(execution.createdAt)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>

          {/* ============================================================ */}
          {/* Pending Human Tasks                                          */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <ListTodo className="w-5 h-5 text-primary-600" />
              <h2 className="text-base font-semibold text-gray-900">Pending Human Tasks</h2>
              <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                {humanTasks.length}
              </span>
            </div>

            {humanTasks.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                    <ListTodo className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">No pending tasks</p>
                  <p className="text-xs text-gray-400 mt-1">
                    All human review tasks have been resolved.
                  </p>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 bg-gray-50/50">
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Agent</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Task Title
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">
                          Priority
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Due</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-500">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {humanTasks.map((task) => (
                        <tr
                          key={task.id}
                          onClick={() => setDrawerTaskId(task.id)}
                          className="border-b border-gray-50 last:border-0 hover:bg-gray-50 cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-4 font-medium text-gray-900">
                            {task.agentId
                              ? agentNameMap[task.agentId] || task.agentId
                              : '--'}
                          </td>
                          <td className="py-3 px-4 text-gray-700">{task.title}</td>
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
                          <td className="py-3 px-4 text-gray-500 text-xs">
                            {formatRelativeTime(task.dueAt)}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setDrawerTaskId(task.id);
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              Review
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </>
      )}

      {/* Task Resolution Drawer */}
      <TaskDrawer
        taskId={drawerTaskId}
        onClose={() => setDrawerTaskId(null)}
      />
    </div>
  );
}
