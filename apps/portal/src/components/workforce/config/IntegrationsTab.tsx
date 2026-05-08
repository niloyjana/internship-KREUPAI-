'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Save,
  Loader2,
  Plug,
  AlertCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { updateAgentFullConfig } from '@/lib/api/agent-config.api';
import type { AgentFullConfig, AgentIntegrationConfig } from '@/lib/types/agent.types';

const statusConfig: Record<
  string,
  { icon: typeof CheckCircle2; color: string; bgColor: string; label: string }
> = {
  connected: {
    icon: CheckCircle2,
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    label: 'Connected',
  },
  disconnected: {
    icon: XCircle,
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    label: 'Disconnected',
  },
  error: {
    icon: AlertTriangle,
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    label: 'Error',
  },
};

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

interface IntegrationsTabProps {
  agentId: string;
  config: AgentFullConfig;
}

export default function IntegrationsTab({ agentId, config }: IntegrationsTabProps) {
  const queryClient = useQueryClient();

  const [integrations, setIntegrations] = useState<AgentIntegrationConfig[]>([]);

  useEffect(() => {
    setIntegrations(config.integrations || []);
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAgentFullConfig(agentId, {
        integrations: integrations.map((i) => ({
          integrationId: i.integrationId,
          enabled: i.enabled,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentConfig', agentId] });
    },
  });

  function toggleIntegration(id: string) {
    setIntegrations((prev) =>
      prev.map((i) => (i.id === id ? { ...i, enabled: !i.enabled } : i)),
    );
  }

  const hasChanges = integrations.some((integration) => {
    const original = config.integrations?.find((i) => i.id === integration.id);
    return original && original.enabled !== integration.enabled;
  });

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Plug className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Connected Integrations</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {integrations.length}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Manage which integrations this agent can access. Toggle integrations on or off
            without disconnecting them.
          </p>
        </div>

        <div className="p-6">
          {integrations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                <Plug className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-600">No integrations connected</p>
              <p className="text-xs text-gray-400 mt-1">
                Connect integrations on the Integrations page to use them with this agent.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {integrations.map((integration) => {
                const statusInfo = statusConfig[integration.status] || statusConfig.disconnected;
                const StatusIcon = statusInfo.icon;

                return (
                  <div
                    key={integration.id}
                    className={cn(
                      'flex items-center justify-between gap-4 p-4 rounded-lg border transition-colors',
                      integration.enabled
                        ? 'border-gray-200 bg-white'
                        : 'border-gray-100 bg-gray-50 opacity-75',
                    )}
                  >
                    <div className="flex items-center gap-4 min-w-0 flex-1">
                      <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600 flex-shrink-0">
                        <Plug className="w-5 h-5" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-sm font-semibold text-gray-900 truncate">
                            {integration.name}
                          </h3>
                          <span
                            className={cn(
                              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                              statusInfo.bgColor,
                              statusInfo.color,
                            )}
                          >
                            <StatusIcon className="w-3 h-3" />
                            {statusInfo.label}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs text-gray-400">
                            {integration.provider.replace(/_/g, ' ')}
                          </span>
                          {integration.lastSyncAt && (
                            <span className="flex items-center gap-1 text-xs text-gray-400">
                              <Activity className="w-3 h-3" />
                              Last sync: {formatRelativeTime(integration.lastSyncAt)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Enable/Disable Toggle */}
                    <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                      <input
                        type="checkbox"
                        checked={integration.enabled}
                        onChange={() => toggleIntegration(integration.id)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600" />
                    </label>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      {integrations.length > 0 && (
        <div className="flex items-center gap-3">
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!hasChanges || saveMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {saveMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Integrations
              </>
            )}
          </button>

          {saveMutation.isSuccess && (
            <p className="text-sm text-green-600">Integrations saved successfully.</p>
          )}

          {saveMutation.isError && (
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <p className="text-sm text-red-600">Failed to save. Please try again.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
