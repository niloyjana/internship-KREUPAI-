import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { AuditService, TOPICS, BaseEvent, HumanTaskCreatedPayload } from '@adwp/kafka';

@Controller()
export class HumanTasksConsumer {
  private readonly logger = new Logger(HumanTasksConsumer.name);

  constructor(private readonly audit: AuditService) {}

  // ----------------------------------------------------------------
  // human.task.created — audit trail
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.HUMAN_TASK_CREATED)
  async handleHumanTaskCreated(
    @Payload() event: BaseEvent<HumanTaskCreatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Human task created: ` +
        `taskId=${event.payload.taskId}, ` +
        `assignedTo=${event.payload.assignedToUserId ?? 'unassigned'}`,
    );

    await this.audit.publishAudit({
      tenantId: event.tenantId,
      actorType: 'SYSTEM',
      actorId: 'workflow-service',
      action: 'HUMAN_TASK_CREATED',
      entityType: 'HUMAN_TASK',
      entityId: event.payload.taskId,
      after: {
        executionId: event.payload.executionId,
        stepId: event.payload.stepId,
        title: event.payload.title,
        assignedToUserId: event.payload.assignedToUserId,
        priority: event.payload.priority,
      },
    });
  }
}
