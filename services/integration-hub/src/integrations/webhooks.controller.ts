import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
} from '@nestjs/common';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { WebhooksService } from './webhooks.service';
import { CreateWebhookDto } from './dto/create-webhook.dto';

@Controller({ path: 'integrations/webhooks', version: '1' })
export class WebhooksController {
  constructor(private readonly webhooksService: WebhooksService) {}

  /**
   * POST /v1/integrations/webhooks
   * Register a webhook URL for integration event notifications.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN
   */
  @Post()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async createWebhook(
    @CurrentUser('tenantId') tenantId: string,
    @Body() dto: CreateWebhookDto,
  ) {
    const data = await this.webhooksService.createWebhook(tenantId, dto);
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/webhooks
   * List all registered webhooks for the tenant.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN, DEPARTMENT_MANAGER
   */
  @Get()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async listWebhooks(
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.webhooksService.listWebhooks(tenantId);
    return { success: true, data };
  }

  /**
   * DELETE /v1/integrations/webhooks/:id
   * Remove a registered webhook.
   * Roles: PLATFORM_ADMIN, TENANT_ADMIN
   */
  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async deleteWebhook(
    @CurrentUser('tenantId') tenantId: string,
    @Param('id') webhookId: string,
  ) {
    await this.webhooksService.deleteWebhook(tenantId, webhookId);
  }
}
