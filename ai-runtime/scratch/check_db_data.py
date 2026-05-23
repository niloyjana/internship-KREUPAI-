
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import select, text

# Load env from root
load_dotenv(os.path.join("e:\\cv\\KreupAI.AISA-main", ".env"))

from db.database import init_db, get_session
from db.models import FinanceInvoice, PurchaseRequisition

async def check_data():
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    await init_db()
    session = get_session()
    if not session:
        print("No session")
        return

    try:
        # Check Tenants (raw SQL)
        try:
            res = await session.execute(text("SELECT id, name, slug FROM tenants"))
            tenants = res.fetchall()
            print(f"Tenants: {tenants}")
        except Exception as e:
            print(f"Could not fetch tenants: {e}")

        # Check POs
        res = await session.execute(select(PurchaseRequisition))
        pos = res.scalars().all()
        print(f"POs: {[ (p.pr_number, p.estimated_amount, p.status) for p in pos]}")

        # Check Invoices
        res = await session.execute(select(FinanceInvoice))
        invoices = res.scalars().all()
        print(f"Invoices: {[ (i.invoice_number, i.vendor_name, i.total_amount) for i in invoices]}")

    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(check_data())
