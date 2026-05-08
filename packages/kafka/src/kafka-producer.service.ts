import { Inject, Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ClientKafka } from '@nestjs/microservices';
import { lastValueFrom } from 'rxjs';
import { randomUUID } from 'crypto';
import { BaseEvent } from './events/base-event.interface';

@Injectable()
export class KafkaProducerService implements OnModuleInit {
  private readonly logger = new Logger(KafkaProducerService.name);
  private connected = false;

  constructor(@Inject('KAFKA_SERVICE') private readonly kafka: ClientKafka) {}

  async onModuleInit() {
    try {
      await this.kafka.connect();
      this.connected = true;
      this.logger.log('Kafka producer connected');
    } catch (error) {
      this.logger.warn(
        `Kafka producer connection failed — events will be unavailable: ${error instanceof Error ? error.message : error}`,
      );
    }
  }

  async emit<T>(
    topic: string,
    event: Omit<BaseEvent<T>, 'eventId' | 'timestamp' | 'schemaVersion'> &
      Partial<Pick<BaseEvent<T>, 'eventId' | 'timestamp' | 'schemaVersion'>>,
  ): Promise<void> {
    if (!this.connected) {
      this.logger.warn(`Kafka not connected — dropping event on topic ${topic}`);
      return;
    }

    const enrichedEvent: BaseEvent<T> = {
      schemaVersion: event.schemaVersion ?? '1.0',
      eventId: event.eventId ?? randomUUID(),
      tenantId: event.tenantId,
      timestamp: event.timestamp ?? new Date().toISOString(),
      source: event.source,
      payload: event.payload,
    };

    try {
      await lastValueFrom(
        this.kafka.emit(topic, {
          key: event.tenantId,
          value: JSON.stringify(enrichedEvent),
          headers: {
            tenantId: event.tenantId,
            schemaVersion: enrichedEvent.schemaVersion,
            source: event.source,
          },
        }),
      );
      this.logger.debug(`Event emitted: ${topic} [${enrichedEvent.eventId}]`);
    } catch (error) {
      this.logger.error(
        `Failed to emit event to ${topic}: ${error instanceof Error ? error.message : error}`,
      );
      throw error;
    }
  }

  async emitWithRetry<T>(
    topic: string,
    event: Omit<BaseEvent<T>, 'eventId' | 'timestamp' | 'schemaVersion'> &
      Partial<Pick<BaseEvent<T>, 'eventId' | 'timestamp' | 'schemaVersion'>>,
    options?: { maxRetries?: number; isBusinessError?: boolean },
  ): Promise<void> {
    const maxRetries = options?.maxRetries ?? 3;
    const isBusinessError = options?.isBusinessError ?? false;

    // Business errors go directly to DLQ
    if (isBusinessError) {
      await this.publishToDlq(topic, event, 'BUSINESS_ERROR', 'Non-retryable business error');
      return;
    }

    let lastError: Error | undefined;
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        await this.emit(topic, event);
        return;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        const backoffMs = Math.pow(4, attempt) * 1000; // 1s, 4s, 16s
        this.logger.warn(
          `Retry ${attempt + 1}/${maxRetries} for topic ${topic} after ${backoffMs}ms: ${lastError.message}`,
        );
        await this.sleep(backoffMs);
      }
    }

    // All retries exhausted → publish to DLQ
    await this.publishToDlq(
      topic,
      event,
      'RETRIES_EXHAUSTED',
      lastError?.message ?? 'Unknown error',
    );
  }

  private async publishToDlq<T>(
    originalTopic: string,
    event: Omit<BaseEvent<T>, 'eventId' | 'timestamp' | 'schemaVersion'> &
      Partial<Pick<BaseEvent<T>, 'eventId' | 'timestamp' | 'schemaVersion'>>,
    errorType: string,
    errorMessage: string,
  ): Promise<void> {
    const dlqTopic = `${originalTopic}.dlq`;
    const dlqEvent = {
      ...event,
      payload: {
        originalTopic,
        originalPayload: event.payload,
        errorType,
        errorMessage,
        failedAt: new Date().toISOString(),
      } as unknown as T,
    };

    try {
      await this.emit(dlqTopic, dlqEvent);
      this.logger.error(`Event published to DLQ ${dlqTopic}: ${errorType} — ${errorMessage}`);
    } catch (dlqError) {
      this.logger.error(
        `CRITICAL: Failed to publish to DLQ ${dlqTopic}: ${dlqError instanceof Error ? dlqError.message : dlqError}`,
      );
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
