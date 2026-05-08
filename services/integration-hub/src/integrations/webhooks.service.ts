import {
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateWebhookDto } from './dto/create-webhook.dto';

export interface WebhookRecord {
  id: string;
  url: string;
  events: string[];
  createdAt: Date;
}

@Injectable()
export class WebhooksService {
  private readonly logger = new Logger(WebhooksService.name);

  constructor(private readonly prisma: PrismaService) {}

  /**
   * Register a new webhook for event notifications.
   *
   * Stores the webhook configuration in the IntegrationWebhook model.
   * The optional `secret` is stored for payload HMAC signing but
   * never returned in list or detail responses.
   */
  async createWebhook(
    tenantId: string,
    dto: CreateWebhookDto,
  ): Promise<WebhookRecord> {
    const webhook = await this.prisma.integrationWebhook.create({
      data: {
        tenantId,
        url: dto.url,
        events: dto.events,
        secret: dto.secret ?? null,
      },
    });

    this.logger.log(
      `Webhook registered: ${webhook.id} → ${dto.url} ` +
        `(tenant: ${tenantId}, events: ${dto.events.join(', ')})`,
    );

    return {
      id: webhook.id,
      url: webhook.url,
      events: webhook.events,
      createdAt: webhook.createdAt,
    };
  }

  /**
   * List all registered webhooks for a tenant.
   */
  async listWebhooks(tenantId: string): Promise<WebhookRecord[]> {
    const webhooks = await this.prisma.integrationWebhook.findMany({
      where: { tenantId },
      select: {
        id: true,
        url: true,
        events: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    return webhooks;
  }

  /**
   * Remove a webhook registration.
   * Throws NotFoundException if the webhook does not exist or does not
   * belong to the specified tenant.
   */
  async deleteWebhook(tenantId: string, webhookId: string): Promise<void> {
    const webhook = await this.prisma.integrationWebhook.findFirst({
      where: { id: webhookId, tenantId },
    });

    if (!webhook) {
      throw new NotFoundException('WEBHOOK_NOT_FOUND');
    }

    await this.prisma.integrationWebhook.delete({
      where: { id: webhookId },
    });

    this.logger.log(
      `Webhook removed: ${webhookId} (tenant: ${tenantId})`,
    );
  }
}
