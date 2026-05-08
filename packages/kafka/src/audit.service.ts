import { Injectable, Logger } from '@nestjs/common';
import { createHash } from 'crypto';
import { KafkaProducerService } from './kafka-producer.service';
import { TOPICS } from './events/topics';
import { AuditEventRecordedPayload } from './events/payloads/audit.events';

export interface PublishAuditParams {
  tenantId: string;
  actorType: 'USER' | 'AI_AGENT' | 'SYSTEM';
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  ipAddress?: string;
  metadata?: Record<string, unknown>;
}

@Injectable()
export class AuditService {
  private readonly logger = new Logger(AuditService.name);

  constructor(private readonly kafkaProducer: KafkaProducerService) {}

  async publishAudit(params: PublishAuditParams): Promise<void> {
    try {
      await this.kafkaProducer.emit<AuditEventRecordedPayload>(TOPICS.AUDIT_EVENT_RECORDED, {
        tenantId: params.tenantId,
        source: 'audit-service',
        payload: {
          actorType: params.actorType,
          actorId: params.actorId,
          action: params.action,
          entityType: params.entityType,
          entityId: params.entityId,
          beforeHash: params.before ? this.hashJson(params.before) : null,
          afterHash: params.after ? this.hashJson(params.after) : null,
          ipAddress: params.ipAddress ?? null,
          metadata: params.metadata ?? null,
        },
      });
    } catch (error) {
      // Log but do not throw — audit failures must not break business flows
      this.logger.error(
        `Failed to publish audit event [${params.action}]: ${error instanceof Error ? error.message : error}`,
      );
    }
  }

  private hashJson(data: Record<string, unknown>): string {
    return createHash('sha256').update(JSON.stringify(data)).digest('hex');
  }
}
