/**
 * Base envelope for all Kafka events.
 * Every event published to Kafka MUST use this wrapper.
 */
export interface BaseEvent<T = Record<string, unknown>> {
  schemaVersion: string;
  eventId: string;
  tenantId: string;
  timestamp: string;
  source: string;
  payload: T;
}
