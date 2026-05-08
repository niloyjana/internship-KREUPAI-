'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Users,
  UserPlus,
  Pencil,
  Ban,
  AlertCircle,
  X,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
  Shield,
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

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'invited' | 'deactivated';
  lastActive: string | null;
}

const ROLES = ['TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'END_USER', 'AUDITOR'];

const roleColors: Record<string, string> = {
  TENANT_ADMIN: 'bg-blue-100 text-blue-800',
  DEPARTMENT_MANAGER: 'bg-green-100 text-green-800',
  END_USER: 'bg-gray-100 text-gray-800',
  AUDITOR: 'bg-amber-100 text-amber-800',
};

const statusColors: Record<string, string> = {
  active: 'bg-green-50 text-green-700',
  invited: 'bg-amber-50 text-amber-700',
  deactivated: 'bg-gray-100 text-gray-500',
};

const MOCK_TEAM: TeamMember[] = [
  { id: '1', name: 'Sarah Chen', email: 'sarah@acme.com', role: 'TENANT_ADMIN', status: 'active', lastActive: '2026-03-11T08:30:00Z' },
  { id: '2', name: 'James Wilson', email: 'james@acme.com', role: 'DEPARTMENT_MANAGER', status: 'active', lastActive: '2026-03-10T16:45:00Z' },
  { id: '3', name: 'Priya Patel', email: 'priya@acme.com', role: 'END_USER', status: 'active', lastActive: '2026-03-09T12:00:00Z' },
  { id: '4', name: 'Alex Thompson', email: 'alex@acme.com', role: 'AUDITOR', status: 'invited', lastActive: null },
  { id: '5', name: 'Maria Garcia', email: 'maria@acme.com', role: 'END_USER', status: 'deactivated', lastActive: '2026-02-15T09:20:00Z' },
];

function formatRole(role: string): string {
  return role.split('_').map((w) => w.charAt(0) + w.slice(1).toLowerCase()).join(' ');
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function SettingsTeamPage() {
  const [members, setMembers] = useState<TeamMember[]>(MOCK_TEAM);
  const [searchQuery, setSearchQuery] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null);

  const filtered = members.filter(
    (m) =>
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  function handleDeactivate(id: string) {
    setMembers((prev) =>
      prev.map((m) => (m.id === id ? { ...m, status: 'deactivated' as const } : m)),
    );
  }

  function handleActivate(id: string) {
    setMembers((prev) =>
      prev.map((m) => (m.id === id ? { ...m, status: 'active' as const } : m)),
    );
  }

  function handleRoleChange(id: string, newRole: string) {
    setMembers((prev) =>
      prev.map((m) => (m.id === id ? { ...m, role: newRole } : m)),
    );
    setEditingMember(null);
  }

  function handleInvite(email: string, role: string) {
    const newMember: TeamMember = {
      id: String(Date.now()),
      name: email.split('@')[0],
      email,
      role,
      status: 'invited',
      lastActive: null,
    };
    setMembers((prev) => [...prev, newMember]);
    setShowInviteModal(false);
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your team members and their access levels.
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
                tab.href === '/settings/team'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Team Members Card */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Team Members</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {members.length}
            </span>
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:flex-initial">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search members..."
                className="w-full sm:w-56 rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
            <button
              onClick={() => setShowInviteModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors whitespace-nowrap"
            >
              <UserPlus className="w-4 h-4" />
              Invite
            </button>
          </div>
        </div>

        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Name</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Email</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Role</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Last Active</th>
                  <th className="text-right py-2.5 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((member) => (
                  <tr key={member.id} className="border-b border-gray-50 last:border-0">
                    <td className="py-3 pr-4 font-medium text-gray-900">{member.name}</td>
                    <td className="py-3 pr-4 text-gray-500">{member.email}</td>
                    <td className="py-3 pr-4">
                      <span
                        className={cn(
                          'inline-block px-2 py-0.5 rounded-full text-xs font-medium',
                          roleColors[member.role] || 'bg-gray-100 text-gray-800',
                        )}
                      >
                        {formatRole(member.role)}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={cn(
                          'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                          statusColors[member.status],
                        )}
                      >
                        {member.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-gray-500 text-xs">
                      {member.lastActive ? formatDateTime(member.lastActive) : 'Never'}
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button
                          onClick={() => setEditingMember(member)}
                          className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          Edit Role
                        </button>
                        {member.status === 'active' || member.status === 'invited' ? (
                          <button
                            onClick={() => handleDeactivate(member.id)}
                            className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                          >
                            <Ban className="w-3.5 h-3.5" />
                            Deactivate
                          </button>
                        ) : (
                          <button
                            onClick={() => handleActivate(member.id)}
                            className="inline-flex items-center gap-1 text-xs text-green-600 hover:text-green-700 font-medium transition-colors"
                          >
                            <Shield className="w-3.5 h-3.5" />
                            Activate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-sm text-gray-400">
                      No members found matching your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <InviteModal onClose={() => setShowInviteModal(false)} onInvite={handleInvite} />
      )}

      {/* Edit Role Modal */}
      {editingMember && (
        <EditRoleModal
          member={editingMember}
          onClose={() => setEditingMember(null)}
          onSave={handleRoleChange}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Invite Modal                                                        */
/* ------------------------------------------------------------------ */

function InviteModal({
  onClose,
  onInvite,
}: {
  onClose: () => void;
  onInvite: (email: string, role: string) => void;
}) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('END_USER');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    onInvite(email.trim(), role);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4 w-full">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Invite Team Member</h3>
              <p className="text-xs text-gray-500">Send an invitation to join your team.</p>
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
            <label htmlFor="invite-email" className="block text-sm font-medium text-gray-700 mb-1.5">
              Email Address
            </label>
            <input
              id="invite-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@company.com"
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

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
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              Send Invitation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Edit Role Modal                                                     */
/* ------------------------------------------------------------------ */

function EditRoleModal({
  member,
  onClose,
  onSave,
}: {
  member: TeamMember;
  onClose: () => void;
  onSave: (id: string, role: string) => void;
}) {
  const [role, setRole] = useState(member.role);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4 w-full">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Edit Role</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              {member.name} ({member.email})
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

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

        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(member.id, role)}
            disabled={role === member.role}
            className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
