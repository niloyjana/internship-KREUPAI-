import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma, EscalationStatus, EscalationSeverity } from '@prisma/client';
import { KafkaProducerService, AuditService, TOPICS, EscalationCreatedPayload } from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { ListEscalationsQueryDto } from './dto/list-escalations-query.dto';
import { UpdateEscalationDto } from './dto/update-escalation.dto';

@Injectable()
export class EscalationsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  async listEscalations(tenantId: string, query: ListEscalationsQueryDto) {
    const { status, severity, agentId } = query;
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.EscalationTicketWhereInput = { tenantId };

    if (status) {
      where.status = status as EscalationStatus;
    }
    if (severity) {
      where.severity = severity as EscalationSeverity;
    }
    if (agentId) {
      where.agentId = agentId;
    }

    const [escalations, total] = await Promise.all([
      this.prisma.escalationTicket.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.escalationTicket.count({ where }),
    ]);

    return {
      items: escalations,
      meta: {
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getEscalation(tenantId: string, escalationId: string) {
    const escalation = await this.prisma.escalationTicket.findFirst({
      where: { id: escalationId, tenantId },
    });

    if (!escalation) {
      throw new NotFoundException('ESCALATION_NOT_FOUND');
    }

    return escalation;
  }

  async updateEscalation(
    tenantId: string,
    escalationId: string,
    userId: string,
    dto: UpdateEscalationDto,
  ) {
    const escalation = await this.prisma.escalationTicket.findFirst({
      where: { id: escalationId, tenantId },
    });

    if (!escalation) {
      throw new NotFoundException('ESCALATION_NOT_FOUND');
    }

    const updateData: Prisma.EscalationTicketUpdateInput = {};

    if (dto.assignedToUserId !== undefined) {
      updateData.assignedToId = dto.assignedToUserId;
    }
    if (dto.status !== undefined) {
      updateData.status = dto.status as EscalationStatus;
    }
    if (dto.resolutionNote !== undefined) {
      updateData.resolutionNote = dto.resolutionNote;
    }

    // If status is being set to RESOLVED, set resolvedAt and resolvedById
    if (dto.status === 'RESOLVED') {
      updateData.resolvedAt = new Date();
      updateData.resolvedById = userId;
    }

    const updated = await this.prisma.escalationTicket.update({
      where: { id: escalationId },
      data: updateData,
    });

    // Emit escalation created/status-changed event
    if (dto.status !== undefined) {
      await this.kafkaProducer.emit<EscalationCreatedPayload>(TOPICS.ESCALATION_CREATED, {
        tenantId,
        source: 'workflow-service',
        payload: {
          escalationId: updated.id,
          executionId: updated.executionId ?? null,
          agentId: updated.agentId,
          severity: updated.severity,
          reason: updated.reason,
          recommendedAction: updated.resolutionNote ?? null,
          slaDeadlineAt: updated.slaDeadlineAt?.toISOString() ?? new Date().toISOString(),
          assignedToUserId: updated.assignedToId ?? null,
          assignedTeam: null,
          contextSummary: `Escalation ${updated.severity}: ${updated.reason}`,
        },
      });
    }

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'ESCALATION_UPDATED',
      entityType: 'ESCALATION_TICKET',
      entityId: escalationId,
      before: { status: escalation.status },
      after: { status: updated.status, assignedToId: updated.assignedToId },
    });

    return updated;
  }
}
