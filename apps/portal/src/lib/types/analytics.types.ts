/**
 * Types for analytics dashboard and reporting.
 */

export interface DashboardData {
  activeAgents: number;
  totalTasksToday: number;
  tasksCompleted: number;
  tasksFailed: number;
  pendingEscalations: number;
  pendingHumanTasks: number;
  avgTaskDurationMs: number;
  totalLlmCostUsdToday: number;
  topAgentByTasks: string | null;
  agentBreakdown: AgentBreakdownItem[];
}

export interface AgentBreakdownItem {
  agentId: string;
  name?: string;
  tasksCompleted: number;
  escalationRate: number;
  avgDurationMs: number;
  costUsd: number;
  status: string;
}

export interface AgentPerformance {
  taskCount: number;
  stpRate: number;
  escalationRate: number;
  avgDurationMs: number;
  totalCostUsd: number;
  dailyBreakdown: DailyBreakdown[];
}

export interface DailyBreakdown {
  date: string;
  tasksCompleted: number;
  tasksEscalated: number;
  tasksFailed: number;
  costUsd: number;
}

export interface CostBreakdown {
  totalCostUsd: number;
  breakdown: CostBreakdownItem[];
}

export interface CostBreakdownItem {
  key: string;
  label: string;
  costUsd: number;
  taskCount: number;
  tokenCount: number;
}

export interface AuditLogEntry {
  id: string;
  actorType: 'USER' | 'AI_AGENT' | 'SYSTEM';
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  timestamp: string;
  metadata: any;
}
