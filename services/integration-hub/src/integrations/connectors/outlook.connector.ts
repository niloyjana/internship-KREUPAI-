import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface OutlookEmailMessage {
  id: string;
  subject: string;
  bodyPreview: string;
  body: { contentType: string; content: string };
  from: { emailAddress: { name: string; address: string } };
  toRecipients: Array<{ emailAddress: { name: string; address: string } }>;
  receivedDateTime: string;
  isRead: boolean;
  parentFolderId: string;
}

export interface OutlookSendEmailParams {
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body: string;
  contentType?: 'Text' | 'HTML';
}

export interface OutlookListEmailsParams {
  folderId?: string;
  top?: number;
  skip?: number;
  filter?: string;
  select?: string[];
}

export interface OutlookListEmailsResult {
  value: OutlookEmailMessage[];
  nextLink?: string;
}

export interface OutlookMailFolder {
  id: string;
  displayName: string;
  parentFolderId?: string;
  childFolderCount: number;
  totalItemCount: number;
  unreadItemCount: number;
}

const MS_GRAPH_BASE = 'https://graph.microsoft.com/v1.0';

/**
 * Microsoft Outlook integration connector (MS Graph API).
 *
 * Uses plain fetch against the Microsoft Graph REST API.
 * Authentication is handled via the OAuth Bearer token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class OutlookConnector {
  private readonly logger = new Logger(OutlookConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('OUTLOOK');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const url = new URL(`${MS_GRAPH_BASE}${path}`);
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
        this.logger.error(`MS Graph API error — ${method} ${path} ${res.status}: ${errorBody}`);
        throw new Error(`MS Graph API returned ${res.status}: ${errorBody}`);
      }

      if (res.status === 202 || res.status === 204) {
        return {} as T;
      }

      return (await res.json()) as T;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * Send an email via Microsoft Graph.
   */
  async sendEmail(tokens: StoredTokens, params: OutlookSendEmailParams): Promise<void> {
    const message = {
      subject: params.subject,
      body: {
        contentType: params.contentType ?? 'HTML',
        content: params.body,
      },
      toRecipients: params.to.map((addr) => ({
        emailAddress: { address: addr },
      })),
      ccRecipients: params.cc?.map((addr) => ({
        emailAddress: { address: addr },
      })),
      bccRecipients: params.bcc?.map((addr) => ({
        emailAddress: { address: addr },
      })),
    };

    try {
      await this.request<void>('POST', '/me/sendMail', tokens, { message, saveToSentItems: true });

      this.logger.log(`Outlook email sent — subject="${params.subject}"`);
    } catch (error) {
      this.logger.error(
        'Failed to send email via MS Graph',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List emails from the user's mailbox.
   */
  async listEmails(
    tokens: StoredTokens,
    params: OutlookListEmailsParams = {},
  ): Promise<OutlookListEmailsResult> {
    const top = Math.min(params.top ?? 10, 100);
    const folderPath = params.folderId
      ? `/me/mailFolders/${params.folderId}/messages`
      : '/me/messages';

    const queryParams: Record<string, string> = {
      $top: String(top),
      $orderby: 'receivedDateTime desc',
    };

    if (params.skip) queryParams.$skip = String(params.skip);
    if (params.filter) queryParams.$filter = params.filter;
    if (params.select?.length) {
      queryParams.$select = params.select.join(',');
    }

    try {
      const data = await this.request<{
        value: OutlookEmailMessage[];
        '@odata.nextLink'?: string;
      }>('GET', folderPath, tokens, undefined, queryParams);

      this.logger.log(`Listed ${data.value.length} emails from Outlook`);

      return {
        value: data.value,
        nextLink: data['@odata.nextLink'],
      };
    } catch (error) {
      this.logger.error(
        'Failed to list emails via MS Graph',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Get a single email by its message ID.
   */
  async getEmail(tokens: StoredTokens, messageId: string): Promise<OutlookEmailMessage> {
    try {
      const message = await this.request<OutlookEmailMessage>(
        'GET',
        `/me/messages/${messageId}`,
        tokens,
      );

      this.logger.log(`Fetched email ${messageId} from Outlook`);
      return message;
    } catch (error) {
      this.logger.error(
        `Failed to get email ${messageId} via MS Graph`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List mail folders.
   */
  async listFolders(tokens: StoredTokens): Promise<OutlookMailFolder[]> {
    try {
      const data = await this.request<{ value: OutlookMailFolder[] }>(
        'GET',
        '/me/mailFolders',
        tokens,
      );

      this.logger.log(`Listed ${data.value.length} mail folders from Outlook`);
      return data.value;
    } catch (error) {
      this.logger.error(
        'Failed to list mail folders via MS Graph',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
