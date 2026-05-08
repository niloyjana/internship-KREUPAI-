import {
  Controller,
  Get,
  Post,
  Param,
  Body,
} from '@nestjs/common';
import { TemplatesService } from './templates.service';
import { Public } from '../common/decorators/public.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { CreateTemplateDto } from './dto/create-template.dto';

@Controller({ path: 'templates', version: '1' })
export class TemplatesController {
  constructor(private readonly templatesService: TemplatesService) {}

  /**
   * GET /v1/templates
   * List all config templates.
   */
  @Public()
  @Get()
  async listTemplates() {
    const data = await this.templatesService.listTemplates();
    return { success: true, data };
  }

  /**
   * GET /v1/templates/:templateId
   * Get template details.
   */
  @Public()
  @Get(':templateId')
  async getTemplateDetail(
    @Param('templateId') templateId: string,
  ) {
    const data = await this.templatesService.getTemplateDetail(templateId);
    return { success: true, data };
  }

  /**
   * POST /v1/templates
   * Create a new config template (PLATFORM_ADMIN only).
   */
  @Roles('PLATFORM_ADMIN')
  @Post()
  async createTemplate(
    @CurrentUser('userId') userId: string,
    @Body() dto: CreateTemplateDto,
  ) {
    const data = await this.templatesService.createTemplate(dto, userId);
    return { success: true, data };
  }
}

/**
 * Nested controller for agent-scoped template application routes.
 * POST /v1/agents/:agentId/apply-template/:templateId
 */
@Controller({ path: 'agents', version: '1' })
export class AgentTemplatesController {
  constructor(private readonly templatesService: TemplatesService) {}

  /**
   * POST /v1/agents/:agentId/apply-template/:templateId
   * Apply a config template to an agent's configuration.
   */
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @Post(':agentId/apply-template/:templateId')
  async applyTemplate(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('agentId') agentId: string,
    @Param('templateId') templateId: string,
  ) {
    const data = await this.templatesService.applyTemplate(
      tenantId,
      agentId,
      templateId,
      userId,
    );
    return { success: true, data };
  }
}
