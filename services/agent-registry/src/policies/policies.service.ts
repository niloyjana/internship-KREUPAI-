import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { KafkaProducerService, AuditService, TOPICS, AgentStatusChangedPayload } from '@adwp/kafka';
import { UpdatePolicyDto } from './dto/update-policy.dto';
import { Prisma } from '@prisma/client';
import { assertValidPolicyConfig } from '../config/config.validator';
import { deepMergeConfigs } from '../config/deep-merge.util';

@Injectable()
export class PoliciesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ------------------------------------------------------------------
  // GET /v1/agents/:agentId/policies — get current policy for agent+tenant
  // ------------------------------------------------------------------
  async getCurrentPolicy(tenantId: string, agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, name: true, defaultPolicyJson: true },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    const config = await this.prisma.agentConfig.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
    });

    if (!config) {
      throw new NotFoundException('AGENT_CONFIG_NOT_FOUND');
    }

    // Deep merge: platform defaults → tenant overrides (P4 spec)
    const defaultPolicy =
      typeof agentDef.defaultPolicyJson === 'object'
        ? (agentDef.defaultPolicyJson as Record<string, unknown>)
        : {};
    const tenantPolicy =
      typeof config.policyJson === 'object' ? (config.policyJson as Record<string, unknown>) : {};
    const mergedPolicyJson = deepMergeConfigs(defaultPolicy, tenantPolicy);

    return {
      agentId,
      agentName: agentDef.name,
      configVersion: config.configVersion,
      policyJson: mergedPolicyJson,
      tenantPolicyJson: config.policyJson,
      defaultPolicyJson: agentDef.defaultPolicyJson,
      lastConfiguredAt: config.lastConfiguredAt,
      configuredByUserId: config.configuredByUserId,
    };
  }

  // ------------------------------------------------------------------
  // PUT /v1/agents/:agentId/policies — update policy (creates new version)
  // ------------------------------------------------------------------
  async updatePolicy(tenantId: string, agentId: string, dto: UpdatePolicyDto, userId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, name: true },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    const existingConfig = await this.prisma.agentConfig.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
    });

    if (!existingConfig) {
      throw new NotFoundException('AGENT_CONFIG_NOT_FOUND');
    }

    // Validate policyJson structure
    if (typeof dto.policyJson !== 'object' || dto.policyJson === null) {
      throw new BadRequestException('policyJson must be a valid JSON object');
    }

    // Validate against P4 config rules and platform constraints
    assertValidPolicyConfig(dto.policyJson as Record<string, unknown>);

    // Update config with new policy and increment version
    const updated = await this.prisma.agentConfig.update({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      data: {
        policyJson: dto.policyJson as unknown as Prisma.InputJsonValue,
        configVersion: { increment: 1 },
        lastConfiguredAt: new Date(),
        configuredByUserId: userId,
      },
    });

    // Save config history snapshot for versioning
    await this.prisma.agentConfigHistory.create({
      data: {
        agentConfigId: existingConfig.id,
        tenantId,
        version: updated.configVersion,
        displayName: updated.displayName,
        policyJson: updated.policyJson ?? {},
        changedBy: userId,
        changeReason: dto.changeReason ?? null,
        snapshot: {
          displayName: updated.displayName,
          policyJson: updated.policyJson,
          configVersion: updated.configVersion,
        },
      },
    });

    // Publish policy update event via Kafka
    await this.kafkaProducer.emit<AgentStatusChangedPayload>(TOPICS.AGENT_STATUS_CHANGED, {
      tenantId,
      source: 'agent-registry',
      payload: {
        tenantId,
        agentId,
        instanceId: 'default',
        previousStatus: 'CONFIGURED',
        newStatus: 'CONFIGURED',
        currentTaskId: null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'POLICY_UPDATED',
      entityType: 'AGENT_CONFIG',
      entityId: updated.id,
      before: { policyJson: existingConfig.policyJson },
      after: {
        agentId,
        policyJson: updated.policyJson,
        configVersion: updated.configVersion,
      },
    });

    return {
      agentId,
      agentName: agentDef.name,
      configVersion: updated.configVersion,
      policyJson: updated.policyJson,
      lastConfiguredAt: updated.lastConfiguredAt,
      configuredByUserId: updated.configuredByUserId,
    };
  }

  // ------------------------------------------------------------------
  // GET /v1/agents/:agentId/policies/history — list policy version history
  // ------------------------------------------------------------------
  async getPolicyHistory(tenantId: string, agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, name: true },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    const config = await this.prisma.agentConfig.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      select: { id: true },
    });

    if (!config) {
      throw new NotFoundException('AGENT_CONFIG_NOT_FOUND');
    }

    const history = await this.prisma.agentConfigHistory.findMany({
      where: {
        agentConfigId: config.id,
        tenantId,
      },
      orderBy: { version: 'desc' },
    });

    return {
      agentId,
      agentName: agentDef.name,
      versions: history.map((h) => ({
        version: h.version,
        policyJson: h.policyJson,
        changedBy: h.changedBy,
        changeReason: h.changeReason,
        createdAt: h.createdAt.toISOString(),
      })),
      totalVersions: history.length,
    };
  }

  // ------------------------------------------------------------------
  // POST /v1/agents/:agentId/policies/rollback/:version — rollback to version
  // ------------------------------------------------------------------
  async rollbackPolicy(tenantId: string, agentId: string, targetVersion: number, userId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, name: true },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    const config = await this.prisma.agentConfig.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
    });

    if (!config) {
      throw new NotFoundException('AGENT_CONFIG_NOT_FOUND');
    }

    // Find the target version in history
    const targetHistory = await this.prisma.agentConfigHistory.findFirst({
      where: {
        agentConfigId: config.id,
        tenantId,
        version: targetVersion,
      },
    });

    if (!targetHistory) {
      throw new NotFoundException('POLICY_VERSION_NOT_FOUND');
    }

    const previousPolicyJson = config.policyJson;

    // Apply rollback: update config with the historical policy and increment version
    const updated = await this.prisma.agentConfig.update({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      data: {
        policyJson: targetHistory.policyJson ?? {},
        configVersion: { increment: 1 },
        lastConfiguredAt: new Date(),
        configuredByUserId: userId,
      },
    });

    // Save rollback as a new history entry
    await this.prisma.agentConfigHistory.create({
      data: {
        agentConfigId: config.id,
        tenantId,
        version: updated.configVersion,
        displayName: updated.displayName,
        policyJson: updated.policyJson ?? {},
        changedBy: userId,
        changeReason: `Rollback to version ${targetVersion}`,
        snapshot: {
          displayName: updated.displayName,
          policyJson: updated.policyJson,
          configVersion: updated.configVersion,
          rolledBackFrom: config.configVersion,
          rolledBackTo: targetVersion,
        },
      },
    });

    await this.kafkaProducer.emit<AgentStatusChangedPayload>(TOPICS.AGENT_STATUS_CHANGED, {
      tenantId,
      source: 'agent-registry',
      payload: {
        tenantId,
        agentId,
        instanceId: 'default',
        previousStatus: 'CONFIGURED',
        newStatus: 'CONFIGURED',
        currentTaskId: null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'POLICY_ROLLBACK',
      entityType: 'AGENT_CONFIG',
      entityId: updated.id,
      before: {
        policyJson: previousPolicyJson,
        configVersion: config.configVersion,
      },
      after: {
        policyJson: updated.policyJson,
        configVersion: updated.configVersion,
        rolledBackToVersion: targetVersion,
      },
    });

    return {
      agentId,
      agentName: agentDef.name,
      previousVersion: config.configVersion,
      rolledBackToVersion: targetVersion,
      currentVersion: updated.configVersion,
      policyJson: updated.policyJson,
      lastConfiguredAt: updated.lastConfiguredAt,
      configuredByUserId: updated.configuredByUserId,
    };
  }
}
