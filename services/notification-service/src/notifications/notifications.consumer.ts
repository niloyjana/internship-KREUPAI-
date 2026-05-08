import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import {
  TOPICS,
  BaseEvent,
  NotificationRequestedPayload,
  EscalationCreatedPayload,
  HumanTaskCreatedPayload,
  BillingPaymentFailedPayload,
  AgentStatusChangedPayload,
} from '@adwp/kafka';
import { NotificationsService } from './notifications.service';

@Controller()
export class NotificationsConsumer {
  private readonly logger = new Logger(NotificationsConsumer.name);

  constructor(private readonly notificationsService: NotificationsService) {}

  // ----------------------------------------------------------------
  // notification.requested
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.NOTIFICATION_REQUESTED)
  async handleNotificationRequested(
    @Payload() event: BaseEvent<NotificationRequestedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Notification requested: ` +
        `channels=${event.payload.channels?.join(', ')}, ` +
        `eventType=${event.payload.eventType}`,
    );

    await this.notificationsService.sendNotification(
      event.tenantId,
      event.payload.recipientUserId ?? 'system',
      event.payload.eventType,
      event.payload.subject,
      { body: event.payload.body, ...event.payload.metadata },
    );
  }

  // ----------------------------------------------------------------
  // escalation.created — trigger escalation notification
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.ESCALATION_CREATED)
  async handleEscalationCreated(
    @Payload() event: BaseEvent<EscalationCreatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Escalation created — sending notification: ` +
        `escalationId=${event.payload.escalationId}, ` +
        `severity=${event.payload.severity}`,
    );

    const assignee = event.payload.assignedToUserId ?? 'system';
    await this.notificationsService.sendNotification(
      event.tenantId,
      assignee,
      'escalation.created',
      `Escalation [${event.payload.severity}]: ${event.payload.reason}`,
      {
        escalationId: event.payload.escalationId,
        executionId: event.payload.executionId,
        agentId: event.payload.agentId,
        severity: event.payload.severity,
        reason: event.payload.reason,
      },
    );
  }

  // ----------------------------------------------------------------
  // human.task.created — notify the assignee
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.HUMAN_TASK_CREATED)
  async handleHumanTaskCreated(
    @Payload() event: BaseEvent<HumanTaskCreatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Human task created — notifying assignee: ` +
        `taskId=${event.payload.taskId}, ` +
        `assignedToUserId=${event.payload.assignedToUserId ?? 'unassigned'}`,
    );

    const assignee = event.payload.assignedToUserId ?? 'system';
    await this.notificationsService.sendNotification(
      event.tenantId,
      assignee,
      'human.task.created',
      `New task assigned: ${event.payload.title} [${event.payload.priority}]`,
      {
        taskId: event.payload.taskId,
        executionId: event.payload.executionId,
        stepId: event.payload.stepId,
        title: event.payload.title,
        priority: event.payload.priority,
      },
    );
  }

  // ----------------------------------------------------------------
  // billing.payment.failed
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.BILLING_PAYMENT_FAILED)
  async handleBillingPaymentFailed(
    @Payload() event: BaseEvent<BillingPaymentFailedPayload>,
  ): Promise<void> {
    this.logger.warn(
      `[${event.tenantId}] Billing payment failed: ` +
        `invoiceId=${event.payload.invoiceId}, ` +
        `amountUsd=${event.payload.amountUsd}, ` +
        `attemptCount=${event.payload.attemptCount}`,
    );

    // Notify tenant admin about payment failure
    await this.notificationsService.sendNotification(
      event.tenantId,
      'system', // resolved to tenant admin in production
      'billing.payment.failed',
      `Payment failed for invoice ${event.payload.invoiceId} ($${event.payload.amountUsd})`,
      {
        invoiceId: event.payload.invoiceId,
        amountUsd: event.payload.amountUsd,
        failureReason: event.payload.failureReason,
        attemptCount: event.payload.attemptCount,
      },
    );
  }

  // ----------------------------------------------------------------
  // agent.status.changed — notify relevant parties
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.AGENT_STATUS_CHANGED)
  async handleAgentStatusChanged(
    @Payload() event: BaseEvent<AgentStatusChangedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Agent status changed: ` +
        `agentId=${event.payload.agentId}, ` +
        `${event.payload.previousStatus} → ${event.payload.newStatus}`,
    );

    await this.notificationsService.sendNotification(
      event.tenantId,
      'system',
      'agent.status.changed',
      `Agent ${event.payload.agentId} status: ${event.payload.previousStatus} → ${event.payload.newStatus}`,
      {
        agentId: event.payload.agentId,
        previousStatus: event.payload.previousStatus,
        newStatus: event.payload.newStatus,
      },
    );
  }
}
