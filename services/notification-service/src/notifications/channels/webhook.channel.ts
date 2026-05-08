import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createHmac } from 'crypto';

/**
 * Generic outbound webhook notification channel.
 *
 * Sends HTTP requests to arbitrary URLs with an optional HMAC-SHA256
 * signature header for security verification on the receiving end.
 */
@Injectable()
export class WebhookChannel {
  private readonly logger = new Logger(WebhookChannel.name);
  private readonly signingSecret: string | undefined;

  constructor(private readonly config: ConfigService) {
    this.signingSecret = this.config.get<string>('WEBHOOK_SIGNING_SECRET');

    if (this.signingSecret) {
      this.logger.log('Webhook channel initialized with HMAC signing');
    } else {
      this.logger.log('Webhook channel initialized (no HMAC signing secret configured)');
    }
  }

  async send(
    url: string,
    payload: Record<string, unknown>,
    headers?: Record<string, string>,
    method: 'POST' | 'PUT' | 'PATCH' = 'POST',
  ): Promise<boolean> {
    try {
      const body = JSON.stringify(payload);

      const requestHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        ...headers,
      };

      // Add HMAC-SHA256 signature if signing secret is configured
      if (this.signingSecret) {
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const signaturePayload = `${timestamp}.${body}`;
        const signature = createHmac('sha256', this.signingSecret)
          .update(signaturePayload)
          .digest('hex');

        requestHeaders['X-Webhook-Timestamp'] = timestamp;
        requestHeaders['X-Webhook-Signature'] = `sha256=${signature}`;
      }

      const res = await fetch(url, {
        method,
        headers: requestHeaders,
        body,
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(
          `Webhook ${method} ${url} returned ${res.status}: ${errorBody.slice(0, 200)}`,
        );
        return false;
      }

      this.logger.log(`Webhook delivered — ${method} ${url} (${res.status})`);
      return true;
    } catch (error) {
      this.logger.error(
        `Failed to deliver webhook to ${url}: ${error instanceof Error ? error.message : error}`,
      );
      return false;
    }
  }
}
