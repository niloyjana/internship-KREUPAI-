import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface QBInvoice {
  Id: string;
  DocNumber: string;
  TxnDate: string;
  DueDate?: string;
  TotalAmt: number;
  Balance: number;
  CustomerRef: { value: string; name: string };
  Line: Array<{
    Id: string;
    Description?: string;
    Amount: number;
    DetailType: string;
  }>;
  EmailStatus?: string;
  PrintStatus?: string;
}

export interface CreateInvoiceParams {
  customerRef: { value: string; name?: string };
  line: Array<{
    amount: number;
    description?: string;
    detailType: string;
    salesItemLineDetail?: {
      itemRef: { value: string; name?: string };
      qty?: number;
      unitPrice?: number;
    };
  }>;
  dueDate?: string;
  txnDate?: string;
}

export interface QBCustomer {
  Id: string;
  DisplayName: string;
  PrimaryEmailAddr?: { Address: string };
  PrimaryPhone?: { FreeFormNumber: string };
  CompanyName?: string;
  Balance: number;
  Active: boolean;
}

export interface QBAccount {
  Id: string;
  Name: string;
  AccountType: string;
  AccountSubType?: string;
  CurrentBalance: number;
  Active: boolean;
  Classification?: string;
}

export interface QBQueryResult<T> {
  QueryResponse: {
    [key: string]: T[] | number | undefined;
    startPosition?: number;
    maxResults?: number;
    totalCount?: number;
  };
}

const QB_API_BASE = 'https://quickbooks.api.intuit.com/v3';

/**
 * QuickBooks Online integration connector.
 *
 * Uses plain fetch against the QuickBooks Online Accounting API v3.
 * Authentication is handled via the OAuth Bearer token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class QuickBooksConnector {
  private readonly logger = new Logger(QuickBooksConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('QUICKBOOKS');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Derive the QuickBooks company (realm) ID from the tokens.
   */
  private getRealmId(tokens: StoredTokens): string {
    return (tokens.realmId as string) || '';
  }

  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const realmId = this.getRealmId(tokens);
      const url = new URL(`${QB_API_BASE}/company/${realmId}${path}`);

      // QuickBooks requires minorversion param
      url.searchParams.set('minorversion', '65');

      if (queryParams) {
        for (const [key, value] of Object.entries(queryParams)) {
          url.searchParams.set(key, value);
        }
      }

      const headers = this.buildHeaders(tokens);

      const res = await fetch(url.toString(), {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(`QuickBooks API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`QuickBooks API returned ${res.status}: ${errorBody}`);
      }

      return (await res.json()) as T;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * List invoices.
   */
  async getInvoices(
    tokens: StoredTokens,
    params: { maxResults?: number; startPosition?: number } = {},
  ): Promise<QBInvoice[]> {
    const maxResults = Math.min(params.maxResults ?? 20, 1000);
    const startPosition = params.startPosition ?? 1;

    const query = `SELECT * FROM Invoice STARTPOSITION ${startPosition} MAXRESULTS ${maxResults}`;

    try {
      const data = await this.request<QBQueryResult<QBInvoice>>(
        'GET',
        '/query',
        tokens,
        undefined,
        { query },
      );

      const invoices = (data.QueryResponse.Invoice as QBInvoice[] | undefined) ?? [];
      this.logger.log(`Fetched ${invoices.length} invoices from QuickBooks`);
      return invoices;
    } catch (error) {
      this.logger.error(
        'Failed to get invoices from QuickBooks',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Create a new invoice.
   */
  async createInvoice(tokens: StoredTokens, params: CreateInvoiceParams): Promise<QBInvoice> {
    const body: Record<string, unknown> = {
      CustomerRef: params.customerRef,
      Line: params.line.map((l) => ({
        Amount: l.amount,
        Description: l.description,
        DetailType: l.detailType,
        SalesItemLineDetail: l.salesItemLineDetail
          ? {
              ItemRef: l.salesItemLineDetail.itemRef,
              Qty: l.salesItemLineDetail.qty,
              UnitPrice: l.salesItemLineDetail.unitPrice,
            }
          : undefined,
      })),
    };

    if (params.dueDate) body.DueDate = params.dueDate;
    if (params.txnDate) body.TxnDate = params.txnDate;

    try {
      const data = await this.request<{ Invoice: QBInvoice }>('POST', '/invoice', tokens, body);

      this.logger.log(`Invoice created in QuickBooks — Id=${data.Invoice.Id}`);
      return data.Invoice;
    } catch (error) {
      this.logger.error(
        'Failed to create invoice in QuickBooks',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List customers.
   */
  async getCustomers(
    tokens: StoredTokens,
    params: { maxResults?: number; startPosition?: number } = {},
  ): Promise<QBCustomer[]> {
    const maxResults = Math.min(params.maxResults ?? 20, 1000);
    const startPosition = params.startPosition ?? 1;

    const query = `SELECT * FROM Customer STARTPOSITION ${startPosition} MAXRESULTS ${maxResults}`;

    try {
      const data = await this.request<QBQueryResult<QBCustomer>>(
        'GET',
        '/query',
        tokens,
        undefined,
        { query },
      );

      const customers = (data.QueryResponse.Customer as QBCustomer[] | undefined) ?? [];
      this.logger.log(`Fetched ${customers.length} customers from QuickBooks`);
      return customers;
    } catch (error) {
      this.logger.error(
        'Failed to get customers from QuickBooks',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List accounts (Chart of Accounts).
   */
  async getAccounts(
    tokens: StoredTokens,
    params: { maxResults?: number; accountType?: string } = {},
  ): Promise<QBAccount[]> {
    const maxResults = Math.min(params.maxResults ?? 50, 1000);
    let query = `SELECT * FROM Account`;

    if (params.accountType) {
      query += ` WHERE AccountType = '${params.accountType}'`;
    }

    query += ` MAXRESULTS ${maxResults}`;

    try {
      const data = await this.request<QBQueryResult<QBAccount>>(
        'GET',
        '/query',
        tokens,
        undefined,
        { query },
      );

      const accounts = (data.QueryResponse.Account as QBAccount[] | undefined) ?? [];
      this.logger.log(`Fetched ${accounts.length} accounts from QuickBooks`);
      return accounts;
    } catch (error) {
      this.logger.error(
        'Failed to get accounts from QuickBooks',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Run a custom QuickBooks query.
   */
  async queryEntities(
    tokens: StoredTokens,
    query: string,
  ): Promise<QBQueryResult<Record<string, unknown>>> {
    try {
      const data = await this.request<QBQueryResult<Record<string, unknown>>>(
        'GET',
        '/query',
        tokens,
        undefined,
        { query },
      );

      this.logger.log(`QuickBooks query executed successfully`);
      return data;
    } catch (error) {
      this.logger.error(
        'Failed to run QuickBooks query',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
