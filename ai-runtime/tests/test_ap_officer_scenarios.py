"""Comprehensive scenario tests for APOfficerAgent.

Verifies specific business rules:
- First-time bank detail submission
- Price and quantity variances
- Exact and near-duplicate detection
- Vendor status handling (new, blocked, approved)
- Bank detail changes
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from agents.finance_procurement.ap_officer import APOfficerAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_agent(mock_llm_gateway, mock_pii_redactor):
    """Create an APOfficerAgent with mocked dependencies."""
    agent = APOfficerAgent(
        llm_gateway=mock_llm_gateway,
        pii_redactor=mock_pii_redactor,
    )
    # Mock call_llm to return a simple summary string
    agent.call_llm = AsyncMock(return_value={"content": "Mocked summary", "tokens_used": 10, "cost_usd": 0.001})
    return agent


def _build_context(overrides=None):
    """Build a standard execution context for test scenarios."""
    ctx = {
        "tenantId": "tenant-001",
        "executionId": "exec-002",
        "vendor_master": [
            {
                "id": "VEND-001",
                "name": "Acme Corp",
                "status": "approved",
                "bank_details": {"iban": "US123456789"},
            },
            {
                "id": "VEND-002",
                "name": "Globex",
                "status": "approved",
                # No bank details for Globex in master
            },
            {
                "id": "VEND-003",
                "name": "Evil Corp",
                "status": "blocked",
            }
        ],
        "purchase_orders": [
            {
                "po_number": "PO-100",
                "vendor_name": "Acme Corp",
                "total_amount": 1000.00,
                "line_items": [
                    {"description": "Gadgets", "quantity": 10, "unit_price": 100.00}
                ],
            }
        ],
        "recent_invoices": [
            {
                "id": "INV-OLD-001",
                "invoice_number": "INV-2024-999",
                "vendor_name": "Acme Corp",
                "total_amount": 500.00,
                "invoice_date": "2024-01-01",
            }
        ],
        "agent_policy": {},
        "resolved_config": {},
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, list) and k in ctx:
                ctx[k].extend(v)
            else:
                ctx[k] = v
    return ctx


# ---------------------------------------------------------------------------
# Scenario Tests
# ---------------------------------------------------------------------------

class TestAPOfficerScenarios:
    """End-to-end business logic tests for AP Officer."""

    @pytest.mark.asyncio
    async def test_scenario_clean_invoice(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 1: Perfect match, approved vendor, no risks."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        payload = {
            "type": "process_invoice",
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-2024-001",
            "total_amount": 1000.00,
            "currency": "USD",
            "po_number": "PO-100",
            "bank_details": {"iban": "US123456789"},
            "line_items": [{"description": "Gadgets", "quantity": 10, "unit_price": 100.00}]
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "completed"
        output = result["output"]
        assert output["outcome"]["outcome"] == "payment_batch"
        assert output["outcome"]["risk_score"] < 0.2
        assert not output["outcome"]["flags"]

    @pytest.mark.asyncio
    async def test_scenario_first_time_bank_details(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 2: First-time bank details for an approved vendor."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        payload = {
            "type": "process_invoice",
            "vendor_name": "Globex",
            "invoice_number": "INV-GLOBEX-001",
            "total_amount": 500.00,
            "currency": "USD",
            "bank_details": {"iban": "GB987654321"}, # Provided first time
            "line_items": [{"description": "Consulting", "quantity": 1, "unit_price": 500.00}]
        }

        result = await agent.execute(payload, context)
        
        # Should be escalated due to first-time bank details
        assert result["status"] == "escalated"
        output = result["output"]
        assert output["outcome"]["outcome"] == "escalate"
        assert "first_time_bank_details" in output["outcome"]["flags"]
        assert output["outcome"]["risk_score"] >= 0.75

    @pytest.mark.asyncio
    async def test_scenario_price_variance(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 3: Price variance exceeding tolerance (2%)."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        payload = {
            "type": "process_invoice",
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-ACME-VAR",
            "total_amount": 1100.00, # 10% higher than PO
            "currency": "USD",
            "po_number": "PO-100",
            "bank_details": {"iban": "US123456789"},
            "line_items": [{"description": "Gadgets", "quantity": 10, "unit_price": 110.00}]
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "escalated"
        output = result["output"]
        assert output["outcome"]["outcome"] == "escalate"
        assert "po_mismatch" in output["outcome"]["flags"]
        assert output["po_matching"]["match_result"] == "mismatch"
        assert output["po_matching"]["price_variance_percent"] == 10.0

    @pytest.mark.asyncio
    async def test_scenario_exact_duplicate(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 4: Exact duplicate detected."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        
        # Add the "existing" invoice to recent_invoices
        context = _build_context({
            "recent_invoices": [
                {
                    "id": "INV-EXISTING-123",
                    "invoice_number": "INV-DUP-100",
                    "vendor_name": "Acme Corp",
                    "total_amount": 1000.00,
                    "invoice_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
            ]
        })

        payload = {
            "type": "process_invoice",
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-DUP-100",
            "total_amount": 1000.00,
            "currency": "USD",
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "escalated" # block routes to escalated result status
        output = result["output"]
        assert output["outcome"]["outcome"] == "block"
        assert "exact_duplicate" in output["outcome"]["flags"]
        assert output["duplicate_check"]["is_duplicate"] is True

    @pytest.mark.asyncio
    async def test_scenario_near_duplicate(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 5: Near-duplicate detected (same vendor, same amount, different invoice number)."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        
        context = _build_context({
            "recent_invoices": [
                {
                    "id": "INV-EXISTING-456",
                    "invoice_number": "INV-ORIG-001",
                    "vendor_name": "Acme Corp",
                    "total_amount": 1000.00,
                    "invoice_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
            ]
        })

        payload = {
            "type": "process_invoice",
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-NEAR-001", # Different number
            "total_amount": 1000.00, # Same amount
            "currency": "USD",
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "escalated"
        output = result["output"]
        assert output["outcome"]["outcome"] == "block"
        assert "near_duplicate" in output["outcome"]["flags"]

    @pytest.mark.asyncio
    async def test_scenario_new_vendor(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 6: New vendor not in master list."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        # Context with multiple POs so the "single PO fallback" doesn't trigger
        context = _build_context({
            "purchase_orders": [
                {
                    "po_number": "PO-OTHER",
                    "vendor_name": "Other Corp",
                    "total_amount": 100.00,
                }
            ]
        })

        payload = {
            "type": "process_invoice",
            "vendor_name": "Unknown Startup",
            "invoice_number": "INV-NEW-999",
            "total_amount": 500.00,
            "currency": "USD",
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "escalated" # hold status results in escalated result status
        output = result["output"]
        assert output["outcome"]["outcome"] == "hold"
        assert "new_vendor_hold" in output["outcome"]["flags"]

    @pytest.mark.asyncio
    async def test_scenario_blocked_vendor(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 7: Vendor is blocked in master list."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        payload = {
            "type": "process_invoice",
            "vendor_name": "Evil Corp",
            "invoice_number": "INV-EVIL-666",
            "total_amount": 666.00,
            "currency": "USD",
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "escalated"
        output = result["output"]
        assert output["outcome"]["outcome"] == "block"
        assert "blocked_vendor" in output["outcome"]["flags"]

    @pytest.mark.asyncio
    async def test_scenario_bank_detail_change(self, mock_llm_gateway, mock_pii_redactor):
        """Scenario 8: Bank details don't match vendor master."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        payload = {
            "type": "process_invoice",
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-FRAUD-001",
            "total_amount": 1000.00,
            "currency": "USD",
            "bank_details": {"iban": "RU666666666"}, # Different from master US123...
            "line_items": [{"description": "Gadgets", "quantity": 10, "unit_price": 100.00}]
        }

        result = await agent.execute(payload, context)
        
        assert result["status"] == "escalated"
        output = result["output"]
        assert output["outcome"]["outcome"] == "escalate"
        assert "bank_details_changed" in output["outcome"]["flags"]
        assert output["vendor_validation"]["bank_details_match"] is False

