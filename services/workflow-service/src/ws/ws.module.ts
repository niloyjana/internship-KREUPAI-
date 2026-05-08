import { Module } from '@nestjs/common';
import { EventsGateway } from './events.gateway';
import { WsKafkaConsumer } from './ws-kafka.consumer';
import { WorkflowKafkaConsumer } from './workflow-kafka.consumer';

@Module({
  providers: [EventsGateway],
  controllers: [WsKafkaConsumer, WorkflowKafkaConsumer],
  exports: [EventsGateway],
})
export class WsModule {}
