import { DynamicModule, Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { KafkaModuleOptions } from './interfaces/kafka-config.interface';
import { KafkaProducerService } from './kafka-producer.service';
import { AuditService } from './audit.service';

@Module({})
export class KafkaModule {
  static register(options: KafkaModuleOptions): DynamicModule {
    return {
      module: KafkaModule,
      global: true,
      imports: [
        ClientsModule.register([
          {
            name: 'KAFKA_SERVICE',
            transport: Transport.KAFKA,
            options: {
              client: {
                clientId: options.clientId,
                brokers: options.brokers,
              },
              consumer: {
                groupId: options.consumerGroupId,
              },
              producer: {
                allowAutoTopicCreation: true,
              },
            },
          },
        ]),
      ],
      providers: [KafkaProducerService, AuditService],
      exports: [ClientsModule, KafkaProducerService, AuditService],
    };
  }
}
