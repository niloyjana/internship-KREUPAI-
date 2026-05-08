import { Injectable, BadRequestException, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  BillingSubscriptionActivatedPayload,
  AgentStatusChangedPayload,
  BillingPaymentFailedPayload,
} from '@adwp/kafka';
import Stripe from 'stripe';

@Injectable()
export class StripeWebhookService {
  private readonly logger = new Logger(StripeWebhookService.name);
  private readonly stripe: Stripe | null;
  private readonly webhookSecret: string;

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
    private readonly config: ConfigService,
  ) {
    const stripeKey = this.config.get<string>('STRIPE_SECRET_KEY', '');
    if (stripeKey) {
      this.stripe = new Stripe(stripeKey, {
        apiVersion: '2024-04-10' as Stripe.LatestApiVersion,
      });
    } else {
      this.logger.warn('STRIPE_SECRET_KEY not set — Stripe webhooks disabled');
      this.stripe = null;
    }
    this.webhookSecret = this.config.get<string>('STRIPE_WEBHOOK_SECRET', '');
  }

  // ------------------------------------------------------------------
  // verifyAndConstructEvent — verify Stripe signature and parse event
  // ------------------------------------------------------------------
  verifyAndConstructEvent(rawBody: Buffer, signature: string): Stripe.Event {
    if (!this.stripe) {
      throw new BadRequestException('Stripe is not configured — STRIPE_SECRET_KEY not set');
    }
    try {
      return this.stripe.webhooks.constructEvent(rawBody, signature, this.webhookSecret);
    } catch (err) {
      this.logger.error('Stripe webhook signature verification failed', err);
      throw new BadRequestException('INVALID_WEBHOOK_SIGNATURE');
    }
  }

  // ------------------------------------------------------------------
  // handleWebhookEvent — route event to appropriate handler
  // ------------------------------------------------------------------
  async handleWebhookEvent(event: Stripe.Event) {
    this.logger.log(`Processing Stripe event: ${event.type} (${event.id})`);

    switch (event.type) {
      case 'invoice.paid':
        return this.handleInvoicePaid(event);

      case 'invoice.payment_failed':
        return this.handleInvoicePaymentFailed(event);

      case 'customer.subscription.updated':
        return this.handleSubscriptionUpdated(event);

      case 'customer.subscription.deleted':
        return this.handleSubscriptionDeleted(event);

      case 'payment_intent.succeeded':
        return this.handlePaymentIntentSucceeded(event);

      case 'payment_intent.payment_failed':
        return this.handlePaymentIntentFailed(event);

      default:
        this.logger.log(`Unhandled Stripe event type: ${event.type}`);
        return { received: true, handled: false, eventType: event.type };
    }
  }

  // ------------------------------------------------------------------
  // invoice.paid
  // ------------------------------------------------------------------
  private async handleInvoicePaid(event: Stripe.Event) {
    const invoice = event.data.object as Stripe.Invoice;
    const stripeCustomerId = invoice.customer as string;

    const tenantId = await this.resolveTenantId(stripeCustomerId);
    if (!tenantId) {
      this.logger.warn(`No tenant found for Stripe customer: ${stripeCustomerId}`);
      return { received: true, handled: false, reason: 'TENANT_NOT_FOUND' };
    }

    // Upsert the invoice record
    await this.prisma.invoice.upsert({
      where: { stripeInvoiceId: invoice.id },
      create: {
        tenantId,
        stripeInvoiceId: invoice.id,
        periodStart: new Date((invoice.period_start ?? 0) * 1000),
        periodEnd: new Date((invoice.period_end ?? 0) * 1000),
        subtotalUsd: (invoice.subtotal ?? 0) / 100,
        taxUsd: (invoice.tax ?? 0) / 100,
        totalUsd: (invoice.total ?? 0) / 100,
        status: 'PAID',
        paidAt: new Date(),
        pdfUrl: invoice.invoice_pdf ?? null,
        lineItems: (invoice.lines?.data ?? []).map((line) => ({
          description: line.description,
          amount: (line.amount ?? 0) / 100,
          currency: line.currency,
        })),
      },
      update: {
        status: 'PAID',
        paidAt: new Date(),
        pdfUrl: invoice.invoice_pdf ?? null,
      },
    });

    // Create billing event
    await this.prisma.billingEvent.create({
      data: {
        tenantId,
        eventType: 'PAYMENT_SUCCEEDED',
        metadata: {
          stripeInvoiceId: invoice.id,
          amountPaid: (invoice.amount_paid ?? 0) / 100,
        },
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'stripe-webhook',
      action: 'INVOICE_PAID',
      entityType: 'INVOICE',
      entityId: invoice.id,
      after: {
        totalUsd: (invoice.total ?? 0) / 100,
        status: 'PAID',
      },
    });

    this.logger.log(`Invoice paid: ${invoice.id} for tenant ${tenantId}`);
    return { received: true, handled: true, eventType: event.type };
  }

  // ------------------------------------------------------------------
  // invoice.payment_failed
  // ------------------------------------------------------------------
  private async handleInvoicePaymentFailed(event: Stripe.Event) {
    const invoice = event.data.object as Stripe.Invoice;
    const stripeCustomerId = invoice.customer as string;

    const tenantId = await this.resolveTenantId(stripeCustomerId);
    if (!tenantId) {
      return { received: true, handled: false, reason: 'TENANT_NOT_FOUND' };
    }

    // Update invoice status
    await this.prisma.invoice.updateMany({
      where: { stripeInvoiceId: invoice.id },
      data: { status: 'UNCOLLECTIBLE' },
    });

    // Create billing event
    await this.prisma.billingEvent.create({
      data: {
        tenantId,
        eventType: 'PAYMENT_FAILED',
        metadata: {
          stripeInvoiceId: invoice.id,
          attemptCount: invoice.attempt_count,
        },
      },
    });

    // Emit billing payment failed event
    await this.kafkaProducer.emit<BillingPaymentFailedPayload>(TOPICS.BILLING_PAYMENT_FAILED, {
      tenantId,
      source: 'subscription-service',
      payload: {
        invoiceId: invoice.id,
        amountUsd: (invoice.amount_due ?? 0) / 100,
        failureReason: invoice.last_finalization_error?.message ?? 'Payment failed',
        attemptCount: invoice.attempt_count ?? 1,
        nextRetryAt: invoice.next_payment_attempt
          ? new Date(invoice.next_payment_attempt * 1000).toISOString()
          : null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'stripe-webhook',
      action: 'INVOICE_PAYMENT_FAILED',
      entityType: 'INVOICE',
      entityId: invoice.id,
      after: {
        status: 'PAYMENT_FAILED',
        attemptCount: invoice.attempt_count,
      },
    });

    this.logger.warn(`Invoice payment failed: ${invoice.id} for tenant ${tenantId}`);
    return { received: true, handled: true, eventType: event.type };
  }

  // ------------------------------------------------------------------
  // customer.subscription.updated
  // ------------------------------------------------------------------
  private async handleSubscriptionUpdated(event: Stripe.Event) {
    const subscription = event.data.object as Stripe.Subscription;
    const stripeCustomerId = subscription.customer as string;

    const tenantId = await this.resolveTenantId(stripeCustomerId);
    if (!tenantId) {
      return { received: true, handled: false, reason: 'TENANT_NOT_FOUND' };
    }

    const stripeStatus = subscription.status;
    const mappedStatus = this.mapStripeStatus(stripeStatus);

    // Update all agent subscriptions linked to this Stripe subscription
    const updatedCount = await this.prisma.agentSubscription.updateMany({
      where: {
        tenantId,
        stripeSubItemId: {
          in: subscription.items.data.map((item) => item.id),
        },
      },
      data: {
        status: mappedStatus,
        ...(mappedStatus === 'CANCELLED' ? { cancelledAt: new Date() } : {}),
      },
    });

    await this.kafkaProducer.emit<BillingSubscriptionActivatedPayload>(
      TOPICS.BILLING_SUBSCRIPTION_ACTIVATED,
      {
        tenantId,
        source: 'subscription-service',
        payload: {
          subscriptionId: subscription.id,
          tenantId,
          agentId: 'all',
          plan: mappedStatus,
          monthlyAmountUsd: 0,
          stripeSubItemId: '',
          billingCycleStart: new Date().toISOString(),
        },
      },
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'stripe-webhook',
      action: 'SUBSCRIPTION_UPDATED',
      entityType: 'AGENT_SUBSCRIPTION',
      entityId: subscription.id,
      after: {
        stripeStatus,
        mappedStatus,
        updatedCount: updatedCount.count,
      },
    });

    this.logger.log(
      `Subscription updated: ${subscription.id} -> ${mappedStatus} for tenant ${tenantId}`,
    );
    return { received: true, handled: true, eventType: event.type };
  }

  // ------------------------------------------------------------------
  // customer.subscription.deleted
  // ------------------------------------------------------------------
  private async handleSubscriptionDeleted(event: Stripe.Event) {
    const subscription = event.data.object as Stripe.Subscription;
    const stripeCustomerId = subscription.customer as string;

    const tenantId = await this.resolveTenantId(stripeCustomerId);
    if (!tenantId) {
      return { received: true, handled: false, reason: 'TENANT_NOT_FOUND' };
    }

    const now = new Date();

    // Cancel all agent subscriptions linked to this Stripe subscription
    await this.prisma.agentSubscription.updateMany({
      where: {
        tenantId,
        stripeSubItemId: {
          in: subscription.items.data.map((item) => item.id),
        },
      },
      data: {
        status: 'CANCELLED',
        cancelledAt: now,
        endsAt: now,
      },
    });

    // Disable associated agent configs
    const affectedSubs = await this.prisma.agentSubscription.findMany({
      where: {
        tenantId,
        stripeSubItemId: {
          in: subscription.items.data.map((item) => item.id),
        },
      },
      select: { agentDefinitionId: true },
    });

    for (const sub of affectedSubs) {
      await this.prisma.agentConfig.updateMany({
        where: {
          tenantId,
          agentDefinitionId: sub.agentDefinitionId,
        },
        data: { isEnabled: false },
      });
    }

    await this.kafkaProducer.emit<AgentStatusChangedPayload>(TOPICS.AGENT_STATUS_CHANGED, {
      tenantId,
      source: 'subscription-service',
      payload: {
        tenantId,
        agentId: 'all',
        instanceId: 'default',
        previousStatus: 'ACTIVE',
        newStatus: 'CANCELLED',
        currentTaskId: null,
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'stripe-webhook',
      action: 'SUBSCRIPTION_DELETED',
      entityType: 'AGENT_SUBSCRIPTION',
      entityId: subscription.id,
      after: { status: 'CANCELLED', cancelledAt: now.toISOString() },
    });

    this.logger.log(`Subscription deleted: ${subscription.id} for tenant ${tenantId}`);
    return { received: true, handled: true, eventType: event.type };
  }

  // ------------------------------------------------------------------
  // payment_intent.succeeded
  // ------------------------------------------------------------------
  private async handlePaymentIntentSucceeded(event: Stripe.Event) {
    const paymentIntent = event.data.object as Stripe.PaymentIntent;
    const stripeCustomerId = paymentIntent.customer as string;

    const tenantId = await this.resolveTenantId(stripeCustomerId);
    if (!tenantId) {
      return { received: true, handled: false, reason: 'TENANT_NOT_FOUND' };
    }

    await this.prisma.billingEvent.create({
      data: {
        tenantId,
        eventType: 'PAYMENT_SUCCEEDED',
        amountUsd: paymentIntent.amount / 100,
        metadata: {
          stripePaymentIntentId: paymentIntent.id,
          currency: paymentIntent.currency,
        },
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'stripe-webhook',
      action: 'PAYMENT_SUCCEEDED',
      entityType: 'PAYMENT',
      entityId: paymentIntent.id,
      after: {
        amountUsd: paymentIntent.amount / 100,
        currency: paymentIntent.currency,
      },
    });

    this.logger.log(`Payment intent succeeded: ${paymentIntent.id} for tenant ${tenantId}`);
    return { received: true, handled: true, eventType: event.type };
  }

  // ------------------------------------------------------------------
  // payment_intent.payment_failed
  // ------------------------------------------------------------------
  private async handlePaymentIntentFailed(event: Stripe.Event) {
    const paymentIntent = event.data.object as Stripe.PaymentIntent;
    const stripeCustomerId = paymentIntent.customer as string;

    const tenantId = await this.resolveTenantId(stripeCustomerId);
    if (!tenantId) {
      return { received: true, handled: false, reason: 'TENANT_NOT_FOUND' };
    }

    const lastError = paymentIntent.last_payment_error;

    await this.prisma.billingEvent.create({
      data: {
        tenantId,
        eventType: 'PAYMENT_FAILED',
        amountUsd: paymentIntent.amount / 100,
        metadata: {
          stripePaymentIntentId: paymentIntent.id,
          errorCode: lastError?.code ?? null,
          errorMessage: lastError?.message ?? null,
        },
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'stripe-webhook',
      action: 'PAYMENT_FAILED',
      entityType: 'PAYMENT',
      entityId: paymentIntent.id,
      after: {
        amountUsd: paymentIntent.amount / 100,
        errorCode: lastError?.code ?? null,
      },
    });

    this.logger.warn(`Payment intent failed: ${paymentIntent.id} for tenant ${tenantId}`);
    return { received: true, handled: true, eventType: event.type };
  }

  // ------------------------------------------------------------------
  // Private helpers
  // ------------------------------------------------------------------

  /**
   * Resolve tenantId from Stripe customerId by looking up the tenant record.
   */
  private async resolveTenantId(stripeCustomerId: string): Promise<string | null> {
    if (!stripeCustomerId) return null;

    const tenant = await this.prisma.tenant.findFirst({
      where: { stripeCustomerId },
      select: { id: true },
    });

    return tenant?.id ?? null;
  }

  /**
   * Map Stripe subscription status to internal subscription status.
   */
  private mapStripeStatus(stripeStatus: string): 'ACTIVE' | 'TRIAL' | 'CANCELLED' | 'PAST_DUE' {
    switch (stripeStatus) {
      case 'active':
        return 'ACTIVE';
      case 'trialing':
        return 'TRIAL';
      case 'canceled':
      case 'unpaid':
      case 'incomplete_expired':
        return 'CANCELLED';
      case 'past_due':
      case 'incomplete':
        return 'PAST_DUE';
      default:
        return 'ACTIVE';
    }
  }
}
