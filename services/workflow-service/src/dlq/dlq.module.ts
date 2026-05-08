import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { DlqService } from './dlq.service';
import { DlqController } from './dlq.controller';
import { DlqConsumer } from './dlq.consumer';

@Module({
  imports: [PrismaModule],
  controllers: [DlqController],
  providers: [DlqService, DlqConsumer],
  exports: [DlqService],
})
export class DlqModule {}
