import {
  Controller,
  Get,
  Patch,
  Param,
  Query,
  Body,
  UseGuards,
} from '@nestjs/common';
import { EscalationsService } from './escalations.service';
import { ListEscalationsQueryDto } from './dto/list-escalations-query.dto';
import { UpdateEscalationDto } from './dto/update-escalation.dto';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { RolesGuard } from '../common/guards/roles.guard';

@Controller({ path: 'workflows/escalations', version: '1' })
@UseGuards(RolesGuard)
export class EscalationsController {
  constructor(private readonly escalationsService: EscalationsService) {}

  @Get()
  async listEscalations(
    @CurrentUser('tenantId') tenantId: string,
    @Query() query: ListEscalationsQueryDto,
  ) {
    const result = await this.escalationsService.listEscalations(
      tenantId,
      query,
    );
    return { success: true, data: result.items, meta: result.meta };
  }

  @Get(':escalationId')
  async getEscalation(
    @CurrentUser('tenantId') tenantId: string,
    @Param('escalationId') escalationId: string,
  ) {
    const data = await this.escalationsService.getEscalation(
      tenantId,
      escalationId,
    );
    return { success: true, data };
  }

  @Patch(':escalationId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  async updateEscalation(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('escalationId') escalationId: string,
    @Body() dto: UpdateEscalationDto,
  ) {
    const data = await this.escalationsService.updateEscalation(
      tenantId,
      escalationId,
      userId,
      dto,
    );
    return { success: true, data };
  }
}
