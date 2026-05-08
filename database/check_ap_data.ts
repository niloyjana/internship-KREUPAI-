import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const tenant = await prisma.tenant.findUnique({
    where: { slug: 'acme-corp' }
  });

  if (!tenant) {
    console.error('Tenant acme-corp not found');
    return;
  }

  // Get Agent Config for AP Officer
  const config = await prisma.agentConfig.findFirst({
    where: { 
      tenantId: tenant.id,
      agentDefinition: { agentId: 'ai-ap-officer' } 
    },
    include: { agentDefinition: true }
  });

  console.log('AP Officer Config:');
  console.log(JSON.stringify(config, null, 2));

  // Get Knowledge Articles for AP Officer
  const articles = await prisma.knowledgeArticle.findMany({
    where: { agentId: 'ai-ap-officer' }
  });

  console.log('\nKnowledge Articles:');
  console.log(JSON.stringify(articles, null, 2));

  // Get counts of business data
  const invoiceCount = await prisma.financeInvoice.count();
  const poCount = await prisma.purchaseRequisition.count();

  console.log(`\nBusiness Data Counts:`);
  console.log(`Invoices: ${invoiceCount}`);
  console.log(`Purchase Requisitions: ${poCount}`);

  // Get workflow definitions
  const defs = await prisma.workflowDefinition.findMany({
    where: { agentId: 'ai-ap-officer' }
  });

  console.log('\nWorkflow Definitions:');
  console.log(JSON.stringify(defs, null, 2));
}

main()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());
