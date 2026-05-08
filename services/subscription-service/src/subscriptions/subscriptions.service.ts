import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  BillingSubscriptionActivatedPayload,
  AgentSubscribedPayload,
  AgentStatusChangedPayload,
} from '@adwp/kafka';
import { SubscribeAgentDto } from './dto/subscribe-agent.dto';
import { UsageQueryDto } from './dto/usage-query.dto';
import { InvoiceQueryDto } from './dto/invoice-query.dto';
import { Prisma } from '@prisma/client';

/** Fixed monthly platform fee in USD */
const PLATFORM_FEE_USD = 499;

/** Bundle discount: 15 % when a tenant has 3+ active agents */
const BUNDLE_DISCOUNT_PCT = 0.15;
const BUNDLE_DISCOUNT_THRESHOLD = 3;

@Injectable()
export class SubscriptionsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ------------------------------------------------------------------
  // GET /v1/subscriptions — list tenant subscriptions + pricing summary
  // ------------------------------------------------------------------
  async getSubscriptions(tenantId: string) {
    const subscriptions = await this.prisma.agentSubscription.findMany({
      where: { tenantId },
      include: { agentDefinition: true },
      orderBy: { startedAt: 'asc' },
    });

    const activeSubscriptions = subscriptions.filter(
      (s) => s.status === 'ACTIVE' || s.status === 'TRIAL',
    );

    const agents = subscriptions.map((sub) => ({
      agentId: sub.agentDefinition.agentId,
      name: sub.agentDefinition.name,
      status: sub.status,
      monthlyPriceUsd: Number(sub.agentDefinition.monthlyPricingUsd),
      startedAt: sub.startedAt.toISOString(),
      cancelledAt: sub.cancelledAt ? sub.cancelledAt.toISOString() : undefined,
      stripeSubItemId: sub.stripeSubItemId ?? undefined,
    }));

    const agentTotalUsd = activeSubscriptions.reduce(
      (sum, s) => sum + Number(s.agentDefinition.monthlyPricingUsd),
      0,
    );

    const activeCount = activeSubscriptions.length;
    const hasDiscount = activeCount >= BUNDLE_DISCOUNT_THRESHOLD;
    const discount = hasDiscount ? BUNDLE_DISCOUNT_PCT : 0;
    const discountReason = hasDiscount
      ? `Department bundle (${BUNDLE_DISCOUNT_THRESHOLD}+ agents)`
      : undefined;

    const subtotalBeforeDiscount = PLATFORM_FEE_USD + agentTotalUsd;
    const totalMonthlyUsd = parseFloat((subtotalBeforeDiscount * (1 - discount)).toFixed(2));

    return {
      platformFeeUsd: PLATFORM_FEE_USD,
      agents,
      totalMonthlyUsd,
      discount,
      discountReason,
    };
  }

  // ------------------------------------------------------------------
  // POST /v1/subscriptions/agents — subscribe to a new agent
  // ------------------------------------------------------------------
  async subscribeAgent(tenantId: string, dto: SubscribeAgentDto) {
    // 1. Verify agent definition exists
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId: dto.agentId },
    });
    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    // 2. Check not already subscribed (active/trial)
    const existing = await this.prisma.agentSubscription.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
    });
    if (existing && (existing.status === 'ACTIVE' || existing.status === 'TRIAL')) {
      throw new ConflictException('AGENT_ALREADY_SUBSCRIBED');
    }

    const now = new Date();

    // 3. Create or update AgentSubscription record
    let subscription;
    if (existing) {
      // Re-activate a previously cancelled subscription
      subscription = await this.prisma.agentSubscription.update({
        where: { id: existing.id },
        data: {
          status: 'ACTIVE',
          startedAt: now,
          cancelledAt: null,
          endsAt: null,
        },
        include: { agentDefinition: true },
      });
    } else {
      subscription = await this.prisma.agentSubscription.create({
        data: {
          tenantId,
          agentDefinitionId: agentDef.id,
          status: 'ACTIVE',
          startedAt: now,
        },
        include: { agentDefinition: true },
      });
    }

    // 4. Create AgentConfig record (upsert so we don't fail on re-subscription)
    await this.prisma.agentConfig.upsert({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
      create: {
        tenantId,
        agentDefinitionId: agentDef.id,
        displayName: agentDef.name,
        policyJson: (agentDef.defaultPolicyJson ?? Prisma.JsonNull) as Prisma.InputJsonValue,
        integrationIds: [],
        isEnabled: true,
      },
      update: {
        isEnabled: true,
      },
    });

    // 5. Create billing event
    await this.prisma.billingEvent.create({
      data: {
        tenantId,
        eventType: 'AGENT_ADDED',
        agentId: dto.agentId,
        amountUsd: agentDef.monthlyPricingUsd,
        metadata: {
          agentDefinitionId: agentDef.id,
          subscriptionId: subscription.id,
        },
      },
    });

    // 6. Calculate new pricing with potential bundle discount
    const activeCount = await this.prisma.agentSubscription.count({
      where: {
        tenantId,
        status: { in: ['ACTIVE', 'TRIAL'] },
      },
    });

    const hasDiscount = activeCount >= BUNDLE_DISCOUNT_THRESHOLD;
    const discount = hasDiscount ? BUNDLE_DISCOUNT_PCT : 0;

    // 7. Publish Kafka events
    await this.kafkaProducer.emit<BillingSubscriptionActivatedPayload>(
      TOPICS.BILLING_SUBSCRIPTION_ACTIVATED,
      {
        tenantId,
        source: 'subscription-service',
        payload: {
          subscriptionId: subscription.id,
          tenantId,
          agentId: dto.agentId,
          plan: subscription.status,
          monthlyAmountUsd: Number(agentDef.monthlyPricingUsd),
          stripeSubItemId: subscription.stripeSubItemId ?? '',
          billingCycleStart: now.toISOString(),
        },
      },
    );

    await this.kafkaProducer.emit<AgentSubscribedPayload>(TOPICS.AGENT_SUBSCRIBED, {
      tenantId,
      source: 'subscription-service',
      payload: {
        subscriptionId: subscription.id,
        tenantId,
        agentId: dto.agentId,
        agentName: agentDef.name,
        department: agentDef.department ?? 'general',
        plan: subscription.status,
        monthlyPriceUsd: Number(agentDef.monthlyPricingUsd),
        startedAt: subscription.startedAt.toISOString(),
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'AGENT_SUBSCRIBED',
      entityType: 'AGENT_SUBSCRIPTION',
      entityId: subscription.id,
      after: { agentId: dto.agentId, status: subscription.status },
    });

    return {
      subscription: {
        id: subscription.id,
        agentId: agentDef.agentId,
        name: agentDef.name,
        status: subscription.status,
        monthlyPriceUsd: Number(agentDef.monthlyPricingUsd),
        startedAt: subscription.startedAt.toISOString(),
      },
      pricing: {
        platformFeeUsd: PLATFORM_FEE_USD,
        activeAgents: activeCount,
        discount,
        discountReason: hasDiscount
          ? `Department bundle (${BUNDLE_DISCOUNT_THRESHOLD}+ agents)`
          : undefined,
      },
    };
  }

  // ------------------------------------------------------------------
  // DELETE /v1/subscriptions/agents/:agentId — unsubscribe from agent
  // ------------------------------------------------------------------
  async unsubscribeAgent(tenantId: string, agentId: string) {
    // 1. Find agent definition
    const agentDef = await this.prisma.agentDefinition.findUnique({
      where: { agentId },
    });
    if (!agentDef) {
      throw new NotFoundException('AGENT_NOT_FOUND');
    }

    // 2. Find active subscription
    const subscription = await this.prisma.agentSubscription.findUnique({
      where: {
        tenantId_agentDefinitionId: {
          tenantId,
          agentDefinitionId: agentDef.id,
        },
      },
    });
    if (!subscription || (subscription.status !== 'ACTIVE' && subscription.status !== 'TRIAL')) {
      throw new NotFoundException('SUBSCRIPTION_NOT_FOUND');
    }

    const now = new Date();

    // 3. Calculate effective cancellation date (end of current billing period)
    //    Billing period = month boundary from the subscription start date.
    const effectiveCancelDate = this.calculateBillingPeriodEnd(subscription.startedAt, now);

    // 4. Update AgentSubscription
    await this.prisma.agentSubscription.update({
      where: { id: subscription.id },
      data: {
        status: 'CANCELLED',
        cancelledAt: now,
        endsAt: effectiveCancelDate,
      },
    });

    // 5. Set AgentConfig to disabled
    await this.prisma.agentConfig.updateMany({
      where: {
        tenantId,
        agentDefinitionId: agentDef.id,
      },
      data: {
        isEnabled: false,
      },
    });

    // 6. Create billing event
    await this.prisma.billingEvent.create({
      data: {
        tenantId,
        eventType: 'AGENT_REMOVED',
        agentId,
        metadata: {
          subscriptionId: subscription.id,
          effectiveCancelDate: effectiveCancelDate.toISOString(),
        },
      },
    });

    // 7. Publish Kafka events for cancellation
    await this.kafkaProducer.emit<AgentStatusChangedPayload>(TOPICS.AGENT_STATUS_CHANGED, {
      tenantId,
      source: 'subscription-service',
      payload: {
        tenantId,
        agentId,
        instanceId: 'default',
        previousStatus: 'ACTIVE',
        newStatus: 'CANCELLED',
        currentTaskId: null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'AGENT_UNSUBSCRIBED',
      entityType: 'AGENT_SUBSCRIPTION',
      entityId: subscription.id,
      before: { agentId, status: 'ACTIVE' },
      after: { status: 'CANCELLED', effectiveCancelDate: effectiveCancelDate.toISOString() },
    });

    return {
      agentId,
      status: 'CANCELLED',
      cancelledAt: now.toISOString(),
      effectiveCancelDate: effectiveCancelDate.toISOString(),
    };
  }

  // ------------------------------------------------------------------
  // GET /v1/subscriptions/usage — get usage metering
  // ------------------------------------------------------------------
  async getUsage(tenantId: string, query: UsageQueryDto) {
    const now = new Date();
    const fromDate = query.from
      ? new Date(query.from)
      : new Date(now.getFullYear(), now.getMonth(), 1);
    const toDate = query.to
      ? new Date(query.to)
      : new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999);

    const where: Record<string, unknown> = {
      tenantId,
      periodStart: { gte: fromDate },
      periodEnd: { lte: toDate },
    };
    if (query.agentId) {
      where.agentId = query.agentId;
    }

    const metrics = await this.prisma.usageMetric.findMany({
      where,
      orderBy: { periodStart: 'desc' },
    });

    if (metrics.length === 0) {
      // Return zeroes if no data
      return {
        from: fromDate.toISOString(),
        to: toDate.toISOString(),
        agentId: query.agentId ?? null,
        taskCount: 0,
        tokenCount: 0,
        llmCostUsd: 0,
        escalationCount: 0,
        avgTaskDurationMs: 0,
        breakdown: [],
      };
    }

    // Aggregate across all matching metrics
    let totalTasks = 0;
    let totalTokens = 0;
    let totalCostUsd = 0;
    let totalEscalations = 0;
    let totalDurationMs = 0;
    let durationMetricCount = 0;

    const breakdown: Array<{
      agentId: string;
      periodStart: string;
      periodEnd: string;
      taskCount: number;
      tokenCount: number;
      llmCostUsd: number;
      escalationCount: number;
      avgTaskDurationMs: number;
    }> = [];

    for (const m of metrics) {
      totalTasks += m.taskCount;
      totalTokens += m.tokenCount;
      totalCostUsd += Number(m.costUsd);
      totalEscalations += m.escalationCount;
      if (m.avgDurationMs !== null) {
        totalDurationMs += m.avgDurationMs * m.taskCount;
        durationMetricCount += m.taskCount;
      }

      breakdown.push({
        agentId: m.agentId,
        periodStart: m.periodStart.toISOString(),
        periodEnd: m.periodEnd.toISOString(),
        taskCount: m.taskCount,
        tokenCount: m.tokenCount,
        llmCostUsd: Number(m.costUsd),
        escalationCount: m.escalationCount,
        avgTaskDurationMs: m.avgDurationMs ?? 0,
      });
    }

    const avgTaskDurationMs =
      durationMetricCount > 0 ? parseFloat((totalDurationMs / durationMetricCount).toFixed(2)) : 0;

    return {
      from: fromDate.toISOString(),
      to: toDate.toISOString(),
      agentId: query.agentId ?? null,
      taskCount: totalTasks,
      tokenCount: totalTokens,
      llmCostUsd: parseFloat(totalCostUsd.toFixed(4)),
      escalationCount: totalEscalations,
      avgTaskDurationMs,
      breakdown,
    };
  }

  // ------------------------------------------------------------------
  // GET /v1/subscriptions/invoices — list invoices
  // ------------------------------------------------------------------
  async getInvoices(tenantId: string, query: InvoiceQueryDto) {
    const page = query.page ?? 1;
    const limit = query.limit ?? 20;
    const skip = (page - 1) * limit;

    const [invoices, total] = await Promise.all([
      this.prisma.invoice.findMany({
        where: { tenantId },
        orderBy: { periodStart: 'desc' },
        skip,
        take: limit,
      }),
      this.prisma.invoice.count({ where: { tenantId } }),
    ]);

    return {
      invoices: invoices.map((inv) => ({
        id: inv.id,
        periodStart: inv.periodStart.toISOString(),
        periodEnd: inv.periodEnd.toISOString(),
        subtotalUsd: Number(inv.subtotalUsd),
        taxUsd: Number(inv.taxUsd),
        totalUsd: Number(inv.totalUsd),
        status: inv.status,
        pdfUrl: inv.pdfUrl,
        paidAt: inv.paidAt ? inv.paidAt.toISOString() : null,
        dueAt: inv.dueAt ? inv.dueAt.toISOString() : null,
        createdAt: inv.createdAt.toISOString(),
      })),
      meta: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  // ------------------------------------------------------------------
  // GET /v1/subscriptions/invoices/:invoiceId — get invoice detail
  // ------------------------------------------------------------------
  async getInvoiceDetail(tenantId: string, invoiceId: string) {
    const invoice = await this.prisma.invoice.findFirst({
      where: { id: invoiceId, tenantId },
    });

    if (!invoice) {
      throw new NotFoundException('INVOICE_NOT_FOUND');
    }

    return {
      id: invoice.id,
      stripeInvoiceId: invoice.stripeInvoiceId,
      periodStart: invoice.periodStart.toISOString(),
      periodEnd: invoice.periodEnd.toISOString(),
      subtotalUsd: Number(invoice.subtotalUsd),
      taxUsd: Number(invoice.taxUsd),
      totalUsd: Number(invoice.totalUsd),
      status: invoice.status,
      pdfUrl: invoice.pdfUrl,
      paidAt: invoice.paidAt ? invoice.paidAt.toISOString() : null,
      dueAt: invoice.dueAt ? invoice.dueAt.toISOString() : null,
      lineItems: invoice.lineItems,
      createdAt: invoice.createdAt.toISOString(),
      updatedAt: invoice.updatedAt.toISOString(),
    };
  }

  // ------------------------------------------------------------------
  // Private helpers
  // ------------------------------------------------------------------

  /**
   * Given a subscription start date and the current date, compute the end
   * of the current monthly billing period.
   *
   * Example: if startedAt is Jan 15 and now is Mar 20, the current period
   * runs from Mar 15 to Apr 14 — so effective cancel date is Apr 15 00:00.
   */
  private calculateBillingPeriodEnd(startedAt: Date, now: Date): Date {
    const startDay = startedAt.getDate();
    let year = now.getFullYear();
    let month = now.getMonth();

    // Find the current period start in the current month
    const periodStartThisMonth = new Date(year, month, startDay);

    if (now < periodStartThisMonth) {
      // We are before this month's period start, so the current period
      // started last month and ends at periodStartThisMonth.
      return periodStartThisMonth;
    }

    // Current period started this month; it ends next month on the same day.
    month += 1;
    if (month > 11) {
      month = 0;
      year += 1;
    }
    return new Date(year, month, startDay);
  }
}
