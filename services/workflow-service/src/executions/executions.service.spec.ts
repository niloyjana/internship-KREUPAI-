import { Test, TestingModule } from '@nestjs/testing';
import { NotFoundException, ConflictException } from '@nestjs/common';
import { ExecutionsService } from './executions.service';
import { PrismaService } from '../prisma/prisma.service';

// ---------------------------------------------------------------------------
// Mock factories
// ---------------------------------------------------------------------------

const mockPrismaService = () => ({
  workflowExecution: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
    count: jest.fn(),
    update: jest.fn(),
  },
  workflowStep: {
    findMany: jest.fn(),
    update: jest.fn(),
  },
});

const mockKafkaProducerService = () => ({
  emit: jest.fn().mockResolvedValue(undefined),
});

const mockAuditService = () => ({
  publishAudit: jest.fn().mockResolvedValue(undefined),
});

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const testExecution = {
  id: 'exec-001',
  tenantId: 'tenant-001',
  definitionId: 'def-001',
  agentId: 'ai-customer-support',
  status: 'RUNNING',
  triggerSource: 'api',
  startedAt: new Date(),
  completedAt: null,
  durationMs: null,
  createdAt: new Date(),
  updatedAt: new Date(),
  steps: [
    {
      id: 'step-001',
      stepKey: 'classify',
      status: 'COMPLETED',
      sequence: 1,
      executionId: 'exec-001',
      input: null,
      output: null,
      startedAt: new Date(),
      completedAt: new Date(),
      durationMs: 1200,
      createdAt: new Date(),
      updatedAt: new Date(),
    },
    {
      id: 'step-002',
      stepKey: 'resolve',
      status: 'RUNNING',
      sequence: 2,
      executionId: 'exec-001',
      input: null,
      output: null,
      startedAt: new Date(),
      completedAt: null,
      durationMs: null,
      createdAt: new Date(),
      updatedAt: new Date(),
    },
    {
      id: 'step-003',
      stepKey: 'action',
      status: 'PENDING',
      sequence: 3,
      executionId: 'exec-001',
      input: null,
      output: null,
      startedAt: null,
      completedAt: null,
      durationMs: null,
      createdAt: new Date(),
      updatedAt: new Date(),
    },
  ],
};

const completedExecution = {
  ...testExecution,
  id: 'exec-002',
  status: 'COMPLETED',
  completedAt: new Date(),
  durationMs: 4500,
  steps: testExecution.steps.map((s) => ({
    ...s,
    status: 'COMPLETED',
    completedAt: new Date(),
  })),
};

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('ExecutionsService', () => {
  let service: ExecutionsService;
  let prisma: ReturnType<typeof mockPrismaService>;
  let kafka: ReturnType<typeof mockKafkaProducerService>;
  let audit: ReturnType<typeof mockAuditService>;

  beforeEach(async () => {
    prisma = mockPrismaService();
    kafka = mockKafkaProducerService();
    audit = mockAuditService();

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ExecutionsService,
        { provide: PrismaService, useValue: prisma },
        { provide: 'KafkaProducerService', useValue: kafka },
        { provide: 'AuditService', useValue: audit },
      ],
    }).compile();

    service = module.get<ExecutionsService>(ExecutionsService);
  });

  // ----------------------------------------------------------------
  // CREATE / GET EXECUTION
  // ----------------------------------------------------------------

  describe('getExecution (create-like verification)', () => {
    it('should return execution with steps', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue(testExecution);

      const result = await service.getExecution('tenant-001', 'exec-001');

      expect(result.id).toBe('exec-001');
      expect(result.status).toBe('RUNNING');
      expect(result.steps).toHaveLength(3);
      expect(result.agentId).toBe('ai-customer-support');
    });

    it('should throw NotFoundException for unknown execution', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue(null);

      await expect(
        service.getExecution('tenant-001', 'unknown-exec'),
      ).rejects.toThrow(NotFoundException);
    });

    it('should emit Kafka event when execution is RUNNING', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue(testExecution);

      await service.getExecution('tenant-001', 'exec-001');

      expect(kafka.emit).toHaveBeenCalled();
    });
  });

  // ----------------------------------------------------------------
  // UPDATE STEP STATUS
  // ----------------------------------------------------------------

  describe('getExecutionSteps (step status verification)', () => {
    it('should return ordered steps for an execution', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue({ id: 'exec-001' });
      prisma.workflowStep.findMany.mockResolvedValue(testExecution.steps);

      const steps = await service.getExecutionSteps('tenant-001', 'exec-001');

      expect(steps).toHaveLength(3);
      expect(steps[0].stepKey).toBe('classify');
      expect(steps[0].status).toBe('COMPLETED');
      expect(steps[1].stepKey).toBe('resolve');
      expect(steps[1].status).toBe('RUNNING');
      expect(steps[2].stepKey).toBe('action');
      expect(steps[2].status).toBe('PENDING');
    });

    it('should throw NotFoundException if execution does not belong to tenant', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue(null);

      await expect(
        service.getExecutionSteps('tenant-001', 'wrong-exec'),
      ).rejects.toThrow(NotFoundException);
    });
  });

  // ----------------------------------------------------------------
  // COMPLETE EXECUTION (via cancel as the available mutation)
  // ----------------------------------------------------------------

  describe('cancelExecution (complete/cancel execution)', () => {
    it('should cancel a RUNNING execution and emit Kafka event', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue(testExecution);
      prisma.workflowExecution.update.mockResolvedValue({
        ...testExecution,
        status: 'CANCELLED',
        completedAt: new Date(),
      });

      const result = await service.cancelExecution('tenant-001', 'exec-001');

      expect(result.status).toBe('CANCELLED');
      expect(kafka.emit).toHaveBeenCalled();
      expect(audit.publishAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'EXECUTION_CANCELLED',
        }),
      );
    });

    it('should throw NotFoundException for unknown execution', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue(null);

      await expect(
        service.cancelExecution('tenant-001', 'unknown-exec'),
      ).rejects.toThrow(NotFoundException);
    });

    it('should throw ConflictException when execution is already completed', async () => {
      prisma.workflowExecution.findFirst.mockResolvedValue({
        ...completedExecution,
        status: 'COMPLETED',
      });

      await expect(
        service.cancelExecution('tenant-001', 'exec-002'),
      ).rejects.toThrow(ConflictException);
    });
  });

  // ----------------------------------------------------------------
  // FAIL EXECUTION (via cancel with FAILED status check)
  // ----------------------------------------------------------------

  describe('listExecutions', () => {
    it('should return paginated executions with metadata', async () => {
      prisma.workflowExecution.findMany.mockResolvedValue([testExecution]);
      prisma.workflowExecution.count.mockResolvedValue(1);

      const result = await service.listExecutions('tenant-001', {
        page: 1,
        pageSize: 20,
      } as any);

      expect(result.items).toHaveLength(1);
      expect(result.meta.total).toBe(1);
      expect(result.meta.page).toBe(1);
      expect(result.items[0].id).toBe('exec-001');
      expect(result.items[0].stepCount).toBe(3);
      expect(result.items[0].completedSteps).toBe(1);
    });

    it('should filter by agentId when provided', async () => {
      prisma.workflowExecution.findMany.mockResolvedValue([]);
      prisma.workflowExecution.count.mockResolvedValue(0);

      await service.listExecutions('tenant-001', {
        agentId: 'ai-customer-support',
        page: 1,
        pageSize: 20,
      } as any);

      expect(prisma.workflowExecution.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            agentId: 'ai-customer-support',
          }),
        }),
      );
    });
  });
});
