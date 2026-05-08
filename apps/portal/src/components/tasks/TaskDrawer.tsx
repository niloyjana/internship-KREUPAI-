'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock,
  User,
  Bot,
  Lightbulb,
  ThumbsUp,
  ThumbsDown,
  Edit3,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getHumanTask, resolveHumanTask, reassignHumanTask } from '@/lib/api/workflows.api';
import type {
  TaskStatus,
  ResolveTaskPayload,
  ReassignTaskPayload,
} from '@/lib/types/workflow.types';

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

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatSlaCountdown(dueAt: string | null): { text: string; urgency: string } {
  if (!dueAt) return { text: 'No deadline', urgency: 'none' };
  const diff = new Date(dueAt).getTime() - Date.now();
  if (diff <= 0) return { text: 'Overdue', urgency: 'overdue' };

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours < 1) {
    return { text: `${minutes}m remaining`, urgency: 'critical' };
  }
  if (hours < 4) {
    return { text: `${hours}h ${remainingMinutes}m remaining`, urgency: 'warning' };
  }
  if (hours < 24) {
    return { text: `${hours}h ${remainingMinutes}m remaining`, urgency: 'normal' };
  }
  const days = Math.floor(hours / 24);
  return { text: `${days}d ${hours % 24}h remaining`, urgency: 'normal' };
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
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface TaskDrawerProps {
  taskId: string | null;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function TaskDrawer({ taskId, onClose }: TaskDrawerProps) {
  const queryClient = useQueryClient();

  const [decisionNote, setDecisionNote] = useState('');
  const [resolved, setResolved] = useState(false);
  const [resolvedDecision, setResolvedDecision] = useState<string | null>(null);
  const [showReassign, setShowReassign] = useState(false);
  const [reassignTo, setReassignTo] = useState('');
  const reassignRef = useRef<HTMLDivElement>(null);

  // Reset state when taskId changes
  useEffect(() => {
    setDecisionNote('');
    setResolved(false);
    setResolvedDecision(null);
    setShowReassign(false);
    setReassignTo('');
  }, [taskId]);

  // Close reassign popover on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (reassignRef.current && !reassignRef.current.contains(e.target as Node)) {
        setShowReassign(false);
      }
    }
    if (showReassign) {
      document.addEventListener('mousedown', handleClick);
    }
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showReassign]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
    }
    if (taskId) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent background scrolling
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [taskId, onClose]);

  // Fetch task detail
  const {
    data: task,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['humanTask', taskId],
    queryFn: () => getHumanTask(taskId!),
    enabled: !!taskId,
  });

  // Resolve mutation
  const resolveMutation = useMutation({
    mutationFn: (payload: ResolveTaskPayload) => resolveHumanTask(taskId!, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['humanTask', taskId] });
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
      setResolved(true);
      setResolvedDecision(variables.decision);
    },
  });

  // Reassign mutation
  const reassignMutation = useMutation({
    mutationFn: (payload: ReassignTaskPayload) => reassignHumanTask(taskId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['humanTask', taskId] });
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
      setShowReassign(false);
      setReassignTo('');
      setResolved(true);
      setResolvedDecision('reassigned');
    },
  });

  function handleDecision(decision: 'approve' | 'reject' | 'modify') {
    resolveMutation.mutate({
      decision,
      decisionNote: decisionNote.trim() || undefined,
    });
  }

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // SLA countdown
  const sla = task ? formatSlaCountdown(task.dueAt) : { text: '--', urgency: 'none' };

  // Parse context JSON for display
  const contextEntries: [string, any][] = task?.contextJson
    ? Object.entries(
        typeof task.contextJson === 'string' ? JSON.parse(task.contextJson) : task.contextJson,
      )
    : [];

  // Extract recommended action from context
  const recommendedAction =
    task?.contextJson?.recommendedAction ||
    (typeof task?.contextJson === 'object' && task?.contextJson !== null
      ? task.contextJson.recommendedAction
      : null);

  const isResolvable = task?.status === 'PENDING' || task?.status === 'IN_PROGRESS';
  const isOpen = !!taskId;

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity duration-300',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none',
        )}
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className={cn(
          'fixed inset-y-0 right-0 z-50 w-[480px] max-w-full bg-white shadow-2xl border-l border-gray-200 transition-transform duration-300 ease-in-out flex flex-col',
          isOpen ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">Task Resolution</h2>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            aria-label="Close drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Loading State */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
              <p className="text-sm text-gray-500 mt-3">Loading task details...</p>
            </div>
          )}

          {/* Error State */}
          {isError && !isLoading && (
            <div className="flex flex-col items-center justify-center py-20 px-6">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
                <AlertCircle className="w-6 h-6 text-red-500" />
              </div>
              <p className="text-sm font-medium text-gray-700">Failed to load task</p>
              <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
            </div>
          )}

          {/* Success State */}
          {resolved && (
            <div className="p-6">
              <div className="flex flex-col items-center justify-center text-center py-8">
                <div className="flex items-center justify-center w-16 h-16 rounded-full bg-green-50 mb-4">
                  <CheckCircle2 className="w-8 h-8 text-green-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">Task Resolved</h3>
                <p className="text-sm text-gray-500 mt-2">
                  Your decision of{' '}
                  <span className="font-medium capitalize text-gray-700">{resolvedDecision}</span>{' '}
                  has been recorded successfully.
                </p>
                {decisionNote && (
                  <p className="text-xs text-gray-400 mt-2">Note: &ldquo;{decisionNote}&rdquo;</p>
                )}
                <div className="flex items-center gap-3 mt-6">
                  <button
                    onClick={handleClose}
                    className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                  >
                    Close
                  </button>
                  <button
                    onClick={() => {
                      setResolved(false);
                      setResolvedDecision(null);
                      setDecisionNote('');
                    }}
                    className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    View Task
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Task Details */}
          {task && !resolved && (
            <div className="p-6 space-y-5">
              {/* Task Header */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
                      priorityColors[task.priority] || 'bg-gray-100 text-gray-800',
                    )}
                  >
                    {task.priority === 'CRITICAL' && (
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                      </span>
                    )}
                    {task.priority} PRIORITY
                  </span>
                  <span
                    className={cn(
                      'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium',
                      taskStatusColors[task.status],
                    )}
                  >
                    {task.status}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-gray-900">{task.title}</h3>

                {task.description && <p className="text-sm text-gray-500">{task.description}</p>}

                {/* SLA Countdown */}
                <div
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium',
                    sla.urgency === 'overdue' && 'bg-red-50 border-red-200 text-red-700',
                    sla.urgency === 'critical' && 'bg-red-50 border-red-200 text-red-600',
                    sla.urgency === 'warning' && 'bg-amber-50 border-amber-200 text-amber-700',
                    sla.urgency === 'normal' && 'bg-gray-50 border-gray-200 text-gray-700',
                    sla.urgency === 'none' && 'bg-gray-50 border-gray-200 text-gray-500',
                  )}
                >
                  <Clock className="w-4 h-4" />
                  {sla.text}
                </div>

                {/* Metadata */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                  {task.assignedToId && (
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" />
                      {task.assignedToId}
                    </span>
                  )}
                  {task.agentId && (
                    <span className="flex items-center gap-1">
                      <Bot className="w-3.5 h-3.5" />
                      {task.agentId}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatTimestamp(task.createdAt)}
                  </span>
                </div>
              </div>

              {/* Context Panel */}
              {contextEntries.length > 0 && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
                    <h4 className="text-sm font-semibold text-gray-900">Task Context</h4>
                  </div>
                  <div className="p-4">
                    <div className="space-y-3">
                      {contextEntries
                        .filter(([key]) => key !== 'recommendedAction' && key !== 'reasoning')
                        .map(([key, value]) => (
                          <div key={key} className="p-2.5 rounded-lg bg-gray-50">
                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                              {key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}
                            </p>
                            <p className="text-sm text-gray-900 mt-0.5">
                              {typeof value === 'object'
                                ? JSON.stringify(value, null, 2)
                                : String(value)}
                            </p>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              )}

              {/* AI Recommendation */}
              {recommendedAction && (
                <div className="border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 flex-shrink-0">
                      <Lightbulb className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-semibold text-gray-900">AI Recommendation</h4>
                      <p className="text-sm text-gray-700 mt-1">{recommendedAction}</p>
                      {task.contextJson?.reasoning && (
                        <div className="mt-2 p-2.5 rounded-lg bg-blue-50">
                          <p className="text-xs font-medium text-blue-700 mb-0.5">Reasoning</p>
                          <p className="text-xs text-blue-600">{task.contextJson.reasoning}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Decision Section */}
              {isResolvable && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
                    <h4 className="text-sm font-semibold text-gray-900">Make a Decision</h4>
                  </div>
                  <div className="p-4 space-y-4">
                    {/* Decision Note */}
                    <div>
                      <label
                        htmlFor="drawer-decision-note"
                        className="block text-sm font-medium text-gray-700 mb-1"
                      >
                        Decision Note
                      </label>
                      <textarea
                        id="drawer-decision-note"
                        rows={3}
                        placeholder="Add a note about your decision (optional)..."
                        value={decisionNote}
                        onChange={(e) => setDecisionNote(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
                      />
                    </div>

                    {/* Mutation error */}
                    {resolveMutation.isError && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        <p className="text-sm text-red-700">
                          Failed to resolve task. Please try again.
                        </p>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => handleDecision('approve')}
                        disabled={resolveMutation.isPending}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                      >
                        {resolveMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <ThumbsUp className="w-4 h-4" />
                        )}
                        Approve
                      </button>

                      <button
                        onClick={() => handleDecision('reject')}
                        disabled={resolveMutation.isPending}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                      >
                        {resolveMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <ThumbsDown className="w-4 h-4" />
                        )}
                        Reject
                      </button>

                      <button
                        onClick={() => handleDecision('modify')}
                        disabled={resolveMutation.isPending}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                      >
                        {resolveMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Edit3 className="w-4 h-4" />
                        )}
                        Escalate
                      </button>

                      {/* Reassign */}
                      <div className="relative" ref={reassignRef}>
                        <button
                          onClick={() => setShowReassign((prev) => !prev)}
                          disabled={resolveMutation.isPending || reassignMutation.isPending}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                        >
                          <ArrowRight className="w-4 h-4" />
                          Reassign
                        </button>

                        {showReassign && (
                          <div className="absolute bottom-full left-0 mb-2 w-72 bg-white rounded-lg border border-gray-200 shadow-xl p-4 space-y-3 z-10">
                            <h4 className="text-sm font-semibold text-gray-900">Reassign Task</h4>
                            <div>
                              <label
                                htmlFor="drawer-reassign-to"
                                className="block text-xs font-medium text-gray-600 mb-1"
                              >
                                Assign to (user ID or email)
                              </label>
                              <input
                                id="drawer-reassign-to"
                                type="text"
                                value={reassignTo}
                                onChange={(e) => setReassignTo(e.target.value)}
                                placeholder="e.g. user@company.com"
                                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                              />
                            </div>
                            <button
                              onClick={() => {
                                if (!reassignTo.trim()) return;
                                reassignMutation.mutate({ assignedTo: reassignTo.trim() });
                              }}
                              disabled={!reassignTo.trim() || reassignMutation.isPending}
                              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 transition-colors"
                            >
                              {reassignMutation.isPending ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <ArrowRight className="w-3.5 h-3.5" />
                              )}
                              Reassign Task
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Already resolved info */}
              {!isResolvable && (
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        This task has been {task.status.toLowerCase()}.
                      </p>
                      {task.decision && (
                        <p className="text-xs text-gray-500 mt-1">
                          Decision: <span className="font-medium capitalize">{task.decision}</span>
                        </p>
                      )}
                      {task.decisionNote && (
                        <p className="text-xs text-gray-500 mt-1">Note: {task.decisionNote}</p>
                      )}
                      {task.completedAt && (
                        <p className="text-xs text-gray-400 mt-1">
                          Completed: {formatTimestamp(task.completedAt)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
