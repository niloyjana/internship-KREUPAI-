import {
  Body,
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
} from '@nestjs/common';
import { PlansService } from './plans.service';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { JwtPayload } from '../auth/jwt.strategy';

@Controller({ path: 'plans', version: '1' })
export class PlansController {
  constructor(private readonly plansService: PlansService) {}

  // ─── GET /v1/plans ── List available plans with features/limits ─────────────

  @Get()
  async listPlans() {
    const data = await this.plansService.listPlans();
    return { success: true, data };
  }

  // ─── GET /v1/plans/:planId ── Get plan details ──────────────────────────────

  @Get(':planId')
  async getPlanById(@Param('planId') planId: string) {
    const data = await this.plansService.getPlanById(planId);
    return { success: true, data };
  }
}

@Controller({ path: 'tenants', version: '1' })
export class TenantPlanController {
  constructor(private readonly plansService: PlansService) {}

  // ─── POST /v1/tenants/:tenantId/upgrade ── Upgrade tenant plan ──────────────

  @Post(':tenantId/upgrade')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @HttpCode(HttpStatus.OK)
  async upgradePlan(
    @Param('tenantId') tenantId: string,
    @Body('plan') plan: string,
    @CurrentUser() user: JwtPayload,
  ) {
    const data = await this.plansService.upgradeTenantPlan(
      tenantId,
      user.sub,
      plan,
    );
    return { success: true, data };
  }

  // ─── POST /v1/tenants/:tenantId/downgrade ── Downgrade tenant plan ─────────

  @Post(':tenantId/downgrade')
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @HttpCode(HttpStatus.OK)
  async downgradePlan(
    @Param('tenantId') tenantId: string,
    @Body('plan') plan: string,
    @CurrentUser() user: JwtPayload,
  ) {
    const data = await this.plansService.downgradeTenantPlan(
      tenantId,
      user.sub,
      plan,
    );
    return { success: true, data };
  }
}
