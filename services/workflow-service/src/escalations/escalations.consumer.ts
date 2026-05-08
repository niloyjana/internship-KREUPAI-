import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { AuditService, TOPICS, BaseEvent, EscalationCreatedPayload } from '@adwp/kafka';

@Controller()
export class EscalationsConsumer {
  private readonly logger = new Logger(EscalationsConsumer.name);

  constructor(private readonly audit: AuditService) {}

  // ----------------------------------------------------------------
  // escalation.created — audit trail
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.ESCALATION_CREATED)
  async handleEscalationCreated(
    @Payload() event: BaseEvent<EscalationCreatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Escalation created: ` +
        `escalationId=${event.payload.escalationId}, ` +
        `severity=${event.payload.severity}`,
    );

    await this.audit.publishAudit({
      tenantId: event.tenantId,
      actorType: 'SYSTEM',
      actorId: event.payload.agentId,
      action: 'ESCALATION_CREATED',
      entityType: 'ESCALATION_TICKET',
      entityId: event.payload.escalationId,
      after: {
        executionId: event.payload.executionId,
        agentId: event.payload.agentId,
        severity: event.payload.severity,
        reason: event.payload.reason,
        assignedToUserId: event.payload.assignedToUserId,
      },
    });
  }
}
