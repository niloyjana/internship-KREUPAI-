import { Module } from '@nestjs/common';
import { KafkaModule } from '@adwp/kafka';
import { HumanTasksController } from './human-tasks.controller';
import { HumanTasksConsumer } from './human-tasks.consumer';
import { HumanTasksService } from './human-tasks.service';

@Module({
  imports: [
    KafkaModule.register({
      clientId: 'workflow-service',
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      consumerGroupId: 'workflow-consumers',
    }),
  ],
  controllers: [HumanTasksController, HumanTasksConsumer],
  providers: [HumanTasksService],
  exports: [HumanTasksService],
})
export class HumanTasksModule {}
