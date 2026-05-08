'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Search,
  Bot,
  Loader2,
  AlertCircle,
  Check,
  Plug,
  X,
  AlertTriangle,
  Landmark,
  Users,
  TrendingUp,
  Settings,
  Scale,
  Headphones,
  Megaphone,
  Code,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAgentCatalog, getSubscribedAgents } from '@/lib/api/agents.api';
import { subscribeToAgent } from '@/lib/api/subscriptions.api';
import { AGENT_WORKFLOWS } from '@/lib/data/agent-workflows';
import type { AgentDefinition, AgentDepartment } from '@/lib/types/agent.types';

const DEPARTMENTS: { value: string; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'finance', label: 'Finance' },
  { value: 'hr', label: 'HR' },
  { value: 'sales', label: 'Sales' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'operations', label: 'Operations' },
  { value: 'engineering', label: 'Engineering' },
  { value: 'legal', label: 'Legal' },
  { value: 'support', label: 'Support' },
];

/** Full labels for department badges on cards. */
const DEPARTMENT_FULL_LABELS: Record<string, string> = {
  finance: 'Finance',
  hr: 'Human Resources',
  sales: 'Sales',
  marketing: 'Marketing',
  operations: 'Operations',
  engineering: 'Engineering',
  legal: 'Legal',
  support: 'Support',
};

const departmentColors: Record<AgentDepartment, { bg: string; text: string }> = {
  finance: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
  hr: { bg: 'bg-violet-50', text: 'text-violet-700' },
  sales: { bg: 'bg-blue-50', text: 'text-blue-700' },
  marketing: { bg: 'bg-pink-50', text: 'text-pink-700' },
  operations: { bg: 'bg-amber-50', text: 'text-amber-700' },
  engineering: { bg: 'bg-cyan-50', text: 'text-cyan-700' },
  legal: { bg: 'bg-slate-100', text: 'text-slate-700' },
  support: { bg: 'bg-orange-50', text: 'text-orange-700' },
};

/** Gradient colors for the card accent strip. */
const departmentGradients: Record<AgentDepartment, string> = {
  finance: 'from-emerald-400 to-emerald-600',
  hr: 'from-violet-400 to-violet-600',
  sales: 'from-blue-400 to-blue-600',
  marketing: 'from-pink-400 to-rose-600',
  operations: 'from-amber-400 to-orange-600',
  engineering: 'from-cyan-400 to-teal-600',
  legal: 'from-slate-400 to-slate-600',
  support: 'from-orange-400 to-red-500',
};

/** Department-specific icons. */
const departmentIcons: Record<AgentDepartment, typeof Bot> = {
  finance: Landmark,
  hr: Users,
  sales: TrendingUp,
  marketing: Megaphone,
  operations: Settings,
  engineering: Code,
  legal: Scale,
  support: Headphones,
};

function getDepartmentLabel(dept: AgentDepartment): string {
  return DEPARTMENT_FULL_LABELS[dept] || dept;
}

export default function WorkforceCatalogPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [subscribeModalAgent, setSubscribeModalAgent] = useState<AgentDefinition | null>(null);

  // Fetch catalog
  const {
    data: catalog = [],
    isLoading: catalogLoading,
    isError: catalogError,
  } = useQuery({
    queryKey: ['agentCatalog', department],
    queryFn: () =>
      getAgentCatalog(department ? { department, isActive: true } : { isActive: true }),
  });

  // Fetch subscribed agents
  const { data: subscribedAgents = [] } = useQuery({
    queryKey: ['subscribedAgents'],
    queryFn: getSubscribedAgents,
  });

  const subscribedIds = useMemo(
    () => new Set(subscribedAgents.map((sa) => sa.agentId)),
    [subscribedAgents],
  );

  // Subscribe mutation
  const subscribeMutation = useMutation({
    mutationFn: subscribeToAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscribedAgents'] });
      queryClient.invalidateQueries({ queryKey: ['agentCatalog'] });
      setSubscribeModalAgent(null);
    },
  });

  // Filter by search
  const filteredCatalog = useMemo(() => {
    if (!search.trim()) return catalog;
    const q = search.toLowerCase();
    return catalog.filter(
      (agent) =>
        agent.name.toLowerCase().includes(q) ||
        agent.description.toLowerCase().includes(q) ||
        agent.department.toLowerCase().includes(q),
    );
  }, [catalog, search]);

  function handleCardClick(agent: AgentDefinition) {
    router.push(`/workforce/${agent.id}`);
  }

  function handleSubscribeClick(e: React.MouseEvent, agent: AgentDefinition) {
    e.stopPropagation();
    setSubscribeModalAgent(agent);
  }

  function handleConfirmSubscribe() {
    if (!subscribeModalAgent) return;
    subscribeMutation.mutate(subscribeModalAgent.id);
  }

  /** Whether all required integrations are connected for the agent in the modal. */
  const modalRequiredIntegrations =
    subscribeModalAgent?.requiredIntegrations.filter((i) => i.required) ?? [];
  const allRequiredConnected = modalRequiredIntegrations.every((i) => i.connected);

  return (
    <div className="p-3 lg:p-4 max-w-[1440px] mx-auto space-y-2">
      {/* Page Header */}
      <div>
        <h1 className="text-lg font-bold text-gray-900">Workforce Catalog</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Browse and subscribe to AI agents for your organization.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="space-y-2">
        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white pl-8 pr-3 py-1.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Department Pill Tabs */}
        <div className="overflow-x-auto -mx-3 px-3 lg:-mx-4 lg:px-4">
          <div className="flex items-center gap-1 min-w-max">
            {DEPARTMENTS.map((dept) => {
              const isSelected = department === dept.value;
              return (
                <button
                  key={dept.value}
                  onClick={() => setDepartment(dept.value)}
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500/40',
                    isSelected
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                  )}
                >
                  {dept.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {catalogLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading agent catalog...</p>
        </div>
      )}

      {/* Error State */}
      {catalogError && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load agent catalog</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {/* Empty State */}
      {!catalogLoading && !catalogError && filteredCatalog.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
            <Bot className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-sm font-medium text-gray-600">No agents found</p>
          <p className="text-xs text-gray-400 mt-1">
            {search ? 'Try adjusting your search or filters.' : 'No agents are available yet.'}
          </p>
        </div>
      )}

      {/* Agent Cards Grid */}
      {!catalogLoading && !catalogError && filteredCatalog.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {filteredCatalog.map((agent) => {
            const isSubscribed = subscribedIds.has(agent.id);
            const colors = departmentColors[agent.department] || {
              bg: 'bg-gray-50',
              text: 'text-gray-700',
            };
            const gradient = departmentGradients[agent.department] || 'from-gray-400 to-gray-600';
            const DeptIcon = departmentIcons[agent.department] || Bot;
            const workflow = AGENT_WORKFLOWS[agent.id];

            return (
              <div
                key={agent.id}
                onClick={() => handleCardClick(agent)}
                className="group bg-white rounded-lg border border-gray-100 shadow-sm hover:shadow-md hover:scale-[1.005] transition-all duration-200 cursor-pointer flex flex-col overflow-hidden"
              >
                {/* Gradient Accent Strip */}
                <div className={cn('h-0.5 w-full bg-gradient-to-r', gradient)} />

                {/* Card Header */}
                <div className="px-3 pt-2.5 pb-1.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <div
                        className={cn(
                          'flex items-center justify-center w-8 h-8 rounded-md flex-shrink-0',
                          colors.bg,
                        )}
                      >
                        <DeptIcon className={cn('w-4 h-4', colors.text)} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-[13px] font-semibold text-gray-900 truncate">
                          {agent.name}
                        </h3>
                        <span
                          className={cn(
                            'inline-block px-1.5 py-px rounded-full text-[11px] font-medium',
                            colors.bg,
                            colors.text,
                          )}
                        >
                          {getDepartmentLabel(agent.department)}
                        </span>
                      </div>
                    </div>

                    {/* Status Badge */}
                    {isSubscribed && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-px rounded-full text-[11px] font-medium bg-green-50 text-green-700 flex-shrink-0">
                        <Check className="w-2.5 h-2.5" />
                        Active
                      </span>
                    )}
                  </div>
                </div>

                {/* Description */}
                <div className="px-3 pb-1.5 flex-1">
                  <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                    {agent.shortDescription || agent.description}
                  </p>
                </div>

                {/* Capabilities */}
                {agent.capabilities.length > 0 && (
                  <div className="px-3 pb-1.5">
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities.slice(0, 3).map((cap) => (
                        <span
                          key={cap.id}
                          className="px-1.5 py-px rounded text-[11px] text-gray-600 bg-gray-50 border border-gray-100"
                        >
                          {cap.name}
                        </span>
                      ))}
                      {agent.capabilities.length > 3 && (
                        <span className="px-1.5 py-px rounded text-[11px] text-gray-400 bg-gray-50 border border-gray-100">
                          +{agent.capabilities.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Workflow Indicator */}
                {workflow && (
                  <div className="px-3 pb-1.5">
                    <p className="text-[11px] text-gray-400">
                      {workflow.steps.length}-step workflow &middot; {workflow.automationLevel}
                    </p>
                  </div>
                )}

                {/* Footer: Price + Action */}
                <div className="px-3 py-2 border-t border-gray-50 flex items-center justify-between mt-auto bg-gray-50/50">
                  <div>
                    <span className="text-sm font-bold text-gray-900">
                      ${agent.pricing.monthlyFeeUsd}
                    </span>
                    <span className="text-[11px] text-gray-400">/mo</span>
                  </div>

                  {!isSubscribed ? (
                    <button
                      onClick={(e) => handleSubscribeClick(e, agent)}
                      className="px-2.5 py-1 rounded-md bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-colors"
                    >
                      Subscribe
                    </button>
                  ) : (
                    <span className="text-[11px] text-gray-400">Subscribed</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bundle Discount Banner */}
      {subscribedAgents.length > 0 && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm font-semibold text-emerald-900">
                Bundle Discount: Subscribe 3+ agents and get 15% off
              </p>
              <p className="text-xs text-emerald-700 mt-0.5">
                You currently have <span className="font-bold">{subscribedAgents.length}</span>{' '}
                agent{subscribedAgents.length !== 1 ? 's' : ''}.
                {subscribedAgents.length >= 3
                  ? ' Bundle discount applied!'
                  : ` Add ${3 - subscribedAgents.length} more to unlock the discount.`}
              </p>
            </div>
            {subscribedAgents.length >= 3 && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-600 text-white text-xs font-semibold">
                <Check className="w-3.5 h-3.5" />
                15% Discount Active
              </span>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* Subscribe Confirmation Modal                                  */}
      {/* ============================================================ */}
      {subscribeModalAgent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
          onClick={() => setSubscribeModalAgent(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl border border-gray-200 p-5 max-w-lg w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900">
                    Subscribe to {subscribeModalAgent.name}
                  </h3>
                  <p className="text-xs text-gray-400">
                    {getDepartmentLabel(subscribeModalAgent.department)} &middot; $
                    {subscribeModalAgent.pricing.monthlyFeeUsd}/month
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSubscribeModalAgent(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Required Integrations */}
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2.5">Required Integrations</h4>

              {subscribeModalAgent.requiredIntegrations.length === 0 ? (
                <p className="text-sm text-gray-400">No integrations required for this agent.</p>
              ) : (
                <div className="space-y-1.5">
                  {subscribeModalAgent.requiredIntegrations.map((integration) => (
                    <div
                      key={integration.id}
                      className="flex items-center justify-between p-2.5 rounded-lg border border-gray-100 bg-gray-50"
                    >
                      <div className="flex items-center gap-2.5">
                        <Plug className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">{integration.name}</p>
                          <p className="text-xs text-gray-400">{integration.type}</p>
                        </div>
                      </div>
                      <div>
                        {integration.connected ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">
                            <Check className="w-3 h-3" />
                            Connected
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-600">
                            <X className="w-3 h-3" />
                            Not Connected
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Warning if required integrations are missing */}
              {!allRequiredConnected && modalRequiredIntegrations.length > 0 && (
                <div className="flex items-start gap-2 mt-2.5 p-2.5 rounded-lg bg-amber-50 border border-amber-200">
                  <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-700">
                    Some required integrations are not connected. Please connect them before
                    subscribing to ensure the agent can function correctly.
                  </p>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-gray-100">
              <button
                onClick={() => setSubscribeModalAgent(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSubscribe}
                disabled={!allRequiredConnected || subscribeMutation.isPending}
                className="px-5 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {subscribeMutation.isPending ? 'Subscribing...' : 'Subscribe'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
