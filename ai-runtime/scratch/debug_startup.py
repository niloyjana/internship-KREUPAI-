"""Simulate full uvicorn startup to find exact crash point."""
import asyncio
import sys
import traceback
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv(override=True)

from db.database import init_db, init_redis, create_tables, close_db
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor
from llm.cost_tracker import CostTracker
from orchestrator.config_resolver import ConfigResolver
from orchestrator.failure_handler import FailureHandler
from memory.manager import MemoryManager
from orchestrator.engine import OrchestrationEngine
from agents.finance_procurement.ap_officer import APOfficerAgent


async def main():
    print("1. init_db...")
    db_ready = await init_db()
    print(f"   db_ready={db_ready}")

    print("2. init_redis...")
    redis_ready = await init_redis()
    print(f"   redis_ready={redis_ready}")

    if db_ready:
        print("3. create_tables...")
        await create_tables()
        print("   tables OK")

    print("4. Building engine...")
    gw = LLMGateway()
    pii = PIIRedactor()
    ct = CostTracker()
    cr = ConfigResolver()
    fh = FailureHandler()
    mm = MemoryManager()
    engine = OrchestrationEngine(gw, pii, ct, cr, fh, mm)
    print(f"   engine OK, provider={gw.default_provider}")

    print("5. Registering ap_officer...")
    engine.register_agent("ai-ap-officer", APOfficerAgent(gw, pii))
    print(f"   registered, count={engine.agent_count}")

    print("6. Executing (mock mode)...")
    result = await engine.execute(
        agent_id="ai-ap-officer",
        task_payload={
            "type": "process_invoice",
            "vendor_name": "Test Vendor",
            "invoice_number": "INV-DEMO-001",
            "total_amount": 1000.0,
            "currency": "USD",
        },
        context={"tenantId": "cmp19c9400000y70sbkv4dl2i", "executionId": "test-123"},
    )
    status = result.get("status")
    print(f"   status={status}")
    print("SUCCESS - ALL OK")
    await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nCRASH: {type(e).__name__}: {e}")
        traceback.print_exc()
