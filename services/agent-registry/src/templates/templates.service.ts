import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { KafkaProducerService, AuditService, TOPICS, AgentStatusChangedPayload } from '@adwp/kafka';
import { CreateTemplateDto } from './dto/create-template.dto';
import { Prisma } from '@prisma/client';

@Injectable()
export class TemplatesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ------------------------------------------------------------------
  // GET /v1/templates — list config templates
  // ------------------------------------------------------------------
  async listTemplates() {
    const templates = await this.prisma.configTemplate.findMany({
      orderBy: { name: 'asc' },
    });

    return templates.map((t) => ({
      id: t.id,
      name: t.name,
      description: t.description,
      category: t.category,
      configJson: t.configJson,
      createdAt: t.createdAt.toISOString(),
      updatedAt: t.updatedAt.toISOString(),
    }));
  }

  // ------------------------------------------------------------------
  // GET /v1/templates/:templateId — get template details
  // ------------------------------------------------------------------
  async getTemplateDetail(templateId: string) {
    const template = await this.prisma.configTemplate.findUnique({
      where: { id: templateId },
    });

    if (!template) {
      throw new NotFoundException('TEMPLATE_NOT_FOUND');
    }

    return {
      id: template.id,
      name: template.name,
      description: template.description,
      category: template.category,
      configJson: template.configJson,
      createdBy: template.createdBy,
      createdAt: template.createdAt.toISOString(),
      updatedAt: template.updatedAt.toISOString(),
    };
  }

  // ------------------------------------------------------------------
  // POST /v1/templates — create template (PLATFORM_ADMIN only)
  // ------------------------------------------------------------------
  async createTemplate(dto: CreateTemplateDto, userId: string) {
    if (typeof dto.configJson !== 'object' || dto.configJson === null) {
      throw new BadRequestException('configJson must be a valid JSON object');
    }

    const template = await this.prisma.configTemplate.create({
      data: {
        name: dto.name,
        description: dto.description ?? null,
        category: dto.category ?? null,
        configJson: dto.configJson as unknown as Prisma.InputJsonValue,
        createdBy: userId,
      },
    });

    await this.audit.publishAudit({
      tenantId: 'PLATFORM',
      actorType: 'USER',
      actorId: userId,
      action: 'TEMPLATE_CREATED',
      entityType: 'CONFIG_TEMPLATE',
      entityId: template.id,
      after: {
        name: template.name,
        category: template.category,
      },
    });

    return {
      id: template.id,
      name: template.name,
      description: template.description,
      category: template.category,
      configJson: template.configJson,
      createdBy: template.createdBy,
      createdAt: template.createdAt.toISOString(),
      updatedAt: template.updatedAt.toISOString(),
    };
  }

  // ------------------------------------------------------------------
  // POST /v1/agents/:agentId/apply-template/:templateId — apply template
  // ------------------------------------------------------------------
  async applyTemplate(tenantId: string, agentId: string, templateId: string, userId: string) {
    // 1. Validate agent definition exists
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, name: true },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    // 2. Validate template exists
    const template = await this.prisma.configTemplate.findUnique({
      where: { id: templateId },
    });

    if (!template) {
      throw new NotFoundException('TEMPLATE_NOT_FOUND');
    }

    // 3. Find existing config
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

    // 4. Extract policy and display name from template config
    const templateConfig =
      typeof template.configJson === 'object' && template.configJson !== null
        ? (template.configJson as Record<string, unknown>)
        : {};

    const updateData: Record<string, unknown> = {
      lastConfiguredAt: new Date(),
      configuredByUserId: userId,
      configVersion: { increment: 1 },
    };

    if (templateConfig.policyJson && typeof templateConfig.policyJson === 'object') {
      updateData.policyJson = templateConfig.policyJson;
    }

    if (typeof templateConfig.displayName === 'string') {
      updateData.displayName = templateConfig.displayName;
    }

    if (Array.isArray(templateConfig.integrationIds)) {
      updateData.integrationIds = templateConfig.integrationIds;
    }

    // 5. Apply template to agent config
    const updated = await this.prisma.agentConfig.update({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      data: updateData as any,
      include: {
        agentDefinition: {
          select: { agentId: true, name: true },
        },
      },
    });

    // 6. Save config history snapshot
    await this.prisma.agentConfigHistory.create({
      data: {
        agentConfigId: existingConfig.id,
        tenantId,
        version: updated.configVersion,
        displayName: updated.displayName,
        policyJson: updated.policyJson ?? {},
        changedBy: userId,
        changeReason: `Applied template: ${template.name}`,
        snapshot: {
          displayName: updated.displayName,
          policyJson: updated.policyJson,
          configVersion: updated.configVersion,
          templateId: template.id,
          templateName: template.name,
        },
      },
    });

    // 7. Publish event via Kafka
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
      action: 'TEMPLATE_APPLIED',
      entityType: 'AGENT_CONFIG',
      entityId: updated.id,
      before: { configVersion: existingConfig.configVersion },
      after: {
        agentId,
        templateId: template.id,
        templateName: template.name,
        configVersion: updated.configVersion,
      },
    });

    return {
      agentId: updated.agentDefinition.agentId,
      agentName: updated.agentDefinition.name,
      templateId: template.id,
      templateName: template.name,
      configVersion: updated.configVersion,
      policyJson: updated.policyJson,
      displayName: updated.displayName,
      integrationIds: updated.integrationIds,
      lastConfiguredAt: updated.lastConfiguredAt,
      configuredByUserId: updated.configuredByUserId,
    };
  }
}
