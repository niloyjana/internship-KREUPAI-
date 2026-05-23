
import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load env from root
env_path = os.path.join("e:\\cv\\KreupAI.AISA-main", ".env")
print(f"Loading env from: {env_path}")
load_dotenv(env_path)

async def debug_db():
    db_url = os.environ.get("DATABASE_URL")
    print(f"DATABASE_URL: {db_url}")
    if not db_url:
        print("DATABASE_URL not set")
        return

    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"Connecting to: {async_url}")
    
    try:
        engine = create_async_engine(async_url, echo=True)
        print("Engine created. Attempting to connect...")
        
        async with engine.connect() as conn:
            print("Connected! Executing query...")
            res = await conn.execute(text("SELECT 1"))
            val = res.scalar()
            print(f"Query result: {val}")
            
            print("Checking tenants...")
            res = await conn.execute(text("SELECT id, name, slug FROM tenants"))
            tenants = res.fetchall()
            print(f"Found {len(tenants)} tenants:")
            for t in tenants:
                print(f"  - {t}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Done.")

if __name__ == "__main__":
    asyncio.run(debug_db())
