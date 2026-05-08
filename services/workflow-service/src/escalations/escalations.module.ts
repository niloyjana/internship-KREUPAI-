import { Module } from '@nestjs/common';
import { KafkaModule } from '@adwp/kafka';
import { EscalationsController } from './escalations.controller';
import { EscalationsConsumer } from './escalations.consumer';
import { EscalationsService } from './escalations.service';

@Module({
  imports: [
    KafkaModule.register({
      clientId: 'workflow-service',
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      consumerGroupId: 'workflow-consumers',
    }),
  ],
  controllers: [EscalationsController, EscalationsConsumer],
  providers: [EscalationsService],
  exports: [EscalationsService],
})
export class EscalationsModule {}
