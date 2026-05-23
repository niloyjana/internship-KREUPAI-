import asyncio
import logging
import sys
from unittest.mock import AsyncMock

# Add current folder to path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.qa_context_loader import load_qa_context
from agents.delivery_ops.qa_coordinator import QACoordinatorAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def test_flow():
    tenant_id = "test-tenant-id-123"
    task_payload = {
        "task_type": "quality_report",
        "build_id": "b-test-build",
        "feature_name": "Database-Driven QA"
    }

    print("--- 1. Testing QA Context Loader ---")
    context = await load_qa_context(tenant_id, task_payload)
    print("\nLoaded context structure:")
    for key, value in context.items():
        if isinstance(value, list):
            print(f"  - {key}: {len(value)} items")
            if value:
                print(f"    Sample: {value[0]}")
        else:
            print(f"  - {key}: {value}")

    print("\n--- 2. Testing QACoordinatorAgent execution with loaded context ---")
    
    # Create mock LLM Gateway
    class MockLLMResponse:
        def __init__(self, content):
            self.content = content
            self.model = "gpt-4"
            self.tokens_used = 150
            self.input_tokens = 100
            self.output_tokens = 50
            self.cost_usd = 0.003
            self.finish_reason = "stop"
            self.provider = "openai"

    mock_llm_gateway = AsyncMock()
    async def mock_complete(*args, **kwargs):
        content_str = '{"report": "# Quality Report\\n\\nEverything is super stable!\\n\\n### Recommendation\\nReady to deploy.", "insight": "Stable build."}'
        return MockLLMResponse(content_str)
    mock_llm_gateway.complete = AsyncMock(side_effect=mock_complete)
    
    # Create mock PII redactor
    class DummyPIIRedactor:
        def redact(self, content, *args, **kwargs):
            return content, []
        def redact_json(self, data, *args, **kwargs):
            return data
    
    mock_pii_redactor = DummyPIIRedactor()

    # Instantiate QACoordinatorAgent
    agent = QACoordinatorAgent(llm_gateway=mock_llm_gateway, pii_redactor=mock_pii_redactor)
    
    # Execute agent
    exec_context = {
        "tenantId": tenant_id,
        "executionId": "test-execution-456",
        "stepId": "step-1",
        **context
    }
    
    print("Executing agent workflow...")
    result = await agent.execute(task_payload, exec_context)
    
    print("\nAgent Execution Result Status:", result.get("status"))
    print("Agent Next Action Recommendation:", result.get("next_action"))
    print("\nRelease Readiness Assessment:")
    rr = result.get("output", {}).get("release_readiness", {})
    print(f"  - Ready for release: {rr.get('is_release_ready')}")
    print(f"  - Recommendation: {rr.get('recommendation')}")
    print(f"  - Blockers: {rr.get('blockers')}")
    print(f"  - Warnings: {rr.get('warnings')}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_flow())
