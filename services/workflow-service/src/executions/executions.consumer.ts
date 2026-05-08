import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import {
  AuditService,
  TOPICS,
  BaseEvent,
  WorkflowExecutionCompletedPayload,
  WorkflowExecutionFailedPayload,
} from '@adwp/kafka';

@Controller()
export class ExecutionsConsumer {
  private readonly logger = new Logger(ExecutionsConsumer.name);

  constructor(private readonly audit: AuditService) {}

  // ----------------------------------------------------------------
  // workflow.execution.completed — audit trail
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.WORKFLOW_EXECUTION_COMPLETED)
  async handleWorkflowExecutionCompleted(
    @Payload() event: BaseEvent<WorkflowExecutionCompletedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Workflow execution completed: ` +
        `executionId=${event.payload.executionId}, ` +
        `status=${event.payload.status}`,
    );

    await this.audit.publishAudit({
      tenantId: event.tenantId,
      actorType: 'SYSTEM',
      actorId: event.payload.agentId,
      action: 'WORKFLOW_EXECUTION_COMPLETED',
      entityType: 'WORKFLOW_EXECUTION',
      entityId: event.payload.executionId,
      after: {
        agentId: event.payload.agentId,
        status: event.payload.status,
        stepCount: event.payload.stepCount,
        durationMs: event.payload.durationMs,
        tokenUsed: event.payload.tokenUsed,
        costUsd: event.payload.costUsd,
      },
    });
  }

  // ----------------------------------------------------------------
  // workflow.execution.failed — audit trail
  // ----------------------------------------------------------------
  @EventPattern(TOPICS.WORKFLOW_EXECUTION_FAILED)
  async handleWorkflowExecutionFailed(
    @Payload() event: BaseEvent<WorkflowExecutionFailedPayload>,
  ): Promise<void> {
    this.logger.warn(
      `[${event.tenantId}] Workflow execution failed: ` +
        `executionId=${event.payload.executionId}, ` +
        `failureReason=${event.payload.failureReason}`,
    );

    await this.audit.publishAudit({
      tenantId: event.tenantId,
      actorType: 'SYSTEM',
      actorId: event.payload.agentId,
      action: 'WORKFLOW_EXECUTION_FAILED',
      entityType: 'WORKFLOW_EXECUTION',
      entityId: event.payload.executionId,
      after: {
        agentId: event.payload.agentId,
        failedAtStepId: event.payload.failedAtStepId,
        failureReason: event.payload.failureReason,
      },
    });
  }
}
