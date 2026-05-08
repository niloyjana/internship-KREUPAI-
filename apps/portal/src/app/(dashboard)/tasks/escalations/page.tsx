'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Filter,
  Loader2,
  AlertCircle,
  AlertTriangle,
  AlertOctagon,
  Info,
  Clock,
  CheckCircle2,
  XCircle,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  Save,
  Eye,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getEscalations, updateEscalation } from '@/lib/api/workflows.api';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import type {
  EscalationTicket,
  EscalationSeverity,
  EscalationStatus,
  UpdateEscalationPayload,
} from '@/lib/types/workflow.types';

/* ------------------------------------------------------------------ */
/*  Color maps                                                         */
/* ------------------------------------------------------------------ */

const severityColors: Record<EscalationSeverity, string> = {
  LOW: 'bg-blue-100 text-blue-800',
  MEDIUM: 'bg-amber-100 text-amber-800',
  HIGH: 'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

const severityIcons: Record<EscalationSeverity, typeof AlertCircle> = {
  LOW: Info,
  MEDIUM: AlertTriangle,
  HIGH: AlertOctagon,
  CRITICAL: AlertOctagon,
};

const escalationStatusColors: Record<EscalationStatus, string> = {
  OPEN: 'bg-red-100 text-red-800',
  IN_REVIEW: 'bg-amber-100 text-amber-800',
  RESOLVED: 'bg-green-100 text-green-800',
  ESCALATED_FURTHER: 'bg-purple-100 text-purple-800',
};

const SEVERITY_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Severities' },
  { value: 'CRITICAL', label: 'Critical' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'OPEN', label: 'Open' },
  { value: 'IN_REVIEW', label: 'In Review' },
  { value: 'RESOLVED', label: 'Resolved' },
];

const ESCALATION_STATUS_UPDATE_OPTIONS: { value: EscalationStatus; label: string }[] = [
  { value: 'OPEN', label: 'Open' },
  { value: 'IN_REVIEW', label: 'In Review' },
  { value: 'RESOLVED', label: 'Resolved' },
  { value: 'ESCALATED_FURTHER', label: 'Escalated Further' },
];

const SEVERITY_ORDER: Record<EscalationSeverity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

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

function getSlaInfo(ticket: EscalationTicket): {
  text: string;
  color: string;
  percentage: number;
} {
  if (!ticket.slaDeadlineAt) {
    return { text: 'No SLA', color: 'text-gray-400', percentage: 100 };
  }
  if (ticket.slaBreachedAt) {
    return { text: 'SLA Breached', color: 'text-red-600', percentage: 0 };
  }

  const now = Date.now();
  const deadline = new Date(ticket.slaDeadlineAt).getTime();
  const created = new Date(ticket.createdAt).getTime();
  const total = deadline - created;
  const remaining = deadline - now;

  if (remaining <= 0) {
    return { text: 'SLA Breached', color: 'text-red-600', percentage: 0 };
  }

  const percentage = Math.round((remaining / total) * 100);

  const hours = Math.floor(remaining / 3600000);
  const minutes = Math.floor((remaining % 3600000) / 60000);

  let text: string;
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    text = `${days}d ${hours % 24}h remaining`;
  } else if (hours >= 1) {
    text = `${hours}h ${minutes}m remaining`;
  } else {
    text = `${minutes}m remaining`;
  }

  let color: string;
  if (percentage > 50) {
    color = 'text-green-600';
  } else if (percentage > 25) {
    color = 'text-amber-600';
  } else {
    color = 'text-red-600';
  }

  return { text, color, percentage };
}

function formatTimestamp(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function EscalationsPage() {
  const queryClient = useQueryClient();

  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [agentFilter, setAgentFilter] = useState('');
  const [expandedTicket, setExpandedTicket] = useState<string | null>(null);

  // Detail panel editing state
  const [editAssignee, setEditAssignee] = useState('');
  const [editStatus, setEditStatus] = useState<EscalationStatus>('OPEN');
  const [editResolutionNote, setEditResolutionNote] = useState('');

  // Fetch escalations
  const {
    data: escalations = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['escalations', severityFilter, statusFilter, agentFilter],
    queryFn: () =>
      getEscalations({
        ...(severityFilter ? { severity: severityFilter as EscalationSeverity } : {}),
        ...(statusFilter ? { status: statusFilter as EscalationStatus } : {}),
        ...(agentFilter ? { agentId: agentFilter } : {}),
      }),
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

  // Update escalation mutation
  const updateMutation = useMutation({
    mutationFn: ({
      escalationId,
      payload,
    }: {
      escalationId: string;
      payload: UpdateEscalationPayload;
    }) => updateEscalation(escalationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escalations'] });
      setExpandedTicket(null);
    },
  });

  // Summary counts
  const summaryCounts = useMemo(() => {
    const open = escalations.filter((e) => e.status === 'OPEN').length;
    const inReview = escalations.filter((e) => e.status === 'IN_REVIEW').length;
    const resolved = escalations.filter((e) => e.status === 'RESOLVED').length;
    return { open, inReview, resolved };
  }, [escalations]);

  // Group by severity and sort
  const groupedEscalations = useMemo(() => {
    const sorted = [...escalations].sort(
      (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
    );
    return sorted;
  }, [escalations]);

  function openDetail(ticket: EscalationTicket) {
    if (expandedTicket === ticket.id) {
      setExpandedTicket(null);
      return;
    }
    setExpandedTicket(ticket.id);
    setEditAssignee(ticket.assignedToId || '');
    setEditStatus(ticket.status);
    setEditResolutionNote(ticket.resolutionNote || '');
  }

  function handleSave(escalationId: string) {
    const payload: UpdateEscalationPayload = {};
    if (editAssignee.trim()) {
      payload.assignedToUserId = editAssignee.trim();
    }
    if (editStatus) {
      payload.status = editStatus;
    }
    if (editResolutionNote.trim()) {
      payload.resolutionNote = editResolutionNote.trim();
    }
    updateMutation.mutate({ escalationId, payload });
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Escalations Center</h1>
        <p className="text-sm text-gray-500 mt-1">
          Review and resolve escalated issues from AI agents.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Severity Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

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

      {/* Summary Pills */}
      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-50 text-red-700 text-xs font-medium">
          <AlertCircle className="w-3 h-3" />
          {summaryCounts.open} Open
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 text-amber-700 text-xs font-medium">
          <Eye className="w-3 h-3" />
          {summaryCounts.inReview} In Review
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 text-green-700 text-xs font-medium">
          <CheckCircle2 className="w-3 h-3" />
          {summaryCounts.resolved} Resolved
        </span>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading escalations...</p>
        </div>
      )}

      {/* Error State */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load escalations</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && groupedEscalations.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <Shield className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No escalations found</p>
            <p className="text-xs text-gray-400 mt-1">
              {severityFilter || statusFilter || agentFilter
                ? 'Try adjusting your filters.'
                : 'All clear. No escalations at this time.'}
            </p>
          </div>
        </div>
      )}

      {/* Escalation Cards */}
      {!isLoading && !isError && groupedEscalations.length > 0 && (
        <div className="space-y-4">
          {groupedEscalations.map((ticket) => {
            const SeverityIcon = severityIcons[ticket.severity];
            const sla = getSlaInfo(ticket);
            const isExpanded = expandedTicket === ticket.id;

            return (
              <div
                key={ticket.id}
                className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
              >
                {/* Card Header */}
                <div
                  onClick={() => openDetail(ticket)}
                  className="p-5 cursor-pointer hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    {/* Severity icon */}
                    <div
                      className={cn(
                        'flex items-center justify-center w-10 h-10 rounded-full flex-shrink-0',
                        ticket.severity === 'CRITICAL' && 'bg-red-100',
                        ticket.severity === 'HIGH' && 'bg-orange-100',
                        ticket.severity === 'MEDIUM' && 'bg-amber-100',
                        ticket.severity === 'LOW' && 'bg-blue-100',
                      )}
                    >
                      <SeverityIcon
                        className={cn(
                          'w-5 h-5',
                          ticket.severity === 'CRITICAL' && 'text-red-600',
                          ticket.severity === 'HIGH' && 'text-orange-600',
                          ticket.severity === 'MEDIUM' && 'text-amber-600',
                          ticket.severity === 'LOW' && 'text-blue-600',
                        )}
                      />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={cn(
                            'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                            severityColors[ticket.severity],
                          )}
                        >
                          {ticket.severity === 'CRITICAL' && (
                            <span className="relative flex h-2 w-2 mr-1">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                            </span>
                          )}
                          {ticket.severity}
                        </span>
                        <span
                          className={cn(
                            'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                            escalationStatusColors[ticket.status],
                          )}
                        >
                          {ticket.status.replace(/_/g, ' ')}
                        </span>
                      </div>

                      <p className="text-sm text-gray-900 font-medium mt-1.5 line-clamp-2">
                        {ticket.reason}
                      </p>

                      <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Bot className="w-3.5 h-3.5" />
                          {agentNameMap[ticket.agentId] || ticket.agentId}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {formatTimeAgo(ticket.createdAt)}
                        </span>
                        <span className={cn('flex items-center gap-1 font-medium', sla.color)}>
                          <Clock className="w-3.5 h-3.5" />
                          {sla.text}
                        </span>
                      </div>
                    </div>

                    {/* Expand toggle */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openDetail(ticket);
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        View & Act
                      </button>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </div>

                  {/* SLA Progress Bar */}
                  {ticket.slaDeadlineAt && (
                    <div className="mt-3 ml-14">
                      <div className="w-full h-1.5 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all',
                            sla.percentage > 50 && 'bg-green-400',
                            sla.percentage > 25 && sla.percentage <= 50 && 'bg-amber-400',
                            sla.percentage <= 25 && 'bg-red-400',
                          )}
                          style={{ width: `${Math.max(0, Math.min(100, sla.percentage))}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Expanded Detail Panel */}
                {isExpanded && (
                  <div className="border-t border-gray-100 p-5 bg-gray-50/50 space-y-4">
                    {/* Full Reason */}
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Full Reason</p>
                      <p className="text-sm text-gray-700">{ticket.reason}</p>
                    </div>

                    {/* Context */}
                    {ticket.contextJson && (
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-1">Context</p>
                        <pre className="p-3 rounded-lg bg-white border border-gray-200 text-xs text-gray-700 overflow-x-auto max-h-40 overflow-y-auto">
                          {typeof ticket.contextJson === 'string'
                            ? ticket.contextJson
                            : JSON.stringify(ticket.contextJson, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Recommended Action */}
                    {ticket.recommendedAction && (
                      <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                        <p className="text-xs font-medium text-blue-700 mb-1">
                          Recommended Action
                        </p>
                        <p className="text-sm text-blue-600">{ticket.recommendedAction}</p>
                      </div>
                    )}

                    {/* Editable fields */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Assign To */}
                      <div>
                        <label
                          htmlFor={`assignee-${ticket.id}`}
                          className="block text-xs font-medium text-gray-500 mb-1"
                        >
                          Assign to User
                        </label>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                          <input
                            id={`assignee-${ticket.id}`}
                            type="text"
                            placeholder="User ID or email"
                            value={editAssignee}
                            onChange={(e) => setEditAssignee(e.target.value)}
                            className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                          />
                        </div>
                      </div>

                      {/* Status Update */}
                      <div>
                        <label
                          htmlFor={`status-${ticket.id}`}
                          className="block text-xs font-medium text-gray-500 mb-1"
                        >
                          Status
                        </label>
                        <select
                          id={`status-${ticket.id}`}
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value as EscalationStatus)}
                          className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
                        >
                          {ESCALATION_STATUS_UPDATE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Resolution Note */}
                    <div>
                      <label
                        htmlFor={`resolution-${ticket.id}`}
                        className="block text-xs font-medium text-gray-500 mb-1"
                      >
                        Resolution Note
                      </label>
                      <textarea
                        id={`resolution-${ticket.id}`}
                        rows={3}
                        placeholder="Add a resolution note..."
                        value={editResolutionNote}
                        onChange={(e) => setEditResolutionNote(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-none"
                      />
                    </div>

                    {/* Mutation error */}
                    {updateMutation.isError && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        <p className="text-sm text-red-700">
                          Failed to update escalation. Please try again.
                        </p>
                      </div>
                    )}

                    {/* Extra info */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400">
                      <span>ID: {ticket.id.slice(0, 8)}...</span>
                      {ticket.executionId && (
                        <span>Execution: {ticket.executionId.slice(0, 8)}...</span>
                      )}
                      {ticket.resolvedAt && (
                        <span>Resolved: {formatTimestamp(ticket.resolvedAt)}</span>
                      )}
                      <span>Created: {formatTimestamp(ticket.createdAt)}</span>
                    </div>

                    {/* Save Button */}
                    <div className="flex items-center justify-end">
                      <button
                        onClick={() => handleSave(ticket.id)}
                        disabled={updateMutation.isPending}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                      >
                        {updateMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Save className="w-4 h-4" />
                        )}
                        {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
