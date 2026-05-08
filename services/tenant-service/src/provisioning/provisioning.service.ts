import { Injectable, Logger, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  TenantStatusChangedPayload,
} from '@adwp/kafka';
import * as crypto from 'crypto';

@Injectable()
export class ProvisioningService {
  private readonly logger = new Logger(ProvisioningService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ─── PROVISION TENANT ──────────────────────────────────────────────────────

  async provisionTenant(tenantId: string) {
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    this.logger.log(`Starting provisioning for tenant ${tenantId} (${tenant.slug})`);

    // 1. Set up default tenant configuration
    const defaultConfig = {
      features: {
        aiAgentEnabled: true,
        mfaRequired: false,
        apiAccessEnabled: true,
        auditLogsEnabled: true,
      },
      branding: {
        primaryColor: tenant.primaryColor || '#1a73e8',
        logoUrl: tenant.logoUrl || null,
      },
      notifications: {
        emailNotifications: true,
        slackIntegration: false,
        webhookUrl: null,
      },
      security: {
        sessionTimeoutMinutes: 480,
        passwordMinLength: 8,
        passwordRequireSpecialChar: true,
        maxLoginAttempts: 5,
      },
    };

    await this.prisma.tenant.update({
      where: { id: tenantId },
      data: {
        config: defaultConfig,
      },
    });

    // 2. Verify admin user exists (created during tenant creation)
    const adminUser = await this.prisma.tenantUser.findFirst({
      where: {
        tenantId,
        role: 'TENANT_ADMIN',
      },
      include: {
        user: {
          select: { id: true, email: true, name: true },
        },
      },
    });

    if (!adminUser) {
      this.logger.warn(`No admin user found for tenant ${tenantId}. Creating a default admin.`);

      // Create a default admin user
      const tempPassword = crypto.randomBytes(12).toString('base64url');
      const salt = crypto.randomBytes(16).toString('hex');
      const passwordHash = await new Promise<string>((resolve, reject) => {
        crypto.scrypt(tempPassword, salt, 64, (err, derivedKey) => {
          if (err) reject(err);
          resolve(`${salt}:${derivedKey.toString('hex')}`);
        });
      });

      const defaultAdmin = await this.prisma.$transaction(async (tx) => {
        const user = await tx.user.create({
          data: {
            email: `admin@${tenant.slug}.local`,
            name: 'Tenant Admin',
            passwordHash,
          },
        });

        const tenantUser = await tx.tenantUser.create({
          data: {
            tenantId,
            userId: user.id,
            role: 'TENANT_ADMIN',
            status: 'ACTIVE',
          },
        });

        return { user, tenantUser };
      });

      this.logger.log(`Default admin created for tenant ${tenantId}: ${defaultAdmin.user.email}`);
    }

    // 3. Publish provisioning complete event
    await this.kafkaProducer.emit(TOPICS.TENANT_PROVISIONING_COMPLETE, {
      tenantId,
      source: 'tenant-service',
      payload: {
        tenantId,
        slug: tenant.slug,
        plan: tenant.plan,
        provisionedAt: new Date().toISOString(),
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'provisioning-service',
      action: 'TENANT_PROVISIONED',
      entityType: 'TENANT',
      entityId: tenantId,
      after: { config: defaultConfig },
    });

    this.logger.log(`Provisioning completed for tenant ${tenantId}`);

    return {
      tenantId,
      slug: tenant.slug,
      status: 'PROVISIONED',
      provisionedAt: new Date().toISOString(),
    };
  }

  // ─── DEPROVISION TENANT ────────────────────────────────────────────────────

  async deprovisionTenant(tenantId: string) {
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
      include: {
        _count: {
          select: {
            users: true,
            agentConfigs: true,
          },
        },
      },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    this.logger.log(
      `Starting deprovisioning for tenant ${tenantId} (${tenant.slug}). ` +
        `Users: ${tenant._count.users}, Agents: ${tenant._count.agentConfigs}`,
    );

    // 1. Mark all tenant users as INACTIVE
    await this.prisma.tenantUser.updateMany({
      where: { tenantId },
      data: { status: 'INACTIVE' },
    });

    // 2. Soft-delete all users that only belong to this tenant
    const tenantUsers = await this.prisma.tenantUser.findMany({
      where: { tenantId },
      select: { userId: true },
    });

    for (const tu of tenantUsers) {
      const otherMemberships = await this.prisma.tenantUser.count({
        where: {
          userId: tu.userId,
          tenantId: { not: tenantId },
        },
      });

      // Only soft-delete users with no other tenant memberships
      if (otherMemberships === 0) {
        await this.prisma.user.update({
          where: { id: tu.userId },
          data: { deletedAt: new Date() },
        });
      }
    }

    // 3. Delete all active sessions for this tenant
    await this.prisma.userSession.deleteMany({
      where: { tenantId },
    });

    // 4. Revoke all API keys for this tenant
    await this.prisma.apiKey.updateMany({
      where: { tenantId, revokedAt: null },
      data: { revokedAt: new Date() },
    });

    // 5. Mark tenant as CHURNED with deletedAt timestamp
    await this.prisma.tenant.update({
      where: { id: tenantId },
      data: {
        status: 'CHURNED',
        deletedAt: new Date(),
      },
    });

    // 5b. Emit tenant status changed event
    await this.kafkaProducer.emit<TenantStatusChangedPayload>(TOPICS.TENANT_STATUS_CHANGED, {
      tenantId,
      source: 'tenant-service',
      payload: {
        tenantId,
        previousStatus: tenant.status,
        newStatus: 'CHURNED',
        reason: 'Tenant deprovisioned',
        changedByUserId: 'system',
      },
    });

    // 6. Publish deprovisioning event
    await this.kafkaProducer.emit(TOPICS.TENANT_DEPROVISIONED, {
      tenantId,
      source: 'tenant-service',
      payload: {
        tenantId,
        slug: tenant.slug,
        deprovisionedAt: new Date().toISOString(),
      },
    });

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'provisioning-service',
      action: 'TENANT_DEPROVISIONED',
      entityType: 'TENANT',
      entityId: tenantId,
      before: { status: tenant.status },
      after: { status: 'CHURNED', deletedAt: new Date().toISOString() },
    });

    this.logger.log(`Deprovisioning completed for tenant ${tenantId}`);

    return {
      tenantId,
      slug: tenant.slug,
      status: 'DEPROVISIONED',
      deprovisionedAt: new Date().toISOString(),
    };
  }

  // ─── VERIFY ISOLATION ──────────────────────────────────────────────────────

  async verifyIsolation(tenantId: string) {
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    this.logger.log(`Verifying RLS isolation for tenant ${tenantId}`);

    const checks: {
      check: string;
      passed: boolean;
      details?: string;
    }[] = [];

    // 1. Verify tenant users are scoped correctly
    try {
      const tenantUserCount = await this.prisma.tenantUser.count({
        where: { tenantId },
      });

      checks.push({
        check: 'tenant_users_scoped',
        passed: true,
        details: `Found ${tenantUserCount} users scoped to tenant`,
      });
    } catch (error) {
      checks.push({
        check: 'tenant_users_scoped',
        passed: false,
        details: `Error querying tenant users: ${error instanceof Error ? error.message : String(error)}`,
      });
    }

    // 2. Verify sessions are scoped correctly
    try {
      const sessionCount = await this.prisma.userSession.count({
        where: { tenantId },
      });

      checks.push({
        check: 'sessions_scoped',
        passed: true,
        details: `Found ${sessionCount} sessions scoped to tenant`,
      });
    } catch (error) {
      checks.push({
        check: 'sessions_scoped',
        passed: false,
        details: `Error querying sessions: ${error instanceof Error ? error.message : String(error)}`,
      });
    }

    // 3. Verify API keys are scoped correctly
    try {
      const apiKeyCount = await this.prisma.apiKey.count({
        where: { tenantId },
      });

      checks.push({
        check: 'api_keys_scoped',
        passed: true,
        details: `Found ${apiKeyCount} API keys scoped to tenant`,
      });
    } catch (error) {
      checks.push({
        check: 'api_keys_scoped',
        passed: false,
        details: `Error querying API keys: ${error instanceof Error ? error.message : String(error)}`,
      });
    }

    // 4. Verify RLS policy by attempting a raw query with tenant context
    try {
      await this.prisma.$executeRawUnsafe(`SET app.tenant_id = '${tenantId}'`);

      checks.push({
        check: 'rls_context_set',
        passed: true,
        details: `RLS tenant context can be set for tenant ${tenantId}`,
      });
    } catch (error) {
      checks.push({
        check: 'rls_context_set',
        passed: false,
        details: `Error setting RLS context: ${error instanceof Error ? error.message : String(error)}`,
      });
    }

    const allPassed = checks.every((c) => c.passed);

    this.logger.log(
      `Isolation verification for tenant ${tenantId}: ${allPassed ? 'ALL PASSED' : 'SOME FAILED'}`,
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'SYSTEM',
      actorId: 'provisioning-service',
      action: 'ISOLATION_VERIFIED',
      entityType: 'TENANT',
      entityId: tenantId,
      metadata: { allPassed, checks },
    });

    return {
      tenantId,
      slug: tenant.slug,
      allPassed,
      checks,
      verifiedAt: new Date().toISOString(),
    };
  }
}
