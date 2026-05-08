import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { IntegrationProvider } from '@prisma/client';
import { PrismaService } from '../../prisma/prisma.service';
import { TokenVaultService, StoredTokens } from '../../token-vault/token-vault.service';
import { ConnectorFactory } from './connector.factory';
import {
  SendEmailParams,
  SendEmailResult,
  ListEmailsParams,
  ListEmailsResult,
  EmailDetail,
  ListContactsResult,
  ListDealsResult,
  HubSpotContact,
  HubSpotDeal,
  HubSpotListParams,
  CreateContactData,
  CreateDealData,
} from './interfaces';

/**
 * Orchestrates connector operations.
 *
 * Responsibilities:
 *  1. Resolve the connection and verify it is CONNECTED.
 *  2. Retrieve decrypted tokens from the Token Vault.
 *  3. Validate the provider matches the requested action.
 *  4. Delegate to the appropriate connector.
 *  5. Log the operation in IntegrationLog.
 */
@Injectable()
export class ConnectorsService {
  private readonly logger = new Logger(ConnectorsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly tokenVault: TokenVaultService,
    private readonly connectorFactory: ConnectorFactory,
  ) {}

  // ── helpers ─────────────────────────────────────────────

  /**
   * Load and validate a connection, returning provider + decrypted tokens.
   */
  private async resolveConnection(
    tenantId: string,
    connectionId: string,
    requiredProvider?: IntegrationProvider,
  ): Promise<{
    provider: IntegrationProvider;
    tokens: StoredTokens;
  }> {
    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    if (connection.status !== 'CONNECTED') {
      throw new BadRequestException(
        `Connection is not active (current status: ${connection.status})`,
      );
    }

    if (requiredProvider && connection.provider !== requiredProvider) {
      throw new BadRequestException(
        `This action requires a ${requiredProvider} connection, but the connection is ${connection.provider}`,
      );
    }

    const tokens = await this.tokenVault.getTokens(tenantId, connectionId);

    return { provider: connection.provider, tokens };
  }

  /**
   * Write an IntegrationLog entry for an action execution.
   */
  private async logAction(
    connectionId: string,
    tenantId: string,
    operation: string,
    status: 'SUCCESS' | 'FAILURE',
    durationMs: number,
    errorMessage?: string,
  ): Promise<void> {
    try {
      await this.prisma.integrationLog.create({
        data: {
          connectionId,
          tenantId,
          direction: 'OUTBOUND',
          operation,
          status,
          httpMethod: 'POST',
          durationMs,
          errorMessage: errorMessage ?? null,
        },
      });
    } catch (logError) {
      // Logging failure should not bubble up to the caller
      this.logger.warn(
        `Failed to write integration log: ${logError instanceof Error ? logError.message : logError}`,
      );
    }
  }

  // ── Gmail actions ───────────────────────────────────────

  async sendEmail(
    tenantId: string,
    connectionId: string,
    params: SendEmailParams,
  ): Promise<SendEmailResult> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.GMAIL,
    );

    const gmail = this.connectorFactory.getGmailConnector();

    try {
      const result = await gmail.sendEmail(tokens, params);

      await this.logAction(
        connectionId,
        tenantId,
        'SEND_EMAIL',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'SEND_EMAIL',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  async listEmails(
    tenantId: string,
    connectionId: string,
    params: ListEmailsParams,
  ): Promise<ListEmailsResult> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.GMAIL,
    );

    const gmail = this.connectorFactory.getGmailConnector();

    try {
      const result = await gmail.listEmails(tokens, params);

      await this.logAction(
        connectionId,
        tenantId,
        'LIST_EMAILS',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'LIST_EMAILS',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  async getEmail(
    tenantId: string,
    connectionId: string,
    messageId: string,
  ): Promise<EmailDetail> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.GMAIL,
    );

    const gmail = this.connectorFactory.getGmailConnector();

    try {
      const result = await gmail.getEmail(tokens, messageId);

      await this.logAction(
        connectionId,
        tenantId,
        'GET_EMAIL',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'GET_EMAIL',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  // ── HubSpot actions ─────────────────────────────────────

  async listContacts(
    tenantId: string,
    connectionId: string,
    params: HubSpotListParams,
  ): Promise<ListContactsResult> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.HUBSPOT,
    );

    const hubspot = this.connectorFactory.getHubSpotConnector();

    try {
      const result = await hubspot.listContacts(tokens, params);

      await this.logAction(
        connectionId,
        tenantId,
        'LIST_CONTACTS',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'LIST_CONTACTS',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  async getContact(
    tenantId: string,
    connectionId: string,
    contactId: string,
    properties?: string[],
  ): Promise<HubSpotContact> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.HUBSPOT,
    );

    const hubspot = this.connectorFactory.getHubSpotConnector();

    try {
      const result = await hubspot.getContact(tokens, contactId, properties);

      await this.logAction(
        connectionId,
        tenantId,
        'GET_CONTACT',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'GET_CONTACT',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  async createContact(
    tenantId: string,
    connectionId: string,
    data: CreateContactData,
  ): Promise<HubSpotContact> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.HUBSPOT,
    );

    const hubspot = this.connectorFactory.getHubSpotConnector();

    try {
      const result = await hubspot.createContact(tokens, data);

      await this.logAction(
        connectionId,
        tenantId,
        'CREATE_CONTACT',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'CREATE_CONTACT',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  async listDeals(
    tenantId: string,
    connectionId: string,
    params: HubSpotListParams,
  ): Promise<ListDealsResult> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.HUBSPOT,
    );

    const hubspot = this.connectorFactory.getHubSpotConnector();

    try {
      const result = await hubspot.listDeals(tokens, params);

      await this.logAction(
        connectionId,
        tenantId,
        'LIST_DEALS',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'LIST_DEALS',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }

  async createDeal(
    tenantId: string,
    connectionId: string,
    data: CreateDealData,
  ): Promise<HubSpotDeal> {
    const start = Date.now();

    const { tokens } = await this.resolveConnection(
      tenantId,
      connectionId,
      IntegrationProvider.HUBSPOT,
    );

    const hubspot = this.connectorFactory.getHubSpotConnector();

    try {
      const result = await hubspot.createDeal(tokens, data);

      await this.logAction(
        connectionId,
        tenantId,
        'CREATE_DEAL',
        'SUCCESS',
        Date.now() - start,
      );

      return result;
    } catch (error) {
      await this.logAction(
        connectionId,
        tenantId,
        'CREATE_DEAL',
        'FAILURE',
        Date.now() - start,
        error instanceof Error ? error.message : String(error),
      );
      throw error;
    }
  }
}
