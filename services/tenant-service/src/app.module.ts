import { Module } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { ConfigModule } from '@nestjs/config';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { KafkaModule } from '@adwp/kafka';
import { HealthModule } from './health/health.module';
import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { TenantsModule } from './tenants/tenants.module';
import { PlansModule } from './plans/plans.module';
import { ProvisioningModule } from './provisioning/provisioning.module';
import { JwtAuthGuard } from './common/guards/jwt-auth.guard';
import { RolesGuard } from './common/guards/roles.guard';
import { GlobalExceptionFilter } from './common/filters/global-exception.filter';
import { TenantContextInterceptor } from './common/interceptors/tenant-context.interceptor';

@Module({
  imports: [
    // Load environment variables globally
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env', '../../.env.local', '../../.env'],
    }),

    // Global Prisma database module
    PrismaModule,

    // Auth module (JWT validation via public key from auth-service)
    AuthModule,

    // Kafka event bus
    KafkaModule.register({
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      clientId: 'tenant-service',
      consumerGroupId: 'tenant-consumers',
    }),

    // Tenant management module
    TenantsModule,

    // Plans module (plan listing, upgrade, downgrade)
    PlansModule,

    // Provisioning module (tenant setup, teardown, isolation verification)
    ProvisioningModule,

    // Rate limiting — 1000 requests/min per tenant (P3 spec: General API)
    ThrottlerModule.forRoot([{ ttl: 60000, limit: 1000 }]),

    // Health checks (liveness + readiness probes)
    HealthModule,
  ],
  controllers: [],
  providers: [
    // Global exception filter — catches all unhandled exceptions
    {
      provide: APP_FILTER,
      useClass: GlobalExceptionFilter,
    },

    // Global rate limiter guard
    {
      provide: APP_GUARD,
      useClass: ThrottlerGuard,
    },

    // Global JWT auth guard — all routes require auth by default
    {
      provide: APP_GUARD,
      useClass: JwtAuthGuard,
    },

    // Global roles guard — checks @Roles() decorator
    {
      provide: APP_GUARD,
      useClass: RolesGuard,
    },

    // Global tenant context interceptor — validates tenant access
    {
      provide: APP_INTERCEPTOR,
      useClass: TenantContextInterceptor,
    },
  ],
})
export class AppModule {}
