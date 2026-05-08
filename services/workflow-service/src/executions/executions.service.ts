import {
  Injectable,
  Logger,
  NotFoundException,
  ConflictException,
  BadRequestException,
} from '@nestjs/common';
import { Prisma, WorkflowStatus } from '@prisma/client';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  WorkflowExecutionStartedPayload,
  WorkflowExecutionCompletedPayload,
  WorkflowExecutionFailedPayload,
} from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { AiRuntimeService } from '../ai-runtime/ai-runtime.service';
import { ListExecutionsQueryDto } from './dto/list-executions-query.dto';

@Injectable()
export class ExecutionsService {
  private readonly logger = new Logger(ExecutionsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
    private readonly aiRuntime: AiRuntimeService,
  ) {}

  async listExecutions(tenantId: string, query: ListExecutionsQueryDto) {
    const { agentId, status, from, to } = query;
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.WorkflowExecutionWhereInput = { tenantId };

    if (agentId) {
      where.agentId = agentId;
    }
    if (status) {
      where.status = status as WorkflowStatus;
    }
    if (from || to) {
      where.createdAt = {};
      if (from) {
        where.createdAt.gte = new Date(from);
      }
      if (to) {
        where.createdAt.lte = new Date(to);
      }
    }

    const [executions, total] = await Promise.all([
      this.prisma.workflowExecution.findMany({
        where,
        include: {
          steps: {
            orderBy: { sequence: 'asc' },
            select: { id: true, stepKey: true, status: true, sequence: true },
          },
        },
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.workflowExecution.count({ where }),
    ]);

    const data = executions.map((exec) => {
      const stepCount = exec.steps.length;
      const completedSteps = exec.steps.filter((s) => s.status === 'COMPLETED').length;

      // Current step: latest non-PENDING step by sequence
      const nonPendingSteps = exec.steps.filter((s) => s.status !== 'PENDING');
      const currentStep =
        nonPendingSteps.length > 0 ? nonPendingSteps[nonPendingSteps.length - 1] : null;

      return {
        id: exec.id,
        definitionId: exec.definitionId,
        agentId: exec.agentId,
        status: exec.status,
        triggerSource: exec.triggerSource,
        currentStep: currentStep
          ? { stepKey: currentStep.stepKey, status: currentStep.status }
          : null,
        startedAt: exec.startedAt,
        durationMs: exec.durationMs,
        stepCount,
        completedSteps,
        createdAt: exec.createdAt,
      };
    });

    return {
      items: data,
      meta: {
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getExecution(tenantId: string, executionId: string) {
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
      include: {
        steps: {
          orderBy: { sequence: 'asc' },
        },
      },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    // Emit execution started event when a RUNNING execution is observed
    if (execution.status === WorkflowStatus.RUNNING) {
      this.kafkaProducer
        .emit<WorkflowExecutionStartedPayload>(TOPICS.WORKFLOW_EXECUTION_STARTED, {
          tenantId,
          source: 'workflow-service',
          payload: {
            executionId: execution.id,
            definitionId: execution.definitionId,
            agentId: execution.agentId,
            triggerSource: execution.triggerSource ?? 'unknown',
            triggerPayload: null,
            estimatedSteps: 0,
          },
        })
        .catch((err) =>
          this.logger.error(`Failed to emit WORKFLOW_EXECUTION_STARTED: ${err.message}`),
        );

      this.audit
        .publishAudit({
          tenantId,
          actorType: 'SYSTEM',
          actorId: execution.agentId,
          action: 'WORKFLOW_EXECUTION_STARTED',
          entityType: 'WORKFLOW_EXECUTION',
          entityId: execution.id,
          after: {
            definitionId: execution.definitionId,
            agentId: execution.agentId,
            triggerSource: execution.triggerSource,
            status: execution.status,
          },
        })
        .catch((err) =>
          this.logger.error(
            `Failed to publish audit WORKFLOW_EXECUTION_STARTED: ${err instanceof Error ? err.message : err}`,
          ),
        );
    }

    return execution;
  }

  async getExecutionSteps(tenantId: string, executionId: string) {
    // Verify execution exists and belongs to tenant
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
      select: { id: true },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    const steps = await this.prisma.workflowStep.findMany({
      where: { executionId },
      orderBy: { sequence: 'asc' },
    });

    return steps;
  }

  async cancelExecution(tenantId: string, executionId: string) {
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    if (
      execution.status !== WorkflowStatus.PENDING &&
      execution.status !== WorkflowStatus.RUNNING
    ) {
      throw new ConflictException('EXECUTION_CANNOT_CANCEL');
    }

    const updated = await this.prisma.workflowExecution.update({
      where: { id: executionId },
      data: {
        status: WorkflowStatus.CANCELLED,
        completedAt: new Date(),
      },
    });

    // Emit workflow execution completed event (cancellation is a form of completion)
    await this.kafkaProducer.emit<WorkflowExecutionCompletedPayload>(
      TOPICS.WORKFLOW_EXECUTION_COMPLETED,
      {
        tenantId,
        source: 'workflow-service',
        payload: {
          executionId: updated.id,
          agentId: updated.agentId,
          status: 'CANCELLED',
          durationMs: updated.durationMs ?? 0,
          stepCount: 0,
          tokenUsed: 0,
          costUsd: 0,
          escalationTriggered: false,
          outcome: 'Execution cancelled by user',
        },
      },
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'EXECUTION_CANCELLED',
      entityType: 'WORKFLOW_EXECUTION',
      entityId: executionId,
      before: { status: execution.status },
      after: { status: 'CANCELLED' },
    });

    return updated;
  }

  // ── Partial Failure Recovery (P6 Section 7) ────────────────────────

  /**
   * Retry a specific failed step within an execution.
   * Generates an idempotency key to prevent duplicate processing.
   */
  async retryStep(tenantId: string, executionId: string, stepKey: string) {
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
      include: { steps: { orderBy: { sequence: 'asc' } } },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    const step = execution.steps.find((s) => s.stepKey === stepKey);
    if (!step) {
      throw new NotFoundException(`Step '${stepKey}' not found in execution`);
    }

    if (step.status !== 'FAILED') {
      throw new ConflictException(`Step '${stepKey}' is not in FAILED status`);
    }

    const newRetryCount = step.retryCount + 1;
    const idempotencyKey = `${executionId}:${stepKey}:${newRetryCount}`;

    // Update step status to RUNNING and increment retry count
    await this.prisma.workflowStep.update({
      where: { id: step.id },
      data: {
        status: 'RUNNING',
        retryCount: newRetryCount,
        failedAt: null,
        errorMessage: null,
        startedAt: new Date(),
      },
    });

    // Update execution status back to RUNNING if it was FAILED
    if (execution.status === WorkflowStatus.FAILED) {
      await this.prisma.workflowExecution.update({
        where: { id: executionId },
        data: { status: WorkflowStatus.RUNNING, completedAt: null },
      });
    }

    // Emit retry event for the AI runtime to re-execute
    await this.kafkaProducer.emit(TOPICS.WORKFLOW_EXECUTION_STARTED, {
      tenantId,
      source: 'workflow-service',
      payload: {
        executionId,
        definitionId: execution.definitionId,
        agentId: execution.agentId,
        triggerSource: 'retry',
        triggerPayload: {
          retryStepKey: stepKey,
          idempotencyKey,
          retryAttempt: newRetryCount,
        },
        estimatedSteps: 1,
      },
    });

    this.logger.log(
      `Step retry initiated: execution=${executionId} step=${stepKey} attempt=${newRetryCount} idempotencyKey=${idempotencyKey}`,
    );

    return {
      executionId,
      stepKey,
      retryCount: newRetryCount,
      idempotencyKey,
      status: 'retrying',
    };
  }

  /**
   * Resume execution from the last completed step.
   * Finds the last completed step and continues from the next one.
   */
  async resumeExecution(tenantId: string, executionId: string) {
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
      include: { steps: { orderBy: { sequence: 'asc' } } },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    if (execution.status !== WorkflowStatus.FAILED) {
      throw new ConflictException('Only FAILED executions can be resumed');
    }

    // Find last completed step
    const completedSteps = execution.steps.filter((s) => s.status === 'COMPLETED');
    const lastCompleted = completedSteps[completedSteps.length - 1] ?? null;
    const resumeFromSequence = lastCompleted ? lastCompleted.sequence + 1 : 0;

    // Reset all steps after the last completed one to PENDING
    const stepsToReset = execution.steps.filter((s) => s.sequence >= resumeFromSequence);
    for (const step of stepsToReset) {
      await this.prisma.workflowStep.update({
        where: { id: step.id },
        data: {
          status: 'PENDING',
          failedAt: null,
          errorMessage: null,
          startedAt: null,
          completedAt: null,
        },
      });
    }

    // Set execution back to RUNNING
    await this.prisma.workflowExecution.update({
      where: { id: executionId },
      data: { status: WorkflowStatus.RUNNING, completedAt: null },
    });

    // Emit resume event
    await this.kafkaProducer.emit(TOPICS.WORKFLOW_EXECUTION_STARTED, {
      tenantId,
      source: 'workflow-service',
      payload: {
        executionId,
        definitionId: execution.definitionId,
        agentId: execution.agentId,
        triggerSource: 'resume',
        triggerPayload: {
          resumeFromSequence,
          completedStepKeys: completedSteps.map((s) => s.stepKey),
        },
        estimatedSteps: stepsToReset.length,
      },
    });

    this.logger.log(
      `Execution resumed: id=${executionId} from_sequence=${resumeFromSequence} steps_remaining=${stepsToReset.length}`,
    );

    return {
      executionId,
      resumeFromSequence,
      stepsRemaining: stepsToReset.length,
      completedSteps: completedSteps.length,
      status: 'resumed',
    };
  }

  /**
   * Compensate completed steps in reverse order when an execution is aborted.
   * Emits compensation events for each completed step.
   */
  async compensateSteps(tenantId: string, executionId: string) {
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
      include: { steps: { orderBy: { sequence: 'desc' } } },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    const completedSteps = execution.steps.filter((s) => s.status === 'COMPLETED');

    if (completedSteps.length === 0) {
      return { executionId, compensatedSteps: 0, status: 'nothing_to_compensate' };
    }

    // Emit compensation events in reverse order (latest first)
    for (const step of completedSteps) {
      await this.kafkaProducer.emit('workflow.step.compensate', {
        tenantId,
        source: 'workflow-service',
        payload: {
          executionId,
          stepKey: step.stepKey,
          stepType: step.stepType,
          outputJson: step.outputJson,
          compensationReason: 'execution_abort',
        },
      });

      // Mark step as compensated
      await this.prisma.workflowStep.update({
        where: { id: step.id },
        data: { status: 'SKIPPED' },
      });
    }

    // Mark execution as compensated
    await this.prisma.workflowExecution.update({
      where: { id: executionId },
      data: { status: WorkflowStatus.CANCELLED, completedAt: new Date() },
    });

    this.logger.log(
      `Compensation completed: execution=${executionId} steps_compensated=${completedSteps.length}`,
    );

    return {
      executionId,
      compensatedSteps: completedSteps.length,
      compensatedStepKeys: completedSteps.map((s) => s.stepKey),
      status: 'compensated',
    };
  }

  async failExecution(
    tenantId: string,
    executionId: string,
    failedAtStepId: string,
    failureReason: string,
    isRetryable: boolean = false,
  ) {
    const execution = await this.prisma.workflowExecution.findFirst({
      where: { id: executionId, tenantId },
    });

    if (!execution) {
      throw new NotFoundException('EXECUTION_NOT_FOUND');
    }

    const updated = await this.prisma.workflowExecution.update({
      where: { id: executionId },
      data: {
        status: WorkflowStatus.FAILED,
        completedAt: new Date(),
      },
    });

    await this.kafkaProducer.emit<WorkflowExecutionFailedPayload>(
      TOPICS.WORKFLOW_EXECUTION_FAILED,
      {
        tenantId,
        source: 'workflow-service',
        payload: {
          executionId: updated.id,
          agentId: updated.agentId,
          failedAtStepId,
          failureReason,
          isRetryable,
          retryAttempt: 0,
          alertOpsTeam: !isRetryable,
        },
      },
    );

    return updated;
  }

  // ── AI Runtime Integration ─────────────────────────────────────────

  /**
   * Execute an agent task via the AI Runtime service.
   *
   * Creates a WorkflowExecution record, calls the AI Runtime,
   * updates the record with the result, and emits Kafka events.
   */
  async executeAgentTask(
    tenantId: string,
    agentId: string,
    taskPayload: Record<string, unknown>,
    options?: {
      definitionId?: string;
      triggerSource?: string;
      tenantConfig?: Record<string, unknown>;
      agentPolicy?: Record<string, unknown>;
    },
  ) {
    // ── Input validation ───────────────────────────────────────────
    if (!tenantId?.trim()) {
      throw new BadRequestException('MISSING_TENANT_ID');
    }
    if (!agentId?.trim()) {
      throw new BadRequestException('MISSING_AGENT_ID');
    }
    try {
      JSON.stringify(taskPayload);
    } catch {
      throw new BadRequestException('INVALID_TASK_PAYLOAD_JSON');
    }

    const startedAt = new Date();

    // 1. Create execution record
    const execution = await this.prisma.workflowExecution.create({
      data: {
        tenantId,
        agentId,
        definitionId: options?.definitionId || `adhoc-${agentId}`,
        status: WorkflowStatus.RUNNING,
        triggerSource: options?.triggerSource || 'api',
        startedAt,
        triggerPayload: taskPayload as Prisma.InputJsonValue,
      },
    });

    this.logger.log(`Execution created: id=${execution.id} agent=${agentId} tenant=${tenantId}`);

    // 2. Emit started event (awaited — critical for downstream consumers)
    await this.kafkaProducer.emit<WorkflowExecutionStartedPayload>(
      TOPICS.WORKFLOW_EXECUTION_STARTED,
      {
        tenantId,
        source: 'workflow-service',
        payload: {
          executionId: execution.id,
          definitionId: execution.definitionId,
          agentId,
          triggerSource: options?.triggerSource || 'api',
          triggerPayload: taskPayload,
          estimatedSteps: 1,
        },
      },
    );

    // 3. Call AI Runtime
    try {
      const result = await this.aiRuntime.executeAgent({
        executionId: execution.id,
        tenantId,
        agentId,
        stepId: 'step-1',
        taskPayload,
        tenantConfig: options?.tenantConfig,
        agentPolicy: options?.agentPolicy,
      });

      const completedAt = new Date();
      const durationMs = completedAt.getTime() - startedAt.getTime();

      const resolvedStatus =
        result.status === 'completed'
          ? WorkflowStatus.COMPLETED
          : result.status === 'escalated'
            ? WorkflowStatus.PAUSED
            : WorkflowStatus.FAILED;

      // 4. Update execution record with result
      const updated = await this.prisma.workflowExecution.update({
        where: { id: execution.id },
        data: {
          status: resolvedStatus,
          completedAt,
          durationMs,
          contextJson: result.output as Prisma.InputJsonValue,
          tokenUsed: result.tokenUsed ?? 0,
          llmCostUsd: result.costUsd ?? 0,
        },
      });

      // 5. Emit completed event (maps escalated → PAUSED)
      const kafkaStatus =
        result.status === 'completed'
          ? ('COMPLETED' as const)
          : result.status === 'escalated'
            ? ('CANCELLED' as const) // PAUSED not in payload union; CANCELLED closest
            : ('FAILED' as const);

      await this.kafkaProducer.emit<WorkflowExecutionCompletedPayload>(
        TOPICS.WORKFLOW_EXECUTION_COMPLETED,
        {
          tenantId,
          source: 'workflow-service',
          payload: {
            executionId: execution.id,
            agentId,
            status: kafkaStatus,
            durationMs,
            stepCount: 1,
            tokenUsed: result.tokenUsed ?? 0,
            costUsd: result.costUsd ?? 0,
            escalationTriggered: result.status === 'escalated',
            outcome: result.nextAction || result.status,
          },
        },
      );

      // 6. Audit trail
      await this.audit.publishAudit({
        tenantId,
        actorType: 'AI_AGENT',
        actorId: agentId,
        action: 'AGENT_TASK_EXECUTED',
        entityType: 'WORKFLOW_EXECUTION',
        entityId: execution.id,
        before: { status: WorkflowStatus.RUNNING },
        after: {
          status: resolvedStatus,
          durationMs,
          tokenUsed: result.tokenUsed,
          costUsd: result.costUsd,
        },
      });

      return updated;
    } catch (error) {
      const completedAt = new Date();
      const durationMs = completedAt.getTime() - startedAt.getTime();
      const errorMessage = error instanceof Error ? error.message : String(error);
      const isTimeout =
        error instanceof Error &&
        (error.name === 'AbortError' || error.message.includes('timeout'));
      const isNetworkError =
        isTimeout ||
        (error instanceof Error &&
          (error.message.includes('ECONNREFUSED') || error.message.includes('fetch failed')));

      // Update execution as failed (try-catch so Kafka emit still fires)
      let updated;
      try {
        updated = await this.prisma.workflowExecution.update({
          where: { id: execution.id },
          data: {
            status: WorkflowStatus.FAILED,
            completedAt,
            durationMs,
          },
        });
      } catch (dbError) {
        this.logger.error(
          `Failed to update execution ${execution.id} to FAILED: ${dbError instanceof Error ? dbError.message : dbError}`,
        );
      }

      // Emit failed event
      await this.kafkaProducer
        .emit<WorkflowExecutionFailedPayload>(TOPICS.WORKFLOW_EXECUTION_FAILED, {
          tenantId,
          source: 'workflow-service',
          payload: {
            executionId: execution.id,
            agentId,
            failedAtStepId: 'step-1',
            failureReason: errorMessage,
            isRetryable: isNetworkError,
            retryAttempt: 0,
            alertOpsTeam: !isNetworkError,
          },
        })
        .catch((kafkaErr) =>
          this.logger.error(
            `Failed to emit WORKFLOW_EXECUTION_FAILED: ${kafkaErr instanceof Error ? kafkaErr.message : kafkaErr}`,
          ),
        );

      // Audit trail for failure
      this.audit
        .publishAudit({
          tenantId,
          actorType: 'AI_AGENT',
          actorId: agentId,
          action: 'AGENT_TASK_FAILED',
          entityType: 'WORKFLOW_EXECUTION',
          entityId: execution.id,
          before: { status: WorkflowStatus.RUNNING },
          after: { status: WorkflowStatus.FAILED, error: errorMessage, durationMs },
        })
        .catch((auditErr) =>
          this.logger.error(
            `Failed to publish failure audit: ${auditErr instanceof Error ? auditErr.message : auditErr}`,
          ),
        );

      this.logger.error(
        `Execution failed: id=${execution.id} agent=${agentId} error=${errorMessage}`,
      );

      return updated ?? execution;
    }
  }
}
