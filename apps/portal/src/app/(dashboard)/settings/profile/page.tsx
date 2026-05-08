'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Building2,
  Save,
  Loader2,
  AlertCircle,
  Upload,
  Globe,
  Clock,
  Link as LinkIcon,
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
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
  'Pacific/Auckland',
];

const LOCALES = [
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'fr-FR', label: 'French (France)' },
  { value: 'de-DE', label: 'German (Germany)' },
  { value: 'es-ES', label: 'Spanish (Spain)' },
  { value: 'pt-BR', label: 'Portuguese (Brazil)' },
  { value: 'ja-JP', label: 'Japanese' },
  { value: 'zh-CN', label: 'Chinese (Simplified)' },
  { value: 'ar-SA', label: 'Arabic (Saudi Arabia)' },
];

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function SettingsProfilePage() {
  const [companyName, setCompanyName] = useState('Acme Corp');
  const [timezone, setTimezone] = useState('UTC');
  const [locale, setLocale] = useState('en-US');
  const [domain, setDomain] = useState('acme.aisa.io');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    // Simulate API call
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your company profile and organization preferences.
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
                tab.href === '/settings/profile'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Company Profile Form */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Company Profile</h2>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Logo Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Company Logo</label>
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-20 h-20 rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 hover:border-primary-400 hover:bg-primary-50/30 transition-colors cursor-pointer">
                <Upload className="w-6 h-6 text-gray-400" />
              </div>
              <div>
                <button className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors">
                  Upload logo
                </button>
                <p className="text-xs text-gray-400 mt-1">
                  PNG, JPG, SVG. Max 2MB. Recommended 256x256.
                </p>
              </div>
            </div>
          </div>

          {/* Company Name */}
          <div>
            <label
              htmlFor="company-name"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Company Name
            </label>
            <input
              id="company-name"
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Timezone */}
          <div>
            <label htmlFor="profile-tz" className="block text-sm font-medium text-gray-700 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-gray-400" />
                Timezone
              </span>
            </label>
            <select
              id="profile-tz"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full max-w-md appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>

          {/* Locale */}
          <div>
            <label
              htmlFor="profile-locale"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              <span className="flex items-center gap-1.5">
                <Globe className="w-4 h-4 text-gray-400" />
                Locale
              </span>
            </label>
            <select
              id="profile-locale"
              value={locale}
              onChange={(e) => setLocale(e.target.value)}
              className="w-full max-w-md appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              {LOCALES.map((loc) => (
                <option key={loc.value} value={loc.value}>
                  {loc.label}
                </option>
              ))}
            </select>
          </div>

          {/* Domain */}
          <div>
            <label
              htmlFor="profile-domain"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              <span className="flex items-center gap-1.5">
                <LinkIcon className="w-4 h-4 text-gray-400" />
                Custom Domain
              </span>
            </label>
            <input
              id="profile-domain"
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="your-company.aisa.io"
              className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              Your workspace will be accessible at this domain.
            </p>
          </div>

          {/* Save */}
          <div className="flex items-center gap-3 pt-2">
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
                  Save Changes
                </>
              )}
            </button>
            {saved && <p className="text-sm text-green-600">Profile saved successfully.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
