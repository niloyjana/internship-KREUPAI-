import { Injectable, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { DlqConsumerBase, DlqEventPayload } from '@adwp/kafka';
import { BaseEvent } from '@adwp/kafka';
import { DlqService } from './dlq.service';

/**
 * Concrete DLQ consumer that persists failed events to the database
 * via DlqService. Extends the abstract DlqConsumerBase from @adwp/kafka.
 */
@Injectable()
export class DlqConsumer extends DlqConsumerBase {
  protected readonly logger = new Logger(DlqConsumer.name);

  constructor(private readonly dlqService: DlqService) {
    super();
  }

  /**
   * Handles DLQ events from any *.dlq topic.
   * Persists the failed event to the DlqEntry database table.
   */
  @EventPattern('*.dlq')
  async handleDlq(@Payload() event: BaseEvent<DlqEventPayload>) {
    // Call parent for structured logging
    this.handleDlqEvent(event, event.payload.originalTopic);

    // Persist to database
    try {
      await this.dlqService.persistFailedEvent(
        event.payload.originalTopic,
        event.tenantId ?? null,
        event.payload.originalPayload,
        `${event.payload.errorType}: ${event.payload.errorMessage}`,
      );
    } catch (error) {
      this.logger.error(
        `Failed to persist DLQ event: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }
}
