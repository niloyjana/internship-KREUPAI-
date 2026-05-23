
import asyncio
from sqlalchemy import select, text
from dotenv import load_dotenv
from db.database import get_session, init_db
from db.models import FinanceInvoice, PurchaseRequisition

load_dotenv()

async def check_data():
    await init_db()
    session = get_session()
    if not session:
        print("No session")
        return
    
    # Get tenant ID for acme-corp
    res = await session.execute(text("SELECT id FROM tenants WHERE slug = 'acme-corp'"))
    tenant = res.fetchone()
    if not tenant:
        print("Tenant acme-corp not found")
        return
    tenant_id = tenant[0]
    print(f"Tenant ID: {tenant_id}")
    
    # Check invoices
    res = await session.execute(select(FinanceInvoice).where(FinanceInvoice.tenant_id == tenant_id))
    invoices = res.scalars().all()
    print(f"Invoices: {len(invoices)}")
    for inv in invoices:
        print(f"  - {inv.vendor_name}: {inv.invoice_number} (${inv.total_amount})")
        
    # Check POs
    res = await session.execute(select(PurchaseRequisition).where(PurchaseRequisition.tenant_id == tenant_id))
    pos = res.scalars().all()
    print(f"POs: {len(pos)}")
    for po in pos:
        print(f"  - {po.pr_number}: ${po.estimated_amount}")

if __name__ == "__main__":
    asyncio.run(check_data())
