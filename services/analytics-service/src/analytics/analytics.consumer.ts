import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import {
  TOPICS,
  BaseEvent,
  WorkflowExecutionCompletedPayload,
  WorkflowExecutionFailedPayload,
  WorkflowExecutionStartedPayload,
  WorkflowStepCompletedPayload,
  EscalationCreatedPayload,
  BillingUsageRecordedPayload,
  TenantProvisionedPayload,
  AgentSubscribedPayload,
  AgentStatusChangedPayload,
  HumanTaskCreatedPayload,
  HumanTaskResolvedPayload,
  IntegrationConnectedPayload,
  NotificationDeliveredPayload,
} from '@adwp/kafka';

@Controller()
export class AnalyticsConsumer {
  private readonly logger = new Logger(AnalyticsConsumer.name);

  // ----------------------------------------------------------------
  // workflow.execution.completed
  // Stub — will record UsageMetric in the future
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.WORKFLOW_EXECUTION_COMPLETED)
  async handleWorkflowCompleted(
    @Payload() event: BaseEvent<WorkflowExecutionCompletedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Workflow execution completed: ` +
        `executionId=${event.payload.executionId}, ` +
        `agentId=${event.payload.agentId}, ` +
        `durationMs=${event.payload.durationMs}, ` +
        `tokenUsed=${event.payload.tokenUsed}, ` +
        `costUsd=${event.payload.costUsd}`,
    );

    // TODO: persist to UsageMetric table
  }

  // ----------------------------------------------------------------
  // workflow.execution.failed
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.WORKFLOW_EXECUTION_FAILED)
  async handleWorkflowFailed(
    @Payload() event: BaseEvent<WorkflowExecutionFailedPayload>,
  ): Promise<void> {
    this.logger.warn(
      `[${event.tenantId}] Workflow execution failed: ` +
        `executionId=${event.payload.executionId}, ` +
        `agentId=${event.payload.agentId}, ` +
        `failedAtStepId=${event.payload.failedAtStepId}, ` +
        `failureReason=${event.payload.failureReason}`,
    );

    // TODO: persist failure metric
  }

  // ----------------------------------------------------------------
  // escalation.created
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.ESCALATION_CREATED)
  async handleEscalationCreated(
    @Payload() event: BaseEvent<EscalationCreatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Escalation created: ` +
        `escalationId=${event.payload.escalationId}, ` +
        `severity=${event.payload.severity}, ` +
        `agentId=${event.payload.agentId}`,
    );

    // TODO: persist escalation metric
  }

  // ----------------------------------------------------------------
  // billing.usage.recorded
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.BILLING_USAGE_RECORDED)
  async handleBillingUsageRecorded(
    @Payload() event: BaseEvent<BillingUsageRecordedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Billing usage recorded: ` +
        `agentId=${event.payload.agentId}, ` +
        `executionId=${event.payload.executionId}, ` +
        `costUsd=${event.payload.costUsd}`,
    );

    // TODO: aggregate into cost dashboard
  }

  // ----------------------------------------------------------------
  // tenant.provisioned
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.TENANT_PROVISIONED)
  async handleTenantProvisioned(
    @Payload() event: BaseEvent<TenantProvisionedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Tenant provisioned: ` +
        `slug=${event.payload.slug}, ` +
        `plan=${event.payload.plan}`,
    );
  }

  // ----------------------------------------------------------------
  // agent.subscribed
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.AGENT_SUBSCRIBED)
  async handleAgentSubscribed(@Payload() event: BaseEvent<AgentSubscribedPayload>): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Agent subscribed: ` +
        `agentId=${event.payload.agentId}, ` +
        `plan=${event.payload.plan}`,
    );
  }

  // ----------------------------------------------------------------
  // agent.status.changed
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
  }

  // ----------------------------------------------------------------
  // workflow.execution.started
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.WORKFLOW_EXECUTION_STARTED)
  async handleWorkflowStarted(
    @Payload() event: BaseEvent<WorkflowExecutionStartedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Workflow started: ` +
        `executionId=${event.payload.executionId}, ` +
        `agentId=${event.payload.agentId}`,
    );
  }

  // ----------------------------------------------------------------
  // workflow.step.completed
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.WORKFLOW_STEP_COMPLETED)
  async handleWorkflowStepCompleted(
    @Payload() event: BaseEvent<WorkflowStepCompletedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Step completed: ` +
        `executionId=${event.payload.executionId}, ` +
        `stepId=${event.payload.stepId}, ` +
        `status=${event.payload.status}`,
    );
  }

  // ----------------------------------------------------------------
  // human.task.created
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.HUMAN_TASK_CREATED)
  async handleHumanTaskCreated(
    @Payload() event: BaseEvent<HumanTaskCreatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Human task created: ` +
        `taskId=${event.payload.taskId}, ` +
        `priority=${event.payload.priority}`,
    );
  }

  // ----------------------------------------------------------------
  // human.task.resolved
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.HUMAN_TASK_RESOLVED)
  async handleHumanTaskResolved(
    @Payload() event: BaseEvent<HumanTaskResolvedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Human task resolved: ` +
        `taskId=${event.payload.taskId}, ` +
        `decision=${event.payload.decision}`,
    );
  }

  // ----------------------------------------------------------------
  // integration.connected
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.INTEGRATION_CONNECTED)
  async handleIntegrationConnected(
    @Payload() event: BaseEvent<IntegrationConnectedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Integration connected: ` +
        `connectionId=${event.payload.connectionId}, ` +
        `provider=${event.payload.provider}`,
    );
  }

  // ----------------------------------------------------------------
  // notification.delivered
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.NOTIFICATION_DELIVERED)
  async handleNotificationDelivered(
    @Payload() event: BaseEvent<NotificationDeliveredPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Notification delivered: ` +
        `notificationId=${event.payload.notificationId}, ` +
        `channel=${event.payload.channel}, ` +
        `status=${event.payload.status}`,
    );
  }
}
