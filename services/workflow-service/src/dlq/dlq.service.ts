import { Injectable, Logger, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { KafkaProducerService } from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { ListDlqQueryDto } from './dto';

const AUTO_RECOVER_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

@Injectable()
export class DlqService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(DlqService.name);
  private autoRecoverTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
  ) {}

  onModuleInit() {
    this.autoRecoverTimer = setInterval(
      () => this.autoRecover().catch((err) => this.logger.error(`Auto-recover error: ${err}`)),
      AUTO_RECOVER_INTERVAL_MS,
    );
  }

  onModuleDestroy() {
    if (this.autoRecoverTimer) {
      clearInterval(this.autoRecoverTimer);
    }
  }

  /**
   * Persist a failed event to the DLQ database table.
   */
  async persistFailedEvent(
    topic: string,
    key: string | null,
    value: Record<string, unknown>,
    error: string,
    maxRetries = 3,
  ) {
    const entry = await this.prisma.dlqEntry.create({
      data: {
        topic,
        partition: 0,
        offset: '0',
        key: key ?? undefined,
        value: value as Prisma.InputJsonValue,
        headers: {},
        error,
        retryCount: 0,
        maxRetries,
        status: 'pending',
      },
    });

    this.logger.warn(
      `DLQ entry created: id=${entry.id} topic=${topic} error=${error.substring(0, 100)}`,
    );

    return entry;
  }

  /**
   * List DLQ entries with filtering and pagination.
   */
  async listEntries(query: ListDlqQueryDto) {
    const { status, topic, from, to } = query;
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const skip = (page - 1) * pageSize;

    const where: Prisma.DlqEntryWhereInput = {};

    if (status) {
      where.status = status;
    }
    if (topic) {
      where.topic = topic;
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

    const [entries, total] = await Promise.all([
      this.prisma.dlqEntry.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.dlqEntry.count({ where }),
    ]);

    return {
      data: entries,
      meta: {
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  /**
   * Replay a single DLQ entry by re-publishing to the original Kafka topic.
   */
  async replayEntry(id: string) {
    const entry = await this.prisma.dlqEntry.findUnique({ where: { id } });

    if (!entry) {
      return null;
    }

    if (entry.status === 'resolved') {
      return { entry, replayed: false, reason: 'Already resolved' };
    }

    // Update status to retrying
    await this.prisma.dlqEntry.update({
      where: { id },
      data: {
        status: 'retrying',
        retryCount: { increment: 1 },
      },
    });

    try {
      // Re-publish to the original topic
      const payload = entry.value as Record<string, unknown>;
      await this.kafkaProducer.emit(entry.topic, {
        tenantId: (payload.tenantId as string) ?? entry.key ?? 'unknown',
        source: 'dlq-replay',
        payload,
      });

      // Mark as resolved
      await this.prisma.dlqEntry.update({
        where: { id },
        data: {
          status: 'resolved',
          processedAt: new Date(),
        },
      });

      this.logger.log(`DLQ entry replayed: id=${id} topic=${entry.topic}`);
      return { entry, replayed: true };
    } catch (error) {
      // Mark as dead if max retries exceeded
      const updatedEntry = await this.prisma.dlqEntry.findUnique({ where: { id } });
      const newStatus =
        updatedEntry && updatedEntry.retryCount >= updatedEntry.maxRetries ? 'dead' : 'pending';

      await this.prisma.dlqEntry.update({
        where: { id },
        data: { status: newStatus },
      });

      this.logger.error(
        `DLQ replay failed: id=${id} error=${error instanceof Error ? error.message : String(error)}`,
      );

      return {
        entry,
        replayed: false,
        reason: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Get aggregate DLQ statistics by status and topic.
   */
  async getStats() {
    const [byStatus, byTopic, total] = await Promise.all([
      this.prisma.dlqEntry.groupBy({
        by: ['status'],
        _count: { id: true },
      }),
      this.prisma.dlqEntry.groupBy({
        by: ['topic'],
        _count: { id: true },
      }),
      this.prisma.dlqEntry.count(),
    ]);

    return {
      total,
      byStatus: byStatus.reduce(
        (acc, item) => {
          acc[item.status] = item._count.id;
          return acc;
        },
        {} as Record<string, number>,
      ),
      byTopic: byTopic.reduce(
        (acc, item) => {
          acc[item.topic] = item._count.id;
          return acc;
        },
        {} as Record<string, number>,
      ),
    };
  }

  /**
   * Auto-recovery: scheduled task that retries pending DLQ entries
   * older than 5 minutes.
   */
  async autoRecover() {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

    const pendingEntries = await this.prisma.dlqEntry.findMany({
      where: {
        status: 'pending',
        createdAt: { lte: fiveMinutesAgo },
      },
      take: 10,
      orderBy: { createdAt: 'asc' },
    });

    if (pendingEntries.length === 0) return;

    this.logger.log(`Auto-recovering ${pendingEntries.length} DLQ entries`);

    for (const entry of pendingEntries) {
      if (entry.retryCount < entry.maxRetries) {
        await this.replayEntry(entry.id);
      } else {
        await this.prisma.dlqEntry.update({
          where: { id: entry.id },
          data: { status: 'dead' },
        });
      }
    }
  }
}
