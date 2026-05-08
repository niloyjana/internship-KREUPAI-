import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { KafkaModule } from '@adwp/kafka';
import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { AgentsModule } from './agents/agents.module';
import { CapabilitiesModule } from './capabilities/capabilities.module';
import { PoliciesModule } from './policies/policies.module';
import { TemplatesModule } from './templates/templates.module';
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

    // Global Prisma database access
    PrismaModule,

    // Authentication module (JWT verification only)
    AuthModule,

    // Kafka event streaming
    KafkaModule.register({
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      clientId: 'agent-registry',
      consumerGroupId: 'agent-registry-group',
    }),

    // Agent registry business logic
    AgentsModule,

    // Capabilities — query agent capabilities catalog
    CapabilitiesModule,

    // Policies — agent policy versioning and rollback
    PoliciesModule,

    // Templates — config templates and agent config templating
    TemplatesModule,

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
