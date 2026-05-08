import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface JiraIssue {
  id: string;
  key: string;
  self: string;
  fields: {
    summary: string;
    description?: string;
    status: { name: string; id: string };
    issuetype: { name: string; id: string };
    priority?: { name: string; id: string };
    assignee?: { accountId: string; displayName: string; emailAddress?: string };
    reporter?: { accountId: string; displayName: string; emailAddress?: string };
    project: { key: string; name: string };
    created: string;
    updated: string;
    labels?: string[];
  };
}

export interface CreateIssueParams {
  projectKey: string;
  summary: string;
  description?: string;
  issueType: string;
  priority?: string;
  assigneeAccountId?: string;
  labels?: string[];
  customFields?: Record<string, unknown>;
}

export interface UpdateIssueParams {
  issueIdOrKey: string;
  summary?: string;
  description?: string;
  priority?: string;
  assigneeAccountId?: string;
  labels?: string[];
  status?: string;
  customFields?: Record<string, unknown>;
}

export interface SearchIssuesParams {
  jql: string;
  maxResults?: number;
  startAt?: number;
  fields?: string[];
}

export interface SearchIssuesResult {
  issues: JiraIssue[];
  total: number;
  startAt: number;
  maxResults: number;
}

export interface AddCommentParams {
  issueIdOrKey: string;
  body: string;
}

export interface JiraComment {
  id: string;
  self: string;
  body: string;
  author: { accountId: string; displayName: string };
  created: string;
  updated: string;
}

/**
 * Jira integration connector.
 *
 * Uses plain fetch against the Jira Cloud REST API v3.
 * Authentication is handled via the OAuth Bearer token or
 * API token stored in the IntegrationConnection record.
 */
@Injectable()
export class JiraConnector {
  private readonly logger = new Logger(JiraConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('JIRA');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Derive the Jira Cloud site URL from the tokens.
   * Typically stored as `siteUrl` in the token payload.
   */
  private getSiteUrl(tokens: StoredTokens): string {
    return (tokens.siteUrl as string) || 'https://your-domain.atlassian.net';
  }

  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const siteUrl = this.getSiteUrl(tokens);
      const url = new URL(`${siteUrl}/rest/api/3${path}`);
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
        this.logger.error(`Jira API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`Jira API returned ${res.status}: ${errorBody}`);
      }

      if (res.status === 204) {
        return {} as T;
      }

      return (await res.json()) as T;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * Create a new issue in Jira.
   */
  async createIssue(tokens: StoredTokens, params: CreateIssueParams): Promise<JiraIssue> {
    const fields: Record<string, unknown> = {
      project: { key: params.projectKey },
      summary: params.summary,
      issuetype: { name: params.issueType },
    };

    if (params.description) {
      fields.description = {
        type: 'doc',
        version: 1,
        content: [
          {
            type: 'paragraph',
            content: [{ type: 'text', text: params.description }],
          },
        ],
      };
    }

    if (params.priority) fields.priority = { name: params.priority };
    if (params.assigneeAccountId) fields.assignee = { accountId: params.assigneeAccountId };
    if (params.labels) fields.labels = params.labels;

    if (params.customFields) {
      Object.assign(fields, params.customFields);
    }

    try {
      const result = await this.request<JiraIssue>('POST', '/issue', tokens, { fields });

      this.logger.log(`Jira issue created — key=${result.key}`);
      return result;
    } catch (error) {
      this.logger.error(
        'Failed to create issue in Jira',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Get a single issue by ID or key.
   */
  async getIssue(
    tokens: StoredTokens,
    issueIdOrKey: string,
    fields?: string[],
  ): Promise<JiraIssue> {
    const queryParams: Record<string, string> = {};
    if (fields?.length) {
      queryParams.fields = fields.join(',');
    }

    try {
      const issue = await this.request<JiraIssue>(
        'GET',
        `/issue/${issueIdOrKey}`,
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Fetched Jira issue ${issueIdOrKey}`);
      return issue;
    } catch (error) {
      this.logger.error(
        `Failed to get issue ${issueIdOrKey} from Jira`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Search issues using JQL.
   */
  async searchIssues(
    tokens: StoredTokens,
    params: SearchIssuesParams,
  ): Promise<SearchIssuesResult> {
    const maxResults = Math.min(params.maxResults ?? 20, 100);

    try {
      const result = await this.request<SearchIssuesResult>('POST', '/search', tokens, {
        jql: params.jql,
        maxResults,
        startAt: params.startAt ?? 0,
        fields: params.fields ?? [
          'summary',
          'status',
          'issuetype',
          'priority',
          'assignee',
          'reporter',
          'project',
          'created',
          'updated',
          'labels',
        ],
      });

      this.logger.log(`JQL search returned ${result.issues.length} of ${result.total} issues`);
      return result;
    } catch (error) {
      this.logger.error(
        'Failed to search issues in Jira',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Update an existing issue.
   */
  async updateIssue(tokens: StoredTokens, params: UpdateIssueParams): Promise<void> {
    const fields: Record<string, unknown> = {};

    if (params.summary) fields.summary = params.summary;
    if (params.description) {
      fields.description = {
        type: 'doc',
        version: 1,
        content: [
          {
            type: 'paragraph',
            content: [{ type: 'text', text: params.description }],
          },
        ],
      };
    }
    if (params.priority) fields.priority = { name: params.priority };
    if (params.assigneeAccountId) fields.assignee = { accountId: params.assigneeAccountId };
    if (params.labels) fields.labels = params.labels;

    if (params.customFields) {
      Object.assign(fields, params.customFields);
    }

    try {
      await this.request<void>('PUT', `/issue/${params.issueIdOrKey}`, tokens, { fields });

      this.logger.log(`Jira issue updated — ${params.issueIdOrKey}`);

      // Handle status transitions separately if requested
      if (params.status) {
        this.logger.log(
          `Status transition for ${params.issueIdOrKey} to "${params.status}" — requires transition ID lookup`,
        );
      }
    } catch (error) {
      this.logger.error(
        `Failed to update issue ${params.issueIdOrKey} in Jira`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Add a comment to an issue.
   */
  async addComment(tokens: StoredTokens, params: AddCommentParams): Promise<JiraComment> {
    try {
      const result = await this.request<JiraComment>(
        'POST',
        `/issue/${params.issueIdOrKey}/comment`,
        tokens,
        {
          body: {
            type: 'doc',
            version: 1,
            content: [
              {
                type: 'paragraph',
                content: [{ type: 'text', text: params.body }],
              },
            ],
          },
        },
      );

      this.logger.log(`Comment added to Jira issue ${params.issueIdOrKey} — id=${result.id}`);
      return result;
    } catch (error) {
      this.logger.error(
        `Failed to add comment to issue ${params.issueIdOrKey} in Jira`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
