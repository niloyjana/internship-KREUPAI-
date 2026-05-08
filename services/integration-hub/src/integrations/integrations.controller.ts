import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
  Query,
} from '@nestjs/common';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { IntegrationsService } from './integrations.service';
import { CreateConnectionDto } from './dto/create-connection.dto';
import { QueryLogsDto } from './dto/query-logs.dto';

@Controller({ path: 'integrations', version: '1' })
export class IntegrationsController {
  constructor(private readonly integrationsService: IntegrationsService) {}

  /**
   * GET /v1/integrations/catalog
   * List available integration providers (static catalog).
   * Roles: Any authenticated user.
   */
  @Get('catalog')
  getCatalog() {
    const data = this.integrationsService.getCatalog();
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/connections
   * List tenant's connected integrations.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN, DEPARTMENT_MANAGER
   */
  @Get('connections')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async listConnections(
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.integrationsService.listConnections(tenantId);
    return { success: true, data };
  }

  /**
   * POST /v1/integrations/connections
   * Initiate new integration connection.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN
   */
  @Post('connections')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async createConnection(
    @CurrentUser('tenantId') tenantId: string,
    @Body() dto: CreateConnectionDto,
  ) {
    const data = await this.integrationsService.createConnection(
      tenantId,
      dto,
    );
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/connections/:connectionId
   * Get connection detail and health.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN, DEPARTMENT_MANAGER
   */
  @Get('connections/:connectionId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async getConnection(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
  ) {
    const data = await this.integrationsService.getConnection(
      tenantId,
      connectionId,
    );
    return { success: true, data };
  }

  /**
   * DELETE /v1/integrations/connections/:connectionId
   * Disconnect and revoke integration.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN
   */
  @Delete('connections/:connectionId')
  @HttpCode(HttpStatus.NO_CONTENT)
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async deleteConnection(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
  ) {
    await this.integrationsService.deleteConnection(
      tenantId,
      connectionId,
    );
  }

  /**
   * GET /v1/integrations/connections/:connectionId/logs
   * Get integration activity logs (paginated).
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN, DEPARTMENT_MANAGER, AUDITOR
   */
  @Get('connections/:connectionId/logs')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async getConnectionLogs(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Query() query: QueryLogsDto,
  ) {
    const result = await this.integrationsService.getConnectionLogs(
      tenantId,
      connectionId,
      query,
    );
    return { success: true, data: result.items, meta: result.meta };
  }

  /**
   * POST /v1/integrations/connections/:connectionId/test
   * Test connectivity.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN
   */
  @Post('connections/:connectionId/test')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async testConnection(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
  ) {
    const data = await this.integrationsService.testConnection(
      tenantId,
      connectionId,
    );
    return { success: true, data };
  }
}
