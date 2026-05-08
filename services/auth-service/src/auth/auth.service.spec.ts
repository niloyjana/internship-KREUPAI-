import { Test, TestingModule } from '@nestjs/testing';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import {
  UnauthorizedException,
  ForbiddenException,
  ConflictException,
} from '@nestjs/common';
import { AuthService } from './auth.service';
import { PrismaService } from '../prisma/prisma.service';
import { TokenRevocationService } from './token-revocation.service';

// ---------------------------------------------------------------------------
// Mock factories
// ---------------------------------------------------------------------------

const mockPrismaService = () => ({
  tenant: {
    findUnique: jest.fn(),
  },
  user: {
    findUnique: jest.fn(),
    update: jest.fn(),
  },
  tenantUser: {
    findUnique: jest.fn(),
  },
  userSession: {
    create: jest.fn(),
    findUnique: jest.fn(),
    delete: jest.fn(),
  },
  apiKey: {
    create: jest.fn(),
    findFirst: jest.fn(),
    update: jest.fn(),
  },
});

const mockJwtService = () => ({
  sign: jest.fn().mockReturnValue('mock-access-token-jwt'),
  decode: jest.fn().mockReturnValue({
    sub: 'user-001',
    jti: 'jti-001',
    exp: Math.floor(Date.now() / 1000) + 3600,
  }),
});

const mockConfigService = () => ({
  get: jest.fn((key: string) => {
    const config: Record<string, string> = {
      JWT_ACCESS_EXPIRY: '15m',
      JWT_REFRESH_EXPIRY: '7d',
      MFA_ISSUER: 'ADWP-TEST',
    };
    return config[key];
  }),
});

const mockTokenRevocationService = () => ({
  revokeToken: jest.fn().mockResolvedValue(undefined),
  isRevoked: jest.fn().mockResolvedValue(false),
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
  status: 'ACTIVE',
  plan: 'PROFESSIONAL',
};

const testUser = {
  id: 'user-001',
  email: 'admin@test-corp.com',
  name: 'Admin User',
  // bcrypt hash of "SecurePassword123"
  passwordHash: '$2a$10$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ12',
  avatarUrl: null,
  deletedAt: null,
  mfaEnabled: false,
  mfaSecret: null,
};

const testTenantUser = {
  id: 'tu-001',
  tenantId: 'tenant-001',
  userId: 'user-001',
  role: 'TENANT_ADMIN',
  status: 'ACTIVE',
};

const testSession = {
  id: 'session-001',
  userId: 'user-001',
  tenantId: 'tenant-001',
  token: 'mock-access-token-jwt',
  refreshToken: 'mock-refresh-token',
  expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
  user: testUser,
};

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('AuthService', () => {
  let service: AuthService;
  let prisma: ReturnType<typeof mockPrismaService>;
  let jwt: ReturnType<typeof mockJwtService>;
  let tokenRevocation: ReturnType<typeof mockTokenRevocationService>;
  let audit: ReturnType<typeof mockAuditService>;

  beforeEach(async () => {
    prisma = mockPrismaService();
    jwt = mockJwtService();
    tokenRevocation = mockTokenRevocationService();
    audit = mockAuditService();

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AuthService,
        { provide: PrismaService, useValue: prisma },
        { provide: JwtService, useValue: jwt },
        { provide: ConfigService, useFactory: mockConfigService },
        { provide: TokenRevocationService, useValue: tokenRevocation },
        { provide: 'AuditService', useValue: audit },
      ],
    }).compile();

    service = module.get<AuthService>(AuthService);
  });

  // ----------------------------------------------------------------
  // LOGIN
  // ----------------------------------------------------------------

  describe('login', () => {
    it('should return tokens and user info on valid credentials', async () => {
      prisma.tenant.findUnique.mockResolvedValue(testTenant);
      prisma.user.findUnique.mockResolvedValue(testUser);
      prisma.tenantUser.findUnique.mockResolvedValue(testTenantUser);
      prisma.userSession.create.mockResolvedValue({ id: 'session-new' });
      prisma.user.update.mockResolvedValue(testUser);

      // Mock bcrypt.compare to return true
      jest.mock('bcryptjs', () => ({
        compare: jest.fn().mockResolvedValue(true),
      }));

      // Since bcrypt is imported at module level, we patch the service method
      // by mocking the password verification directly
      const bcrypt = require('bcryptjs');
      bcrypt.compare = jest.fn().mockResolvedValue(true);

      const result = await service.login(
        'admin@test-corp.com',
        'SecurePassword123',
        'test-corp',
      );

      expect(result).toHaveProperty('accessToken');
      expect(result).toHaveProperty('refreshToken');
      expect(result).toHaveProperty('user');
      expect(result.user.email).toBe('admin@test-corp.com');
      expect(result.user.tenantId).toBe('tenant-001');
      expect(prisma.userSession.create).toHaveBeenCalled();
    });

    it('should throw UnauthorizedException for invalid credentials (unknown tenant)', async () => {
      prisma.tenant.findUnique.mockResolvedValue(null);

      await expect(
        service.login('unknown@test.com', 'password', 'unknown-tenant'),
      ).rejects.toThrow(UnauthorizedException);
    });

    it('should throw ForbiddenException for inactive tenant', async () => {
      prisma.tenant.findUnique.mockResolvedValue({
        ...testTenant,
        status: 'SUSPENDED',
      });

      await expect(
        service.login('admin@test-corp.com', 'password', 'test-corp'),
      ).rejects.toThrow(ForbiddenException);
    });
  });

  // ----------------------------------------------------------------
  // REFRESH
  // ----------------------------------------------------------------

  describe('refresh', () => {
    it('should return new tokens on valid refresh token', async () => {
      prisma.userSession.findUnique.mockResolvedValue(testSession);
      prisma.tenantUser.findUnique.mockResolvedValue(testTenantUser);
      prisma.userSession.delete.mockResolvedValue(testSession);
      prisma.userSession.create.mockResolvedValue({ id: 'session-new' });

      const result = await service.refresh('mock-refresh-token');

      expect(result).toHaveProperty('accessToken');
      expect(result).toHaveProperty('refreshToken');
      expect(result).toHaveProperty('expiresIn');
      // Old session should be deleted (token rotation)
      expect(prisma.userSession.delete).toHaveBeenCalled();
      // New session should be created
      expect(prisma.userSession.create).toHaveBeenCalled();
    });

    it('should throw UnauthorizedException for invalid refresh token', async () => {
      prisma.userSession.findUnique.mockResolvedValue(null);

      await expect(
        service.refresh('invalid-refresh-token'),
      ).rejects.toThrow(UnauthorizedException);
    });
  });

  // ----------------------------------------------------------------
  // LOGOUT
  // ----------------------------------------------------------------

  describe('logout', () => {
    it('should revoke token and delete session', async () => {
      prisma.userSession.findUnique.mockResolvedValue(testSession);
      prisma.userSession.delete.mockResolvedValue(testSession);

      const result = await service.logout('mock-access-token-jwt');

      expect(result).toEqual({ message: 'Logged out successfully' });
      expect(tokenRevocation.revokeToken).toHaveBeenCalledWith(
        'jti-001',
        expect.any(Number),
      );
      expect(prisma.userSession.delete).toHaveBeenCalled();
    });
  });

  // ----------------------------------------------------------------
  // MFA SETUP
  // ----------------------------------------------------------------

  describe('setupMfa', () => {
    it('should generate TOTP secret and otpauth URI', async () => {
      prisma.user.findUnique.mockResolvedValue({
        ...testUser,
        mfaEnabled: false,
        mfaSecret: null,
      });
      prisma.user.update.mockResolvedValue(testUser);

      const result = await service.setupMfa('user-001', 'tenant-001');

      expect(result).toHaveProperty('secret');
      expect(result).toHaveProperty('otpauthUri');
      expect(result.secret).toBeTruthy();
      expect(result.otpauthUri).toContain('otpauth://totp/');
      expect(prisma.user.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { id: 'user-001' },
          data: expect.objectContaining({ mfaSecret: expect.any(String) }),
        }),
      );
    });

    it('should throw ConflictException when MFA already enabled', async () => {
      prisma.user.findUnique.mockResolvedValue({
        ...testUser,
        mfaEnabled: true,
        mfaSecret: 'existing-secret',
      });

      await expect(
        service.setupMfa('user-001', 'tenant-001'),
      ).rejects.toThrow(ConflictException);
    });
  });

  // ----------------------------------------------------------------
  // MFA VERIFY
  // ----------------------------------------------------------------

  describe('verifyMfa', () => {
    it('should verify valid TOTP code and enable MFA on first use', async () => {
      const { authenticator } = require('otplib');
      const secret = authenticator.generateSecret();

      prisma.user.findUnique.mockResolvedValue({
        ...testUser,
        mfaEnabled: false,
        mfaSecret: secret,
      });
      prisma.user.update.mockResolvedValue(testUser);

      const validCode = authenticator.generate(secret);

      const result = await service.verifyMfa('user-001', 'tenant-001', validCode);

      expect(result).toEqual({ verified: true });
    });

    it('should throw UnauthorizedException for invalid code', async () => {
      const { authenticator } = require('otplib');
      const secret = authenticator.generateSecret();

      prisma.user.findUnique.mockResolvedValue({
        ...testUser,
        mfaEnabled: false,
        mfaSecret: secret,
      });

      await expect(
        service.verifyMfa('user-001', 'tenant-001', '000000'),
      ).rejects.toThrow(UnauthorizedException);
    });
  });
});
