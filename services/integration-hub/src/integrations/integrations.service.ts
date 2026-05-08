import {
  BadRequestException,
  ConflictException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { IntegrationProvider, Prisma } from '@prisma/client';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  IntegrationConnectedPayload,
  IntegrationConnectionFailedPayload,
} from '@adwp/kafka';
import { PrismaService } from '../prisma/prisma.service';
import { TokenVaultService } from '../token-vault/token-vault.service';
import { INTEGRATION_CATALOG, getCatalogEntry } from './catalog/integration-catalog';
import { CreateConnectionDto, AuthTypeEnum } from './dto/create-connection.dto';
import { QueryLogsDto } from './dto/query-logs.dto';

@Injectable()
export class IntegrationsService {
  private readonly logger = new Logger(IntegrationsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly tokenVault: TokenVaultService,
    private readonly configService: ConfigService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  /**
   * GET /v1/integrations/catalog
   * Returns the static catalog of available integration providers.
   */
  getCatalog() {
    return INTEGRATION_CATALOG;
  }

  /**
   * GET /v1/integrations/connections
   * List tenant's connected integrations.
   */
  async listConnections(tenantId: string) {
    const connections = await this.prisma.integrationConnection.findMany({
      where: { tenantId },
      select: {
        id: true,
        provider: true,
        name: true,
        status: true,
        lastSyncAt: true,
        scopesGranted: true,
        authType: true,
        createdAt: true,
        updatedAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    return connections;
  }

  /**
   * POST /v1/integrations/connections
   * Initiate a new integration connection.
   */
  async createConnection(tenantId: string, dto: CreateConnectionDto) {
    // Validate the provider is in the catalog
    const catalogEntry = getCatalogEntry(dto.provider);
    if (!catalogEntry) {
      throw new BadRequestException('PROVIDER_NOT_SUPPORTED');
    }

    // Validate authType matches what the catalog expects
    if (catalogEntry.authType !== dto.authType) {
      throw new BadRequestException(
        `Provider ${dto.provider} requires authType '${catalogEntry.authType}', but '${dto.authType}' was provided`,
      );
    }

    // Validate the provider is a valid enum value
    if (!(dto.provider in IntegrationProvider)) {
      throw new BadRequestException('PROVIDER_NOT_SUPPORTED');
    }

    // Check for duplicate connection
    const existing = await this.prisma.integrationConnection.findUnique({
      where: {
        tenantId_provider_name: {
          tenantId,
          provider: dto.provider as IntegrationProvider,
          name: dto.name,
        },
      },
    });

    if (existing) {
      throw new ConflictException('CONNECTION_ALREADY_EXISTS');
    }

    try {
      if (dto.authType === AuthTypeEnum.API_KEY) {
        return await this.createApiKeyConnection(tenantId, dto, catalogEntry.scopes);
      }

      return await this.createOAuth2Connection(tenantId, dto, catalogEntry.scopes);
    } catch (error) {
      // Emit connection failed event for unexpected errors (not validation errors)
      if (!(error instanceof BadRequestException) && !(error instanceof ConflictException)) {
        await this.kafkaProducer.emit<IntegrationConnectionFailedPayload>(
          TOPICS.INTEGRATION_CONNECTION_FAILED,
          {
            tenantId,
            source: 'integration-hub',
            payload: {
              connectionId: '',
              provider: dto.provider,
              errorType: 'endpoint_unreachable',
              errorMessage: error instanceof Error ? error.message : String(error),
              retryAfterSeconds: null,
            },
          },
        );
      }
      throw error;
    }
  }

  /**
   * Handles API key-based connection creation.
   * Encrypts the API key and stores it, marks connection as CONNECTED.
   */
  private async createApiKeyConnection(
    tenantId: string,
    dto: CreateConnectionDto,
    scopes: string[],
  ) {
    const apiKey = dto.config?.apiKey as string | undefined;
    if (!apiKey) {
      throw new BadRequestException('config.apiKey is required for api_key auth type');
    }

    // Create the connection with a placeholder, then store encrypted tokens
    const connection = await this.prisma.integrationConnection.create({
      data: {
        tenantId,
        provider: dto.provider as IntegrationProvider,
        name: dto.name,
        authType: dto.authType,
        authSecretRef: '', // will be filled by token vault
        scopesGranted: scopes,
        status: 'CONNECTED',
        configJson: (dto.config ?? null) as Prisma.InputJsonValue,
      },
    });

    // Store the encrypted API key
    await this.tokenVault.storeTokens(tenantId, connection.id, {
      accessToken: apiKey,
      apiKey,
    });

    // Emit integration connected event
    await this.kafkaProducer.emit<IntegrationConnectedPayload>(TOPICS.INTEGRATION_CONNECTED, {
      tenantId,
      source: 'integration-hub',
      payload: {
        connectionId: connection.id,
        provider: connection.provider,
        name: connection.name ?? dto.name ?? connection.provider,
        status: 'CONNECTED',
        scopesGranted: connection.scopesGranted ?? [],
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'INTEGRATION_CONNECTED',
      entityType: 'INTEGRATION_CONNECTION',
      entityId: connection.id,
      after: { provider: connection.provider, authType: dto.authType },
    });

    return {
      connectionId: connection.id,
      provider: connection.provider,
      name: connection.name,
      status: connection.status,
    };
  }

  /**
   * Handles OAuth2-based connection creation.
   * Creates connection in PENDING_AUTH state and returns a mock auth URL.
   */
  private async createOAuth2Connection(
    tenantId: string,
    dto: CreateConnectionDto,
    scopes: string[],
  ) {
    const connection = await this.prisma.integrationConnection.create({
      data: {
        tenantId,
        provider: dto.provider as IntegrationProvider,
        name: dto.name,
        authType: dto.authType,
        authSecretRef: '',
        scopesGranted: scopes,
        status: 'PENDING_AUTH',
        configJson: (dto.config ?? null) as Prisma.InputJsonValue,
      },
    });

    // Generate mock OAuth URL for local dev
    const baseUrl = this.configService.get<string>('PLATFORM_URL') || 'http://localhost:3006';

    // Encode connection info in state parameter
    const state = Buffer.from(
      JSON.stringify({
        connectionId: connection.id,
        tenantId,
        provider: dto.provider,
      }),
    ).toString('base64url');

    const authUrl = `${baseUrl}/v1/integrations/oauth/callback?code=mock_auth_code_${connection.id}&state=${state}`;

    return {
      connectionId: connection.id,
      authUrl,
    };
  }

  /**
   * GET /v1/integrations/connections/:connectionId
   * Get connection detail and health.
   */
  async getConnection(tenantId: string, connectionId: string) {
    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
      select: {
        id: true,
        provider: true,
        name: true,
        status: true,
        authType: true,
        scopesGranted: true,
        configJson: true,
        lastSyncAt: true,
        lastErrorAt: true,
        lastErrorMessage: true,
        rateLimitRemaining: true,
        rateLimitResetsAt: true,
        createdAt: true,
        updatedAt: true,
        revokedAt: true,
      },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    return connection;
  }

  /**
   * DELETE /v1/integrations/connections/:connectionId
   * Disconnect and revoke integration.
   */
  async deleteConnection(tenantId: string, connectionId: string) {
    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    // Revoke tokens (clears authSecretRef and sets DISCONNECTED)
    await this.tokenVault.revokeTokens(connectionId);

    this.logger.log(`Disconnected integration ${connectionId} (tenant: ${tenantId})`);

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'INTEGRATION_DISCONNECTED',
      entityType: 'INTEGRATION_CONNECTION',
      entityId: connectionId,
      before: { provider: connection.provider, status: connection.status },
      after: { status: 'DISCONNECTED' },
    });

    return { connectionId, status: 'DISCONNECTED' };
  }

  /**
   * GET /v1/integrations/connections/:connectionId/logs
   * Get integration activity logs (paginated).
   */
  async getConnectionLogs(tenantId: string, connectionId: string, query: QueryLogsDto) {
    // Verify connection exists and belongs to tenant
    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 50;
    const skip = (page - 1) * pageSize;

    const where: Prisma.IntegrationLogWhereInput = {
      connectionId,
      tenantId,
    };

    if (query.status) {
      where.status = query.status;
    }

    if (query.from) {
      where.createdAt = { gte: new Date(query.from) };
    }

    const [logs, total] = await Promise.all([
      this.prisma.integrationLog.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: pageSize,
      }),
      this.prisma.integrationLog.count({ where }),
    ]);

    return {
      items: logs,
      meta: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  /**
   * POST /v1/integrations/connections/:connectionId/test
   * Test connectivity. For local dev, validates the connection exists and is CONNECTED.
   */
  async testConnection(tenantId: string, connectionId: string) {
    const startTime = Date.now();

    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    const responseTimeMs = Date.now() - startTime;

    if (connection.status !== 'CONNECTED') {
      return {
        status: 'unhealthy' as const,
        responseTimeMs,
        permissionsValid: false,
        currentStatus: connection.status,
        message: `Connection is in ${connection.status} state`,
      };
    }

    return {
      status: 'healthy' as const,
      responseTimeMs,
      permissionsValid: true,
      currentStatus: connection.status,
    };
  }

  /**
   * OAuth callback handler.
   * Decodes state to get connectionId, exchanges code for tokens (mock),
   * encrypts and stores tokens, updates connection status to CONNECTED.
   */
  async handleOAuthCallback(code: string, state: string) {
    let statePayload: {
      connectionId: string;
      tenantId: string;
      provider: string;
    };

    try {
      const decoded = Buffer.from(state, 'base64url').toString('utf8');
      statePayload = JSON.parse(decoded);
    } catch {
      throw new BadRequestException('OAUTH_CALLBACK_FAILED');
    }

    const { connectionId, tenantId, provider } = statePayload;

    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    if (connection.status === 'CONNECTED') {
      return {
        connectionId,
        status: 'CONNECTED',
        message: 'Connection is already authorized',
      };
    }

    // Mock token exchange for local dev (code is used as part of the mock token)
    const mockTokens = {
      accessToken: `mock_access_token_${provider}_${code}_${Date.now()}`,
      refreshToken: `mock_refresh_token_${provider}_${Date.now()}`,
      expiresAt: new Date(Date.now() + 3600 * 1000).toISOString(),
      tokenType: 'Bearer',
      scope: connection.scopesGranted.join(' '),
    };

    // Encrypt and store tokens
    await this.tokenVault.storeTokens(tenantId, connectionId, mockTokens);

    // Update connection status to CONNECTED
    await this.prisma.integrationConnection.update({
      where: { id: connectionId },
      data: {
        status: 'CONNECTED',
        lastSyncAt: new Date(),
      },
    });

    // Log the OAuth callback
    await this.prisma.integrationLog.create({
      data: {
        connectionId,
        tenantId,
        direction: 'INBOUND',
        operation: 'OAUTH_CALLBACK',
        status: 'SUCCESS',
        httpMethod: 'GET',
        responseStatus: 200,
        durationMs: 0,
      },
    });

    this.logger.log(
      `OAuth callback successful for connection ${connectionId} (provider: ${provider})`,
    );

    // Emit integration connected event
    await this.kafkaProducer.emit<IntegrationConnectedPayload>(TOPICS.INTEGRATION_CONNECTED, {
      tenantId,
      source: 'integration-hub',
      payload: {
        connectionId,
        provider,
        name: connection.name ?? provider,
        status: 'CONNECTED',
        scopesGranted: connection.scopesGranted ?? [],
      },
    });

    return {
      connectionId,
      status: 'CONNECTED',
      message: `Successfully connected to ${provider}`,
    };
  }
}
