'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  X,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Sub-navigation                                                      */
/* ------------------------------------------------------------------ */

const settingsTabs = [
  { label: 'Profile', href: '/settings/profile' },
  { label: 'Team', href: '/settings/team' },
  { label: 'Security', href: '/settings/security' },
  { label: 'API Keys', href: '/settings/api-keys' },
];

/* ------------------------------------------------------------------ */
/*  Types & Mock Data                                                   */
/* ------------------------------------------------------------------ */

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsedAt: string | null;
  status: 'active' | 'revoked';
}

const MOCK_API_KEYS: ApiKey[] = [
  {
    id: '1',
    name: 'Production API',
    prefix: 'aisa_live_7x8k',
    createdAt: '2026-01-15T10:00:00Z',
    lastUsedAt: '2026-03-11T08:30:00Z',
    status: 'active',
  },
  {
    id: '2',
    name: 'Staging API',
    prefix: 'aisa_test_3m9p',
    createdAt: '2026-02-01T14:00:00Z',
    lastUsedAt: '2026-03-10T16:00:00Z',
    status: 'active',
  },
  {
    id: '3',
    name: 'CI/CD Pipeline',
    prefix: 'aisa_ci_5n7q',
    createdAt: '2026-02-15T09:00:00Z',
    lastUsedAt: '2026-03-11T06:45:00Z',
    status: 'active',
  },
  {
    id: '4',
    name: 'Development (old)',
    prefix: 'aisa_dev_1a2b',
    createdAt: '2025-11-20T09:00:00Z',
    lastUsedAt: '2026-01-05T11:00:00Z',
    status: 'revoked',
  },
  {
    id: '5',
    name: 'Testing Key',
    prefix: 'aisa_test_9z0y',
    createdAt: '2025-12-10T16:00:00Z',
    lastUsedAt: null,
    status: 'revoked',
  },
];

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function SettingsApiKeysPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>(MOCK_API_KEYS);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiKey | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filtered = apiKeys.filter(
    (k) =>
      k.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      k.prefix.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  function handleCreateKey(name: string) {
    const fullKey = `aisa_live_${Math.random().toString(36).slice(2, 10)}${Math.random().toString(36).slice(2, 10)}`;
    const newKey: ApiKey = {
      id: String(Date.now()),
      name,
      prefix: fullKey.slice(0, 14),
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      status: 'active',
    };
    setApiKeys((prev) => [newKey, ...prev]);
    setNewlyCreatedKey(fullKey);
    setShowCreateModal(false);
  }

  function handleRevokeKey(id: string) {
    setApiKeys((prev) => prev.map((k) => (k.id === id ? { ...k, status: 'revoked' as const } : k)));
    setRevokeTarget(null);
  }

  function handleCopyPrefix(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  const activeCount = apiKeys.filter((k) => k.status === 'active').length;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage API keys for programmatic access to the AISA platform.
        </p>
      </div>

      {/* Sub-navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {settingsTabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                tab.href === '/settings/api-keys'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Newly Created Key Banner */}
      {newlyCreatedKey && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-800">API key created successfully</p>
              <p className="text-xs text-green-600 mt-1">
                Copy your key now. You will not be able to see it again.
              </p>
              <div className="flex items-center gap-2 mt-3">
                <code className="flex-1 px-3 py-2 rounded-lg bg-white border border-green-300 text-sm font-mono text-gray-900 break-all">
                  {newlyCreatedKey}
                </code>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(newlyCreatedKey);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
                >
                  <Copy className="w-4 h-4" />
                  Copy
                </button>
              </div>
            </div>
            <button
              onClick={() => setNewlyCreatedKey(null)}
              className="p-1 rounded-md text-green-400 hover:text-green-600 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* API Keys Table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">API Keys</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {activeCount} active
            </span>
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:flex-initial">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search keys..."
                className="w-full sm:w-56 rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors whitespace-nowrap"
            >
              <Plus className="w-4 h-4" />
              Create Key
            </button>
          </div>
        </div>

        <div className="p-6">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                <Key className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-600">
                {searchQuery ? 'No keys match your search' : 'No API keys yet'}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Create an API key to get started with the AISA API.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Name</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Key Prefix</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Created</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Last Used</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Status</th>
                    <th className="text-right py-2.5 font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((key) => (
                    <tr key={key.id} className="border-b border-gray-50 last:border-0">
                      <td className="py-3 pr-4 font-medium text-gray-900">{key.name}</td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <code className="px-2 py-0.5 rounded bg-gray-100 text-xs font-mono text-gray-600">
                            {key.prefix}...
                          </code>
                          <button
                            onClick={() => handleCopyPrefix(key.id, key.prefix)}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title="Copy prefix"
                          >
                            {copiedId === key.id ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-gray-500 text-xs">
                        {formatDate(key.createdAt)}
                      </td>
                      <td className="py-3 pr-4 text-gray-500 text-xs">
                        {key.lastUsedAt ? formatDateTime(key.lastUsedAt) : 'Never'}
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={cn(
                            'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                            key.status === 'active'
                              ? 'bg-green-50 text-green-700'
                              : 'bg-gray-100 text-gray-500',
                          )}
                        >
                          {key.status}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        {key.status === 'active' ? (
                          <button
                            onClick={() => setRevokeTarget(key)}
                            className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Revoke
                          </button>
                        ) : (
                          <span className="text-xs text-gray-400">Revoked</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Create Key Modal */}
      {showCreateModal && (
        <CreateKeyModal onClose={() => setShowCreateModal(false)} onCreate={handleCreateKey} />
      )}

      {/* Revoke Confirmation */}
      {revokeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-50">
                <AlertCircle className="w-5 h-5 text-red-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Revoke API Key</h3>
            </div>
            <p className="text-sm text-gray-500">
              Are you sure you want to revoke <strong>{revokeTarget.name}</strong> (
              <code className="text-xs">{revokeTarget.prefix}...</code>)? This will immediately
              invalidate the key and cannot be undone.
            </p>
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setRevokeTarget(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleRevokeKey(revokeTarget.id)}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
              >
                Revoke Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Create Key Modal                                                    */
/* ------------------------------------------------------------------ */

function CreateKeyModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (name: string) => void;
}) {
  const [name, setName] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate(name.trim());
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4 w-full">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Create API Key</h3>
              <p className="text-xs text-gray-500">Generate a new key for API access.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="key-name" className="block text-sm font-medium text-gray-700 mb-1.5">
              Key Name
            </label>
            <input
              id="key-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production API, CI/CD Pipeline"
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Key
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
