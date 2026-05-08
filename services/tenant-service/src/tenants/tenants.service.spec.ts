import { Test, TestingModule } from '@nestjs/testing';
import {
  ConflictException,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import { TenantsService } from './tenants.service';
import { PrismaService } from '../prisma/prisma.service';

// ---------------------------------------------------------------------------
// Mock factories
// ---------------------------------------------------------------------------

const mockPrismaService = () => ({
  tenant: {
    findUnique: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
  },
  user: {
    findUnique: jest.fn(),
    create: jest.fn(),
  },
  tenantUser: {
    findUnique: jest.fn(),
    create: jest.fn(),
    delete: jest.fn(),
    count: jest.fn(),
    update: jest.fn(),
    findMany: jest.fn(),
  },
  $transaction: jest.fn(),
});

const mockKafkaProducerService = () => ({
  emit: jest.fn().mockResolvedValue(undefined),
});

const mockAuditService = () => ({
  publishAudit: jest.fn().mockResolvedValue(undefined),
});

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const testTenant = {
  id: 'tenant-001',
  name: 'Test Corp',
  slug: 'test-corp',
  plan: 'STARTER',
  status: 'TRIAL',
  countryCode: 'BH',
  timezone: 'UTC',
  stripeCustomerId: null,
  deletedAt: null,
  trialEndsAt: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
  createdAt: new Date(),
  updatedAt: new Date(),
};

const testUser = {
  id: 'user-001',
  email: 'admin@test-corp.com',
  name: 'Admin User',
  passwordHash: 'hashed-password',
};

const testTenantUser = {
  id: 'tu-001',
  tenantId: 'tenant-001',
  userId: 'user-001',
  role: 'TENANT_ADMIN',
  status: 'ACTIVE',
  department: null,
  createdAt: new Date(),
  updatedAt: new Date(),
};

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('TenantsService', () => {
  let service: TenantsService;
  let prisma: ReturnType<typeof mockPrismaService>;
  let kafka: ReturnType<typeof mockKafkaProducerService>;
  let audit: ReturnType<typeof mockAuditService>;

  beforeEach(async () => {
    prisma = mockPrismaService();
    kafka = mockKafkaProducerService();
    audit = mockAuditService();

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        TenantsService,
        { provide: PrismaService, useValue: prisma },
        { provide: 'KafkaProducerService', useValue: kafka },
        { provide: 'AuditService', useValue: audit },
      ],
    }).compile();

    service = module.get<TenantsService>(TenantsService);
  });

  // ----------------------------------------------------------------
  // CREATE TENANT
  // ----------------------------------------------------------------

  describe('createTenant', () => {
    it('should create tenant, admin user, and link them', async () => {
      prisma.tenant.findUnique.mockResolvedValue(null); // No existing tenant
      prisma.user.findUnique.mockResolvedValue(null); // No existing user

      prisma.$transaction.mockImplementation(async (fn: any) => {
        const tx = {
          tenant: { create: jest.fn().mockResolvedValue(testTenant) },
          user: { create: jest.fn().mockResolvedValue(testUser) },
          tenantUser: { create: jest.fn().mockResolvedValue(testTenantUser) },
        };
        return fn(tx);
      });

      const result = await service.createTenant({
        name: 'Test Corp',
        slug: 'test-corp',
        adminEmail: 'admin@test-corp.com',
        adminName: 'Admin User',
        plan: 'STARTER',
      } as any);

      expect(result).toHaveProperty('tenant');
      expect(result).toHaveProperty('admin');
      expect(result.admin.email).toBe('admin@test-corp.com');
      expect(result.admin).toHaveProperty('tempPassword');
      expect(kafka.emit).toHaveBeenCalled();
      expect(audit.publishAudit).toHaveBeenCalled();
    });

    it('should throw ConflictException when slug already exists', async () => {
      prisma.tenant.findUnique.mockResolvedValue(testTenant);

      await expect(
        service.createTenant({
          name: 'Test Corp',
          slug: 'test-corp',
          adminEmail: 'new@test-corp.com',
          adminName: 'New Admin',
        } as any),
      ).rejects.toThrow(ConflictException);
    });
  });

  // ----------------------------------------------------------------
  // GET TENANT
  // ----------------------------------------------------------------

  describe('getTenant', () => {
    it('should return tenant with counts', async () => {
      prisma.tenant.findUnique.mockResolvedValue({
        ...testTenant,
        _count: { users: 5, agentConfigs: 3 },
      });

      const result = await service.getTenant('tenant-001');

      expect(result.id).toBe('tenant-001');
      expect(result.name).toBe('Test Corp');
      expect(result.userCount).toBe(5);
      expect(result.agentCount).toBe(3);
      // Should not expose stripeCustomerId
      expect(result).not.toHaveProperty('stripeCustomerId');
    });

    it('should throw NotFoundException for unknown tenant', async () => {
      prisma.tenant.findUnique.mockResolvedValue(null);

      await expect(service.getTenant('unknown-id')).rejects.toThrow(
        NotFoundException,
      );
    });
  });

  // ----------------------------------------------------------------
  // UPDATE TENANT
  // ----------------------------------------------------------------

  describe('updateTenant', () => {
    it('should update tenant fields and publish Kafka event', async () => {
      prisma.tenant.findUnique.mockResolvedValue(testTenant);
      prisma.tenant.update.mockResolvedValue({
        ...testTenant,
        name: 'Updated Corp',
        timezone: 'Asia/Bahrain',
      });

      const result = await service.updateTenant('tenant-001', {
        name: 'Updated Corp',
        timezone: 'Asia/Bahrain',
      } as any);

      expect(result.name).toBe('Updated Corp');
      expect(kafka.emit).toHaveBeenCalled();
      expect(audit.publishAudit).toHaveBeenCalled();
    });

    it('should throw NotFoundException for unknown tenant', async () => {
      prisma.tenant.findUnique.mockResolvedValue(null);

      await expect(
        service.updateTenant('unknown-id', { name: 'New Name' } as any),
      ).rejects.toThrow(NotFoundException);
    });
  });

  // ----------------------------------------------------------------
  // INVITE USER
  // ----------------------------------------------------------------

  describe('inviteUser', () => {
    it('should create new user and link to tenant with INVITED status', async () => {
      prisma.tenant.findUnique.mockResolvedValue(testTenant);
      prisma.user.findUnique.mockResolvedValue(null); // New user

      const newUser = { ...testUser, id: 'user-002', email: 'new@test-corp.com' };
      const newTenantUser = {
        ...testTenantUser,
        id: 'tu-002',
        userId: 'user-002',
        role: 'TEAM_MEMBER',
        status: 'INVITED',
      };

      prisma.$transaction.mockImplementation(async (fn: any) => {
        const tx = {
          user: { create: jest.fn().mockResolvedValue(newUser) },
          tenantUser: { create: jest.fn().mockResolvedValue(newTenantUser) },
        };
        return fn(tx);
      });

      const result = await service.inviteUser('tenant-001', {
        email: 'new@test-corp.com',
        name: 'New Member',
        role: 'TEAM_MEMBER',
      } as any);

      expect(result.email).toBe('new@test-corp.com');
      expect(result.status).toBe('INVITED');
      expect(result).toHaveProperty('tempPassword');
    });

    it('should throw ConflictException when user is already a member', async () => {
      prisma.tenant.findUnique.mockResolvedValue(testTenant);
      prisma.user.findUnique.mockResolvedValue(testUser);
      prisma.tenantUser.findUnique.mockResolvedValue(testTenantUser);

      await expect(
        service.inviteUser('tenant-001', {
          email: 'admin@test-corp.com',
          name: 'Admin',
          role: 'TEAM_MEMBER',
        } as any),
      ).rejects.toThrow(ConflictException);
    });
  });

  // ----------------------------------------------------------------
  // REMOVE USER
  // ----------------------------------------------------------------

  describe('removeUser', () => {
    it('should remove user from tenant', async () => {
      prisma.tenantUser.findUnique.mockResolvedValue({
        ...testTenantUser,
        role: 'TEAM_MEMBER', // Not the last admin
        user: testUser,
      });
      prisma.tenantUser.delete.mockResolvedValue(testTenantUser);

      const result = await service.removeUser('tenant-001', 'user-001');

      expect(result).toHaveProperty('removedAt');
      expect(prisma.tenantUser.delete).toHaveBeenCalled();
    });

    it('should throw NotFoundException for unknown user', async () => {
      prisma.tenantUser.findUnique.mockResolvedValue(null);

      await expect(
        service.removeUser('tenant-001', 'unknown-user'),
      ).rejects.toThrow(NotFoundException);
    });

    it('should prevent removing the last tenant admin', async () => {
      prisma.tenantUser.findUnique.mockResolvedValue({
        ...testTenantUser,
        role: 'TENANT_ADMIN',
        user: testUser,
      });
      prisma.tenantUser.count.mockResolvedValue(1); // Only 1 admin

      await expect(
        service.removeUser('tenant-001', 'user-001'),
      ).rejects.toThrow(BadRequestException);
    });
  });
});
