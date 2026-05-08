"""AI General Ledger Analyst -- validates journals, reconciles accounts, detects anomalies.

Implements the 4-step GL analysis workflow:
  1. VALIDATE JOURNAL -- Check journal entries for balance, completeness, and policy
  2. RECONCILE -- Match GL accounts against sub-ledgers or bank statements
  3. ANOMALY DETECTION -- Detect unusual postings, variances, and patterns
  4. REPORTING -- Generate period-end GL report with findings and recommendations

Also handles:
  - ``validate_journal``: Validate one or more journal entries individually
  - ``reconcile_accounts``: Reconcile a specific GL account against external source

Worker ID: ai-gl-analyst
Department: Finance & Procurement
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.finance_procurement.tools import (
    JournalValidatorTool,
    ReconciliationTool,
    VarianceDetectorTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "reconciliation_tolerances": {
        "balance_tolerance": 0.01,
        "stale_item_days": 30,
        "auto_clear_matched": True,
        "mandatory_accounts": [
            "cash",
            "bank",
            "accounts_receivable",
            "accounts_payable",
            "intercompany",
        ],
        "reconciliation_frequency": "monthly",
    },
    "journal_validation_rules": {
        "auto_post_limit": 10000,
        "materiality_threshold": 50000,
        "trivial_threshold": 5000,
        "require_dual_approval_above": 50000,
        "blocked_account_types": ["suspense", "intercompany"],
        "auto_post_entry_types": [
            "standard",
            "recurring",
            "accrual",
            "depreciation",
        ],
        "require_description": True,
        "require_source_document": True,
    },
    "anomaly_detection": {
        "round_number_threshold": 10000,
        "off_hours_posting_alert": True,
        "unusual_account_combination_check": True,
        "historical_lookback_months": 12,
        "variance_threshold_percent": 5,
        "variance_threshold_amount": 1000,
        "critical_variance_percent": 15,
        "critical_variance_amount": 10000,
        "trend_alert_consecutive_months": 3,
    },
    "period_close": {
        "close_checklist": [
            "validate_all_journals",
            "reconcile_mandatory_accounts",
            "run_variance_analysis",
            "review_suspense_balances",
            "post_accruals",
            "run_depreciation",
            "generate_trial_balance",
        ],
        "max_open_items_for_close": 5,
        "auto_reverse_accruals": True,
        "close_day_of_month": 5,
        "reminder_days_before": [3, 1],
    },
}


class GLAnalystAgent(BaseAgent):
    """AI General Ledger Analyst -- validates journals, reconciles, detects anomalies.

    Executes a four-step workflow for GL analysis:
      1. Validate Journal: check entries for balance and policy compliance
      2. Reconcile: match GL accounts against sub-ledgers and bank statements
      3. Anomaly Detection: detect unusual postings and budget variances
      4. Reporting: generate period-end GL report with findings

    Also supports individual tasks for journal validation and account
    reconciliation via the ``validate_journal`` and ``reconcile_accounts``
    task types.

    Attributes:
        _journal_validator: Tool for validating journal entries.
        _reconciliation: Tool for reconciling GL accounts.
        _variance_detector: Tool for detecting budget variances.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the GL Analyst agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-gl-analyst", llm_gateway, pii_redactor)
        self.name = "AI General Ledger Analyst"
        self._journal_validator = JournalValidatorTool()
        self._reconciliation = ReconciliationTool()
        self._variance_detector = VarianceDetectorTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "journal_entry_validation",
            "debit_credit_balance_check",
            "account_code_validation",
            "auto_post_evaluation",
            "materiality_assessment",
            "account_reconciliation",
            "bank_reconciliation",
            "sub_ledger_reconciliation",
            "intercompany_reconciliation",
            "anomaly_detection",
            "budget_vs_actual_analysis",
            "trend_analysis",
            "period_end_close_support",
            "trial_balance_review",
            "gl_reporting",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``handle_inquiry`` (default): Full 4-step period close workflow
          - ``validate_journal``: Validate one or more journal entries
          - ``reconcile_accounts``: Reconcile a GL account against external source

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "handle_inquiry")

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "validate_journal":
            return await self._handle_validate_journal(task_payload, context)
        elif task_type == "reconcile_accounts":
            return await self._handle_reconcile_accounts(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Main workflow: handle_inquiry (4-step)
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step GL analysis workflow.

        Steps:
          1. Validate Journal -- validate all pending journal entries
          2. Reconcile -- reconcile mandatory accounts
          3. Anomaly Detection -- run budget-vs-actual and pattern analysis
          4. Reporting -- generate period-end GL report

        Args:
            task_payload: Period close parameters (period, fiscal_year).
            context: Execution context with journal_entries, gl_transactions,
                     budget, and account data.

        Returns:
            Standardized result dict with detailed period close output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", "unknown"))
        audit_events: list[dict[str, Any]] = []

        policy = self._resolve_policy(context)
        period = task_payload.get(
            "period", datetime.now(timezone.utc).strftime("%Y-%m")
        )

        # Step 1: Validate Journals
        journal_results = await self._step_validate_journals(context, policy)
        audit_events.append(self._audit_event(
            "gl.journal.validated",
            tenant_id,
            execution_id,
            period=period,
            total_entries=journal_results.get("total_entries", 0),
            valid=journal_results.get("valid", 0),
            invalid=journal_results.get("invalid", 0),
        ))

        # Step 2: Reconcile Accounts
        recon_results = await self._step_reconcile_accounts(context, policy)
        audit_events.append(self._audit_event(
            "gl.reconciliation.completed",
            tenant_id,
            execution_id,
            period=period,
            total_accounts=recon_results.get("total_accounts", 0),
            reconciled=recon_results.get("reconciled", 0),
            unreconciled=recon_results.get("unreconciled", 0),
        ))

        # Step 3: Anomaly Detection
        anomaly_results = await self._step_anomaly_detection(
            context, policy, period
        )
        if anomaly_results.get("anomaly_count", 0) > 0:
            audit_events.append(self._audit_event(
                "gl.anomaly.detected",
                tenant_id,
                execution_id,
                period=period,
                anomaly_count=anomaly_results.get("anomaly_count", 0),
                high_severity_count=anomaly_results.get("high_severity_count", 0),
            ))
        audit_events.append(self._audit_event(
            "gl.variance.analyzed",
            tenant_id,
            execution_id,
            period=period,
            flagged_count=anomaly_results.get("flagged_count", 0),
            critical_count=anomaly_results.get("critical_count", 0),
            accounts_analyzed=anomaly_results.get("accounts_analyzed", 0),
        ))

        # Step 4: Generate Report via LLM
        report_result = await self._step_generate_report(
            journal_results, recon_results, anomaly_results, policy, period
        )
        total_tokens += report_result.get("tokens_used", 0)
        total_cost += report_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "gl.report.generated",
            tenant_id,
            execution_id,
            period=period,
            tokens_used=report_result.get("tokens_used", 0),
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Evaluate close readiness
        close_readiness = self._evaluate_close_readiness(
            journal_results, recon_results, anomaly_results, policy
        )

        # Build comprehensive output
        output: dict[str, Any] = {
            "period": period,
            "journal_validation": journal_results,
            "reconciliation": recon_results,
            "anomaly_detection": anomaly_results,
            "close_readiness": close_readiness,
            "report": report_result.get("content", "Period close report generated."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Journal entries always require human accountant approval "
                "before posting. Period lock/unlock only authorized by "
                "finance controller."
            ),
        }

        # Determine status
        ready_to_close = close_readiness.get("ready", False)
        has_critical = close_readiness.get("critical_issues", 0) > 0

        next_action: Optional[str] = None
        if not ready_to_close or has_critical:
            next_action = "human_review"

        result = self.format_result(
            status="completed" if ready_to_close else "escalated",
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "period": period,
                "ready_to_close": ready_to_close,
                "journals_validated": journal_results.get("total_entries", 0),
                "accounts_reconciled": recon_results.get("total_accounts", 0),
                "anomalies_flagged": anomaly_results.get("flagged_count", 0),
            },
        )

        if has_critical:
            result["risk_level"] = "high"
        elif not ready_to_close:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Validate Journals
    # ------------------------------------------------------------------

    async def _step_validate_journals(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate all pending journal entries for balance and compliance.

        Iterates through journal entries in context and validates each
        one for debit/credit balance, completeness, valid account codes,
        materiality thresholds, and auto-post eligibility.

        Args:
            context: Execution context containing journal_entries and
                     chart_of_accounts.
            policy: Resolved policy configuration.

        Returns:
            Dict with validation summary including valid/invalid counts,
            errors, warnings, and individual results.
        """
        journal_entries = context.get("journal_entries", [])
        coa = context.get("chart_of_accounts", [])
        je_rules = policy.get("journal_validation_rules", {})
        auto_post_limit = je_rules.get("auto_post_limit", 10000)
        materiality = je_rules.get("materiality_threshold", 50000)

        if not journal_entries:
            return {
                "total_entries": 0,
                "valid": 0,
                "invalid": 0,
                "can_auto_post": 0,
                "needs_approval": 0,
                "material_entries": 0,
                "total_debit": 0.0,
                "total_credit": 0.0,
                "errors": [],
                "warnings": [],
                "results": [],
                "summary": "No journal entries to validate.",
            }

        valid_count = 0
        invalid_count = 0
        auto_post_count = 0
        needs_approval_count = 0
        material_count = 0
        all_errors: list[str] = []
        all_warnings: list[str] = []
        results: list[dict[str, Any]] = []
        total_debit = 0.0
        total_credit = 0.0

        for je in journal_entries:
            result = await self._journal_validator.execute({
                "journal_entry": je,
                "chart_of_accounts": coa,
                "auto_post_limit": auto_post_limit,
                "materiality_threshold": materiality,
            })

            if result.get("success"):
                data = result["data"]
                results.append(data)

                if data.get("valid"):
                    valid_count += 1
                else:
                    invalid_count += 1
                    all_errors.extend(data.get("errors", []))

                all_warnings.extend(data.get("warnings", []))

                if data.get("can_auto_post"):
                    auto_post_count += 1
                else:
                    needs_approval_count += 1

                if data.get("is_material"):
                    material_count += 1

                total_debit += data.get("total_debit", 0)
                total_credit += data.get("total_credit", 0)
            else:
                invalid_count += 1
                all_errors.append(f"Validation failed: {result.get('error')}")

        return {
            "total_entries": len(journal_entries),
            "valid": valid_count,
            "invalid": invalid_count,
            "can_auto_post": auto_post_count,
            "needs_approval": needs_approval_count,
            "material_entries": material_count,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "errors": all_errors,
            "warnings": all_warnings,
            "results": results,
            "summary": (
                f"Validated {len(journal_entries)} entries: "
                f"{valid_count} valid, {invalid_count} invalid. "
                f"{auto_post_count} can auto-post, {needs_approval_count} need approval."
            ),
        }

    # ------------------------------------------------------------------
    # Step 2: Reconcile Accounts
    # ------------------------------------------------------------------

    async def _step_reconcile_accounts(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Reconcile mandatory GL accounts against external sources.

        Processes reconciliation data for each account provided in the
        context. Uses the ReconciliationTool for matching transactions.

        Args:
            context: Execution context containing reconciliation_data
                     with account details and transactions.
            policy: Resolved policy configuration.

        Returns:
            Dict with reconciliation summary including reconciled/unreconciled
            counts, unmatched items, and individual results.
        """
        recon_data = context.get("reconciliation_data", [])
        recon_policy = policy.get("reconciliation_tolerances", {})
        tolerance = recon_policy.get("balance_tolerance", 0.01)

        if not recon_data:
            return {
                "total_accounts": 0,
                "reconciled": 0,
                "unreconciled": 0,
                "total_unmatched_items": 0,
                "total_balance_difference": 0.0,
                "results": [],
                "summary": "No reconciliation data provided.",
            }

        reconciled_count = 0
        unreconciled_count = 0
        total_unmatched = 0
        total_diff = 0.0
        results: list[dict[str, Any]] = []

        for account in recon_data:
            result = await self._reconciliation.execute({
                "account_code": account.get("account_code", ""),
                "account_name": account.get("account_name", ""),
                "gl_transactions": account.get("gl_transactions", []),
                "external_transactions": account.get("external_transactions", []),
                "gl_balance": account.get("gl_balance"),
                "external_balance": account.get("external_balance"),
                "reconciliation_type": account.get(
                    "reconciliation_type", "bank"
                ),
                "tolerance": tolerance,
            })

            if result.get("success"):
                data = result["data"]
                results.append(data)

                if data.get("reconciled"):
                    reconciled_count += 1
                else:
                    unreconciled_count += 1

                total_unmatched += (
                    data.get("unmatched_gl_count", 0)
                    + data.get("unmatched_external_count", 0)
                )
                if data.get("balance_difference") is not None:
                    total_diff += abs(data["balance_difference"])
            else:
                unreconciled_count += 1

        return {
            "total_accounts": len(recon_data),
            "reconciled": reconciled_count,
            "unreconciled": unreconciled_count,
            "total_unmatched_items": total_unmatched,
            "total_balance_difference": round(total_diff, 2),
            "results": results,
            "summary": (
                f"Reconciled {len(recon_data)} accounts: "
                f"{reconciled_count} reconciled, {unreconciled_count} unreconciled. "
                f"{total_unmatched} unmatched items, ${total_diff:,.2f} total difference."
            ),
        }

    # ------------------------------------------------------------------
    # Step 3: Anomaly Detection
    # ------------------------------------------------------------------

    async def _step_anomaly_detection(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
        period: str,
    ) -> dict[str, Any]:
        """Detect anomalies in GL postings and budget variances.

        Uses the VarianceDetectorTool for budget-vs-actual comparison and
        the LLM for pattern-based anomaly detection (round numbers, unusual
        account combinations, off-hours postings).

        Args:
            context: Execution context with actuals, budget, and GL data.
            policy: Resolved policy configuration.
            period: Period label for the analysis.

        Returns:
            Dict with detected anomalies, variance results, and flags.
        """
        actuals = context.get("actuals", context.get("gl_balances", []))
        budget = context.get("budget", context.get("budget_data", []))
        anomaly_config = policy.get("anomaly_detection", {})

        # Run variance detection
        variance_result = await self._variance_detector.execute({
            "actuals": actuals,
            "budget": budget,
            "period": period,
            "variance_threshold_percent": anomaly_config.get(
                "variance_threshold_percent", 5
            ),
            "variance_threshold_amount": anomaly_config.get(
                "variance_threshold_amount", 1000
            ),
            "comparison_type": context.get("comparison_type", "budget"),
        })

        variance_data: dict[str, Any] = {}
        if variance_result.get("success"):
            variance_data = variance_result["data"]

        # Use LLM for pattern-based anomaly detection
        journal_entries = context.get("journal_entries", [])
        recent_postings = journal_entries[:20] if journal_entries else []

        anomaly_input = json.dumps(
            {
                "period": period,
                "variance_summary": {
                    "total_variance": variance_data.get("total_variance", 0),
                    "flagged_count": variance_data.get("flagged_count", 0),
                    "critical_count": variance_data.get("critical_count", 0),
                    "top_variances": [
                        {
                            "account": v.get("account_name"),
                            "variance_amount": v.get("variance_amount"),
                            "variance_percent": v.get("variance_percent"),
                            "significance": v.get("significance"),
                        }
                        for v in variance_data.get("flagged_variances", [])[:5]
                    ],
                },
                "recent_postings_count": len(recent_postings),
                "posting_samples": [
                    {
                        "entry_id": p.get("entry_id", p.get("id")),
                        "date": p.get("date", p.get("entry_date")),
                        "description": p.get("description", p.get("memo")),
                        "amount": sum(
                            float(l.get("debit", 0))
                            for l in p.get("line_items", p.get("lines", []))
                        ),
                    }
                    for p in recent_postings[:10]
                ],
                "anomaly_rules": {
                    "round_number_threshold": anomaly_config.get(
                        "round_number_threshold", 10000
                    ),
                    "off_hours_alert": anomaly_config.get(
                        "off_hours_posting_alert", True
                    ),
                    "unusual_combinations": anomaly_config.get(
                        "unusual_account_combination_check", True
                    ),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI General Ledger Analyst performing anomaly detection. "
                    "Analyze the GL data for:\n"
                    "1. Round-number postings above the threshold\n"
                    "2. Entries posted outside business hours\n"
                    "3. Reversals of large entries without explanation\n"
                    "4. Unusual account combinations (debit/credit patterns)\n"
                    "5. Month-end spike entries exceeding historical averages\n"
                    "6. Entries without source document references\n\n"
                    "Classify each anomaly as: LOW | MEDIUM | HIGH severity.\n\n"
                    "Respond in JSON format with keys: anomalies (array), "
                    "anomaly_count, high_severity_count, summary, confidence."
                ),
            },
            {
                "role": "user",
                "content": f"GL anomaly detection data:\n{anomaly_input}",
            },
        ]

        llm_result = await self.call_llm(messages)

        # Parse LLM response
        llm_content = llm_result.get("content", "")
        anomaly_analysis: dict[str, Any] = {}
        try:
            anomaly_analysis = json.loads(llm_content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse anomaly detection LLM response as JSON: %s",
                llm_content[:200],
            )
            anomaly_analysis = {
                "anomalies": [],
                "anomaly_count": 0,
                "high_severity_count": 0,
                "summary": "Anomaly detection could not parse LLM response.",
                "confidence": 0.5,
            }

        # Merge variance and anomaly results
        return {
            "period": period,
            "variance_analysis": variance_data,
            "anomalies": anomaly_analysis.get("anomalies", []),
            "anomaly_count": anomaly_analysis.get("anomaly_count", 0),
            "high_severity_count": anomaly_analysis.get(
                "high_severity_count", 0
            ),
            "flagged_count": variance_data.get("flagged_count", 0),
            "critical_count": variance_data.get("critical_count", 0),
            "accounts_analyzed": variance_data.get("accounts_analyzed", 0),
            "summary": anomaly_analysis.get(
                "summary", "Anomaly detection completed."
            ),
            "confidence": anomaly_analysis.get("confidence", 0.75),
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
        }

    # ------------------------------------------------------------------
    # Step 4: Generate Report
    # ------------------------------------------------------------------

    async def _step_generate_report(
        self,
        journal_results: dict[str, Any],
        recon_results: dict[str, Any],
        anomaly_results: dict[str, Any],
        policy: dict[str, Any],
        period: str,
    ) -> dict[str, Any]:
        """Generate a period-end GL report using the LLM.

        Produces a comprehensive summary of all GL analysis steps
        with findings, anomaly flags, and recommendations.

        Args:
            journal_results: Journal validation results.
            recon_results: Reconciliation results.
            anomaly_results: Anomaly detection results.
            policy: Resolved policy configuration.
            period: Period label.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        report_data = json.dumps(
            {
                "period": period,
                "journals": {
                    "total": journal_results.get("total_entries", 0),
                    "valid": journal_results.get("valid", 0),
                    "invalid": journal_results.get("invalid", 0),
                    "auto_post": journal_results.get("can_auto_post", 0),
                    "material": journal_results.get("material_entries", 0),
                    "errors": journal_results.get("errors", [])[:5],
                },
                "reconciliation": {
                    "total_accounts": recon_results.get("total_accounts", 0),
                    "reconciled": recon_results.get("reconciled", 0),
                    "unreconciled": recon_results.get("unreconciled", 0),
                    "unmatched_items": recon_results.get(
                        "total_unmatched_items", 0
                    ),
                    "balance_diff": recon_results.get(
                        "total_balance_difference", 0
                    ),
                },
                "anomalies": {
                    "anomaly_count": anomaly_results.get("anomaly_count", 0),
                    "high_severity": anomaly_results.get(
                        "high_severity_count", 0
                    ),
                    "variance_flagged": anomaly_results.get("flagged_count", 0),
                    "variance_critical": anomaly_results.get(
                        "critical_count", 0
                    ),
                    "top_variances": [
                        {
                            "account": v.get("account_name"),
                            "variance": v.get("variance_amount"),
                            "percent": v.get("variance_percent"),
                        }
                        for v in anomaly_results.get(
                            "variance_analysis", {}
                        ).get("flagged_variances", [])[:5]
                    ],
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI General Ledger Analyst. Generate a concise period-end "
                    "GL report (5-8 sentences) covering:\n"
                    "- Journal entry validation summary and any issues\n"
                    "- Account reconciliation status and unmatched items\n"
                    "- Anomalies detected and their severity\n"
                    "- Key budget variances and their significance\n"
                    "- Overall close readiness assessment\n"
                    "- Recommended actions before closing the period\n"
                    "Be precise with numbers. Use professional financial language."
                ),
            },
            {
                "role": "user",
                "content": f"Period close data for {period}:\n{report_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get(
                    "response", parsed.get("report", parsed.get("summary", ""))
                )
            except json.JSONDecodeError:
                pass

        # Fallback to generated summary
        if not content or content.startswith("{"):
            j = journal_results
            r = recon_results
            a = anomaly_results

            content = (
                f"GL Period Close Report for {period}: "
                f"Validated {j.get('total_entries', 0)} journal entries -- "
                f"{j.get('valid', 0)} valid, {j.get('invalid', 0)} invalid. "
                f"Reconciled {r.get('total_accounts', 0)} accounts -- "
                f"{r.get('reconciled', 0)} reconciled, "
                f"{r.get('unreconciled', 0)} unreconciled "
                f"with ${r.get('total_balance_difference', 0):,.2f} total difference. "
                f"Anomaly detection: {a.get('anomaly_count', 0)} anomalies found, "
                f"{a.get('high_severity_count', 0)} high severity. "
                f"Variance analysis: {a.get('flagged_count', 0)} flagged "
                f"({a.get('critical_count', 0)} critical) of "
                f"{a.get('accounts_analyzed', 0)} accounts analyzed."
            )

        llm_result["content"] = content
        return llm_result

    # ------------------------------------------------------------------
    # Individual task: validate_journal
    # ------------------------------------------------------------------

    async def _handle_validate_journal(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate one or more journal entries individually.

        Accepts either a single journal_entry or a list of journal_entries
        in the task payload. Checks debit/credit balance, account code
        validity, materiality, and auto-post eligibility.

        Args:
            task_payload: Journal entry data.
            context: Execution context with chart_of_accounts.

        Returns:
            Standardized result with validation details and LLM summary.
        """
        policy = self._resolve_policy(context)
        je_rules = policy.get("journal_validation_rules", {})
        auto_post_limit = je_rules.get("auto_post_limit", 10000)
        materiality = je_rules.get("materiality_threshold", 50000)
        coa = context.get("chart_of_accounts", [])

        # Handle single entry or list
        entries = task_payload.get("journal_entries", [])
        single_entry = task_payload.get("journal_entry")
        if single_entry and not entries:
            entries = [single_entry]

        if not entries:
            # Treat payload minus type as journal entry
            entry_data = {k: v for k, v in task_payload.items() if k != "type"}
            if entry_data:
                entries = [entry_data]

        results: list[dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0

        for je in entries:
            result = await self._journal_validator.execute({
                "journal_entry": je,
                "chart_of_accounts": coa,
                "auto_post_limit": auto_post_limit,
                "materiality_threshold": materiality,
            })

            if result.get("success"):
                data = result["data"]
                results.append(data)
                if data.get("valid"):
                    valid_count += 1
                else:
                    invalid_count += 1
            else:
                invalid_count += 1
                results.append({
                    "valid": False,
                    "error": result.get("error"),
                })

        # Generate LLM summary for validated entries
        total_tokens = 0
        total_cost = 0.0
        summary = ""

        if entries:
            val_data = json.dumps(
                {
                    "entries_validated": len(entries),
                    "valid": valid_count,
                    "invalid": invalid_count,
                    "details": [
                        {
                            "entry_id": r.get("entry_id"),
                            "valid": r.get("valid"),
                            "balanced": r.get("balanced"),
                            "amount": r.get("entry_amount"),
                            "can_auto_post": r.get("can_auto_post"),
                            "errors": r.get("errors", []),
                            "warnings": r.get("warnings", []),
                        }
                        for r in results
                    ],
                },
                default=str,
            )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are the AI GL Analyst. Summarize the journal entry validation "
                        "results in 2-3 sentences. Highlight any errors, balance issues, "
                        "or approval requirements. Be specific about which entries have issues."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Validation results:\n{val_data}",
                },
            ]

            llm_result = await self.call_llm(messages)
            total_tokens = llm_result.get("tokens_used", 0)
            total_cost = llm_result.get("cost_usd", 0.0)
            summary = llm_result.get("content", "")

            if summary.startswith("{"):
                try:
                    parsed = json.loads(summary)
                    summary = parsed.get(
                        "response", parsed.get("summary", "")
                    )
                except json.JSONDecodeError:
                    pass

            if not summary or summary.startswith("{"):
                summary = (
                    f"Validated {len(entries)} journal entries: "
                    f"{valid_count} valid, {invalid_count} invalid."
                )

        return self.format_result(
            status="completed",
            output={
                "entries_validated": len(entries),
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "results": results,
                "summary": summary,
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action="human_review" if invalid_count > 0 else None,
            metadata={
                "valid": valid_count,
                "invalid": invalid_count,
            },
        )

    # ------------------------------------------------------------------
    # Individual task: reconcile_accounts
    # ------------------------------------------------------------------

    async def _handle_reconcile_accounts(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Reconcile a specific GL account against an external source.

        Matches GL transactions against bank statements, sub-ledger entries,
        or intercompany balances. Uses the LLM to generate a summary
        of findings and recommended adjustments.

        Args:
            task_payload: Account details and transaction data.
            context: Execution context.

        Returns:
            Standardized result with reconciliation details and summary.
        """
        policy = self._resolve_policy(context)
        tolerance = policy.get("reconciliation_tolerances", {}).get(
            "balance_tolerance", 0.01
        )

        account_code = task_payload.get("account_code", "")
        account_name = task_payload.get("account_name", account_code)

        result = await self._reconciliation.execute({
            "account_code": account_code,
            "account_name": account_name,
            "gl_transactions": task_payload.get("gl_transactions", []),
            "external_transactions": task_payload.get(
                "external_transactions", []
            ),
            "gl_balance": task_payload.get("gl_balance"),
            "external_balance": task_payload.get("external_balance"),
            "reconciliation_type": task_payload.get(
                "reconciliation_type", "bank"
            ),
            "tolerance": tolerance,
        })

        if not result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Reconciliation failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        recon_data = result["data"]

        # Generate LLM summary
        recon_summary = json.dumps(
            {
                "account": account_code,
                "account_name": account_name,
                "reconciliation_type": recon_data.get("reconciliation_type"),
                "reconciled": recon_data.get("reconciled"),
                "matched": recon_data.get("matched_count"),
                "unmatched_gl": recon_data.get("unmatched_gl_count"),
                "unmatched_ext": recon_data.get("unmatched_external_count"),
                "gl_balance": recon_data.get("gl_balance"),
                "external_balance": recon_data.get("external_balance"),
                "balance_diff": recon_data.get("balance_difference"),
                "adjustments": recon_data.get("recommended_adjustments", []),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI GL Analyst. Summarize the account reconciliation "
                    "results in 2-3 sentences. Note the reconciliation status, any "
                    "unmatched items, balance differences, and recommended adjustments. "
                    "Be specific with dollar amounts."
                ),
            },
            {
                "role": "user",
                "content": f"Reconciliation results:\n{recon_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get(
                    "response", parsed.get("summary", "")
                )
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            reconciled = recon_data.get("reconciled", False)
            summary = (
                f"Account {account_code}: "
                f"{'RECONCILED' if reconciled else 'UNRECONCILED'}. "
                f"{recon_data.get('matched_count', 0)} matched, "
                f"{recon_data.get('unmatched_gl_count', 0)} GL-only, "
                f"{recon_data.get('unmatched_external_count', 0)} external-only."
            )

        is_reconciled = recon_data.get("reconciled", False)

        return self.format_result(
            status="completed",
            output={
                "reconciliation": recon_data,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=None if is_reconciled else "human_review",
            metadata={
                "account_code": account_code,
                "reconciled": is_reconciled,
                "balance_difference": recon_data.get("balance_difference"),
            },
        )

    # ------------------------------------------------------------------
    # Close readiness evaluation
    # ------------------------------------------------------------------

    def _evaluate_close_readiness(
        self,
        journal_results: dict[str, Any],
        recon_results: dict[str, Any],
        anomaly_results: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate whether the period is ready to close.

        Checks all analysis results against policy thresholds to
        determine close readiness.

        Args:
            journal_results: Journal validation results.
            recon_results: Reconciliation results.
            anomaly_results: Anomaly detection results.
            policy: Resolved policy configuration.

        Returns:
            Dict with readiness assessment, blockers, and warnings.
        """
        close_policy = policy.get("period_close", {})
        max_open_items = close_policy.get("max_open_items_for_close", 5)

        blockers: list[str] = []
        warnings: list[str] = []
        critical_issues = 0

        # Check journal validation
        invalid_je = journal_results.get("invalid", 0)
        if invalid_je > 0:
            blockers.append(
                f"{invalid_je} invalid journal entries must be corrected."
            )
            critical_issues += invalid_je

        # Check reconciliation
        unreconciled = recon_results.get("unreconciled", 0)
        if unreconciled > 0:
            unmatched = recon_results.get("total_unmatched_items", 0)
            if unmatched > max_open_items:
                blockers.append(
                    f"{unreconciled} account(s) unreconciled with {unmatched} "
                    f"open items (max: {max_open_items})."
                )
                critical_issues += 1
            else:
                warnings.append(
                    f"{unreconciled} account(s) unreconciled but within "
                    f"open-item threshold ({unmatched} items)."
                )

        # Check anomalies
        high_severity = anomaly_results.get("high_severity_count", 0)
        if high_severity > 0:
            warnings.append(
                f"{high_severity} high-severity anomalies require investigation."
            )

        # Check critical variances
        critical_variances = anomaly_results.get("critical_count", 0)
        if critical_variances > 0:
            warnings.append(
                f"{critical_variances} critical variance(s) require investigation."
            )

        ready = len(blockers) == 0

        return {
            "ready": ready,
            "blockers": blockers,
            "warnings": warnings,
            "critical_issues": critical_issues,
            "checklist": close_policy.get("close_checklist", []),
            "summary": (
                f"Period close: {'READY' if ready else 'NOT READY'}. "
                f"{len(blockers)} blocker(s), {len(warnings)} warning(s)."
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge default policy with any overrides from the context.

        Args:
            context: Execution context potentially containing policy overrides.

        Returns:
            Merged policy configuration dict.
        """
        policy = dict(DEFAULT_POLICY)

        overrides = context.get("agent_policy", {}) or {}
        resolved = context.get("resolved_config", {}) or {}

        for section_key in DEFAULT_POLICY:
            section_override = overrides.get(section_key) or resolved.get(
                section_key
            )
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {
                    **DEFAULT_POLICY[section_key],
                    **section_override,
                }

        return policy

    # ------------------------------------------------------------------
    # Audit event builder
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict."""
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-gl-analyst",
        }
        event.update(extra)
        return event
