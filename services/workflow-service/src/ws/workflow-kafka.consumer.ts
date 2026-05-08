import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { TOPICS, BaseEvent, EscalationSlaBreachedPayload } from '@adwp/kafka';

@Controller()
export class WorkflowKafkaConsumer {
  private readonly logger = new Logger(WorkflowKafkaConsumer.name);

  @EventPattern(TOPICS.ESCALATION_SLA_BREACHED)
  async handleEscalationSlaBreached(
    @Payload() event: BaseEvent<EscalationSlaBreachedPayload>,
  ): Promise<void> {
    this.logger.warn(
      `[${event.tenantId}] Escalation SLA breached: ` +
        `escalationId=${event.payload.escalationId}, ` +
        `minutesOverdue=${event.payload.minutesOverdue}`,
    );
  }
}
