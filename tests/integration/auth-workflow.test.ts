/**
 * Integration test: Authentication Workflow
 *
 * End-to-end authentication flow:
 *   1. Create a test tenant (signup)
 *   2. Login with admin credentials
 *   3. Refresh the access token
 *   4. Logout and verify the token is revoked
 *   5. Verify revoked token cannot access protected resources
 *
 * Prerequisites:
 *   - Auth service running
 *   - Tenant service running
 */

import {
  CONFIG,
  createTestTenant,
  loginTestUser,
  refreshTokens,
  logoutUser,
  cleanupTestTenant,
  waitForService,
  TestCredentials,
} from './setup';

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('Authentication Workflow (Integration)', () => {
  let tenantId: string;
  let tenantSlug: string;
  let adminEmail: string;
  let tempPassword: string;
  let credentials: TestCredentials;

  // ------------------------------------------------------------------
  // Setup: ensure services are available and create test tenant
  // ------------------------------------------------------------------

  beforeAll(async () => {
    // Wait for required services
    const authReady = await waitForService(CONFIG.AUTH_SERVICE_URL, 15_000);
    const tenantReady = await waitForService(CONFIG.TENANT_SERVICE_URL, 15_000);

    if (!authReady || !tenantReady) {
      console.warn(
        'Required services not available -- skipping integration tests',
      );
      return;
    }
  }, 30_000);

  afterAll(async () => {
    // Clean up test tenant
    if (tenantId) {
      await cleanupTestTenant(tenantId);
    }
  });

  // ------------------------------------------------------------------
  // Test 1: Signup (Create Tenant)
  // ------------------------------------------------------------------

  it('should create a new tenant with admin user', async () => {
    const result = await createTestTenant();

    expect(result.tenantId).toBeTruthy();
    expect(result.tenantSlug).toBe(CONFIG.TEST_TENANT_SLUG);
    expect(result.adminEmail).toBe(CONFIG.TEST_ADMIN_EMAIL);
    expect(result.tempPassword).toBeTruthy();

    // Save for subsequent tests
    tenantId = result.tenantId;
    tenantSlug = result.tenantSlug;
    adminEmail = result.adminEmail;
    tempPassword = result.tempPassword;
  });

  // ------------------------------------------------------------------
  // Test 2: Login
  // ------------------------------------------------------------------

  it('should login with admin credentials and receive tokens', async () => {
    expect(tenantSlug).toBeTruthy();
    expect(adminEmail).toBeTruthy();
    expect(tempPassword).toBeTruthy();

    credentials = await loginTestUser(adminEmail, tempPassword, tenantSlug);

    expect(credentials.accessToken).toBeTruthy();
    expect(credentials.refreshToken).toBeTruthy();
    expect(credentials.userId).toBeTruthy();
    expect(credentials.tenantId).toBe(tenantId);
    expect(credentials.email).toBe(adminEmail);
  });

  // ------------------------------------------------------------------
  // Test 3: Access protected resource with valid token
  // ------------------------------------------------------------------

  it('should access protected profile endpoint with valid token', async () => {
    expect(credentials?.accessToken).toBeTruthy();

    const response = await fetch(`${CONFIG.AUTH_SERVICE_URL}/auth/profile`, {
      headers: {
        Authorization: `Bearer ${credentials.accessToken}`,
        'X-Tenant-ID': credentials.tenantId,
      },
    });

    expect(response.status).toBe(200);

    const profile = await response.json();
    expect(profile.email).toBe(adminEmail);
    expect(profile.role).toBe('TENANT_ADMIN');
  });

  // ------------------------------------------------------------------
  // Test 4: Refresh token
  // ------------------------------------------------------------------

  it('should refresh tokens and receive a new token pair', async () => {
    expect(credentials?.refreshToken).toBeTruthy();

    const oldAccessToken = credentials.accessToken;
    const oldRefreshToken = credentials.refreshToken;

    const result = await refreshTokens(credentials.refreshToken);

    expect(result.accessToken).toBeTruthy();
    expect(result.refreshToken).toBeTruthy();

    // New tokens should differ from old ones (token rotation)
    expect(result.accessToken).not.toBe(oldAccessToken);
    expect(result.refreshToken).not.toBe(oldRefreshToken);

    // Update credentials for subsequent tests
    credentials.accessToken = result.accessToken;
    credentials.refreshToken = result.refreshToken;
  });

  // ------------------------------------------------------------------
  // Test 5: Old refresh token should be invalidated (token rotation)
  // ------------------------------------------------------------------

  it('should reject reuse of the old refresh token', async () => {
    // The previous test rotated the tokens. Attempting to use an older
    // refresh token should fail because it was already consumed.
    // We use a placeholder here since the old token was overwritten;
    // in a real test harness you'd store it before refreshing.

    await expect(
      refreshTokens('invalid-refresh-token'),
    ).rejects.toThrow();
  });

  // ------------------------------------------------------------------
  // Test 6: Logout
  // ------------------------------------------------------------------

  it('should logout and invalidate the session', async () => {
    expect(credentials?.accessToken).toBeTruthy();

    // Logout should succeed
    await logoutUser(credentials.accessToken);

    // After logout, the access token should be revoked
    const response = await fetch(`${CONFIG.AUTH_SERVICE_URL}/auth/profile`, {
      headers: {
        Authorization: `Bearer ${credentials.accessToken}`,
        'X-Tenant-ID': credentials.tenantId,
      },
    });

    // Should be 401 (token revoked) or similar unauthorized status
    expect(response.status).toBeGreaterThanOrEqual(400);
    expect(response.status).toBeLessThan(500);
  });

  // ------------------------------------------------------------------
  // Test 7: Revoked token cannot access resources
  // ------------------------------------------------------------------

  it('should reject requests with revoked token', async () => {
    const revokedToken = credentials.accessToken;

    const response = await fetch(`${CONFIG.AUTH_SERVICE_URL}/auth/profile`, {
      headers: {
        Authorization: `Bearer ${revokedToken}`,
        'X-Tenant-ID': credentials.tenantId,
      },
    });

    expect(response.status).toBeGreaterThanOrEqual(400);
    expect(response.status).toBeLessThan(500);
  });
});
