import { Module } from '@nestjs/common';
import { KafkaModule } from '@adwp/kafka';
import { ExecutionsController } from './executions.controller';
import { ExecutionsConsumer } from './executions.consumer';
import { ExecutionsService } from './executions.service';
import { AiRuntimeModule } from '../ai-runtime/ai-runtime.module';

@Module({
  imports: [
    KafkaModule.register({
      clientId: 'workflow-service',
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      consumerGroupId: 'workflow-consumers',
    }),
    AiRuntimeModule,
  ],
  controllers: [ExecutionsController, ExecutionsConsumer],
  providers: [ExecutionsService],
  exports: [ExecutionsService],
})
export class ExecutionsModule {}
