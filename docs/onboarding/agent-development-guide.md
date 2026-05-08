# Agent Development Guide

This guide walks you through building a new AI agent for the ADWP platform, from understanding the BaseAgent pattern to registering and testing your agent.

---

## Table of Contents

1. [Understanding the BaseAgent Pattern](#understanding-the-baseagent-pattern)
2. [Step-by-Step: Creating a New Agent](#step-by-step-creating-a-new-agent)
3. [Tool Development Guide](#tool-development-guide)
4. [Testing Agents](#testing-agents)
5. [Policy Configuration Reference](#policy-configuration-reference)
6. [Example: Building a Custom Agent from Scratch](#example-building-a-custom-agent-from-scratch)

---

## Understanding the BaseAgent Pattern

Every AI agent in the ADWP platform extends the `BaseAgent` abstract class defined in `ai-runtime/agents/base_agent.py`. This base class provides:

### Core Capabilities

| Method             | Purpose                                                        |
|--------------------|----------------------------------------------------------------|
| `execute()`        | **Abstract** -- your agent's main workflow (must be implemented) |
| `call_llm()`       | Call the LLM with automatic PII redaction                      |
| `should_escalate()`| Check if the result requires human escalation                  |
| `format_result()`  | Create a standardized result envelope                          |
| `get_capabilities()` | Advertise agent capabilities (override to customize)         |

### Execution Lifecycle

When the orchestration engine calls your agent, this is what happens:

```
OrchestrationEngine.execute()
    |
    |-- 1. Resolve configuration (merge tenant + agent policy)
    |-- 2. Redact PII from task payload
    |-- 3. Create execution record in database
    |-- 4. Load working memory
    |
    +-- 5. YOUR_AGENT.execute(redacted_payload, enriched_context)
    |       |
    |       |-- call_llm() with PII-redacted messages
    |       |-- Tool execution (via LLM function calling)
    |       |-- Multi-step reasoning
    |       |-- format_result() to create output
    |       |
    |       +-- Returns: { status, output, tokensUsed, ... }
    |
    |-- 6. Track costs
    |-- 7. Check escalation conditions
    |-- 8. Record episodic memory
    |-- 9. Persist execution results
```

### What the BaseAgent Handles for You

- **PII redaction** -- `call_llm()` automatically scans user messages for emails, phone numbers, credit cards, SSNs, IBANs, and IP addresses, replacing them with tokens like `[REDACTED_EMAIL]` before sending to the LLM.
- **Provider abstraction** -- The LLM Gateway routes calls to OpenAI or Anthropic with automatic failover. Your agent code never touches provider-specific APIs.
- **Escalation logic** -- `should_escalate()` checks confidence thresholds, cost limits, risk levels, and PII detection against the agent's policy configuration.
- **Result formatting** -- `format_result()` ensures every agent returns a consistent output structure.

---

## Step-by-Step: Creating a New Agent

This section walks through creating a new agent from start to finish.

### Step 1: Create the Agent File

Create a new Python file in the appropriate department directory:

```
ai-runtime/agents/
  |-- customer_ops/        # Customer Operations
  |-- sales_marketing/     # Sales & Marketing
  |-- hr_people_ops/       # HR & People Ops
  |-- finance_procurement/ # Finance & Procurement
  |-- delivery_ops/        # Delivery Operations
  |-- governance_risk/     # Governance, Risk & Control
```

For example, to create a new Contract Review Agent in the governance department:

```bash
touch ai-runtime/agents/governance_risk/contract_reviewer.py
```

### Step 2: Define the DEFAULT_POLICY

The policy defines configurable thresholds and rules for your agent. Place it at the module level:

```python
"""AI Contract Review Agent -- analyzes contracts for risks and obligations.

Implements a 3-step contract review workflow:
  1. EXTRACT  -- Extract key terms, parties, dates, and clauses
  2. ANALYZE  -- Assess risk, identify obligations, flag concerns
  3. REPORT   -- Generate structured review report with recommendations

Worker ID: ai-contract-reviewer
Department: Governance, Risk & Control
"""

import json
import logging
from typing import Any, Optional

from agents.base_agent import BaseAgent
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)

DEFAULT_POLICY: dict[str, Any] = {
    "risk_scoring": {
        "high_risk_threshold": 7,      # Score >= 7 is high risk
        "auto_approve_below": 3,       # Score < 3 can be auto-approved
    },
    "escalation": {
        "always_escalate_types": ["employment", "nda", "merger"],
        "value_threshold_usd": 100000,  # Escalate contracts above this value
    },
    "extraction": {
        "max_clauses": 50,
        "required_fields": ["parties", "effective_date", "term", "governing_law"],
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.75,
            "max_cost_usd": 0.50,
        },
    },
    "pii_redaction": {
        "enabled": True,
        "enabled_patterns": ["email", "phone_intl", "ssn_us"],
        "escalate_on_detection": True,
    },
}
```

### Step 3: Extend BaseAgent and Implement the Constructor

```python
class ContractReviewAgent(BaseAgent):
    """Reviews contracts for risks, obligations, and key terms."""

    def __init__(
        self,
        llm_gateway: LLMGateway,
        pii_redactor: PIIRedactor,
    ):
        super().__init__(
            agent_id="ai-contract-reviewer",
            llm_gateway=llm_gateway,
            pii_redactor=pii_redactor,
            name="Contract Review Agent",
        )

    def get_capabilities(self) -> list[str]:
        return [
            "contract_extraction",
            "risk_assessment",
            "obligation_tracking",
            "clause_analysis",
        ]
```

### Step 4: Define Tools (Extend BaseTool)

If your agent needs to interact with external systems, create tool classes. See [Tool Development Guide](#tool-development-guide) below for full details.

```python
# In agents/governance_risk/tools.py (or a separate tools file)
from tools.base_tool import BaseTool
from typing import Any

class ContractStorageTool(BaseTool):
    @property
    def name(self) -> str:
        return "fetch_contract_document"

    @property
    def description(self) -> str:
        return "Retrieve a contract document from storage by its ID."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "contract_id": {
                    "type": "string",
                    "description": "The unique identifier of the contract",
                },
            },
            "required": ["contract_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        contract_id = params.get("contract_id")
        # In production, fetch from document storage (S3, etc.)
        # For now, return mock data
        return self.success_result({
            "contract_id": contract_id,
            "content": "Contract content would be here...",
            "metadata": {"pages": 12, "file_type": "pdf"},
        })
```

### Step 5: Implement execute() with Multi-Step Workflow

```python
    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the contract review workflow.

        Steps:
          1. EXTRACT -- Parse and extract key contract terms
          2. ANALYZE -- Assess risks and identify obligations
          3. REPORT  -- Generate structured review report
        """
        policy = context.get("agent_policy", DEFAULT_POLICY)
        contract_text = task_payload.get("contract_text", "")
        contract_id = task_payload.get("contract_id")

        total_tokens = 0
        total_cost = 0.0

        # ----- Step 1: EXTRACT -----
        extract_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a contract analysis specialist. "
                        "Extract key terms from the following contract. "
                        "Return a JSON object with: parties, effective_date, "
                        "expiry_date, term, governing_law, key_clauses, "
                        "total_value, currency."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Contract to analyze:\n\n{contract_text}",
                },
            ],
            agent_policy=policy,
        )
        total_tokens += extract_result.get("tokens_used", 0)
        total_cost += extract_result.get("cost_usd", 0.0)

        try:
            extracted_terms = json.loads(extract_result["content"])
        except (json.JSONDecodeError, KeyError):
            extracted_terms = {"raw_response": extract_result.get("content", "")}

        # ----- Step 2: ANALYZE -----
        analyze_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a legal risk analyst. Analyze the following "
                        "contract terms and provide: risk_score (1-10), "
                        "risk_factors (list), obligations (list with deadlines), "
                        "concerns (list), recommendations (list). "
                        "Return as JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(extracted_terms),
                },
            ],
            agent_policy=policy,
        )
        total_tokens += analyze_result.get("tokens_used", 0)
        total_cost += analyze_result.get("cost_usd", 0.0)

        try:
            analysis = json.loads(analyze_result["content"])
        except (json.JSONDecodeError, KeyError):
            analysis = {"raw_response": analyze_result.get("content", "")}

        # ----- Step 3: REPORT -----
        risk_score = analysis.get("risk_score", 5)
        risk_config = policy.get("risk_scoring", {})

        # Determine if escalation is needed
        needs_escalation = False
        escalation_reasons = []

        if risk_score >= risk_config.get("high_risk_threshold", 7):
            needs_escalation = True
            escalation_reasons.append(f"High risk score: {risk_score}")

        contract_value = extracted_terms.get("total_value", 0)
        value_threshold = policy.get("escalation", {}).get("value_threshold_usd", 100000)
        if contract_value and float(contract_value) > value_threshold:
            needs_escalation = True
            escalation_reasons.append(
                f"Contract value ${contract_value} exceeds threshold ${value_threshold}"
            )

        result = self.format_result(
            status="escalated" if needs_escalation else "completed",
            output={
                "contract_id": contract_id,
                "extracted_terms": extracted_terms,
                "analysis": analysis,
                "risk_score": risk_score,
                "needs_escalation": needs_escalation,
                "escalation_reasons": escalation_reasons,
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action="human_review" if needs_escalation else None,
            metadata={
                "steps_completed": ["extract", "analyze", "report"],
                "pii_detected": extract_result.get("pii_detected", []),
            },
        )

        # Add fields used by should_escalate()
        result["confidence"] = 1.0 - (risk_score / 10.0)
        result["risk_level"] = "high" if risk_score >= 7 else "medium" if risk_score >= 4 else "low"
        result["cost_usd"] = total_cost
        result["pii_detected"] = extract_result.get("pii_detected", [])

        return result
```

### Step 6: Register in api/main.py

Add your agent to the startup registration in `ai-runtime/api/main.py`:

```python
# Import your agent
from agents.governance_risk.contract_reviewer import ContractReviewAgent

# In the lifespan function, after other agent registrations:
contract_reviewer = ContractReviewAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-contract-reviewer", contract_reviewer)
```

### Step 7: Add to Database Seed Data

Add the agent definition to `database/prisma/seed.ts` so it appears in the agent registry:

```typescript
await prisma.agentDefinition.upsert({
  where: { agentId: 'ai-contract-reviewer' },
  update: {},
  create: {
    agentId: 'ai-contract-reviewer',
    name: 'Contract Review Agent',
    department: 'GOVERNANCE_RISK_CONTROL',
    description: 'Analyzes contracts for risks, obligations, and key terms. Extracts clauses, scores risk, and generates structured review reports.',
    version: '1.0.0',
    monthlyPricingUsd: 199,
    pricingTier: 'professional',
    capabilities: ['contract_extraction', 'risk_assessment', 'obligation_tracking', 'clause_analysis'],
    requiredIntegrations: [],
    optionalIntegrations: ['GOOGLE_CALENDAR', 'SLACK'],
    defaultPolicyJson: {
      risk_scoring: { high_risk_threshold: 7, auto_approve_below: 3 },
      escalation: { always_escalate_types: ['employment', 'nda', 'merger'], value_threshold_usd: 100000 },
    },
    escalationMapJson: {
      high_risk: { assignTo: 'legal_team', sla_minutes: 240 },
      value_threshold: { assignTo: 'cfo', sla_minutes: 480 },
    },
  },
});
```

Then re-run the seed:

```bash
pnpm db:seed
```

---

## Tool Development Guide

Tools enable agents to interact with external systems (CRM, ERP, document storage, email, etc.) via LLM function calling.

### BaseTool Interface

All tools extend `BaseTool` from `ai-runtime/tools/base_tool.py`:

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Snake_case identifier, e.g., 'search_documents'."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the LLM."""
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""
        return {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool and return results."""
        ...

    # Utility methods:
    def success_result(self, data) -> dict   # {"success": True, "data": ...}
    def error_result(self, error) -> dict    # {"success": False, "error": ...}
    def to_llm_tool_spec(self, format="openai") -> dict  # Auto-converts to tool definition
```

### Using Tools in an Agent

1. **Instantiate tools** in your agent's constructor:
   ```python
   def __init__(self, llm_gateway, pii_redactor):
       super().__init__(...)
       self.storage_tool = ContractStorageTool()
       self.search_tool = KnowledgeSearchTool()
   ```

2. **Pass tool specs to `call_llm()`** for function calling:
   ```python
   tools = [
       self.storage_tool.to_llm_tool_spec(),
       self.search_tool.to_llm_tool_spec(),
   ]
   result = await self.call_llm(messages=messages, tools=tools)
   ```

3. **Execute the tool** when the LLM requests it:
   ```python
   if result.get("tool_calls"):
       for tool_call in result["tool_calls"]:
           if tool_call["name"] == "fetch_contract_document":
               tool_result = await self.storage_tool.execute(tool_call["arguments"])
   ```

### Available Tool Categories

| File                | Tools                                                   |
|---------------------|---------------------------------------------------------|
| `search_tools.py`   | Knowledge base search, document search                  |
| `crm_tools.py`      | CRM record lookup, contact management                   |
| `erp_tools.py`      | ERP system integration, order management                |
| `email_tools.py`    | Email composition, sending, template rendering          |
| `calendar_tools.py` | Calendar event creation, availability checking          |
| `document_tools.py` | Document parsing, OCR, content extraction               |

### Tool Format Conversion

The `to_llm_tool_spec()` method automatically generates the correct format for the active LLM provider:

**OpenAI format:**
```json
{
  "type": "function",
  "function": {
    "name": "fetch_contract_document",
    "description": "Retrieve a contract document from storage by its ID.",
    "parameters": { "type": "object", "properties": {...}, "required": [...] }
  }
}
```

**Anthropic format:**
```json
{
  "name": "fetch_contract_document",
  "description": "Retrieve a contract document from storage by its ID.",
  "input_schema": { "type": "object", "properties": {...}, "required": [...] }
}
```

---

## Testing Agents

### Unit Test Structure

Create test files in `ai-runtime/tests/`:

```python
# tests/test_contract_reviewer.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from agents.governance_risk.contract_reviewer import ContractReviewAgent, DEFAULT_POLICY
from llm.gateway import LLMGateway, LLMResponse
from orchestrator.pii_redactor import PIIRedactor


@pytest.fixture
def mock_llm_gateway():
    """Create a mock LLM gateway that returns predictable responses."""
    gateway = MagicMock(spec=LLMGateway)

    # Mock complete() to return a structured response
    async def mock_complete(messages, **kwargs):
        return LLMResponse(
            content=json.dumps({
                "parties": ["Acme Corp", "Widget Inc"],
                "effective_date": "2025-01-01",
                "risk_score": 4,
                "risk_factors": ["standard terms"],
                "obligations": [],
                "concerns": [],
                "recommendations": ["approve"],
            }),
            model="mock-gpt-4o",
            tokens_used=500,
            input_tokens=300,
            output_tokens=200,
            cost_usd=0.01,
            finish_reason="stop",
            provider="mock-openai",
        )

    gateway.complete = AsyncMock(side_effect=mock_complete)
    return gateway


@pytest.fixture
def mock_pii_redactor():
    """Create a PII redactor that passes text through unchanged."""
    redactor = PIIRedactor()
    return redactor


@pytest.fixture
def agent(mock_llm_gateway, mock_pii_redactor):
    return ContractReviewAgent(mock_llm_gateway, mock_pii_redactor)


class TestContractReviewAgent:
    async def test_execute_happy_path(self, agent):
        """Test successful contract review with low risk."""
        result = await agent.execute(
            task_payload={
                "contract_text": "Standard service agreement between Acme and Widget...",
                "contract_id": "contract-123",
            },
            context={"tenantId": "test-tenant", "agent_policy": DEFAULT_POLICY},
        )

        assert result["status"] == "completed"
        assert result["output"]["contract_id"] == "contract-123"
        assert "extracted_terms" in result["output"]

    async def test_escalation_on_high_risk(self, agent):
        """Test that high-risk contracts trigger escalation."""
        # Override mock to return high risk score
        # ... (customize mock response)

        result = await agent.execute(
            task_payload={"contract_text": "..."},
            context={"tenantId": "test-tenant", "agent_policy": DEFAULT_POLICY},
        )

        # Verify escalation behavior
        assert result.get("risk_level") in ("high", "critical") or result["status"] == "escalated"

    async def test_pii_redaction(self, agent):
        """Test that PII is redacted before LLM call."""
        result = await agent.execute(
            task_payload={
                "contract_text": "Contact john@example.com or call 555-1234567",
                "contract_id": "contract-456",
            },
            context={"tenantId": "test-tenant", "agent_policy": DEFAULT_POLICY},
        )

        # PII should be detected
        # The exact assertion depends on your mock setup
        assert result is not None

    async def test_capabilities(self, agent):
        """Test that the agent advertises the correct capabilities."""
        caps = agent.get_capabilities()
        assert "contract_extraction" in caps
        assert "risk_assessment" in caps
```

### Running Agent Tests

```bash
cd ai-runtime

# Run all tests
pytest

# Run a specific test file
pytest tests/test_contract_reviewer.py -v

# Run with coverage
pytest --cov=agents --cov-report=term-missing
```

### Mock LLM Responses

The `LLMGateway` automatically returns mock responses when no API keys are configured. This means you can run the full agent workflow locally without external dependencies:

```bash
# No API keys needed -- gateway returns mock responses
uvicorn api.main:app --reload
```

For more controlled testing, use the mock fixtures shown above.

---

## Policy Configuration Reference

Agent policies control behavior thresholds. They are defined as `DEFAULT_POLICY` in the agent module and can be overridden per-tenant via `AgentConfig.policyJson` in the database.

### Common Policy Fields

```python
DEFAULT_POLICY = {
    # Approval thresholds (used by should_escalate)
    "approval": {
        "thresholds": {
            "min_confidence": 0.7,    # Escalate if confidence < this
            "max_cost_usd": 1.0,      # Escalate if LLM cost exceeds this
        },
    },

    # PII redaction configuration
    "pii_redaction": {
        "enabled": True,              # Global enable/disable
        "enabled_patterns": [         # Which PII types to redact
            "email", "phone_intl", "credit_card",
            "ssn_us", "iban", "ip_address",
        ],
        "disabled_patterns": [],      # Alternative: exclude specific types
        "escalate_on_detection": False, # Escalate if PII is found
    },

    # Escalation rules
    "escalation": {
        "auto_escalate_risk_levels": ["high", "critical"],
    },

    # Retry configuration
    "retry": {
        "profile": "llm_call",       # Retry profile name
    },

    # Domain-specific settings (vary per agent)
    # ... (refund limits, SLA targets, scoring thresholds, etc.)
}
```

### How Policies Are Resolved

```
1. Agent DEFAULT_POLICY (hardcoded in agent module)
     |
     v
2. AgentConfig.policyJson (tenant-specific overrides in database)
     |
     v
3. ConfigResolver.resolve() merges tenant config over defaults
     |
     v
4. Resolved policy passed to agent in context["resolved_config"]
```

---

## Example: Building a Custom Agent from Scratch

Here is a complete, minimal agent that classifies and responds to internal IT help desk tickets.

### File: `ai-runtime/agents/delivery_ops/helpdesk_agent.py`

```python
"""AI Help Desk Agent -- classifies and responds to IT support tickets.

Implements a 2-step workflow:
  1. CLASSIFY -- Determine ticket category and priority
  2. RESPOND  -- Generate a response or escalate to human

Worker ID: ai-helpdesk-agent
Department: Delivery Operations
"""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)

DEFAULT_POLICY: dict[str, Any] = {
    "categories": ["password_reset", "software_install", "hardware_issue",
                    "network", "access_request", "other"],
    "auto_resolve_categories": ["password_reset"],
    "escalation": {
        "always_escalate_categories": ["hardware_issue"],
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.8,
            "max_cost_usd": 0.25,
        },
    },
    "pii_redaction": {
        "enabled": True,
    },
}


class HelpDeskAgent(BaseAgent):
    """Classifies IT tickets and generates responses."""

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        super().__init__(
            agent_id="ai-helpdesk-agent",
            llm_gateway=llm_gateway,
            pii_redactor=pii_redactor,
            name="Help Desk Agent",
        )

    def get_capabilities(self) -> list[str]:
        return ["ticket_classification", "auto_response", "priority_assessment"]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        policy = context.get("agent_policy", DEFAULT_POLICY)
        ticket_text = task_payload.get("ticket_text", "")
        ticket_id = task_payload.get("ticket_id", "unknown")

        total_tokens = 0
        total_cost = 0.0

        # Step 1: CLASSIFY
        classify_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the IT ticket into one of these categories: "
                        f"{', '.join(policy.get('categories', []))}. "
                        "Also assign a priority (low, medium, high, critical). "
                        "Return JSON: {category, priority, confidence, summary}."
                    ),
                },
                {"role": "user", "content": ticket_text},
            ],
            agent_policy=policy,
        )
        total_tokens += classify_result.get("tokens_used", 0)
        total_cost += classify_result.get("cost_usd", 0.0)

        try:
            classification = json.loads(classify_result["content"])
        except (json.JSONDecodeError, KeyError):
            classification = {
                "category": "other",
                "priority": "medium",
                "confidence": 0.5,
                "summary": ticket_text[:200],
            }

        category = classification.get("category", "other")
        confidence = classification.get("confidence", 0.5)

        # Check if this category should always be escalated
        always_escalate = policy.get("escalation", {}).get(
            "always_escalate_categories", []
        )
        if category in always_escalate:
            return self.format_result(
                status="escalated",
                output={
                    "ticket_id": ticket_id,
                    "classification": classification,
                    "reason": f"Category '{category}' requires human handling",
                },
                tokens_used=total_tokens,
                cost_usd=total_cost,
                next_action="human_review",
            )

        # Step 2: RESPOND
        respond_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a helpful response for this IT support ticket. "
                        "Be concise and provide step-by-step instructions. "
                        "Return JSON: {response_text, resolved, follow_up_needed}."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "ticket_text": ticket_text,
                        "classification": classification,
                    }),
                },
            ],
            agent_policy=policy,
        )
        total_tokens += respond_result.get("tokens_used", 0)
        total_cost += respond_result.get("cost_usd", 0.0)

        try:
            response = json.loads(respond_result["content"])
        except (json.JSONDecodeError, KeyError):
            response = {"response_text": respond_result.get("content", ""), "resolved": False}

        result = self.format_result(
            status="completed",
            output={
                "ticket_id": ticket_id,
                "classification": classification,
                "response": response,
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

        # Add escalation-check fields
        result["confidence"] = confidence
        result["cost_usd"] = total_cost
        result["pii_detected"] = classify_result.get("pii_detected", [])

        return result
```

### Registration

In `ai-runtime/api/main.py`:

```python
from agents.delivery_ops.helpdesk_agent import HelpDeskAgent

helpdesk = HelpDeskAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-helpdesk-agent", helpdesk)
```

### Test It

```bash
# Start the AI Runtime
cd ai-runtime
uvicorn api.main:app --reload

# Send a test request
curl -X POST http://localhost:8000/v1/agents/ai-helpdesk-agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_payload": {
      "ticket_id": "HELP-001",
      "ticket_text": "I cannot connect to the VPN from home. I get a timeout error after entering my credentials."
    },
    "context": {
      "tenantId": "test-tenant",
      "executionId": "exec-001"
    }
  }' | jq .
```
