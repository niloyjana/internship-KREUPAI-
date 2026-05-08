import {
  Controller,
  Get,
  Put,
  Post,
  Param,
  Query,
  Body,
} from '@nestjs/common';
import { AgentsService } from './agents.service';
import { CatalogQueryDto } from './dto/catalog-query.dto';
import { UpdateAgentConfigDto } from './dto/update-agent-config.dto';
import { Public } from '../common/decorators/public.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';

@Controller({ path: 'agents', version: '1' })
export class AgentsController {
  constructor(private readonly agentsService: AgentsService) {}

  // ─── Catalog (public / any authenticated user) ──────────────────────

  @Public()
  @Get('catalog')
  listCatalog(@Query() query: CatalogQueryDto) {
    return this.agentsService.listCatalog(query);
  }

  @Public()
  @Get('catalog/:agentId')
  getCatalogAgent(@Param('agentId') agentId: string) {
    return this.agentsService.getCatalogAgent(agentId);
  }

  // ─── Subscribed Agents (tenant-scoped) ──────────────────────────────

  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  @Get('subscribed')
  listSubscribedAgents(@CurrentUser('tenantId') tenantId: string) {
    return this.agentsService.listSubscribedAgents(tenantId);
  }

  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  @Get(':agentId/config')
  getAgentConfig(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    return this.agentsService.getAgentConfig(tenantId, agentId);
  }

  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  @Put(':agentId/config')
  updateAgentConfig(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('agentId') agentId: string,
    @Body() dto: UpdateAgentConfigDto,
  ) {
    return this.agentsService.updateAgentConfig(tenantId, agentId, dto, userId);
  }

  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  @Get(':agentId/status')
  getAgentStatus(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    return this.agentsService.getAgentStatus(tenantId, agentId);
  }

  // ─── Enable / Pause (admin only) ───────────────────────────────────

  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @Post(':agentId/enable')
  enableAgent(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    return this.agentsService.enableAgent(tenantId, agentId);
  }

  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @Post(':agentId/pause')
  pauseAgent(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    return this.agentsService.pauseAgent(tenantId, agentId);
  }
}
