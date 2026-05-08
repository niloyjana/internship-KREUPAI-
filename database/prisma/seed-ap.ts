import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Training AP Officer with local business data...');

  // 1. Get the test tenant
  const tenant = await prisma.tenant.findUnique({
    where: { slug: 'acme-corp' },
  });

  if (!tenant) {
    console.error('Tenant acme-corp not found. Run main seed first.');
    return;
  }

  const tenantId = tenant.id;

  // 2. Seed Approved Vendor (Matched to test scenarios)
  const vendorName = 'Global Logistics Ltd';
  const vendorId = 'VEND-001';

  // 3. Seed Purchase Order (Matches the invoice we will test)
  const poNumber = 'PO-2024-882';
  console.log(`Seeding PO: ${poNumber} for $1,250.00...`);

  await prisma.purchaseRequisition.upsert({
    where: { id: 'test-po-882' },
    update: {},
    create: {
      id: 'test-po-882',
      tenantId: tenantId,
      prNumber: poNumber,
      requestedById: 'user-001',
      department: 'Logistics',
      category: 'Shipping Services',
      description: 'Monthly freight services - March 2024',
      estimatedAmount: 1250.00,
      status: 'approved',
    },
  });

  // 4. Seed Historical Invoices (to test duplicate detection)
  console.log('Seeding historical invoices for duplicate detection...');
  
  await prisma.financeInvoice.upsert({
    where: { id: 'hist-inv-001' },
    update: {},
    create: {
      id: 'hist-inv-001',
      tenantId: tenantId,
      vendorName: vendorName,
      vendorId: vendorId,
      invoiceNumber: 'INV-2024-001',
      invoiceDate: new Date('2024-01-15'),
      totalAmount: 1250.00,
      subtotal: 1250.00,
      status: 'paid',
      poReference: poNumber,
      paidAt: new Date('2024-01-20'),
    },
  });

  await prisma.financeInvoice.upsert({
    where: { id: 'hist-inv-002' },
    update: {},
    create: {
      id: 'hist-inv-002',
      tenantId: tenantId,
      vendorName: vendorName,
      vendorId: vendorId,
      invoiceNumber: 'INV-2024-002',
      invoiceDate: new Date('2024-02-15'),
      totalAmount: 1250.00,
      subtotal: 1250.00,
      status: 'paid',
      poReference: poNumber,
      paidAt: new Date('2024-02-20'),
    },
  });

  console.log('AP Officer training (seeding) complete!');
  console.log('---');
  console.log('Test Scenario Ready:');
  console.log(`- Vendor: ${vendorName}`);
  console.log(`- Open PO: ${poNumber} ($1,250.00)`);
  console.log('- Agent will now match invoices to this PO instead of placing them on Hold.');
}

main()
  .catch((e) => {
    console.error('Training failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
