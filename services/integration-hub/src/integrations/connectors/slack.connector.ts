import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface SlackMessage {
  ok: boolean;
  channel: string;
  ts: string;
  message: {
    text: string;
    user?: string;
    ts: string;
    type: string;
  };
}

export interface SlackChannel {
  id: string;
  name: string;
  is_channel: boolean;
  is_private: boolean;
  is_archived: boolean;
  num_members: number;
  topic: { value: string };
  purpose: { value: string };
}

export interface ListChannelsResult {
  channels: SlackChannel[];
  nextCursor?: string;
}

export interface ChannelHistoryMessage {
  type: string;
  user?: string;
  text: string;
  ts: string;
  thread_ts?: string;
  reply_count?: number;
}

export interface ChannelHistoryResult {
  messages: ChannelHistoryMessage[];
  hasMore: boolean;
  nextCursor?: string;
}

export interface SendMessageParams {
  channel: string;
  text: string;
  blocks?: Record<string, unknown>[];
  threadTs?: string;
}

const SLACK_API_BASE = 'https://slack.com/api';

/**
 * Slack integration connector.
 *
 * Uses plain fetch against the Slack Web API.
 * Authentication is handled via the OAuth Bot token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class SlackConnector {
  private readonly logger = new Logger(SlackConnector.name);
  private readonly circuitBreaker = CircuitBreakerRegistry.getInstance().getBreaker('SLACK');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json; charset=utf-8',
      Accept: 'application/json',
    };
  }

  private async request<T>(
    method: string,
    endpoint: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const url = new URL(`${SLACK_API_BASE}/${endpoint}`);
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
        this.logger.error(
          `Slack API HTTP error — ${method} ${endpoint} ${res.status}: ${errorBody}`,
        );
        throw new Error(`Slack API returned HTTP ${res.status}: ${errorBody}`);
      }

      const data = (await res.json()) as T & { ok: boolean; error?: string };

      if (!data.ok) {
        this.logger.error(`Slack API error — ${endpoint}: ${data.error}`);
        throw new Error(`Slack API error: ${data.error}`);
      }

      return data;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * Send a message to a Slack channel.
   */
  async sendMessage(tokens: StoredTokens, params: SendMessageParams): Promise<SlackMessage> {
    try {
      const body: Record<string, unknown> = {
        channel: params.channel,
        text: params.text,
      };

      if (params.blocks?.length) body.blocks = params.blocks;
      if (params.threadTs) body.thread_ts = params.threadTs;

      const result = await this.request<SlackMessage>('POST', 'chat.postMessage', tokens, body);

      this.logger.log(`Slack message sent — channel=${params.channel} ts=${result.ts}`);
      return result;
    } catch (error) {
      this.logger.error(
        'Failed to send message via Slack API',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * List channels in the workspace.
   */
  async listChannels(
    tokens: StoredTokens,
    params: { limit?: number; cursor?: string; types?: string } = {},
  ): Promise<ListChannelsResult> {
    const limit = Math.min(params.limit ?? 20, 200);

    const queryParams: Record<string, string> = {
      limit: String(limit),
      types: params.types ?? 'public_channel,private_channel',
    };

    if (params.cursor) queryParams.cursor = params.cursor;

    try {
      const data = await this.request<{
        channels: SlackChannel[];
        response_metadata?: { next_cursor?: string };
      }>('GET', 'conversations.list', tokens, undefined, queryParams);

      this.logger.log(`Listed ${data.channels.length} Slack channels`);

      return {
        channels: data.channels,
        nextCursor: data.response_metadata?.next_cursor || undefined,
      };
    } catch (error) {
      this.logger.error(
        'Failed to list channels via Slack API',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Get message history for a channel.
   */
  async getChannelHistory(
    tokens: StoredTokens,
    params: { channel: string; limit?: number; cursor?: string },
  ): Promise<ChannelHistoryResult> {
    const limit = Math.min(params.limit ?? 20, 200);

    const queryParams: Record<string, string> = {
      channel: params.channel,
      limit: String(limit),
    };

    if (params.cursor) queryParams.cursor = params.cursor;

    try {
      const data = await this.request<{
        messages: ChannelHistoryMessage[];
        has_more: boolean;
        response_metadata?: { next_cursor?: string };
      }>('GET', 'conversations.history', tokens, undefined, queryParams);

      this.logger.log(
        `Fetched ${data.messages.length} messages from Slack channel ${params.channel}`,
      );

      return {
        messages: data.messages,
        hasMore: data.has_more,
        nextCursor: data.response_metadata?.next_cursor || undefined,
      };
    } catch (error) {
      this.logger.error(
        `Failed to get channel history for ${params.channel} via Slack API`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Add a reaction emoji to a message.
   */
  async addReaction(
    tokens: StoredTokens,
    params: { channel: string; timestamp: string; name: string },
  ): Promise<void> {
    try {
      await this.request<{ ok: boolean }>('POST', 'reactions.add', tokens, {
        channel: params.channel,
        timestamp: params.timestamp,
        name: params.name,
      });

      this.logger.log(
        `Reaction :${params.name}: added to message ${params.timestamp} in ${params.channel}`,
      );
    } catch (error) {
      this.logger.error(
        'Failed to add reaction via Slack API',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
