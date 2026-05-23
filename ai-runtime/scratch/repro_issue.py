
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv(override=True)

from agents.finance_procurement.ap_officer import APOfficerAgent
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

async def test():
    llm = LLMGateway()
    pii = PIIRedactor()
    agent = APOfficerAgent(llm, pii)
    
    # Simulate Portal UI sending a wrapped task
    task_payload = {
        "task": json.dumps({
            "executionId": "exec-match-001",
            "tenantId": "cmostem4m0000y76cglzikowk",
            "taskPayload": {
                "type": "process_invoice",
                "vendor_name": "Global Logistics Ltd",
                "invoice_number": "INV-2024-501",
                "total_amount": 1250.00,
                "currency": "USD",
                "po_number": "PO-2024-882",
                "line_items": [
                    {"description": "Monthly freight services", "quantity": 1, "unit_price": 1250.00}
                ]
            }
        })
    }
    
    context = {
        "tenantId": "cmostem4m0000y76cglzikowk",
        "vendor_master": [{"name": "Global Logistics Ltd", "status": "approved"}]
    }
    
    result = await agent.execute(task_payload, context)
    print(json.dumps(result["output"]["extraction"], indent=2))
    print(f"Outcome: {result['output']['outcome']['outcome']}")

if __name__ == "__main__":
    asyncio.run(test())
