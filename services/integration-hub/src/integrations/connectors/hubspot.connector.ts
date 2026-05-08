import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';
import {
  HubSpotListParams,
  HubSpotContact,
  ListContactsResult,
  CreateContactData,
  HubSpotDeal,
  ListDealsResult,
  CreateDealData,
} from './interfaces';

const HUBSPOT_API_BASE = 'https://api.hubapi.com';

/**
 * HubSpot CRM integration connector.
 *
 * Uses plain fetch against the HubSpot v3 REST API.
 * Authentication is handled via the OAuth Bearer token or
 * API key stored in the IntegrationConnection record.
 */
@Injectable()
export class HubSpotConnector {
  private readonly logger = new Logger(HubSpotConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('HUBSPOT');

  // ── helpers ─────────────────────────────────────────────

  /**
   * Build common headers for HubSpot API requests.
   * Supports both OAuth2 Bearer tokens and private-app API keys.
   */
  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    const token = tokens.accessToken || tokens.apiKey;
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Perform a request against the HubSpot API and return parsed JSON.
   * Throws on non-2xx responses with context for debugging.
   */
  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const url = new URL(`${HUBSPOT_API_BASE}${path}`);
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
        this.logger.error(`HubSpot API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`HubSpot API returned ${res.status}: ${errorBody}`);
      }

      return (await res.json()) as T;
    });
  }

  // ── Contacts ────────────────────────────────────────────

  /**
   * List CRM contacts with optional pagination and property selection.
   */
  async listContacts(
    tokens: StoredTokens,
    params: HubSpotListParams = {},
  ): Promise<ListContactsResult> {
    const limit = Math.min(params.limit ?? 10, 100);
    const queryParams: Record<string, string> = {
      limit: String(limit),
    };

    if (params.after) {
      queryParams.after = params.after;
    }
    if (params.properties?.length) {
      queryParams.properties = params.properties.join(',');
    }

    try {
      const data = await this.request<{
        results: HubSpotContact[];
        paging?: { next?: { after: string; link: string } };
        total: number;
      }>('GET', '/crm/v3/objects/contacts', tokens, undefined, queryParams);

      return {
        results: data.results,
        paging: data.paging,
        total: data.total,
      };
    } catch (error) {
      this.logger.error(
        'Failed to list contacts from HubSpot',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Get a single contact by ID.
   */
  async getContact(
    tokens: StoredTokens,
    contactId: string,
    properties?: string[],
  ): Promise<HubSpotContact> {
    const queryParams: Record<string, string> = {};
    if (properties?.length) {
      queryParams.properties = properties.join(',');
    }

    try {
      return await this.request<HubSpotContact>(
        'GET',
        `/crm/v3/objects/contacts/${contactId}`,
        tokens,
        undefined,
        queryParams,
      );
    } catch (error) {
      this.logger.error(
        `Failed to get contact ${contactId} from HubSpot`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Create a new contact in HubSpot CRM.
   */
  async createContact(tokens: StoredTokens, data: CreateContactData): Promise<HubSpotContact> {
    try {
      return await this.request<HubSpotContact>('POST', '/crm/v3/objects/contacts', tokens, {
        properties: data,
      });
    } catch (error) {
      this.logger.error(
        'Failed to create contact in HubSpot',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  // ── Deals ───────────────────────────────────────────────

  /**
   * List CRM deals with optional pagination and property selection.
   */
  async listDeals(tokens: StoredTokens, params: HubSpotListParams = {}): Promise<ListDealsResult> {
    const limit = Math.min(params.limit ?? 10, 100);
    const queryParams: Record<string, string> = {
      limit: String(limit),
    };

    if (params.after) {
      queryParams.after = params.after;
    }
    if (params.properties?.length) {
      queryParams.properties = params.properties.join(',');
    }

    try {
      const data = await this.request<{
        results: HubSpotDeal[];
        paging?: { next?: { after: string; link: string } };
        total: number;
      }>('GET', '/crm/v3/objects/deals', tokens, undefined, queryParams);

      return {
        results: data.results,
        paging: data.paging,
        total: data.total,
      };
    } catch (error) {
      this.logger.error(
        'Failed to list deals from HubSpot',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Create a new deal in HubSpot CRM.
   */
  async createDeal(tokens: StoredTokens, data: CreateDealData): Promise<HubSpotDeal> {
    try {
      return await this.request<HubSpotDeal>('POST', '/crm/v3/objects/deals', tokens, {
        properties: data,
      });
    } catch (error) {
      this.logger.error(
        'Failed to create deal in HubSpot',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
