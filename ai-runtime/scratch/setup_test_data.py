import asyncio
from sqlalchemy import text
from db.database import get_session, init_db

async def setup():
    # Initialize DB connection
    initialized = await init_db()
    if not initialized:
        print("Failed to initialize DB connection. Check DATABASE_URL.")
        return

    session = get_session()
    if not session:
        print("No session")
        return

    try:
        # Get tenant ID
        res = await session.execute(text("SELECT id FROM tenants WHERE slug = 'acme-corp' LIMIT 1"))
        row = res.fetchone()
        if not row:
            print("Tenant acme-corp not found")
            return
        tenant_id = row[0]

        # 1. Create a Vendor (via an existing invoice)
        # We'll insert a "completed" invoice to act as the vendor master record
        await session.execute(text(f"""
            INSERT INTO finance_invoices (id, "tenantId", "vendorName", "invoiceNumber", "totalAmount", status, "invoiceDate", "createdAt")
            VALUES ('seed-inv-001', '{tenant_id}', 'Global Logistics Ltd', 'PREV-001', 1000.00, 'completed', now(), now())
            ON CONFLICT (id) DO NOTHING
        """))

        # 2. Create a Purchase Order
        await session.execute(text(f"""
            INSERT INTO purchase_requisitions (id, "tenantId", "prNumber", description, "estimatedAmount", status, "createdAt")
            VALUES ('seed-po-001', '{tenant_id}', 'PO-2024-882', 'Shipping Services', 1200.00, 'approved', now(), now())
            ON CONFLICT (id) DO NOTHING
        """))

        await session.commit()
        print("Test data setup complete.")
    except Exception as e:
        print(f"Error: {e}")
        await session.rollback()
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(setup())
