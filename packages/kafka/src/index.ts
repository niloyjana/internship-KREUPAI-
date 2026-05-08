// Module
export { KafkaModule } from './kafka.module';
export { KafkaProducerService } from './kafka-producer.service';
export { AuditService, PublishAuditParams } from './audit.service';
export { DlqConsumerBase, DlqEventPayload } from './dlq-consumer.base';

// Interfaces
export { KafkaModuleOptions } from './interfaces/kafka-config.interface';
export { BaseEvent } from './events/base-event.interface';

// Topic constants
export { TOPICS, TopicName } from './events/topics';

// Event payloads
export * from './events/payloads/tenant.events';
export * from './events/payloads/agent.events';
export * from './events/payloads/workflow.events';
export * from './events/payloads/escalation.events';
export * from './events/payloads/integration.events';
export * from './events/payloads/billing.events';
export * from './events/payloads/notification.events';
export * from './events/payloads/audit.events';
