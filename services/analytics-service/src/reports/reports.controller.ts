import {
  Body,
  Controller,
  Get,
  Param,
  Post,
  Query,
} from '@nestjs/common';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { ReportsService, GenerateReportParams, ReportType } from './reports.service';

@Controller({ path: 'analytics/reports', version: '1' })
export class ReportsController {
  constructor(private readonly reportsService: ReportsService) {}

  // POST /v1/analytics/reports — Generate report
  @Post()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async generateReport(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Body() body: GenerateReportParams,
  ) {
    const data = await this.reportsService.generateReport(tenantId, userId, body);
    return { success: true, data };
  }

  // GET /v1/analytics/reports — List generated reports
  @Get()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async listReports(
    @CurrentUser('tenantId') tenantId: string,
    @Query('page') page?: string,
    @Query('pageSize') pageSize?: string,
    @Query('type') type?: ReportType,
  ) {
    const result = await this.reportsService.listReports(tenantId, {
      page: page ? parseInt(page, 10) : undefined,
      pageSize: pageSize ? parseInt(pageSize, 10) : undefined,
      type,
    });
    return { success: true, data: result.items, meta: result.meta };
  }

  // GET /v1/analytics/reports/:id — Get report by ID
  @Get(':id')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async getReport(
    @CurrentUser('tenantId') tenantId: string,
    @Param('id') id: string,
  ) {
    const data = await this.reportsService.getReportById(tenantId, id);
    return { success: true, data };
  }

  // GET /v1/analytics/reports/:id/download — Download report file
  @Get(':id/download')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async downloadReport(
    @CurrentUser('tenantId') tenantId: string,
    @Param('id') id: string,
  ) {
    const data = await this.reportsService.downloadReport(tenantId, id);
    return { success: true, data };
  }
}
