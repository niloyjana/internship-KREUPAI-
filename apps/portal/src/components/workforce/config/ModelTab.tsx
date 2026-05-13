'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Loader2, Bot, AlertCircle, Info, ChevronDown } from 'lucide-react';
import { updateAgentFullConfig } from '@/lib/api/agent-config.api';
import type { AgentFullConfig } from '@/lib/types/agent.types';
import { cn } from '@/lib/utils';

interface ModelTabProps {
  agentId: string;
  config: AgentFullConfig;
}

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
  {
    id: 'anthropic',
    name: 'Anthropic',
    models: ['claude-3-5-sonnet-20240620', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
  },
  {
    id: 'groq',
    name: 'Groq',
    models: ['llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
  },
];

export default function ModelTab({ agentId, config }: ModelTabProps) {
  const queryClient = useQueryClient();

  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(4096);

  useEffect(() => {
    try {
      const policy = JSON.parse(config.policyJson || '{}');
      if (policy.llm) {
        setProvider(policy.llm.provider || 'openai');
        setModel(policy.llm.model || 'gpt-4o');
        setTemperature(policy.llm.temperature ?? 0.2);
        setMaxTokens(policy.llm.max_tokens ?? 4096);
      }
    } catch (e) {
      console.error('Failed to parse policy JSON', e);
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: () => {
      let currentPolicy = {};
      try {
        currentPolicy = JSON.parse(config.policyJson || '{}');
      } catch (e) {
        currentPolicy = {};
      }

      const updatedPolicy = {
        ...currentPolicy,
        llm: {
          provider,
          model,
          temperature,
          max_tokens: maxTokens,
        },
      };

      return updateAgentFullConfig(agentId, {
        policyJson: JSON.stringify(updatedPolicy, null, 2),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentConfig', agentId] });
    },
  });

  const selectedProvider = PROVIDERS.find((p) => p.id === provider);

  // Check for changes against the policy in config
  let initialProvider = 'openai';
  let initialModel = 'gpt-4o';
  let initialTemp = 0.2;
  let initialTokens = 4096;

  try {
    const p = JSON.parse(config.policyJson || '{}');
    if (p.llm) {
      initialProvider = p.llm.provider || 'openai';
      initialModel = p.llm.model || 'gpt-4o';
      initialTemp = p.llm.temperature ?? 0.2;
      initialTokens = p.llm.max_tokens ?? 4096;
    }
  } catch (e) {}

  const hasChanges =
    provider !== initialProvider ||
    model !== initialModel ||
    temperature !== initialTemp ||
    maxTokens !== initialTokens;

  return (
    <div className="space-y-6">
      {/* Provider Selection */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">LLM Provider & Model</h2>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Select the primary AI model used by this agent for reasoning and task execution.
          </p>
        </div>

        <div className="p-6 space-y-8">
          {/* Provider Grid */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-4">Select Provider</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {PROVIDERS.map((p) => {
                const isActive = provider === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      setProvider(p.id);
                      setModel(p.models[0]);
                    }}
                    className={cn(
                      'flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all text-center',
                      isActive
                        ? 'border-primary-600 bg-primary-50/30'
                        : 'border-gray-100 bg-white hover:border-gray-200',
                    )}
                  >
                    <div
                      className={cn(
                        'flex items-center justify-center w-12 h-12 rounded-full',
                        isActive ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-400',
                      )}
                    >
                      <Bot className="w-6 h-6" />
                    </div>
                    <div>
                      <p
                        className={cn(
                          'text-sm font-semibold',
                          isActive ? 'text-gray-900' : 'text-gray-600',
                        )}
                      >
                        {p.name}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {p.id === 'openai'
                          ? 'Industry standard'
                          : p.id === 'anthropic'
                            ? 'Superior reasoning'
                            : 'Ultra-fast inference'}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Model Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
            <div>
              <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-1.5">
                Model Architecture
              </label>
              <div className="relative">
                <select
                  id="model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
                >
                  {selectedProvider?.models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
            </div>

            <div>
              <label
                htmlFor="temperature"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Temperature ({temperature})
              </label>
              <input
                id="temperature"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600 mt-4"
              />
              <div className="flex justify-between mt-2 text-[10px] text-gray-400 uppercase font-medium">
                <span>Precise</span>
                <span>Creative</span>
              </div>
            </div>
          </div>

          <div>
            <label htmlFor="maxTokens" className="block text-sm font-medium text-gray-700 mb-1.5">
              Max Response Tokens
            </label>
            <input
              id="maxTokens"
              type="number"
              min={1}
              max={128000}
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="w-full max-w-xs rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1.5">
              Limits the length of the model&apos;s output to control costs.
            </p>
          </div>
        </div>

        <div className="px-6 pb-6">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-100">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-700 leading-relaxed">
              <p className="font-semibold">Automatic Failover Active</p>
              <p className="mt-1">
                The platform will automatically fall back to alternative providers if{' '}
                {selectedProvider?.name} is unavailable, ensuring your AP workflow remains
                uninterrupted.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!hasChanges || saveMutation.isPending}
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-all shadow-sm"
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving Configuration...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save Model Settings
            </>
          )}
        </button>

        {saveMutation.isSuccess && (
          <div className="flex items-center gap-2 text-green-600 animate-in fade-in slide-in-from-left-2">
            <AlertCircle className="w-4 h-4" />
            <p className="text-sm font-medium">Model settings updated successfully.</p>
          </div>
        )}
      </div>
    </div>
  );
}
