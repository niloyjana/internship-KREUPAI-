import { Controller, Get, Param, Query } from '@nestjs/common';
import { AnalyticsService } from './analytics.service';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { AgentPerformanceQueryDto } from './dto/agent-performance.dto';
import { AgentTasksQueryDto } from './dto/agent-tasks.dto';
import { EscalationTrendsQueryDto } from './dto/escalation-trends.dto';
import { CostBreakdownQueryDto } from './dto/cost-breakdown.dto';
import { AuditLogQueryDto } from './dto/audit-log.dto';

@Controller({ path: 'analytics', version: '1' })
export class AnalyticsController {
  constructor(private readonly analyticsService: AnalyticsService) {}

  // GET /v1/analytics/dashboard
  @Get('dashboard')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async getDashboard(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
  ) {
    const data = await this.analyticsService.getDashboard(tenantId, userId);
    return { success: true, data };
  }

  // GET /v1/analytics/agents/:agentId/performance
  @Get('agents/:agentId/performance')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async getAgentPerformance(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('agentId') agentId: string,
    @Query() query: AgentPerformanceQueryDto,
  ) {
    const data = await this.analyticsService.getAgentPerformance(tenantId, agentId, query, userId);
    return { success: true, data };
  }

  // GET /v1/analytics/agents/:agentId/tasks
  @Get('agents/:agentId/tasks')
  async getAgentTasks(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
    @Query() query: AgentTasksQueryDto,
  ) {
    const result = await this.analyticsService.getAgentTasks(tenantId, agentId, query);
    return { success: true, data: result.items, meta: result.meta };
  }

  // GET /v1/analytics/escalations
  @Get('escalations')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async getEscalationTrends(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Query() query: EscalationTrendsQueryDto,
  ) {
    const data = await this.analyticsService.getEscalationTrends(tenantId, query, userId);
    return { success: true, data };
  }

  // GET /v1/analytics/cost
  @Get('cost')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async getCostBreakdown(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Query() query: CostBreakdownQueryDto,
  ) {
    const data = await this.analyticsService.getCostBreakdown(tenantId, query, userId);
    return { success: true, data };
  }

  // GET /v1/analytics/compliance
  @Get('compliance')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'AUDITOR')
  async getCompliance(@CurrentUser('tenantId') tenantId: string, @Query() query: AuditLogQueryDto) {
    const result = await this.analyticsService.getAuditLog(tenantId, query);
    return { success: true, data: result.items, meta: result.meta };
  }
}
