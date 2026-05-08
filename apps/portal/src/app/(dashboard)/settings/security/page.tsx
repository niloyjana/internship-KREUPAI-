'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Shield,
  ShieldCheck,
  Smartphone,
  Lock,
  Clock,
  Key,
  AlertCircle,
  Loader2,
  Save,
  Copy,
  Trash2,
  Plus,
  X,
  Eye,
  EyeOff,
  CheckCircle2,
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
    name: 'Production Key',
    prefix: 'aisa_live_7x8k',
    createdAt: '2026-01-15T10:00:00Z',
    lastUsedAt: '2026-03-11T08:30:00Z',
    status: 'active',
  },
  {
    id: '2',
    name: 'Staging Key',
    prefix: 'aisa_test_3m9p',
    createdAt: '2026-02-01T14:00:00Z',
    lastUsedAt: '2026-03-10T16:00:00Z',
    status: 'active',
  },
  {
    id: '3',
    name: 'Old Development Key',
    prefix: 'aisa_dev_1a2b',
    createdAt: '2025-11-20T09:00:00Z',
    lastUsedAt: '2026-01-05T11:00:00Z',
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

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function SettingsSecurityPage() {
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [mfaToggling, setMfaToggling] = useState(false);

  // Password policy
  const [minLength, setMinLength] = useState(12);
  const [requireUppercase, setRequireUppercase] = useState(true);
  const [requireNumbers, setRequireNumbers] = useState(true);
  const [requireSpecial, setRequireSpecial] = useState(true);
  const [policySaving, setPolicySaving] = useState(false);
  const [policySaved, setPolicySaved] = useState(false);

  // Session timeout
  const [sessionTimeout, setSessionTimeout] = useState(60);
  const [timeoutSaving, setTimeoutSaving] = useState(false);
  const [timeoutSaved, setTimeoutSaved] = useState(false);

  // API Keys
  const [apiKeys, setApiKeys] = useState<ApiKey[]>(MOCK_API_KEYS);
  const [showCreateKeyModal, setShowCreateKeyModal] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<ApiKey | null>(null);

  async function handleMfaToggle() {
    setMfaToggling(true);
    await new Promise((r) => setTimeout(r, 600));
    setMfaEnabled((prev) => !prev);
    setMfaToggling(false);
  }

  async function handlePolicySave() {
    setPolicySaving(true);
    await new Promise((r) => setTimeout(r, 500));
    setPolicySaving(false);
    setPolicySaved(true);
    setTimeout(() => setPolicySaved(false), 3000);
  }

  async function handleTimeoutSave() {
    setTimeoutSaving(true);
    await new Promise((r) => setTimeout(r, 500));
    setTimeoutSaving(false);
    setTimeoutSaved(true);
    setTimeout(() => setTimeoutSaved(false), 3000);
  }

  function handleRevokeKey(id: string) {
    setApiKeys((prev) => prev.map((k) => (k.id === id ? { ...k, status: 'revoked' as const } : k)));
    setRevokeTarget(null);
  }

  function handleCreateKey(name: string) {
    const newKey: ApiKey = {
      id: String(Date.now()),
      name,
      prefix: `aisa_live_${Math.random().toString(36).slice(2, 6)}`,
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      status: 'active',
    };
    setApiKeys((prev) => [...prev, newKey]);
    setShowCreateKeyModal(false);
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure security, authentication, and access controls.
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
                tab.href === '/settings/security'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* MFA Toggle */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">
              Multi-Factor Authentication (MFA)
            </h2>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Require all team members to use MFA when signing in.
              </p>
              <p className="text-xs text-gray-400 mt-1">
                This adds an extra layer of security to all accounts.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {mfaToggling && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={mfaEnabled}
                  onChange={handleMfaToggle}
                  disabled={mfaToggling}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600 peer-disabled:cursor-not-allowed peer-disabled:opacity-50" />
              </label>
            </div>
          </div>
          {mfaEnabled && (
            <div className="mt-4 flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200">
              <ShieldCheck className="w-4 h-4 text-green-600 flex-shrink-0" />
              <p className="text-sm text-green-700">MFA is enabled for all team members.</p>
            </div>
          )}
        </div>
      </div>

      {/* Password Policy */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Password Policy</h2>
          </div>
        </div>
        <div className="p-6 space-y-5">
          {/* Min Length */}
          <div>
            <label htmlFor="min-length" className="block text-sm font-medium text-gray-700 mb-1.5">
              Minimum Password Length
            </label>
            <input
              id="min-length"
              type="number"
              min={8}
              max={64}
              value={minLength}
              onChange={(e) => setMinLength(Number(e.target.value))}
              className="w-32 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Requirements */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-gray-700">Requirements</p>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={requireUppercase}
                onChange={(e) => setRequireUppercase(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-600">Require uppercase letters (A-Z)</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={requireNumbers}
                onChange={(e) => setRequireNumbers(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-600">Require numbers (0-9)</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={requireSpecial}
                onChange={(e) => setRequireSpecial(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-600">Require special characters (!@#$%)</span>
            </label>
          </div>

          {/* Save */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handlePolicySave}
              disabled={policySaving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {policySaving ? (
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
            {policySaved && <p className="text-sm text-green-600">Password policy updated.</p>}
          </div>
        </div>
      </div>

      {/* Session Timeout */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Session Timeout</h2>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label
              htmlFor="session-timeout"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Idle Timeout (minutes)
            </label>
            <select
              id="session-timeout"
              value={sessionTimeout}
              onChange={(e) => setSessionTimeout(Number(e.target.value))}
              className="w-48 appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              <option value={15}>15 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={60}>1 hour</option>
              <option value={120}>2 hours</option>
              <option value={480}>8 hours</option>
              <option value={1440}>24 hours</option>
            </select>
            <p className="text-xs text-gray-400 mt-1">
              Users will be signed out after this period of inactivity.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleTimeoutSave}
              disabled={timeoutSaving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {timeoutSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save
                </>
              )}
            </button>
            {timeoutSaved && <p className="text-sm text-green-600">Session timeout updated.</p>}
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">API Keys</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {apiKeys.filter((k) => k.status === 'active').length} active
            </span>
          </div>
          <button
            onClick={() => setShowCreateKeyModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Key
          </button>
        </div>

        <div className="p-6">
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
                {apiKeys.map((key) => (
                  <tr key={key.id} className="border-b border-gray-50 last:border-0">
                    <td className="py-3 pr-4 font-medium text-gray-900">{key.name}</td>
                    <td className="py-3 pr-4">
                      <code className="px-2 py-0.5 rounded bg-gray-100 text-xs font-mono text-gray-600">
                        {key.prefix}...
                      </code>
                    </td>
                    <td className="py-3 pr-4 text-gray-500 text-xs">{formatDate(key.createdAt)}</td>
                    <td className="py-3 pr-4 text-gray-500 text-xs">
                      {key.lastUsedAt ? formatDate(key.lastUsedAt) : 'Never'}
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
                      {key.status === 'active' && (
                        <button
                          onClick={() => setRevokeTarget(key)}
                          className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Create Key Modal */}
      {showCreateKeyModal && (
        <CreateKeyModal onClose={() => setShowCreateKeyModal(false)} onCreate={handleCreateKey} />
      )}

      {/* Revoke Key Confirmation */}
      {revokeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Revoke &quot;{revokeTarget.name}&quot;?
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              This API key will be immediately invalidated. Any applications using this key will
              lose access. This action cannot be undone.
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
              <p className="text-xs text-gray-500">Generate a new API key for your application.</p>
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
              placeholder="e.g. Production API"
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              Give your key a descriptive name so you can identify it later.
            </p>
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
              Create Key
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
