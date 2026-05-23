import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Training QA Coordinator with database-backed business data...');

  // 1. Get the test tenant
  const tenant = await prisma.tenant.findUnique({
    where: { slug: 'acme-corp' },
  });

  if (!tenant) {
    console.error('Tenant acme-corp not found. Run main seed first.');
    return;
  }

  const tenantId = tenant.id;

  // 2. Seed QA Requirements
  console.log('Seeding QA Requirements...');
  const reqs = [
    { id: 'qa-req-1', text: 'REQ-1: User should be able to reset password via email link' },
    { id: 'qa-req-2', text: 'REQ-2: Login page must be responsive on mobile devices' },
    { id: 'qa-req-3', text: 'REQ-3: Users should be prompted for MFA if configured' }
  ];
  for (const r of reqs) {
    await prisma.qaRequirement.upsert({
      where: { id: r.id },
      update: { text: r.text },
      create: { id: r.id, tenantId: tenantId, text: r.text }
    });
  }

  // 3. Seed QA Baseline Test Results
  console.log('Seeding QA Baseline Test Results...');
  const baselines = [
    { id: 'qa-bl-1', name: 'test_login_success', status: 'passed' },
    { id: 'qa-bl-2', name: 'test_sso_redirect', status: 'passed' },
    { id: 'qa-bl-3', name: 'test_password_reset', status: 'passed' },
    { id: 'qa-bl-4', name: 'test_invalid_credentials', status: 'passed' }
  ];
  for (const b of baselines) {
    await prisma.qaBaselineResult.upsert({
      where: { id: b.id },
      update: { name: b.name, status: b.status },
      create: { id: b.id, tenantId: tenantId, name: b.name, status: b.status }
    });
  }

  // 4. Seed QA Current Test Run Results
  console.log('Seeding QA Current Test Run Results...');
  const testResults = [
    { id: 'qa-tr-1', name: 'test_login_success', status: 'passed', durationMs: 120, error: null },
    { id: 'qa-tr-2', name: 'test_sso_redirect', status: 'passed', durationMs: 250, error: null },
    { id: 'qa-tr-3', name: 'test_password_reset', status: 'failed', durationMs: 5000, error: 'Timeout: SMTP server failed to respond in 5000ms' },
    { id: 'qa-tr-4', name: 'test_invalid_credentials', status: 'passed', durationMs: 110, error: null }
  ];
  for (const t of testResults) {
    await prisma.qaTestResult.upsert({
      where: { id: t.id },
      update: { name: t.name, status: t.status, durationMs: t.durationMs, error: t.error },
      create: { id: t.id, tenantId: tenantId, name: t.name, status: t.status, durationMs: t.durationMs, error: t.error }
    });
  }

  // 5. Seed QA Open Defects
  console.log('Seeding QA Defects...');
  const defects = [
    { id: 'qa-df-1', title: 'Password reset email not sent on local environment', status: 'open', severity: 'P2' },
    { id: 'qa-df-2', title: 'Minor UI glitch on mobile safari browser', status: 'open', severity: 'P3' }
  ];
  for (const d of defects) {
    await prisma.qaDefect.upsert({
      where: { id: d.id },
      update: { title: d.title, status: d.status, severity: d.severity },
      create: { id: d.id, tenantId: tenantId, title: d.title, status: d.status, severity: d.severity }
    });
  }

  console.log('QA Coordinator database training (seeding) complete!');
  console.log('---');
  console.log('Database Seeding Summary:');
  console.log(`- ${reqs.length} Requirements seeded.`);
  console.log(`- ${baselines.length} Baseline results seeded.`);
  console.log(`- ${testResults.length} Current test results seeded.`);
  console.log(`- ${defects.length} Defects seeded.`);
}

main()
  .catch((e) => {
    console.error('QA training database seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
