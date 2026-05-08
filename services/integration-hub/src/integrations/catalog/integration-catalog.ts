export interface CatalogEntry {
  provider: string;
  name: string;
  description: string;
  category: string;
  authType: 'oauth2' | 'api_key';
  scopes: string[];
  icon: string;
}

/**
 * Static catalog of available integration providers.
 * No DB query needed — this is built into the service.
 */
export const INTEGRATION_CATALOG: CatalogEntry[] = [
  {
    provider: 'HUBSPOT',
    name: 'HubSpot',
    description: 'CRM platform for marketing, sales, and customer service',
    category: 'CRM',
    authType: 'oauth2',
    scopes: ['contacts.read', 'contacts.write', 'deals.read', 'deals.write'],
    icon: 'hubspot',
  },
  {
    provider: 'SALESFORCE',
    name: 'Salesforce',
    description: 'Enterprise CRM and cloud computing platform',
    category: 'CRM',
    authType: 'oauth2',
    scopes: ['api', 'refresh_token', 'full'],
    icon: 'salesforce',
  },
  {
    provider: 'GMAIL',
    name: 'Gmail',
    description: 'Google email service for sending and receiving messages',
    category: 'Email',
    authType: 'oauth2',
    scopes: ['gmail.readonly', 'gmail.send', 'gmail.modify'],
    icon: 'gmail',
  },
  {
    provider: 'GOOGLE_CALENDAR',
    name: 'Google Calendar',
    description: 'Google scheduling and calendar management service',
    category: 'Calendar',
    authType: 'oauth2',
    scopes: ['calendar', 'calendar.events'],
    icon: 'google-calendar',
  },
  {
    provider: 'OUTLOOK',
    name: 'Microsoft Outlook',
    description: 'Microsoft email and calendar service',
    category: 'Email',
    authType: 'oauth2',
    scopes: ['Mail.Read', 'Mail.Send'],
    icon: 'outlook',
  },
  {
    provider: 'SLACK',
    name: 'Slack',
    description: 'Team messaging and collaboration platform',
    category: 'Communication',
    authType: 'oauth2',
    scopes: ['channels:read', 'chat:write', 'users:read'],
    icon: 'slack',
  },
  {
    provider: 'ODOO',
    name: 'Odoo',
    description: 'Open-source ERP and business management suite',
    category: 'ERP',
    authType: 'api_key',
    scopes: [],
    icon: 'odoo',
  },
  {
    provider: 'QUICKBOOKS',
    name: 'QuickBooks',
    description: 'Intuit accounting and financial management software',
    category: 'Accounting',
    authType: 'oauth2',
    scopes: ['com.intuit.quickbooks.accounting'],
    icon: 'quickbooks',
  },
  {
    provider: 'XERO',
    name: 'Xero',
    description: 'Cloud-based accounting software for small businesses',
    category: 'Accounting',
    authType: 'oauth2',
    scopes: ['openid', 'profile', 'accounting.transactions'],
    icon: 'xero',
  },
  {
    provider: 'JIRA',
    name: 'Jira',
    description: 'Atlassian project tracking and issue management tool',
    category: 'Project Management',
    authType: 'oauth2',
    scopes: ['read:jira-work', 'write:jira-work'],
    icon: 'jira',
  },
];

/**
 * Lookup a catalog entry by provider enum value.
 */
export function getCatalogEntry(provider: string): CatalogEntry | undefined {
  return INTEGRATION_CATALOG.find((entry) => entry.provider === provider);
}
