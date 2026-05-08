import {
  Controller,
  Get,
  Put,
  Post,
  Param,
  Body,
  ParseIntPipe,
} from '@nestjs/common';
import { PoliciesService } from './policies.service';
import { Roles } from '../common/decorators/roles.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { UpdatePolicyDto } from './dto/update-policy.dto';

@Controller({ path: 'agents', version: '1' })
export class PoliciesController {
  constructor(private readonly policiesService: PoliciesService) {}

  /**
   * GET /v1/agents/:agentId/policies
   * Get current policy for agent + tenant.
   */
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER')
  @Get(':agentId/policies')
  async getCurrentPolicy(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    const data = await this.policiesService.getCurrentPolicy(
      tenantId,
      agentId,
    );
    return { success: true, data };
  }

  /**
   * PUT /v1/agents/:agentId/policies
   * Update policy (creates new version).
   */
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @Put(':agentId/policies')
  async updatePolicy(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('agentId') agentId: string,
    @Body() dto: UpdatePolicyDto,
  ) {
    const data = await this.policiesService.updatePolicy(
      tenantId,
      agentId,
      dto,
      userId,
    );
    return { success: true, data };
  }

  /**
   * GET /v1/agents/:agentId/policies/history
   * List policy version history.
   */
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'AUDITOR')
  @Get(':agentId/policies/history')
  async getPolicyHistory(
    @CurrentUser('tenantId') tenantId: string,
    @Param('agentId') agentId: string,
  ) {
    const data = await this.policiesService.getPolicyHistory(
      tenantId,
      agentId,
    );
    return { success: true, data };
  }

  /**
   * POST /v1/agents/:agentId/policies/rollback/:version
   * Rollback to a specific policy version.
   */
  @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
  @Post(':agentId/policies/rollback/:version')
  async rollbackPolicy(
    @CurrentUser('tenantId') tenantId: string,
    @CurrentUser('userId') userId: string,
    @Param('agentId') agentId: string,
    @Param('version', ParseIntPipe) version: number,
  ) {
    const data = await this.policiesService.rollbackPolicy(
      tenantId,
      agentId,
      version,
      userId,
    );
    return { success: true, data };
  }
}
