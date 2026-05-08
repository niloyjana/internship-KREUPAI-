// ─── Enums ────────────────────────────────────────────────────────────────────

export enum IntegrationProvider {
  SLACK = 'slack',
  MICROSOFT_TEAMS = 'microsoft_teams',
  GOOGLE_WORKSPACE = 'google_workspace',
  SALESFORCE = 'salesforce',
  HUBSPOT = 'hubspot',
  JIRA = 'jira',
  GITHUB = 'github',
  ZENDESK = 'zendesk',
  QUICKBOOKS = 'quickbooks',
  SAP = 'sap',
  CUSTOM_WEBHOOK = 'custom_webhook',
}

export enum IntegrationStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
  PENDING_AUTH = 'pending_auth',
  EXPIRED = 'expired',
}

// ─── Interfaces ───────────────────────────────────────────────────────────────

export interface IntegrationConnection {
  id: string;
  tenantId: string;
  provider: IntegrationProvider;
  status: IntegrationStatus;
  displayName: string;
  credentials: Record<string, unknown>; // encrypted at rest
  config: Record<string, unknown>;
  scopes: string[];
  externalAccountId?: string;
  lastSyncAt?: Date;
  tokenExpiresAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface IntegrationLog {
  id: string;
  tenantId: string;
  connectionId: string;
  provider: IntegrationProvider;
  direction: 'inbound' | 'outbound';
  method: string;
  endpoint: string;
  requestPayload?: Record<string, unknown>;
  responsePayload?: Record<string, unknown>;
  statusCode?: number;
  durationMs: number;
  error?: string;
  createdAt: Date;
}
