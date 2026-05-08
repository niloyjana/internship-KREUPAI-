import {
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { AuditService } from '@adwp/kafka';

@Injectable()
export class CapabilitiesService {
  constructor(
    private readonly prisma: PrismaService,
    // @ts-ignore TS6138 — injected for future use
    private readonly audit: AuditService,
  ) {}

  // ------------------------------------------------------------------
  // GET /v1/agents/:agentId/capabilities — list capabilities for agent
  // ------------------------------------------------------------------
  async getAgentCapabilities(agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: {
        id: true,
        agentId: true,
        name: true,
        capabilities: true,
      },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    // capabilities is stored as a JSON array on AgentDefinition
    const capabilities = Array.isArray(agentDef.capabilities)
      ? agentDef.capabilities
      : [];

    return {
      agentId: agentDef.agentId,
      agentName: agentDef.name,
      capabilities,
      totalCapabilities: capabilities.length,
    };
  }

  // ------------------------------------------------------------------
  // GET /v1/capabilities — list all capabilities across all agents
  // ------------------------------------------------------------------
  async listAllCapabilities() {
    const agents = await this.prisma.agentDefinition.findMany({
      where: { isActive: true },
      select: {
        agentId: true,
        name: true,
        department: true,
        capabilities: true,
      },
      orderBy: { name: 'asc' },
    });

    const allCapabilities: Array<{
      capabilityId: string;
      name: string;
      description: string | null;
      agentId: string;
      agentName: string;
      department: string;
    }> = [];

    for (const agent of agents) {
      const capabilities = Array.isArray(agent.capabilities)
        ? agent.capabilities
        : [];

      for (const cap of capabilities) {
        const capObj =
          typeof cap === 'object' && cap !== null
            ? (cap as Record<string, unknown>)
            : { id: String(cap), name: String(cap) };

        allCapabilities.push({
          capabilityId: String(capObj.id ?? capObj.name ?? cap),
          name: String(capObj.name ?? cap),
          description:
            typeof capObj.description === 'string'
              ? capObj.description
              : null,
          agentId: agent.agentId,
          agentName: agent.name,
          department: agent.department,
        });
      }
    }

    return {
      capabilities: allCapabilities,
      totalCapabilities: allCapabilities.length,
    };
  }

  // ------------------------------------------------------------------
  // GET /v1/capabilities/:capabilityId — get capability details
  // ------------------------------------------------------------------
  async getCapabilityDetail(capabilityId: string) {
    // Search across all active agents for the matching capability
    const agents = await this.prisma.agentDefinition.findMany({
      where: { isActive: true },
      select: {
        agentId: true,
        name: true,
        department: true,
        capabilities: true,
        requiredIntegrations: true,
      },
    });

    for (const agent of agents) {
      const capabilities = Array.isArray(agent.capabilities)
        ? agent.capabilities
        : [];

      for (const cap of capabilities) {
        const capObj =
          typeof cap === 'object' && cap !== null
            ? (cap as Record<string, unknown>)
            : { id: String(cap), name: String(cap) };

        const id = String(capObj.id ?? capObj.name ?? cap);

        if (id === capabilityId) {
          return {
            capabilityId: id,
            name: String(capObj.name ?? cap),
            description:
              typeof capObj.description === 'string'
                ? capObj.description
                : null,
            parameters:
              typeof capObj.parameters === 'object'
                ? capObj.parameters
                : null,
            agentId: agent.agentId,
            agentName: agent.name,
            department: agent.department,
            requiredIntegrations: agent.requiredIntegrations,
          };
        }
      }
    }

    throw new NotFoundException('CAPABILITY_NOT_FOUND');
  }
}
