import {
  Controller,
  Get,
  Post,
  Param,
  Query,
  UseGuards,
} from '@nestjs/common';
import { ExecutionsService } from './executions.service';
import { ListExecutionsQueryDto } from './dto/list-executions-query.dto';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { RolesGuard } from '../common/guards/roles.guard';

@Controller({ path: 'workflows/executions', version: '1' })
@UseGuards(RolesGuard)
export class ExecutionsController {
  constructor(private readonly executionsService: ExecutionsService) {}

  @Get()
  async listExecutions(
    @CurrentUser('tenantId') tenantId: string,
    @Query() query: ListExecutionsQueryDto,
  ) {
    const result = await this.executionsService.listExecutions(tenantId, query);
    return { success: true, data: result.items, meta: result.meta };
  }

  @Get(':executionId')
  async getExecution(
    @CurrentUser('tenantId') tenantId: string,
    @Param('executionId') executionId: string,
  ) {
    const data = await this.executionsService.getExecution(tenantId, executionId);
    return { success: true, data };
  }

  @Get(':executionId/steps')
  async getExecutionSteps(
    @CurrentUser('tenantId') tenantId: string,
    @Param('executionId') executionId: string,
  ) {
    const data = await this.executionsService.getExecutionSteps(tenantId, executionId);
    return { success: true, data };
  }

  @Post(':executionId/cancel')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async cancelExecution(
    @CurrentUser('tenantId') tenantId: string,
    @Param('executionId') executionId: string,
  ) {
    const data = await this.executionsService.cancelExecution(tenantId, executionId);
    return { success: true, data };
  }
}
