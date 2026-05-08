import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Redis from 'ioredis';
import { PrismaService } from '../prisma/prisma.service';

/**
 * Redis-backed token revocation service.
 *
 * Stores revoked JWT IDs (jti) with a TTL equal to the token's remaining
 * lifetime so entries are automatically cleaned up once the token would
 * have expired anyway.
 */
@Injectable()
export class TokenRevocationService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(TokenRevocationService.name);
  private redis!: Redis;
  private static readonly KEY_PREFIX = 'revoked_jwt:';

  constructor(
    private readonly configService: ConfigService,
    private readonly prisma: PrismaService,
  ) {}

  async onModuleInit() {
    const redisUrl = this.configService.get<string>('REDIS_URL') || 'redis://localhost:6379';

    this.redis = new Redis(redisUrl, {
      maxRetriesPerRequest: 3,
      retryStrategy(times: number) {
        if (times > 5) return null; // stop retrying after 5 attempts
        return Math.min(times * 200, 2000);
      },
    });

    this.redis.on('error', (err) => {
      this.logger.error('Redis connection error', err);
    });

    this.redis.on('connect', () => {
      this.logger.log('Connected to Redis for token revocation');
    });
  }

  async onModuleDestroy() {
    if (this.redis) {
      await this.redis.quit();
    }
  }

  /**
   * Revoke a token by storing its JTI in Redis with a TTL.
   *
   * @param jti  The unique JWT ID to revoke
   * @param expiresInSeconds  TTL in seconds (should match the remaining
   *                          lifetime of the token so the key auto-expires)
   */
  async revokeToken(jti: string, expiresInSeconds: number): Promise<void> {
    const key = `${TokenRevocationService.KEY_PREFIX}${jti}`;
    await this.redis.set(key, '1', 'EX', expiresInSeconds);
    this.logger.log(`Token revoked: ${jti} (TTL: ${expiresInSeconds}s)`);
  }

  /**
   * Check whether a token has been revoked.
   *
   * @param jti  The unique JWT ID to check
   * @returns    `true` if the token has been revoked, `false` otherwise
   */
  async isRevoked(jti: string): Promise<boolean> {
    const key = `${TokenRevocationService.KEY_PREFIX}${jti}`;
    const result = await this.redis.exists(key);
    return result === 1;
  }

  /**
   * Revoke all active sessions for a user.
   *
   * Called on account suspension, password change, or security compromise.
   * Adds each session's refresh token JTI to the Redis blocklist and
   * expires all sessions in the database.
   *
   * @param userId  The user whose sessions should be revoked
   */
  async revokeAllUserSessions(userId: string): Promise<void> {
    // Find all active (non-expired) sessions for this user
    const sessions = await this.prisma.userSession.findMany({
      where: { userId, expiresAt: { gt: new Date() } },
    });

    // Revoke each session's refresh token in Redis
    const REFRESH_TOKEN_TTL_SECONDS = 604800; // 7 days max
    for (const session of sessions) {
      if (session.refreshToken) {
        await this.revokeToken(session.refreshToken, REFRESH_TOKEN_TTL_SECONDS);
      }
    }

    // Expire all sessions in the database
    await this.prisma.userSession.updateMany({
      where: { userId },
      data: { expiresAt: new Date() },
    });

    this.logger.log(`Revoked all sessions for user ${userId} (${sessions.length} sessions)`);
  }
}
