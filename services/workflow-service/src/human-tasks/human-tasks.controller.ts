import {
  Controller,
  Get,
  Post,
  Param,
  Query,
  Body,
  UseGuards,
} from '@nestjs/common';
import { HumanTasksService } from './human-tasks.service';
import { ListHumanTasksQueryDto } from './dto/list-human-tasks-query.dto';
import { ResolveTaskDto } from './dto/resolve-task.dto';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { RolesGuard } from '../common/guards/roles.guard';

@Controller({ path: 'workflows/human-tasks', version: '1' })
@UseGuards(RolesGuard)
export class HumanTasksController {
  constructor(private readonly humanTasksService: HumanTasksService) {}

  @Get()
  async listHumanTasks(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Query() query: ListHumanTasksQueryDto,
  ) {
    const result = await this.humanTasksService.listHumanTasks(
      tenantId,
      userId,
      query,
    );
    return { success: true, data: result.items, meta: result.meta };
  }

  @Get(':taskId')
  async getHumanTask(
    @CurrentUser('tenantId') tenantId: string,
    @Param('taskId') taskId: string,
  ) {
    const data = await this.humanTasksService.getHumanTask(tenantId, taskId);
    return { success: true, data };
  }

  @Post(':taskId/resolve')
  async resolveHumanTask(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('taskId') taskId: string,
    @Body() dto: ResolveTaskDto,
  ) {
    const data = await this.humanTasksService.resolveHumanTask(
      tenantId,
      taskId,
      userId,
      dto,
    );
    return { success: true, data };
  }
}
