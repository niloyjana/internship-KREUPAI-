import { Controller, Get } from '@nestjs/common';
import { DegradationManager, DegradationLevel } from '@adwp/utils';
import { Public } from '../common/decorators/public.decorator';
import { PrismaHealthIndicator } from './indicators/prisma-health.indicator';
import { KafkaHealthIndicator } from './indicators/kafka-health.indicator';

@Controller({ path: 'health', version: '1' })
export class HealthController {
  private readonly startTime = Date.now();
  private readonly degradationManager = DegradationManager.getInstance();

  constructor(
    private readonly prismaHealth: PrismaHealthIndicator,
    private readonly kafkaHealth: KafkaHealthIndicator,
  ) {}

  /**
   * Liveness probe — returns enhanced health status with degradation level.
   */
  @Public()
  @Get()
  check() {
    const level = this.degradationManager.getLevel('agent-registry');
    return {
      status:
        level <= DegradationLevel.REDUCED_INTEGRATION
          ? 'healthy'
          : level <= DegradationLevel.LLM_FALLBACK
            ? 'degraded'
            : 'unhealthy',
      service: 'agent-registry',
      version: '1.0.0',
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      degradationLevel: level,
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Readiness probe — deep check of database and Kafka connectivity
   * with per-check latency tracking and degradation management.
   */
  @Public()
  @Get('ready')
  async ready() {
    const checks: Array<{
      name: string;
      status: string;
      latencyMs: number;
      details?: any;
    }> = [];

    for (const [name, indicator] of [
      ['database', this.prismaHealth],
      ['kafka', this.kafkaHealth],
    ] as const) {
      const start = Date.now();
      try {
        await indicator.isHealthy(name as string);
        checks.push({
          name: name as string,
          status: 'up',
          latencyMs: Date.now() - start,
        });
      } catch {
        checks.push({
          name: name as string,
          status: 'down',
          latencyMs: Date.now() - start,
        });
      }
    }

    this.degradationManager.checkAndTransition(
      'agent-registry',
      checks.map((c) => ({
        name: c.name,
        status: c.status as 'up' | 'down',
        critical: c.name === 'database',
      })),
    );

    const level = this.degradationManager.getLevel('agent-registry');
    const allUp = checks.every((c) => c.status === 'up');

    return {
      status: allUp
        ? 'healthy'
        : checks.some((c) => c.name === 'database' && c.status === 'down')
          ? 'unhealthy'
          : 'degraded',
      version: '1.0.0',
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      degradationLevel: level,
      checks,
    };
  }
}
