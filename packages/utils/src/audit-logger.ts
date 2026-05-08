import { randomUUID } from 'crypto';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AuditEvent {
  id: string;
  tenantId: string;
  actorType: string;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  beforeJson?: unknown;
  afterJson?: unknown;
  metadata?: unknown;
  ipAddress?: string;
  timestamp: string; // ISO 8601
}

export interface CreateAuditEventParams {
  tenantId: string;
  actorType: string;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  beforeJson?: unknown;
  afterJson?: unknown;
  metadata?: unknown;
  ipAddress?: string;
}

// ─── Functions ────────────────────────────────────────────────────────────────

/**
 * Creates a structured audit event object.
 *
 * @param params - The audit event parameters
 * @returns A fully populated AuditEvent with generated id and timestamp
 */
export function createAuditEvent(params: CreateAuditEventParams): AuditEvent {
  return {
    id: randomUUID(),
    tenantId: params.tenantId,
    actorType: params.actorType,
    actorId: params.actorId,
    action: params.action,
    entityType: params.entityType,
    entityId: params.entityId,
    beforeJson: params.beforeJson,
    afterJson: params.afterJson,
    metadata: params.metadata,
    ipAddress: params.ipAddress,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Publishes an audit event.
 *
 * This is a placeholder implementation that logs the event to console.
 * Kafka integration will be added in a later phase.
 *
 * @param event - The audit event to publish
 */
export async function publishAuditEvent(event: AuditEvent): Promise<void> {
  // TODO: Replace with Kafka producer when available
  console.log('[AUDIT]', JSON.stringify(event));
}
