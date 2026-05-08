import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
  Req,
  UseGuards,
} from '@nestjs/common';
import { Request } from 'express';
import { AuthService } from './auth.service';
import { LoginDto } from './dto/login.dto';
import { RefreshDto } from './dto/refresh.dto';
import { CreateApiKeyDto } from './dto/create-api-key.dto';
import { VerifyMfaDto } from './dto/verify-mfa.dto';
import { Public } from '../common/decorators/public.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { RolesGuard } from '../common/guards/roles.guard';

@Controller({ path: 'auth', version: '1' })
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  // ----------------------------------------------------------------
  // POST /v1/auth/login
  // ----------------------------------------------------------------
  @Public()
  @Post('login')
  async login(@Body() dto: LoginDto) {
    const data = await this.authService.login(
      dto.email,
      dto.password,
      dto.tenantSlug,
    );
    return { success: true, data };
  }

  // ----------------------------------------------------------------
  // POST /v1/auth/refresh
  // ----------------------------------------------------------------
  @Public()
  @Post('refresh')
  async refresh(@Body() dto: RefreshDto) {
    const data = await this.authService.refresh(dto.refreshToken);
    return { success: true, data };
  }

  // ----------------------------------------------------------------
  // POST /v1/auth/logout
  // ----------------------------------------------------------------
  @Post('logout')
  @HttpCode(HttpStatus.NO_CONTENT)
  async logout(@Req() req: Request) {
    const authHeader = req.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    await this.authService.logout(token);
  }

  // ----------------------------------------------------------------
  // GET /v1/auth/me
  // ----------------------------------------------------------------
  @Get('me')
  async me(
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.authService.getProfile(userId, tenantId);
    return { success: true, data };
  }

  // ----------------------------------------------------------------
  // POST /v1/auth/mfa/setup
  // ----------------------------------------------------------------
  @Post('mfa/setup')
  @HttpCode(HttpStatus.OK)
  async setupMfa(
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.authService.setupMfa(userId, tenantId);
    return { success: true, data };
  }

  // ----------------------------------------------------------------
  // POST /v1/auth/mfa/verify
  // ----------------------------------------------------------------
  @Post('mfa/verify')
  @HttpCode(HttpStatus.OK)
  async verifyMfa(
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
    @Body() dto: VerifyMfaDto,
  ) {
    const data = await this.authService.verifyMfa(userId, tenantId, dto.code);
    return { success: true, data };
  }

  // ----------------------------------------------------------------
  // POST /v1/auth/api-keys
  // ----------------------------------------------------------------
  @Post('api-keys')
  @UseGuards(RolesGuard)
  @Roles('TENANT_ADMIN', 'PLATFORM_ADMIN')
  async createApiKey(
    @CurrentUser('userId') userId: string,
    @CurrentUser('tenantId') tenantId: string,
    @Body() dto: CreateApiKeyDto,
  ) {
    const data = await this.authService.createApiKey(
      userId,
      tenantId,
      dto.name,
      dto.expiresAt,
    );
    return { success: true, data };
  }

  // ----------------------------------------------------------------
  // DELETE /v1/auth/api-keys/:keyId
  // ----------------------------------------------------------------
  @Delete('api-keys/:keyId')
  @HttpCode(HttpStatus.NO_CONTENT)
  @UseGuards(RolesGuard)
  @Roles('TENANT_ADMIN', 'PLATFORM_ADMIN')
  async revokeApiKey(
    @Param('keyId') keyId: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    await this.authService.revokeApiKey(keyId, tenantId);
  }
}
