import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { google, gmail_v1 } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import { StoredTokens } from '../../token-vault/token-vault.service';
import {
  SendEmailParams,
  SendEmailResult,
  ListEmailsParams,
  ListEmailsResult,
  EmailSummary,
  EmailDetail,
} from './interfaces';

/**
 * Gmail integration connector.
 *
 * Uses the googleapis SDK with an OAuth2 access token
 * retrieved from the encrypted IntegrationConnection record.
 */
@Injectable()
export class GmailConnector {
  private readonly logger = new Logger(GmailConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('GMAIL');

  // ── helpers ─────────────────────────────────────────────

  /**
   * Build an authenticated Gmail client from stored tokens.
   */
  private buildClient(tokens: StoredTokens): gmail_v1.Gmail {
    const oauth2Client = new OAuth2Client();
    oauth2Client.setCredentials({
      access_token: tokens.accessToken,
      refresh_token: tokens.refreshToken,
      token_type: tokens.tokenType ?? 'Bearer',
    });

    return google.gmail({ version: 'v1', auth: oauth2Client });
  }

  /**
   * Extract a named header from a Gmail message payload.
   */
  private getHeader(
    headers: gmail_v1.Schema$MessagePartHeader[] | undefined,
    name: string,
  ): string | undefined {
    return headers?.find((h) => h.name?.toLowerCase() === name.toLowerCase())?.value ?? undefined;
  }

  /**
   * Recursively walk MIME parts to find the body in the preferred content type.
   * Falls back to text/plain when text/html is unavailable.
   */
  private extractBody(payload: gmail_v1.Schema$MessagePart | undefined): {
    body: string;
    contentType: string;
  } {
    if (!payload) {
      return { body: '', contentType: 'text/plain' };
    }

    // Simple single-part message
    if (payload.body?.data) {
      const ct = payload.mimeType ?? 'text/plain';
      return {
        body: Buffer.from(payload.body.data, 'base64url').toString('utf8'),
        contentType: ct,
      };
    }

    // Multipart — look for text/html first, fall back to text/plain
    if (payload.parts) {
      let plainPart: gmail_v1.Schema$MessagePart | undefined;
      for (const part of payload.parts) {
        if (part.mimeType === 'text/html' && part.body?.data) {
          return {
            body: Buffer.from(part.body.data, 'base64url').toString('utf8'),
            contentType: 'text/html',
          };
        }
        if (part.mimeType === 'text/plain' && part.body?.data) {
          plainPart = part;
        }
        // Recurse into nested multipart
        if (part.parts) {
          const nested = this.extractBody(part);
          if (nested.body) return nested;
        }
      }
      if (plainPart?.body?.data) {
        return {
          body: Buffer.from(plainPart.body.data, 'base64url').toString('utf8'),
          contentType: 'text/plain',
        };
      }
    }

    return { body: '', contentType: 'text/plain' };
  }

  // ── public API ──────────────────────────────────────────

  /**
   * Send an email via the Gmail API.
   */
  async sendEmail(tokens: StoredTokens, params: SendEmailParams): Promise<SendEmailResult> {
    const gmail = this.buildClient(tokens);

    const toHeader = params.to;
    const ccHeader = params.cc?.join(', ');
    const bccHeader = params.bcc?.join(', ');
    const contentType = params.contentType ?? 'text/plain';

    // Build RFC 2822 message
    const messageParts = [
      `To: ${toHeader}`,
      `Subject: ${params.subject}`,
      `Content-Type: ${contentType}; charset="UTF-8"`,
      'MIME-Version: 1.0',
    ];

    if (ccHeader) messageParts.splice(1, 0, `Cc: ${ccHeader}`);
    if (bccHeader) messageParts.splice(1, 0, `Bcc: ${bccHeader}`);

    messageParts.push('', params.body);

    const rawMessage = Buffer.from(messageParts.join('\r\n')).toString('base64url');

    try {
      return await this.circuitBreaker.execute(async () => {
        const res = await gmail.users.messages.send({
          userId: 'me',
          requestBody: { raw: rawMessage },
        });

        this.logger.log(`Email sent — messageId=${res.data.id}`);

        return {
          messageId: res.data.id!,
          threadId: res.data.threadId!,
          labelIds: res.data.labelIds ?? [],
        };
      });
    } catch (error) {
      this.logger.error(
        'Failed to send email via Gmail API',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List emails matching an optional query.
   */
  async listEmails(tokens: StoredTokens, params: ListEmailsParams = {}): Promise<ListEmailsResult> {
    const gmail = this.buildClient(tokens);

    const maxResults = Math.min(params.maxResults ?? 10, 100);

    try {
      return await this.circuitBreaker.execute(async () => {
        const listRes = await gmail.users.messages.list({
          userId: 'me',
          q: params.query || undefined,
          maxResults,
          pageToken: params.pageToken || undefined,
        });

        const messageRefs = listRes.data.messages ?? [];
        const messages: EmailSummary[] = [];

        // Fetch minimal metadata for each message
        for (const ref of messageRefs) {
          const msgRes = await gmail.users.messages.get({
            userId: 'me',
            id: ref.id!,
            format: 'metadata',
            metadataHeaders: ['From', 'To', 'Subject', 'Date'],
          });

          const headers = msgRes.data.payload?.headers;

          messages.push({
            id: msgRes.data.id!,
            threadId: msgRes.data.threadId!,
            snippet: msgRes.data.snippet ?? '',
            from: this.getHeader(headers, 'From'),
            to: this.getHeader(headers, 'To'),
            subject: this.getHeader(headers, 'Subject'),
            date: this.getHeader(headers, 'Date'),
            labelIds: msgRes.data.labelIds ?? [],
          });
        }

        return {
          messages,
          nextPageToken: listRes.data.nextPageToken ?? undefined,
          resultSizeEstimate: listRes.data.resultSizeEstimate ?? 0,
        };
      });
    } catch (error) {
      this.logger.error(
        'Failed to list emails via Gmail API',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Get full email details by message ID.
   */
  async getEmail(tokens: StoredTokens, messageId: string): Promise<EmailDetail> {
    const gmail = this.buildClient(tokens);

    try {
      return await this.circuitBreaker.execute(async () => {
        const res = await gmail.users.messages.get({
          userId: 'me',
          id: messageId,
          format: 'full',
        });

        const headers = res.data.payload?.headers;
        const { body, contentType } = this.extractBody(res.data.payload);

        return {
          id: res.data.id!,
          threadId: res.data.threadId!,
          snippet: res.data.snippet ?? '',
          labelIds: res.data.labelIds ?? [],
          from: this.getHeader(headers, 'From'),
          to: this.getHeader(headers, 'To'),
          subject: this.getHeader(headers, 'Subject'),
          date: this.getHeader(headers, 'Date'),
          body,
          contentType,
        };
      });
    } catch (error) {
      this.logger.error(
        `Failed to get email ${messageId} via Gmail API`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
