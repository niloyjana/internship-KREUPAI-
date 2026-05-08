/**
 * k6 Load Test: API Gateway Mixed Workload
 *
 * Tests a mixed workload against the API gateway:
 *   - GET health checks (lightweight, high frequency)
 *   - GET agent catalog (medium weight)
 *   - POST login (authentication flow)
 *
 * Ramp-up profile:
 *   - 0 -> 50 VUs over 30 seconds
 *   - Hold 50 VUs for 3 minutes
 *   - 50 -> 0 VUs ramp-down over 15 seconds
 *
 * Thresholds:
 *   - p95 response time < 500ms
 *   - Error rate < 5%
 *
 * Usage:
 *   k6 run tests/load/api-gateway.js
 *   k6 run --env BASE_URL=http://staging:8000 tests/load/api-gateway.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const errorRate = new Rate('gateway_error_rate');
const healthDuration = new Trend('health_check_duration', true);
const catalogDuration = new Trend('catalog_duration', true);
const loginDuration = new Trend('login_duration', true);
const requestCount = new Counter('gateway_requests');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH_SERVICE_URL = __ENV.AUTH_SERVICE_URL || 'http://localhost:3001';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up to 50 VUs
    { duration: '3m', target: 50 },     // Hold at 50 VUs for 3 minutes
    { duration: '15s', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],          // 95th percentile < 500ms
    gateway_error_rate: ['rate<0.05'],          // Error rate < 5%
    http_req_failed: ['rate<0.05'],             // HTTP failure rate < 5%
    health_check_duration: ['p(95)<200'],       // Health checks < 200ms
    catalog_duration: ['p(95)<500'],            // Catalog < 500ms
    login_duration: ['p(95)<1000'],             // Login < 1s
  },
  tags: {
    testSuite: 'api-gateway-load',
  },
};

// ---------------------------------------------------------------------------
// Workload weights (probability of each request type)
// ---------------------------------------------------------------------------

const WORKLOAD = {
  health: 0.4,   // 40% health checks
  catalog: 0.35, // 35% catalog requests
  login: 0.25,   // 25% login attempts
};

// ---------------------------------------------------------------------------
// Request functions
// ---------------------------------------------------------------------------

function healthCheck() {
  const response = http.get(`${BASE_URL}/health`, {
    tags: { endpoint: 'health' },
  });

  healthDuration.add(response.timings.duration);
  requestCount.add(1);

  const success = check(response, {
    'health: status 200': (r) => r.status === 200,
    'health: response < 200ms': (r) => r.timings.duration < 200,
    'health: has status field': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status !== undefined;
      } catch {
        return true; // Some health endpoints return plain text
      }
    },
  });

  return success;
}

function getCatalog() {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': 'tenant-load-test',
    },
    tags: { endpoint: 'catalog' },
  };

  const response = http.get(`${BASE_URL}/v1/agents/catalog`, params);

  catalogDuration.add(response.timings.duration);
  requestCount.add(1);

  const success = check(response, {
    'catalog: status 200': (r) => r.status === 200,
    'catalog: response < 500ms': (r) => r.timings.duration < 500,
    'catalog: has body': (r) => r.body && r.body.length > 0,
  });

  return success;
}

function loginAttempt() {
  const payload = JSON.stringify({
    email: 'loadtest@demo.kreupai.com',
    password: 'load-test-password',
    tenantSlug: 'demo',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'login' },
  };

  const response = http.post(`${AUTH_SERVICE_URL}/auth/login`, payload, params);

  loginDuration.add(response.timings.duration);
  requestCount.add(1);

  const success = check(response, {
    'login: status 200 or 401': (r) => r.status === 200 || r.status === 401,
    'login: response < 1s': (r) => r.timings.duration < 1000,
    'login: has body': (r) => r.body && r.body.length > 0,
  });

  return success;
}

// ---------------------------------------------------------------------------
// Test execution
// ---------------------------------------------------------------------------

export default function () {
  const rand = Math.random();
  let success = false;

  if (rand < WORKLOAD.health) {
    group('Health Check', () => {
      success = healthCheck();
    });
  } else if (rand < WORKLOAD.health + WORKLOAD.catalog) {
    group('Agent Catalog', () => {
      success = getCatalog();
    });
  } else {
    group('Login', () => {
      success = loginAttempt();
    });
  }

  errorRate.add(!success);

  // Short think time for realistic load pattern
  sleep(Math.random() * 1 + 0.5); // 0.5-1.5 seconds
}

// ---------------------------------------------------------------------------
// Setup and teardown
// ---------------------------------------------------------------------------

export function setup() {
  // Verify the API gateway is reachable
  const healthResponse = http.get(`${BASE_URL}/health`);

  const isReachable = check(healthResponse, {
    'API gateway is reachable': (r) => r.status === 200,
  });

  if (!isReachable) {
    console.warn('API gateway health check failed -- tests may not produce meaningful results');
  }

  return {
    startTime: Date.now(),
    isReachable,
  };
}

export function teardown(data) {
  const totalDuration = (Date.now() - data.startTime) / 1000;
  console.log(`API gateway load test completed in ${totalDuration.toFixed(1)} seconds`);
}
