"""Cost Tracker -- monitors LLM token usage and costs per tenant.

Tracks costs in-memory and optionally persists to a local file for
development. In production this would write to the billing database.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks LLM API token usage and costs per tenant.

    Maintains per-model pricing tables and records usage for billing.
    In local dev, usage records are written to a JSON-lines file.
    In production, records would be written to the billing database
    via the workflow service.
    """

    # Token pricing per 1 million tokens (USD)
    PRICING: dict[str, dict[str, float]] = {
        # OpenAI models
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        # Anthropic models
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
        "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
        # Groq models
        "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    }

    def __init__(self, usage_log_dir: Optional[str] = None):
        """Initialize the cost tracker.

        Args:
            usage_log_dir: Directory for local usage log files. Defaults to
                           ai-runtime/logs/usage. Set to None to disable file
                           logging.
        """
        self._costs: dict[str, Decimal] = {}
        self._records: list[dict[str, Any]] = []

        if usage_log_dir is None:
            default_dir = Path(__file__).parent.parent / "logs" / "usage"
            self._usage_log_dir = default_dir
        else:
            self._usage_log_dir = Path(usage_log_dir)

    # ------------------------------------------------------------------
    # Cost calculation
    # ------------------------------------------------------------------

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for a given model and token counts.

        Args:
            model: Model identifier (e.g. 'gpt-4o', 'claude-sonnet-4-20250514').
            input_tokens: Number of input / prompt tokens.
            output_tokens: Number of output / completion tokens.

        Returns:
            Cost in USD as a float. Returns 0.0 for unknown or mock models.
        """
        # Strip mock- prefix for pricing lookup
        lookup_model = model.replace("mock-", "")

        pricing = self.PRICING.get(lookup_model)
        if pricing is None:
            logger.debug("No pricing info for model '%s'; returning $0.00", model)
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total = round(input_cost + output_cost, 8)
        return total

    # ------------------------------------------------------------------
    # Usage recording
    # ------------------------------------------------------------------

    def record_usage(
        self,
        tenant_id: str,
        agent_id: str,
        execution_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> dict[str, Any]:
        """Record a usage event for billing and observability.

        In local dev this writes to a JSON-lines log file.
        In production the workflow service would persist this to the database.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            execution_id: Execution / request identifier.
            model: Model used.
            input_tokens: Input token count.
            output_tokens: Output token count.
            cost_usd: Total cost in USD.

        Returns:
            The recorded usage entry as a dict.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "execution_id": execution_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
        }

        # Update in-memory running total
        key = tenant_id
        self._costs[key] = self._costs.get(key, Decimal("0")) + Decimal(str(cost_usd))
        self._records.append(record)

        # Persist to local file
        self._write_to_file(record)

        logger.info(
            "Usage recorded: tenant=%s agent=%s model=%s tokens=%d cost=$%.6f",
            tenant_id,
            agent_id,
            model,
            input_tokens + output_tokens,
            cost_usd,
        )
        return record

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    def get_tenant_total(self, tenant_id: str) -> float:
        """Get running total cost for a tenant (in-memory).

        Args:
            tenant_id: Tenant identifier.

        Returns:
            Total cost in USD.
        """
        return float(self._costs.get(tenant_id, Decimal("0")))

    def check_budget(self, tenant_id: str, budget_limit_usd: float) -> bool:
        """Check whether the tenant is within their budget.

        Args:
            tenant_id: Tenant identifier.
            budget_limit_usd: Maximum allowed spend in USD.

        Returns:
            True if tenant spend is below the limit, False otherwise.
        """
        current = self._costs.get(tenant_id, Decimal("0"))
        return current < Decimal(str(budget_limit_usd))

    def get_usage_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get a summary of usage for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            Dict with total_cost, total_tokens, request_count, and
            per-model breakdown.
        """
        tenant_records = [r for r in self._records if r["tenant_id"] == tenant_id]
        total_cost = sum(r["cost_usd"] for r in tenant_records)
        total_tokens = sum(r["total_tokens"] for r in tenant_records)

        per_model: dict[str, dict[str, Any]] = {}
        for r in tenant_records:
            model = r["model"]
            if model not in per_model:
                per_model[model] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            per_model[model]["requests"] += 1
            per_model[model]["tokens"] += r["total_tokens"]
            per_model[model]["cost_usd"] += r["cost_usd"]

        return {
            "tenant_id": tenant_id,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "request_count": len(tenant_records),
            "per_model": per_model,
        }

    # ------------------------------------------------------------------
    # File persistence (local dev)
    # ------------------------------------------------------------------

    def _write_to_file(self, record: dict[str, Any]) -> None:
        """Append a usage record to the local JSON-lines log file."""
        try:
            self._usage_log_dir.mkdir(parents=True, exist_ok=True)
            log_file = self._usage_log_dir / f"usage_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.warning("Failed to write usage log: %s", exc)
