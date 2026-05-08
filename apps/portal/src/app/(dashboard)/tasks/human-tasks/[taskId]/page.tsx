'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Bot,
  AlertTriangle,
  Lightbulb,
  Edit3,
  UserPlus,
  ThumbsUp,
  ThumbsDown,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getHumanTask, resolveHumanTask, reassignHumanTask } from '@/lib/api/workflows.api';
import { getTeamUsers } from '@/lib/api/settings.api';
import { useToast } from '@/components/shared/Toast';
import type { TaskStatus, ResolveTaskPayload, ReassignTaskPayload } from '@/lib/types/workflow.types';

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
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function HumanTaskResolutionPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const taskId = params.taskId as string;

  const [decisionNote, setDecisionNote] = useState('');
  const [resolved, setResolved] = useState(false);
  const [resolvedDecision, setResolvedDecision] = useState<string | null>(null);

  // Reassign popover state
  const [showReassign, setShowReassign] = useState(false);
  const [reassignTo, setReassignTo] = useState('');
  const [reassignReason, setReassignReason] = useState('');
  const reassignRef = useRef<HTMLDivElement>(null);

  // Close reassign popover on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (reassignRef.current && !reassignRef.current.contains(e.target as Node)) {
        setShowReassign(false);
      }
    }
    if (showReassign) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showReassign]);

  // Fetch task detail
  const {
    data: task,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['humanTask', taskId],
    queryFn: () => getHumanTask(taskId),
  });

  // Fetch team users for the reassign selector
  const { data: teamData } = useQuery({
    queryKey: ['teamUsers'],
    queryFn: () => getTeamUsers({ page: 1, pageSize: 100 }),
  });

  // Resolve mutation
  const resolveMutation = useMutation({
    mutationFn: (payload: ResolveTaskPayload) => resolveHumanTask(taskId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['humanTask', taskId] });
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
      setResolved(true);
      setResolvedDecision(variables.decision);
    },
  });

  // Reassign mutation
  const reassignMutation = useMutation({
    mutationFn: (payload: ReassignTaskPayload) => reassignHumanTask(taskId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['humanTask', taskId] });
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
      setShowReassign(false);
      setReassignTo('');
      setReassignReason('');
      toast({
        variant: 'success',
        title: 'Task reassigned',
        description: 'The task has been reassigned successfully.',
      });
    },
    onError: () => {
      toast({
        variant: 'error',
        title: 'Reassignment failed',
        description: 'Could not reassign the task. Please try again.',
      });
    },
  });

  function handleReassign() {
    if (!reassignTo.trim()) return;
    reassignMutation.mutate({
      assignedTo: reassignTo.trim(),
      reassignReason: reassignReason.trim() || undefined,
    });
  }

  function handleDecision(decision: 'approve' | 'reject' | 'modify') {
    resolveMutation.mutate({
      decision,
      decisionNote: decisionNote.trim() || undefined,
    });
  }

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
          <p className="text-sm text-gray-500 mt-3">Loading task details...</p>
        </div>
      )}

      {/* Error State */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load task</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {task && !resolved && (
        <>
          {/* ============================================================ */}
          {/* Task Header                                                   */}
          {/* ============================================================ */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-3 flex-wrap">
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

                <h1 className="text-xl font-bold text-gray-900">{task.title}</h1>

                {task.description && (
                  <p className="text-sm text-gray-500">{task.description}</p>
                )}

                <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                  {task.assignedToId && (
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" />
                      Assigned to: {task.assignedToId}
                    </span>
                  )}
                  {task.assignedTeam && (
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" />
                      Team: {task.assignedTeam}
                    </span>
                  )}
                  {task.agentId && (
                    <span className="flex items-center gap-1">
                      <Bot className="w-3.5 h-3.5" />
                      Agent: {task.agentId}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    Created: {formatTimestamp(task.createdAt)}
                  </span>
                </div>
              </div>

              {/* SLA Countdown */}
              <div
                className={cn(
                  'flex items-center gap-2 px-4 py-3 rounded-lg border text-sm font-medium',
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
            </div>
          </div>

          {/* ============================================================ */}
          {/* Context Panel                                                 */}
          {/* ============================================================ */}
          {contextEntries.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <h2 className="text-base font-semibold text-gray-900">Task Context</h2>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {contextEntries
                    .filter(([key]) => key !== 'recommendedAction' && key !== 'reasoning')
                    .map(([key, value]) => (
                      <div key={key} className="p-3 rounded-lg bg-gray-50">
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                          {key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}
                        </p>
                        <p className="text-sm text-gray-900 mt-1">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </p>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* AI Recommendation                                             */}
          {/* ============================================================ */}
          {recommendedAction && (
            <div className="bg-white rounded-lg border border-blue-200 shadow-sm">
              <div className="p-6">
                <div className="flex items-start gap-3">
                  <div className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-50 flex-shrink-0">
                    <Lightbulb className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-gray-900">AI Recommendation</h3>
                    <p className="text-sm text-gray-700 mt-1">{recommendedAction}</p>
                    {task.contextJson?.reasoning && (
                      <div className="mt-3 p-3 rounded-lg bg-blue-50">
                        <p className="text-xs font-medium text-blue-700 mb-1">Reasoning</p>
                        <p className="text-xs text-blue-600">{task.contextJson.reasoning}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* Decision Section                                              */}
          {/* ============================================================ */}
          {isResolvable && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <h2 className="text-base font-semibold text-gray-900">Make a Decision</h2>
              </div>
              <div className="p-6 space-y-4">
                {/* Decision Note */}
                <div>
                  <label
                    htmlFor="decision-note"
                    className="block text-sm font-medium text-gray-700 mb-1.5"
                  >
                    Decision Note
                  </label>
                  <textarea
                    id="decision-note"
                    rows={4}
                    placeholder="Add a note about your decision (optional)..."
                    value={decisionNote}
                    onChange={(e) => setDecisionNote(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
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
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() => handleDecision('approve')}
                    disabled={resolveMutation.isPending}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
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
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
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
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                  >
                    {resolveMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Edit3 className="w-4 h-4" />
                    )}
                    Modify
                  </button>

                  {/* Reassign Button + Popover */}
                  <div className="relative" ref={reassignRef}>
                    <button
                      onClick={() => setShowReassign((prev) => !prev)}
                      disabled={resolveMutation.isPending || reassignMutation.isPending}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-amber-400 text-amber-700 text-sm font-medium hover:bg-amber-50 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                    >
                      <UserPlus className="w-4 h-4" />
                      Reassign
                    </button>

                    {/* Reassign Popover */}
                    {showReassign && (
                      <div className="absolute left-0 top-full mt-2 w-80 bg-white rounded-lg border border-gray-200 shadow-xl z-50 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-semibold text-gray-900">Reassign Task</h4>
                          <button
                            onClick={() => setShowReassign(false)}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>

                        {/* User / Team Selector */}
                        <div>
                          <label
                            htmlFor="reassign-to"
                            className="block text-xs font-medium text-gray-600 mb-1"
                          >
                            Assign to User / Team
                          </label>
                          <select
                            id="reassign-to"
                            value={reassignTo}
                            onChange={(e) => setReassignTo(e.target.value)}
                            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
                          >
                            <option value="">Select a user or team...</option>
                            {teamData?.users && teamData.users.length > 0 && (
                              <optgroup label="Users">
                                {teamData.users.map((u) => (
                                  <option key={u.id} value={u.id}>
                                    {u.name} ({u.email})
                                  </option>
                                ))}
                              </optgroup>
                            )}
                            <optgroup label="Teams">
                              <option value="team:engineering">Engineering</option>
                              <option value="team:operations">Operations</option>
                              <option value="team:compliance">Compliance</option>
                              <option value="team:support">Support</option>
                            </optgroup>
                          </select>
                        </div>

                        {/* Reason */}
                        <div>
                          <label
                            htmlFor="reassign-reason"
                            className="block text-xs font-medium text-gray-600 mb-1"
                          >
                            Reason (optional)
                          </label>
                          <textarea
                            id="reassign-reason"
                            rows={2}
                            placeholder="Why are you reassigning this task?"
                            value={reassignReason}
                            onChange={(e) => setReassignReason(e.target.value)}
                            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
                          />
                        </div>

                        {/* Confirm button */}
                        <button
                          onClick={handleReassign}
                          disabled={!reassignTo.trim() || reassignMutation.isPending}
                          className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                        >
                          {reassignMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <UserPlus className="w-4 h-4" />
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
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
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
        </>
      )}

      {/* ============================================================ */}
      {/* Success State                                                  */}
      {/* ============================================================ */}
      {resolved && (
        <div className="bg-white rounded-lg border border-green-200 shadow-sm p-8">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="flex items-center justify-center w-16 h-16 rounded-full bg-green-50 mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Task Resolved</h2>
            <p className="text-sm text-gray-500 mt-2">
              Your decision of{' '}
              <span className="font-medium capitalize text-gray-700">{resolvedDecision}</span> has
              been recorded successfully.
            </p>
            {decisionNote && (
              <p className="text-xs text-gray-400 mt-2">
                Note: &ldquo;{decisionNote}&rdquo;
              </p>
            )}
            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={() => router.push('/tasks/live')}
                className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
              >
                Back to Live Queue
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
    </div>
  );
}
