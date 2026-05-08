'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Loader2, Shield, AlertCircle, Info } from 'lucide-react';
import { updateAgentFullConfig } from '@/lib/api/agent-config.api';
import type { AgentFullConfig } from '@/lib/types/agent.types';

interface PolicyTabProps {
  agentId: string;
  config: AgentFullConfig;
}

export default function PolicyTab({ agentId, config }: PolicyTabProps) {
  const queryClient = useQueryClient();

  // Policy JSON editor
  const [policyJson, setPolicyJson] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Execution limits
  const [maxTasksPerDay, setMaxTasksPerDay] = useState(100);
  const [maxTasksPerHour, setMaxTasksPerHour] = useState(20);
  const [maxConcurrentTasks, setMaxConcurrentTasks] = useState(5);

  // Auto-approve thresholds
  const [autoApproveEnabled, setAutoApproveEnabled] = useState(false);
  const [costLimitUsd, setCostLimitUsd] = useState(50);
  const [riskScoreMax, setRiskScoreMax] = useState(30);

  useEffect(() => {
    setPolicyJson(config.policyJson || '{\n  \n}');
    setJsonError(null);

    if (config.executionLimits) {
      setMaxTasksPerDay(config.executionLimits.maxTasksPerDay);
      setMaxTasksPerHour(config.executionLimits.maxTasksPerHour);
      setMaxConcurrentTasks(config.executionLimits.maxConcurrentTasks);
    }

    if (config.autoApproveThresholds) {
      setAutoApproveEnabled(config.autoApproveThresholds.enabled);
      setCostLimitUsd(config.autoApproveThresholds.costLimitUsd);
      setRiskScoreMax(config.autoApproveThresholds.riskScoreMax);
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: () => {
      // Validate JSON before saving
      if (policyJson.trim()) {
        try {
          JSON.parse(policyJson);
        } catch {
          throw new Error('Invalid JSON in policy editor');
        }
      }

      return updateAgentFullConfig(agentId, {
        policyJson,
        executionLimits: {
          maxTasksPerDay,
          maxTasksPerHour,
          maxConcurrentTasks,
        },
        autoApproveThresholds: {
          enabled: autoApproveEnabled,
          costLimitUsd,
          riskScoreMax,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentConfig', agentId] });
      setJsonError(null);
    },
    onError: (error: Error) => {
      if (error.message === 'Invalid JSON in policy editor') {
        setJsonError('The policy JSON is not valid. Please fix the syntax errors.');
      }
    },
  });

  function validateJson(value: string) {
    setPolicyJson(value);
    if (!value.trim()) {
      setJsonError(null);
      return;
    }
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch {
      setJsonError('Invalid JSON syntax');
    }
  }

  const hasChanges =
    policyJson !== (config.policyJson || '{\n  \n}') ||
    maxTasksPerDay !== (config.executionLimits?.maxTasksPerDay ?? 100) ||
    maxTasksPerHour !== (config.executionLimits?.maxTasksPerHour ?? 20) ||
    maxConcurrentTasks !== (config.executionLimits?.maxConcurrentTasks ?? 5) ||
    autoApproveEnabled !== (config.autoApproveThresholds?.enabled ?? false) ||
    costLimitUsd !== (config.autoApproveThresholds?.costLimitUsd ?? 50) ||
    riskScoreMax !== (config.autoApproveThresholds?.riskScoreMax ?? 30);

  return (
    <div className="space-y-6">
      {/* Policy JSON Editor */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Policy Rules (JSON)</h2>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Define custom policy rules for this agent in JSON format.
          </p>
        </div>

        <div className="p-6">
          <div className="relative">
            <textarea
              value={policyJson}
              onChange={(e) => validateJson(e.target.value)}
              rows={12}
              spellCheck={false}
              className={`w-full rounded-lg border bg-gray-50 px-4 py-3 text-sm text-gray-900 font-mono outline-none transition-colors resize-y ${
                jsonError
                  ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-500/20'
                  : 'border-gray-300 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20'
              }`}
            />
            {jsonError && (
              <div className="flex items-center gap-1.5 mt-2">
                <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                <p className="text-xs text-red-600">{jsonError}</p>
              </div>
            )}
            {!jsonError && policyJson.trim() && policyJson.trim() !== '{\n  \n}' && (
              <p className="text-xs text-green-600 mt-2">Valid JSON</p>
            )}
          </div>
        </div>
      </div>

      {/* Execution Limits */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Execution Limits</h2>
          <p className="text-sm text-gray-500 mt-1">
            Control how many tasks the agent can process.
          </p>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div>
            <label
              htmlFor="maxTasksPerDay"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Max Tasks / Day
            </label>
            <input
              id="maxTasksPerDay"
              type="number"
              min={1}
              max={10000}
              value={maxTasksPerDay}
              onChange={(e) => setMaxTasksPerDay(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          <div>
            <label
              htmlFor="maxTasksPerHour"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Max Tasks / Hour
            </label>
            <input
              id="maxTasksPerHour"
              type="number"
              min={1}
              max={1000}
              value={maxTasksPerHour}
              onChange={(e) => setMaxTasksPerHour(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          <div>
            <label
              htmlFor="maxConcurrentTasks"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Max Concurrent Tasks
            </label>
            <input
              id="maxConcurrentTasks"
              type="number"
              min={1}
              max={100}
              value={maxConcurrentTasks}
              onChange={(e) => setMaxConcurrentTasks(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>
        </div>
      </div>

      {/* Auto-Approve Thresholds */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Auto-Approve Thresholds</h2>
              <p className="text-sm text-gray-500 mt-1">
                Automatically approve tasks that fall within these limits.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoApproveEnabled}
                onChange={() => setAutoApproveEnabled(!autoApproveEnabled)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600" />
            </label>
          </div>
        </div>

        <div className={`p-6 grid grid-cols-1 sm:grid-cols-2 gap-6 ${!autoApproveEnabled ? 'opacity-50 pointer-events-none' : ''}`}>
          <div>
            <label
              htmlFor="costLimitUsd"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Cost Limit (USD)
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">$</span>
              <input
                id="costLimitUsd"
                type="number"
                min={0}
                step={0.01}
                value={costLimitUsd}
                onChange={(e) => setCostLimitUsd(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-300 bg-white pl-7 pr-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Tasks costing below this amount are auto-approved.
            </p>
          </div>

          <div>
            <label
              htmlFor="riskScoreMax"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Max Risk Score
            </label>
            <input
              id="riskScoreMax"
              type="number"
              min={0}
              max={100}
              value={riskScoreMax}
              onChange={(e) => setRiskScoreMax(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              Tasks with a risk score at or below this value are auto-approved (0-100).
            </p>
          </div>
        </div>

        {autoApproveEnabled && (
          <div className="px-6 pb-4">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200">
              <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700">
                Auto-approve is enabled. Tasks within both the cost limit and risk score threshold
                will be executed without manual review.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!hasChanges || saveMutation.isPending || !!jsonError}
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
              Save Policy
            </>
          )}
        </button>

        {saveMutation.isSuccess && (
          <p className="text-sm text-green-600">Policy saved successfully.</p>
        )}

        {saveMutation.isError && (
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <p className="text-sm text-red-600">
              {jsonError || 'Failed to save policy. Please try again.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
