import { Module } from '@nestjs/common';
import { AnalyticsController } from './analytics.controller';
import { AnalyticsConsumer } from './analytics.consumer';
import { AnalyticsService } from './analytics.service';

@Module({
  controllers: [AnalyticsController, AnalyticsConsumer],
  providers: [AnalyticsService],
  exports: [AnalyticsService],
})
export class AnalyticsModule {}
