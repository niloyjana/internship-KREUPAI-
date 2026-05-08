'use client';

import { useState, useMemo, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth.store';
import {
  ArrowLeft,
  Bot,
  Loader2,
  AlertCircle,
  Check,
  X,
  Play,
  Pause,
  Save,
  Plug,
  Shield,
  Zap,
  Clock,
  CheckCircle2,
  Workflow,
  Activity,
  Settings,
  Lock,
  DollarSign,
  ArrowRight,
  AlertTriangle,
  Timer,
  Bell,
  Sliders,
  Target,
  Gauge,
  Users,
  Wrench,
  Globe,
  ShieldCheck,
  ShieldX,
  Eye,
  Sparkles,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getAgentDetails,
  getSubscribedAgents,
  updateAgentConfig,
  enableAgent,
  pauseAgent,
} from '@/lib/api/agents.api';
import { subscribeToAgent, unsubscribeFromAgent } from '@/lib/api/subscriptions.api';
import { getAgentPerformance, getAgentTasks } from '@/lib/api/analytics.api';
import { executeAgent } from '@/lib/api/runtime.api';
import type { AgentExecuteResponse } from '@/lib/types/runtime.types';
import { AreaChart } from '@/components/charts/AreaChart';
import { AGENT_WORKFLOWS } from '@/lib/data/agent-workflows';
import { getToolsForAgent } from '@/lib/data/agent-tools';
import { AGENT_POLICIES, GLOBAL_GUARDRAILS } from '@/lib/data/agent-policies';
import type { AgentPolicySet } from '@/lib/data/agent-policies';
import { ErrorBoundary } from '@/components/shared/error-boundary';
import type { DailyBreakdown } from '@/lib/types/analytics.types';
import type { WorkflowStatus } from '@/lib/types/workflow.types';

import {
  type TabId,
  departmentColors,
  departmentLabels,
  statusColors,
  knowledgeTypeIcons,
  priorityColors,
  PIPELINE_STAGES,
  formatDuration,
  formatRelativeTime,
  generateDemoPerformanceData,
  DEMO_EXECUTIONS,
} from './constants';
import { RunTaskModal } from './components/RunTaskModal';
import { UnsubscribeModal } from './components/UnsubscribeModal';
import { ToolCard } from './components/ToolCard';

/* ------------------------------------------------------------------ */
/*  Locked Placeholder for non-subscribed tabs                         */
/* ------------------------------------------------------------------ */

function LockedPlaceholder({
  label,
  onSubscribe,
  isPending,
}: {
  label: string;
  onSubscribe: () => void;
  isPending: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
        <Lock className="w-7 h-7 text-gray-400" />
      </div>
      <p className="text-base font-medium text-gray-600 mb-1">Subscribe to view {label}</p>
      <p className="text-sm text-gray-400 mb-5 max-w-sm">
        Access {label.toLowerCase()}, monitor executions, and configure this agent after
        subscribing.
      </p>
      <button
        onClick={onSubscribe}
        disabled={isPending}
        className="px-6 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 transition-colors"
      >
        {isPending ? 'Subscribing...' : 'Subscribe Now'}
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const agentId = params.agentId as string;
  const tenantId = useAuthStore((s) => s.user?.tenantId) ?? '';

  const [activeTab, setActiveTab] = useState<TabId>('blueprint');
  const [displayName, setDisplayName] = useState('');
  const [policyJson, setPolicyJson] = useState('');
  const [policyJsonError, setPolicyJsonError] = useState('');
  const [configDirty, setConfigDirty] = useState(false);
  const [showUnsubConfirm, setShowUnsubConfirm] = useState(false);
  const [showRunTask, setShowRunTask] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [execResult, setExecResult] = useState<AgentExecuteResponse | null>(null);
  const [taskFilter, setTaskFilter] = useState<WorkflowStatus | 'ALL'>('ALL');

  // Fetch agent details
  const {
    data: agent,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['agentDetails', agentId],
    queryFn: () => getAgentDetails(agentId),
    enabled: !!agentId,
  });

  // Fetch subscribed agents
  const { data: subscribedAgents = [] } = useQuery({
    queryKey: ['subscribedAgents'],
    queryFn: getSubscribedAgents,
  });

  const subscribedAgent = subscribedAgents.find((sa) => sa.agentId === agentId);
  const isSubscribed = !!subscribedAgent;
  const isEnabled = subscribedAgent?.config?.isEnabled ?? false;

  // Fetch performance data (only when subscribed)
  const { data: performance } = useQuery({
    queryKey: ['agentPerformance', agentId],
    queryFn: () => getAgentPerformance(agentId),
    enabled: isSubscribed,
  });

  // Fetch task executions (only when subscribed)
  const { data: tasks = [] } = useQuery({
    queryKey: ['agentTasks', agentId],
    queryFn: () => getAgentTasks(agentId, { pageSize: 30 }),
    enabled: isSubscribed,
  });

  // Initialize config fields from subscribed agent data
  useEffect(() => {
    if (subscribedAgent?.config && !configDirty) {
      setDisplayName(subscribedAgent.config.displayName || '');
      setPolicyJson(subscribedAgent.config.policyJson || '{\n  \n}');
    }
  }, [subscribedAgent, configDirty]);

  // Mutations
  const subscribeMutation = useMutation({
    mutationFn: () => subscribeToAgent(agentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] }),
  });
  const unsubscribeMutation = useMutation({
    mutationFn: () => unsubscribeFromAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] });
      setShowUnsubConfirm(false);
    },
  });
  const configMutation = useMutation({
    mutationFn: () =>
      updateAgentConfig(agentId, {
        displayName: displayName || undefined,
        policyJson: policyJson || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] });
      setConfigDirty(false);
    },
  });
  const enableMutation = useMutation({
    mutationFn: () => enableAgent(agentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] }),
  });
  const pauseMutation = useMutation({
    mutationFn: () => pauseAgent(agentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] }),
  });
  const executeMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      executeAgent({
        agentId,
        tenantId,
        taskPayload: payload,
      }),
    onSuccess: (data) => {
      setExecResult(data);
      queryClient.invalidateQueries({ queryKey: ['agentTasks', agentId] });
    },
  });

  // Filtered tasks
  const filteredTasks = useMemo(() => {
    if (taskFilter === 'ALL') return tasks;
    return tasks.filter((t) => t.status === taskFilter);
  }, [tasks, taskFilter]);

  // Daily breakdown chart data (real or demo)
  const demoData = useMemo(() => generateDemoPerformanceData(), []);
  const chartData = useMemo(() => {
    if (performance?.dailyBreakdown && performance.dailyBreakdown.length > 0) {
      return performance.dailyBreakdown.map((d: DailyBreakdown) => ({
        ...d,
        date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      }));
    }
    return demoData;
  }, [performance, demoData]);

  const hasRealTasks = tasks.length > 0;

  // Static data from local modules
  const agentTools = useMemo(() => getToolsForAgent(agentId), [agentId]);
  const agentPolicies: AgentPolicySet | undefined = AGENT_POLICIES[agentId];
  const workflow = AGENT_WORKFLOWS[agentId];

  // Loading
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Loading agent details...</p>
      </div>
    );
  }

  // Error
  if (isError || !agent) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
          <AlertCircle className="w-6 h-6 text-red-500" />
        </div>
        <p className="text-sm font-medium text-gray-700">Failed to load agent details</p>
        <p className="text-xs text-gray-400 mt-1">
          The agent may not exist or there was a network error.
        </p>
        <button
          onClick={() => router.push('/workforce/catalog')}
          className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Back to catalog
        </button>
      </div>
    );
  }

  const colors = departmentColors[agent.department] || {
    bg: 'bg-gray-50',
    text: 'text-gray-700',
    icon: 'bg-gray-100 text-gray-600',
  };

  const tabs: { id: TabId; label: string; icon: React.ElementType; locked?: boolean }[] = [
    { id: 'blueprint', label: 'Blueprint', icon: Workflow },
    { id: 'tools', label: 'Tools & Actions', icon: Wrench },
    { id: 'integrations', label: 'Integrations', icon: Plug },
    { id: 'rules', label: 'Rules & Policies', icon: Shield },
    { id: 'activity', label: 'Activity', icon: Activity, locked: !isSubscribed },
    { id: 'settings', label: 'Settings', icon: Settings, locked: !isSubscribed },
  ];

  return (
    <ErrorBoundary>
      <div className="p-4 lg:p-6 space-y-0">
        {/* Back Button */}
        <button
          onClick={() => router.push('/workforce/catalog')}
          className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to catalog
        </button>

        {/* ============================================================ */}
        {/*  Hero Header -- Full Width                                    */}
        {/* ============================================================ */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-5 py-4">
          <div className="flex flex-col md:flex-row md:items-center gap-4">
            {/* Icon */}
            <div
              className={cn(
                'flex items-center justify-center w-16 h-16 rounded-xl flex-shrink-0',
                colors.icon,
              )}
            >
              <Bot className="w-8 h-8" />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <h1 className="text-xl font-bold text-gray-900">{agent.name}</h1>
                <span
                  className={cn(
                    'px-2.5 py-0.5 rounded-full text-xs font-medium',
                    colors.bg,
                    colors.text,
                  )}
                >
                  {departmentLabels[agent.department] || agent.department}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-500">
                  v{agent.version}
                </span>
                {isSubscribed && (
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium',
                      isEnabled ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700',
                    )}
                  >
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full',
                        isEnabled ? 'bg-green-500 animate-pulse' : 'bg-amber-500',
                      )}
                    />
                    {isEnabled ? 'Active' : 'Paused'}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">{agent.description}</p>
              <div className="flex items-baseline gap-2 mt-1.5">
                <span className="text-lg font-bold text-gray-900">
                  ${agent.pricing.monthlyFeeUsd}
                </span>
                <span className="text-sm text-gray-400">/month</span>
                {agent.pricing.includedTasksPerMonth > 0 && (
                  <>
                    <span className="text-gray-300">|</span>
                    <span className="text-xs text-gray-500">
                      {agent.pricing.includedTasksPerMonth} tasks included, then $
                      {agent.pricing.perTaskFeeUsd}/task
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 flex-shrink-0">
              {!isSubscribed ? (
                <button
                  onClick={() => subscribeMutation.mutate()}
                  disabled={subscribeMutation.isPending}
                  className="px-6 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-60 transition-colors"
                >
                  {subscribeMutation.isPending ? 'Subscribing...' : 'Subscribe'}
                </button>
              ) : (
                <>
                  {isEnabled ? (
                    <button
                      onClick={() => pauseMutation.mutate()}
                      disabled={pauseMutation.isPending}
                      className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg border border-amber-300 bg-amber-50 text-amber-700 text-sm font-medium hover:bg-amber-100 transition-colors disabled:opacity-60"
                    >
                      <Pause className="w-4 h-4" />
                      {pauseMutation.isPending ? 'Pausing...' : 'Pause'}
                    </button>
                  ) : (
                    <button
                      onClick={() => enableMutation.mutate()}
                      disabled={enableMutation.isPending}
                      className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-60"
                    >
                      <Play className="w-4 h-4" />
                      {enableMutation.isPending ? 'Enabling...' : 'Enable'}
                    </button>
                  )}
                  {isEnabled && (
                    <button
                      onClick={() => {
                        setShowRunTask(true);
                        setExecResult(null);
                        setTaskInput('');
                      }}
                      className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                    >
                      <Zap className="w-4 h-4" />
                      Run Task
                    </button>
                  )}
                  <button
                    onClick={() => setShowUnsubConfirm(true)}
                    className="text-sm text-red-500 hover:text-red-600 font-medium transition-colors"
                  >
                    Unsubscribe
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* ============================================================ */}
        {/*  Tab Navigation + Content -- Full Width                       */}
        {/* ============================================================ */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm mt-3 min-h-[60vh]">
          <div className="border-b border-gray-100 px-5 overflow-x-auto">
            <nav className="flex gap-0 -mb-px" aria-label="Agent tabs">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      'flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                      isActive
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                    {tab.locked && <Lock className="w-3 h-3 text-gray-400" />}
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="p-5 lg:p-6">
            {/* ======================================================== */}
            {/*  Tab 1: Blueprint (default)                               */}
            {/* ======================================================== */}
            {activeTab === 'blueprint' && (
              <div className="space-y-8">
                {/* 1. Execution Pipeline */}
                <section>
                  <h2 className="text-base font-semibold text-gray-900 mb-4">Execution Pipeline</h2>
                  <div className="flex items-stretch gap-0 overflow-x-auto pb-2">
                    {PIPELINE_STAGES.map((stage, idx) => {
                      const StageIcon = stage.icon;
                      return (
                        <div key={stage.key} className="flex items-stretch flex-shrink-0">
                          <div
                            className={cn(
                              'flex flex-col items-center justify-start px-4 py-4 rounded-xl border w-40',
                              stage.bg,
                              stage.border,
                            )}
                          >
                            <div
                              className={cn(
                                'flex items-center justify-center w-10 h-10 rounded-lg mb-2',
                                stage.iconBg,
                              )}
                            >
                              <StageIcon className={cn('w-5 h-5', stage.iconColor)} />
                            </div>
                            <p className="text-[11px] font-bold text-gray-700 uppercase tracking-wide text-center leading-tight">
                              {stage.label}
                            </p>
                            <p className="text-[10px] text-gray-500 text-center mt-1 leading-tight">
                              {stage.desc}
                            </p>
                          </div>
                          {idx < PIPELINE_STAGES.length - 1 && (
                            <div className="flex items-center px-1">
                              <ArrowRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>

                {/* 2. Agent Workflow Steps */}
                {workflow && (
                  <section>
                    <h2 className="text-base font-semibold text-gray-900 mb-1">
                      Agent Workflow Steps
                    </h2>
                    <p className="text-xs text-gray-500 mb-4">{workflow.summary}</p>

                    {/* Badges */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">
                        <Sparkles className="w-3 h-3" />
                        {workflow.automationLevel}
                      </span>
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                        <Clock className="w-3 h-3" />
                        {workflow.avgResponseTime}
                      </span>
                      {workflow.humanApprovalRequired.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700"
                        >
                          <Users className="w-3 h-3" />
                          {tag}
                        </span>
                      ))}
                    </div>

                    {/* Horizontal stepper */}
                    <div className="flex items-start gap-0 overflow-x-auto pb-2">
                      {workflow.steps.map((step, idx) => {
                        // Find matching tool for this step
                        const matchingTool = agentTools.find(
                          (t) =>
                            step.title
                              .toLowerCase()
                              .includes(t.name.replace(/_/g, ' ').toLowerCase()) ||
                            t.name
                              .replace(/_/g, ' ')
                              .toLowerCase()
                              .includes(step.title.toLowerCase().split(' ')[0]),
                        );
                        return (
                          <div key={idx} className="flex items-start flex-shrink-0">
                            <div className="flex flex-col items-center w-44">
                              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-600 text-white text-sm font-bold mb-2">
                                {idx + 1}
                              </div>
                              <p className="text-xs font-semibold text-gray-800 text-center mb-1">
                                {step.title}
                              </p>
                              <p className="text-[10px] text-gray-500 text-center leading-tight px-2">
                                {step.description}
                              </p>
                              {matchingTool && (
                                <span className="mt-2 px-2 py-0.5 rounded text-[9px] font-mono bg-gray-100 text-gray-600 truncate max-w-[140px]">
                                  {matchingTool.name}
                                </span>
                              )}
                            </div>
                            {idx < workflow.steps.length - 1 && (
                              <div className="flex items-center pt-3 px-0.5">
                                <ArrowRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}

                {/* 3. Quick Stats (subscribed only) */}
                {isSubscribed && subscribedAgent && (
                  <section>
                    <h2 className="text-base font-semibold text-gray-900 mb-4">Quick Stats</h2>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="bg-gradient-to-br from-blue-50 to-blue-50/50 rounded-xl px-4 py-3 border border-blue-100">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle2 className="w-4 h-4 text-blue-500" />
                          <span className="text-xs font-medium text-blue-600">Tasks Today</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">
                          {subscribedAgent.stats?.tasksToday ?? 0}
                        </p>
                      </div>
                      <div className="bg-gradient-to-br from-green-50 to-green-50/50 rounded-xl px-4 py-3 border border-green-100">
                        <div className="flex items-center gap-2 mb-1">
                          <Target className="w-4 h-4 text-green-500" />
                          <span className="text-xs font-medium text-green-600">Success Rate</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">
                          {subscribedAgent.stats?.successRate ?? 0}%
                        </p>
                      </div>
                      <div className="bg-gradient-to-br from-purple-50 to-purple-50/50 rounded-xl px-4 py-3 border border-purple-100">
                        <div className="flex items-center gap-2 mb-1">
                          <Timer className="w-4 h-4 text-purple-500" />
                          <span className="text-xs font-medium text-purple-600">Avg Duration</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">
                          {performance ? formatDuration(performance.avgDurationMs) : '\u2014'}
                        </p>
                      </div>
                      <div className="bg-gradient-to-br from-emerald-50 to-emerald-50/50 rounded-xl px-4 py-3 border border-emerald-100">
                        <div className="flex items-center gap-2 mb-1">
                          <Gauge className="w-4 h-4 text-emerald-500" />
                          <span className="text-xs font-medium text-emerald-600">Status</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              'w-2.5 h-2.5 rounded-full',
                              isEnabled ? 'bg-green-500 animate-pulse' : 'bg-amber-500',
                            )}
                          />
                          <p className="text-2xl font-bold text-gray-900">
                            {isEnabled ? 'Active' : 'Paused'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </section>
                )}
              </div>
            )}

            {/* ======================================================== */}
            {/*  Tab 2: Tools & Actions                                   */}
            {/* ======================================================== */}
            {activeTab === 'tools' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-base font-semibold text-gray-900">
                    Tools & Actions
                    {agentTools.length > 0 && (
                      <span className="ml-2 text-sm font-normal text-gray-400">
                        ({agentTools.length})
                      </span>
                    )}
                  </h2>
                  {agentTools.length > 0 && (
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span className="inline-flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-500" />
                        {agentTools.filter((t) => t.implemented).length} implemented
                      </span>
                      {agentTools.filter((t) => !t.implemented).length > 0 && (
                        <span className="inline-flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-gray-300" />
                          {agentTools.filter((t) => !t.implemented).length} planned
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {agentTools.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-3">
                      <Wrench className="w-6 h-6 text-gray-400" />
                    </div>
                    <p className="text-sm font-medium text-gray-600 mb-1">No tools defined yet</p>
                    <p className="text-xs text-gray-400 max-w-sm">
                      Tool definitions for this agent have not been registered. They will appear
                      here once configured.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {agentTools.map((tool) => (
                      <ToolCard key={tool.name} tool={tool} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ======================================================== */}
            {/*  Tab 3: Integrations                                      */}
            {/* ======================================================== */}
            {activeTab === 'integrations' && (
              <div className="space-y-6">
                <h2 className="text-base font-semibold text-gray-900">Required Integrations</h2>

                {agent.requiredIntegrations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-3">
                      <Plug className="w-6 h-6 text-gray-400" />
                    </div>
                    <p className="text-sm font-medium text-gray-600 mb-1">
                      No integrations required
                    </p>
                    <p className="text-xs text-gray-400 max-w-sm">
                      This agent operates independently and does not require external system
                      connections.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* Integration Cards */}
                    <div className="space-y-3">
                      {agent.requiredIntegrations.map((integration) => {
                        // Find which tools depend on this integration
                        const dependentTools = agentTools.filter(
                          (t) =>
                            t.category === 'integration' &&
                            (t.name
                              .toLowerCase()
                              .includes(
                                integration.name.toLowerCase().split(' ')[0].toLowerCase(),
                              ) ||
                              integration.name
                                .toLowerCase()
                                .includes(t.name.split('_')[0].toLowerCase())),
                        );

                        return (
                          <div
                            key={integration.id}
                            className="bg-white rounded-xl border border-gray-100 shadow-sm p-4"
                          >
                            <div className="flex items-center justify-between gap-4">
                              <div className="flex items-center gap-3 min-w-0 flex-1">
                                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-50 flex-shrink-0">
                                  <Globe className="w-5 h-5 text-gray-500" />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <div className="flex flex-wrap items-center gap-2 mb-0.5">
                                    <h4 className="text-sm font-semibold text-gray-900">
                                      {integration.name}
                                    </h4>
                                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-600 uppercase">
                                      {integration.type}
                                    </span>
                                    <span
                                      className={cn(
                                        'px-2 py-0.5 rounded-full text-[10px] font-medium',
                                        integration.required
                                          ? 'bg-red-50 text-red-600'
                                          : 'bg-gray-50 text-gray-500',
                                      )}
                                    >
                                      {integration.required ? 'Required' : 'Optional'}
                                    </span>
                                  </div>
                                  {dependentTools.length > 0 && (
                                    <p className="text-[10px] text-gray-400 mt-0.5">
                                      Used by: {dependentTools.map((t) => t.name).join(', ')}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-3 flex-shrink-0">
                                <div className="flex items-center gap-1.5">
                                  <span
                                    className={cn(
                                      'w-2 h-2 rounded-full',
                                      integration.connected ? 'bg-green-500' : 'bg-gray-300',
                                    )}
                                  />
                                  <span className="text-xs text-gray-500">
                                    {integration.connected ? 'Connected' : 'Disconnected'}
                                  </span>
                                </div>
                                <button
                                  onClick={() => router.push('/settings/api-keys')}
                                  className="px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                                >
                                  {integration.connected ? 'Manage' : 'Connect'}
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Setup Checklist */}
                    <div className="bg-gray-50 rounded-xl border border-gray-100 p-4">
                      <h3 className="text-sm font-semibold text-gray-800 mb-3">Setup Checklist</h3>
                      <div className="space-y-2">
                        {agent.requiredIntegrations.map((integration) => (
                          <div key={integration.id} className="flex items-center gap-2">
                            {integration.connected ? (
                              <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                            ) : (
                              <X className="w-4 h-4 text-red-400 flex-shrink-0" />
                            )}
                            <span className="text-xs text-gray-600">{integration.name}</span>
                            {!integration.connected && integration.required && (
                              <span className="text-[10px] text-red-500 font-medium">Required</span>
                            )}
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        {(() => {
                          const connected = agent.requiredIntegrations.filter(
                            (i) => i.connected,
                          ).length;
                          const total = agent.requiredIntegrations.length;
                          return (
                            <p className="text-xs font-medium text-gray-600">
                              {connected === total ? (
                                <span className="text-green-600">All integrations connected</span>
                              ) : (
                                <span>
                                  {connected} of {total} connected
                                </span>
                              )}
                            </p>
                          );
                        })()}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* ======================================================== */}
            {/*  Tab 4: Rules & Policies                                  */}
            {/* ======================================================== */}
            {activeTab === 'rules' && (
              <div className="space-y-8">
                {!agentPolicies ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-3">
                      <Shield className="w-6 h-6 text-gray-400" />
                    </div>
                    <p className="text-sm font-medium text-gray-600 mb-1">No policies defined</p>
                    <p className="text-xs text-gray-400 max-w-sm">
                      Policy definitions for this agent are not yet available. Global guardrails
                      still apply.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* 1. Approval Gates */}
                    {agentPolicies.approvalGates.length > 0 && (
                      <section>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">
                          Approval Gates
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {agentPolicies.approvalGates.map((gate, idx) => {
                            const gateColors = {
                              green: {
                                bg: 'bg-green-50',
                                border: 'border-green-200',
                                icon: 'text-green-600',
                                iconBg: 'bg-green-100',
                              },
                              amber: {
                                bg: 'bg-amber-50',
                                border: 'border-amber-200',
                                icon: 'text-amber-600',
                                iconBg: 'bg-amber-100',
                              },
                              red: {
                                bg: 'bg-red-50',
                                border: 'border-red-200',
                                icon: 'text-red-600',
                                iconBg: 'bg-red-100',
                              },
                            };
                            const gc = gateColors[gate.color];
                            const GateIcon =
                              gate.color === 'green'
                                ? ShieldCheck
                                : gate.color === 'amber'
                                  ? Eye
                                  : ShieldX;
                            return (
                              <div
                                key={idx}
                                className={cn('rounded-xl border p-4', gc.bg, gc.border)}
                              >
                                <div className="flex items-center gap-2 mb-2">
                                  <div
                                    className={cn(
                                      'flex items-center justify-center w-7 h-7 rounded-lg',
                                      gc.iconBg,
                                    )}
                                  >
                                    <GateIcon className={cn('w-4 h-4', gc.icon)} />
                                  </div>
                                  <h4 className="text-sm font-semibold text-gray-800">
                                    {gate.label}
                                  </h4>
                                </div>
                                <p className="text-xs text-gray-600 mb-2">{gate.description}</p>
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] font-medium text-gray-500 uppercase">
                                    Threshold:
                                  </span>
                                  <span className="text-xs font-medium text-gray-700">
                                    {gate.threshold}
                                  </span>
                                </div>
                                <span
                                  className={cn(
                                    'inline-block mt-2 px-2 py-0.5 rounded-full text-[10px] font-medium',
                                    gate.autoApprove
                                      ? 'bg-green-100 text-green-700'
                                      : 'bg-amber-100 text-amber-700',
                                  )}
                                >
                                  {gate.autoApprove ? 'Auto-approve' : 'Human review'}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                    )}

                    {/* 2. Escalation Rules */}
                    {agentPolicies.escalationTriggers.length > 0 && (
                      <section>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">
                          Escalation Rules
                        </h2>
                        <div className="space-y-2">
                          {agentPolicies.escalationTriggers.map((trigger, idx) => {
                            const pc = priorityColors[trigger.priority] || priorityColors.low;
                            return (
                              <div
                                key={idx}
                                className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-col sm:flex-row sm:items-center gap-3"
                              >
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs font-semibold text-gray-800 mb-0.5">
                                    {trigger.condition}
                                  </p>
                                  <p className="text-[11px] text-gray-500">{trigger.description}</p>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 text-blue-700 uppercase">
                                    {trigger.action.replace('_', ' ')}
                                  </span>
                                  <span
                                    className={cn(
                                      'px-2 py-0.5 rounded-full text-[10px] font-medium uppercase',
                                      pc.bg,
                                      pc.text,
                                    )}
                                  >
                                    {trigger.priority}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                    )}

                    {/* 3. Policy Rules */}
                    {agentPolicies.rules.length > 0 && (
                      <section>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">Policy Rules</h2>
                        {(() => {
                          const grouped = agentPolicies.rules.reduce<
                            Record<string, typeof agentPolicies.rules>
                          >((acc, rule) => {
                            const cat = rule.category;
                            if (!acc[cat]) acc[cat] = [];
                            acc[cat].push(rule);
                            return acc;
                          }, {});
                          return (
                            <div className="space-y-4">
                              {Object.entries(grouped).map(([category, rules]) => (
                                <div key={category}>
                                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                                    {category.replace(/_/g, ' ')}
                                  </h3>
                                  <div className="bg-white rounded-xl border border-gray-100 shadow-sm divide-y divide-gray-50">
                                    {rules.map((rule) => (
                                      <div
                                        key={rule.id}
                                        className="px-4 py-3 flex items-start justify-between gap-4"
                                      >
                                        <div className="min-w-0">
                                          <p className="text-xs font-semibold text-gray-800">
                                            {rule.label}
                                          </p>
                                          <p className="text-[11px] text-gray-500 mt-0.5">
                                            {rule.description}
                                          </p>
                                        </div>
                                        <div className="flex-shrink-0 text-right">
                                          <span className="text-xs font-mono font-medium text-gray-700">
                                            {String(rule.defaultValue)}
                                            {rule.unit ? ` ${rule.unit}` : ''}
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          );
                        })()}
                      </section>
                    )}

                    {/* 4. Knowledge Sources */}
                    {agentPolicies.knowledgeSources.length > 0 && (
                      <section>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">
                          Knowledge Sources
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {agentPolicies.knowledgeSources.map((source, idx) => {
                            const KsIcon = knowledgeTypeIcons[source.type] || FileText;
                            return (
                              <div
                                key={idx}
                                className="bg-white rounded-xl border border-gray-100 shadow-sm p-4"
                              >
                                <div className="flex items-center gap-2 mb-2">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-50">
                                    <KsIcon className="w-4 h-4 text-indigo-600" />
                                  </div>
                                  <div>
                                    <h4 className="text-xs font-semibold text-gray-800">
                                      {source.label}
                                    </h4>
                                    <span className="text-[10px] text-gray-400 uppercase">
                                      {source.type.replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                </div>
                                <p className="text-[11px] text-gray-500 leading-relaxed">
                                  {source.description}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                    )}

                    {/* 5. SLA & Rate Limits */}
                    {(agentPolicies.sla || agentPolicies.rateLimits) && (
                      <section>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">
                          SLA & Rate Limits
                        </h2>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                          {agentPolicies.sla && (
                            <>
                              <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">
                                <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                                  Response Time
                                </p>
                                <p className="text-lg font-bold text-gray-900">
                                  {agentPolicies.sla.responseMinutes}m
                                </p>
                              </div>
                              <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">
                                <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                                  Resolution Time
                                </p>
                                <p className="text-lg font-bold text-gray-900">
                                  {agentPolicies.sla.resolutionMinutes}m
                                </p>
                              </div>
                            </>
                          )}
                          {agentPolicies.rateLimits && (
                            <>
                              <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">
                                <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                                  Max Tasks / Day
                                </p>
                                <p className="text-lg font-bold text-gray-900">
                                  {agentPolicies.rateLimits.maxTasksPerDay}
                                </p>
                              </div>
                              <div className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">
                                <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                                  Max Concurrent
                                </p>
                                <p className="text-lg font-bold text-gray-900">
                                  {agentPolicies.rateLimits.maxConcurrent}
                                </p>
                              </div>
                            </>
                          )}
                        </div>
                      </section>
                    )}
                  </>
                )}

                {/* Global Guardrails -- always shown */}
                <section>
                  <h2 className="text-base font-semibold text-gray-900 mb-3">
                    Platform Guardrails
                  </h2>
                  <div className="bg-gray-50 rounded-xl border border-gray-100 p-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                          Financial Auto-Approve
                        </p>
                        <p className="text-sm font-semibold text-gray-800">
                          &lt; ${GLOBAL_GUARDRAILS.financial.autoApproveBelow}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                          Human Review
                        </p>
                        <p className="text-sm font-semibold text-gray-800">
                          &lt; ${GLOBAL_GUARDRAILS.financial.humanReviewBelow}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                          Hard Block
                        </p>
                        <p className="text-sm font-semibold text-gray-800">
                          &gt; ${GLOBAL_GUARDRAILS.financial.hardBlockAbove}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                          Max Tokens / Exec
                        </p>
                        <p className="text-sm font-semibold text-gray-800">
                          {GLOBAL_GUARDRAILS.budget.maxTokensPerExec.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                          Max Cost / Exec
                        </p>
                        <p className="text-sm font-semibold text-gray-800">
                          ${GLOBAL_GUARDRAILS.budget.maxCostPerExec}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">
                          Confidence Hard Fail
                        </p>
                        <p className="text-sm font-semibold text-gray-800">
                          &lt; {GLOBAL_GUARDRAILS.confidence.hardFailBelow}
                        </p>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            )}

            {/* ======================================================== */}
            {/*  Tab 5: Activity (subscribed only)                        */}
            {/* ======================================================== */}
            {activeTab === 'activity' && (
              <>
                {!isSubscribed ? (
                  <LockedPlaceholder
                    label="Activity"
                    onSubscribe={() => subscribeMutation.mutate()}
                    isPending={subscribeMutation.isPending}
                  />
                ) : (
                  <div className="space-y-6">
                    {/* Getting started guide when no real tasks */}
                    {process.env.NODE_ENV === 'development' && !hasRealTasks && (
                      <div className="bg-primary-50 border border-primary-100 rounded-xl p-4 mb-4">
                        <div className="flex gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-100 flex-shrink-0">
                            <Sparkles className="w-4 h-4 text-primary-600" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-primary-800 mb-1">
                              Getting Started
                            </p>
                            <p className="text-xs text-primary-600 leading-relaxed">
                              This agent is subscribed and ready to work. Trigger it via the API, a
                              webhook, or configure a schedule. Executions will appear here in
                              real-time. For now, demo data is shown below.
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Status filter pills */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {(
                        ['ALL', 'COMPLETED', 'RUNNING', 'PENDING', 'FAILED', 'PAUSED'] as const
                      ).map((status) => (
                        <button
                          key={status}
                          onClick={() => setTaskFilter(status)}
                          className={cn(
                            'px-3 py-1.5 rounded-full text-xs font-medium transition-colors',
                            taskFilter === status
                              ? 'bg-primary-600 text-white'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                          )}
                        >
                          {status === 'ALL'
                            ? 'All'
                            : status.charAt(0) + status.slice(1).toLowerCase()}
                        </button>
                      ))}
                    </div>

                    {/* Execution table */}
                    {hasRealTasks ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-100">
                              <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                Status
                              </th>
                              <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                Trigger
                              </th>
                              <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                Started
                              </th>
                              <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                Duration
                              </th>
                              <th className="text-left py-2.5 text-xs font-medium text-gray-500">
                                Steps
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredTasks.map((task) => {
                              const sc = statusColors[task.status] || statusColors.PENDING;
                              return (
                                <tr
                                  key={task.id}
                                  className="border-b border-gray-50 hover:bg-gray-50/50"
                                >
                                  <td className="py-2.5 pr-4">
                                    <span
                                      className={cn(
                                        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium',
                                        sc.bg,
                                        sc.text,
                                      )}
                                    >
                                      <span className={cn('w-1.5 h-1.5 rounded-full', sc.dot)} />
                                      {task.status}
                                    </span>
                                  </td>
                                  <td className="py-2.5 pr-4 text-xs text-gray-600">
                                    {task.triggerSource || '\u2014'}
                                  </td>
                                  <td className="py-2.5 pr-4 text-xs text-gray-500">
                                    {formatRelativeTime(task.startedAt)}
                                  </td>
                                  <td className="py-2.5 pr-4 text-xs text-gray-500 font-mono">
                                    {formatDuration(task.durationMs)}
                                  </td>
                                  <td className="py-2.5 text-xs text-gray-500">
                                    {task.completedSteps}/{task.stepCount}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    ) : process.env.NODE_ENV === 'development' ? (
                      <>
                        {/* Demo data banner */}
                        <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-100 rounded-lg mb-2">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                          <span className="text-[11px] text-amber-700">
                            Showing sample data. Real executions will replace this once the agent
                            starts processing tasks.
                          </span>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-gray-100">
                                <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                  Status
                                </th>
                                <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                  Trigger
                                </th>
                                <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                  Started
                                </th>
                                <th className="text-left py-2.5 pr-4 text-xs font-medium text-gray-500">
                                  Duration
                                </th>
                                <th className="text-left py-2.5 text-xs font-medium text-gray-500">
                                  Steps
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {DEMO_EXECUTIONS.map((exec) => {
                                const sc = statusColors[exec.status] || statusColors.PENDING;
                                return (
                                  <tr
                                    key={exec.id}
                                    className="border-b border-gray-50 hover:bg-gray-50/50"
                                  >
                                    <td className="py-2.5 pr-4">
                                      <span
                                        className={cn(
                                          'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium',
                                          sc.bg,
                                          sc.text,
                                        )}
                                      >
                                        <span className={cn('w-1.5 h-1.5 rounded-full', sc.dot)} />
                                        {exec.status}
                                      </span>
                                    </td>
                                    <td className="py-2.5 pr-4 text-xs text-gray-600">
                                      {exec.triggerSource}
                                    </td>
                                    <td className="py-2.5 pr-4 text-xs text-gray-500">
                                      {exec.startedAt}
                                    </td>
                                    <td className="py-2.5 pr-4 text-xs text-gray-500 font-mono">
                                      {exec.durationMs}
                                    </td>
                                    <td className="py-2.5 text-xs text-gray-500">{exec.steps}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : null}

                    {/* Performance chart */}
                    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                      <h3 className="text-sm font-semibold text-gray-800 mb-4">
                        Task Trend (30 days)
                      </h3>
                      <AreaChart
                        data={chartData}
                        xAxisKey="date"
                        series={[
                          { dataKey: 'tasksCompleted', label: 'Completed', color: '#10b981' },
                          { dataKey: 'tasksEscalated', label: 'Escalated', color: '#f59e0b' },
                          { dataKey: 'tasksFailed', label: 'Failed', color: '#ef4444' },
                        ]}
                        height={240}
                      />
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ======================================================== */}
            {/*  Tab 6: Settings (subscribed only)                        */}
            {/* ======================================================== */}
            {activeTab === 'settings' && (
              <>
                {!isSubscribed ? (
                  <LockedPlaceholder
                    label="Settings"
                    onSubscribe={() => subscribeMutation.mutate()}
                    isPending={subscribeMutation.isPending}
                  />
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left: Config form */}
                    <div className="space-y-6">
                      {/* Display Name */}
                      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                        <h3 className="text-sm font-semibold text-gray-800 mb-3">Display Name</h3>
                        <input
                          type="text"
                          value={displayName}
                          onChange={(e) => {
                            setDisplayName(e.target.value);
                            setConfigDirty(true);
                          }}
                          placeholder="Custom display name for this agent"
                          className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
                        />
                      </div>

                      {/* Policy JSON */}
                      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                        <h3 className="text-sm font-semibold text-gray-800 mb-3">
                          Policy JSON Override
                        </h3>
                        <textarea
                          rows={8}
                          value={policyJson}
                          onChange={(e) => {
                            const value = e.target.value;
                            setPolicyJson(value);
                            setConfigDirty(true);
                            if (value.trim()) {
                              try {
                                JSON.parse(value);
                                setPolicyJsonError('');
                              } catch (err) {
                                setPolicyJsonError(
                                  err instanceof Error ? err.message : 'Invalid JSON',
                                );
                              }
                            } else {
                              setPolicyJsonError('');
                            }
                          }}
                          spellCheck={false}
                          className="w-full px-3 py-2 rounded-lg border border-gray-200 text-xs font-mono text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 resize-y"
                        />
                        {policyJsonError && (
                          <p className="mt-1 text-xs text-red-500">{policyJsonError}</p>
                        )}
                        <div className="flex items-center justify-between mt-3">
                          <span className="text-[11px] text-gray-400">
                            Merge with platform defaults
                          </span>
                          <button
                            onClick={() => configMutation.mutate()}
                            disabled={!configDirty || !!policyJsonError || configMutation.isPending}
                            className={cn(
                              'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                              configDirty
                                ? 'bg-primary-600 text-white hover:bg-primary-700'
                                : 'bg-gray-100 text-gray-400 cursor-not-allowed',
                            )}
                          >
                            <Save className="w-3.5 h-3.5" />
                            {configMutation.isPending ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                        {configMutation.isSuccess && (
                          <p className="text-[11px] text-green-600 mt-2 flex items-center gap-1">
                            <Check className="w-3 h-3" /> Configuration saved
                          </p>
                        )}
                        {configMutation.isError && (
                          <p className="text-[11px] text-red-500 mt-2 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> Failed to save
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Right: Info cards */}
                    <div className="space-y-6">
                      {/* Execution Settings */}
                      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                        <div className="flex items-center gap-2 mb-3">
                          <Sliders className="w-4 h-4 text-gray-500" />
                          <h3 className="text-sm font-semibold text-gray-800">
                            Execution Settings
                          </h3>
                        </div>
                        <div className="space-y-3 text-xs text-gray-600">
                          <div className="flex items-center justify-between">
                            <span>Max Tasks / Day</span>
                            <span className="font-medium text-gray-800">
                              {agentPolicies?.rateLimits?.maxTasksPerDay ?? 500}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Max Concurrent</span>
                            <span className="font-medium text-gray-800">
                              {agentPolicies?.rateLimits?.maxConcurrent ?? 10}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Max Tokens / Execution</span>
                            <span className="font-medium text-gray-800">
                              {GLOBAL_GUARDRAILS.budget.maxTokensPerExec.toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Max Cost / Execution</span>
                            <span className="font-medium text-gray-800">
                              ${GLOBAL_GUARDRAILS.budget.maxCostPerExec}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Notifications */}
                      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                        <div className="flex items-center gap-2 mb-3">
                          <Bell className="w-4 h-4 text-gray-500" />
                          <h3 className="text-sm font-semibold text-gray-800">Notifications</h3>
                        </div>
                        <div className="space-y-3 text-xs text-gray-600">
                          <div className="flex items-center justify-between">
                            <span>Escalation alerts</span>
                            <span className="font-medium text-green-600">Enabled</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Failure alerts</span>
                            <span className="font-medium text-green-600">Enabled</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Daily summary email</span>
                            <span className="font-medium text-gray-400">Disabled</span>
                          </div>
                        </div>
                      </div>

                      {/* Subscription Info */}
                      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                        <div className="flex items-center gap-2 mb-3">
                          <DollarSign className="w-4 h-4 text-gray-500" />
                          <h3 className="text-sm font-semibold text-gray-800">Subscription</h3>
                        </div>
                        <div className="space-y-3 text-xs text-gray-600">
                          <div className="flex items-center justify-between">
                            <span>Plan</span>
                            <span className="font-medium text-gray-800">
                              ${agent.pricing.monthlyFeeUsd}/mo
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Included tasks</span>
                            <span className="font-medium text-gray-800">
                              {agent.pricing.includedTasksPerMonth}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Overage rate</span>
                            <span className="font-medium text-gray-800">
                              ${agent.pricing.perTaskFeeUsd}/task
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>This month usage</span>
                            <span className="font-medium text-gray-800">
                              {subscribedAgent?.stats?.tasksThisMonth ?? 0} tasks
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* ============================================================ */}
        {/*  Unsubscribe Confirmation Modal                               */}
        {/* ============================================================ */}
        <UnsubscribeModal
          open={showUnsubConfirm}
          onClose={() => setShowUnsubConfirm(false)}
          onConfirm={() => unsubscribeMutation.mutate()}
          isPending={unsubscribeMutation.isPending}
          agentName={agent.name}
        />

        {/* ============================================================ */}
        {/*  Run Task Modal                                                */}
        {/* ============================================================ */}
        <RunTaskModal
          open={showRunTask}
          onClose={() => setShowRunTask(false)}
          agentName={agent.name}
          taskInput={taskInput}
          onTaskInputChange={setTaskInput}
          onExecute={(payload) => executeMutation.mutate(payload)}
          isPending={executeMutation.isPending}
          isError={executeMutation.isError}
          error={executeMutation.error}
          result={execResult}
          onRunAnother={() => {
            setExecResult(null);
            setTaskInput('');
          }}
        />
      </div>
    </ErrorBoundary>
  );
}
