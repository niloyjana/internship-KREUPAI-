import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface XeroInvoice {
  InvoiceID: string;
  InvoiceNumber: string;
  Type: 'ACCREC' | 'ACCPAY';
  Status: string;
  Contact: { ContactID: string; Name: string };
  Date: string;
  DueDate: string;
  Total: number;
  AmountDue: number;
  AmountPaid: number;
  CurrencyCode: string;
  LineItems: Array<{
    LineItemID: string;
    Description: string;
    Quantity: number;
    UnitAmount: number;
    LineAmount: number;
    AccountCode?: string;
    TaxType?: string;
  }>;
}

export interface CreateXeroInvoiceParams {
  type: 'ACCREC' | 'ACCPAY';
  contact: { contactID: string };
  lineItems: Array<{
    description: string;
    quantity: number;
    unitAmount: number;
    accountCode?: string;
    taxType?: string;
  }>;
  date?: string;
  dueDate?: string;
  reference?: string;
  status?: string;
}

export interface XeroContact {
  ContactID: string;
  Name: string;
  FirstName?: string;
  LastName?: string;
  EmailAddress?: string;
  Phones?: Array<{ PhoneType: string; PhoneNumber: string }>;
  IsCustomer: boolean;
  IsSupplier: boolean;
  ContactStatus: string;
}

export interface XeroAccount {
  AccountID: string;
  Code: string;
  Name: string;
  Type: string;
  Class: string;
  Status: string;
  TaxType?: string;
  Description?: string;
}

export interface XeroBankTransaction {
  BankTransactionID: string;
  Type: string;
  Contact: { ContactID: string; Name: string };
  Date: string;
  Status: string;
  Total: number;
  BankAccount: { AccountID: string; Code: string; Name: string };
  LineItems: Array<{
    Description: string;
    Quantity: number;
    UnitAmount: number;
    LineAmount: number;
    AccountCode?: string;
  }>;
}

const XERO_API_BASE = 'https://api.xero.com/api.xro/2.0';

/**
 * Xero accounting integration connector.
 *
 * Uses plain fetch against the Xero Accounting API v2.0.
 * Authentication is handled via the OAuth2 Bearer token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class XeroConnector {
  private readonly logger = new Logger(XeroConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('XERO');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    // Xero requires the tenant ID in the header
    const tenantId = tokens.xeroTenantId as string;
    if (tenantId) {
      headers['Xero-Tenant-Id'] = tenantId;
    }

    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const url = new URL(`${XERO_API_BASE}${path}`);
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
        this.logger.error(`Xero API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`Xero API returned ${res.status}: ${errorBody}`);
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
    params: { page?: number; where?: string; statuses?: string[] } = {},
  ): Promise<XeroInvoice[]> {
    const queryParams: Record<string, string> = {};

    if (params.page) queryParams.page = String(params.page);
    if (params.where) queryParams.where = params.where;
    if (params.statuses?.length) {
      queryParams.Statuses = params.statuses.join(',');
    }

    try {
      const data = await this.request<{ Invoices: XeroInvoice[] }>(
        'GET',
        '/Invoices',
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Fetched ${data.Invoices.length} invoices from Xero`);
      return data.Invoices;
    } catch (error) {
      this.logger.error(
        'Failed to get invoices from Xero',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Create a new invoice.
   */
  async createInvoice(tokens: StoredTokens, params: CreateXeroInvoiceParams): Promise<XeroInvoice> {
    const body = {
      Type: params.type,
      Contact: { ContactID: params.contact.contactID },
      LineItems: params.lineItems.map((li) => ({
        Description: li.description,
        Quantity: li.quantity,
        UnitAmount: li.unitAmount,
        AccountCode: li.accountCode,
        TaxType: li.taxType,
      })),
      Date: params.date,
      DueDate: params.dueDate,
      Reference: params.reference,
      Status: params.status ?? 'DRAFT',
    };

    try {
      const data = await this.request<{ Invoices: XeroInvoice[] }>(
        'POST',
        '/Invoices',
        tokens,
        body,
      );

      const invoice = data.Invoices[0];
      this.logger.log(`Invoice created in Xero — InvoiceID=${invoice.InvoiceID}`);
      return invoice;
    } catch (error) {
      this.logger.error(
        'Failed to create invoice in Xero',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List contacts.
   */
  async getContacts(
    tokens: StoredTokens,
    params: { page?: number; where?: string; includeArchived?: boolean } = {},
  ): Promise<XeroContact[]> {
    const queryParams: Record<string, string> = {};

    if (params.page) queryParams.page = String(params.page);
    if (params.where) queryParams.where = params.where;
    if (params.includeArchived) queryParams.includeArchived = 'true';

    try {
      const data = await this.request<{ Contacts: XeroContact[] }>(
        'GET',
        '/Contacts',
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Fetched ${data.Contacts.length} contacts from Xero`);
      return data.Contacts;
    } catch (error) {
      this.logger.error(
        'Failed to get contacts from Xero',
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
    params: { where?: string; classType?: string } = {},
  ): Promise<XeroAccount[]> {
    const queryParams: Record<string, string> = {};

    if (params.where) queryParams.where = params.where;
    if (params.classType) {
      queryParams.where = `Class=="${params.classType}"`;
    }

    try {
      const data = await this.request<{ Accounts: XeroAccount[] }>(
        'GET',
        '/Accounts',
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Fetched ${data.Accounts.length} accounts from Xero`);
      return data.Accounts;
    } catch (error) {
      this.logger.error(
        'Failed to get accounts from Xero',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List bank transactions.
   */
  async getBankTransactions(
    tokens: StoredTokens,
    params: { page?: number; where?: string } = {},
  ): Promise<XeroBankTransaction[]> {
    const queryParams: Record<string, string> = {};

    if (params.page) queryParams.page = String(params.page);
    if (params.where) queryParams.where = params.where;

    try {
      const data = await this.request<{ BankTransactions: XeroBankTransaction[] }>(
        'GET',
        '/BankTransactions',
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Fetched ${data.BankTransactions.length} bank transactions from Xero`);
      return data.BankTransactions;
    } catch (error) {
      this.logger.error(
        'Failed to get bank transactions from Xero',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
