'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Bot,
  CheckSquare,
  AlertTriangle,
  DollarSign,
  Bell,
  Loader2,
  AlertCircle,
  Activity,
  ArrowRight,
  Clock,
  ArrowUp,
  ArrowDown,
  Minus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/lib/stores/auth.store';
import { getDashboard } from '@/lib/api/analytics.api';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import { getHumanTasks } from '@/lib/api/workflows.api';
import { useDashboardFeed } from '@/lib/hooks/useDashboardFeed';
import type { DashboardData, AgentBreakdownItem } from '@/lib/types/analytics.types';
import type { HumanTask } from '@/lib/types/workflow.types';

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

const departmentColors: Record<string, { bg: string; text: string }> = {
  finance: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
  hr: { bg: 'bg-violet-50', text: 'text-violet-700' },
  sales: { bg: 'bg-blue-50', text: 'text-blue-700' },
  marketing: { bg: 'bg-pink-50', text: 'text-pink-700' },
  operations: { bg: 'bg-amber-50', text: 'text-amber-700' },
  engineering: { bg: 'bg-cyan-50', text: 'text-cyan-700' },
  legal: { bg: 'bg-slate-100', text: 'text-slate-700' },
  support: { bg: 'bg-orange-50', text: 'text-orange-700' },
};

const priorityIcons: Record<string, { color: string }> = {
  LOW: { color: 'text-green-500' },
  MEDIUM: { color: 'text-amber-500' },
  HIGH: { color: 'text-red-500' },
  CRITICAL: { color: 'text-red-700' },
};

/* ------------------------------------------------------------------ */
/*  KPI Change Indicator                                               */
/* ------------------------------------------------------------------ */

/** Compute the percentage change between a current and previous value. */
function computeChange(
  current: number,
  previous: number,
): { pct: number; direction: 'up' | 'down' | 'flat' } {
  if (previous === 0 && current === 0) return { pct: 0, direction: 'flat' };
  if (previous === 0) return { pct: 100, direction: 'up' };
  const pct = ((current - previous) / previous) * 100;
  if (Math.abs(pct) < 0.5) return { pct: 0, direction: 'flat' };
  return { pct: Math.round(pct), direction: pct > 0 ? 'up' : 'down' };
}

/**
 * Renders a small "+12%" / "-5%" badge with an arrow icon.
 * `invertColor` flips the meaning so "up" is bad (red) for metrics like cost, failures, or escalations.
 */
function ChangeIndicator({
  current,
  previous,
  invertColor = false,
}: {
  current: number;
  previous: number;
  invertColor?: boolean;
}) {
  const { pct, direction } = computeChange(current, previous);

  const colorMap = {
    up: invertColor ? 'text-red-600' : 'text-green-600',
    down: invertColor ? 'text-green-600' : 'text-red-600',
    flat: 'text-gray-400',
  };

  const Icon = direction === 'up' ? ArrowUp : direction === 'down' ? ArrowDown : Minus;
  const sign = direction === 'up' ? '+' : direction === 'down' ? '' : '';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-xs font-medium mt-1',
        colorMap[direction],
      )}
    >
      <Icon className="w-3 h-3" />
      {sign}
      {pct}% vs yesterday
    </span>
  );
}

/** Mock data representing yesterday's KPI values for comparison. */
const YESTERDAY_KPIS = {
  activeAgents: 4,
  tasksCompleted: 18,
  pendingHumanTasks: 5,
  totalLlmCostUsdToday: 8.45,
  pendingEscalations: 3,
};

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  // Fetch dashboard data
  const {
    data: dashboard,
    isLoading: dashboardLoading,
    isError: dashboardError,
  } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    refetchInterval: 30000,
  });

  // Fetch subscribed agents for additional context
  const { data: subscribedAgents = [] } = useQuery({
    queryKey: ['subscribedAgents'],
    queryFn: getSubscribedAgents,
  });

  // Fetch pending human tasks for the approvals panel
  const { data: humanTasks = [] } = useQuery({
    queryKey: ['humanTasks', 'PENDING'],
    queryFn: () => getHumanTasks({ status: 'PENDING', pageSize: 5 }),
    refetchInterval: 15000,
  });

  // WebSocket live feed -- invalidates react-query caches on real-time events
  const { status: wsStatus } = useDashboardFeed();

  // Agent name + department lookup from subscribed agents
  const agentLookup = useMemo(() => {
    const map: Record<string, { name: string; department: string }> = {};
    subscribedAgents.forEach((sa) => {
      map[sa.agentId] = {
        name: sa.agent?.name || sa.agentId,
        department: sa.agent?.department || '',
      };
    });
    return map;
  }, [subscribedAgents]);

  const totalSubscribed = subscribedAgents.length;

  return (
    <div className="p-3 lg:p-4 max-w-[1440px] mx-auto space-y-2">
      {/* Greeting */}
      <div>
        <h1 className="text-lg font-bold text-gray-900">
          Welcome back, {user?.name?.split(' ')[0] || 'there'}
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Here is what is happening with your AI workforce today.
        </p>
      </div>

      {/* Loading State */}
      {dashboardLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading dashboard...</p>
        </div>
      )}

      {/* Error State */}
      {dashboardError && !dashboardLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load dashboard</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {dashboard && (
        <>
          {/* ============================================================ */}
          {/* KPI Cards Row                                                */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
            {/* Active Agents */}
            <div className="bg-white rounded-lg border border-gray-100 shadow-sm px-3.5 py-2.5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">
                    Active Agents
                  </p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">
                    {dashboard.activeAgents}
                    <span className="text-sm font-normal text-gray-400"> / {totalSubscribed}</span>
                  </p>
                  <ChangeIndicator
                    current={dashboard.activeAgents}
                    previous={YESTERDAY_KPIS.activeAgents}
                  />
                </div>
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50">
                  <Bot className="w-4 h-4 text-blue-600" />
                </div>
              </div>
            </div>

            {/* Tasks Today */}
            <div className="bg-white rounded-lg border border-gray-100 shadow-sm px-3.5 py-2.5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">
                    Tasks Today
                  </p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">
                    {dashboard.tasksCompleted}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {dashboard.tasksFailed > 0 && (
                      <span className="text-red-500">{dashboard.tasksFailed} failed</span>
                    )}
                    {dashboard.tasksFailed === 0 && `${dashboard.totalTasksToday} total`}
                  </p>
                  <ChangeIndicator
                    current={dashboard.tasksCompleted}
                    previous={YESTERDAY_KPIS.tasksCompleted}
                  />
                </div>
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-green-50">
                  <CheckSquare className="w-4 h-4 text-green-600" />
                </div>
              </div>
            </div>

            {/* Pending Approvals */}
            <div
              className={cn(
                'bg-white rounded-lg border shadow-sm px-3.5 py-2.5',
                dashboard.pendingHumanTasks > 0 ? 'border-red-400' : 'border-gray-200',
              )}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">
                    Pending Approvals
                  </p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">
                    {dashboard.pendingHumanTasks}
                  </p>
                  <ChangeIndicator
                    current={dashboard.pendingHumanTasks}
                    previous={YESTERDAY_KPIS.pendingHumanTasks}
                    invertColor
                  />
                </div>
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-red-50">
                  <Bell className="w-4 h-4 text-red-600" />
                </div>
              </div>
            </div>

            {/* Cost Today */}
            <div className="bg-white rounded-lg border border-gray-100 shadow-sm px-3.5 py-2.5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">
                    Cost Today
                  </p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">
                    {formatCurrency(dashboard.totalLlmCostUsdToday)}
                  </p>
                  <ChangeIndicator
                    current={dashboard.totalLlmCostUsdToday}
                    previous={YESTERDAY_KPIS.totalLlmCostUsdToday}
                    invertColor
                  />
                </div>
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-purple-50">
                  <DollarSign className="w-4 h-4 text-purple-600" />
                </div>
              </div>
            </div>

            {/* Open Escalations */}
            <div
              className={cn(
                'bg-white rounded-lg border shadow-sm px-3.5 py-2.5',
                dashboard.pendingEscalations > 0 ? 'border-amber-400' : 'border-gray-200',
              )}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">
                    Open Escalations
                  </p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">
                    {dashboard.pendingEscalations}
                  </p>
                  <ChangeIndicator
                    current={dashboard.pendingEscalations}
                    previous={YESTERDAY_KPIS.pendingEscalations}
                    invertColor
                  />
                </div>
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-50">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* Agent Status Grid                                            */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-gray-900">Agent Status</h2>
              <Link
                href="/workforce/catalog"
                className="text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors"
              >
                View all agents
              </Link>
            </div>

            {dashboard.agentBreakdown.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-100 shadow-sm">
                <div className="flex flex-col items-center justify-center py-10">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                    <Bot className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">No agents subscribed</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Subscribe to agents from the workforce catalog.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
                {dashboard.agentBreakdown.map((agent) => {
                  const lookup = agentLookup[agent.agentId];
                  const agentName = agent.name || lookup?.name || agent.agentId;
                  const department = lookup?.department || '';
                  const colors = departmentColors[department] || {
                    bg: 'bg-gray-50',
                    text: 'text-gray-700',
                  };

                  const isActive = agent.status === 'active';
                  const isWorking = agent.status === 'working' || agent.status === 'running';

                  return (
                    <div
                      key={agent.agentId}
                      onClick={() => router.push(`/workforce/${agent.agentId}`)}
                      className="bg-white rounded-lg border border-gray-100 shadow-sm px-3.5 py-2.5 hover:shadow-md transition-shadow cursor-pointer"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-50 text-primary-600 flex-shrink-0">
                            <Bot className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-gray-900 truncate">
                              {agentName}
                            </p>
                            {department && (
                              <span
                                className={cn(
                                  'inline-block mt-0.5 px-2 py-0.5 rounded-full text-xs font-medium',
                                  colors.bg,
                                  colors.text,
                                )}
                              >
                                {department}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Status indicator */}
                        <span
                          className="flex-shrink-0 mt-1 relative flex h-2.5 w-2.5"
                          title={agent.status}
                        >
                          {(isWorking || agent.status === 'escalating') && (
                            <span
                              className={cn(
                                'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
                                agent.status === 'escalating' ? 'bg-amber-400' : 'bg-blue-400',
                              )}
                            />
                          )}
                          <span
                            className={cn(
                              'relative inline-flex rounded-full h-2.5 w-2.5',
                              isActive && 'bg-green-500',
                              isWorking && 'bg-blue-500',
                              agent.status === 'escalating' && 'bg-amber-500',
                              agent.status === 'idle' && 'bg-gray-300',
                              !isActive &&
                                !isWorking &&
                                agent.status !== 'escalating' &&
                                agent.status !== 'idle' &&
                                'bg-gray-300',
                            )}
                          />
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>{agent.tasksCompleted} tasks today</span>
                        <span>{formatDuration(agent.avgDurationMs)} avg</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* ============================================================ */}
          {/* Two-column: Pending Approvals + Live Activity Feed            */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
            {/* Pending Approvals Panel */}
            <div className="bg-white rounded-lg border border-gray-100 shadow-sm">
              <div className="px-3.5 py-2.5 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Bell className="w-4 h-4 text-primary-600" />
                  <h2 className="text-sm font-semibold text-gray-900">Pending Approvals</h2>
                  {humanTasks.length > 0 && (
                    <span className="ml-1 px-2 py-0.5 rounded-full bg-red-50 text-xs font-medium text-red-700">
                      {humanTasks.length}
                    </span>
                  )}
                </div>
              </div>

              <div className="px-3.5 py-2.5">
                {humanTasks.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-6">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 mb-2">
                      <CheckSquare className="w-5 h-5 text-gray-400" />
                    </div>
                    <p className="text-sm text-gray-500">No pending approvals</p>
                    <p className="text-xs text-gray-400 mt-1">All tasks are resolved.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {humanTasks.slice(0, 5).map((task) => {
                      const priorityStyle = priorityIcons[task.priority] || {
                        color: 'text-gray-400',
                      };
                      const agentName = task.agentId
                        ? agentLookup[task.agentId]?.name || task.agentId
                        : 'System';

                      return (
                        <div
                          key={task.id}
                          onClick={() => router.push(`/tasks/human-tasks/${task.id}`)}
                          className="flex items-start gap-2.5 px-2.5 py-2 rounded-lg border border-gray-100 hover:border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors"
                        >
                          <AlertTriangle
                            className={cn('w-4 h-4 mt-0.5 flex-shrink-0', priorityStyle.color)}
                          />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {task.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-gray-400">{agentName}</span>
                              <span className="text-xs text-gray-300">&#183;</span>
                              <span className="text-xs text-gray-400">
                                {task.createdAt ? formatTimeAgo(task.createdAt) : '--'}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {dashboard.pendingHumanTasks > 5 && (
                      <Link
                        href="/tasks/live"
                        className="flex items-center justify-center gap-1 py-2 text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors"
                      >
                        View all {dashboard.pendingHumanTasks} approvals
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Live Activity Feed (placeholder) */}
            <div className="bg-white rounded-lg border border-gray-100 shadow-sm">
              <div className="px-3.5 py-2.5 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-primary-600" />
                  <h2 className="text-sm font-semibold text-gray-900">Live Activity</h2>
                </div>
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
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

              <div className="px-3.5 py-2.5">
                {dashboard.agentBreakdown.length > 0 ? (
                  <div className="space-y-2">
                    {dashboard.agentBreakdown
                      .filter((a) => a.tasksCompleted > 0)
                      .slice(0, 5)
                      .map((agent) => {
                        const agentName =
                          agent.name || agentLookup[agent.agentId]?.name || agent.agentId;
                        return (
                          <div
                            key={agent.agentId}
                            className="flex items-center gap-2.5 py-1.5 border-b border-gray-50 last:border-0"
                          >
                            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-green-50">
                              <CheckSquare className="w-4 h-4 text-green-500" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm text-gray-700">
                                <span className="font-medium">{agentName}</span> completed{' '}
                                {agent.tasksCompleted} task
                                {agent.tasksCompleted !== 1 ? 's' : ''}
                              </p>
                              <p className="text-xs text-gray-400">Today</p>
                            </div>
                          </div>
                        );
                      })}

                    {dashboard.agentBreakdown.filter((a) => a.tasksCompleted > 0).length === 0 && (
                      <div className="flex flex-col items-center justify-center py-8 text-center">
                        <Clock className="w-6 h-6 text-gray-300 mb-2" />
                        <p className="text-sm text-gray-500">No completed tasks yet today</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 mb-2">
                      <Activity className="w-5 h-5 text-gray-400" />
                    </div>
                    <p className="text-sm text-gray-500">Recent activity will appear here</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Activity from your AI agents will show up once they start processing tasks.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
