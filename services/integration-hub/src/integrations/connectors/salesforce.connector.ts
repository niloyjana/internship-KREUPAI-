import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface SalesforceContact {
  Id: string;
  FirstName: string;
  LastName: string;
  Email: string;
  Phone?: string;
  AccountId?: string;
  Title?: string;
}

export interface SalesforceOpportunity {
  Id: string;
  Name: string;
  StageName: string;
  Amount?: number;
  CloseDate: string;
  AccountId?: string;
  OwnerId: string;
  Probability?: number;
}

export interface SalesforceLead {
  Id: string;
  FirstName: string;
  LastName: string;
  Email: string;
  Company: string;
  Status: string;
}

export interface CreateLeadParams {
  FirstName: string;
  LastName: string;
  Email: string;
  Company: string;
  Phone?: string;
  Title?: string;
  Status?: string;
}

export interface UpdateRecordParams {
  objectType: string;
  recordId: string;
  fields: Record<string, unknown>;
}

export interface SoqlQueryResult {
  totalSize: number;
  done: boolean;
  records: Record<string, unknown>[];
}

/**
 * Salesforce CRM integration connector.
 *
 * Uses plain fetch against the Salesforce REST API.
 * Authentication is handled via the OAuth Bearer token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class SalesforceConnector {
  private readonly logger = new Logger(SalesforceConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('SALESFORCE');

  // ── helpers ─────────────────────────────────────────────

  /**
   * Build common headers for Salesforce API requests.
   */
  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Derive the Salesforce instance URL from the tokens.
   * Typically stored as `instanceUrl` in the token payload.
   */
  private getInstanceUrl(tokens: StoredTokens): string {
    return (tokens.instanceUrl as string) || 'https://login.salesforce.com';
  }

  /**
   * Perform a request against the Salesforce REST API and return parsed JSON.
   */
  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const instanceUrl = this.getInstanceUrl(tokens);
      const url = `${instanceUrl}/services/data/v59.0${path}`;
      const headers = this.buildHeaders(tokens);

      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(`Salesforce API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`Salesforce API returned ${res.status}: ${errorBody}`);
      }

      // DELETE and some PATCH return 204 No Content
      if (res.status === 204) {
        return {} as T;
      }

      return (await res.json()) as T;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * List CRM contacts.
   */
  async getContacts(
    tokens: StoredTokens,
    params: { limit?: number } = {},
  ): Promise<SalesforceContact[]> {
    const limit = Math.min(params.limit ?? 20, 200);

    try {
      const result = await this.request<SoqlQueryResult>(
        'GET',
        `/query?q=${encodeURIComponent(`SELECT Id, FirstName, LastName, Email, Phone, AccountId, Title FROM Contact LIMIT ${limit}`)}`,
        tokens,
      );

      this.logger.log(`Fetched ${result.records.length} contacts from Salesforce`);
      return result.records as unknown as SalesforceContact[];
    } catch (error) {
      this.logger.error(
        'Failed to get contacts from Salesforce',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List CRM opportunities.
   */
  async getOpportunities(
    tokens: StoredTokens,
    params: { limit?: number; stageName?: string } = {},
  ): Promise<SalesforceOpportunity[]> {
    const limit = Math.min(params.limit ?? 20, 200);
    let soql = `SELECT Id, Name, StageName, Amount, CloseDate, AccountId, OwnerId, Probability FROM Opportunity`;

    if (params.stageName) {
      soql += ` WHERE StageName = '${params.stageName}'`;
    }

    soql += ` LIMIT ${limit}`;

    try {
      const result = await this.request<SoqlQueryResult>(
        'GET',
        `/query?q=${encodeURIComponent(soql)}`,
        tokens,
      );

      this.logger.log(`Fetched ${result.records.length} opportunities from Salesforce`);
      return result.records as unknown as SalesforceOpportunity[];
    } catch (error) {
      this.logger.error(
        'Failed to get opportunities from Salesforce',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Create a new lead in Salesforce.
   */
  async createLead(tokens: StoredTokens, params: CreateLeadParams): Promise<SalesforceLead> {
    try {
      const result = await this.request<{ id: string; success: boolean }>(
        'POST',
        '/sobjects/Lead',
        tokens,
        {
          FirstName: params.FirstName,
          LastName: params.LastName,
          Email: params.Email,
          Company: params.Company,
          Phone: params.Phone,
          Title: params.Title,
          Status: params.Status ?? 'Open - Not Contacted',
        },
      );

      this.logger.log(`Lead created in Salesforce — id=${result.id}`);

      return {
        Id: result.id,
        FirstName: params.FirstName,
        LastName: params.LastName,
        Email: params.Email,
        Company: params.Company,
        Status: params.Status ?? 'Open - Not Contacted',
      };
    } catch (error) {
      this.logger.error(
        'Failed to create lead in Salesforce',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Update a record in Salesforce.
   */
  async updateRecord(tokens: StoredTokens, params: UpdateRecordParams): Promise<void> {
    try {
      await this.request<void>(
        'PATCH',
        `/sobjects/${params.objectType}/${params.recordId}`,
        tokens,
        params.fields,
      );

      this.logger.log(`Record updated in Salesforce — ${params.objectType}/${params.recordId}`);
    } catch (error) {
      this.logger.error(
        `Failed to update ${params.objectType}/${params.recordId} in Salesforce`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Run a SOQL query against Salesforce.
   */
  async runQuery(tokens: StoredTokens, soql: string): Promise<SoqlQueryResult> {
    try {
      const result = await this.request<SoqlQueryResult>(
        'GET',
        `/query?q=${encodeURIComponent(soql)}`,
        tokens,
      );

      this.logger.log(`SOQL query returned ${result.totalSize} records`);
      return result;
    } catch (error) {
      this.logger.error(
        'Failed to run SOQL query',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
