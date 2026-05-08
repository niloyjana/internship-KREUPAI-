import {
  Controller,
  Get,
  Param,
} from '@nestjs/common';
import { CapabilitiesService } from './capabilities.service';
import { Public } from '../common/decorators/public.decorator';

@Controller({ path: 'capabilities', version: '1' })
export class CapabilitiesController {
  constructor(private readonly capabilitiesService: CapabilitiesService) {}

  /**
   * GET /v1/capabilities
   * List all capabilities across all agents.
   */
  @Public()
  @Get()
  async listAllCapabilities() {
    const data = await this.capabilitiesService.listAllCapabilities();
    return { success: true, data };
  }

  /**
   * GET /v1/capabilities/:capabilityId
   * Get capability details.
   */
  @Public()
  @Get(':capabilityId')
  async getCapabilityDetail(
    @Param('capabilityId') capabilityId: string,
  ) {
    const data = await this.capabilitiesService.getCapabilityDetail(
      capabilityId,
    );
    return { success: true, data };
  }
}

/**
 * Nested controller for agent-scoped capability routes.
 * GET /v1/agents/:agentId/capabilities
 */
@Controller({ path: 'agents', version: '1' })
export class AgentCapabilitiesController {
  constructor(private readonly capabilitiesService: CapabilitiesService) {}

  /**
   * GET /v1/agents/:agentId/capabilities
   * List capabilities for a specific agent.
   */
  @Public()
  @Get(':agentId/capabilities')
  async getAgentCapabilities(
    @Param('agentId') agentId: string,
  ) {
    const data = await this.capabilitiesService.getAgentCapabilities(agentId);
    return { success: true, data };
  }
}
