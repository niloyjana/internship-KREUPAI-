import { Inject, Injectable } from '@nestjs/common';
import {
  HealthIndicator,
  HealthIndicatorResult,
  HealthCheckError,
} from '@nestjs/terminus';
import { ClientKafka } from '@nestjs/microservices';

@Injectable()
export class KafkaHealthIndicator extends HealthIndicator {
  constructor(
    @Inject('KAFKA_SERVICE') private readonly kafkaClient: ClientKafka,
  ) {
    super();
  }

  async isHealthy(key: string = 'kafka'): Promise<HealthIndicatorResult> {
    try {
      const client = (this.kafkaClient as any).client;
      if (!client) {
        throw new Error('Kafka client not initialised');
      }
      const admin = client.admin();
      await admin.connect();
      await admin.listTopics();
      await admin.disconnect();
      return this.getStatus(key, true);
    } catch (error) {
      throw new HealthCheckError(
        'Kafka check failed',
        this.getStatus(key, false, {
          message: error instanceof Error ? error.message : 'Unknown error',
        }),
      );
    }
  }
}
