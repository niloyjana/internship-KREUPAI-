"""AI Payroll Analyst -- handles payroll pre-processing and validation end-to-end.

Implements the 5-step payroll processing workflow:
  1. TIMESHEET VALIDATION -- Validate attendance, overtime, and leave data
  2. TAX CALCULATION -- Compute statutory tax obligations by jurisdiction
  3. DEDUCTION PROCESSING -- Process and validate all payroll deductions
  4. VARIANCE ANALYSIS -- Compare current payroll to previous cycle and detect anomalies
  5. PAYROLL REPORT -- Generate comprehensive payroll summary report

Also handles employee payslip inquiries, exception processing,
and on-demand report generation.

Worker ID: ai-payroll-analyst
Department: HR & People Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.hr_people_ops.payroll_tools import (
    DeductionProcessorTool,
    ExceptionDetectorTool,
    PayrollReportTool,
    PayrollValidatorTool,
    TaxCalculatorTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "validation": {
        "critical_rules": [
            "duplicate_employee_payment",
            "inactive_employee_in_run",
            "missing_attendance_record",
        ],
        "warning_rules": [
            "salary_variance_above_threshold",
            "overtime_above_cap",
            "allowance_above_maximum",
        ],
        "required_fields": [
            "employee_id",
            "employee_name",
            "base_salary",
            "pay_period",
        ],
        "variance_threshold_pct": 10.0,
        "auto_approve_if_valid": False,
        "require_dual_approval_above": 50000,
    },
    "tax_brackets": {
        "region": "bahrain",
        "gosi_employee_rate": 0.07,
        "gosi_employer_rate": 0.12,
        "supported_countries": ["SA", "AE", "BH", "US", "GB"],
    },
    "overtime": {
        "cap_hours_per_month": 60,
        "standard_multiplier": 1.5,
        "holiday_multiplier": 2.0,
        "weekly_threshold_hours": 48,
        "sa_daily_limit": 2,
        "sa_weekly_limit": 12,
    },
    "deductions": {
        "types": [
            "statutory",
            "voluntary",
            "loan",
            "one_time",
            "benefit",
        ],
        "max_total_deduction_pct": 50,
        "require_authorization": True,
    },
    "anomaly_detection": {
        "salary_variance_threshold_pct": 10,
        "overtime_cap_hours": 60,
        "inactive_employee_check": True,
        "duplicate_payment_check": True,
        "max_gross_salary": 100000,
        "min_gross_salary": 1000,
        "max_retro_adjustment": 5000,
    },
    "employee_query": {
        "self_service_scope": [
            "payslip_explanation",
            "deduction_breakdown",
            "leave_deduction",
            "overtime_payment",
        ],
        "escalate_to_human": [
            "salary_dispute",
            "attendance_dispute",
            "legal_query",
        ],
    },
    "reporting": {
        "default_report_type": "full",
        "default_currency": "USD",
        "include_department_breakdown": True,
        "include_compliance_section": True,
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.7,
            "max_cost_usd": 0.5,
        },
    },
    "pii_redaction": {
        "escalate_on_detection": True,
    },
}


class PayrollAnalystAgent(BaseAgent):
    """AI Payroll Analyst -- handles payroll pre-processing and validation.

    Executes a five-step workflow for every payroll processing cycle:
      1. Validate timesheet and attendance data for completeness and accuracy
      2. Calculate statutory tax obligations by jurisdiction
      3. Process and validate all payroll deductions
      4. Perform variance analysis and anomaly detection against prior period
      5. Generate comprehensive payroll summary report

    Also supports employee payslip inquiries via ``handle_inquiry``,
    exception processing via ``process_exceptions``, and on-demand
    report generation via ``generate_report``.

    Attributes:
        _payroll_validator: Tool for validating payroll data.
        _tax_calculator: Tool for calculating tax obligations.
        _deduction_processor: Tool for processing deductions.
        _exception_detector: Tool for detecting payroll anomalies.
        _report_generator: Tool for generating payroll reports.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Payroll Analyst agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-payroll-analyst", llm_gateway, pii_redactor)
        self.name = "AI Payroll Analyst"
        self._payroll_validator = PayrollValidatorTool()
        self._tax_calculator = TaxCalculatorTool()
        self._deduction_processor = DeductionProcessorTool()
        self._exception_detector = ExceptionDetectorTool()
        self._report_generator = PayrollReportTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "payroll_input_collection",
            "data_validation",
            "anomaly_detection",
            "variance_analysis",
            "payroll_summary_preparation",
            "employee_query_handling",
            "statutory_calculation_assistance",
            "payslip_distribution_trigger",
            "exception_report_generation",
            "audit_trail_maintenance",
            "month_end_close_support",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``validate_payroll`` (default): Full 5-step payroll validation workflow
          - ``handle_inquiry``: Handle employee payslip inquiry
          - ``process_exceptions``: Detect and process payroll exceptions
          - ``generate_report``: Generate on-demand payroll report

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "validate_payroll")

        if task_type == "validate_payroll":
            return await self._validate_payroll(task_payload, context)
        elif task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "process_exceptions":
            return await self._process_exceptions(task_payload, context)
        elif task_type == "generate_report":
            return await self._generate_report(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full payroll validation workflow (5 steps)
    # ------------------------------------------------------------------

    async def _validate_payroll(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 5-step payroll validation workflow.

        Steps:
          1. Validate timesheet/attendance data for completeness and accuracy
          2. Calculate statutory tax obligations for each employee
          3. Process and validate all deductions
          4. Perform variance analysis and anomaly detection
          5. Generate comprehensive payroll report

        Args:
            task_payload: Payroll data including records, pay_period, and country.
            context: Execution context with previous_period_records, active_employees,
                     historical_records, and policy overrides.

        Returns:
            Standardized result dict with detailed validation output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0
        audit_events: list[dict[str, Any]] = []

        tenant_id = context.get("tenantId", "")
        execution_id = context.get("executionId", str(uuid.uuid4()))

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        records = task_payload.get("payroll_records", [])
        pay_period = task_payload.get("pay_period", "")
        country = task_payload.get("country", "")

        if not records:
            return self.format_result(
                "failed",
                {"error": "No payroll records provided.", "step": "input"},
                tokens_used=0,
                cost_usd=0.0,
            )

        if not pay_period:
            return self.format_result(
                "failed",
                {"error": "No pay period specified.", "step": "input"},
                tokens_used=0,
                cost_usd=0.0,
            )

        audit_events.append(self._audit_event(
            "payroll.validation.started", tenant_id, execution_id,
            pay_period=pay_period, country=country, total_records=len(records),
        ))

        # Step 1: Timesheet Validation
        validation_result = await self._step_timesheet_validation(
            records, pay_period, country, context, policy
        )

        val_data = validation_result.get("data", {})

        audit_events.append(self._audit_event(
            "payroll.validation.completed", tenant_id, execution_id,
            is_valid=val_data.get("is_valid", False),
            error_count=val_data.get("error_count", 0),
            warning_count=val_data.get("warning_count", 0),
        ))

        # Step 2: Tax Calculation
        tax_results = await self._step_tax_calculation(
            records, country, policy
        )

        audit_events.append(self._audit_event(
            "payroll.tax.calculated", tenant_id, execution_id,
            total_employees=len(tax_results),
            total_withholding=round(
                sum(t.get("total_withholding", 0) for t in tax_results), 2
            ),
            advisory_note="Statutory deduction calculations are advisory — verify with accountant",
        ))

        # Step 3: Deduction Processing
        deduction_results = await self._step_deduction_processing(
            records, country, context, policy
        )

        audit_events.append(self._audit_event(
            "payroll.deductions.processed", tenant_id, execution_id,
            total_processed=len(deduction_results),
            all_valid=not any(not d.get("is_valid", True) for d in deduction_results),
        ))

        # Step 4: Variance Analysis
        variance_data = await self._step_variance_analysis(
            records, pay_period, context, policy
        )

        if variance_data.get("total_exceptions", 0) > 0:
            audit_events.append(self._audit_event(
                "payroll.anomaly.detected", tenant_id, execution_id,
                total_exceptions=variance_data.get("total_exceptions", 0),
                by_severity=variance_data.get("by_severity", {}),
                requires_review=variance_data.get("requires_review", False),
            ))

        # Cross-check validation and exception results
        cross_check = self._cross_check_results(
            val_data, variance_data, policy
        )

        # Step 5: Generate Payroll Report
        report_result = await self._step_payroll_report(
            records, pay_period, country, policy
        )
        rpt_data = report_result.get("data", {})

        audit_events.append(self._audit_event(
            "payroll.report.generated", tenant_id, execution_id,
            report_id=rpt_data.get("report_id"),
        ))

        # Use LLM to generate an executive summary
        llm_result = await self._generate_payroll_summary(
            pay_period, records, val_data, tax_results, deduction_results,
            variance_data, cross_check, rpt_data, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Determine overall status
        is_valid = val_data.get("is_valid", False)
        has_critical = variance_data.get("requires_review", False)
        has_deduction_errors = any(
            not d.get("is_valid", True) for d in deduction_results
        )

        if has_critical:
            overall_status = "requires_review"
        elif not is_valid or has_deduction_errors:
            overall_status = "validation_failed"
        else:
            overall_status = "passed"

        # Build comprehensive output
        output: dict[str, Any] = {
            "pay_period": pay_period,
            "country": country,
            "total_records": len(records),
            "validation": {
                "is_valid": is_valid,
                "error_count": val_data.get("error_count", 0),
                "warning_count": val_data.get("warning_count", 0),
                "errors": val_data.get("errors", [])[:20],
                "warnings": val_data.get("warnings", [])[:20],
            },
            "tax_calculations": {
                "total_calculated": len(tax_results),
                "total_withholding": round(
                    sum(t.get("total_withholding", 0) for t in tax_results), 2
                ),
                "results": tax_results[:10],
            },
            "deductions": {
                "total_processed": len(deduction_results),
                "all_valid": not has_deduction_errors,
                "total_deductions": round(
                    sum(d.get("total_deductions", 0) for d in deduction_results), 2
                ),
            },
            "variance_analysis": {
                "total_exceptions": variance_data.get("total_exceptions", 0),
                "requires_review": has_critical,
                "by_severity": variance_data.get("by_severity", {}),
                "exceptions": variance_data.get("exceptions", [])[:20],
            },
            "cross_check": cross_check,
            "report": {
                "report_id": rpt_data.get("report_id"),
                "summary": rpt_data.get("summary", {}),
                "department_breakdown": rpt_data.get("department_breakdown", []),
            },
            "overall_status": overall_status,
            "executive_summary": llm_result.get("content", "Payroll validation complete."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": "Payroll never processed without explicit payroll manager approval. "
                              "Statutory calculations are advisory — verify with accountant.",
        }

        # Determine next action
        next_action: Optional[str] = None
        if overall_status == "requires_review":
            next_action = "human_review"
        elif overall_status == "validation_failed":
            next_action = "fix_and_revalidate"
        elif policy.get("validation", {}).get("auto_approve_if_valid", False):
            next_action = "approve_payroll"
        else:
            next_action = "submit_for_approval"

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "pay_period": pay_period,
                "overall_status": overall_status,
                "is_valid": is_valid,
                "exception_count": variance_data.get("total_exceptions", 0),
                "requires_review": has_critical,
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = 0.95 if is_valid else 0.60
        if has_critical:
            result["risk_level"] = "high"
        elif not is_valid:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Timesheet Validation
    # ------------------------------------------------------------------

    async def _step_timesheet_validation(
        self,
        records: list[dict[str, Any]],
        pay_period: str,
        country: str,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate timesheet, attendance, and leave data.

        Uses the PayrollValidatorTool to perform completeness,
        mathematical accuracy, statutory compliance, overtime,
        and cross-period consistency checks on payroll records.

        Args:
            records: Payroll records to validate.
            pay_period: Pay period identifier.
            country: ISO country code.
            context: Execution context with previous period records.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with validation findings.
        """
        prev_records = context.get("previous_period_records", [])
        variance_threshold = policy.get("validation", {}).get(
            "variance_threshold_pct", 10.0
        )

        result = await self._payroll_validator.execute({
            "payroll_records": records,
            "pay_period": pay_period,
            "country": country,
            "previous_period_records": prev_records,
            "variance_threshold_pct": variance_threshold,
        })

        return result

    # ------------------------------------------------------------------
    # Step 2: Tax Calculation
    # ------------------------------------------------------------------

    async def _step_tax_calculation(
        self,
        records: list[dict[str, Any]],
        country: str,
        policy: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Calculate statutory tax obligations for each employee.

        Iterates over payroll records and uses the TaxCalculatorTool
        to compute income tax and social insurance contributions
        based on employee jurisdiction and salary.

        Args:
            records: List of payroll records.
            country: Default ISO country code.
            policy: Resolved policy configuration.

        Returns:
            List of tax calculation result dicts per employee.
        """
        tax_results: list[dict[str, Any]] = []

        for record in records:
            employee_id = record.get("employee_id", record.get("id", "unknown"))
            gross_salary = float(
                record.get("gross_salary", record.get("base_salary", 0))
            )
            nationality = record.get("nationality", "")
            annual_salary = float(record.get("annual_salary", gross_salary * 12))
            ytd_gross = float(record.get("ytd_gross", 0))
            emp_country = record.get("country", country)

            result = await self._tax_calculator.execute({
                "employee_id": employee_id,
                "country": emp_country,
                "gross_salary": gross_salary,
                "annual_salary": annual_salary,
                "nationality": nationality,
                "filing_status": record.get("filing_status", "single"),
                "pay_period": "monthly",
                "ytd_gross": ytd_gross,
            })

            if result.get("success"):
                tax_results.append(result["data"])
            else:
                tax_results.append({
                    "employee_id": employee_id,
                    "error": result.get("error", "Tax calculation failed"),
                    "total_withholding": 0,
                    "is_valid": False,
                })

        return tax_results

    # ------------------------------------------------------------------
    # Step 3: Deduction Processing
    # ------------------------------------------------------------------

    async def _step_deduction_processing(
        self,
        records: list[dict[str, Any]],
        country: str,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Process and validate deductions for each employee.

        Iterates over payroll records and uses the DeductionProcessorTool
        to validate deductions against authorization records and policy
        limits for each employee.

        Args:
            records: List of payroll records with deduction data.
            country: Default ISO country code.
            context: Execution context with authorized deductions map.
            policy: Resolved policy configuration.

        Returns:
            List of deduction processing result dicts per employee.
        """
        deduction_results: list[dict[str, Any]] = []
        authorized_map = context.get("authorized_deductions", {})

        for record in records:
            employee_id = record.get("employee_id", record.get("id", "unknown"))
            gross_salary = float(
                record.get("gross_salary", record.get("base_salary", 0))
            )
            deductions_data = record.get("deductions", {})

            # Convert deductions dict to list format if needed
            deduction_items: list[dict[str, Any]] = []
            if isinstance(deductions_data, dict):
                for code, amount in deductions_data.items():
                    deduction_items.append({
                        "code": code,
                        "amount": float(amount),
                        "type": self._classify_deduction_type(code),
                        "description": code,
                    })
            elif isinstance(deductions_data, list):
                deduction_items = deductions_data

            # Get employee-specific authorized deductions
            emp_authorized = authorized_map.get(employee_id, [])

            if not deduction_items:
                deduction_results.append({
                    "employee_id": employee_id,
                    "total_deductions": 0,
                    "is_valid": True,
                    "processed_count": 0,
                })
                continue

            result = await self._deduction_processor.execute({
                "employee_id": employee_id,
                "gross_salary": gross_salary,
                "country": record.get("country", country),
                "deductions": deduction_items,
                "authorized_deductions": emp_authorized,
                "pay_period": record.get("pay_period", ""),
            })

            if result.get("success"):
                deduction_results.append(result["data"])
            else:
                deduction_results.append({
                    "employee_id": employee_id,
                    "error": result.get("error", "Deduction processing failed"),
                    "total_deductions": 0,
                    "is_valid": False,
                })

        return deduction_results

    # ------------------------------------------------------------------
    # Step 4: Variance Analysis
    # ------------------------------------------------------------------

    async def _step_variance_analysis(
        self,
        records: list[dict[str, Any]],
        pay_period: str,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform variance analysis and anomaly detection.

        Uses the ExceptionDetectorTool to compare the current payroll
        data against historical records and detect anomalies such as
        unusual amounts, duplicates, missing payments, and outliers.

        Args:
            records: Current period payroll records.
            pay_period: Current pay period identifier.
            context: Execution context with historical records and active employees.
            policy: Resolved policy configuration.

        Returns:
            Exception detection data dict.
        """
        historical = context.get("historical_records", [])
        active_employees = context.get("active_employees", [])
        anomaly_policy = policy.get("anomaly_detection", {})

        thresholds = {
            "max_gross_salary": anomaly_policy.get("max_gross_salary", 100000),
            "min_gross_salary": anomaly_policy.get("min_gross_salary", 1000),
            "max_retro_adjustment": anomaly_policy.get("max_retro_adjustment", 5000),
        }

        result = await self._exception_detector.execute({
            "payroll_records": records,
            "historical_records": historical,
            "pay_period": pay_period,
            "active_employees": active_employees,
            "thresholds": thresholds,
        })

        if result.get("success"):
            return result["data"]

        return {
            "total_exceptions": 0,
            "exceptions": [],
            "by_severity": {},
            "requires_review": False,
            "error": result.get("error", "Variance analysis failed"),
        }

    # ------------------------------------------------------------------
    # Step 5: Payroll Report
    # ------------------------------------------------------------------

    async def _step_payroll_report(
        self,
        records: list[dict[str, Any]],
        pay_period: str,
        country: str,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate the comprehensive payroll summary report.

        Uses the PayrollReportTool to produce a full report including
        totals, department breakdown, deduction summary, and compliance.

        Args:
            records: Payroll records for the period.
            pay_period: Pay period identifier.
            country: ISO country code for currency determination.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with report data.
        """
        reporting = policy.get("reporting", {})

        # Determine currency from country
        currency_map = {
            "SA": "SAR", "AE": "AED", "BH": "BHD",
            "US": "USD", "GB": "GBP",
        }
        currency = reporting.get(
            "default_currency",
            currency_map.get(country.upper(), "USD") if country else "USD",
        )

        result = await self._report_generator.execute({
            "payroll_records": records,
            "pay_period": pay_period,
            "report_type": reporting.get("default_report_type", "full"),
            "currency": currency,
        })

        return result

    # ------------------------------------------------------------------
    # Cross-check helper
    # ------------------------------------------------------------------

    def _cross_check_results(
        self,
        val_data: dict[str, Any],
        variance_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Cross-reference validation and exception findings.

        Synthesizes findings from validation and exception detection
        to produce a unified cross-check summary with hold and
        escalation decisions.

        Args:
            val_data: Validation step result data.
            variance_data: Variance analysis / exception detection data.
            policy: Resolved policy configuration.

        Returns:
            Cross-check summary dict.
        """
        validation_errors = val_data.get("error_count", 0)
        validation_warnings = val_data.get("warning_count", 0)
        exception_count = variance_data.get("total_exceptions", 0)

        # Check for overlapping employee issues
        val_emp_ids = {
            e.get("employee_id") for e in val_data.get("errors", [])
        }
        exc_emp_ids = {
            e.get("employee_id") for e in variance_data.get("exceptions", [])
        }
        overlapping = val_emp_ids & exc_emp_ids

        # Determine hold and escalation decisions
        severity_config = policy.get("anomaly_detection", {})
        hold_records: list[str] = []
        escalate_records: list[str] = []

        for exc in variance_data.get("exceptions", []):
            severity = exc.get("severity", "medium")
            emp_id = exc.get("employee_id", "")

            if severity in ("critical", "high") and emp_id:
                hold_records.append(emp_id)
            if severity == "critical" and emp_id:
                escalate_records.append(emp_id)

        # Add validation error records to hold list
        for err in val_data.get("errors", []):
            emp_id = err.get("employee_id", "")
            if emp_id and err.get("type") in ("completeness", "math_accuracy"):
                if emp_id not in hold_records:
                    hold_records.append(emp_id)

        can_process = len(hold_records) == 0 and validation_errors == 0

        return {
            "total_issues": validation_errors + validation_warnings + exception_count,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "exception_count": exception_count,
            "employees_with_multiple_issues": list(overlapping),
            "hold_records": list(set(hold_records)),
            "escalate_records": list(set(escalate_records)),
            "can_process": can_process,
            "summary": (
                f"Cross-check: {validation_errors} validation errors, "
                f"{validation_warnings} warnings, {exception_count} exceptions. "
                f"{len(set(hold_records))} records on hold, "
                f"{len(set(escalate_records))} require escalation. "
                f"{'Ready to process.' if can_process else 'Requires review.'}"
            ),
        }

    # ------------------------------------------------------------------
    # Employee Inquiry Handler
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle an employee payslip or payroll inquiry.

        Checks if the query falls within the self-service scope and
        generates an appropriate response using the LLM. Escalates
        disputes and legal queries to the HR payroll team.

        Args:
            task_payload: Inquiry details including employee_id and query text.
            context: Execution context with payslip data and policy overrides.

        Returns:
            Standardized result with response text and resolution details.
        """
        policy = self._resolve_policy(context)
        query_policy = policy.get("employee_query", {})

        tenant_id = context.get("tenantId", "")
        execution_id = context.get("executionId", str(uuid.uuid4()))

        employee_id = task_payload.get("employee_id", "")
        employee_name = task_payload.get("employee_name", "")
        query_text = task_payload.get("query", "")
        query_type = task_payload.get("query_type", "")

        # Audit: employee query received (Spec Workflow 2 Step 4)
        query_audit = [self._audit_event(
            "payroll.employee_query.received", tenant_id, execution_id,
            employee_id=employee_id,
            query_type=query_type or "general",
        )]

        # Guardrail: Employee query scope strictly limited to own payslip data (Spec Section 7)
        # The system only serves data matching the authenticated employee_id.

        # Check if escalation is required
        escalation_topics = query_policy.get("escalate_to_human", [])
        if query_type in escalation_topics:
            query_audit.append(self._audit_event(
                "payroll.employee_query.escalated", tenant_id, execution_id,
                employee_id=employee_id,
                query_type=query_type,
                reason=f"Query type '{query_type}' requires human review",
            ))
            return self.format_result(
                status="completed",
                output={
                    "response_text": (
                        f"Dear {employee_name or 'Employee'}, thank you for reaching out. "
                        f"Your inquiry regarding '{query_type}' requires attention from "
                        f"our HR payroll team. We have escalated this to a payroll specialist "
                        f"who will get back to you within 24 hours."
                    ),
                    "escalated": True,
                    "escalation_reason": f"Query type '{query_type}' requires human review.",
                    "employee_id": employee_id,
                    "query_type": query_type,
                    "audit_events": query_audit,
                },
                tokens_used=0,
                cost_usd=0.0,
                next_action="escalate_to_payroll_team",
            )

        # Retrieve payslip data from context
        payslip_data = context.get("payslip_data", {})
        recent_payslips = context.get("recent_payslips", [])
        salary_structure = context.get("salary_structure", {})

        # Also search payroll_records in context for fallback
        payroll_records: list[dict[str, Any]] = context.get("payroll_records", [])
        matched_records: list[dict[str, Any]] = []
        for record in payroll_records:
            rec_id = record.get("employee_id", record.get("id", ""))
            rec_name = (record.get("employee_name", "") or "").strip().lower()
            if (employee_id and rec_id == employee_id) or (
                employee_name and rec_name == employee_name.strip().lower()
            ):
                matched_records.append(record)

        # Build context for LLM
        payslip_context = json.dumps({
            "employee_name": employee_name,
            "employee_id": employee_id,
            "current_payslip": payslip_data or (matched_records[-1] if matched_records else {}),
            "recent_payslips": recent_payslips[:3] or matched_records[:3],
            "salary_structure": salary_structure,
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Payroll Analyst. An employee is asking about "
                    "their payslip or payroll details. Generate a professional, "
                    "clear response based on the payslip data provided. Follow "
                    "these rules:\n"
                    "- Only share information about the employee's own payslip\n"
                    "- Explain deductions clearly with amounts and percentages\n"
                    "- For salary differences, show the comparison with breakdown\n"
                    "- For statutory deductions (GOSI, tax), explain the calculation\n"
                    "- Never reveal other employees' salary information\n"
                    "- If the data is insufficient, ask for the specific pay period\n"
                    "- Be concise and use a professional tone\n"
                    "Return a JSON object with keys: 'response', 'query_resolved' "
                    "(boolean), 'breakdown' (list of items if applicable)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Employee: {employee_name or employee_id}\n"
                    f"Query: {query_text or 'General payslip inquiry'}\n\n"
                    f"Payslip Data:\n{payslip_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        response_data: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                response_data = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not response_data:
            # Fallback response
            source_data = payslip_data or (matched_records[-1] if matched_records else {})
            if source_data:
                gross = source_data.get("gross_salary", "N/A")
                net = source_data.get("net_salary", "N/A")
                deductions = source_data.get("total_deductions", "N/A")
                response_text = (
                    f"Dear {employee_name or 'Employee'}, here is a summary of "
                    f"your payslip:\n\n"
                    f"Gross Salary: {gross}\n"
                    f"Total Deductions: {deductions}\n"
                    f"Net Salary: {net}\n\n"
                    f"If you need more details about specific deductions or "
                    f"components, please specify and I'll provide a breakdown."
                )
                query_resolved = True
            else:
                response_text = (
                    f"Dear {employee_name or 'Employee'}, thank you for your inquiry. "
                    f"I was unable to locate your payslip data for the requested period. "
                    f"Please provide your employee ID and the specific pay period you "
                    f"are inquiring about."
                )
                query_resolved = False

            response_data = {
                "response": response_text,
                "query_resolved": query_resolved,
                "breakdown": [],
            }

        query_audit.append(self._audit_event(
            "payroll.employee_query.answered", tenant_id, execution_id,
            employee_id=employee_id,
            query_type=query_type or "general",
            query_resolved=response_data.get("query_resolved", False),
        ))

        return self.format_result(
            status="completed",
            output={
                "response_text": response_data.get("response", ""),
                "query_resolved": response_data.get("query_resolved", False),
                "breakdown": response_data.get("breakdown", []),
                "employee_id": employee_id,
                "query_type": query_type or "general",
                "escalated": False,
                "audit_events": query_audit,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    # ------------------------------------------------------------------
    # Exception Processing Handler
    # ------------------------------------------------------------------

    async def _process_exceptions(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Detect and categorize payroll exceptions.

        Runs the ExceptionDetectorTool on the provided payroll records
        and uses the LLM to generate a prioritized action plan with
        recommendations for each exception.

        Args:
            task_payload: Payroll data for exception analysis.
            context: Execution context with historical data and thresholds.

        Returns:
            Standardized result with categorized exceptions and recommendations.
        """
        policy = self._resolve_policy(context)
        records = task_payload.get("payroll_records", [])
        pay_period = task_payload.get("pay_period", "")

        if not records:
            return self.format_result(
                "failed",
                {"error": "No payroll records provided for exception analysis."},
                tokens_used=0,
                cost_usd=0.0,
            )

        # Run exception detection
        variance_data = await self._step_variance_analysis(
            records, pay_period, context, policy
        )

        exceptions = variance_data.get("exceptions", [])

        if not exceptions:
            return self.format_result(
                status="completed",
                output={
                    "detection_id": variance_data.get("detection_id"),
                    "pay_period": pay_period,
                    "total_exceptions": 0,
                    "message": "No exceptions detected. Payroll data appears clean.",
                    "exceptions": [],
                    "requires_review": False,
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        # Use LLM to generate an action plan
        exception_summary = json.dumps(
            [
                {
                    "type": e.get("exception_type"),
                    "employee_id": e.get("employee_id"),
                    "severity": e.get("severity"),
                    "message": e.get("message"),
                }
                for e in exceptions[:20]
            ],
            indent=2,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Payroll Analyst. Review the payroll exceptions "
                    "detected and generate a prioritized action plan. "
                    "Return a JSON object with keys:\n"
                    "- 'summary': brief overview (1-2 sentences)\n"
                    "- 'critical_actions': list of actions for critical/high exceptions\n"
                    "- 'review_items': list of items needing manager review\n"
                    "- 'auto_resolvable': list of items that can be auto-resolved\n"
                    "- 'risk_assessment': overall risk level (low/medium/high/critical)"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pay period: {pay_period}\n"
                    f"Total exceptions: {len(exceptions)}\n\n"
                    f"Exceptions:\n{exception_summary}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        action_plan: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                action_plan = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not action_plan:
            critical_count = len([
                e for e in exceptions
                if e.get("severity") in ("critical", "high")
            ])
            action_plan = {
                "summary": (
                    f"Detected {len(exceptions)} exceptions including "
                    f"{critical_count} critical/high severity items requiring "
                    f"immediate attention."
                ),
                "critical_actions": [
                    e.get("recommended_action", "Review and resolve")
                    for e in exceptions
                    if e.get("severity") in ("critical", "high")
                ],
                "review_items": [
                    e.get("message", "")
                    for e in exceptions
                    if e.get("severity") == "medium"
                ],
                "auto_resolvable": [],
                "risk_assessment": "high" if critical_count > 0 else "medium",
            }

        requires_review = variance_data.get("requires_review", False)

        result = self.format_result(
            status="completed",
            output={
                "detection_id": variance_data.get("detection_id"),
                "pay_period": pay_period,
                "total_exceptions": len(exceptions),
                "exceptions": exceptions,
                "by_severity": variance_data.get("by_severity", {}),
                "action_plan": action_plan,
                "requires_review": requires_review,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="resolve_exceptions" if requires_review else None,
            metadata={
                "total_exceptions": len(exceptions),
                "requires_review": requires_review,
                "risk_assessment": action_plan.get("risk_assessment", "medium"),
            },
        )

        result["confidence"] = 0.85
        result["risk_level"] = action_plan.get("risk_assessment", "medium")

        return result

    # ------------------------------------------------------------------
    # Report Generation Handler
    # ------------------------------------------------------------------

    async def _generate_report(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an on-demand payroll report.

        Creates a payroll report using the PayrollReportTool and
        enriches it with an LLM-generated executive narrative.

        Args:
            task_payload: Report parameters including records and type.
            context: Execution context with policy overrides.

        Returns:
            Standardized result with report data and narrative.
        """
        policy = self._resolve_policy(context)
        records = task_payload.get("payroll_records", [])
        pay_period = task_payload.get("pay_period", "")
        report_type = task_payload.get("report_type", "full")
        currency = task_payload.get("currency", "USD")

        if not records:
            return self.format_result(
                "failed",
                {"error": "No payroll records provided for report."},
                tokens_used=0,
                cost_usd=0.0,
            )

        rpt_result = await self._report_generator.execute({
            "payroll_records": records,
            "pay_period": pay_period,
            "report_type": report_type,
            "currency": currency,
        })

        if not rpt_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Report generation failed",
                    "details": rpt_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        rpt_data = rpt_result["data"]

        # Generate executive summary using LLM
        report_summary = json.dumps({
            "pay_period": pay_period,
            "total_employees": rpt_data.get("total_employees", 0),
            "summary": rpt_data.get("summary", {}),
            "department_breakdown": rpt_data.get("department_breakdown", [])[:10],
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Payroll Analyst. Generate a brief executive "
                    "summary (3-5 sentences) of the payroll report. Include key "
                    "figures: total headcount, total gross/net payroll, average salary, "
                    "and any notable department-level insights. Use a professional "
                    "tone suitable for a payroll manager."
                ),
            },
            {
                "role": "user",
                "content": f"Payroll report data:\n{report_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)
        executive_summary = llm_result.get("content", "")

        # Handle mock JSON responses
        if executive_summary.startswith("{"):
            try:
                parsed = json.loads(executive_summary)
                executive_summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not executive_summary or executive_summary.startswith("{"):
            summary_data = rpt_data.get("summary", {})
            executive_summary = (
                f"Payroll report for period {pay_period}: "
                f"{rpt_data.get('total_employees', 0)} employees, "
                f"total gross {currency} {summary_data.get('total_gross', 0):,.2f}, "
                f"total net {currency} {summary_data.get('total_net', 0):,.2f}."
            )

        return self.format_result(
            status="completed",
            output={
                "report_id": rpt_data.get("report_id"),
                "pay_period": pay_period,
                "report_type": report_type,
                "currency": currency,
                "total_employees": rpt_data.get("total_employees", 0),
                "summary": rpt_data.get("summary", {}),
                "department_breakdown": rpt_data.get("department_breakdown", []),
                "deduction_summary": rpt_data.get("deduction_summary", {}),
                "compliance": rpt_data.get("compliance", {}),
                "executive_summary": executive_summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="distribute_report",
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_payroll_summary(
        self,
        pay_period: str,
        records: list[dict[str, Any]],
        val_data: dict[str, Any],
        tax_results: list[dict[str, Any]],
        deduction_results: list[dict[str, Any]],
        variance_data: dict[str, Any],
        cross_check: dict[str, Any],
        rpt_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a human-readable payroll processing summary using the LLM.

        Args:
            pay_period: Pay period identifier.
            records: Payroll records processed.
            val_data: Validation step result data.
            tax_results: Tax calculation results.
            deduction_results: Deduction processing results.
            variance_data: Variance analysis / exception detection data.
            cross_check: Cross-check summary data.
            rpt_data: Report data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        summary_data = json.dumps({
            "pay_period": pay_period,
            "total_records": len(records),
            "validation_passed": val_data.get("is_valid", False),
            "validation_errors": val_data.get("error_count", 0),
            "validation_warnings": val_data.get("warning_count", 0),
            "tax_employees_processed": len(tax_results),
            "total_tax_withholding": round(
                sum(t.get("total_withholding", 0) for t in tax_results), 2
            ),
            "deductions_processed": len(deduction_results),
            "all_deductions_valid": all(
                d.get("is_valid", True) for d in deduction_results
            ),
            "total_exceptions": variance_data.get("total_exceptions", 0),
            "requires_review": variance_data.get("requires_review", False),
            "can_process": cross_check.get("can_process", False),
            "hold_records": len(cross_check.get("hold_records", [])),
            "total_gross": rpt_data.get("summary", {}).get("total_gross", 0),
            "total_net": rpt_data.get("summary", {}).get("total_net", 0),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Payroll Analyst. Generate a brief executive "
                    "summary (3-5 sentences) of the payroll processing results. "
                    "Include: validation status, tax calculations, deduction "
                    "processing, exceptions found, records on hold, total payroll "
                    "amount, and overall recommendation (approve/review/hold). "
                    "Be precise and professional."
                ),
            },
            {
                "role": "user",
                "content": f"Payroll processing results:\n{summary_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            is_valid = val_data.get("is_valid", False)
            errors = val_data.get("error_count", 0)
            exceptions = variance_data.get("total_exceptions", 0)
            can_process = cross_check.get("can_process", False)

            content = (
                f"Payroll processing for period {pay_period}: "
                f"{len(records)} records analyzed. "
                f"Validation {'PASSED' if is_valid else 'FAILED'} "
                f"({errors} errors, {val_data.get('warning_count', 0)} warnings). "
                f"Tax calculations completed for {len(tax_results)} employees. "
                f"{exceptions} exception(s) detected. "
            )
            if can_process:
                content += "Payroll is ready for manager approval."
            else:
                hold_count = len(cross_check.get("hold_records", []))
                content += f"{hold_count} record(s) on hold pending review."

        llm_result["content"] = content
        return llm_result

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
            section_override = overrides.get(section_key) or resolved.get(section_key)
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}

        return policy

    @staticmethod
    def _classify_deduction_type(code: str) -> str:
        """Classify a deduction code into a type category.

        Uses naming conventions to determine whether a deduction
        is statutory, voluntary, a loan repayment, a benefit, or one-time.

        Args:
            code: Deduction code string.

        Returns:
            Deduction type string.
        """
        code_lower = code.lower()

        statutory_codes = (
            "gosi", "fica", "ni_", "paye", "tax", "pension_mandatory",
            "social_ins", "social_security", "medicare",
        )
        if any(sc in code_lower for sc in statutory_codes):
            return "statutory"

        loan_codes = ("loan", "advance", "repayment")
        if any(lc in code_lower for lc in loan_codes):
            return "loan"

        benefit_codes = ("gym", "parking", "meal", "childcare", "transport")
        if any(bc in code_lower for bc in benefit_codes):
            return "benefit"

        voluntary_codes = (
            "insurance", "pension_vol", "health", "life", "dental", "vision",
        )
        if any(vc in code_lower for vc in voluntary_codes):
            return "voluntary"

        return "one_time"

    @staticmethod
    def _extract_payroll_details(
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract payroll processing details from payload and context.

        Combines payroll parameters from the task payload and
        execution context into a single configuration dict.

        Args:
            task_payload: Task payload with payroll fields.
            context: Execution context with additional payroll data.

        Returns:
            Dict with all available payroll processing details.
        """
        return {
            "pay_period": (
                task_payload.get("pay_period")
                or context.get("pay_period")
                or ""
            ),
            "country": (
                task_payload.get("country")
                or context.get("country")
                or ""
            ),
            "currency": (
                task_payload.get("currency")
                or context.get("currency")
                or "USD"
            ),
            "payroll_records": (
                task_payload.get("payroll_records")
                or context.get("payroll_records")
                or []
            ),
            "previous_period_records": (
                context.get("previous_period_records")
                or []
            ),
            "historical_records": (
                context.get("historical_records")
                or []
            ),
            "active_employees": (
                context.get("active_employees")
                or []
            ),
        }

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit-event dict.

        Args:
            event_type: Dot-delimited event type (e.g. 'payroll.validation.started').
            tenant_id: Owning tenant ID.
            execution_id: Current workflow execution ID.
            **extra: Arbitrary additional fields.

        Returns:
            Audit event dict.
        """
        return {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-payroll-analyst",
            **extra,
        }
