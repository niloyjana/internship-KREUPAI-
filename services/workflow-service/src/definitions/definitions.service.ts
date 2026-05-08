import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { CreateDefinitionDto } from './dto/create-definition.dto';

@Injectable()
export class DefinitionsService {
  constructor(private readonly prisma: PrismaService) {}

  async listDefinitions(tenantId: string, agentId?: string) {
    const where: Prisma.WorkflowDefinitionWhereInput = { tenantId };
    if (agentId) {
      where.agentId = agentId;
    }

    const definitions = await this.prisma.workflowDefinition.findMany({
      where,
      orderBy: { createdAt: 'desc' },
    });

    return definitions;
  }

  async createDefinition(tenantId: string, userId: string, dto: CreateDefinitionDto) {
    const definition = await this.prisma.workflowDefinition.create({
      data: {
        tenantId,
        agentId: dto.agentId,
        name: dto.name,
        description: dto.description,
        triggerType: dto.triggerType,
        triggerConfig: dto.triggerConfig as Prisma.InputJsonValue,
        stepsJson: dto.stepsJson as Prisma.InputJsonValue,
        createdByUserId: userId,
      },
    });

    return definition;
  }

  async getDefinition(tenantId: string, definitionId: string) {
    const definition = await this.prisma.workflowDefinition.findFirst({
      where: { id: definitionId, tenantId },
    });

    if (!definition) {
      throw new NotFoundException('DEFINITION_NOT_FOUND');
    }

    return definition;
  }
}
