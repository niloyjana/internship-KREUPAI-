import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

/**
 * Slack webhook notification channel.
 *
 * Posts messages to a Slack workspace via an Incoming Webhook URL.
 * Falls back to dev-mode logging when the webhook URL is not configured.
 */
@Injectable()
export class SlackChannel {
  private readonly logger = new Logger(SlackChannel.name);
  private readonly enabled: boolean;
  private readonly webhookUrl: string | undefined;

  constructor(private readonly config: ConfigService) {
    this.webhookUrl = this.config.get<string>('SLACK_WEBHOOK_URL');

    if (this.webhookUrl) {
      this.enabled = true;
      this.logger.log('Slack webhook channel initialized');
    } else {
      this.enabled = false;
      this.logger.warn('SLACK_WEBHOOK_URL not set — Slack channel disabled (dev mode)');
    }
  }

  async send(
    channel: string,
    text: string,
    blocks?: Record<string, unknown>[],
  ): Promise<boolean> {
    if (!this.enabled) {
      this.logger.log(
        `[DEV] Slack channel=${channel} text="${text.slice(0, 80)}" (webhook disabled)`,
      );
      return true; // Return true in dev mode so the flow continues
    }

    try {
      const payload: Record<string, unknown> = {
        channel,
        text,
      };

      if (blocks && blocks.length > 0) {
        payload.blocks = blocks;
      }

      const res = await fetch(this.webhookUrl!, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(`Slack webhook error ${res.status}: ${errorBody}`);
        return false;
      }

      this.logger.log(`Slack message sent to channel=${channel}`);
      return true;
    } catch (error) {
      this.logger.error(
        `Failed to send Slack message to ${channel}: ${error instanceof Error ? error.message : error}`,
      );
      return false;
    }
  }
}
