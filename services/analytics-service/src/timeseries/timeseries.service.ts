import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

export type TimeInterval = 'hourly' | 'daily' | 'weekly' | 'monthly';

export interface DateRange {
  from: string;
  to: string;
}

export interface TimeSeriesDataPoint {
  period: string;
  value: number;
  metadata?: Record<string, unknown>;
}

export interface AgentTrendData {
  period: string;
  tasksCompleted: number;
  tasksFailed: number;
  avgDurationMs: number;
  costUsd: number;
  stpRate: number;
}

export interface CostTrendData {
  period: string;
  totalCostUsd: number;
  totalActions: number;
  totalTokens: number;
}

@Injectable()
export class TimeSeriesService {
  private readonly logger = new Logger(TimeSeriesService.name);

  constructor(private readonly prisma: PrismaService) {}

  // ----------------------------------------------------------------
  // AGGREGATE METRICS
  // ----------------------------------------------------------------

  /**
   * Aggregate time-series data for a given metric over the specified interval.
   */
  async aggregateMetrics(
    tenantId: string,
    metric: string,
    interval: TimeInterval,
    dateRange: DateRange,
  ): Promise<TimeSeriesDataPoint[]> {
    const from = new Date(dateRange.from);
    const to = new Date(dateRange.to);

    this.logger.debug(
      `Aggregating metric="${metric}" interval=${interval} from=${dateRange.from} to=${dateRange.to}`,
    );

    switch (metric) {
      case 'task_count':
        return this.aggregateTaskCount(tenantId, interval, from, to);
      case 'cost':
        return this.aggregateCost(tenantId, interval, from, to);
      case 'token_usage':
        return this.aggregateTokenUsage(tenantId, interval, from, to);
      case 'escalation_count':
        return this.aggregateEscalationCount(tenantId, interval, from, to);
      default:
        this.logger.warn(`Unknown metric "${metric}" — returning empty series`);
        return [];
    }
  }

  // ----------------------------------------------------------------
  // AGENT TRENDS
  // ----------------------------------------------------------------

  /**
   * Get performance trends over time for a specific agent.
   */
  async getAgentTrends(
    tenantId: string,
    agentId: string,
    days: number,
  ): Promise<AgentTrendData[]> {
    const from = this.daysAgo(days);
    const to = new Date();

    const executions = await this.prisma.workflowExecution.findMany({
      where: {
        tenantId,
        agentId,
        createdAt: { gte: from, lte: to },
      },
      include: { escalations: { select: { id: true } } },
      orderBy: { createdAt: 'asc' },
    });

    // Group by day
    const dailyMap = new Map<
      string,
      {
        completed: number;
        failed: number;
        durations: number[];
        cost: number;
        total: number;
        escalated: number;
      }
    >();

    for (const exec of executions) {
      const key = this.periodKey(exec.createdAt, 'daily');
      const entry = dailyMap.get(key) ?? {
        completed: 0,
        failed: 0,
        durations: [],
        cost: 0,
        total: 0,
        escalated: 0,
      };

      entry.total += 1;
      if (exec.status === 'COMPLETED') entry.completed += 1;
      if (exec.status === 'FAILED') entry.failed += 1;
      if (exec.durationMs !== null) entry.durations.push(exec.durationMs);
      if (exec.llmCostUsd) entry.cost += Number(exec.llmCostUsd);
      if (exec.escalations.length > 0) entry.escalated += 1;

      dailyMap.set(key, entry);
    }

    const result: AgentTrendData[] = Array.from(dailyMap.entries()).map(
      ([period, data]) => ({
        period,
        tasksCompleted: data.completed,
        tasksFailed: data.failed,
        avgDurationMs:
          data.durations.length > 0
            ? Math.round(
                data.durations.reduce((s, d) => s + d, 0) / data.durations.length,
              )
            : 0,
        costUsd: Number(data.cost.toFixed(6)),
        stpRate:
          data.total > 0
            ? Number((((data.total - data.escalated) / data.total) * 100).toFixed(2))
            : 0,
      }),
    );

    this.logger.log(
      `Agent trends for ${agentId}: ${result.length} data points over ${days} days`,
    );

    return result;
  }

  // ----------------------------------------------------------------
  // COST TRENDS
  // ----------------------------------------------------------------

  /**
   * Get cost trends over time for the entire tenant.
   */
  async getCostTrends(
    tenantId: string,
    days: number,
  ): Promise<CostTrendData[]> {
    const from = this.daysAgo(days);
    const to = new Date();

    const actions = await this.prisma.agentAction.findMany({
      where: {
        tenantId,
        timestamp: { gte: from, lte: to },
      },
      select: {
        costUsd: true,
        tokenUsed: true,
        timestamp: true,
      },
      orderBy: { timestamp: 'asc' },
    });

    // Group by day
    const dailyMap = new Map<
      string,
      { cost: number; actions: number; tokens: number }
    >();

    for (const action of actions) {
      const key = this.periodKey(action.timestamp, 'daily');
      const entry = dailyMap.get(key) ?? { cost: 0, actions: 0, tokens: 0 };

      entry.cost += action.costUsd ? Number(action.costUsd) : 0;
      entry.actions += 1;
      entry.tokens += action.tokenUsed ?? 0;

      dailyMap.set(key, entry);
    }

    const result: CostTrendData[] = Array.from(dailyMap.entries()).map(
      ([period, data]) => ({
        period,
        totalCostUsd: Number(data.cost.toFixed(6)),
        totalActions: data.actions,
        totalTokens: data.tokens,
      }),
    );

    this.logger.log(
      `Cost trends for tenant ${tenantId}: ${result.length} data points over ${days} days`,
    );

    return result;
  }

  // ----------------------------------------------------------------
  // PRIVATE — METRIC AGGREGATORS
  // ----------------------------------------------------------------

  private async aggregateTaskCount(
    tenantId: string,
    interval: TimeInterval,
    from: Date,
    to: Date,
  ): Promise<TimeSeriesDataPoint[]> {
    const executions = await this.prisma.workflowExecution.findMany({
      where: { tenantId, createdAt: { gte: from, lte: to } },
      select: { createdAt: true, status: true },
      orderBy: { createdAt: 'asc' },
    });

    const map = new Map<string, number>();
    for (const exec of executions) {
      const key = this.periodKey(exec.createdAt, interval);
      map.set(key, (map.get(key) ?? 0) + 1);
    }

    return Array.from(map.entries()).map(([period, value]) => ({
      period,
      value,
    }));
  }

  private async aggregateCost(
    tenantId: string,
    interval: TimeInterval,
    from: Date,
    to: Date,
  ): Promise<TimeSeriesDataPoint[]> {
    const actions = await this.prisma.agentAction.findMany({
      where: { tenantId, timestamp: { gte: from, lte: to } },
      select: { timestamp: true, costUsd: true },
      orderBy: { timestamp: 'asc' },
    });

    const map = new Map<string, number>();
    for (const action of actions) {
      const key = this.periodKey(action.timestamp, interval);
      const current = map.get(key) ?? 0;
      map.set(key, current + (action.costUsd ? Number(action.costUsd) : 0));
    }

    return Array.from(map.entries()).map(([period, value]) => ({
      period,
      value: Number(value.toFixed(6)),
    }));
  }

  private async aggregateTokenUsage(
    tenantId: string,
    interval: TimeInterval,
    from: Date,
    to: Date,
  ): Promise<TimeSeriesDataPoint[]> {
    const actions = await this.prisma.agentAction.findMany({
      where: { tenantId, timestamp: { gte: from, lte: to } },
      select: { timestamp: true, tokenUsed: true },
      orderBy: { timestamp: 'asc' },
    });

    const map = new Map<string, number>();
    for (const action of actions) {
      const key = this.periodKey(action.timestamp, interval);
      const current = map.get(key) ?? 0;
      map.set(key, current + (action.tokenUsed ?? 0));
    }

    return Array.from(map.entries()).map(([period, value]) => ({
      period,
      value,
    }));
  }

  private async aggregateEscalationCount(
    tenantId: string,
    interval: TimeInterval,
    from: Date,
    to: Date,
  ): Promise<TimeSeriesDataPoint[]> {
    const escalations = await this.prisma.escalationTicket.findMany({
      where: { tenantId, createdAt: { gte: from, lte: to } },
      select: { createdAt: true },
      orderBy: { createdAt: 'asc' },
    });

    const map = new Map<string, number>();
    for (const esc of escalations) {
      const key = this.periodKey(esc.createdAt, interval);
      map.set(key, (map.get(key) ?? 0) + 1);
    }

    return Array.from(map.entries()).map(([period, value]) => ({
      period,
      value,
    }));
  }

  // ----------------------------------------------------------------
  // PRIVATE HELPERS
  // ----------------------------------------------------------------

  private daysAgo(days: number): Date {
    const d = new Date();
    d.setDate(d.getDate() - days);
    d.setHours(0, 0, 0, 0);
    return d;
  }

  private periodKey(date: Date, interval: TimeInterval): string {
    const d = new Date(date);
    switch (interval) {
      case 'hourly':
        return d.toISOString().slice(0, 13) + ':00';
      case 'daily':
        return d.toISOString().slice(0, 10);
      case 'weekly': {
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        const weekStart = new Date(d);
        weekStart.setDate(diff);
        return weekStart.toISOString().slice(0, 10);
      }
      case 'monthly':
        return d.toISOString().slice(0, 7);
      default:
        return d.toISOString().slice(0, 10);
    }
  }
}
