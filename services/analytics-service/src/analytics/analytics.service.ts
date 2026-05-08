import { Injectable, Logger } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { KafkaProducerService, AuditService, TOPICS, BillingUsageRecordedPayload } from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { AgentPerformanceQueryDto } from './dto/agent-performance.dto';
import { AgentTasksQueryDto } from './dto/agent-tasks.dto';
import { EscalationTrendsQueryDto } from './dto/escalation-trends.dto';
import { CostBreakdownQueryDto } from './dto/cost-breakdown.dto';
import { AuditLogQueryDto } from './dto/audit-log.dto';

@Injectable()
export class AnalyticsService {
  private readonly logger = new Logger(AnalyticsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ----------------------------------------------------------------
  // DASHBOARD
  // ----------------------------------------------------------------

  async getDashboard(tenantId: string, userId?: string) {
    this.logger.debug(`Fetching dashboard for tenant ${tenantId}`);
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);

    // Parallel aggregation queries
    const [
      todayExecutions,
      completedToday,
      failedToday,
      openEscalations,
      pendingHumanTasks,
      todayActions,
      activeAgents,
    ] = await Promise.all([
      // Total tasks today
      this.prisma.workflowExecution.count({
        where: { tenantId, createdAt: { gte: todayStart } },
      }),
      // Completed today
      this.prisma.workflowExecution.count({
        where: { tenantId, status: 'COMPLETED', completedAt: { gte: todayStart } },
      }),
      // Failed today
      this.prisma.workflowExecution.count({
        where: { tenantId, status: 'FAILED', failedAt: { gte: todayStart } },
      }),
      // Pending escalations
      this.prisma.escalationTicket.count({
        where: { tenantId, status: 'OPEN' },
      }),
      // Pending human tasks
      this.prisma.humanTask.count({
        where: { tenantId, status: 'PENDING' },
      }),
      // Today's agent actions (for cost aggregation)
      this.prisma.agentAction.findMany({
        where: { tenantId, timestamp: { gte: todayStart } },
        select: { agentId: true, costUsd: true, durationMs: true },
      }),
      // Active agents (distinct agentIds with executions today)
      this.prisma.workflowExecution.findMany({
        where: { tenantId, createdAt: { gte: todayStart } },
        select: { agentId: true },
        distinct: ['agentId'],
      }),
    ]);

    // Calculate total LLM cost today
    const totalLlmCostUsdToday = todayActions.reduce(
      (sum, a) => sum + (a.costUsd ? Number(a.costUsd) : 0),
      0,
    );

    // Calculate avg task duration from completed executions today
    const completedExecs = await this.prisma.workflowExecution.findMany({
      where: { tenantId, status: 'COMPLETED', completedAt: { gte: todayStart } },
      select: { durationMs: true },
    });

    const durations = completedExecs
      .map((e) => e.durationMs)
      .filter((d): d is number => d !== null);
    const avgTaskDurationMs =
      durations.length > 0
        ? Math.round(durations.reduce((s, d) => s + d, 0) / durations.length)
        : 0;

    // Agent breakdown
    const agentMap = new Map<string, { tasks: number; cost: number }>();
    for (const action of todayActions) {
      const existing = agentMap.get(action.agentId) ?? { tasks: 0, cost: 0 };
      existing.tasks += 1;
      existing.cost += action.costUsd ? Number(action.costUsd) : 0;
      agentMap.set(action.agentId, existing);
    }

    const agentBreakdown = Array.from(agentMap.entries()).map(([agentId, data]) => ({
      agentId,
      tasks: data.tasks,
      costUsd: Number(data.cost.toFixed(6)),
    }));

    const result = {
      activeAgents: activeAgents.length,
      totalTasksToday: todayExecutions,
      tasksCompleted: completedToday,
      tasksFailed: failedToday,
      pendingEscalations: openEscalations,
      pendingHumanTasks: pendingHumanTasks,
      avgTaskDurationMs,
      totalLlmCostUsdToday: Number(totalLlmCostUsdToday.toFixed(6)),
      agentBreakdown,
    };

    this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId ?? 'system',
      action: 'REPORT_GENERATED',
      entityType: 'ANALYTICS_REPORT',
      entityId: tenantId,
      metadata: { reportType: 'dashboard' },
    }).catch((err) =>
      this.logger.error(
        `Failed to publish audit REPORT_GENERATED (dashboard): ${err instanceof Error ? err.message : err}`,
      ),
    );

    return result;
  }

  // ----------------------------------------------------------------
  // AGENT PERFORMANCE
  // ----------------------------------------------------------------

  async getAgentPerformance(
    tenantId: string,
    agentId: string,
    query: AgentPerformanceQueryDto,
    userId?: string,
  ) {
    const from = query.from ? new Date(query.from) : this.daysAgo(30);
    const to = query.to ? new Date(query.to) : new Date();

    const executions = await this.prisma.workflowExecution.findMany({
      where: {
        tenantId,
        agentId,
        createdAt: { gte: from, lte: to },
      },
      include: {
        escalations: { select: { id: true } },
      },
      orderBy: { createdAt: 'asc' },
    });

    const taskCount = executions.length;
    const completedCount = executions.filter((e) => e.status === 'COMPLETED').length;
    const withEscalation = executions.filter((e) => e.escalations.length > 0).length;
    const stp = taskCount > 0 ? taskCount - withEscalation : 0;
    const stpRate = taskCount > 0 ? Number(((stp / taskCount) * 100).toFixed(2)) : 0;
    const escalationRate = taskCount > 0 ? Number(((withEscalation / taskCount) * 100).toFixed(2)) : 0;

    const durations = executions
      .map((e) => e.durationMs)
      .filter((d): d is number => d !== null);
    const avgDurationMs =
      durations.length > 0
        ? Math.round(durations.reduce((s, d) => s + d, 0) / durations.length)
        : 0;

    const totalCostUsd = executions.reduce(
      (sum, e) => sum + (e.llmCostUsd ? Number(e.llmCostUsd) : 0),
      0,
    );

    // Daily breakdown
    const dailyMap = new Map<string, { tasks: number; completed: number; cost: number }>();
    for (const exec of executions) {
      const key = this.periodKey(exec.createdAt, query.granularity ?? 'daily');
      const entry = dailyMap.get(key) ?? { tasks: 0, completed: 0, cost: 0 };
      entry.tasks += 1;
      if (exec.status === 'COMPLETED') entry.completed += 1;
      entry.cost += exec.llmCostUsd ? Number(exec.llmCostUsd) : 0;
      dailyMap.set(key, entry);
    }

    const dailyBreakdown = Array.from(dailyMap.entries()).map(([period, data]) => ({
      period,
      tasks: data.tasks,
      completed: data.completed,
      costUsd: Number(data.cost.toFixed(6)),
    }));

    const result = {
      taskCount,
      completedCount,
      stpRate,
      escalationRate,
      avgDurationMs,
      totalCostUsd: Number(totalCostUsd.toFixed(6)),
      dailyBreakdown,
    };

    this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId ?? 'system',
      action: 'REPORT_GENERATED',
      entityType: 'ANALYTICS_REPORT',
      entityId: agentId,
      metadata: { reportType: 'agent_performance', agentId },
    }).catch((err) =>
      this.logger.error(
        `Failed to publish audit REPORT_GENERATED (agent_performance): ${err instanceof Error ? err.message : err}`,
      ),
    );

    return result;
  }

  // ----------------------------------------------------------------
  // AGENT TASKS
  // ----------------------------------------------------------------

  async getAgentTasks(
    tenantId: string,
    agentId: string,
    query: AgentTasksQueryDto,
  ) {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.WorkflowExecutionWhereInput = {
      tenantId,
      agentId,
    };

    if (query.status) {
      where.status = query.status as Prisma.EnumWorkflowStatusFilter;
    }

    if (query.from) {
      where.createdAt = { gte: new Date(query.from) };
    }

    const [items, total] = await Promise.all([
      this.prisma.workflowExecution.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
        select: {
          id: true,
          agentId: true,
          definitionId: true,
          status: true,
          triggerSource: true,
          startedAt: true,
          completedAt: true,
          failedAt: true,
          failureReason: true,
          durationMs: true,
          tokenUsed: true,
          llmCostUsd: true,
          createdAt: true,
        },
      }),
      this.prisma.workflowExecution.count({ where }),
    ]);

    return {
      items,
      meta: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  // ----------------------------------------------------------------
  // ESCALATION TRENDS
  // ----------------------------------------------------------------

  async getEscalationTrends(tenantId: string, query: EscalationTrendsQueryDto, userId?: string) {
    const from = query.from ? new Date(query.from) : this.daysAgo(30);
    const to = query.to ? new Date(query.to) : new Date();

    const where: Prisma.EscalationTicketWhereInput = {
      tenantId,
      createdAt: { gte: from, lte: to },
    };

    if (query.agentId) {
      where.agentId = query.agentId;
    }

    const escalations = await this.prisma.escalationTicket.findMany({
      where,
      orderBy: { createdAt: 'asc' },
    });

    const totalEscalations = escalations.length;

    // Average resolution time
    const resolved = escalations.filter((e) => e.resolvedAt !== null);
    const resolutionTimes = resolved.map((e) =>
      e.resolvedAt!.getTime() - e.createdAt.getTime(),
    );
    const avgResolutionTimeMs =
      resolutionTimes.length > 0
        ? Math.round(
            resolutionTimes.reduce((s, t) => s + t, 0) / resolutionTimes.length,
          )
        : 0;

    // By severity
    const bySeverity: Record<string, number> = {};
    for (const esc of escalations) {
      bySeverity[esc.severity] = (bySeverity[esc.severity] ?? 0) + 1;
    }

    // By agent
    const agentMap = new Map<string, number>();
    for (const esc of escalations) {
      agentMap.set(esc.agentId, (agentMap.get(esc.agentId) ?? 0) + 1);
    }
    const byAgent = Array.from(agentMap.entries()).map(([agentId, count]) => ({
      agentId,
      count,
    }));

    const result = {
      totalEscalations,
      avgResolutionTimeMs,
      bySeverity,
      byAgent,
    };

    this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId ?? 'system',
      action: 'REPORT_GENERATED',
      entityType: 'ANALYTICS_REPORT',
      entityId: tenantId,
      metadata: { reportType: 'escalation_trends' },
    }).catch((err) =>
      this.logger.error(
        `Failed to publish audit REPORT_GENERATED (escalation_trends): ${err instanceof Error ? err.message : err}`,
      ),
    );

    return result;
  }

  // ----------------------------------------------------------------
  // COST BREAKDOWN
  // ----------------------------------------------------------------

  async getCostBreakdown(tenantId: string, query: CostBreakdownQueryDto, userId?: string) {
    const from = query.from ? new Date(query.from) : this.daysAgo(30);
    const to = query.to ? new Date(query.to) : new Date();
    const groupBy = query.groupBy ?? 'agent';

    const actions = await this.prisma.agentAction.findMany({
      where: {
        tenantId,
        timestamp: { gte: from, lte: to },
      },
      select: {
        agentId: true,
        costUsd: true,
        actionType: true,
        timestamp: true,
      },
    });

    const totalCostUsd = actions.reduce(
      (sum, a) => sum + (a.costUsd ? Number(a.costUsd) : 0),
      0,
    );

    // Group by agent or model (actionType as proxy for model)
    const breakdownMap = new Map<string, number>();
    for (const action of actions) {
      const key = groupBy === 'agent' ? action.agentId : (action.actionType ?? 'unknown');
      const current = breakdownMap.get(key) ?? 0;
      breakdownMap.set(key, current + (action.costUsd ? Number(action.costUsd) : 0));
    }

    const breakdown = Array.from(breakdownMap.entries()).map(([key, cost]) => ({
      [groupBy]: key,
      costUsd: Number(cost.toFixed(6)),
    }));

    const result = {
      totalCostUsd: Number(totalCostUsd.toFixed(6)),
      breakdown,
    };

    this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId ?? 'system',
      action: 'REPORT_GENERATED',
      entityType: 'ANALYTICS_REPORT',
      entityId: tenantId,
      metadata: { reportType: 'cost_breakdown', groupBy },
    }).catch((err) =>
      this.logger.error(
        `Failed to publish audit REPORT_GENERATED (cost_breakdown): ${err instanceof Error ? err.message : err}`,
      ),
    );

    return result;
  }

  // ----------------------------------------------------------------
  // AUDIT LOG
  // ----------------------------------------------------------------

  async getAuditLog(tenantId: string, query: AuditLogQueryDto) {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 50;
    const skip = (page - 1) * pageSize;

    const where: Prisma.AuditLogWhereInput = { tenantId };

    if (query.actorType) {
      where.actorType = query.actorType as Prisma.EnumAuditActorTypeFilter;
    }

    if (query.entityType) {
      where.entityType = query.entityType;
    }

    if (query.from || query.to) {
      where.timestamp = {};
      if (query.from) {
        where.timestamp.gte = new Date(query.from);
      }
      if (query.to) {
        where.timestamp.lte = new Date(query.to);
      }
    }

    const [items, total] = await Promise.all([
      this.prisma.auditLog.findMany({
        where,
        orderBy: { timestamp: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.auditLog.count({ where }),
    ]);

    return {
      items,
      meta: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  // ----------------------------------------------------------------
  // KAFKA PRODUCERS
  // ----------------------------------------------------------------

  async emitBillingUsage(
    tenantId: string,
    payload: BillingUsageRecordedPayload,
  ): Promise<void> {
    await this.kafkaProducer.emit<BillingUsageRecordedPayload>(
      TOPICS.BILLING_USAGE_RECORDED,
      {
        tenantId,
        source: 'analytics-service',
        payload,
      },
    );
    this.logger.log(
      `Emitted ${TOPICS.BILLING_USAGE_RECORDED} for tenant ${tenantId}`,
    );
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

  private periodKey(
    date: Date,
    granularity: 'daily' | 'weekly' | 'monthly',
  ): string {
    const d = new Date(date);
    switch (granularity) {
      case 'daily':
        return d.toISOString().slice(0, 10);
      case 'weekly': {
        // ISO week start (Monday)
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
