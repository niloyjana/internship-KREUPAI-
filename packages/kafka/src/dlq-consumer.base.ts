import { Logger } from '@nestjs/common';
import { Payload } from '@nestjs/microservices';
import { BaseEvent } from './events/base-event.interface';

export interface DlqEventPayload {
  originalTopic: string;
  originalPayload: Record<string, unknown>;
  errorType: string;
  errorMessage: string;
  failedAt: string;
}

export abstract class DlqConsumerBase {
  protected abstract readonly logger: Logger;

  protected handleDlqEvent(@Payload() event: BaseEvent<DlqEventPayload>, dlqTopic: string): void {
    this.logger.error(
      `[DLQ][${event.tenantId}] ${dlqTopic}: ` +
        `originalTopic=${event.payload.originalTopic}, ` +
        `errorType=${event.payload.errorType}, ` +
        `error=${event.payload.errorMessage}, ` +
        `failedAt=${event.payload.failedAt}`,
    );

    // In production: persist to DLQ table, alert PagerDuty if rate > 1%
    // For now: structured logging is sufficient
  }
}
