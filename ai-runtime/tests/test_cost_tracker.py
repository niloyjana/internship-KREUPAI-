"""Tests for CostTracker.

Verifies cost calculation for known models, usage recording,
budget enforcement, and usage summary aggregation.
"""

import pytest

from llm.cost_tracker import CostTracker


class TestCostCalculation:
    """Tests for CostTracker.calculate_cost."""

    def test_known_model_cost(self):
        """calculate_cost returns correct cost for a known model."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        # gpt-4o pricing: input=$2.50/1M, output=$10.00/1M
        cost = ct.calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)

        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert abs(cost - expected) < 1e-6

    def test_mock_model_prefix_stripped(self):
        """Mock model prefix is stripped for pricing lookup."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        cost = ct.calculate_cost("mock-gpt-4o", input_tokens=1000, output_tokens=500)

        assert cost > 0

    def test_unknown_model_returns_zero(self):
        """Unknown models return $0.00."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        cost = ct.calculate_cost("unknown-model", input_tokens=1000, output_tokens=500)

        assert cost == 0.0

    def test_anthropic_model_cost(self):
        """Anthropic model pricing is applied correctly."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        cost = ct.calculate_cost(
            "claude-sonnet-4-20250514",
            input_tokens=10000,
            output_tokens=5000,
        )

        expected = (10000 / 1_000_000) * 3.00 + (5000 / 1_000_000) * 15.00
        assert abs(cost - expected) < 1e-6


class TestUsageRecording:
    """Tests for CostTracker.record_usage."""

    def test_record_usage_returns_record(self):
        """record_usage returns a complete usage record dict."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        record = ct.record_usage(
            tenant_id="t1",
            agent_id="a1",
            execution_id="exec-001",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.002,
        )

        assert record["tenant_id"] == "t1"
        assert record["agent_id"] == "a1"
        assert record["model"] == "gpt-4o"
        assert record["total_tokens"] == 150
        assert record["cost_usd"] == 0.002
        assert "timestamp" in record

    def test_multiple_records_aggregate(self):
        """Multiple usage records accumulate in tenant total."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        ct.record_usage("t1", "a1", "exec-001", "gpt-4o", 100, 50, 0.002)
        ct.record_usage("t1", "a1", "exec-002", "gpt-4o", 200, 100, 0.005)

        total = ct.get_tenant_total("t1")
        assert abs(total - 0.007) < 1e-6


class TestBudgetEnforcement:
    """Tests for CostTracker.check_budget."""

    def test_within_budget(self):
        """check_budget returns True when spend is below limit."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")
        ct.record_usage("t1", "a1", "exec-001", "gpt-4o", 100, 50, 1.00)

        assert ct.check_budget("t1", budget_limit_usd=10.00) is True

    def test_over_budget(self):
        """check_budget returns False when spend exceeds limit."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")
        ct.record_usage("t1", "a1", "exec-001", "gpt-4o", 100, 50, 15.00)

        assert ct.check_budget("t1", budget_limit_usd=10.00) is False

    def test_unknown_tenant_within_budget(self):
        """Unknown tenant has zero spend, always within budget."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        assert ct.check_budget("unknown-tenant", budget_limit_usd=1.00) is True


class TestUsageSummary:
    """Tests for CostTracker.get_usage_summary."""

    def test_summary_structure(self):
        """get_usage_summary returns expected structure with per-model breakdown."""
        ct = CostTracker(usage_log_dir="/tmp/test_usage")

        ct.record_usage("t1", "a1", "exec-001", "gpt-4o", 100, 50, 0.002)
        ct.record_usage("t1", "a1", "exec-002", "gpt-4o-mini", 200, 100, 0.001)
        ct.record_usage("t1", "a1", "exec-003", "gpt-4o", 300, 150, 0.004)

        summary = ct.get_usage_summary("t1")

        assert summary["tenant_id"] == "t1"
        assert summary["request_count"] == 3
        assert summary["total_tokens"] == 900  # 150 + 300 + 450
        assert abs(summary["total_cost_usd"] - 0.007) < 1e-6
        assert "gpt-4o" in summary["per_model"]
        assert "gpt-4o-mini" in summary["per_model"]
        assert summary["per_model"]["gpt-4o"]["requests"] == 2
