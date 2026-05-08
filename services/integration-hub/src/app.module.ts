import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { ScheduleModule } from '@nestjs/schedule';
import { KafkaModule } from '@adwp/kafka';
import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { IntegrationsModule } from './integrations/integrations.module';
import { TokenVaultModule } from './token-vault/token-vault.module';
import { HealthModule } from './health/health.module';
import { JwtAuthGuard } from './common/guards/jwt-auth.guard';
import { RolesGuard } from './common/guards/roles.guard';
import { TenantContextInterceptor } from './common/interceptors/tenant-context.interceptor';
import { GlobalExceptionFilter } from './common/filters/global-exception.filter';

@Module({
  imports: [
    // Load environment variables globally
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env', '../../.env.local', '../../.env'],
    }),

    // Scheduled tasks (cron jobs for token refresh, etc.)
    ScheduleModule.forRoot(),

    // Global Prisma database access
    PrismaModule,

    // Authentication module (JWT verification only)
    AuthModule,

    // Token vault for encrypted credential storage
    TokenVaultModule,

    // Kafka event bus
    KafkaModule.register({
      clientId: 'integration-hub',
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      consumerGroupId: 'integration-consumers',
    }),

    // Integration connections and catalog
    IntegrationsModule,

    // Rate limiting — 1000 requests/min per tenant (P3 spec: General API)
    ThrottlerModule.forRoot([{ ttl: 60000, limit: 1000 }]),

    // Health checks (liveness + readiness probes)
    HealthModule,
  ],
  controllers: [],
  providers: [
    // Global exception filter — catches all errors and returns a standardized envelope
    {
      provide: APP_FILTER,
      useClass: GlobalExceptionFilter,
    },

    // Global rate limiter guard
    {
      provide: APP_GUARD,
      useClass: ThrottlerGuard,
    },

    // Global JWT guard — every route requires auth unless decorated with @Public()
    {
      provide: APP_GUARD,
      useClass: JwtAuthGuard,
    },

    // Global roles guard — checks @Roles() metadata after JWT validation
    {
      provide: APP_GUARD,
      useClass: RolesGuard,
    },

    // Global interceptor — sets app.tenant_id for RLS on every request
    {
      provide: APP_INTERCEPTOR,
      useClass: TenantContextInterceptor,
    },
  ],
})
export class AppModule {}
