import { Controller, Get, Put, Body, Query } from '@nestjs/common';
import { NotificationsService } from './notifications.service';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { UpdatePreferencesDto } from './dto/update-preferences.dto';
import { GetHistoryQueryDto } from './dto/get-history.dto';

@Controller({ path: 'notifications', version: '1' })
export class NotificationsController {
  constructor(private readonly notificationsService: NotificationsService) {}

  // GET /v1/notifications/preferences
  @Get('preferences')
  async getPreferences(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
  ) {
    const data = await this.notificationsService.getPreferences(tenantId, userId);
    return { success: true, data };
  }

  // PUT /v1/notifications/preferences
  @Put('preferences')
  async updatePreferences(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Body() dto: UpdatePreferencesDto,
  ) {
    const data = await this.notificationsService.updatePreferences(
      tenantId,
      userId,
      dto.preferences,
    );
    return { success: true, data };
  }

  // GET /v1/notifications/history
  @Get('history')
  async getHistory(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Query() query: GetHistoryQueryDto,
  ) {
    const result = await this.notificationsService.getHistory(tenantId, userId, query);
    return { success: true, data: result.items, meta: result.meta };
  }
}
