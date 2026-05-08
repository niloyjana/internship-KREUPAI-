import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  AgentStatusChangedPayload,
  AgentActivatedPayload,
} from '@adwp/kafka';
import { CatalogQueryDto } from './dto/catalog-query.dto';
import { UpdateAgentConfigDto } from './dto/update-agent-config.dto';
import { Prisma } from '@prisma/client';
import { assertValidPolicyConfig } from '../config/config.validator';
import { deepMergeConfigs } from '../config/deep-merge.util';

@Injectable()
export class AgentsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ─── Catalog ────────────────────────────────────────────────────────

  async listCatalog(query: CatalogQueryDto) {
    const { department, isActive, page = 1, limit = 20, search } = query;
    const skip = (page - 1) * limit;

    const where: Prisma.AgentDefinitionWhereInput = {};

    if (department) {
      where.department = department;
    }

    if (isActive !== undefined) {
      where.isActive = isActive;
    }

    if (search) {
      where.OR = [
        { name: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } },
        { agentId: { contains: search, mode: 'insensitive' } },
      ];
    }

    const [items, total] = await Promise.all([
      this.prisma.agentDefinition.findMany({
        where,
        select: {
          id: true,
          agentId: true,
          name: true,
          department: true,
          description: true,
          version: true,
          monthlyPricingUsd: true,
          capabilities: true,
          requiredIntegrations: true,
          isActive: true,
        },
        skip,
        take: limit,
        orderBy: { name: 'asc' },
      }),
      this.prisma.agentDefinition.count({ where }),
    ]);

    return {
      success: true,
      data: items,
      meta: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  async getCatalogAgent(agentId: string) {
    const agent = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
    });

    if (!agent) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    return {
      success: true,
      data: agent,
    };
  }

  // ─── Subscribed Agents ──────────────────────────────────────────────

  async listSubscribedAgents(tenantId: string) {
    const configs = await this.prisma.agentConfig.findMany({
      where: { tenantId },
      include: {
        agentDefinition: {
          select: {
            agentId: true,
            name: true,
            department: true,
            description: true,
            capabilities: true,
          },
        },
      },
    });

    // Fetch subscriptions for this tenant to get subscription status
    const subscriptions = await this.prisma.agentSubscription.findMany({
      where: { tenantId },
    });

    const subscriptionMap = new Map(subscriptions.map((sub) => [sub.agentDefinitionId, sub]));

    // Get today's date boundaries for task counts
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const todayEnd = new Date();
    todayEnd.setHours(23, 59, 59, 999);

    // Fetch today's agent instances for task counts
    const todayInstances = await this.prisma.agentInstance.groupBy({
      by: ['agentConfigId'],
      where: {
        tenantId,
        createdAt: { gte: todayStart, lte: todayEnd },
      },
      _count: { id: true },
    });

    const instanceCountMap = new Map(
      todayInstances.map((inst) => [inst.agentConfigId, inst._count.id]),
    );

    // Fetch pending escalations per agent
    const pendingEscalations = await this.prisma.escalationTicket.groupBy({
      by: ['agentId'],
      where: {
        tenantId,
        status: { in: ['OPEN', 'IN_REVIEW'] },
      },
      _count: { id: true },
    });

    const escalationMap = new Map(pendingEscalations.map((esc) => [esc.agentId, esc._count.id]));

    // Get latest agent instance per config for lastActiveAt and status
    const latestInstances = await this.prisma.agentInstance.findMany({
      where: {
        tenantId,
        agentConfigId: { in: configs.map((c) => c.id) },
      },
      orderBy: { updatedAt: 'desc' },
      distinct: ['agentConfigId'],
      select: {
        agentConfigId: true,
        status: true,
        lastActiveAt: true,
      },
    });

    const latestInstanceMap = new Map(latestInstances.map((inst) => [inst.agentConfigId, inst]));

    const data = configs.map((config) => {
      const subscription = subscriptionMap.get(config.agentDefinitionId);
      const latestInstance = latestInstanceMap.get(config.id);
      const agentIdStr = config.agentDefinition.agentId;

      return {
        agentId: agentIdStr,
        name: config.agentDefinition.name,
        displayName: config.displayName || config.agentDefinition.name,
        department: config.agentDefinition.department,
        status: latestInstance?.status || (config.isEnabled ? 'IDLE' : 'PAUSED'),
        subscriptionStatus: subscription?.status || null,
        integrationIds: config.integrationIds,
        isEnabled: config.isEnabled,
        lastActiveAt: latestInstance?.lastActiveAt || null,
        todayTaskCount: instanceCountMap.get(config.id) || 0,
        pendingEscalations: escalationMap.get(agentIdStr) || 0,
      };
    });

    return {
      success: true,
      data,
    };
  }

  // ─── Agent Config ───────────────────────────────────────────────────

  async getAgentConfig(tenantId: string, agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, defaultPolicyJson: true },
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
      include: {
        agentDefinition: {
          select: {
            agentId: true,
            name: true,
            defaultPolicyJson: true,
          },
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
      success: true,
      data: {
        id: config.id,
        agentId: config.agentDefinition.agentId,
        name: config.agentDefinition.name,
        displayName: config.displayName,
        policyJson: mergedPolicyJson,
        integrationIds: config.integrationIds,
        isEnabled: config.isEnabled,
        configVersion: config.configVersion,
        lastConfiguredAt: config.lastConfiguredAt,
        configuredByUserId: config.configuredByUserId,
        createdAt: config.createdAt,
        updatedAt: config.updatedAt,
      },
    };
  }

  async updateAgentConfig(
    tenantId: string,
    agentId: string,
    dto: UpdateAgentConfigDto,
    userId: string,
  ) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true },
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

    // Validate policyJson if provided — ensure it has expected structure
    if (dto.policyJson !== undefined) {
      if (typeof dto.policyJson !== 'object' || dto.policyJson === null) {
        throw new BadRequestException('policyJson must be a valid JSON object');
      }
      // Validate against P4 config rules and platform constraints
      assertValidPolicyConfig(dto.policyJson as Record<string, unknown>);
    }

    const updateData: Prisma.AgentConfigUpdateInput = {
      lastConfiguredAt: new Date(),
      configuredByUserId: userId,
      configVersion: { increment: 1 },
    };

    if (dto.displayName !== undefined) {
      updateData.displayName = dto.displayName;
    }

    if (dto.policyJson !== undefined) {
      updateData.policyJson = dto.policyJson as unknown as Prisma.InputJsonValue;
    }

    if (dto.integrationIds !== undefined) {
      updateData.integrationIds = dto.integrationIds;
    }

    const updated = await this.prisma.agentConfig.update({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      data: updateData,
      include: {
        agentDefinition: {
          select: { agentId: true, name: true },
        },
      },
    });

    // Publish agent config updated event via Kafka
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

    // Save config history snapshot
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

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'AGENT_CONFIG_UPDATED',
      entityType: 'AGENT_CONFIG',
      entityId: updated.id,
      after: { agentId, configVersion: updated.configVersion },
    });

    return {
      success: true,
      data: {
        id: updated.id,
        agentId: updated.agentDefinition.agentId,
        name: updated.agentDefinition.name,
        displayName: updated.displayName,
        policyJson: updated.policyJson,
        integrationIds: updated.integrationIds,
        isEnabled: updated.isEnabled,
        configVersion: updated.configVersion,
        lastConfiguredAt: updated.lastConfiguredAt,
        configuredByUserId: updated.configuredByUserId,
        updatedAt: updated.updatedAt,
      },
    };
  }

  // ─── Agent Status ───────────────────────────────────────────────────

  async getAgentStatus(tenantId: string, agentId: string) {
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

    // Get the latest agent instance for current task info
    const latestInstance = await this.prisma.agentInstance.findFirst({
      where: {
        tenantId,
        agentConfigId: config.id,
      },
      orderBy: { updatedAt: 'desc' },
      select: {
        status: true,
        currentTaskId: true,
        lastActiveAt: true,
      },
    });

    // Today's date boundaries
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const todayEnd = new Date();
    todayEnd.setHours(23, 59, 59, 999);

    // Get today's workflow execution stats for this agent + tenant
    const todayExecutions = await this.prisma.workflowExecution.findMany({
      where: {
        tenantId,
        agentId,
        createdAt: { gte: todayStart, lte: todayEnd },
      },
      select: {
        status: true,
        durationMs: true,
        llmCostUsd: true,
      },
    });

    const tasksCompleted = todayExecutions.filter((e) => e.status === 'COMPLETED').length;
    const tasksFailed = todayExecutions.filter((e) => e.status === 'FAILED').length;

    // Count escalations for today
    const tasksEscalated = await this.prisma.escalationTicket.count({
      where: {
        tenantId,
        agentId,
        createdAt: { gte: todayStart, lte: todayEnd },
      },
    });

    // Calculate avg duration and total cost
    const completedExecutions = todayExecutions.filter(
      (e) => e.status === 'COMPLETED' && e.durationMs != null,
    );
    const avgDurationMs =
      completedExecutions.length > 0
        ? Math.round(
            completedExecutions.reduce((sum, e) => sum + (e.durationMs || 0), 0) /
              completedExecutions.length,
          )
        : null;

    const tokenCostUsd = todayExecutions.reduce(
      (sum, e) => sum + (e.llmCostUsd ? Number(e.llmCostUsd) : 0),
      0,
    );

    return {
      success: true,
      data: {
        agentId,
        name: agentDef.name,
        status: latestInstance?.status || (config.isEnabled ? 'IDLE' : 'PAUSED'),
        isEnabled: config.isEnabled,
        currentTaskId: latestInstance?.currentTaskId || null,
        lastActiveAt: latestInstance?.lastActiveAt || null,
        todayStats: {
          tasksCompleted,
          tasksFailed,
          tasksEscalated,
          avgDurationMs,
          tokenCostUsd: Math.round(tokenCostUsd * 10000) / 10000,
        },
      },
    };
  }

  // ─── Enable / Pause ─────────────────────────────────────────────────

  async enableAgent(tenantId: string, agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true },
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

    const updated = await this.prisma.agentConfig.update({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      data: { isEnabled: true },
      include: {
        agentDefinition: {
          select: { agentId: true, name: true },
        },
      },
    });

    // Publish agent activated and status changed events via Kafka
    await this.kafkaProducer.emit<AgentActivatedPayload>(TOPICS.AGENT_ACTIVATED, {
      tenantId,
      source: 'agent-registry',
      payload: {
        tenantId,
        agentId,
        agentConfigId: updated.id,
        integrationIds: updated.integrationIds ?? [],
        policyVersion: updated.configVersion ?? 1,
      },
    });

    await this.kafkaProducer.emit<AgentStatusChangedPayload>(TOPICS.AGENT_STATUS_CHANGED, {
      tenantId,
      source: 'agent-registry',
      payload: {
        tenantId,
        agentId,
        instanceId: 'default',
        previousStatus: 'PAUSED',
        newStatus: 'ACTIVE',
        currentTaskId: null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'AGENT_ENABLED',
      entityType: 'AGENT_CONFIG',
      entityId: updated.id,
      before: { isEnabled: false },
      after: { agentId, isEnabled: true },
    });

    return {
      success: true,
      data: {
        agentId: updated.agentDefinition.agentId,
        name: updated.agentDefinition.name,
        isEnabled: updated.isEnabled,
        status: 'ACTIVE',
      },
    };
  }

  async pauseAgent(tenantId: string, agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true },
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

    const updated = await this.prisma.agentConfig.update({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      data: { isEnabled: false },
      include: {
        agentDefinition: {
          select: { agentId: true, name: true },
        },
      },
    });

    // Publish agent status changed event via Kafka
    await this.kafkaProducer.emit<AgentStatusChangedPayload>(TOPICS.AGENT_STATUS_CHANGED, {
      tenantId,
      source: 'agent-registry',
      payload: {
        tenantId,
        agentId,
        instanceId: 'default',
        previousStatus: 'ACTIVE',
        newStatus: 'PAUSED',
        currentTaskId: null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'AGENT_PAUSED',
      entityType: 'AGENT_CONFIG',
      entityId: updated.id,
      before: { isEnabled: true },
      after: { agentId, isEnabled: false },
    });

    return {
      success: true,
      data: {
        agentId: updated.agentDefinition.agentId,
        name: updated.agentDefinition.name,
        isEnabled: updated.isEnabled,
        status: 'PAUSED',
      },
    };
  }
}
