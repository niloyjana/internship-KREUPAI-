import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Patch,
  Post,
  Query,
} from '@nestjs/common';
import { TenantsService } from './tenants.service';
import { CreateTenantDto } from './dto/create-tenant.dto';
import { UpdateTenantDto } from './dto/update-tenant.dto';
import { InviteUserDto } from './dto/invite-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { PaginationDto } from './dto/pagination.dto';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { JwtPayload } from '../auth/jwt.strategy';

@Controller({ path: 'tenants', version: '1' })
export class TenantsController {
  constructor(private readonly tenantsService: TenantsService) {}

  // ─── POST /v1/tenants ── Create tenant + admin user (PLATFORM_ADMIN only) ──

  @Post()
  @Roles('PLATFORM_ADMIN')
  @HttpCode(HttpStatus.CREATED)
  async createTenant(
    @Body() dto: CreateTenantDto,
    @CurrentUser() _user: JwtPayload,
  ) {
    const data = await this.tenantsService.createTenant(dto);
    return {
      success: true,
      data,
    };
  }

  // ─── GET /v1/tenants/:tenantId ── Get tenant details (TENANT_ADMIN+) ───────

  @Get(':tenantId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async getTenant(
    @Param('tenantId') tenantId: string,
    @CurrentUser() _user: JwtPayload,
  ) {
    const data = await this.tenantsService.getTenant(tenantId);
    return {
      success: true,
      data,
    };
  }

  // ─── PATCH /v1/tenants/:tenantId ── Update tenant config (TENANT_ADMIN) ────

  @Patch(':tenantId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async updateTenant(
    @Param('tenantId') tenantId: string,
    @Body() dto: UpdateTenantDto,
    @CurrentUser() _user: JwtPayload,
  ) {
    const data = await this.tenantsService.updateTenant(tenantId, dto);
    return {
      success: true,
      data,
    };
  }

  // ─── GET /v1/tenants/:tenantId/users ── List users with pagination ─────────

  @Get(':tenantId/users')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  async listUsers(
    @Param('tenantId') tenantId: string,
    @Query() query: PaginationDto,
    @CurrentUser() _user: JwtPayload,
  ) {
    const result = await this.tenantsService.listUsers(tenantId, query);
    return {
      success: true,
      data: result.users,
      meta: result.meta,
    };
  }

  // ─── POST /v1/tenants/:tenantId/users ── Invite user (TENANT_ADMIN only) ──

  @Post(':tenantId/users')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @HttpCode(HttpStatus.CREATED)
  async inviteUser(
    @Param('tenantId') tenantId: string,
    @Body() dto: InviteUserDto,
    @CurrentUser() _user: JwtPayload,
  ) {
    const data = await this.tenantsService.inviteUser(tenantId, dto);
    return {
      success: true,
      data,
    };
  }

  // ─── PATCH /v1/tenants/:tenantId/users/:userId ── Update user role/status ──

  @Patch(':tenantId/users/:userId')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async updateUser(
    @Param('tenantId') tenantId: string,
    @Param('userId') userId: string,
    @Body() dto: UpdateUserDto,
    @CurrentUser() _user: JwtPayload,
  ) {
    const data = await this.tenantsService.updateUser(tenantId, userId, dto);
    return {
      success: true,
      data,
    };
  }

  // ─── DELETE /v1/tenants/:tenantId/users/:userId ── Remove user from tenant ─

  @Delete(':tenantId/users/:userId')
  @HttpCode(HttpStatus.NO_CONTENT)
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async removeUser(
    @Param('tenantId') tenantId: string,
    @Param('userId') userId: string,
    @CurrentUser() _user: JwtPayload,
  ) {
    await this.tenantsService.removeUser(tenantId, userId);
  }
}
