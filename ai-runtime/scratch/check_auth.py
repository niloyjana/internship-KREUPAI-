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

async def check_auth_data():
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
        # Check Users and their Tenant IDs
        try:
            print("\n--- Users and Tenants ---")
            # Use double quotes for case-sensitive columns in PostgreSQL
            query = """
            SELECT u.email, tu."tenantId" as tenant_id, t.slug as tenant_slug
            FROM users u
            LEFT JOIN tenant_users tu ON u.id = tu."userId"
            LEFT JOIN tenants t ON tu."tenantId" = t.id
            """
            res = await session.execute(text(query))
            rows = res.all()
            for r in rows:
                print(f"User: {r.email}, TenantID: {r.tenant_id}, Slug: {r.tenant_slug}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_auth_data())
