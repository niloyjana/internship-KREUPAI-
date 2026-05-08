import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { Prisma, TaskStatus, StepStatus } from '@prisma/client';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  HumanTaskResolvedPayload,
  HumanTaskCreatedPayload,
} from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { ListHumanTasksQueryDto } from './dto/list-human-tasks-query.dto';
import { ResolveTaskDto } from './dto/resolve-task.dto';

@Injectable()
export class HumanTasksService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  async listHumanTasks(tenantId: string, userId: string, query: ListHumanTasksQueryDto) {
    const { status, assignedTo, priority } = query;
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.HumanTaskWhereInput = { tenantId };

    if (status) {
      where.status = status as TaskStatus;
    }
    if (priority) {
      where.priority = priority;
    }
    if (assignedTo === 'me') {
      where.assignedToId = userId;
    } else if (assignedTo) {
      where.assignedToId = assignedTo;
    }

    const [tasks, total] = await Promise.all([
      this.prisma.humanTask.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.humanTask.count({ where }),
    ]);

    return {
      items: tasks,
      meta: {
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getHumanTask(tenantId: string, taskId: string) {
    const task = await this.prisma.humanTask.findFirst({
      where: { id: taskId, tenantId },
      include: {
        step: true,
      },
    });

    if (!task) {
      throw new NotFoundException('TASK_NOT_FOUND');
    }

    return task;
  }

  async resolveHumanTask(tenantId: string, taskId: string, userId: string, dto: ResolveTaskDto) {
    const task = await this.prisma.humanTask.findFirst({
      where: { id: taskId, tenantId },
    });

    if (!task) {
      throw new NotFoundException('TASK_NOT_FOUND');
    }

    if (task.status === TaskStatus.COMPLETED || task.status === TaskStatus.REJECTED) {
      throw new ConflictException('TASK_ALREADY_RESOLVED');
    }

    const newTaskStatus = dto.decision === 'reject' ? TaskStatus.REJECTED : TaskStatus.COMPLETED;

    const newStepStatus = dto.decision === 'reject' ? StepStatus.FAILED : StepStatus.COMPLETED;

    const now = new Date();

    const [updatedTask] = await this.prisma.$transaction([
      this.prisma.humanTask.update({
        where: { id: taskId },
        data: {
          status: newTaskStatus,
          decision: dto.decision,
          decisionNote: dto.decisionNote,
          completedAt: now,
          completedById: userId,
        },
      }),
      this.prisma.workflowStep.update({
        where: { id: task.stepId },
        data: {
          status: newStepStatus,
          completedAt: now,
        },
      }),
    ]);

    // Emit human task resolved event
    const durationMs = task.createdAt ? now.getTime() - new Date(task.createdAt).getTime() : 0;

    await this.kafkaProducer.emit<HumanTaskResolvedPayload>(TOPICS.HUMAN_TASK_RESOLVED, {
      tenantId,
      source: 'workflow-service',
      payload: {
        taskId: updatedTask.id,
        executionId: task.executionId,
        stepId: task.stepId,
        decision: dto.decision,
        decisionNote: dto.decisionNote ?? null,
        resolvedByUserId: userId,
        durationToResolveMs: durationMs,
        slaBreached: false,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'HUMAN_TASK_RESOLVED',
      entityType: 'HUMAN_TASK',
      entityId: taskId,
      before: { status: task.status },
      after: { status: updatedTask.status, decision: dto.decision },
    });

    return updatedTask;
  }

  async createHumanTask(
    tenantId: string,
    executionId: string,
    stepId: string,
    title: string,
    priority: string,
    assignedToUserId: string | null,
    dueAt: Date,
  ) {
    const task = await this.prisma.humanTask.create({
      data: {
        tenantId,
        executionId,
        stepId,
        title,
        priority,
        assignedToId: assignedToUserId,
        dueAt,
        status: 'PENDING',
      },
    });

    await this.kafkaProducer.emit<HumanTaskCreatedPayload>(TOPICS.HUMAN_TASK_CREATED, {
      tenantId,
      source: 'workflow-service',
      payload: {
        taskId: task.id,
        executionId,
        stepId,
        title,
        priority,
        assignedToUserId,
        assignedTeam: null,
        dueAt: dueAt.toISOString(),
      },
    });

    return task;
  }
}
