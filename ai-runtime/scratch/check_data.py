import asyncio
import os
import json
from sqlalchemy import text
from db.database import init_db, get_engine

async def check():
    from dotenv import load_dotenv
    load_dotenv()
    
    await init_db()
    engine = get_engine()
    async with engine.connect() as conn:
        print("\n--- Finance Invoices ---")
        res = await conn.execute(text("SELECT * FROM finance_invoices LIMIT 5"))
        for row in res:
            print(dict(row._mapping))
            
        print("\n--- Purchase Requisitions ---")
        res = await conn.execute(text("SELECT * FROM purchase_requisitions LIMIT 5"))
        for row in res:
            print(dict(row._mapping))
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
