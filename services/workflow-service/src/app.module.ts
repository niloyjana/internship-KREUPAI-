import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { KafkaModule } from '@adwp/kafka';

import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';

import { JwtAuthGuard } from './common/guards/jwt-auth.guard';
import { RolesGuard } from './common/guards/roles.guard';
import { GlobalExceptionFilter } from './common/filters/global-exception.filter';
import { TenantContextInterceptor } from './common/interceptors/tenant-context.interceptor';

import { HealthModule } from './health/health.module';
import { DefinitionsModule } from './definitions/definitions.module';
import { ExecutionsModule } from './executions/executions.module';
import { HumanTasksModule } from './human-tasks/human-tasks.module';
import { EscalationsModule } from './escalations/escalations.module';
import { WsModule } from './ws/ws.module';
import { DlqModule } from './dlq/dlq.module';
import { AiRuntimeModule } from './ai-runtime/ai-runtime.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env', '../../.env.local', '../../.env'],
    }),

    // Kafka event bus
    KafkaModule.register({
      clientId: 'workflow-service',
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      consumerGroupId: 'workflow-consumers',
    }),

    PrismaModule,
    AuthModule,
    DefinitionsModule,
    ExecutionsModule,
    HumanTasksModule,
    EscalationsModule,
    WsModule,
    DlqModule,
    AiRuntimeModule,

    // Rate limiting — 1000 requests/min per tenant (P3 spec: General API)
    ThrottlerModule.forRoot([{ ttl: 60000, limit: 1000 }]),

    // Health checks (liveness + readiness probes)
    HealthModule,
  ],
  controllers: [],
  providers: [
    { provide: APP_GUARD, useClass: ThrottlerGuard },
    { provide: APP_GUARD, useClass: JwtAuthGuard },
    { provide: APP_GUARD, useClass: RolesGuard },
    { provide: APP_FILTER, useClass: GlobalExceptionFilter },
    { provide: APP_INTERCEPTOR, useClass: TenantContextInterceptor },
  ],
})
export class AppModule {}
