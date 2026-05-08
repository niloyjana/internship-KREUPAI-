import { Injectable, Logger } from '@nestjs/common';
import { NotificationChannel, Prisma } from '@prisma/client';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  NotificationDeliveredPayload,
} from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { PreferenceItemDto } from './dto/update-preferences.dto';
import { GetHistoryQueryDto } from './dto/get-history.dto';
import { EmailChannel } from './channels/email.channel';

@Injectable()
export class NotificationsService {
  private readonly logger = new Logger(NotificationsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly emailChannel: EmailChannel,
    private readonly audit: AuditService,
  ) {}

  // ----------------------------------------------------------------
  // GET PREFERENCES
  // ----------------------------------------------------------------

  async getPreferences(tenantId: string, userId: string) {
    const preferences = await this.prisma.notificationPreference.findMany({
      where: { tenantId, userId },
      orderBy: { eventType: 'asc' },
    });

    return preferences;
  }

  // ----------------------------------------------------------------
  // UPDATE PREFERENCES
  // ----------------------------------------------------------------

  async updatePreferences(tenantId: string, userId: string, prefs: PreferenceItemDto[]) {
    const results = await Promise.all(
      prefs.map((pref) =>
        this.prisma.notificationPreference.upsert({
          where: {
            tenantId_userId_eventType: {
              tenantId,
              userId,
              eventType: pref.eventType,
            },
          },
          update: {
            channels: pref.channels,
            enabled: pref.enabled ?? true,
          },
          create: {
            tenantId,
            userId,
            eventType: pref.eventType,
            channels: pref.channels,
            enabled: pref.enabled ?? true,
          },
        }),
      ),
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'NOTIFICATION_PREFERENCES_UPDATED',
      entityType: 'NOTIFICATION_PREFERENCE',
      entityId: userId,
      after: { preferences: prefs.map((p) => ({ eventType: p.eventType, channels: p.channels })) },
    });

    return results;
  }

  // ----------------------------------------------------------------
  // GET HISTORY
  // ----------------------------------------------------------------

  async getHistory(tenantId: string, userId: string, query: GetHistoryQueryDto) {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.NotificationLogWhereInput = {
      tenantId,
      userId,
    };

    if (query.channel) {
      where.channel = query.channel;
    }

    if (query.from) {
      where.createdAt = { gte: new Date(query.from) };
    }

    const [items, total] = await Promise.all([
      this.prisma.notificationLog.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.notificationLog.count({ where }),
    ]);

    return {
      items,
      meta: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  // ----------------------------------------------------------------
  // SEND NOTIFICATION
  // ----------------------------------------------------------------

  async sendNotification(
    tenantId: string,
    userId: string,
    eventType: string,
    subject: string | undefined,
    payload: Record<string, unknown>,
  ) {
    const channels: NotificationChannel[] = ['EMAIL'];

    // Check user preferences
    const pref = await this.prisma.notificationPreference.findUnique({
      where: {
        tenantId_userId_eventType: {
          tenantId,
          userId,
          eventType,
        },
      },
    });

    if (pref && !pref.enabled) {
      this.logger.log(`Notification suppressed for user ${userId}, event ${eventType} (disabled)`);
      return null;
    }

    const activeChannels = pref?.channels ?? channels;

    const logs = await Promise.all(
      activeChannels.map(async (channel) => {
        // Create log record with 'pending' status first
        const log = await this.prisma.notificationLog.create({
          data: {
            tenantId,
            userId,
            channel,
            eventType,
            subject,
            status: 'pending',
          },
        });

        // Dispatch to the appropriate channel
        let sent = false;
        if (channel === 'EMAIL') {
          const to = (payload.to as string) || userId;
          const body = (payload.body as string) || `Notification: ${eventType}`;
          sent = await this.emailChannel.send({
            to,
            subject: subject || eventType,
            body,
          });
        } else {
          this.logger.warn(`Unsupported channel "${channel}" — skipping`);
        }

        // Update log status based on delivery result
        const updatedLog = await this.prisma.notificationLog.update({
          where: { id: log.id },
          data: {
            status: sent ? 'sent' : 'failed',
            sentAt: sent ? new Date() : undefined,
          },
        });

        return updatedLog;
      }),
    );

    this.logger.log(
      `Notification processed for user ${userId}, event ${eventType}, channels: ${activeChannels.join(', ')}`,
    );

    // Emit delivery events to Kafka for each successfully sent channel
    for (const log of logs) {
      if (log.status === 'sent') {
        await this.kafkaProducer.emit<NotificationDeliveredPayload>(TOPICS.NOTIFICATION_DELIVERED, {
          tenantId,
          source: 'notification-service',
          payload: {
            notificationId: log.id,
            channel: log.channel,
            status: 'delivered',
            providerRef: null,
          },
        });

        this.audit
          .publishAudit({
            tenantId,
            actorType: 'SYSTEM',
            actorId: 'notification-service',
            action: 'NOTIFICATION_DELIVERED',
            entityType: 'NOTIFICATION_LOG',
            entityId: log.id,
            after: {
              userId,
              channel: log.channel,
              eventType,
              status: 'delivered',
              sentAt: log.sentAt?.toISOString(),
            },
          })
          .catch((err) =>
            this.logger.error(
              `Failed to publish audit NOTIFICATION_DELIVERED: ${err instanceof Error ? err.message : err}`,
            ),
          );
      }
    }

    return logs;
  }
}
