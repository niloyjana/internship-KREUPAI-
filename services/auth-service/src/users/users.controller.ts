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
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';

@Controller({ path: 'users', version: '1' })
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  // ─── GET /v1/users ── List users (TENANT_ADMIN+) with pagination ────────────

  @Get()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async listUsers(
    @CurrentUser('tenantId') tenantId: string,
    @Query('page') page?: string,
    @Query('pageSize') pageSize?: string,
  ) {
    const data = await this.usersService.listUsers(tenantId, {
      page: page ? parseInt(page, 10) : undefined,
      pageSize: pageSize ? parseInt(pageSize, 10) : undefined,
    });
    return {
      success: true,
      data: data.users,
      meta: data.meta,
    };
  }

  // ─── GET /v1/users/:id ── Get user by ID ────────────────────────────────────

  @Get(':id')
  async getUserById(
    @Param('id') id: string,
    @CurrentUser('tenantId') tenantId: string,
  ) {
    const data = await this.usersService.getUserById(tenantId, id);
    return { success: true, data };
  }

  // ─── POST /v1/users ── Create user (TENANT_ADMIN+) ─────────────────────────

  @Post()
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @HttpCode(HttpStatus.CREATED)
  async createUser(
    @Body() dto: CreateUserDto,
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') actorId: string,
  ) {
    const data = await this.usersService.createUser(tenantId, actorId, dto);
    return { success: true, data };
  }

  // ─── PATCH /v1/users/:id ── Update user (TENANT_ADMIN+) ────────────────────

  @Patch(':id')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async updateUser(
    @Param('id') id: string,
    @Body() dto: UpdateUserDto,
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') actorId: string,
  ) {
    const data = await this.usersService.updateUser(tenantId, id, actorId, dto);
    return { success: true, data };
  }

  // ─── DELETE /v1/users/:id ── Deactivate user (soft delete, TENANT_ADMIN+) ──

  @Delete(':id')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  async deactivateUser(
    @Param('id') id: string,
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') actorId: string,
  ) {
    const data = await this.usersService.deactivateUser(
      tenantId,
      id,
      actorId,
    );
    return { success: true, data };
  }

  // ─── POST /v1/users/:id/reset-password ── Trigger password reset email ─────

  @Post(':id/reset-password')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @HttpCode(HttpStatus.OK)
  async resetPassword(
    @Param('id') id: string,
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') actorId: string,
  ) {
    const data = await this.usersService.triggerPasswordReset(
      tenantId,
      id,
      actorId,
    );
    return { success: true, data };
  }
}
