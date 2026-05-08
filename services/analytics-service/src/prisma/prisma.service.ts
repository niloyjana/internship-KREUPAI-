import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  async onModuleInit(): Promise<void> {
    await this.$connect();
  }

  async onModuleDestroy(): Promise<void> {
    await this.$disconnect();
  }

  /**
   * Sets the PostgreSQL session variable `app.tenant_id` so that
   * Row-Level Security (RLS) policies can reference it via
   * `current_setting('app.tenant_id')`.
   */
  async setTenantId(tenantId: string): Promise<void> {
    await this.$executeRawUnsafe(
      `SET LOCAL app.tenant_id = '${tenantId.replace(/'/g, "''")}'`,
    );
  }
}
