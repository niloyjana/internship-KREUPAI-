import {
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Req,
} from '@nestjs/common';
import { Request } from 'express';
import { SessionsService } from './sessions.service';
import { CurrentUser } from '../common/decorators/current-user.decorator';

@Controller({ path: 'sessions', version: '1' })
export class SessionsController {
  constructor(private readonly sessionsService: SessionsService) {}

  // ─── GET /v1/sessions ── List active sessions for current user ──────────────

  @Get()
  async listSessions(
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.sessionsService.listSessions(userId, tenantId);
    return { success: true, data };
  }

  // ─── DELETE /v1/sessions/:id ── Revoke a specific session ───────────────────

  @Delete(':id')
  @HttpCode(HttpStatus.OK)
  async revokeSession(
    @Param('id') id: string,
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.sessionsService.revokeSession(
      id,
      userId,
      tenantId,
    );
    return { success: true, data };
  }

  // ─── DELETE /v1/sessions ── Revoke all sessions except current ──────────────

  @Delete()
  @HttpCode(HttpStatus.OK)
  async revokeAllSessions(
    @Req() req: Request,
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const authHeader = req.headers.authorization || '';
    const currentToken = authHeader.replace('Bearer ', '');
    const data = await this.sessionsService.revokeAllSessions(
      userId,
      tenantId,
      currentToken,
    );
    return { success: true, data };
  }
}
