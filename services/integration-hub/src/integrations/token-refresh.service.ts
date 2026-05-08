import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { PrismaService } from '../prisma/prisma.service';
import { TokenVaultService, StoredTokens } from '../token-vault/token-vault.service';
import { KafkaProducerService, TOPICS, IntegrationTokenRefreshedPayload } from '@adwp/kafka';

/**
 * OAuth provider token endpoint map.
 * Maps IntegrationProvider enum values to their OAuth2 token refresh URLs.
 */
const PROVIDER_TOKEN_ENDPOINTS: Record<string, string> = {
  HUBSPOT: 'https://api.hubapi.com/oauth/v1/token',
  SALESFORCE: 'https://login.salesforce.com/services/oauth2/token',
  GMAIL: 'https://oauth2.googleapis.com/token',
  GOOGLE_CALENDAR: 'https://oauth2.googleapis.com/token',
  OUTLOOK: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
  SLACK: 'https://slack.com/api/oauth.v2.access',
  QUICKBOOKS: 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
  XERO: 'https://identity.xero.com/connect/token',
  JIRA: 'https://auth.atlassian.com/oauth/token',
};

@Injectable()
export class TokenRefreshService {
  private readonly logger = new Logger(TokenRefreshService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly tokenVault: TokenVaultService,
    private readonly kafkaProducer: KafkaProducerService,
  ) {}

  /**
   * Cron job that runs every 5 minutes.
   * Finds all OAuth2 connections whose tokens expire within the next 15 minutes
   * and attempts to refresh them using the provider's token endpoint.
   *
   * @see P5_Security_Secrets_Spec.md Section 4
   */
  @Cron('*/5 * * * *')
  async handleTokenRefresh(): Promise<void> {
    this.logger.log('Token refresh job started');

    const now = new Date();
    const refreshWindow = new Date(now.getTime() + 15 * 60 * 1000); // now + 15 minutes (P5 spec)

    try {
      // Find all CONNECTED OAuth2 connections whose tokens expire within 15 minutes
      const connections = await this.prisma.integrationConnection.findMany({
        where: {
          status: 'CONNECTED',
          authType: 'oauth2',
          tokenExpiresAt: {
            lt: refreshWindow,
          },
        },
      });

      if (connections.length === 0) {
        this.logger.debug('No tokens require refresh');
        return;
      }

      this.logger.log(`Found ${connections.length} connection(s) requiring token refresh`);

      for (const connection of connections) {
        try {
          await this.refreshConnectionToken(
            connection.id,
            connection.tenantId,
            connection.provider,
          );
        } catch (error) {
          this.logger.error(
            `Failed to refresh token for connection ${connection.id} ` +
              `(provider: ${connection.provider}, tenant: ${connection.tenantId}): ` +
              `${error instanceof Error ? error.message : String(error)}`,
            error instanceof Error ? error.stack : undefined,
          );
        }
      }
    } catch (error) {
      this.logger.error(
        `Token refresh job failed: ${error instanceof Error ? error.message : String(error)}`,
        error instanceof Error ? error.stack : undefined,
      );
    }

    this.logger.log('Token refresh job completed');
  }

  /**
   * Refreshes the OAuth2 token for a single connection.
   * Retrieves the stored refresh token, calls the provider's token endpoint,
   * and updates the stored credentials.
   */
  private async refreshConnectionToken(
    connectionId: string,
    tenantId: string,
    provider: string,
  ): Promise<void> {
    // Retrieve existing tokens from the vault
    const storedTokens = await this.tokenVault.getTokens(tenantId, connectionId);

    if (!storedTokens.refreshToken) {
      this.logger.warn(`Connection ${connectionId} has no refresh token; skipping`);
      return;
    }

    const tokenEndpoint = PROVIDER_TOKEN_ENDPOINTS[provider];
    if (!tokenEndpoint) {
      this.logger.warn(`No token endpoint configured for provider ${provider}; skipping`);
      return;
    }

    // Call the provider's token refresh endpoint
    const newTokens = await this.exchangeRefreshToken(
      tokenEndpoint,
      storedTokens.refreshToken,
      provider,
    );

    // Calculate new expiration time
    const expiresAt = new Date(Date.now() + (newTokens.expiresIn ?? 3600) * 1000).toISOString();

    // Build the updated token payload
    const updatedTokens: StoredTokens = {
      ...storedTokens,
      accessToken: newTokens.accessToken,
      refreshToken: newTokens.refreshToken ?? storedTokens.refreshToken,
      expiresAt,
      tokenType: newTokens.tokenType ?? storedTokens.tokenType,
    };

    // Store updated tokens in the vault
    await this.tokenVault.storeTokens(tenantId, connectionId, updatedTokens);

    // Update tokenExpiresAt on the connection record
    await this.prisma.integrationConnection.update({
      where: { id: connectionId },
      data: {
        tokenExpiresAt: new Date(expiresAt),
        lastSyncAt: new Date(),
      },
    });

    this.logger.log(
      `Successfully refreshed token for connection ${connectionId} ` +
        `(provider: ${provider}, tenant: ${tenantId}). New expiry: ${expiresAt}`,
    );

    // Emit Kafka event for successful token refresh
    await this.kafkaProducer.emit<IntegrationTokenRefreshedPayload>(
      TOPICS.INTEGRATION_TOKEN_REFRESHED,
      {
        tenantId,
        source: 'integration-hub',
        payload: {
          connectionId,
          provider,
          expiresAt,
        },
      },
    );
  }

  /**
   * Exchanges a refresh token for new access/refresh tokens via the provider's
   * OAuth2 token endpoint.
   *
   * Uses standard OAuth2 refresh_token grant type. In local dev, falls back
   * to generating mock tokens if the request fails.
   */
  private async exchangeRefreshToken(
    tokenEndpoint: string,
    refreshToken: string,
    provider: string,
  ): Promise<{
    accessToken: string;
    refreshToken?: string;
    expiresIn?: number;
    tokenType?: string;
  }> {
    try {
      const response = await fetch(tokenEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          refresh_token: refreshToken,
          client_id: process.env[`${provider}_CLIENT_ID`] ?? '',
          client_secret: process.env[`${provider}_CLIENT_SECRET`] ?? '',
        }).toString(),
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Token refresh failed with status ${response.status}: ${errorBody}`);
      }

      const data = (await response.json()) as Record<string, unknown>;

      return {
        accessToken: data.access_token as string,
        refreshToken: (data.refresh_token as string) ?? undefined,
        expiresIn: (data.expires_in as number) ?? 3600,
        tokenType: (data.token_type as string) ?? 'Bearer',
      };
    } catch (error) {
      // In local development, generate mock tokens instead of failing
      if (process.env.NODE_ENV !== 'production') {
        this.logger.warn(
          `Token refresh HTTP request failed for provider ${provider}. ` +
            `Generating mock tokens for local development. ` +
            `Error: ${error instanceof Error ? error.message : String(error)}`,
        );

        return {
          accessToken: `mock_refreshed_access_${provider}_${Date.now()}`,
          refreshToken: `mock_refreshed_refresh_${provider}_${Date.now()}`,
          expiresIn: 3600,
          tokenType: 'Bearer',
        };
      }

      throw error;
    }
  }
}
