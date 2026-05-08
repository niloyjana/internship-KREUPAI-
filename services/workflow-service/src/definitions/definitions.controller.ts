import {
  Controller,
  Get,
  Post,
  Param,
  Query,
  Body,
  UseGuards,
} from '@nestjs/common';
import { DefinitionsService } from './definitions.service';
import { CreateDefinitionDto } from './dto/create-definition.dto';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { RolesGuard } from '../common/guards/roles.guard';

@Controller({ path: 'workflows/definitions', version: '1' })
@UseGuards(RolesGuard)
export class DefinitionsController {
  constructor(private readonly definitionsService: DefinitionsService) {}

  @Get()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async listDefinitions(
    @CurrentUser('tenantId') tenantId: string,
    @Query('agentId') agentId?: string,
  ) {
    const data = await this.definitionsService.listDefinitions(tenantId, agentId);
    return { success: true, data };
  }

  @Post()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async createDefinition(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Body() dto: CreateDefinitionDto,
  ) {
    const data = await this.definitionsService.createDefinition(tenantId, userId, dto);
    return { success: true, data };
  }

  @Get(':definitionId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async getDefinition(
    @CurrentUser('tenantId') tenantId: string,
    @Param('definitionId') definitionId: string,
  ) {
    const data = await this.definitionsService.getDefinition(tenantId, definitionId);
    return { success: true, data };
  }
}
