import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import {
  TOPICS,
  BaseEvent,
  WorkflowExecutionCompletedPayload,
  WorkflowExecutionFailedPayload,
  HumanTaskCreatedPayload,
  HumanTaskResolvedPayload,
  EscalationCreatedPayload,
  AgentStatusChangedPayload,
} from '@adwp/kafka';
import { EventsGateway } from './events.gateway';

/**
 * Kafka consumer that forwards events to WebSocket clients via EventsGateway.
 *
 * Maps Kafka events to P3 spec WebSocket event types:
 *   - agent.status.changed
 *   - escalation.created
 *   - workflow.execution.completed
 *   - human.task.assigned
 *   - cost.alert
 */
@Controller()
export class WsKafkaConsumer {
  private readonly logger = new Logger(WsKafkaConsumer.name);

  constructor(private readonly gateway: EventsGateway) {}

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: agent.status.changed                                      */
  /* ------------------------------------------------------------------ */

  @EventPattern(TOPICS.AGENT_STATUS_CHANGED)
  handleAgentStatusChanged(@Payload() message: BaseEvent<AgentStatusChangedPayload>) {
    const p = message.payload;
    this.logger.debug(`Agent status changed: ${p.agentId} → ${p.newStatus}`);

    this.gateway.emitAgentStatusChanged(message.tenantId, {
      tenantId: message.tenantId,
      agentId: p.agentId,
      status: p.newStatus,
      timestamp: new Date().toISOString(),
    });
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: escalation.created                                        */
  /* ------------------------------------------------------------------ */

  @EventPattern(TOPICS.ESCALATION_CREATED)
  handleEscalationCreated(@Payload() message: BaseEvent<EscalationCreatedPayload>) {
    const p = message.payload;
    this.logger.debug(`Escalation created: ${p.escalationId}`);

    this.gateway.emitEscalationCreated(message.tenantId, {
      escalationId: p.escalationId,
      agentId: p.agentId,
      severity: p.severity,
      title: p.reason,
      slaDeadlineAt: p.slaDeadlineAt ?? new Date().toISOString(),
    });
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: workflow.execution.completed                              */
  /* ------------------------------------------------------------------ */

  @EventPattern(TOPICS.WORKFLOW_EXECUTION_COMPLETED)
  handleExecutionCompleted(@Payload() message: BaseEvent<WorkflowExecutionCompletedPayload>) {
    const p = message.payload;
    this.logger.debug(`Execution completed: ${p.executionId} (${p.status})`);

    this.gateway.emitWorkflowExecutionCompleted(message.tenantId, {
      executionId: p.executionId,
      agentId: p.agentId,
      status: p.status,
      summary: p.outcome ?? `Completed with ${p.stepCount} steps`,
    });

    this.gateway.emitDashboardMetrics(message.tenantId, {
      hint: 'execution_completed',
      executionId: p.executionId,
      agentId: p.agentId,
      status: p.status,
      timestamp: new Date().toISOString(),
    });
  }

  @EventPattern(TOPICS.WORKFLOW_EXECUTION_FAILED)
  handleExecutionFailed(@Payload() message: BaseEvent<WorkflowExecutionFailedPayload>) {
    const p = message.payload;
    this.logger.debug(`Execution failed: ${p.executionId}`);

    this.gateway.emitWorkflowExecutionCompleted(message.tenantId, {
      executionId: p.executionId,
      agentId: p.agentId,
      status: 'FAILED',
      summary: p.failureReason,
    });

    this.gateway.emitDashboardMetrics(message.tenantId, {
      hint: 'execution_failed',
      executionId: p.executionId,
      agentId: p.agentId,
      timestamp: new Date().toISOString(),
    });
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: human.task.assigned                                       */
  /* ------------------------------------------------------------------ */

  @EventPattern(TOPICS.HUMAN_TASK_CREATED)
  handleTaskCreated(@Payload() message: BaseEvent<HumanTaskCreatedPayload>) {
    const p = message.payload;
    this.logger.debug(`Human task created: ${p.taskId}`);

    this.gateway.emitHumanTaskAssigned(message.tenantId, {
      taskId: p.taskId,
      title: p.title,
      priority: p.priority,
      dueAt: p.dueAt ?? new Date().toISOString(),
    });

    this.gateway.emitDashboardMetrics(message.tenantId, {
      hint: 'task_created',
      taskId: p.taskId,
      priority: p.priority,
      timestamp: new Date().toISOString(),
    });
  }

  @EventPattern(TOPICS.HUMAN_TASK_RESOLVED)
  handleTaskResolved(@Payload() message: BaseEvent<HumanTaskResolvedPayload>) {
    const p = message.payload;
    this.logger.debug(`Human task resolved: ${p.taskId}`);

    this.gateway.emitDashboardMetrics(message.tenantId, {
      hint: 'task_resolved',
      taskId: p.taskId,
      decision: p.decision,
      timestamp: new Date().toISOString(),
    });
  }
}
