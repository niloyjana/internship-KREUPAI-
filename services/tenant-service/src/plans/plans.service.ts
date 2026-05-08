import { BadRequestException, Injectable, Logger, NotFoundException } from '@nestjs/common';
import { TenantPlan } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { KafkaProducerService, AuditService, TOPICS, TenantPlanChangedPayload } from '@adwp/kafka';

export interface PlanDefinition {
  id: string;
  name: string;
  description: string;
  monthlyPrice: number;
  yearlyPrice: number;
  features: string[];
  limits: {
    maxUsers: number;
    maxAgents: number;
    maxStorageGb: number;
    maxApiCallsPerMonth: number;
  };
}

const PLAN_DEFINITIONS: PlanDefinition[] = [
  {
    id: 'STARTER',
    name: 'Starter',
    description: 'For small teams getting started with AI-powered operations',
    monthlyPrice: 49,
    yearlyPrice: 470,
    features: [
      'Up to 5 users',
      'Basic AI agent',
      'Email support',
      '5 GB storage',
      'Standard analytics',
    ],
    limits: {
      maxUsers: 5,
      maxAgents: 1,
      maxStorageGb: 5,
      maxApiCallsPerMonth: 10000,
    },
  },
  {
    id: 'GROWTH',
    name: 'Growth',
    description: 'For growing teams that need more power and flexibility',
    monthlyPrice: 149,
    yearlyPrice: 1430,
    features: [
      'Up to 25 users',
      'Multiple AI agents',
      'Priority support',
      '50 GB storage',
      'Advanced analytics',
      'Custom workflows',
    ],
    limits: {
      maxUsers: 25,
      maxAgents: 5,
      maxStorageGb: 50,
      maxApiCallsPerMonth: 100000,
    },
  },
  {
    id: 'ENTERPRISE',
    name: 'Enterprise',
    description: 'For large organizations with advanced requirements',
    monthlyPrice: 499,
    yearlyPrice: 4790,
    features: [
      'Unlimited users',
      'Unlimited AI agents',
      'Dedicated support',
      '500 GB storage',
      'Custom analytics & reports',
      'Custom workflows',
      'SSO / SAML',
      'Audit logs',
      'SLA guarantee',
    ],
    limits: {
      maxUsers: -1, // unlimited
      maxAgents: -1, // unlimited
      maxStorageGb: 500,
      maxApiCallsPerMonth: 1000000,
    },
  },
  {
    id: 'CUSTOM',
    name: 'Custom',
    description: 'Tailored plan for unique business needs — contact sales',
    monthlyPrice: -1, // contact sales
    yearlyPrice: -1, // contact sales
    features: [
      'Everything in Enterprise',
      'Custom integrations',
      'Dedicated infrastructure',
      'White-label options',
      'Custom SLA',
    ],
    limits: {
      maxUsers: -1,
      maxAgents: -1,
      maxStorageGb: -1,
      maxApiCallsPerMonth: -1,
    },
  },
];

@Injectable()
export class PlansService {
  private readonly logger = new Logger(PlansService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ─── LIST PLANS ─────────────────────────────────────────────────────────────

  async listPlans(): Promise<PlanDefinition[]> {
    return PLAN_DEFINITIONS;
  }

  // ─── GET PLAN DETAILS ──────────────────────────────────────────────────────

  async getPlanById(planId: string): Promise<PlanDefinition> {
    const plan = PLAN_DEFINITIONS.find((p) => p.id === planId.toUpperCase());

    if (!plan) {
      throw new NotFoundException(`Plan "${planId}" not found`);
    }

    return plan;
  }

  // ─── UPGRADE TENANT PLAN ───────────────────────────────────────────────────

  async upgradeTenantPlan(tenantId: string, actorId: string, targetPlan: string) {
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    const currentPlanIndex = this.getPlanIndex(tenant.plan);
    const targetPlanIndex = this.getPlanIndex(targetPlan.toUpperCase());

    if (targetPlanIndex === -1) {
      throw new BadRequestException(`Invalid target plan "${targetPlan}"`);
    }

    if (targetPlanIndex <= currentPlanIndex) {
      throw new BadRequestException(
        `Cannot upgrade from ${tenant.plan} to ${targetPlan.toUpperCase()}. Use the downgrade endpoint instead or select a higher plan.`,
      );
    }

    const previousPlan = tenant.plan;

    const updated = await this.prisma.tenant.update({
      where: { id: tenantId },
      data: { plan: targetPlan.toUpperCase() as TenantPlan },
    });

    this.logger.log(
      `Tenant ${tenantId} upgraded from ${previousPlan} to ${targetPlan.toUpperCase()}`,
    );

    await this.kafkaProducer.emit<TenantPlanChangedPayload>(TOPICS.TENANT_PLAN_CHANGED, {
      tenantId,
      source: 'tenant-service',
      payload: {
        tenantId,
        previousPlan,
        newPlan: targetPlan.toUpperCase(),
        action: 'UPGRADE',
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId,
      action: 'TENANT_PLAN_UPGRADED',
      entityType: 'TENANT',
      entityId: tenantId,
      before: { plan: previousPlan },
      after: { plan: targetPlan.toUpperCase() },
    });

    return {
      tenantId: updated.id,
      previousPlan,
      currentPlan: updated.plan,
      action: 'UPGRADE',
      updatedAt: updated.updatedAt,
    };
  }

  // ─── DOWNGRADE TENANT PLAN ────────────────────────────────────────────────

  async downgradeTenantPlan(tenantId: string, actorId: string, targetPlan: string) {
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    const currentPlanIndex = this.getPlanIndex(tenant.plan);
    const targetPlanIndex = this.getPlanIndex(targetPlan.toUpperCase());

    if (targetPlanIndex === -1) {
      throw new BadRequestException(`Invalid target plan "${targetPlan}"`);
    }

    if (targetPlanIndex >= currentPlanIndex) {
      throw new BadRequestException(
        `Cannot downgrade from ${tenant.plan} to ${targetPlan.toUpperCase()}. Use the upgrade endpoint instead or select a lower plan.`,
      );
    }

    const previousPlan = tenant.plan;

    const updated = await this.prisma.tenant.update({
      where: { id: tenantId },
      data: { plan: targetPlan.toUpperCase() as TenantPlan },
    });

    this.logger.log(
      `Tenant ${tenantId} downgraded from ${previousPlan} to ${targetPlan.toUpperCase()}`,
    );

    await this.kafkaProducer.emit<TenantPlanChangedPayload>(TOPICS.TENANT_PLAN_CHANGED, {
      tenantId,
      source: 'tenant-service',
      payload: {
        tenantId,
        previousPlan,
        newPlan: targetPlan.toUpperCase(),
        action: 'DOWNGRADE',
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId,
      action: 'TENANT_PLAN_DOWNGRADED',
      entityType: 'TENANT',
      entityId: tenantId,
      before: { plan: previousPlan },
      after: { plan: targetPlan.toUpperCase() },
    });

    return {
      tenantId: updated.id,
      previousPlan,
      currentPlan: updated.plan,
      action: 'DOWNGRADE',
      updatedAt: updated.updatedAt,
    };
  }

  // ─── HELPERS ────────────────────────────────────────────────────────────────

  private getPlanIndex(plan: string): number {
    const order = ['STARTER', 'GROWTH', 'ENTERPRISE', 'CUSTOM'];
    return order.indexOf(plan);
  }
}
