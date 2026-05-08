import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Param,
  Query,
} from '@nestjs/common';
import { SubscriptionsService } from './subscriptions.service';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { SubscribeAgentDto } from './dto/subscribe-agent.dto';
import { UsageQueryDto } from './dto/usage-query.dto';
import { InvoiceQueryDto } from './dto/invoice-query.dto';

@Controller({ path: 'subscriptions', version: '1' })
export class SubscriptionsController {
  constructor(private readonly subscriptionsService: SubscriptionsService) {}

  /**
   * GET /v1/subscriptions
   * Get tenant's agent subscriptions with pricing summary.
   */
  @Get()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async getSubscriptions(
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.subscriptionsService.getSubscriptions(tenantId);
    return { success: true, data };
  }

  /**
   * POST /v1/subscriptions/agents
   * Subscribe to a new agent.
   */
  @Post('agents')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async subscribeAgent(
    @CurrentUser('tenantId') tenantId: string,
    @Body() dto: SubscribeAgentDto,
  ) {
    const data = await this.subscriptionsService.subscribeAgent(tenantId, dto);
    return { success: true, data };
  }

  /**
   * DELETE /v1/subscriptions/agents/:agentId
   * Unsubscribe from an agent.
   */
  @Delete('agents/:agentId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async unsubscribeAgent(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    const data = await this.subscriptionsService.unsubscribeAgent(
      tenantId,
      agentId,
    );
    return { success: true, data };
  }

  /**
   * GET /v1/subscriptions/usage
   * Get usage metering for the current billing period.
   */
  @Get('usage')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async getUsage(
    @CurrentUser('tenantId') tenantId: string,
    @Query() query: UsageQueryDto,
  ) {
    const data = await this.subscriptionsService.getUsage(tenantId, query);
    return { success: true, data };
  }

  /**
   * GET /v1/subscriptions/invoices
   * List invoices for tenant with pagination.
   */
  @Get('invoices')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async getInvoices(
    @CurrentUser('tenantId') tenantId: string,
    @Query() query: InvoiceQueryDto,
  ) {
    const result = await this.subscriptionsService.getInvoices(tenantId, query);
    return {
      success: true,
      data: result.invoices,
      meta: result.meta,
    };
  }

  /**
   * GET /v1/subscriptions/invoices/:invoiceId
   * Get invoice detail with line items.
   */
  @Get('invoices/:invoiceId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async getInvoiceDetail(
    @CurrentUser('tenantId') tenantId: string,
    @Param('invoiceId') invoiceId: string,
  ) {
    const data = await this.subscriptionsService.getInvoiceDetail(
      tenantId,
      invoiceId,
    );
    return { success: true, data };
  }
}
