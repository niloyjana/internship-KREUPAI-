import { Module } from '@nestjs/common';
import { AiRuntimeService } from './ai-runtime.service';

@Module({
  providers: [AiRuntimeService],
  exports: [AiRuntimeService],
})
export class AiRuntimeModule {}
