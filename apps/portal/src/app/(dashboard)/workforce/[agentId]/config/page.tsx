'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Bot,
  Loader2,
  AlertCircle,
  User,
  Shield,
  AlertTriangle,
  Plug,
  History,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAgentConfig } from '@/lib/api/agent-config.api';
import { getAgentDetails } from '@/lib/api/agents.api';
import IdentityTab from '@/components/workforce/config/IdentityTab';
import PolicyTab from '@/components/workforce/config/PolicyTab';
import EscalationTab from '@/components/workforce/config/EscalationTab';
import IntegrationsTab from '@/components/workforce/config/IntegrationsTab';
import HistoryTab from '@/components/workforce/config/HistoryTab';
import ModelTab from '@/components/workforce/config/ModelTab';

/* ------------------------------------------------------------------ */
/*  Tab Configuration                                                  */
/* ------------------------------------------------------------------ */

const TABS = [
  { key: 'identity', label: 'Identity', icon: User },
  { key: 'model', label: 'Model', icon: Bot },
  { key: 'policy', label: 'Policy', icon: Shield },
  { key: 'escalation', label: 'Escalation', icon: AlertTriangle },
  { key: 'integrations', label: 'Integrations', icon: Plug },
  { key: 'history', label: 'History', icon: History },
] as const;

type TabKey = (typeof TABS)[number]['key'];

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function AgentConfigPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.agentId as string;

  const [activeTab, setActiveTab] = useState<TabKey>('identity');

  // Fetch agent definition (for header)
  const {
    data: agent,
    isLoading: agentLoading,
    isError: agentError,
  } = useQuery({
    queryKey: ['agentDetails', agentId],
    queryFn: () => getAgentDetails(agentId),
    enabled: !!agentId,
  });

  // Fetch agent config
  const {
    data: config,
    isLoading: configLoading,
    isError: configError,
  } = useQuery({
    queryKey: ['agentConfig', agentId],
    queryFn: () => getAgentConfig(agentId),
    enabled: !!agentId,
  });

  const isLoading = agentLoading || configLoading;
  const isError = agentError || configError;

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Loading agent configuration...</p>
      </div>
    );
  }

  // Error state
  if (isError || !agent || !config) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
          <AlertCircle className="w-6 h-6 text-red-500" />
        </div>
        <p className="text-sm font-medium text-gray-700">Failed to load agent configuration</p>
        <p className="text-xs text-gray-400 mt-1">
          The agent may not exist or you may not have permission to view its configuration.
        </p>
        <button
          onClick={() => router.push(`/workforce/${agentId}`)}
          className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Back to agent details
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Back Button */}
      <button
        onClick={() => router.push(`/workforce/${agentId}`)}
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to agent details
      </button>

      {/* Page Header */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary-50 text-primary-600 flex-shrink-0 overflow-hidden">
            {config.avatarUrl ? (
              <img
                src={config.avatarUrl}
                alt={agent.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            ) : (
              <Bot className="w-6 h-6" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900 truncate">
                {config.displayName || agent.name}
              </h1>
              <div className="flex items-center gap-1.5">
                <Settings className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-400">Configuration</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-0.5 truncate">{agent.description}</p>
          </div>
          <span
            className={cn(
              'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium flex-shrink-0',
              config.isEnabled ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700',
            )}
          >
            {config.isEnabled ? 'Active' : 'Paused'}
          </span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-8" aria-label="Agent configuration tabs">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  'flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors -mb-px',
                  isActive
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'identity' && <IdentityTab agentId={agentId} config={config} />}
        {activeTab === 'model' && <ModelTab agentId={agentId} config={config} />}
        {activeTab === 'policy' && <PolicyTab agentId={agentId} config={config} />}
        {activeTab === 'escalation' && <EscalationTab agentId={agentId} config={config} />}
        {activeTab === 'integrations' && <IntegrationsTab agentId={agentId} config={config} />}
        {activeTab === 'history' && <HistoryTab agentId={agentId} />}
      </div>
    </div>
  );
}
