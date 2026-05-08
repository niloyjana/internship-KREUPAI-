# Agent Development Guide

This guide explains how to develop, test, and deploy new AI agents for the AI Digital Workforce Platform (ADWP).

---

## Table of Contents

1. [Agent Architecture Overview](#agent-architecture-overview)
2. [Step-by-Step: Create a New Agent](#step-by-step-create-a-new-agent)
3. [Tool Development](#tool-development)
4. [Policy Configuration](#policy-configuration)
5. [Memory Management](#memory-management)
6. [Testing Guidelines](#testing-guidelines)
7. [Deployment and Registration](#deployment-and-registration)

---

## Agent Architecture Overview

Every AI agent in the platform follows a layered architecture:

```
┌─────────────────────────────────────────────────────┐
│                  OrchestrationEngine                  │
│  (PII redaction, cost tracking, memory, retry logic) │
└───────────────────────┬─────────────────────────────┘
                        │
                        v
┌─────────────────────────────────────────────────────┐
│                    YourAgent                          │
│              (extends BaseAgent)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ execute() │  │ call_llm()│  │ should_escalate()│  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │
                        v
┌─────────────────────────────────────────────────────┐
│                      Tools                            │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ CRM Tools  │  │ Email Tools│  │ Search Tools │  │
│  └────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Key concepts:**

- **BaseAgent** provides `call_llm()` (with automatic PII redaction), `should_escalate()`, and `format_result()`.
- **OrchestrationEngine** handles cross-cutting concerns: configuration resolution, PII redaction on payloads, cost tracking, failure handling with retries, and memory management.
- **Tools** extend `BaseTool` and provide structured interaction with external systems (CRM, ERP, email, etc.).
- **Policies** are dictionaries of configurable thresholds that tenants can override.

### Agent Directory Structure

All agents live under `ai-runtime/agents/`, organized by department:

```
ai-runtime/agents/
├── base_agent.py                    # Abstract base class
├── customer_ops/
│   ├── __init__.py
│   ├── support_agent.py             # Customer Support Agent
│   ├── service_desk_analyst.py
│   └── executive_assistant.py
├── sales_marketing/
│   ├── __init__.py
│   ├── sdr.py
│   └── ...
├── hr_people/
├── finance_procurement/
├── delivery_ops/
└── governance/
```

---

## Step-by-Step: Create a New Agent

This example creates a hypothetical "Invoice Reconciliation Agent" in the Finance & Procurement department.

### Step 1: Create the Agent File

Create `ai-runtime/agents/finance_procurement/invoice_reconciliation_agent.py`:

```python
"""Invoice Reconciliation Agent -- reconciles invoices against PO and receipts."""

import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class InvoiceReconciliationAgent(BaseAgent):
    """
    AI agent that reconciles supplier invoices against purchase orders
    and goods receipts, flagging discrepancies for human review.
    """

    DEFAULT_POLICY = {
        "reconciliation": {
            "tolerance_percentage": 2.0,       # Allow 2% variance
            "auto_approve_below_amount": 500,   # Auto-approve small invoices
            "max_auto_approve_amount": 5000,    # Never auto-approve above this
        },
        "escalation": {
            "confidence_threshold": 0.75,
            "always_escalate_above_amount": 10000,
        },
    }

    def __init__(self, llm_gateway, pii_redactor):
        super().__init__(
            agent_id="ai-invoice-reconciliation",
            llm_gateway=llm_gateway,
            pii_redactor=pii_redactor,
            name="Invoice Reconciliation Agent",
        )

    async def execute(self, task_payload: dict, context: dict) -> dict[str, Any]:
        """
        Multi-step invoice reconciliation workflow.

        Steps:
        1. EXTRACT  -- Parse invoice details from the payload.
        2. MATCH    -- Match invoice against POs and receipts.
        3. VALIDATE -- Check for discrepancies and policy violations.
        4. DECIDE   -- Auto-approve, flag for review, or escalate.
        """
        tenant_id = context.get("tenantId", "unknown")
        policy = context.get("agent_policy", self.DEFAULT_POLICY)

        # Step 1: Extract invoice details
        extract_result = await self.call_llm(
            messages=[
                {"role": "system", "content": (
                    "You are an invoice reconciliation specialist. "
                    "Extract structured invoice data from the input."
                )},
                {"role": "user", "content": str(task_payload)},
            ],
            tools=self._get_extraction_tools(),
            agent_policy=policy,
        )

        # Step 2: Match against POs
        match_result = await self.call_llm(
            messages=[
                {"role": "system", "content": (
                    "Match the extracted invoice to purchase orders. "
                    "Identify the matching PO and any line-item discrepancies."
                )},
                {"role": "user", "content": str(extract_result)},
            ],
            tools=self._get_matching_tools(),
            agent_policy=policy,
        )

        # Step 3: Validate and decide
        total_tokens = (
            extract_result.get("tokens_used", 0)
            + match_result.get("tokens_used", 0)
        )
        total_cost = (
            extract_result.get("cost_usd", 0.0)
            + match_result.get("cost_usd", 0.0)
        )

        # Check escalation conditions
        result = self.format_result(
            status="completed",
            output={
                "invoice_details": extract_result.get("content", ""),
                "match_result": match_result.get("content", ""),
                "recommendation": "approve",  # or "review" or "escalate"
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

        if self.should_escalate(result, policy):
            result["status"] = "escalated"
            result["nextAction"] = {
                "type": "human_review",
                "reason": "Reconciliation requires human verification",
            }

        return result

    def _get_extraction_tools(self):
        """Return tool specs for invoice extraction."""
        return []  # Add ERP tools here

    def _get_matching_tools(self):
        """Return tool specs for PO matching."""
        return []  # Add ERP lookup tools here
```

### Step 2: Create Agent-Specific Tools (if needed)

Create tools in `ai-runtime/tools/` if your agent needs new integrations:

```python
"""ai-runtime/tools/erp_tools.py -- ERP integration tools."""

from typing import Any
from tools.base_tool import BaseTool


class LookupPurchaseOrderTool(BaseTool):
    """Look up a purchase order by PO number from the ERP system."""

    @property
    def name(self) -> str:
        return "lookup_purchase_order"

    @property
    def description(self) -> str:
        return "Retrieve purchase order details by PO number from the ERP system."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "po_number": {
                    "type": "string",
                    "description": "The purchase order number to look up.",
                },
            },
            "required": ["po_number"],
        }

    async def execute(self, params: dict) -> dict[str, Any]:
        po_number = params.get("po_number")
        if not po_number:
            return self.error_result("po_number is required")

        # In production, this calls the Integration Hub API
        # For now, return mock data
        return self.success_result({
            "po_number": po_number,
            "vendor": "Acme Corp",
            "total_amount": 4500.00,
            "status": "received",
            "line_items": [
                {"description": "Widget A", "quantity": 100, "unit_price": 45.00}
            ],
        })
```

### Step 3: Register the Agent

Add your agent to `ai-runtime/api/main.py`:

```python
from agents.finance_procurement.invoice_reconciliation_agent import (
    InvoiceReconciliationAgent,
)

# During startup, after other agent registrations:
invoice_recon = InvoiceReconciliationAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-invoice-reconciliation", invoice_recon)
```

### Step 4: Write Tests

Create `ai-runtime/tests/agents/test_invoice_reconciliation_agent.py`:

```python
"""Tests for InvoiceReconciliationAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agents.finance_procurement.invoice_reconciliation_agent import (
    InvoiceReconciliationAgent,
)


@pytest.fixture
def mock_llm_gateway():
    gateway = MagicMock()
    gateway.complete = AsyncMock(return_value={
        "content": "Invoice INV-001: $4,500.00 from Acme Corp",
        "tokens_used": 150,
        "cost_usd": 0.003,
        "provider": "mock",
    })
    gateway.complete_with_tools = AsyncMock(return_value={
        "content": "Matched to PO-5678",
        "tool_calls": [],
        "tokens_used": 200,
        "cost_usd": 0.004,
        "provider": "mock",
    })
    return gateway


@pytest.fixture
def mock_pii_redactor():
    redactor = MagicMock()
    redactor.redact.side_effect = lambda text: (text, [])
    return redactor


@pytest.fixture
def agent(mock_llm_gateway, mock_pii_redactor):
    return InvoiceReconciliationAgent(mock_llm_gateway, mock_pii_redactor)


@pytest.mark.asyncio
async def test_execute_returns_completed_status(agent):
    result = await agent.execute(
        task_payload={
            "invoice_number": "INV-001",
            "amount": 4500.00,
            "vendor": "Acme Corp",
        },
        context={"tenantId": "tenant-001"},
    )
    assert result["status"] in ("completed", "escalated")
    assert "output" in result


@pytest.mark.asyncio
async def test_execute_escalates_on_low_confidence(agent):
    # Override should_escalate to always return True
    agent.should_escalate = MagicMock(return_value=True)

    result = await agent.execute(
        task_payload={"invoice_number": "INV-002", "amount": 50000.00},
        context={"tenantId": "tenant-001"},
    )
    assert result["status"] == "escalated"
    assert result.get("nextAction", {}).get("type") == "human_review"


def test_default_policy_structure(agent):
    assert "reconciliation" in agent.DEFAULT_POLICY
    assert "escalation" in agent.DEFAULT_POLICY
    assert "tolerance_percentage" in agent.DEFAULT_POLICY["reconciliation"]
```

---

## Tool Development

### BaseTool Interface

Every tool must implement these methods:

| Method              | Required | Purpose                                        |
|---------------------|----------|------------------------------------------------|
| `name`              | Yes      | Unique tool identifier                         |
| `description`       | Yes      | Human-readable description (sent to LLM)       |
| `parameters_schema` | Yes      | JSON Schema for tool parameters                |
| `execute(params)`   | Yes      | Execute the tool action, return result dict     |

### Formatting Tool Specs for LLM

The `BaseTool.to_llm_tool_spec()` method auto-converts your tool to OpenAI or Anthropic format:

```python
tool = LookupPurchaseOrderTool()

# For OpenAI
openai_spec = tool.to_llm_tool_spec(format="openai")

# For Anthropic
anthropic_spec = tool.to_llm_tool_spec(format="anthropic")
```

### Available Tool Categories

| File                | Tools                                      |
|---------------------|--------------------------------------------|
| `search_tools.py`   | Knowledge base search, document search     |
| `crm_tools.py`      | Contact lookup, deal update, activity log  |
| `erp_tools.py`      | PO lookup, invoice creation, inventory     |
| `email_tools.py`    | Send email, search inbox, create draft     |
| `calendar_tools.py` | Schedule meeting, check availability       |
| `document_tools.py` | Parse PDF, extract tables, summarize       |
| `data_tools.py`     | SQL query, data aggregation, export        |

---

## Policy Configuration

Policies define configurable thresholds that control agent behavior. They are defined as `DEFAULT_POLICY` on the agent class and can be overridden per tenant.

### Policy Structure

```python
DEFAULT_POLICY = {
    "<domain>": {
        "<threshold_name>": <value>,
    },
    "escalation": {
        "confidence_threshold": 0.75,  # Escalate below this confidence
        "max_auto_responses": 3,       # Limit automated responses
    },
    "sla": {
        "first_response_minutes": 5,
        "resolution_minutes": 240,
    },
}
```

### Tenant Override

Tenants configure policy overrides through the Agent Registry service. The `ConfigResolver` merges tenant settings with agent defaults at execution time:

```python
# In OrchestrationEngine.execute():
resolved_policy = config_resolver.resolve(
    agent_id=agent_id,
    tenant_id=tenant_id,
    default_policy=agent.DEFAULT_POLICY,
)
```

### Policy Best Practices

- Always define sensible defaults in `DEFAULT_POLICY`.
- Use numeric thresholds for financial limits (not hardcoded values in logic).
- Document each policy key with a comment explaining its effect.
- Include an `"escalation"` section in every agent's policy.

---

## Memory Management

### Working Memory (Redis)

Short-term, session-scoped memory. Used for multi-turn conversations and in-progress task context.

```python
# Loaded automatically by OrchestrationEngine before agent execution
memory = memory_manager.load_working_memory(session_id)

# Available in the context passed to execute()
previous_messages = context.get("working_memory", [])
```

### Episodic Memory (PostgreSQL)

Long-term memory of past task executions. Used for learning from previous interactions.

```python
# Automatically recorded by OrchestrationEngine after execution
# Includes: agent_id, tenant_id, task summary, outcome, timestamp
```

### Semantic Memory (Vector DB)

Knowledge embeddings for domain-specific information. Used for RAG (retrieval-augmented generation).

```python
# Accessed via search_tools.py
results = await search_tool.execute({
    "query": "return policy for electronics",
    "tenant_id": tenant_id,
    "top_k": 5,
})
```

---

## Testing Guidelines

### Test Structure

```
ai-runtime/tests/
├── agents/
│   ├── test_support_agent.py
│   ├── test_recruiter_agent.py
│   └── test_<your_agent>.py
├── tools/
│   ├── test_crm_tools.py
│   └── test_<your_tools>.py
├── orchestrator/
│   └── test_engine.py
└── conftest.py          # Shared fixtures (mock gateway, redactor, etc.)
```

### Running Tests

```bash
cd ai-runtime
source .venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run tests for a specific agent
pytest tests/agents/test_invoice_reconciliation_agent.py -v

# Run with verbose output
pytest -v --tb=short
```

### What to Test

| Aspect                   | Test Approach                                         |
|--------------------------|-------------------------------------------------------|
| Happy path execution     | Mock LLM, verify `execute()` returns expected output  |
| Escalation logic         | Set conditions that trigger escalation, verify status |
| Policy enforcement       | Override policy values, verify behavior changes       |
| PII redaction            | Pass PII in payload, verify it is redacted            |
| Tool integration         | Mock tool responses, verify agent uses results        |
| Error handling           | Simulate LLM failure, verify graceful degradation     |

### Linting

```bash
# Run ruff linter
ruff check ai-runtime/

# Auto-fix issues
ruff check --fix ai-runtime/
```
