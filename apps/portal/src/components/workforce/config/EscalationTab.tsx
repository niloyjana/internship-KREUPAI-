'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Save,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Plus,
  Trash2,
  Clock,
  Users,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { updateAgentFullConfig } from '@/lib/api/agent-config.api';
import type {
  AgentFullConfig,
  EscalationRule,
  EscalationContact,
} from '@/lib/types/agent.types';

const PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;
const ACTIONS = ['notify', 'escalate', 'pause_agent'] as const;

const priorityColors: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-amber-100 text-amber-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

const actionLabels: Record<string, string> = {
  notify: 'Notify',
  escalate: 'Escalate',
  pause_agent: 'Pause Agent',
};

function generateId(): string {
  return `esc_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

interface EscalationTabProps {
  agentId: string;
  config: AgentFullConfig;
}

export default function EscalationTab({ agentId, config }: EscalationTabProps) {
  const queryClient = useQueryClient();

  const [rules, setRules] = useState<EscalationRule[]>([]);
  const [slaMinutes, setSlaMinutes] = useState(60);
  const [contacts, setContacts] = useState<EscalationContact[]>([]);
  const [showAddRule, setShowAddRule] = useState(false);
  const [showAddContact, setShowAddContact] = useState(false);

  // New rule form
  const [newRuleCondition, setNewRuleCondition] = useState('');
  const [newRulePriority, setNewRulePriority] = useState<EscalationRule['priority']>('medium');
  const [newRuleAction, setNewRuleAction] = useState<EscalationRule['action']>('notify');
  const [newRuleDescription, setNewRuleDescription] = useState('');

  // New contact form
  const [newContactName, setNewContactName] = useState('');
  const [newContactEmail, setNewContactEmail] = useState('');
  const [newContactRole, setNewContactRole] = useState('');
  const [newContactIsPrimary, setNewContactIsPrimary] = useState(false);

  useEffect(() => {
    if (config.escalation) {
      setRules(config.escalation.rules || []);
      setSlaMinutes(config.escalation.slaMinutes || 60);
      setContacts(config.escalation.contacts || []);
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAgentFullConfig(agentId, {
        escalation: {
          rules,
          slaMinutes,
          contacts,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentConfig', agentId] });
    },
  });

  function addRule() {
    if (!newRuleCondition.trim()) return;
    const rule: EscalationRule = {
      id: generateId(),
      condition: newRuleCondition.trim(),
      priority: newRulePriority,
      action: newRuleAction,
      description: newRuleDescription.trim(),
    };
    setRules((prev) => [...prev, rule]);
    resetRuleForm();
  }

  function removeRule(id: string) {
    setRules((prev) => prev.filter((r) => r.id !== id));
  }

  function resetRuleForm() {
    setNewRuleCondition('');
    setNewRulePriority('medium');
    setNewRuleAction('notify');
    setNewRuleDescription('');
    setShowAddRule(false);
  }

  function addContact() {
    if (!newContactName.trim() || !newContactEmail.trim()) return;
    const contact: EscalationContact = {
      id: generateId(),
      name: newContactName.trim(),
      email: newContactEmail.trim(),
      role: newContactRole.trim(),
      isPrimary: newContactIsPrimary,
    };
    setContacts((prev) => [...prev, contact]);
    resetContactForm();
  }

  function removeContact(id: string) {
    setContacts((prev) => prev.filter((c) => c.id !== id));
  }

  function resetContactForm() {
    setNewContactName('');
    setNewContactEmail('');
    setNewContactRole('');
    setNewContactIsPrimary(false);
    setShowAddContact(false);
  }

  return (
    <div className="space-y-6">
      {/* SLA Settings */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">SLA Settings</h2>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Define the service level agreement for escalation response times.
          </p>
        </div>

        <div className="p-6">
          <div>
            <label
              htmlFor="slaMinutes"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Escalation SLA (minutes)
            </label>
            <input
              id="slaMinutes"
              type="number"
              min={1}
              max={10080}
              value={slaMinutes}
              onChange={(e) => setSlaMinutes(Number(e.target.value))}
              className="w-full max-w-[200px] rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
            <p className="text-xs text-gray-400 mt-1">
              Maximum time (in minutes) before an escalation must be acknowledged.
              {slaMinutes >= 60 && (
                <span className="ml-1 text-gray-500">
                  ({Math.floor(slaMinutes / 60)}h {slaMinutes % 60 > 0 ? `${slaMinutes % 60}m` : ''})
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Escalation Rules */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Escalation Rules</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {rules.length}
            </span>
          </div>
          <button
            onClick={() => setShowAddRule(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Rule
          </button>
        </div>

        <div className="p-6">
          {rules.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10">
              <AlertTriangle className="w-8 h-8 text-gray-300 mb-2" />
              <p className="text-sm text-gray-500">No escalation rules configured.</p>
              <p className="text-xs text-gray-400 mt-1">
                Add rules to define when and how escalations should trigger.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-start justify-between gap-4 p-4 rounded-lg border border-gray-100 bg-gray-50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={cn(
                          'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                          priorityColors[rule.priority] || 'bg-gray-100 text-gray-800',
                        )}
                      >
                        {rule.priority}
                      </span>
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
                        {actionLabels[rule.action] || rule.action}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mt-1.5">{rule.condition}</p>
                    {rule.description && (
                      <p className="text-xs text-gray-500 mt-1">{rule.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => removeRule(rule.id)}
                    className="p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0"
                    title="Remove rule"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Rule Dialog */}
      {showAddRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-lg mx-4 w-full">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold text-gray-900">Add Escalation Rule</h3>
              <button
                onClick={resetRuleForm}
                className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Condition
                </label>
                <input
                  type="text"
                  value={newRuleCondition}
                  onChange={(e) => setNewRuleCondition(e.target.value)}
                  placeholder="e.g., task.errorCount > 3"
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Priority
                  </label>
                  <select
                    value={newRulePriority}
                    onChange={(e) => setNewRulePriority(e.target.value as EscalationRule['priority'])}
                    className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
                  >
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p.charAt(0).toUpperCase() + p.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Action
                  </label>
                  <select
                    value={newRuleAction}
                    onChange={(e) => setNewRuleAction(e.target.value as EscalationRule['action'])}
                    className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
                  >
                    {ACTIONS.map((a) => (
                      <option key={a} value={a}>
                        {actionLabels[a]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Description <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <textarea
                  value={newRuleDescription}
                  onChange={(e) => setNewRuleDescription(e.target.value)}
                  placeholder="Describe when and why this rule triggers..."
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 resize-y"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={resetRuleForm}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={addRule}
                disabled={!newRuleCondition.trim()}
                className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                Add Rule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Escalation Contacts */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Escalation Contacts</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {contacts.length}
            </span>
          </div>
          <button
            onClick={() => setShowAddContact(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-medium hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Contact
          </button>
        </div>

        <div className="p-6">
          {contacts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10">
              <Users className="w-8 h-8 text-gray-300 mb-2" />
              <p className="text-sm text-gray-500">No escalation contacts configured.</p>
              <p className="text-xs text-gray-400 mt-1">
                Add contacts who will be notified when escalations occur.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Name</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Email</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Role</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Primary</th>
                    <th className="text-right py-2.5 font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {contacts.map((contact) => (
                    <tr key={contact.id} className="border-b border-gray-50 last:border-0">
                      <td className="py-3 pr-4 font-medium text-gray-900">{contact.name}</td>
                      <td className="py-3 pr-4 text-gray-500">{contact.email}</td>
                      <td className="py-3 pr-4 text-gray-500">{contact.role || '--'}</td>
                      <td className="py-3 pr-4">
                        {contact.isPrimary ? (
                          <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Primary
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">--</span>
                        )}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => removeContact(contact.id)}
                          className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                          title="Remove contact"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Add Contact Dialog */}
      {showAddContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-lg mx-4 w-full">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold text-gray-900">Add Escalation Contact</h3>
              <button
                onClick={resetContactForm}
                className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={newContactName}
                  onChange={(e) => setNewContactName(e.target.value)}
                  placeholder="Jane Smith"
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  value={newContactEmail}
                  onChange={(e) => setNewContactEmail(e.target.value)}
                  placeholder="jane@example.com"
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Role <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  value={newContactRole}
                  onChange={(e) => setNewContactRole(e.target.value)}
                  placeholder="e.g., Team Lead, Manager"
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={newContactIsPrimary}
                  onChange={() => setNewContactIsPrimary(!newContactIsPrimary)}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">Set as primary contact</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={resetContactForm}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={addContact}
                disabled={!newContactName.trim() || !newContactEmail.trim()}
                className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                Add Contact
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
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
              Save Escalation Settings
            </>
          )}
        </button>

        {saveMutation.isSuccess && (
          <p className="text-sm text-green-600">Escalation settings saved successfully.</p>
        )}

        {saveMutation.isError && (
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <p className="text-sm text-red-600">Failed to save. Please try again.</p>
          </div>
        )}
      </div>
    </div>
  );
}
