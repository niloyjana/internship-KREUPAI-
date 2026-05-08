'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Bot,
  Filter,
  Loader2,
  AlertCircle,
  Users,
  Tag,
} from 'lucide-react';
import { getAgentDefinitions, type AgentDefinition } from '@/lib/api/agents.api';
import { cn } from '@/lib/utils';

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

const statusColors: Record<string, string> = {
  active: 'bg-green-50 text-green-700',
  deprecated: 'bg-red-50 text-red-700',
  draft: 'bg-gray-100 text-gray-700',
};

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
  }).format(amount);
}

export default function AgentsPage() {
  const [departmentFilter, setDepartmentFilter] = useState('');

  const { data: agents = [], isLoading, isError } = useQuery({
    queryKey: ['admin-agents', departmentFilter],
    queryFn: () =>
      getAgentDefinitions({
        department: departmentFilter || undefined,
      }),
  });

  // Unique departments for filter
  const departments = [...new Set(agents.map((a) => a.department).filter(Boolean))];

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Definitions</h1>
          <p className="text-sm text-gray-500 mt-1">All available AI agent definitions</p>
        </div>
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-gray-400" />
          <span className="text-sm text-gray-500">{agents.length} agents</span>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Departments</option>
            {departments.map((dept) => (
              <option key={dept} value={dept}>{dept.charAt(0).toUpperCase() + dept.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading agents...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
          <p className="text-sm font-medium text-gray-700">Failed to load agents</p>
        </div>
      )}

      {/* Agent Cards Grid */}
      {!isLoading && !isError && (
        <>
          {agents.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="flex flex-col items-center justify-center py-16">
                <Bot className="w-10 h-10 text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">No agents found</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent) => {
                const colors = departmentColors[agent.department] || { bg: 'bg-gray-50', text: 'text-gray-700' };
                return (
                  <Link
                    key={agent.id}
                    href={`/agents/${agent.id}`}
                    className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600">
                          <Bot className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{agent.name}</p>
                          {agent.department && (
                            <span className={cn('inline-block mt-0.5 px-2 py-0.5 rounded-full text-xs font-medium capitalize', colors.bg, colors.text)}>
                              {agent.department}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium capitalize', statusColors[agent.status] || 'bg-gray-100 text-gray-700')}>
                        {agent.status}
                      </span>
                    </div>

                    <p className="text-xs text-gray-500 mb-3 line-clamp-2">{agent.description}</p>

                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Tag className="w-3.5 h-3.5" />
                        <span>v{agent.version}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        <span>{agent.subscriptionCount} subscriptions</span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
