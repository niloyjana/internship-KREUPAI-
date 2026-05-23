import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const counts = {
    tenants: await prisma.tenant.count(),
    users: await prisma.user.count(),
    invoices: await prisma.financeInvoice.count(),
    pos: await prisma.purchaseRequisition.count(),
    agents: await prisma.agentDefinition.count(),
    escalations: await prisma.escalationTicket.count(),
  };
  console.log('---DATABASE_COUNTS---');
  console.log(JSON.stringify(counts, null, 2));
  console.log('---END---');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
