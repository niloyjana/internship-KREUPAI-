/**
 * Types for third-party integration connections and catalog.
 */

export type IntegrationProvider =
  | 'HUBSPOT'
  | 'SALESFORCE'
  | 'GMAIL'
  | 'GOOGLE_CALENDAR'
  | 'OUTLOOK'
  | 'OUTLOOK_CALENDAR'
  | 'SLACK'
  | 'ODOO'
  | 'QUICKBOOKS'
  | 'XERO'
  | 'JIRA'
  | 'FRESHDESK'
  | 'SAP'
  | 'ORACLE'
  | 'NETSUITE'
  | 'WORKDAY'
  | 'BAMBOOHR'
  | 'GREENHOUSE'
  | 'LEVER'
  | 'SERVICENOW'
  | 'GENERIC_REST'
  | 'WEBHOOK'
  | 'SFTP'
  | 'CUSTOM';

export type IntegrationStatus =
  | 'CONNECTED'
  | 'DISCONNECTED'
  | 'ERROR'
  | 'PENDING_AUTH'
  | 'EXPIRED';

export type IntegrationCategory =
  | 'CRM'
  | 'Email'
  | 'Calendar'
  | 'Accounting'
  | 'HR'
  | 'Support'
  | 'Productivity'
  | 'ERP';

export type IntegrationAuthType = 'oauth2' | 'api_key';

export interface CatalogProvider {
  provider: IntegrationProvider;
  name: string;
  description: string;
  category: IntegrationCategory;
  authType: IntegrationAuthType;
  availableScopes: string[];
  iconName: string;
}

export interface IntegrationConnection {
  id: string;
  provider: IntegrationProvider;
  name: string;
  status: IntegrationStatus;
  authType: string;
  scopesGranted: string[];
  lastSyncAt: string | null;
  lastErrorAt: string | null;
  lastErrorMessage: string | null;
  createdAt: string;
}

export interface IntegrationLog {
  id: string;
  connectionId: string;
  direction: string;
  operation: string;
  status: string;
  httpMethod: string | null;
  responseStatus: number | null;
  durationMs: number | null;
  errorMessage: string | null;
  createdAt: string;
}

export interface ConnectionTestResult {
  status: 'healthy' | 'unhealthy';
  responseTimeMs: number;
  permissionsValid: boolean;
}

export interface CreateConnectionPayload {
  provider: IntegrationProvider;
  name: string;
  authType: IntegrationAuthType;
  scopes?: string[];
  apiKey?: string;
}

export interface CreateConnectionResponse {
  connection: IntegrationConnection;
  authUrl?: string;
}

export interface ConnectionLogsParams {
  page?: number;
  pageSize?: number;
}

export interface ConnectionLogsResponse {
  logs: IntegrationLog[];
  meta: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  };
}
