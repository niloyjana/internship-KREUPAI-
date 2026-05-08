import {
  Injectable,
  InternalServerErrorException,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { encrypt, decrypt } from '@adwp/utils';
import { PrismaService } from '../prisma/prisma.service';

export interface StoredTokens {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: string;
  tokenType?: string;
  scope?: string;
  apiKey?: string;
  [key: string]: unknown;
}

@Injectable()
export class TokenVaultService {
  private readonly logger = new Logger(TokenVaultService.name);
  private readonly encryptionKey: string;

  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
  ) {
    const key = this.configService.get<string>('FIELD_ENCRYPTION_KEY');
    if (!key) {
      throw new Error('FIELD_ENCRYPTION_KEY environment variable is not set');
    }
    this.encryptionKey = key;
  }

  /**
   * Encrypts token JSON with FIELD_ENCRYPTION_KEY and stores in authSecretRef.
   * Dev-mode token vault: stores encrypted tokens directly in the DB field.
   */
  async storeTokens(tenantId: string, connectionId: string, tokens: StoredTokens): Promise<void> {
    const tokenJson = JSON.stringify(tokens);
    const encryptedRef = encrypt(tokenJson, this.encryptionKey);

    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    await this.prisma.integrationConnection.update({
      where: { id: connectionId },
      data: { authSecretRef: encryptedRef },
    });

    this.logger.log(`Stored tokens for connection ${connectionId} (tenant: ${tenantId})`);
  }

  /**
   * Decrypts tokens from authSecretRef field.
   */
  async getTokens(tenantId: string, connectionId: string): Promise<StoredTokens> {
    const connection = await this.prisma.integrationConnection.findFirst({
      where: { id: connectionId, tenantId },
    });

    if (!connection) {
      throw new NotFoundException('CONNECTION_NOT_FOUND');
    }

    if (!connection.authSecretRef) {
      throw new InternalServerErrorException('No tokens stored for this connection');
    }

    try {
      const decryptedJson = decrypt(connection.authSecretRef, this.encryptionKey);
      return JSON.parse(decryptedJson) as StoredTokens;
    } catch (error) {
      this.logger.error(
        `Failed to decrypt tokens for connection ${connectionId}`,
        error instanceof Error ? error.stack : undefined,
      );
      throw new InternalServerErrorException('Failed to decrypt stored tokens');
    }
  }

  /**
   * Clears authSecretRef and sets status to DISCONNECTED.
   */
  async revokeTokens(connectionId: string): Promise<void> {
    await this.prisma.integrationConnection.update({
      where: { id: connectionId },
      data: {
        authSecretRef: '',
        status: 'DISCONNECTED',
        revokedAt: new Date(),
      },
    });

    this.logger.log(`Revoked tokens for connection ${connectionId}`);
  }

  /**
   * Revoke all tokens for a tenant (on offboarding).
   *
   * Clears all authSecretRef fields and marks connections as DISCONNECTED.
   * In production with AWS Secrets Manager, this would also delete the
   * secret with ForceDeleteWithoutRecovery=false (30-day recovery window).
   *
   * @see P5_Security_Secrets_Spec.md Section 4
   */
  async revokeAllTenantTokens(tenantId: string): Promise<void> {
    const connections = await this.prisma.integrationConnection.findMany({
      where: { tenantId, status: 'CONNECTED' },
      select: { id: true },
    });

    for (const conn of connections) {
      try {
        await this.revokeTokens(conn.id);
      } catch (error) {
        // Log and continue — don't fail offboarding for a single connection
        this.logger.error(
          `Failed to revoke tokens for connection ${conn.id}: ${
            error instanceof Error ? error.message : String(error)
          }`,
        );
      }
    }

    this.logger.log(
      `Revoked all tokens for tenant ${tenantId} (${connections.length} connections)`,
    );
  }
}
