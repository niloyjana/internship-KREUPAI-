import {
  Injectable,
  ForbiddenException,
  NotFoundException,
  Logger,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { AuditService } from '@adwp/kafka';

@Injectable()
export class EntitlementsService {
  private readonly logger = new Logger(EntitlementsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly audit: AuditService,
  ) {}

  // ------------------------------------------------------------------
  // checkEntitlement — verify tenant has active subscription for agent
  // ------------------------------------------------------------------
  async checkEntitlement(tenantId: string, agentId: string) {
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
      select: { id: true, name: true },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    const subscription = await this.prisma.agentSubscription.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
    });

    const isEntitled =
      !!subscription &&
      (subscription.status === 'ACTIVE' || subscription.status === 'TRIAL');

    // Check if the agent config is enabled
    const config = await this.prisma.agentConfig.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      select: { isEnabled: true },
    });

    return {
      tenantId,
      agentId,
      agentName: agentDef.name,
      isEntitled,
      subscriptionStatus: subscription?.status ?? null,
      isEnabled: config?.isEnabled ?? false,
      expiresAt: subscription?.endsAt
        ? subscription.endsAt.toISOString()
        : null,
    };
  }

  // ------------------------------------------------------------------
  // getEntitlements — list all active entitlements for tenant
  // ------------------------------------------------------------------
  async getEntitlements(tenantId: string) {
    const subscriptions = await this.prisma.agentSubscription.findMany({
      where: {
        tenantId,
        status: { in: ['ACTIVE', 'TRIAL'] },
      },
      include: { agentDefinition: true },
      orderBy: { startedAt: 'asc' },
    });

    const entitlements = subscriptions.map((sub) => ({
      agentId: sub.agentDefinition.agentId,
      agentName: sub.agentDefinition.name,
      subscriptionStatus: sub.status,
      startedAt: sub.startedAt.toISOString(),
      expiresAt: sub.endsAt ? sub.endsAt.toISOString() : null,
    }));

    return {
      tenantId,
      entitlements,
      totalActive: entitlements.length,
    };
  }

  // ------------------------------------------------------------------
  // enforceUsageQuota — check if usage quota exceeded for agent
  // ------------------------------------------------------------------
  async enforceUsageQuota(tenantId: string, agentId: string) {
    // 1. Verify entitlement first
    const entitlement = await this.checkEntitlement(tenantId, agentId);
    if (!entitlement.isEntitled) {
      throw new ForbiddenException('NO_ACTIVE_SUBSCRIPTION');
    }

    if (!entitlement.isEnabled) {
      throw new ForbiddenException('AGENT_DISABLED');
    }

    // 2. Fetch the agent definition for quota limits
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
    });

    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    // 3. Get current billing period usage
    const now = new Date();
    const periodStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const periodEnd = new Date(
      now.getFullYear(),
      now.getMonth() + 1,
      0,
      23,
      59,
      59,
      999,
    );

    const usageMetrics = await this.prisma.usageMetric.findMany({
      where: {
        tenantId,
        agentId,
        periodStart: { gte: periodStart },
        periodEnd: { lte: periodEnd },
      },
    });

    const totalTasks = usageMetrics.reduce((sum, m) => sum + m.taskCount, 0);
    const totalTokens = usageMetrics.reduce((sum, m) => sum + m.tokenCount, 0);

    // 4. Extract quota limits from agent definition metadata
    const agentDefAny = agentDef as Record<string, unknown>;
    const metadata =
      typeof agentDefAny.metadata === 'object' && agentDefAny.metadata !== null
        ? (agentDefAny.metadata as Record<string, unknown>)
        : {};

    const maxTasksPerMonth =
      typeof metadata.maxTasksPerMonth === 'number'
        ? metadata.maxTasksPerMonth
        : null;

    const maxTokensPerMonth =
      typeof metadata.maxTokensPerMonth === 'number'
        ? metadata.maxTokensPerMonth
        : null;

    const taskQuotaExceeded =
      maxTasksPerMonth !== null && totalTasks >= maxTasksPerMonth;

    const tokenQuotaExceeded =
      maxTokensPerMonth !== null && totalTokens >= maxTokensPerMonth;

    const quotaExceeded = taskQuotaExceeded || tokenQuotaExceeded;

    if (quotaExceeded) {
      this.logger.warn(
        `Usage quota exceeded for tenant=${tenantId} agent=${agentId}: tasks=${totalTasks}/${maxTasksPerMonth}, tokens=${totalTokens}/${maxTokensPerMonth}`,
      );

      await this.audit.publishAudit({
        tenantId,
        actorType: 'SYSTEM',
        actorId: 'entitlements-service',
        action: 'USAGE_QUOTA_EXCEEDED',
        entityType: 'AGENT_SUBSCRIPTION',
        entityId: agentId,
        after: {
          totalTasks,
          maxTasksPerMonth,
          totalTokens,
          maxTokensPerMonth,
        },
      });

      throw new ForbiddenException('USAGE_QUOTA_EXCEEDED');
    }

    return {
      tenantId,
      agentId,
      quotaExceeded: false,
      usage: {
        tasks: totalTasks,
        maxTasks: maxTasksPerMonth,
        tokens: totalTokens,
        maxTokens: maxTokensPerMonth,
      },
      period: {
        start: periodStart.toISOString(),
        end: periodEnd.toISOString(),
      },
    };
  }
}
