import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from agents.finance_procurement.ap_officer import APOfficerAgent
from db.ap_context_loader import load_ap_context
from db.database import init_db
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

async def test_workflow():
    print("Initializing Database...")
    await init_db()
    
    llm = LLMGateway()
    pii = PIIRedactor()
    agent = APOfficerAgent(llm, pii)
    
    tenant_id = "clt9x9x9x0000ux01v1v1v1v1" # Tenant ID from seed / verify_escalations
    
    # Let's dynamically lookup tenant_id to make sure it matches database
    from sqlalchemy import text
    from db.database import get_session
    session = get_session()
    if session:
        try:
            res = await session.execute(text("SELECT id FROM tenants WHERE slug = 'acme-corp' LIMIT 1"))
            row = res.fetchone()
            if row:
                tenant_id = row[0]
                print(f"Using dynamic tenant_id from database: {tenant_id}")
        except Exception as e:
            print(f"Error fetching tenant_id: {e}")
        finally:
            await session.close()

    # Case 1: Valid Invoice (Global Logistics Ltd - Matches PO exactly)
    payload_completed = {
        "type": "process_invoice",
        "invoice_data": {
            "vendor_name": "Global Logistics Ltd",
            "invoice_number": "INV-2024-003",
            "total_amount": 1250.00,
            "currency": "USD",
            "po_number": "PO-2024-882",
            "line_items": [
                {
                    "description": "Shipping Services",
                    "quantity": 1,
                    "unit_price": 1250.00
                }
            ]
        }
    }
    
    # Case 2: Unrecognized Vendor (Unknown Vendor Inc - Should Escalate)
    payload_escalated = {
        "type": "process_invoice",
        "invoice_data": {
            "vendor_name": "Unknown Vendor Inc",
            "invoice_number": "INV-NEW-999",
            "total_amount": 500.00,
            "currency": "USD",
            "po_number": "PO-NONE",
            "line_items": [
                {
                    "description": "Miscellaneous Supplies",
                    "quantity": 1,
                    "unit_price": 500.00
                }
            ]
        }
    }

    print("\n==================================================")
    print("TEST 1: Valid Invoice (Global Logistics Ltd)")
    print("==================================================")
    context_completed = await load_ap_context(tenant_id, payload_completed)
    # Merge context with standard context
    full_context_completed = {
        "tenantId": tenant_id,
        "executionId": "test-execution-completed",
        **context_completed
    }
    result_completed = await agent.execute(payload_completed, full_context_completed)
    print(f"Status: {result_completed['status']}")
    print(f"Outcome: {result_completed['output']['outcome']['outcome']}")
    print(f"Reason: {result_completed['output']['outcome']['reason']}")
    print(f"Flags: {result_completed['output']['outcome']['flags']}")

    print("\n==================================================")
    print("TEST 2: Unrecognized Vendor (Unknown Vendor Inc)")
    print("==================================================")
    context_escalated = await load_ap_context(tenant_id, payload_escalated)
    full_context_escalated = {
        "tenantId": tenant_id,
        "executionId": "test-execution-escalated",
        **context_escalated
    }
    result_escalated = await agent.execute(payload_escalated, full_context_escalated)
    print(f"Status: {result_escalated['status']}")
    print(f"Outcome: {result_escalated['output']['outcome']['outcome']}")
    print(f"Reason: {result_escalated['output']['outcome']['reason']}")
    print(f"Flags: {result_escalated['output']['outcome']['flags']}")
    print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(test_workflow())
