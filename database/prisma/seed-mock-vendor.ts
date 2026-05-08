import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Adding specific "Mock Vendor" data to match your requested format...');

  const tenant = await prisma.tenant.findUnique({
    where: { slug: 'acme-corp' },
  });

  if (!tenant) {
    console.error('Tenant acme-corp not found.');
    return;
  }

  const tenantId = tenant.id;

  // 1. Seed the Vendor in the user's request
  const vendorName = 'Mock Vendor Ltd';

  // 2. Seed an approved Purchase Order for 1100.00
  const poNumber = 'PO-MOCK-777';
  console.log(`Seeding PO: ${poNumber} for $1,100.00 for ${vendorName}...`);

  await prisma.purchaseRequisition.upsert({
    where: { id: 'test-po-mock' },
    update: {},
    create: {
      id: 'test-po-mock',
      tenantId: tenantId,
      prNumber: poNumber,
      requestedById: 'user-001',
      department: 'IT',
      category: 'Professional Services',
      description: 'Consultancy services for Q2',
      estimatedAmount: 1100.00,
      status: 'approved',
    },
  });

  console.log('Data ready!');
}

main()
  .catch((e) => {
    console.error('Failed to update mock data:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
