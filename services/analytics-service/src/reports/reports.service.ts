import {
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

export type ReportType = 'performance' | 'cost' | 'compliance' | 'usage';
export type ReportFormat = 'json' | 'csv' | 'pdf';
export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface GenerateReportParams {
  type: ReportType;
  format: ReportFormat;
  dateRange: { from: string; to: string };
  filters?: Record<string, unknown>;
}

export interface ReportRecord {
  id: string;
  tenantId: string;
  type: ReportType;
  format: ReportFormat;
  status: ReportStatus;
  dateRange: { from: string; to: string };
  filters: Record<string, unknown>;
  resultData?: Record<string, unknown>;
  fileUrl?: string;
  createdAt: Date;
  completedAt?: Date;
}

@Injectable()
export class ReportsService {
  private readonly logger = new Logger(ReportsService.name);

  constructor(private readonly prisma: PrismaService) {}

  // ----------------------------------------------------------------
  // GENERATE REPORT
  // ----------------------------------------------------------------

  async generateReport(
    tenantId: string,
    userId: string,
    params: GenerateReportParams,
  ): Promise<ReportRecord> {
    // Create the report record with 'pending' status
    const report = await this.prisma.analyticsReport.create({
      data: {
        tenantId,
        createdBy: userId,
        type: params.type,
        format: params.format,
        status: 'generating',
        dateRange: params.dateRange as unknown as Prisma.InputJsonValue,
        filters: (params.filters ?? {}) as Prisma.InputJsonValue,
      },
    });

    this.logger.log(
      `Report generation started — id=${report.id} type=${params.type} format=${params.format}`,
    );

    // Generate report data asynchronously (in-process for simplicity)
    try {
      const resultData = await this.buildReportData(
        tenantId,
        params.type,
        params.dateRange,
        params.filters,
      );

      const completed = await this.prisma.analyticsReport.update({
        where: { id: report.id },
        data: {
          status: 'completed',
          resultData: resultData as Prisma.InputJsonValue,
          completedAt: new Date(),
        },
      });

      this.logger.log(`Report completed — id=${report.id}`);
      return completed as unknown as ReportRecord;
    } catch (error) {
      await this.prisma.analyticsReport.update({
        where: { id: report.id },
        data: {
          status: 'failed',
          resultData: {
            error: error instanceof Error ? error.message : String(error),
          } as Prisma.InputJsonValue,
        },
      });

      this.logger.error(
        `Report generation failed — id=${report.id}: ${error instanceof Error ? error.message : error}`,
      );

      return {
        ...report,
        status: 'failed' as ReportStatus,
      } as unknown as ReportRecord;
    }
  }

  // ----------------------------------------------------------------
  // LIST REPORTS
  // ----------------------------------------------------------------

  async listReports(
    tenantId: string,
    params: { page?: number; pageSize?: number; type?: ReportType } = {},
  ) {
    const page = params.page ?? 1;
    const pageSize = params.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.AnalyticsReportWhereInput = { tenantId };

    if (params.type) {
      where.type = params.type;
    }

    const [items, total] = await Promise.all([
      this.prisma.analyticsReport.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.analyticsReport.count({ where }),
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
  // GET REPORT BY ID
  // ----------------------------------------------------------------

  async getReportById(tenantId: string, reportId: string) {
    const report = await this.prisma.analyticsReport.findFirst({
      where: { id: reportId, tenantId },
    });

    if (!report) {
      throw new NotFoundException('REPORT_NOT_FOUND');
    }

    return report;
  }

  // ----------------------------------------------------------------
  // DOWNLOAD REPORT
  // ----------------------------------------------------------------

  async downloadReport(tenantId: string, reportId: string) {
    const report = await this.prisma.analyticsReport.findFirst({
      where: { id: reportId, tenantId },
    });

    if (!report) {
      throw new NotFoundException('REPORT_NOT_FOUND');
    }

    if (report.status !== 'completed') {
      throw new NotFoundException(
        `Report is not ready for download (status: ${report.status})`,
      );
    }

    // In a production system, this would return a pre-signed URL
    // or stream the file. For now, return the data inline.
    return {
      id: report.id,
      type: report.type,
      format: report.format,
      data: report.resultData,
      fileUrl: report.fileUrl ?? null,
    };
  }

  // ----------------------------------------------------------------
  // PRIVATE — REPORT DATA BUILDERS
  // ----------------------------------------------------------------

  private async buildReportData(
    tenantId: string,
    type: ReportType,
    dateRange: { from: string; to: string },
    filters?: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const from = new Date(dateRange.from);
    const to = new Date(dateRange.to);

    switch (type) {
      case 'performance':
        return this.buildPerformanceReport(tenantId, from, to, filters);
      case 'cost':
        return this.buildCostReport(tenantId, from, to, filters);
      case 'compliance':
        return this.buildComplianceReport(tenantId, from, to);
      case 'usage':
        return this.buildUsageReport(tenantId, from, to);
      default:
        throw new Error(`Unknown report type: ${type}`);
    }
  }

  private async buildPerformanceReport(
    tenantId: string,
    from: Date,
    to: Date,
    filters?: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const where: Prisma.WorkflowExecutionWhereInput = {
      tenantId,
      createdAt: { gte: from, lte: to },
    };

    if (filters?.agentId) {
      where.agentId = filters.agentId as string;
    }

    const executions = await this.prisma.workflowExecution.findMany({
      where,
      include: { escalations: { select: { id: true } } },
    });

    const total = executions.length;
    const completed = executions.filter((e) => e.status === 'COMPLETED').length;
    const failed = executions.filter((e) => e.status === 'FAILED').length;
    const withEscalation = executions.filter((e) => e.escalations.length > 0).length;
    const stpRate = total > 0 ? Number((((total - withEscalation) / total) * 100).toFixed(2)) : 0;

    const durations = executions
      .map((e) => e.durationMs)
      .filter((d): d is number => d !== null);
    const avgDurationMs =
      durations.length > 0
        ? Math.round(durations.reduce((s, d) => s + d, 0) / durations.length)
        : 0;

    return {
      reportType: 'performance',
      period: { from: from.toISOString(), to: to.toISOString() },
      totalExecutions: total,
      completed,
      failed,
      escalated: withEscalation,
      stpRate,
      avgDurationMs,
    };
  }

  private async buildCostReport(
    tenantId: string,
    from: Date,
    to: Date,
    filters?: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const where: Prisma.AgentActionWhereInput = {
      tenantId,
      timestamp: { gte: from, lte: to },
    };

    if (filters?.agentId) {
      where.agentId = filters.agentId as string;
    }

    const actions = await this.prisma.agentAction.findMany({
      where,
      select: { agentId: true, costUsd: true, actionType: true, timestamp: true },
    });

    const totalCostUsd = actions.reduce(
      (sum, a) => sum + (a.costUsd ? Number(a.costUsd) : 0),
      0,
    );

    const byAgent = new Map<string, number>();
    for (const action of actions) {
      const current = byAgent.get(action.agentId) ?? 0;
      byAgent.set(action.agentId, current + (action.costUsd ? Number(action.costUsd) : 0));
    }

    return {
      reportType: 'cost',
      period: { from: from.toISOString(), to: to.toISOString() },
      totalCostUsd: Number(totalCostUsd.toFixed(6)),
      byAgent: Array.from(byAgent.entries()).map(([agentId, cost]) => ({
        agentId,
        costUsd: Number(cost.toFixed(6)),
      })),
    };
  }

  private async buildComplianceReport(
    tenantId: string,
    from: Date,
    to: Date,
  ): Promise<Record<string, unknown>> {
    const [auditLogs, escalations] = await Promise.all([
      this.prisma.auditLog.count({
        where: { tenantId, timestamp: { gte: from, lte: to } },
      }),
      this.prisma.escalationTicket.findMany({
        where: { tenantId, createdAt: { gte: from, lte: to } },
        select: { severity: true, status: true },
      }),
    ]);

    const bySeverity: Record<string, number> = {};
    for (const esc of escalations) {
      bySeverity[esc.severity] = (bySeverity[esc.severity] ?? 0) + 1;
    }

    return {
      reportType: 'compliance',
      period: { from: from.toISOString(), to: to.toISOString() },
      totalAuditEntries: auditLogs,
      totalEscalations: escalations.length,
      escalationsBySeverity: bySeverity,
    };
  }

  private async buildUsageReport(
    tenantId: string,
    from: Date,
    to: Date,
  ): Promise<Record<string, unknown>> {
    const [executions, actions] = await Promise.all([
      this.prisma.workflowExecution.count({
        where: { tenantId, createdAt: { gte: from, lte: to } },
      }),
      this.prisma.agentAction.aggregate({
        where: { tenantId, timestamp: { gte: from, lte: to } },
        _sum: { tokenUsed: true },
        _count: true,
      }),
    ]);

    return {
      reportType: 'usage',
      period: { from: from.toISOString(), to: to.toISOString() },
      totalWorkflowExecutions: executions,
      totalAgentActions: actions._count,
      totalTokensUsed: actions._sum.tokenUsed ?? 0,
    };
  }
}
