export interface AuditEventRecordedPayload {
  actorType: 'USER' | 'AI_AGENT' | 'SYSTEM';
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  beforeHash: string | null;
  afterHash: string | null;
  ipAddress: string | null;
  metadata: Record<string, unknown> | null;
}
