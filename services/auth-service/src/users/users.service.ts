import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { AuditService } from '@adwp/kafka';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import * as crypto from 'crypto';

@Injectable()
export class UsersService {
  private readonly logger = new Logger(UsersService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly audit: AuditService,
  ) {}

  // ─── LIST USERS ─────────────────────────────────────────────────────────────

  async listUsers(
    tenantId: string,
    query: { page?: number; pageSize?: number },
  ) {
    const page = query.page || 1;
    const pageSize = query.pageSize || 20;
    const skip = (page - 1) * pageSize;

    const where: any = { tenantId };

    const [tenantUsers, total] = await Promise.all([
      this.prisma.tenantUser.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { createdAt: 'desc' },
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
              deletedAt: true,
            },
          },
        },
      }),
      this.prisma.tenantUser.count({ where }),
    ]);

    const users = tenantUsers
      .filter((tu) => !tu.user.deletedAt)
      .map((tu) => ({
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

  // ─── GET USER BY ID ─────────────────────────────────────────────────────────

  async getUserById(tenantId: string, userId: string) {
    const tenantUser = await this.prisma.tenantUser.findUnique({
      where: {
        tenantId_userId: {
          tenantId,
          userId,
        },
      },
      include: {
        user: {
          select: {
            id: true,
            email: true,
            name: true,
            avatarUrl: true,
            phone: true,
            mfaEnabled: true,
            lastLoginAt: true,
            createdAt: true,
            deletedAt: true,
          },
        },
      },
    });

    if (!tenantUser || tenantUser.user.deletedAt) {
      throw new NotFoundException(`User "${userId}" not found in this tenant`);
    }

    return {
      id: tenantUser.user.id,
      tenantUserId: tenantUser.id,
      email: tenantUser.user.email,
      name: tenantUser.user.name,
      avatarUrl: tenantUser.user.avatarUrl,
      phone: tenantUser.user.phone,
      mfaEnabled: tenantUser.user.mfaEnabled,
      role: tenantUser.role,
      status: tenantUser.status,
      department: tenantUser.department,
      lastLoginAt: tenantUser.user.lastLoginAt,
      joinedAt: tenantUser.createdAt,
      userCreatedAt: tenantUser.user.createdAt,
    };
  }

  // ─── CREATE USER ────────────────────────────────────────────────────────────

  async createUser(tenantId: string, actorId: string, dto: CreateUserDto) {
    // Check if user with this email already exists
    const existingUser = await this.prisma.user.findUnique({
      where: { email: dto.email.toLowerCase() },
    });

    if (existingUser) {
      // Check if user is already in this tenant
      const existingTenantUser = await this.prisma.tenantUser.findUnique({
        where: {
          tenantId_userId: {
            tenantId,
            userId: existingUser.id,
          },
        },
      });

      if (existingTenantUser) {
        throw new BadRequestException(
          `User with email "${dto.email}" is already a member of this tenant`,
        );
      }
    }

    // Generate temporary password
    const tempPassword = this.generateTempPassword();
    const passwordHash = await this.hashPassword(tempPassword);

    const result = await this.prisma.$transaction(async (tx) => {
      let user = existingUser;

      if (!user) {
        user = await tx.user.create({
          data: {
            email: dto.email.toLowerCase(),
            name: `${dto.firstName} ${dto.lastName}`,
            passwordHash,
          },
        });
      }

      const tenantUser = await tx.tenantUser.create({
        data: {
          tenantId,
          userId: user.id,
          role: dto.role || 'END_USER',
          status: 'ACTIVE',
          department: dto.department,
        },
      });

      return { user, tenantUser };
    });

    this.logger.log(
      `User ${dto.email} created in tenant ${tenantId} with role ${dto.role || 'END_USER'}`,
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId,
      action: 'USER_CREATED',
      entityType: 'USER',
      entityId: result.user.id,
      after: { email: dto.email, role: dto.role || 'END_USER' },
    });

    return {
      id: result.user.id,
      tenantUserId: result.tenantUser.id,
      email: result.user.email,
      name: result.user.name,
      role: result.tenantUser.role,
      status: result.tenantUser.status,
      department: result.tenantUser.department,
      tempPassword,
    };
  }

  // ─── UPDATE USER ────────────────────────────────────────────────────────────

  async updateUser(
    tenantId: string,
    userId: string,
    actorId: string,
    dto: UpdateUserDto,
  ) {
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
      throw new NotFoundException(
        `User "${userId}" not found in tenant "${tenantId}"`,
      );
    }

    const tenantUserUpdate: any = {};
    const userUpdate: any = {};

    if (dto.role !== undefined) tenantUserUpdate.role = dto.role;
    if (dto.status !== undefined) tenantUserUpdate.status = dto.status;

    // Update user name if firstName or lastName provided
    if (dto.firstName !== undefined || dto.lastName !== undefined) {
      const currentNameParts = (tenantUser.user.name || '').split(' ');
      const firstName = dto.firstName ?? currentNameParts[0] ?? '';
      const lastName =
        dto.lastName ?? currentNameParts.slice(1).join(' ') ?? '';
      userUpdate.name = `${firstName} ${lastName}`.trim();
    }

    if (
      Object.keys(tenantUserUpdate).length === 0 &&
      Object.keys(userUpdate).length === 0
    ) {
      throw new BadRequestException('No fields to update');
    }

    const result = await this.prisma.$transaction(async (tx) => {
      let updatedTenantUser = tenantUser;

      if (Object.keys(tenantUserUpdate).length > 0) {
        updatedTenantUser = await tx.tenantUser.update({
          where: {
            tenantId_userId: { tenantId, userId },
          },
          data: tenantUserUpdate,
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
      }

      if (Object.keys(userUpdate).length > 0) {
        await tx.user.update({
          where: { id: userId },
          data: userUpdate,
        });
      }

      return updatedTenantUser;
    });

    this.logger.log(`User ${userId} updated in tenant ${tenantId}`);

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId,
      action: 'USER_UPDATED',
      entityType: 'USER',
      entityId: userId,
      before: {
        role: tenantUser.role,
        status: tenantUser.status,
        name: tenantUser.user.name,
      },
      after: { ...tenantUserUpdate, ...userUpdate },
    });

    return {
      id: result.user.id,
      tenantUserId: result.id,
      email: result.user.email,
      name: userUpdate.name || result.user.name,
      role: result.role,
      status: result.status,
      department: result.department,
      updatedAt: result.updatedAt,
    };
  }

  // ─── DEACTIVATE USER (SOFT DELETE) ──────────────────────────────────────────

  async deactivateUser(tenantId: string, userId: string, actorId: string) {
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
      throw new NotFoundException(
        `User "${userId}" not found in tenant "${tenantId}"`,
      );
    }

    // Prevent deactivating the last TENANT_ADMIN
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
          'Cannot deactivate the last tenant admin. Assign another admin first.',
        );
      }
    }

    // Soft delete: set deletedAt on the user and mark TenantUser as INACTIVE
    await this.prisma.$transaction(async (tx) => {
      await tx.user.update({
        where: { id: userId },
        data: { deletedAt: new Date() },
      });

      await tx.tenantUser.update({
        where: {
          tenantId_userId: { tenantId, userId },
        },
        data: { status: 'INACTIVE' },
      });
    });

    this.logger.log(
      `User ${tenantUser.user.email} deactivated in tenant ${tenantId}`,
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId,
      action: 'USER_DEACTIVATED',
      entityType: 'USER',
      entityId: userId,
      before: { email: tenantUser.user.email, status: tenantUser.status },
      after: { status: 'INACTIVE', deletedAt: new Date().toISOString() },
    });

    return {
      id: tenantUser.user.id,
      email: tenantUser.user.email,
      name: tenantUser.user.name,
      deactivatedAt: new Date().toISOString(),
    };
  }

  // ─── TRIGGER PASSWORD RESET ─────────────────────────────────────────────────

  async triggerPasswordReset(
    tenantId: string,
    userId: string,
    actorId: string,
  ) {
    const tenantUser = await this.prisma.tenantUser.findUnique({
      where: {
        tenantId_userId: {
          tenantId,
          userId,
        },
      },
      include: {
        user: {
          select: { id: true, email: true, name: true, deletedAt: true },
        },
      },
    });

    if (!tenantUser || tenantUser.user.deletedAt) {
      throw new NotFoundException(
        `User "${userId}" not found in tenant "${tenantId}"`,
      );
    }

    // Generate a password reset token
    const resetToken = crypto.randomBytes(32).toString('hex');
    const resetTokenHash = crypto
      .createHash('sha256')
      .update(resetToken)
      .digest('hex');
    const resetTokenExpiresAt = new Date(Date.now() + 60 * 60 * 1000); // 1 hour

    await this.prisma.user.update({
      where: { id: userId },
      data: {
        resetToken: resetTokenHash,
        resetTokenExpiresAt,
      },
    });

    this.logger.log(
      `Password reset triggered for user ${tenantUser.user.email} in tenant ${tenantId}`,
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId,
      action: 'PASSWORD_RESET_TRIGGERED',
      entityType: 'USER',
      entityId: userId,
      metadata: { email: tenantUser.user.email },
    });

    return {
      message: 'Password reset email has been triggered',
      email: tenantUser.user.email,
      expiresAt: resetTokenExpiresAt.toISOString(),
    };
  }

  // ─── HELPERS ────────────────────────────────────────────────────────────────

  private generateTempPassword(): string {
    return crypto.randomBytes(12).toString('base64url');
  }

  private async hashPassword(password: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const salt = crypto.randomBytes(16).toString('hex');
      crypto.scrypt(password, salt, 64, (err, derivedKey) => {
        if (err) reject(err);
        resolve(`${salt}:${derivedKey.toString('hex')}`);
      });
    });
  }
}
