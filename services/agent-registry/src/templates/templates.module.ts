import { Module } from '@nestjs/common';
import {
  TemplatesController,
  AgentTemplatesController,
} from './templates.controller';
import { TemplatesService } from './templates.service';

@Module({
  controllers: [TemplatesController, AgentTemplatesController],
  providers: [TemplatesService],
  exports: [TemplatesService],
})
export class TemplatesModule {}
