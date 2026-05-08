import { Injectable } from '@nestjs/common';
import {
  HealthIndicator,
  HealthIndicatorResult,
  HealthCheckError,
} from '@nestjs/terminus';
import { ConfigService } from '@nestjs/config';
import Redis from 'ioredis';

@Injectable()
export class RedisHealthIndicator extends HealthIndicator {
  private redis: Redis | null = null;

  constructor(private readonly configService: ConfigService) {
    super();
  }

  async isHealthy(key: string = 'redis'): Promise<HealthIndicatorResult> {
    try {
      if (!this.redis) {
        const redisUrl =
          this.configService.get<string>('REDIS_URL') ||
          'redis://localhost:6379';
        this.redis = new Redis(redisUrl, {
          maxRetriesPerRequest: 1,
          connectTimeout: 5000,
          lazyConnect: true,
        });
      }

      await this.redis.connect().catch(() => {
        // Already connected — ignore
      });
      const result = await this.redis.ping();

      if (result !== 'PONG') {
        throw new Error(`Unexpected PING response: ${result}`);
      }

      return this.getStatus(key, true);
    } catch (error) {
      throw new HealthCheckError(
        'Redis check failed',
        this.getStatus(key, false, {
          message: error instanceof Error ? error.message : 'Unknown error',
        }),
      );
    }
  }

  async onModuleDestroy() {
    if (this.redis) {
      await this.redis.quit().catch(() => {});
      this.redis = null;
    }
  }
}
