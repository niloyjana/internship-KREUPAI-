import {
  BadRequestException,
  ConflictException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  KafkaProducerService,
  AuditService,
  TOPICS,
  TenantProvisionedPayload,
  TenantConfigUpdatedPayload,
} from '@adwp/kafka';
import { CreateTenantDto } from './dto/create-tenant.dto';
import { UpdateTenantDto } from './dto/update-tenant.dto';
import { InviteUserDto } from './dto/invite-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { PaginationDto } from './dto/pagination.dto';
import * as crypto from 'crypto';

@Injectable()
export class TenantsService {
  private readonly logger = new Logger(TenantsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly kafkaProducer: KafkaProducerService,
    private readonly audit: AuditService,
  ) {}

  // ─── CREATE TENANT ─────────────────────────────────────────────────────────

  async createTenant(dto: CreateTenantDto) {
    // Validate slug uniqueness
    const existingTenant = await this.prisma.tenant.findUnique({
      where: { slug: dto.slug },
    });

    if (existingTenant) {
      throw new ConflictException(`Tenant with slug "${dto.slug}" already exists`);
    }

    // Check if admin email is already taken
    const existingUser = await this.prisma.user.findUnique({
      where: { email: dto.adminEmail },
    });

    if (existingUser) {
      throw new ConflictException(`User with email "${dto.adminEmail}" already exists`);
    }

    // Hash the admin password (generate a temporary one)
    const tempPassword = this.generateTempPassword();
    const passwordHash = await this.hashPassword(tempPassword);

    // Create Tenant + User + TenantUser in a single transaction
    const result = await this.prisma.$transaction(async (tx) => {
      // 1. Create the tenant
      const tenant = await tx.tenant.create({
        data: {
          name: dto.name,
          slug: dto.slug,
          plan: dto.plan || 'STARTER',
          status: 'TRIAL',
          countryCode: dto.countryCode || 'BH',
          timezone: dto.timezone || 'UTC',
          trialEndsAt: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), // 14-day trial
        },
      });

      // 2. Create the admin user
      const user = await tx.user.create({
        data: {
          email: dto.adminEmail,
          name: dto.adminName,
          passwordHash,
        },
      });

      // 3. Link user to tenant as TENANT_ADMIN
      const tenantUser = await tx.tenantUser.create({
        data: {
          tenantId: tenant.id,
          userId: user.id,
          role: 'TENANT_ADMIN',
          status: 'ACTIVE',
        },
      });

      return { tenant, user, tenantUser };
    });

    // Publish tenant.provisioned event to Kafka
    await this.kafkaProducer.emit<TenantProvisionedPayload>(TOPICS.TENANT_PROVISIONED, {
      tenantId: result.tenant.id,
      source: 'tenant-service',
      payload: {
        tenantId: result.tenant.id,
        name: result.tenant.name,
        slug: result.tenant.slug,
        plan: result.tenant.plan as 'STARTER' | 'GROWTH' | 'ENTERPRISE' | 'CUSTOM',
        adminUserId: result.user.id,
        adminEmail: result.user.email,
        countryCode: result.tenant.countryCode ?? 'BH',
        timezone: result.tenant.timezone ?? 'UTC',
      },
    });

    await this.audit.publishAudit({
      tenantId: result.tenant.id,
      actorType: 'USER',
      actorId: result.user.id,
      action: 'TENANT_CREATED',
      entityType: 'TENANT',
      entityId: result.tenant.id,
      after: { slug: result.tenant.slug, plan: result.tenant.plan },
    });

    return {
      tenant: this.sanitizeTenant(result.tenant),
      admin: {
        id: result.user.id,
        email: result.user.email,
        name: result.user.name,
        role: result.tenantUser.role,
        tempPassword, // Return temp password so it can be communicated to admin
      },
    };
  }

  // ─── GET TENANT ─────────────────────────────────────────────────────────────

  async getTenant(tenantId: string) {
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

    return {
      ...this.sanitizeTenant(tenant),
      activeUserCount: tenant._count.users,
      agentCount: tenant._count.agentConfigs,
    };
  }

  // ─── UPDATE TENANT ──────────────────────────────────────────────────────────

  async updateTenant(tenantId: string, dto: UpdateTenantDto) {
    // Ensure tenant exists
    const existing = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!existing) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    const updateData: any = {};

    if (dto.name !== undefined) updateData.name = dto.name;
    if (dto.timezone !== undefined) updateData.timezone = dto.timezone;
    if (dto.config !== undefined) updateData.config = dto.config;
    if (dto.logoUrl !== undefined) updateData.logoUrl = dto.logoUrl;
    if (dto.primaryColor !== undefined) updateData.primaryColor = dto.primaryColor;

    const updated = await this.prisma.tenant.update({
      where: { id: tenantId },
      data: updateData,
    });

    // Publish tenant.config.updated event to Kafka
    await this.kafkaProducer.emit<TenantConfigUpdatedPayload>(TOPICS.TENANT_CONFIG_UPDATED, {
      tenantId: updated.id,
      source: 'tenant-service',
      payload: {
        tenantId: updated.id,
        agentId: null,
        configSection: 'branding',
        changedKeys: Object.keys(updateData),
        changedByUserId: 'system',
      },
    });

    await this.audit.publishAudit({
      tenantId: tenantId,
      actorType: 'USER',
      actorId: 'system', // caller identity not available at service layer
      action: 'TENANT_UPDATED',
      entityType: 'TENANT',
      entityId: tenantId,
      before: { name: existing.name, timezone: existing.timezone },
      after: updateData,
    });

    return this.sanitizeTenant(updated);
  }

  // ─── LIST USERS ─────────────────────────────────────────────────────────────

  async listUsers(tenantId: string, query: PaginationDto) {
    // Ensure tenant exists
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    const page = query.page || 1;
    const pageSize = query.pageSize || 20;
    const skip = (page - 1) * pageSize;

    // Build where clause with optional filters
    const where: any = { tenantId };

    if (query.role) {
      where.role = query.role;
    }

    if (query.status) {
      where.status = query.status;
    }

    // Determine sort field -- only allow safe fields
    const allowedSortFields = ['createdAt', 'updatedAt', 'role', 'status'];
    const sortBy = allowedSortFields.includes(query.sortBy || '') ? query.sortBy : 'createdAt';
    const sortDir = query.sortDir || 'desc';

    const [tenantUsers, total] = await Promise.all([
      this.prisma.tenantUser.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy!]: sortDir },
        include: {
          user: {
            select: {
              id: true,
              email: true,
              name: true,
              avatarUrl: true,
              phone: true,
              lastLoginAt: true,
              createdAt: true,
            },
          },
        },
      }),
      this.prisma.tenantUser.count({ where }),
    ]);

    const users = tenantUsers.map((tu) => ({
      id: tu.user.id,
      tenantUserId: tu.id,
      email: tu.user.email,
      name: tu.user.name,
      avatarUrl: tu.user.avatarUrl,
      phone: tu.user.phone,
      role: tu.role,
      status: tu.status,
      department: tu.department,
      lastLoginAt: tu.user.lastLoginAt,
      joinedAt: tu.createdAt,
      userCreatedAt: tu.user.createdAt,
    }));

    return {
      users,
      meta: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  // ─── INVITE USER ────────────────────────────────────────────────────────────

  async inviteUser(tenantId: string, dto: InviteUserDto) {
    // Ensure tenant exists
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: tenantId },
    });

    if (!tenant) {
      throw new NotFoundException(`Tenant with id "${tenantId}" not found`);
    }

    // Check if user with this email already exists
    let user = await this.prisma.user.findUnique({
      where: { email: dto.email },
    });

    if (user) {
      // Check if user is already in this tenant
      const existingTenantUser = await this.prisma.tenantUser.findUnique({
        where: {
          tenantId_userId: {
            tenantId,
            userId: user.id,
          },
        },
      });

      if (existingTenantUser) {
        throw new ConflictException(`User "${dto.email}" is already a member of this tenant`);
      }
    }

    // Generate temporary password for the new user
    const tempPassword = this.generateTempPassword();
    const passwordHash = await this.hashPassword(tempPassword);

    const result = await this.prisma.$transaction(async (tx) => {
      // Create user if they don't exist
      if (!user) {
        user = await tx.user.create({
          data: {
            email: dto.email,
            name: dto.name,
            passwordHash,
          },
        });
      }

      // Create the TenantUser link with INVITED status
      const tenantUser = await tx.tenantUser.create({
        data: {
          tenantId,
          userId: user!.id,
          role: dto.role,
          status: 'INVITED',
          department: dto.department,
        },
      });

      return { user: user!, tenantUser };
    });

    this.logger.log(`User ${dto.email} invited to tenant ${tenantId} with role ${dto.role}`);

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'USER_INVITED',
      entityType: 'USER',
      entityId: result.user.id,
      after: { email: dto.email, role: dto.role },
    });

    return {
      id: result.user.id,
      tenantUserId: result.tenantUser.id,
      email: result.user.email,
      name: result.user.name,
      role: result.tenantUser.role,
      status: result.tenantUser.status,
      department: result.tenantUser.department,
      tempPassword, // Return so it can be sent via email/notification
    };
  }

  // ─── UPDATE USER ────────────────────────────────────────────────────────────

  async updateUser(tenantId: string, userId: string, dto: UpdateUserDto) {
    // Find the TenantUser record
    const tenantUser = await this.prisma.tenantUser.findUnique({
      where: {
        tenantId_userId: {
          tenantId,
          userId,
        },
      },
      include: {
        user: {
          select: { id: true, email: true, name: true },
        },
      },
    });

    if (!tenantUser) {
      throw new NotFoundException(`User "${userId}" not found in tenant "${tenantId}"`);
    }

    const updateData: any = {};

    if (dto.role !== undefined) updateData.role = dto.role;
    if (dto.status !== undefined) updateData.status = dto.status;
    if (dto.department !== undefined) updateData.department = dto.department;

    if (Object.keys(updateData).length === 0) {
      throw new BadRequestException('No fields to update');
    }

    const updated = await this.prisma.tenantUser.update({
      where: {
        tenantId_userId: {
          tenantId,
          userId,
        },
      },
      data: updateData,
      include: {
        user: {
          select: {
            id: true,
            email: true,
            name: true,
            avatarUrl: true,
          },
        },
      },
    });

    return {
      id: updated.user.id,
      tenantUserId: updated.id,
      email: updated.user.email,
      name: updated.user.name,
      avatarUrl: updated.user.avatarUrl,
      role: updated.role,
      status: updated.status,
      department: updated.department,
      updatedAt: updated.updatedAt,
    };
  }

  // ─── REMOVE USER ────────────────────────────────────────────────────────────

  async removeUser(tenantId: string, userId: string) {
    // Find the TenantUser record
    const tenantUser = await this.prisma.tenantUser.findUnique({
      where: {
        tenantId_userId: {
          tenantId,
          userId,
        },
      },
      include: {
        user: {
          select: { id: true, email: true, name: true },
        },
      },
    });

    if (!tenantUser) {
      throw new NotFoundException(`User "${userId}" not found in tenant "${tenantId}"`);
    }

    // Prevent removing the last TENANT_ADMIN
    if (tenantUser.role === 'TENANT_ADMIN') {
      const adminCount = await this.prisma.tenantUser.count({
        where: {
          tenantId,
          role: 'TENANT_ADMIN',
          status: { in: ['ACTIVE', 'INVITED'] },
        },
      });

      if (adminCount <= 1) {
        throw new BadRequestException(
          'Cannot remove the last tenant admin. Assign another admin first.',
        );
      }
    }

    // Delete the TenantUser record (not the User itself)
    await this.prisma.tenantUser.delete({
      where: {
        tenantId_userId: {
          tenantId,
          userId,
        },
      },
    });

    this.logger.log(`User ${tenantUser.user.email} removed from tenant ${tenantId}`);

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: 'system',
      action: 'USER_REMOVED',
      entityType: 'USER',
      entityId: userId,
      before: { email: tenantUser.user.email, role: tenantUser.role },
    });

    return {
      id: tenantUser.user.id,
      email: tenantUser.user.email,
      name: tenantUser.user.name,
      removedAt: new Date().toISOString(),
    };
  }

  // ─── HELPERS ────────────────────────────────────────────────────────────────

  /**
   * Generate a cryptographically secure temporary password.
   * 16 chars, base64url-safe.
   */
  private generateTempPassword(): string {
    return crypto.randomBytes(12).toString('base64url');
  }

  /**
   * Hash a password using scrypt (Node.js built-in, no bcrypt dependency needed).
   */
  private async hashPassword(password: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const salt = crypto.randomBytes(16).toString('hex');
      crypto.scrypt(password, salt, 64, (err, derivedKey) => {
        if (err) reject(err);
        resolve(`${salt}:${derivedKey.toString('hex')}`);
      });
    });
  }

  /**
   * Strip internal/sensitive fields from tenant for API responses.
   */
  private sanitizeTenant(tenant: any) {
    const { stripeCustomerId, deletedAt, ...safe } = tenant;
    return safe;
  }
}
