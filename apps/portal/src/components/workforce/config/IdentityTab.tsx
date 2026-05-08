'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Loader2, User, AlertCircle } from 'lucide-react';
import { updateAgentFullConfig } from '@/lib/api/agent-config.api';
import type { AgentFullConfig, AgentDepartment } from '@/lib/types/agent.types';

const DEPARTMENTS: { value: AgentDepartment; label: string }[] = [
  { value: 'finance', label: 'Finance' },
  { value: 'hr', label: 'Human Resources' },
  { value: 'sales', label: 'Sales' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'operations', label: 'Operations' },
  { value: 'engineering', label: 'Engineering' },
  { value: 'legal', label: 'Legal' },
  { value: 'support', label: 'Support' },
];

interface IdentityTabProps {
  agentId: string;
  config: AgentFullConfig;
}

export default function IdentityTab({ agentId, config }: IdentityTabProps) {
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [department, setDepartment] = useState<AgentDepartment>('engineering');
  const [avatarUrl, setAvatarUrl] = useState('');

  // Sync form state when config loads
  useEffect(() => {
    setDisplayName(config.displayName || '');
    setDescription(config.description || '');
    setDepartment(config.department || 'engineering');
    setAvatarUrl(config.avatarUrl || '');
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAgentFullConfig(agentId, {
        displayName: displayName || undefined,
        description: description || undefined,
        department,
        avatarUrl: avatarUrl || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentConfig', agentId] });
    },
  });

  const hasChanges =
    displayName !== (config.displayName || '') ||
    description !== (config.description || '') ||
    department !== (config.department || 'engineering') ||
    avatarUrl !== (config.avatarUrl || '');

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <User className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Agent Identity</h2>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Customize how this agent appears across the platform.
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Avatar Preview */}
        <div className="flex items-center gap-5">
          <div className="flex items-center justify-center w-16 h-16 rounded-xl bg-primary-50 text-primary-600 flex-shrink-0 overflow-hidden">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt="Agent avatar"
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            ) : (
              <User className="w-8 h-8" />
            )}
          </div>
          <div className="flex-1">
            <label htmlFor="avatarUrl" className="block text-sm font-medium text-gray-700 mb-1.5">
              Avatar URL
            </label>
            <input
              id="avatarUrl"
              type="url"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://example.com/avatar.png"
              className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              Provide a URL for a custom agent icon or avatar image.
            </p>
          </div>
        </div>

        {/* Display Name */}
        <div>
          <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 mb-1.5">
            Display Name
          </label>
          <input
            id="displayName"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Enter a display name"
            className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1.5">
            Description
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this agent does..."
            rows={4}
            className="w-full max-w-lg rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-y"
          />
          <p className="text-xs text-gray-400 mt-1">
            A brief description of the agent&apos;s purpose and responsibilities.
          </p>
        </div>

        {/* Department */}
        <div>
          <label htmlFor="department" className="block text-sm font-medium text-gray-700 mb-1.5">
            Department
          </label>
          <select
            id="department"
            value={department}
            onChange={(e) => setDepartment(e.target.value as AgentDepartment)}
            className="w-full max-w-md appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
          >
            {DEPARTMENTS.map((dept) => (
              <option key={dept.value} value={dept.value}>
                {dept.label}
              </option>
            ))}
          </select>
        </div>

        {/* Save Button */}
        <div className="flex items-center gap-3 pt-2">
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
                Save Identity
              </>
            )}
          </button>

          {saveMutation.isSuccess && (
            <p className="text-sm text-green-600">Identity saved successfully.</p>
          )}

          {saveMutation.isError && (
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <p className="text-sm text-red-600">Failed to save. Please try again.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
