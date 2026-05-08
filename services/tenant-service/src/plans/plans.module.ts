import { Module } from '@nestjs/common';
import { PlansController, TenantPlanController } from './plans.controller';
import { PlansService } from './plans.service';

@Module({
  controllers: [PlansController, TenantPlanController],
  providers: [PlansService],
  exports: [PlansService],
})
export class PlansModule {}
