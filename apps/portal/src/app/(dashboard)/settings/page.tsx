'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Loader2,
  AlertCircle,
  Building2,
  Users,
  Bell,
  Save,
  UserPlus,
  Trash2,
  Pencil,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getTenantDetails,
  updateTenant,
  getTeamUsers,
  inviteUser,
  updateUser,
  removeUser,
  getNotificationPreferences,
  updateNotificationPreferences,
} from '@/lib/api/settings.api';
import type {
  TenantDetails,
  TeamUser,
  InviteUserPayload,
  NotificationPref,
} from '@/lib/types/settings.types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const TABS = [
  { key: 'organization', label: 'Organization', icon: Building2 },
  { key: 'team', label: 'Team', icon: Users },
  { key: 'notifications', label: 'Notifications', icon: Bell },
] as const;

type TabKey = (typeof TABS)[number]['key'];

const ROLES = ['TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'END_USER', 'AUDITOR'] as const;

const roleColors: Record<string, string> = {
  PLATFORM_ADMIN: 'bg-purple-100 text-purple-800',
  TENANT_ADMIN: 'bg-blue-100 text-blue-800',
  DEPARTMENT_MANAGER: 'bg-green-100 text-green-800',
  END_USER: 'bg-gray-100 text-gray-800',
  AUDITOR: 'bg-amber-100 text-amber-800',
};

const userStatusColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  INVITED: 'bg-amber-100 text-amber-800',
  SUSPENDED: 'bg-red-100 text-red-800',
  DEACTIVATED: 'bg-gray-100 text-gray-600',
};

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

const EVENT_TYPE_LABELS: Record<string, string> = {
  'escalation.created': 'Escalation Created',
  'human.task.created': 'Human Task Created',
  'agent.status.changed': 'Agent Status Changed',
  'billing.invoice.created': 'Billing Invoice Created',
  'integration.connection.failed': 'Integration Connection Failed',
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

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

function formatRole(role: string): string {
  return role
    .split('_')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>('organization');

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your organization, team members, and notification preferences.
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
      {activeTab === 'organization' && <OrganizationTab />}
      {activeTab === 'team' && <TeamTab />}
      {activeTab === 'notifications' && <NotificationsTab />}
    </div>
  );
}

/* ================================================================== */
/*  TAB 1: Organization                                                */
/* ================================================================== */

function OrganizationTab() {
  const queryClient = useQueryClient();

  const {
    data: tenant,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['tenantDetails'],
    queryFn: getTenantDetails,
  });

  // Local form state
  const [name, setName] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [timezone, setTimezone] = useState('');

  // Sync form state when tenant loads
  useEffect(() => {
    if (tenant) {
      setName(tenant.name);
      setCountryCode(tenant.countryCode);
      setTimezone(tenant.timezone);
    }
  }, [tenant]);

  const updateMutation = useMutation({
    mutationFn: (data: { name?: string; countryCode?: string; timezone?: string }) =>
      updateTenant(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenantDetails'] });
    },
  });

  const hasChanges =
    tenant && (name !== tenant.name || countryCode !== tenant.countryCode || timezone !== tenant.timezone);

  function handleSave() {
    if (!tenant || !hasChanges) return;
    const payload: Record<string, string> = {};
    if (name !== tenant.name) payload.name = name;
    if (countryCode !== tenant.countryCode) payload.countryCode = countryCode;
    if (timezone !== tenant.timezone) payload.timezone = timezone;
    updateMutation.mutate(payload);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
        <p className="text-sm text-gray-500">Failed to load organization details.</p>
      </div>
    );
  }

  if (!tenant) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Organization Details</h2>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Tenant Name */}
        <div>
          <label htmlFor="org-name" className="block text-sm font-medium text-gray-700 mb-1.5">
            Organization Name
          </label>
          <input
            id="org-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Slug (read-only) */}
        <div>
          <label htmlFor="org-slug" className="block text-sm font-medium text-gray-700 mb-1.5">
            Slug
          </label>
          <input
            id="org-slug"
            type="text"
            value={tenant.slug}
            readOnly
            className="w-full max-w-md rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-500 cursor-not-allowed"
          />
          <p className="text-xs text-gray-400 mt-1">The slug cannot be changed.</p>
        </div>

        {/* Plan (read-only badge) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Plan</label>
          <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-primary-50 text-primary-700">
            {tenant.plan}
          </span>
        </div>

        {/* Country Code */}
        <div>
          <label
            htmlFor="org-country"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            Country Code
          </label>
          <input
            id="org-country"
            type="text"
            value={countryCode}
            onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
            maxLength={2}
            placeholder="US"
            className="w-full max-w-[120px] rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 uppercase"
          />
        </div>

        {/* Timezone */}
        <div>
          <label
            htmlFor="org-timezone"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            Timezone
          </label>
          <select
            id="org-timezone"
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

        {/* Save Button */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={!hasChanges || updateMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {updateMutation.isPending ? (
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

          {updateMutation.isSuccess && (
            <p className="text-sm text-green-600">Changes saved successfully.</p>
          )}

          {updateMutation.isError && (
            <p className="text-sm text-red-600">Failed to save changes. Please try again.</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  TAB 2: Team                                                        */
/* ================================================================== */

function TeamTab() {
  const queryClient = useQueryClient();
  const [teamPage, setTeamPage] = useState(1);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [editingUser, setEditingUser] = useState<TeamUser | null>(null);
  const [removeTarget, setRemoveTarget] = useState<TeamUser | null>(null);

  // Fetch team users
  const {
    data: teamData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['teamUsers', teamPage],
    queryFn: () => getTeamUsers({ page: teamPage, pageSize: 10 }),
  });

  // Remove user mutation
  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamUsers'] });
      setRemoveTarget(null);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
        <p className="text-sm text-gray-500">Failed to load team members.</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Team Members</h2>
            {teamData && (
              <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                {teamData.meta.totalItems}
              </span>
            )}
          </div>
          <button
            onClick={() => setShowInviteModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            Invite User
          </button>
        </div>

        {teamData && teamData.users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <Users className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No team members yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Invite users to start building your team.
            </p>
          </div>
        ) : teamData ? (
          <div className="p-6 space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Name</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Email</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Role</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                      Department
                    </th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Status</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                      Last Login
                    </th>
                    <th className="text-right py-2.5 font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {teamData.users.map((user) => (
                    <tr key={user.id} className="border-b border-gray-50 last:border-0">
                      <td className="py-3 pr-4 font-medium text-gray-900">{user.name}</td>
                      <td className="py-3 pr-4 text-gray-500">{user.email}</td>
                      <td className="py-3 pr-4">
                        <span
                          className={cn(
                            'inline-block px-2 py-0.5 rounded-full text-xs font-medium',
                            roleColors[user.role] || 'bg-gray-100 text-gray-800',
                          )}
                        >
                          {formatRole(user.role)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-gray-500">{user.department || '--'}</td>
                      <td className="py-3 pr-4">
                        <span
                          className={cn(
                            'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                            userStatusColors[user.status] || 'bg-gray-100 text-gray-600',
                          )}
                        >
                          {user.status.toLowerCase()}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-gray-500 text-xs">
                        {user.lastLoginAt ? formatDateTime(user.lastLoginAt) : 'Never'}
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <button
                            onClick={() => setEditingUser(user)}
                            className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                            title="Edit role"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                            Edit
                          </button>
                          <button
                            onClick={() => setRemoveTarget(user)}
                            className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                            title="Remove user"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {teamData.meta.totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-gray-400">
                  Page {teamData.meta.page} of {teamData.meta.totalPages} (
                  {teamData.meta.totalItems} members)
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setTeamPage((p) => Math.max(1, p - 1))}
                    disabled={teamPage <= 1}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    Previous
                  </button>
                  <button
                    onClick={() =>
                      setTeamPage((p) => Math.min(teamData.meta.totalPages, p + 1))
                    }
                    disabled={teamPage >= teamData.meta.totalPages}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Invite User Modal */}
      {showInviteModal && (
        <InviteUserModal onClose={() => setShowInviteModal(false)} />
      )}

      {/* Edit User Role Modal */}
      {editingUser && (
        <EditUserModal user={editingUser} onClose={() => setEditingUser(null)} />
      )}

      {/* Remove User Confirmation Dialog */}
      {removeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Remove {removeTarget.name}?
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              This will revoke {removeTarget.email}&apos;s access to the organization. This action
              cannot be undone.
            </p>

            {removeMutation.isError && (
              <div className="flex items-center gap-2 p-3 mt-3 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <p className="text-sm text-red-700">Failed to remove user. Please try again.</p>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setRemoveTarget(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => removeMutation.mutate(removeTarget.id)}
                disabled={removeMutation.isPending}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 transition-colors"
              >
                {removeMutation.isPending ? 'Removing...' : 'Confirm Remove'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Invite User Modal                                                  */
/* ------------------------------------------------------------------ */

function InviteUserModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<string>(ROLES[2]); // Default to END_USER
  const [department, setDepartment] = useState('');

  const inviteMutation = useMutation({
    mutationFn: (payload: InviteUserPayload) => inviteUser(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamUsers'] });
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !name.trim()) return;

    const payload: InviteUserPayload = {
      email: email.trim(),
      name: name.trim(),
      role,
    };
    if (department.trim()) {
      payload.department = department.trim();
    }
    inviteMutation.mutate(payload);
  }

  const isValid = email.trim().length > 0 && name.trim().length > 0 && /\S+@\S+\.\S+/.test(email);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-lg mx-4 w-full">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Invite User</h3>
              <p className="text-xs text-gray-500">
                Send an invitation to join your organization.
              </p>
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
          {/* Email */}
          <div>
            <label htmlFor="invite-email" className="block text-sm font-medium text-gray-700 mb-1.5">
              Email Address
            </label>
            <input
              id="invite-email"
              type="email"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Name */}
          <div>
            <label htmlFor="invite-name" className="block text-sm font-medium text-gray-700 mb-1.5">
              Full Name
            </label>
            <input
              id="invite-name"
              type="text"
              placeholder="Jane Smith"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Role */}
          <div>
            <label htmlFor="invite-role" className="block text-sm font-medium text-gray-700 mb-1.5">
              Role
            </label>
            <select
              id="invite-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {formatRole(r)}
                </option>
              ))}
            </select>
          </div>

          {/* Department */}
          <div>
            <label
              htmlFor="invite-department"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Department{' '}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              id="invite-department"
              type="text"
              placeholder="Engineering, Sales, etc."
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Error */}
          {inviteMutation.isError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">
                Failed to send invitation. Please try again.
              </p>
            </div>
          )}

          {/* Actions */}
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
              disabled={!isValid || inviteMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {inviteMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Sending...
                </>
              ) : (
                'Send Invitation'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Edit User Modal                                                    */
/* ------------------------------------------------------------------ */

function EditUserModal({ user, onClose }: { user: TeamUser; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [role, setRole] = useState(user.role);
  const [department, setDepartment] = useState(user.department || '');

  const editMutation = useMutation({
    mutationFn: (payload: { role?: string; department?: string }) =>
      updateUser(user.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamUsers'] });
      onClose();
    },
  });

  const hasChanges = role !== user.role || department !== (user.department || '');

  function handleSave() {
    if (!hasChanges) return;
    const payload: Record<string, string> = {};
    if (role !== user.role) payload.role = role;
    if (department !== (user.department || '')) payload.department = department;
    editMutation.mutate(payload);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4 w-full">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Edit User</h3>
            <p className="text-sm text-gray-500 mt-0.5">{user.name} ({user.email})</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Role */}
          <div>
            <label htmlFor="edit-role" className="block text-sm font-medium text-gray-700 mb-1.5">
              Role
            </label>
            <select
              id="edit-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {formatRole(r)}
                </option>
              ))}
            </select>
          </div>

          {/* Department */}
          <div>
            <label
              htmlFor="edit-department"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Department
            </label>
            <input
              id="edit-department"
              type="text"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              placeholder="Engineering, Sales, etc."
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          {/* Error */}
          {editMutation.isError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">
                Failed to update user. Please try again.
              </p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || editMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {editMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  TAB 3: Notifications                                               */
/* ================================================================== */

function NotificationsTab() {
  const queryClient = useQueryClient();

  const {
    data: preferences,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['notificationPreferences'],
    queryFn: getNotificationPreferences,
  });

  // Local state mirrors the server data so users can toggle before saving
  const [localPrefs, setLocalPrefs] = useState<NotificationPref[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (preferences) {
      setLocalPrefs(preferences);
      setDirty(false);
    }
  }, [preferences]);

  const saveMutation = useMutation({
    mutationFn: (prefs: NotificationPref[]) => updateNotificationPreferences(prefs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationPreferences'] });
      setDirty(false);
    },
  });

  function toggleEnabled(id: string) {
    setLocalPrefs((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p)),
    );
    setDirty(true);
  }

  function toggleChannel(id: string, channel: string) {
    setLocalPrefs((prev) =>
      prev.map((p) => {
        if (p.id !== id) return p;
        const channels = p.channels.includes(channel)
          ? p.channels.filter((c) => c !== channel)
          : [...p.channels, channel];
        return { ...p, channels };
      }),
    );
    setDirty(true);
  }

  function handleSave() {
    saveMutation.mutate(localPrefs);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
        <p className="text-sm text-gray-500">Failed to load notification preferences.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Notification Preferences</h2>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Choose which events you want to be notified about and how.
        </p>
      </div>

      <div className="p-6 space-y-1">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 pb-3 border-b border-gray-100">
          <div className="col-span-5">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Event</p>
          </div>
          <div className="col-span-2 text-center">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Email</p>
          </div>
          <div className="col-span-2 text-center">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Push</p>
          </div>
          <div className="col-span-3 text-center">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Enabled</p>
          </div>
        </div>

        {/* Notification Rows */}
        {localPrefs.map((pref) => (
          <div
            key={pref.id}
            className={cn(
              'grid grid-cols-12 gap-4 py-4 border-b border-gray-50 last:border-0 items-center',
              !pref.enabled && 'opacity-50',
            )}
          >
            {/* Event Type Label */}
            <div className="col-span-5">
              <p className="text-sm font-medium text-gray-900">
                {EVENT_TYPE_LABELS[pref.eventType] || pref.eventType}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">{pref.eventType}</p>
            </div>

            {/* Email Channel Toggle */}
            <div className="col-span-2 flex justify-center">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={pref.channels.includes('EMAIL')}
                  onChange={() => toggleChannel(pref.id, 'EMAIL')}
                  disabled={!pref.enabled}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600 peer-disabled:cursor-not-allowed peer-disabled:opacity-50" />
              </label>
            </div>

            {/* Push Channel Toggle */}
            <div className="col-span-2 flex justify-center">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={pref.channels.includes('PUSH')}
                  onChange={() => toggleChannel(pref.id, 'PUSH')}
                  disabled={!pref.enabled}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600 peer-disabled:cursor-not-allowed peer-disabled:opacity-50" />
              </label>
            </div>

            {/* Enabled Toggle */}
            <div className="col-span-3 flex justify-center">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={pref.enabled}
                  onChange={() => toggleEnabled(pref.id)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-green-600" />
              </label>
            </div>
          </div>
        ))}

        {localPrefs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12">
            <Bell className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-sm text-gray-400">No notification preferences configured.</p>
          </div>
        )}
      </div>

      {/* Save Button */}
      {localPrefs.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-100 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={!dirty || saveMutation.isPending}
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
                Save Preferences
              </>
            )}
          </button>

          {saveMutation.isSuccess && !dirty && (
            <p className="text-sm text-green-600">Preferences saved successfully.</p>
          )}

          {saveMutation.isError && (
            <p className="text-sm text-red-600">Failed to save preferences. Please try again.</p>
          )}
        </div>
      )}
    </div>
  );
}
