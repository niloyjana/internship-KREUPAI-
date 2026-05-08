/**
 * k6 Load Test: Agent Execution Endpoint
 *
 * Tests the POST /v1/agents/{agentId}/execute endpoint under load.
 *
 * Ramp-up profile:
 *   - 0 -> 10 VUs over 30 seconds
 *   - 10 -> 100 VUs over 90 seconds (2 min total)
 *   - Hold 100 VUs for 5 minutes
 *   - 100 -> 0 VUs ramp-down over 30 seconds
 *
 * Thresholds:
 *   - p95 response time < 5 seconds
 *   - Error rate < 5%
 *
 * Usage:
 *   k6 run tests/load/agent-execution.js
 *   k6 run --env BASE_URL=http://staging:8000 tests/load/agent-execution.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const errorRate = new Rate('agent_exec_error_rate');
const executionDuration = new Trend('agent_exec_duration', true);

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'test-bearer-token';

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 VUs
    { duration: '90s', target: 100 },   // Ramp up to 100 VUs
    { duration: '5m', target: 100 },    // Hold at 100 VUs for 5 minutes
    { duration: '30s', target: 0 },     // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],         // 95th percentile < 5s
    agent_exec_error_rate: ['rate<0.05'],       // Error rate < 5%
    http_req_failed: ['rate<0.05'],             // HTTP failure rate < 5%
  },
  tags: {
    testSuite: 'agent-execution-load',
  },
};

// ---------------------------------------------------------------------------
// Agent configurations for varied workload
// ---------------------------------------------------------------------------

const agentConfigs = [
  {
    agentId: 'ai-customer-support-agent',
    payload: {
      type: 'screen_inquiry',
      customer_name: 'Load Test User',
      message: 'I have a question about my recent billing statement',
      customer_id: `cust-load-${Date.now()}`,
    },
  },
  {
    agentId: 'ai-ap-officer',
    payload: {
      type: 'process_invoice',
      vendor_name: 'Load Test Vendor',
      invoice_number: `INV-LOAD-${Date.now()}`,
      amount: 1500.00,
      currency: 'USD',
    },
  },
  {
    agentId: 'ai-recruiter',
    payload: {
      type: 'screen_application',
      resume_data: {
        name: 'Load Test Candidate',
        email: `candidate-${Date.now()}@loadtest.com`,
        skills: ['Python', 'Machine Learning'],
        total_years_experience: 5,
      },
      job_definition: {
        title: 'Senior Engineer',
        requirements: {
          mandatory: ['Python'],
          min_years_experience: 3,
        },
      },
    },
  },
];

// ---------------------------------------------------------------------------
// Test execution
// ---------------------------------------------------------------------------

export default function () {
  // Pick a random agent configuration for each iteration
  const config = agentConfigs[Math.floor(Math.random() * agentConfigs.length)];

  const url = `${BASE_URL}/v1/agents/${config.agentId}/execute`;

  const params = {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${AUTH_TOKEN}`,
      'X-Tenant-ID': 'tenant-load-test',
    },
    tags: {
      agent: config.agentId,
    },
  };

  const payload = JSON.stringify({
    taskPayload: config.payload,
    context: {
      tenantId: 'tenant-load-test',
      executionId: `exec-load-${__VU}-${__ITER}-${Date.now()}`,
      userId: 'user-load-test',
    },
  });

  const response = http.post(url, payload, params);

  // Record custom metrics
  executionDuration.add(response.timings.duration);

  // Check response
  const success = check(response, {
    'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
    'response has body': (r) => r.body && r.body.length > 0,
    'response has status field': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status !== undefined;
      } catch {
        return false;
      }
    },
    'response time < 5s': (r) => r.timings.duration < 5000,
  });

  errorRate.add(!success);

  // Think time between requests (simulates realistic user behavior)
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

// ---------------------------------------------------------------------------
// Setup and teardown
// ---------------------------------------------------------------------------

export function setup() {
  // Verify the API is reachable
  const healthCheck = http.get(`${BASE_URL}/health`);
  check(healthCheck, {
    'API is reachable': (r) => r.status === 200,
  });

  return { startTime: Date.now() };
}

export function teardown(data) {
  const totalDuration = (Date.now() - data.startTime) / 1000;
  console.log(`Load test completed in ${totalDuration.toFixed(1)} seconds`);
}
