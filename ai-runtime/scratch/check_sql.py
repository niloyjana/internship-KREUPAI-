from sqlalchemy import select
from sqlalchemy.schema import CreateTable
from sqlalchemy.ext.asyncio import create_async_engine
from db.models import FinanceInvoice, Base

def check_sql():
    # We don't even need a real engine to see the CREATE TABLE statement or the query
    from sqlalchemy.dialects import postgresql
    from sqlalchemy import select
    
    # 1. Check SELECT statement
    stmt = select(FinanceInvoice).where(FinanceInvoice.tenant_id == "test")
    print("--- SELECT STATEMENT ---")
    print(stmt.compile(dialect=postgresql.dialect()))
    
    # 2. Check CREATE TABLE statement
    print("\n--- CREATE TABLE STATEMENT ---")
    print(CreateTable(FinanceInvoice.__table__).compile(dialect=postgresql.dialect()))

if __name__ == "__main__":
    check_sql()
