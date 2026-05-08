import os
import asyncio
from sqlalchemy import select
from db.database import init_db, get_session
from sqlalchemy import text

async def get_tenant_id():
    await init_db()
    session = get_session()
    try:
        # Prisma uses 'tenants' table (mapped from Tenant)
        result = await session.execute(text("SELECT id FROM tenants WHERE slug = 'acme-corp'"))
        tenant = result.fetchone()
        if tenant:
            print(f"TENANT_ID={tenant[0]}")
        else:
            print("Tenant not found")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(get_tenant_id())
