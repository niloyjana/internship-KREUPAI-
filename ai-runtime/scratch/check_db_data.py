import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

from db.database import init_db, get_session
from sqlalchemy import text

async def check_data():
    # Initialize DB
    ready = await init_db()
    if not ready:
        print("DB not ready")
        return

    session = get_session()
    if not session:
        print("Could not create session")
        return

    async with session:
        # Check POs
        try:
            print("\n--- Purchase Orders ---")
            # Use double quotes for case-sensitive columns in PostgreSQL
            query = 'SELECT "prNumber", "estimatedAmount", status FROM purchase_requisitions LIMIT 5'
            res = await session.execute(text(query))
            rows = res.all()
            for r in rows:
                print(f"PO: {r.prNumber}, Amount: {r.estimatedAmount}, Status: {r.status}")
        except Exception as e:
            print(f"Error fetching POs: {e}")

        # Check Finance Invoices (Vendors are derived from here)
        try:
            print("\n--- Recent Invoices ---")
            query = 'SELECT "vendorName", "invoiceNumber", "totalAmount" FROM finance_invoices LIMIT 5'
            res = await session.execute(text(query))
            rows = res.all()
            for r in rows:
                print(f"Vendor: {r.vendorName}, Invoice: {r.invoiceNumber}, Amount: {r.totalAmount}")
        except Exception as e:
            print(f"Error fetching invoices: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
