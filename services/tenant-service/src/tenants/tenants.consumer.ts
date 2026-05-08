import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import {
  TOPICS,
  BaseEvent,
  BillingPaymentFailedPayload,
  BillingSubscriptionActivatedPayload,
} from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';

@Controller()
export class TenantsConsumer {
  private readonly logger = new Logger(TenantsConsumer.name);

  constructor(private readonly prisma: PrismaService) {}

  @EventPattern(TOPICS.BILLING_PAYMENT_FAILED)
  async handleBillingPaymentFailed(
    @Payload() event: BaseEvent<BillingPaymentFailedPayload>,
  ): Promise<void> {
    this.logger.warn(
      `[${event.tenantId}] Billing payment failed: ` +
        `invoiceId=${event.payload.invoiceId}, ` +
        `attemptCount=${event.payload.attemptCount}`,
    );

    // Suspend tenant after 3 failed payment attempts
    if (event.payload.attemptCount >= 3) {
      this.logger.warn(
        `[${event.tenantId}] Suspending tenant after ${event.payload.attemptCount} failed payments`,
      );
      await this.prisma.tenant.update({
        where: { id: event.tenantId },
        data: { status: 'SUSPENDED' },
      });
    }
  }

  @EventPattern(TOPICS.BILLING_SUBSCRIPTION_ACTIVATED)
  async handleBillingSubscriptionActivated(
    @Payload() event: BaseEvent<BillingSubscriptionActivatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Billing subscription activated: ` +
        `agentId=${event.payload.agentId}, ` +
        `plan=${event.payload.plan}`,
    );

    // Ensure tenant status is ACTIVE when subscription is activated
    await this.prisma.tenant.update({
      where: { id: event.tenantId },
      data: { status: 'ACTIVE' },
    });
  }
}
