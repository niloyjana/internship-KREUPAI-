'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  DollarSign,
  Users,
  Tag,
  Settings,
  Loader2,
  AlertCircle,
  Zap,
} from 'lucide-react';
import { getAgentDefinition } from '@/lib/api/agents.api';
import { cn } from '@/lib/utils';

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

const statusColors: Record<string, string> = {
  active: 'bg-green-50 text-green-700',
  deprecated: 'bg-red-50 text-red-700',
  draft: 'bg-gray-100 text-gray-700',
};

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.agentId as string;

  const { data: agent, isLoading, isError } = useQuery({
    queryKey: ['admin-agent', agentId],
    queryFn: () => getAgentDefinition(agentId),
    enabled: !!agentId,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Loading agent details...</p>
      </div>
    );
  }

  if (isError || !agent) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
        <p className="text-sm font-medium text-gray-700">Failed to load agent</p>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Back link + Header */}
      <div>
        <Link
          href="/agents"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to agents
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-primary-50 text-primary-600">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{agent.name}</h1>
              <p className="text-sm text-gray-500 capitalize">{agent.department}</p>
            </div>
          </div>
          <span className={cn('px-3 py-1 rounded-full text-sm font-medium capitalize', statusColors[agent.status] || 'bg-gray-100 text-gray-700')}>
            {agent.status}
          </span>
        </div>
      </div>

      {/* Description */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-2">Description</h2>
        <p className="text-sm text-gray-600 leading-relaxed">{agent.description}</p>
        <div className="flex items-center gap-4 mt-4">
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Tag className="w-3.5 h-3.5" />
            <span>Version {agent.version}</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Users className="w-3.5 h-3.5" />
            <span>{agent.subscriptionCount} active subscriptions</span>
          </div>
        </div>
      </div>

      {/* Capabilities + Pricing */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Capabilities */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Capabilities</h2>
          </div>
          {agent.capabilities.length === 0 ? (
            <p className="text-sm text-gray-500">No capabilities listed</p>
          ) : (
            <ul className="space-y-2">
              {agent.capabilities.map((cap, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-1.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{cap}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Pricing */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Pricing</h2>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Monthly Base</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatCurrency(agent.pricing.monthlyBase)}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Per Task Fee</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatCurrency(agent.pricing.perTaskFee)}
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-gray-600">Currency</span>
              <span className="text-sm font-semibold text-gray-900 uppercase">
                {agent.pricing.currency}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Config Schema */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Configuration Schema</h2>
        </div>
        <pre className="bg-gray-50 rounded-lg p-4 text-xs text-gray-700 overflow-x-auto">
          {JSON.stringify(agent.configSchema, null, 2)}
        </pre>
      </div>
    </div>
  );
}
