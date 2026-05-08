import {
  Body,
  Controller,
  Get,
  Param,
  Patch,
  Post,
} from '@nestjs/common';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { TemplatesService, CreateTemplateData, UpdateTemplateData } from './templates.service';

@Controller({ path: 'notifications/templates', version: '1' })
export class TemplatesController {
  constructor(private readonly templatesService: TemplatesService) {}

  // GET /v1/notifications/templates
  @Get()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async listTemplates(
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.templatesService.listTemplates(tenantId);
    return { success: true, data };
  }

  // POST /v1/notifications/templates
  @Post()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async createTemplate(
    @CurrentUser('tenantId') tenantId: string,
    @Body() body: CreateTemplateData,
  ) {
    const data = await this.templatesService.createTemplate(tenantId, body);
    return { success: true, data };
  }

  // PATCH /v1/notifications/templates/:id
  @Patch(':id')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async updateTemplate(
    @CurrentUser('tenantId') tenantId: string,
    @Param('id') id: string,
    @Body() body: UpdateTemplateData,
  ) {
    const data = await this.templatesService.updateTemplate(tenantId, id, body);
    return { success: true, data };
  }

  // POST /v1/notifications/templates/:id/render
  @Post(':id/render')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async renderTemplate(
    @CurrentUser('tenantId') tenantId: string,
    @Param('id') id: string,
    @Body() body: { variables: Record<string, string> },
  ) {
    const data = await this.templatesService.renderTemplate(
      tenantId,
      id,
      body.variables,
    );
    return { success: true, data };
  }
}
