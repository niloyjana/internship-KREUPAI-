import {
  Zap,
  Database,
  Brain,
  Cog,
  ShieldCheck,
  ClipboardCheck,
  HelpCircle,
  BookOpen,
  FileText,
  Shield,
  Layers,
} from 'lucide-react';
import type { AgentDepartment } from '@/lib/types/agent.types';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type TabId = 'blueprint' | 'tools' | 'integrations' | 'rules' | 'activity' | 'settings';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

export const departmentColors: Record<AgentDepartment, { bg: string; text: string; icon: string }> =
  {
    finance: {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      icon: 'bg-emerald-100 text-emerald-600',
    },
    hr: { bg: 'bg-violet-50', text: 'text-violet-700', icon: 'bg-violet-100 text-violet-600' },
    sales: { bg: 'bg-blue-50', text: 'text-blue-700', icon: 'bg-blue-100 text-blue-600' },
    marketing: { bg: 'bg-pink-50', text: 'text-pink-700', icon: 'bg-pink-100 text-pink-600' },
    operations: { bg: 'bg-amber-50', text: 'text-amber-700', icon: 'bg-amber-100 text-amber-600' },
    engineering: { bg: 'bg-cyan-50', text: 'text-cyan-700', icon: 'bg-cyan-100 text-cyan-600' },
    legal: { bg: 'bg-slate-100', text: 'text-slate-700', icon: 'bg-slate-200 text-slate-600' },
    support: { bg: 'bg-orange-50', text: 'text-orange-700', icon: 'bg-orange-100 text-orange-600' },
  };

export const departmentLabels: Record<string, string> = {
  finance: 'Finance',
  hr: 'Human Resources',
  sales: 'Sales',
  marketing: 'Marketing',
  operations: 'Operations',
  engineering: 'Engineering',
  legal: 'Legal',
  support: 'Support',
};

export const statusColors: Record<string, { dot: string; bg: string; text: string }> = {
  COMPLETED: { dot: 'bg-green-500', bg: 'bg-green-50', text: 'text-green-700' },
  RUNNING: { dot: 'bg-blue-500', bg: 'bg-blue-50', text: 'text-blue-700' },
  PENDING: { dot: 'bg-gray-400', bg: 'bg-gray-50', text: 'text-gray-600' },
  FAILED: { dot: 'bg-red-500', bg: 'bg-red-50', text: 'text-red-700' },
  PAUSED: { dot: 'bg-amber-500', bg: 'bg-amber-50', text: 'text-amber-700' },
  CANCELLED: { dot: 'bg-gray-400', bg: 'bg-gray-50', text: 'text-gray-500' },
};

export const toolCategoryColors: Record<string, { bg: string; text: string }> = {
  compute: { bg: 'bg-purple-100', text: 'text-purple-700' },
  integration: { bg: 'bg-blue-100', text: 'text-blue-700' },
  search: { bg: 'bg-green-100', text: 'text-green-700' },
  data: { bg: 'bg-cyan-100', text: 'text-cyan-700' },
  communication: { bg: 'bg-pink-100', text: 'text-pink-700' },
  document: { bg: 'bg-amber-100', text: 'text-amber-700' },
  workflow: { bg: 'bg-gray-100', text: 'text-gray-600' },
};

export const knowledgeTypeIcons: Record<string, React.ElementType> = {
  faq: HelpCircle,
  documentation: BookOpen,
  past_resolutions: FileText,
  policy_docs: Shield,
  templates: Layers,
};

export const priorityColors: Record<string, { bg: string; text: string }> = {
  low: { bg: 'bg-gray-100', text: 'text-gray-600' },
  medium: { bg: 'bg-amber-100', text: 'text-amber-700' },
  high: { bg: 'bg-orange-100', text: 'text-orange-700' },
  critical: { bg: 'bg-red-100', text: 'text-red-700' },
};

/* ------------------------------------------------------------------ */
/*  Pipeline stage definitions for Blueprint tab                       */
/* ------------------------------------------------------------------ */

export const PIPELINE_STAGES = [
  {
    key: 'trigger',
    label: 'TRIGGER',
    desc: 'Webhook / Schedule / API / Email',
    icon: Zap,
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
  },
  {
    key: 'context',
    label: 'CONTEXT LOAD',
    desc: 'Tenant config + customer data',
    icon: Database,
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    iconBg: 'bg-indigo-100',
    iconColor: 'text-indigo-600',
  },
  {
    key: 'llm',
    label: 'LLM PLANNING',
    desc: 'Decompose task into steps',
    icon: Brain,
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    iconBg: 'bg-purple-100',
    iconColor: 'text-purple-600',
  },
  {
    key: 'execute',
    label: 'EXECUTE STEPS',
    desc: 'Call tools sequentially',
    icon: Cog,
    bg: 'bg-primary-50',
    border: 'border-primary-200',
    iconBg: 'bg-primary-100',
    iconColor: 'text-primary-600',
  },
  {
    key: 'guardrail',
    label: 'GUARDRAIL CHECK',
    desc: 'Policy validation + confidence',
    icon: ShieldCheck,
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600',
  },
  {
    key: 'output',
    label: 'OUTPUT & LOG',
    desc: 'Audit trail + metrics',
    icon: ClipboardCheck,
    bg: 'bg-green-50',
    border: 'border-green-200',
    iconBg: 'bg-green-100',
    iconColor: 'text-green-600',
  },
];

/* ------------------------------------------------------------------ */
/*  Helper functions                                                   */
/* ------------------------------------------------------------------ */

export function formatDuration(ms: number | null): string {
  if (!ms) return '\u2014';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = Math.round((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

export function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '\u2014';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ago`;
}

/* ------------------------------------------------------------------ */
/*  Demo data for when no real data exists yet                         */
/* ------------------------------------------------------------------ */

export interface DemoDataPoint {
  [key: string]: unknown;
  date: string;
  tasksCompleted: number;
  tasksFailed: number;
  tasksEscalated: number;
  costUsd: number;
}

export function generateDemoPerformanceData(): DemoDataPoint[] {
  const data: DemoDataPoint[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const weekday = d.getDay();
    const base = 8 + Math.floor(Math.random() * 12);
    const tasks = weekday === 0 || weekday === 6 ? Math.floor(base * 0.3) : base;
    const failed = Math.floor(Math.random() * 2);
    const escalated = Math.floor(Math.random() * 2);
    const cost = +(tasks * 0.02 + Math.random() * 0.05).toFixed(3);
    data.push({
      date: dateStr,
      tasksCompleted: tasks,
      tasksFailed: failed,
      tasksEscalated: escalated,
      costUsd: cost,
    });
  }
  return data;
}

export const DEMO_EXECUTIONS = [
  {
    id: 'd1',
    status: 'COMPLETED' as const,
    triggerSource: 'CRM Webhook',
    startedAt: '25m ago',
    durationMs: '3.2s',
    steps: '5/5',
  },
  {
    id: 'd2',
    status: 'COMPLETED' as const,
    triggerSource: 'Scheduled',
    startedAt: '1h ago',
    durationMs: '1.8s',
    steps: '3/3',
  },
  {
    id: 'd3',
    status: 'RUNNING' as const,
    triggerSource: 'API Call',
    startedAt: '2m ago',
    durationMs: '\u2014',
    steps: '2/4',
  },
  {
    id: 'd4',
    status: 'FAILED' as const,
    triggerSource: 'Email Trigger',
    startedAt: '3h ago',
    durationMs: '0.4s',
    steps: '1/5',
  },
  {
    id: 'd5',
    status: 'COMPLETED' as const,
    triggerSource: 'Manual',
    startedAt: '5h ago',
    durationMs: '2.1s',
    steps: '4/4',
  },
  {
    id: 'd6',
    status: 'COMPLETED' as const,
    triggerSource: 'CRM Webhook',
    startedAt: '8h ago',
    durationMs: '4.5s',
    steps: '6/6',
  },
  {
    id: 'd7',
    status: 'PAUSED' as const,
    triggerSource: 'Escalation',
    startedAt: '12h ago',
    durationMs: '\u2014',
    steps: '3/5',
  },
  {
    id: 'd8',
    status: 'COMPLETED' as const,
    triggerSource: 'Scheduled',
    startedAt: '1d ago',
    durationMs: '2.8s',
    steps: '4/4',
  },
];
