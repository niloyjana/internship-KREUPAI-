import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface ServiceNowIncident {
  sys_id: string;
  number: string;
  short_description: string;
  description: string;
  state: string;
  priority: string;
  urgency: string;
  impact: string;
  category: string;
  assigned_to: { value: string; display_value: string } | string;
  caller_id: { value: string; display_value: string } | string;
  assignment_group: { value: string; display_value: string } | string;
  opened_at: string;
  resolved_at?: string;
  closed_at?: string;
  sys_created_on: string;
  sys_updated_on: string;
}

export interface CreateIncidentParams {
  short_description: string;
  description?: string;
  urgency?: string;
  impact?: string;
  category?: string;
  assignment_group?: string;
  assigned_to?: string;
  caller_id?: string;
}

export interface UpdateIncidentParams {
  sys_id: string;
  short_description?: string;
  description?: string;
  state?: string;
  urgency?: string;
  impact?: string;
  assignment_group?: string;
  assigned_to?: string;
}

export interface ListIncidentsParams {
  limit?: number;
  offset?: number;
  query?: string;
  state?: string;
  orderBy?: string;
}

export interface ListIncidentsResult {
  result: ServiceNowIncident[];
}

export interface WorkNote {
  sys_id: string;
  value: string;
  sys_created_on: string;
  sys_created_by: string;
}

/**
 * ServiceNow integration connector.
 *
 * Uses plain fetch against the ServiceNow Table API.
 * Authentication is handled via the OAuth Bearer token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class ServiceNowConnector {
  private readonly logger = new Logger(ServiceNowConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('SERVICENOW');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Derive the ServiceNow instance URL from the tokens.
   */
  private getInstanceUrl(tokens: StoredTokens): string {
    return (tokens.instanceUrl as string) || 'https://dev.service-now.com';
  }

  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const instanceUrl = this.getInstanceUrl(tokens);
      const url = new URL(`${instanceUrl}/api/now${path}`);
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
        this.logger.error(`ServiceNow API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`ServiceNow API returned ${res.status}: ${errorBody}`);
      }

      return (await res.json()) as T;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * Create a new incident.
   */
  async createIncident(
    tokens: StoredTokens,
    params: CreateIncidentParams,
  ): Promise<ServiceNowIncident> {
    try {
      const data = await this.request<{ result: ServiceNowIncident }>(
        'POST',
        '/table/incident',
        tokens,
        {
          short_description: params.short_description,
          description: params.description,
          urgency: params.urgency ?? '2',
          impact: params.impact ?? '2',
          category: params.category,
          assignment_group: params.assignment_group,
          assigned_to: params.assigned_to,
          caller_id: params.caller_id,
        },
      );

      this.logger.log(
        `Incident created in ServiceNow — number=${data.result.number} sys_id=${data.result.sys_id}`,
      );
      return data.result;
    } catch (error) {
      this.logger.error(
        'Failed to create incident in ServiceNow',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Get a single incident by sys_id.
   */
  async getIncident(tokens: StoredTokens, sysId: string): Promise<ServiceNowIncident> {
    try {
      const data = await this.request<{ result: ServiceNowIncident }>(
        'GET',
        `/table/incident/${sysId}`,
        tokens,
      );

      this.logger.log(`Fetched incident ${sysId} from ServiceNow`);
      return data.result;
    } catch (error) {
      this.logger.error(
        `Failed to get incident ${sysId} from ServiceNow`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List incidents with optional filters.
   */
  async listIncidents(
    tokens: StoredTokens,
    params: ListIncidentsParams = {},
  ): Promise<ServiceNowIncident[]> {
    const limit = Math.min(params.limit ?? 20, 100);
    const offset = params.offset ?? 0;

    const queryParams: Record<string, string> = {
      sysparm_limit: String(limit),
      sysparm_offset: String(offset),
      sysparm_display_value: 'true',
    };

    if (params.orderBy) {
      queryParams.sysparm_orderby = params.orderBy;
    } else {
      queryParams.sysparm_orderby = 'sys_created_on desc';
    }

    // Build encoded query
    const queryParts: string[] = [];
    if (params.query) queryParts.push(params.query);
    if (params.state) queryParts.push(`state=${params.state}`);

    if (queryParts.length > 0) {
      queryParams.sysparm_query = queryParts.join('^');
    }

    try {
      const data = await this.request<ListIncidentsResult>(
        'GET',
        '/table/incident',
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Listed ${data.result.length} incidents from ServiceNow`);
      return data.result;
    } catch (error) {
      this.logger.error(
        'Failed to list incidents from ServiceNow',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Update an existing incident.
   */
  async updateIncident(
    tokens: StoredTokens,
    params: UpdateIncidentParams,
  ): Promise<ServiceNowIncident> {
    const body: Record<string, unknown> = {};

    if (params.short_description !== undefined) body.short_description = params.short_description;
    if (params.description !== undefined) body.description = params.description;
    if (params.state !== undefined) body.state = params.state;
    if (params.urgency !== undefined) body.urgency = params.urgency;
    if (params.impact !== undefined) body.impact = params.impact;
    if (params.assignment_group !== undefined) body.assignment_group = params.assignment_group;
    if (params.assigned_to !== undefined) body.assigned_to = params.assigned_to;

    try {
      const data = await this.request<{ result: ServiceNowIncident }>(
        'PATCH',
        `/table/incident/${params.sys_id}`,
        tokens,
        body,
      );

      this.logger.log(`Incident updated in ServiceNow — sys_id=${params.sys_id}`);
      return data.result;
    } catch (error) {
      this.logger.error(
        `Failed to update incident ${params.sys_id} in ServiceNow`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Add a work note to an incident.
   */
  async addWorkNote(
    tokens: StoredTokens,
    sysId: string,
    workNote: string,
  ): Promise<ServiceNowIncident> {
    try {
      const data = await this.request<{ result: ServiceNowIncident }>(
        'PATCH',
        `/table/incident/${sysId}`,
        tokens,
        { work_notes: workNote },
      );

      this.logger.log(`Work note added to incident ${sysId} in ServiceNow`);
      return data.result;
    } catch (error) {
      this.logger.error(
        `Failed to add work note to incident ${sysId} in ServiceNow`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
