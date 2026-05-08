'use client';

import { useState } from 'react';
import {
  Settings,
  Shield,
  ToggleLeft,
  ToggleRight,
  Save,
  Loader2,
  Globe,
  Mail,
  Clock,
  Lock,
  Database,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  category: 'agents' | 'billing' | 'security' | 'general';
}

/* ------------------------------------------------------------------ */
/*  Placeholder Data                                                   */
/* ------------------------------------------------------------------ */

const INITIAL_FLAGS: FeatureFlag[] = [
  {
    id: 'ff-1',
    name: 'Multi-Tenant SSO',
    description: 'Enable SSO configuration for enterprise tenants',
    enabled: true,
    category: 'security',
  },
  {
    id: 'ff-2',
    name: 'Agent Auto-Scaling',
    description: 'Automatically scale agent instances based on demand',
    enabled: true,
    category: 'agents',
  },
  {
    id: 'ff-3',
    name: 'Usage-Based Billing',
    description: 'Enable per-task usage-based billing model',
    enabled: false,
    category: 'billing',
  },
  {
    id: 'ff-4',
    name: 'Advanced Analytics',
    description: 'Enable advanced analytics dashboard for tenants',
    enabled: true,
    category: 'general',
  },
  {
    id: 'ff-5',
    name: 'Webhook Notifications',
    description: 'Allow tenants to configure webhook endpoints',
    enabled: true,
    category: 'general',
  },
  {
    id: 'ff-6',
    name: 'Custom Agent Templates',
    description: 'Allow tenants to create custom agent templates',
    enabled: false,
    category: 'agents',
  },
  {
    id: 'ff-7',
    name: 'Two-Factor Enforcement',
    description: 'Require 2FA for all platform admin accounts',
    enabled: true,
    category: 'security',
  },
  {
    id: 'ff-8',
    name: 'Trial Extensions',
    description: 'Allow automatic trial period extensions',
    enabled: false,
    category: 'billing',
  },
  {
    id: 'ff-9',
    name: 'Auto-Suspend Overdue',
    description: 'Automatically suspend tenants with overdue invoices after 30 days',
    enabled: true,
    category: 'billing',
  },
  {
    id: 'ff-10',
    name: 'Agent Marketplace',
    description: 'Enable the public agent marketplace for third-party agents',
    enabled: false,
    category: 'agents',
  },
];

const CATEGORIES = [
  { key: '', label: 'All' },
  { key: 'agents', label: 'Agents' },
  { key: 'billing', label: 'Billing' },
  { key: 'security', label: 'Security' },
  { key: 'general', label: 'General' },
];

const categoryColors: Record<string, string> = {
  agents: 'bg-blue-50 text-blue-700',
  billing: 'bg-purple-50 text-purple-700',
  security: 'bg-red-50 text-red-700',
  general: 'bg-gray-100 text-gray-700',
};

const TABS = [
  { key: 'defaults', label: 'Default Config', icon: Settings },
  { key: 'features', label: 'Feature Flags', icon: ToggleLeft },
] as const;

type TabKey = (typeof TABS)[number]['key'];

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('defaults');

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Platform Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure default platform settings and manage feature flags.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-8" aria-label="Settings tabs">
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
      {activeTab === 'defaults' && <DefaultConfigTab />}
      {activeTab === 'features' && <FeatureFlagsTab />}
    </div>
  );
}

/* ================================================================== */
/*  TAB 1: Default Configuration                                       */
/* ================================================================== */

function DefaultConfigTab() {
  const [platformName, setPlatformName] = useState('AISA — AI Digital Workforce Platform');
  const [defaultPlan, setDefaultPlan] = useState('starter');
  const [trialDays, setTrialDays] = useState(14);
  const [maxUsersPerTenant, setMaxUsersPerTenant] = useState(50);
  const [maxAgentsPerTenant, setMaxAgentsPerTenant] = useState(25);
  const [defaultTimezone, setDefaultTimezone] = useState('UTC');
  const [sessionTimeoutMinutes, setSessionTimeoutMinutes] = useState(60);
  const [supportEmail, setSupportEmail] = useState('support@aisa.io');
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    // TODO: call platform settings API
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="space-y-6">
      {/* General Settings */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">General</h2>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Platform Name */}
          <div>
            <label
              htmlFor="platform-name"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Platform Name
            </label>
            <input
              id="platform-name"
              type="text"
              value={platformName}
              onChange={(e) => setPlatformName(e.target.value)}
              className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Support Email */}
          <div>
            <label
              htmlFor="support-email"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              <span className="flex items-center gap-1.5">
                <Mail className="w-4 h-4 text-gray-400" />
                Support Email
              </span>
            </label>
            <input
              id="support-email"
              type="email"
              value={supportEmail}
              onChange={(e) => setSupportEmail(e.target.value)}
              className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Maintenance Mode */}
          <div className="flex items-center justify-between max-w-md">
            <div>
              <p className="text-sm font-medium text-gray-700">Maintenance Mode</p>
              <p className="text-xs text-gray-400 mt-0.5">
                When enabled, all tenant portals show a maintenance notice.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={maintenanceMode}
                onChange={(e) => setMaintenanceMode(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-500 peer-disabled:cursor-not-allowed" />
            </label>
          </div>

          {maintenanceMode && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 max-w-md">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">
                Maintenance mode is active. Tenant portals are showing maintenance notices.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Tenant Defaults */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Tenant Defaults</h2>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Default settings applied to new tenant accounts.
          </p>
        </div>

        <div className="p-6 space-y-5">
          {/* Default Plan */}
          <div>
            <label
              htmlFor="default-plan"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Default Plan
            </label>
            <select
              id="default-plan"
              value={defaultPlan}
              onChange={(e) => setDefaultPlan(e.target.value)}
              className="w-full max-w-md appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          {/* Trial Duration */}
          <div>
            <label htmlFor="trial-days" className="block text-sm font-medium text-gray-700 mb-1.5">
              Trial Period (days)
            </label>
            <input
              id="trial-days"
              type="number"
              min={0}
              max={90}
              value={trialDays}
              onChange={(e) => setTrialDays(Number(e.target.value))}
              className="w-32 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              Number of days for new tenant trial periods. Set to 0 to disable.
            </p>
          </div>

          {/* Max Users */}
          <div>
            <label htmlFor="max-users" className="block text-sm font-medium text-gray-700 mb-1.5">
              Max Users per Tenant
            </label>
            <input
              id="max-users"
              type="number"
              min={1}
              max={10000}
              value={maxUsersPerTenant}
              onChange={(e) => setMaxUsersPerTenant(Number(e.target.value))}
              className="w-32 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Max Agents */}
          <div>
            <label htmlFor="max-agents" className="block text-sm font-medium text-gray-700 mb-1.5">
              Max Agents per Tenant
            </label>
            <input
              id="max-agents"
              type="number"
              min={1}
              max={100}
              value={maxAgentsPerTenant}
              onChange={(e) => setMaxAgentsPerTenant(Number(e.target.value))}
              className="w-32 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Default Timezone */}
          <div>
            <label htmlFor="default-tz" className="block text-sm font-medium text-gray-700 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-gray-400" />
                Default Timezone
              </span>
            </label>
            <select
              id="default-tz"
              value={defaultTimezone}
              onChange={(e) => setDefaultTimezone(e.target.value)}
              className="w-full max-w-md appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              {[
                'UTC',
                'America/New_York',
                'America/Chicago',
                'America/Denver',
                'America/Los_Angeles',
                'Europe/London',
                'Europe/Paris',
                'Europe/Berlin',
                'Asia/Dubai',
                'Asia/Kolkata',
                'Asia/Singapore',
                'Asia/Tokyo',
                'Australia/Sydney',
              ].map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Security Defaults */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Security Defaults</h2>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Session Timeout */}
          <div>
            <label
              htmlFor="session-timeout"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Session Timeout
            </label>
            <select
              id="session-timeout"
              value={sessionTimeoutMinutes}
              onChange={(e) => setSessionTimeoutMinutes(Number(e.target.value))}
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
              Default session timeout for all tenants. Individual tenants can override this value.
            </p>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save All Settings
            </>
          )}
        </button>
        {saved && <p className="text-sm text-green-600">Settings saved successfully.</p>}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  TAB 2: Feature Flags                                               */
/* ================================================================== */

function FeatureFlagsTab() {
  const [flags, setFlags] = useState<FeatureFlag[]>(INITIAL_FLAGS);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);

  const filtered = categoryFilter ? flags.filter((f) => f.category === categoryFilter) : flags;

  function toggleFlag(id: string) {
    setFlags((prev) => prev.map((f) => (f.id === id ? { ...f, enabled: !f.enabled } : f)));
    setDirty(true);
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    // TODO: call feature flags API
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    setSaved(true);
    setDirty(false);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="space-y-6">
      {/* Filter */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <div className="flex items-center gap-3">
          <Shield className="w-4 h-4 text-gray-400" />
          <div className="flex items-center gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setCategoryFilter(cat.key)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  categoryFilter === cat.key
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Flags List */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ToggleRight className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Feature Flags</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {flags.filter((f) => f.enabled).length} / {flags.length} enabled
            </span>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {filtered.map((flag) => (
            <div key={flag.id} className="p-6 flex items-center justify-between">
              <div className="flex-1 min-w-0 mr-4">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-semibold text-gray-900">{flag.name}</p>
                  <span
                    className={cn(
                      'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                      categoryColors[flag.category] || 'bg-gray-100 text-gray-700',
                    )}
                  >
                    {flag.category}
                  </span>
                </div>
                <p className="text-xs text-gray-500">{flag.description}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                <input
                  type="checkbox"
                  checked={flag.enabled}
                  onChange={() => toggleFlag(flag.id)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600" />
              </label>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16">
              <ToggleLeft className="w-8 h-8 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">No feature flags in this category.</p>
            </div>
          )}
        </div>

        {/* Save */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Feature Flags
              </>
            )}
          </button>
          {saved && !dirty && (
            <p className="text-sm text-green-600">Feature flags saved successfully.</p>
          )}
        </div>
      </div>
    </div>
  );
}
