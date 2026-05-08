'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Filter,
  Loader2,
  AlertCircle,
  Bot,
  Search,
  Activity,
  CheckCircle2,
  PauseCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getSubscribedAgents } from '@/lib/api/agents.api';
import { getExecutions } from '@/lib/api/workflows.api';
import type { WorkflowStatus } from '@/lib/types/workflow.types';

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

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function ActiveAgentsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Fetch subscribed agents
  const {
    data: subscribedAgents = [],
    isLoading: agentsLoading,
    isError: agentsError,
  } = useQuery({
    queryKey: ['subscribedAgents'],
    queryFn: getSubscribedAgents,
    refetchInterval: 15000,
  });

  // Fetch running executions to determine which agents are active
  const { data: runningExecutions = [], isLoading: executionsLoading } = useQuery({
    queryKey: ['executions', 'RUNNING'],
    queryFn: () => getExecutions({ status: 'RUNNING' as WorkflowStatus }),
    refetchInterval: 10000,
  });

  // Build agent activity data
  const agentActivityMap = useMemo(() => {
    const map: Record<string, { running: number; lastActive: string | null }> = {};
    runningExecutions.forEach((exec) => {
      if (!map[exec.agentId]) {
        map[exec.agentId] = { running: 0, lastActive: null };
      }
      map[exec.agentId].running += 1;
      const execTime = exec.startedAt || exec.createdAt;
      if (!map[exec.agentId].lastActive || execTime > map[exec.agentId].lastActive!) {
        map[exec.agentId].lastActive = execTime;
      }
    });
    return map;
  }, [runningExecutions]);

  // Enrich agent data with activity status
  const enrichedAgents = useMemo(() => {
    return subscribedAgents.map((sa) => {
      const activity = agentActivityMap[sa.agentId];
      return {
        ...sa,
        isRunning: !!activity && activity.running > 0,
        runningCount: activity?.running || 0,
        lastActive: activity?.lastActive || null,
      };
    });
  }, [subscribedAgents, agentActivityMap]);

  // Filter by search and status
  const filteredAgents = useMemo(() => {
    let result = enrichedAgents;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          (a.agent?.name || a.agentId).toLowerCase().includes(q) ||
          a.agentId.toLowerCase().includes(q),
      );
    }

    if (statusFilter === 'running') {
      result = result.filter((a) => a.isRunning);
    } else if (statusFilter === 'idle') {
      result = result.filter((a) => !a.isRunning);
    }

    return result;
  }, [enrichedAgents, searchQuery, statusFilter]);

  // Summary counts
  const summaryCounts = useMemo(() => {
    const total = enrichedAgents.length;
    const running = enrichedAgents.filter((a) => a.isRunning).length;
    const idle = total - running;
    return { total, running, idle };
  }, [enrichedAgents]);

  const isLoading = agentsLoading || executionsLoading;

  return (
    <div className="p-3 lg:p-4 max-w-[1440px] mx-auto space-y-2">
      {/* Page Header */}
      <div>
        <h1 className="text-lg font-bold text-gray-900">Active Agents</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Monitor currently running and subscribed AI agents.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-2">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white pl-8 pr-3 py-1.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Status Filter */}
        <div className="relative">
          <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="appearance-none rounded-lg border border-gray-300 bg-white pl-8 pr-8 py-1.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            <option value="">All Agents</option>
            <option value="running">Running</option>
            <option value="idle">Idle</option>
          </select>
        </div>
      </div>

      {/* Summary Pills */}
      <div className="flex flex-wrap gap-1.5">
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-medium">
          <Bot className="w-3 h-3" />
          {summaryCounts.total} Subscribed
        </span>
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium">
          <span className="relative flex h-2 w-2">
            {summaryCounts.running > 0 && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
            )}
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
          </span>
          {summaryCounts.running} Running
        </span>
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 text-xs font-medium">
          <Clock className="w-3 h-3" />
          {summaryCounts.idle} Idle
        </span>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading agents...</p>
        </div>
      )}

      {/* Error */}
      {agentsError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load agents</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !agentsError && filteredAgents.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <Bot className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No agents found</p>
            <p className="text-xs text-gray-400 mt-1">
              {searchQuery || statusFilter
                ? 'Try adjusting your search or filters.'
                : 'Subscribe to agents from the Workforce Catalog.'}
            </p>
          </div>
        </div>
      )}

      {/* Agent Cards */}
      {!isLoading && !agentsError && filteredAgents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {filteredAgents.map((agent) => (
            <div
              key={agent.agentId}
              onClick={() => router.push(`/workforce/${agent.agentId}`)}
              className="bg-white rounded-lg border border-gray-100 shadow-sm hover:shadow-md hover:scale-[1.005] transition-all duration-200 cursor-pointer"
            >
              <div className="px-3 pt-2.5 pb-2">
                <div className="flex items-start justify-between gap-2.5">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={cn(
                        'flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0',
                        agent.isRunning ? 'bg-blue-50' : 'bg-gray-100',
                      )}
                    >
                      <Bot
                        className={cn(
                          'w-4 h-4',
                          agent.isRunning ? 'text-blue-600' : 'text-gray-400',
                        )}
                      />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-[13px] font-semibold text-gray-900 truncate">
                        {agent.agent?.name || agent.agentId}
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5 font-mono truncate">
                        {agent.agentId}
                      </p>
                    </div>
                  </div>

                  {/* Status indicator */}
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-1.5 py-px rounded-full text-[11px] font-medium flex-shrink-0',
                      agent.isRunning ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-500',
                    )}
                  >
                    {agent.isRunning ? (
                      <>
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                        </span>
                        Running
                      </>
                    ) : (
                      <>
                        <span className="inline-flex rounded-full h-2 w-2 bg-gray-400" />
                        Idle
                      </>
                    )}
                  </span>
                </div>

                {/* Agent details */}
                <div className="mt-2.5 space-y-1.5">
                  {agent.isRunning && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Active executions</span>
                      <span className="font-medium text-blue-700">{agent.runningCount}</span>
                    </div>
                  )}
                  {agent.lastActive && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Last active</span>
                      <span className="text-gray-700">{formatTimeAgo(agent.lastActive)}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Subscribed</span>
                    <span className="text-gray-700">
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-500 inline" />
                    </span>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="px-3 py-2 border-t border-gray-50 flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {agent.agent?.department || 'General'}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/workforce/${agent.agentId}/config`);
                  }}
                  className="text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                >
                  Configure
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
