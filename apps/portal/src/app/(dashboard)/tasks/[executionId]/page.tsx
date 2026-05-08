'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  PlayCircle,
  Ban,
  Download,
  ChevronDown,
  ChevronRight,
  Zap,
  User,
  Bot,
  Timer,
  Workflow,
  SkipForward,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getExecution, cancelExecution } from '@/lib/api/workflows.api';
import type { WorkflowStatus, StepStatus, WorkflowStep } from '@/lib/types/workflow.types';

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

const stepStatusIcons: Record<StepStatus, { icon: typeof CheckCircle2; color: string }> = {
  COMPLETED: { icon: CheckCircle2, color: 'text-green-500' },
  RUNNING: { icon: PlayCircle, color: 'text-blue-500' },
  FAILED: { icon: XCircle, color: 'text-red-500' },
  PENDING: { icon: Clock, color: 'text-gray-400' },
  SKIPPED: { icon: SkipForward, color: 'text-gray-400' },
};

const actorColors: Record<string, string> = {
  SYSTEM: 'text-gray-500 bg-gray-50',
  AI_AGENT: 'text-blue-600 bg-blue-50',
  HUMAN: 'text-green-600 bg-green-50',
};

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
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
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

function getStepActor(step: WorkflowStep): string {
  if (step.stepType === 'HUMAN_REVIEW') return 'HUMAN';
  if (step.stepType === 'AI_TASK') return 'AI_AGENT';
  return 'SYSTEM';
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function ExecutionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const executionId = params.executionId as string;

  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  // Fetch execution detail
  const {
    data: execution,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['execution', executionId],
    queryFn: () => getExecution(executionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'RUNNING' || status === 'PENDING' ? 5000 : false;
    },
  });

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => cancelExecution(executionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['execution', executionId] });
      queryClient.invalidateQueries({ queryKey: ['executions'] });
      setShowCancelDialog(false);
    },
  });

  function toggleStep(stepId: string) {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  }

  // Sort steps by sequence
  const sortedSteps = execution?.steps
    ? [...execution.steps].sort((a, b) => a.sequence - b.sequence)
    : [];

  // Build audit trail from steps
  const auditEntries = sortedSteps
    .filter((step) => step.startedAt || step.completedAt)
    .flatMap((step) => {
      const entries: { timestamp: string; actor: string; message: string; stepKey: string }[] = [];
      if (step.startedAt) {
        entries.push({
          timestamp: step.startedAt,
          actor: getStepActor(step),
          message: `Step "${step.stepKey}" started`,
          stepKey: step.stepKey,
        });
      }
      if (step.completedAt && step.status === 'COMPLETED') {
        entries.push({
          timestamp: step.completedAt,
          actor: getStepActor(step),
          message: `Step "${step.stepKey}" completed${step.durationMs ? ` in ${formatDuration(step.durationMs)}` : ''}`,
          stepKey: step.stepKey,
        });
      }
      if (step.completedAt && step.status === 'FAILED') {
        entries.push({
          timestamp: step.completedAt,
          actor: getStepActor(step),
          message: `Step "${step.stepKey}" failed: ${step.errorMessage || 'Unknown error'}`,
          stepKey: step.stepKey,
        });
      }
      return entries;
    })
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Back Button */}
      <button
        onClick={() => router.push('/tasks/live')}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Live Queue
      </button>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading execution details...</p>
        </div>
      )}

      {/* Error State */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load execution</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {execution && (
        <>
          {/* ============================================================ */}
          {/* Header                                                       */}
          {/* ============================================================ */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <h1 className="text-xl font-bold text-gray-900">
                    Execution {execution.id.slice(0, 8)}...
                  </h1>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
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
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Bot className="w-3.5 h-3.5" />
                    Agent: {execution.agentId}
                  </span>
                  <span className="flex items-center gap-1">
                    <Timer className="w-3.5 h-3.5" />
                    Duration: {formatDuration(execution.durationMs)}
                  </span>
                  {execution.triggerSource && (
                    <span className="flex items-center gap-1">
                      <Zap className="w-3.5 h-3.5" />
                      Trigger: {execution.triggerSource}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatTimestamp(execution.startedAt || execution.createdAt)}
                  </span>
                </div>

                {/* Token and cost info */}
                <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400">
                  {execution.tokenUsed !== null && (
                    <span>Tokens: {execution.tokenUsed.toLocaleString()}</span>
                  )}
                  {execution.llmCostUsd !== null && (
                    <span>LLM Cost: ${execution.llmCostUsd.toFixed(4)}</span>
                  )}
                  <span>
                    Steps: {execution.completedSteps}/{execution.stepCount}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {/* Export Audit button */}
                <button
                  onClick={() => {
                    const auditData = {
                      executionId: execution.id,
                      agentId: execution.agentId,
                      status: execution.status,
                      startedAt: execution.startedAt,
                      completedAt: execution.completedAt,
                      durationMs: execution.durationMs,
                      steps: sortedSteps.map((s) => ({
                        sequence: s.sequence,
                        stepKey: s.stepKey,
                        status: s.status,
                        durationMs: s.durationMs,
                        startedAt: s.startedAt,
                        completedAt: s.completedAt,
                        errorMessage: s.errorMessage,
                      })),
                      auditTrail: auditEntries,
                    };
                    const blob = new Blob([JSON.stringify(auditData, null, 2)], {
                      type: 'application/json',
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `audit-${execution.id.slice(0, 8)}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export Audit
                </button>

                {/* Cancel button */}
                {(execution.status === 'RUNNING' || execution.status === 'PENDING') && (
                  <button
                    onClick={() => setShowCancelDialog(true)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-red-300 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors"
                  >
                    <Ban className="w-4 h-4" />
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {/* Failure reason */}
            {execution.failureReason && (
              <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800">Execution Failed</p>
                    <p className="text-xs text-red-600 mt-1">{execution.failureReason}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Cancel Confirmation Dialog */}
          {showCancelDialog && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
              <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
                <h3 className="text-lg font-semibold text-gray-900">Cancel Execution?</h3>
                <p className="text-sm text-gray-500 mt-2">
                  This will cancel the running execution. Any completed steps will be preserved, but
                  pending steps will not run.
                </p>

                {cancelMutation.isError && (
                  <div className="flex items-center gap-2 p-3 mt-3 rounded-lg bg-red-50 border border-red-200">
                    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                    <p className="text-sm text-red-700">Failed to cancel. Please try again.</p>
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 mt-6">
                  <button
                    onClick={() => setShowCancelDialog(false)}
                    className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Keep Running
                  </button>
                  <button
                    onClick={() => cancelMutation.mutate()}
                    disabled={cancelMutation.isPending}
                    className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 transition-colors"
                  >
                    {cancelMutation.isPending ? 'Cancelling...' : 'Confirm Cancel'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* Workflow Timeline                                             */}
          {/* ============================================================ */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Workflow className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Workflow Timeline</h2>
              </div>
            </div>

            <div className="p-6">
              {sortedSteps.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <Workflow className="w-8 h-8 text-gray-300 mb-2" />
                  <p className="text-sm text-gray-400">No steps recorded yet.</p>
                </div>
              ) : (
                <div className="space-y-0">
                  {sortedSteps.map((step, index) => {
                    const isExpanded = expandedSteps.has(step.id);
                    const stepConfig = stepStatusIcons[step.status] || stepStatusIcons.PENDING;
                    const StepIcon = stepConfig.icon;
                    const isLast = index === sortedSteps.length - 1;

                    return (
                      <div key={step.id} className="relative flex gap-4">
                        {/* Vertical line */}
                        {!isLast && (
                          <div className="absolute left-[15px] top-8 bottom-0 w-0.5 bg-gray-200" />
                        )}

                        {/* Step icon */}
                        <div className="relative flex-shrink-0 mt-1">
                          <div
                            className={cn(
                              'flex items-center justify-center w-8 h-8 rounded-full bg-white border-2',
                              step.status === 'COMPLETED' && 'border-green-300',
                              step.status === 'RUNNING' && 'border-blue-300',
                              step.status === 'FAILED' && 'border-red-300',
                              step.status === 'PENDING' && 'border-gray-200',
                              step.status === 'SKIPPED' && 'border-gray-200',
                            )}
                          >
                            {step.status === 'RUNNING' ? (
                              <span className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500" />
                              </span>
                            ) : (
                              <StepIcon className={cn('w-4 h-4', stepConfig.color)} />
                            )}
                          </div>
                        </div>

                        {/* Step content */}
                        <div className={cn('flex-1 pb-6', isLast && 'pb-0')}>
                          <button
                            onClick={() => toggleStep(step.id)}
                            className="flex items-center gap-2 w-full text-left group"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-gray-400">
                                  #{step.sequence}
                                </span>
                                <span className="text-sm font-medium text-gray-900">
                                  {step.stepKey}
                                </span>
                                <span className="text-xs text-gray-400 px-1.5 py-0.5 rounded bg-gray-50">
                                  {step.stepType.replace(/_/g, ' ')}
                                </span>
                              </div>
                              <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                                {step.durationMs !== null && (
                                  <span>{formatDuration(step.durationMs)}</span>
                                )}
                                {step.toolCalled && <span>Tool: {step.toolCalled}</span>}
                                {step.retryCount > 0 && (
                                  <span className="text-amber-600">Retried {step.retryCount}x</span>
                                )}
                              </div>
                            </div>
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4 text-gray-400" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-gray-400" />
                            )}
                          </button>

                          {/* Error message */}
                          {step.errorMessage && (
                            <div className="mt-2 p-2 rounded bg-red-50 border border-red-100">
                              <p className="text-xs text-red-700">{step.errorMessage}</p>
                            </div>
                          )}

                          {/* Expanded details */}
                          {isExpanded && (
                            <div className="mt-3 space-y-3">
                              {/* Timestamps */}
                              <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                                {step.startedAt && (
                                  <span>Started: {formatTimestamp(step.startedAt)}</span>
                                )}
                                {step.completedAt && (
                                  <span>Completed: {formatTimestamp(step.completedAt)}</span>
                                )}
                              </div>

                              {/* Input JSON */}
                              {step.inputJson && (
                                <div>
                                  <p className="text-xs font-medium text-gray-500 mb-1">Input</p>
                                  <pre className="p-3 rounded-lg bg-gray-50 border border-gray-100 text-xs text-gray-700 overflow-x-auto max-h-48 overflow-y-auto">
                                    {typeof step.inputJson === 'string'
                                      ? step.inputJson
                                      : JSON.stringify(step.inputJson, null, 2)}
                                  </pre>
                                </div>
                              )}

                              {/* Output JSON */}
                              {step.outputJson && (
                                <div>
                                  <p className="text-xs font-medium text-gray-500 mb-1">Output</p>
                                  <pre className="p-3 rounded-lg bg-gray-50 border border-gray-100 text-xs text-gray-700 overflow-x-auto max-h-48 overflow-y-auto">
                                    {typeof step.outputJson === 'string'
                                      ? step.outputJson
                                      : JSON.stringify(step.outputJson, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ============================================================ */}
          {/* Audit Trail                                                   */}
          {/* ============================================================ */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-semibold text-gray-900">Audit Trail</h2>
              </div>
            </div>

            <div className="p-6">
              {auditEntries.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <Clock className="w-8 h-8 text-gray-300 mb-2" />
                  <p className="text-sm text-gray-400">No audit events yet.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {auditEntries.map((entry, index) => {
                    const ActorIcon =
                      entry.actor === 'AI_AGENT' ? Bot : entry.actor === 'HUMAN' ? User : Zap;
                    const colorClass = actorColors[entry.actor] || actorColors.SYSTEM;

                    return (
                      <div key={index} className="flex items-start gap-3">
                        <div
                          className={cn(
                            'flex items-center justify-center w-7 h-7 rounded-full flex-shrink-0',
                            colorClass,
                          )}
                        >
                          <ActorIcon className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-700">{entry.message}</p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {formatTimestamp(entry.timestamp)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
