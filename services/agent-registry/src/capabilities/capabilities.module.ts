import { Module } from '@nestjs/common';
import {
  CapabilitiesController,
  AgentCapabilitiesController,
} from './capabilities.controller';
import { CapabilitiesService } from './capabilities.service';

@Module({
  controllers: [CapabilitiesController, AgentCapabilitiesController],
  providers: [CapabilitiesService],
  exports: [CapabilitiesService],
})
export class CapabilitiesModule {}
