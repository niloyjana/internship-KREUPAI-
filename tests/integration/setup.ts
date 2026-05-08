/**
 * Shared setup for integration tests.
 *
 * Provides:
 *   - Test tenant and user creation
 *   - Authenticated API client with token management
 *   - Cleanup utilities for test isolation
 *
 * Prerequisites:
 *   - Auth service running at AUTH_SERVICE_URL
 *   - API gateway running at API_GATEWAY_URL
 *   - Tenant service running at TENANT_SERVICE_URL
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

export const CONFIG = {
  AUTH_SERVICE_URL: process.env.AUTH_SERVICE_URL || 'http://localhost:3001',
  API_GATEWAY_URL: process.env.API_GATEWAY_URL || 'http://localhost:8000',
  TENANT_SERVICE_URL: process.env.TENANT_SERVICE_URL || 'http://localhost:3002',
  WORKFLOW_SERVICE_URL: process.env.WORKFLOW_SERVICE_URL || 'http://localhost:3005',

  TEST_TENANT_SLUG: `test-${Date.now()}`,
  TEST_TENANT_NAME: 'Integration Test Tenant',
  TEST_ADMIN_EMAIL: `admin-${Date.now()}@integration-test.com`,
  TEST_ADMIN_NAME: 'Integration Test Admin',
  TEST_ADMIN_PASSWORD: 'IntegrationTestPassword123!',
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TestCredentials {
  tenantId: string;
  tenantSlug: string;
  userId: string;
  email: string;
  accessToken: string;
  refreshToken: string;
}

export interface ApiClient {
  get: (path: string, options?: RequestInit) => Promise<Response>;
  post: (path: string, body: any, options?: RequestInit) => Promise<Response>;
  put: (path: string, body: any, options?: RequestInit) => Promise<Response>;
  delete: (path: string, options?: RequestInit) => Promise<Response>;
  credentials: TestCredentials;
  refreshTokens: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Test tenant provisioning
// ---------------------------------------------------------------------------

export async function createTestTenant(): Promise<{
  tenantId: string;
  tenantSlug: string;
  adminUserId: string;
  adminEmail: string;
  tempPassword: string;
}> {
  const response = await fetch(`${CONFIG.TENANT_SERVICE_URL}/tenants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: CONFIG.TEST_TENANT_NAME,
      slug: CONFIG.TEST_TENANT_SLUG,
      adminEmail: CONFIG.TEST_ADMIN_EMAIL,
      adminName: CONFIG.TEST_ADMIN_NAME,
      plan: 'PROFESSIONAL',
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create test tenant: ${response.status} ${error}`);
  }

  const data = await response.json();

  return {
    tenantId: data.tenant.id,
    tenantSlug: data.tenant.slug,
    adminUserId: data.admin.id,
    adminEmail: data.admin.email,
    tempPassword: data.admin.tempPassword,
  };
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

export async function loginTestUser(
  email: string,
  password: string,
  tenantSlug: string,
): Promise<TestCredentials> {
  const response = await fetch(`${CONFIG.AUTH_SERVICE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, tenantSlug }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Login failed: ${response.status} ${error}`);
  }

  const data = await response.json();

  return {
    tenantId: data.user.tenantId,
    tenantSlug,
    userId: data.user.id,
    email: data.user.email,
    accessToken: data.accessToken,
    refreshToken: data.refreshToken,
  };
}

export async function refreshTokens(refreshToken: string): Promise<{
  accessToken: string;
  refreshToken: string;
}> {
  const response = await fetch(`${CONFIG.AUTH_SERVICE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Token refresh failed: ${response.status} ${error}`);
  }

  return response.json();
}

export async function logoutUser(accessToken: string): Promise<void> {
  const response = await fetch(`${CONFIG.AUTH_SERVICE_URL}/auth/logout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Logout failed: ${response.status} ${error}`);
  }
}

// ---------------------------------------------------------------------------
// API client factory
// ---------------------------------------------------------------------------

export function createApiClient(
  credentials: TestCredentials,
  baseUrl: string = CONFIG.API_GATEWAY_URL,
): ApiClient {
  const headers = () => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${credentials.accessToken}`,
    'X-Tenant-ID': credentials.tenantId,
  });

  const client: ApiClient = {
    credentials,

    get: (path, options = {}) =>
      fetch(`${baseUrl}${path}`, {
        method: 'GET',
        headers: { ...headers(), ...((options.headers as Record<string, string>) || {}) },
        ...options,
      }),

    post: (path, body, options = {}) =>
      fetch(`${baseUrl}${path}`, {
        method: 'POST',
        headers: { ...headers(), ...((options.headers as Record<string, string>) || {}) },
        body: JSON.stringify(body),
        ...options,
      }),

    put: (path, body, options = {}) =>
      fetch(`${baseUrl}${path}`, {
        method: 'PUT',
        headers: { ...headers(), ...((options.headers as Record<string, string>) || {}) },
        body: JSON.stringify(body),
        ...options,
      }),

    delete: (path, options = {}) =>
      fetch(`${baseUrl}${path}`, {
        method: 'DELETE',
        headers: { ...headers(), ...((options.headers as Record<string, string>) || {}) },
        ...options,
      }),

    refreshTokens: async () => {
      const result = await refreshTokens(credentials.refreshToken);
      credentials.accessToken = result.accessToken;
      credentials.refreshToken = result.refreshToken;
    },
  };

  return client;
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

export async function cleanupTestTenant(tenantId: string): Promise<void> {
  try {
    await fetch(`${CONFIG.TENANT_SERVICE_URL}/tenants/${tenantId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.warn(`Cleanup: failed to delete test tenant ${tenantId}:`, err);
  }
}

// ---------------------------------------------------------------------------
// Utility: wait for service readiness
// ---------------------------------------------------------------------------

export async function waitForService(
  url: string,
  timeoutMs: number = 30_000,
): Promise<boolean> {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(`${url}/health`);
      if (response.ok) return true;
    } catch {
      // Service not ready yet
    }
    await new Promise((r) => setTimeout(r, 1000));
  }

  return false;
}
