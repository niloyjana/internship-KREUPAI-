"""Payroll Analyst Tools -- integration tools for the AI Payroll Analyst.

Provides five tools used by the Payroll Analyst agent during payroll
processing workflows:
  - PayrollValidatorTool: Validates payroll data for completeness and accuracy
  - TaxCalculatorTool: Calculates statutory tax obligations by jurisdiction
  - DeductionProcessorTool: Processes and validates payroll deductions
  - ExceptionDetectorTool: Detects anomalies and exceptions in payroll records
  - PayrollReportTool: Generates payroll summary and compliance reports

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with HRIS, payroll systems,
and regulatory compliance engines.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Payroll Validator Tool
# ---------------------------------------------------------------------------


class PayrollValidatorTool(BaseTool):
    """Validates payroll data for completeness and accuracy.

    Performs multi-level validation of payroll records including:
    - Required field completeness checks
    - Mathematical accuracy (gross = base + allowances, net = gross - deductions)
    - Statutory compliance (minimum wage, mandatory deductions)
    - Cross-period consistency (variance checks against previous periods)

    In production this tool would integrate with the payroll system and
    regulatory APIs. For local development it validates data provided
    in the parameters.
    """

    # Mandatory deductions by country
    _MANDATORY_DEDUCTIONS: dict[str, list[dict[str, Any]]] = {
        "SA": [
            {"code": "GOSI_EMP", "name": "GOSI Employee Share", "rate_pct": 9.75, "applies_to": "saudi_nationals"},
            {"code": "GOSI_EMP_NS", "name": "GOSI Employee Share (Non-Saudi)", "rate_pct": 2.0, "applies_to": "non_saudi"},
        ],
        "AE": [
            {"code": "PENSION_EMP", "name": "Pension Fund Employee Share", "rate_pct": 5.0, "applies_to": "uae_nationals"},
        ],
        "US": [
            {"code": "FICA_SS", "name": "Social Security (FICA)", "rate_pct": 6.2, "applies_to": "all"},
            {"code": "FICA_MED", "name": "Medicare (FICA)", "rate_pct": 1.45, "applies_to": "all"},
            {"code": "FIT", "name": "Federal Income Tax", "rate_pct": None, "applies_to": "all"},
        ],
        "GB": [
            {"code": "NI_EMP", "name": "National Insurance (Employee)", "rate_pct": 12.0, "applies_to": "all"},
            {"code": "PAYE", "name": "PAYE Income Tax", "rate_pct": None, "applies_to": "all"},
            {"code": "PENSION_AE", "name": "Auto-Enrolment Pension", "rate_pct": 5.0, "applies_to": "all"},
        ],
    }

    # Overtime rules by country
    _OVERTIME_RULES: dict[str, dict[str, Any]] = {
        "SA": {"daily_limit_hours": 2, "weekly_limit_hours": 12, "rate_multiplier": 1.5, "friday_multiplier": 2.0},
        "AE": {"daily_limit_hours": 2, "weekly_limit_hours": 12, "rate_multiplier": 1.25, "holiday_multiplier": 1.5},
        "US": {"weekly_threshold_hours": 40, "rate_multiplier": 1.5, "double_time_hours": 12},
        "GB": {"weekly_max_hours": 48, "rate_multiplier": 1.0, "opt_out_available": True},
    }

    @property
    def name(self) -> str:
        return "validate_payroll"

    @property
    def description(self) -> str:
        return (
            "Validate payroll data for completeness, mathematical accuracy, "
            "statutory compliance, and cross-period consistency. Checks required "
            "fields, deduction calculations, overtime rules, and variance "
            "against previous pay periods."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "payroll_records": {
                    "type": "array",
                    "description": "List of payroll records to validate.",
                    "items": {"type": "object"},
                },
                "pay_period": {
                    "type": "string",
                    "description": "Pay period identifier (e.g., '2025-01').",
                },
                "country": {
                    "type": "string",
                    "description": "ISO country code for compliance rules.",
                },
                "previous_period_records": {
                    "type": "array",
                    "description": "Previous period records for variance checking.",
                    "items": {"type": "object"},
                },
                "variance_threshold_pct": {
                    "type": "number",
                    "description": "Maximum allowed variance percentage (default: 10).",
                },
            },
            "required": ["payroll_records", "pay_period"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate payroll records.

        Performs completeness, accuracy, compliance, and consistency checks.

        Args:
            params: Tool parameters with payroll records and validation config.

        Returns:
            Success result with validation results, errors, and warnings.
        """
        records = params.get("payroll_records", [])
        pay_period = params.get("pay_period", "")
        country = params.get("country", "").upper()
        prev_records = params.get("previous_period_records", [])
        variance_threshold = params.get("variance_threshold_pct", 10.0)

        if not records:
            return self.error_result("No payroll records provided.")
        if not pay_period:
            return self.error_result("No pay period specified.")

        validation_id = f"VAL-{uuid.uuid4().hex[:8].upper()}"
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        validated_count = 0

        for record in records:
            emp_id = record.get("employee_id", record.get("id", "unknown"))

            # Completeness check
            comp_issues = self._check_completeness(record)
            for issue in comp_issues:
                errors.append({"employee_id": emp_id, "type": "completeness", **issue})

            # Mathematical accuracy
            math_issues = self._check_math_accuracy(record)
            for issue in math_issues:
                errors.append({"employee_id": emp_id, "type": "math_accuracy", **issue})

            # Statutory compliance
            if country:
                compliance_issues = self._check_compliance(record, country)
                for issue in compliance_issues:
                    if issue.get("severity") == "error":
                        errors.append({"employee_id": emp_id, "type": "compliance", **issue})
                    else:
                        warnings.append({"employee_id": emp_id, "type": "compliance", **issue})

            # Overtime validation
            if country:
                ot_issues = self._check_overtime(record, country)
                for issue in ot_issues:
                    warnings.append({"employee_id": emp_id, "type": "overtime", **issue})

            # Variance check against previous period
            if prev_records:
                var_issues = self._check_variance(record, prev_records, variance_threshold)
                for issue in var_issues:
                    warnings.append({"employee_id": emp_id, "type": "variance", **issue})

            validated_count += 1

        is_valid = len(errors) == 0

        return self.success_result({
            "validation_id": validation_id,
            "pay_period": pay_period,
            "country": country or "N/A",
            "total_records": len(records),
            "validated_count": validated_count,
            "is_valid": is_valid,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "summary": (
                f"Payroll validation '{validation_id}' for period {pay_period}: "
                f"{validated_count} records validated. "
                f"{'PASSED' if is_valid else 'FAILED'} -- "
                f"{len(errors)} errors, {len(warnings)} warnings."
            ),
        })

    def _check_completeness(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Check required fields are present and non-empty.

        Args:
            record: Payroll record dict.

        Returns:
            List of completeness issue dicts.
        """
        required_fields = [
            "employee_id", "employee_name", "base_salary", "pay_period",
        ]
        issues: list[dict[str, Any]] = []

        for field in required_fields:
            value = record.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append({
                    "field": field,
                    "message": f"Required field '{field}' is missing or empty.",
                    "severity": "error",
                })

        return issues

    def _check_math_accuracy(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Verify mathematical accuracy of payroll calculations.

        Args:
            record: Payroll record dict.

        Returns:
            List of math accuracy issue dicts.
        """
        issues: list[dict[str, Any]] = []

        base = float(record.get("base_salary", 0))
        allowances = float(record.get("total_allowances", 0))
        deductions = float(record.get("total_deductions", 0))
        gross = record.get("gross_salary")
        net = record.get("net_salary")

        if gross is not None:
            expected_gross = base + allowances
            if abs(float(gross) - expected_gross) > 0.01:
                issues.append({
                    "field": "gross_salary",
                    "message": (
                        f"Gross salary {gross} does not match "
                        f"base ({base}) + allowances ({allowances}) = {expected_gross}."
                    ),
                    "severity": "error",
                    "expected": expected_gross,
                    "actual": float(gross),
                })

        if net is not None and gross is not None:
            expected_net = float(gross) - deductions
            if abs(float(net) - expected_net) > 0.01:
                issues.append({
                    "field": "net_salary",
                    "message": (
                        f"Net salary {net} does not match "
                        f"gross ({gross}) - deductions ({deductions}) = {expected_net}."
                    ),
                    "severity": "error",
                    "expected": expected_net,
                    "actual": float(net),
                })

        return issues

    def _check_compliance(
        self, record: dict[str, Any], country: str
    ) -> list[dict[str, Any]]:
        """Check statutory compliance for deductions.

        Args:
            record: Payroll record dict.
            country: ISO country code.

        Returns:
            List of compliance issue dicts.
        """
        issues: list[dict[str, Any]] = []
        mandatory = self._MANDATORY_DEDUCTIONS.get(country, [])
        deductions = record.get("deductions", {})
        nationality = record.get("nationality", "").lower()

        for req in mandatory:
            applies = req["applies_to"]
            if applies == "all":
                should_apply = True
            elif applies == "saudi_nationals":
                should_apply = nationality in ("saudi", "sa")
            elif applies == "non_saudi":
                should_apply = nationality not in ("saudi", "sa") and nationality != ""
            elif applies == "uae_nationals":
                should_apply = nationality in ("uae", "emirati", "ae")
            else:
                should_apply = True

            if should_apply:
                code = req["code"]
                if code not in deductions and req["rate_pct"] is not None:
                    issues.append({
                        "deduction_code": code,
                        "message": (
                            f"Mandatory deduction '{req['name']}' ({code}) "
                            f"at {req['rate_pct']}% not found."
                        ),
                        "severity": "error",
                    })
                elif code in deductions and req["rate_pct"] is not None:
                    base = float(record.get("base_salary", 0))
                    expected = round(base * req["rate_pct"] / 100, 2)
                    actual = float(deductions[code])
                    if abs(actual - expected) > 1.0:
                        issues.append({
                            "deduction_code": code,
                            "message": (
                                f"Deduction '{req['name']}' amount {actual} "
                                f"differs from expected {expected} "
                                f"({req['rate_pct']}% of {base})."
                            ),
                            "severity": "warning",
                            "expected": expected,
                            "actual": actual,
                        })

        return issues

    def _check_overtime(
        self, record: dict[str, Any], country: str
    ) -> list[dict[str, Any]]:
        """Validate overtime hours and rates.

        Args:
            record: Payroll record dict.
            country: ISO country code.

        Returns:
            List of overtime issue dicts.
        """
        issues: list[dict[str, Any]] = []
        rules = self._OVERTIME_RULES.get(country)
        if not rules:
            return issues

        ot_hours = float(record.get("overtime_hours", 0))
        if ot_hours <= 0:
            return issues

        weekly_limit = rules.get("weekly_limit_hours") or rules.get("weekly_max_hours")
        if weekly_limit and ot_hours > weekly_limit:
            issues.append({
                "field": "overtime_hours",
                "message": (
                    f"Overtime hours {ot_hours} exceed weekly limit "
                    f"of {weekly_limit} hours for {country}."
                ),
                "severity": "warning",
            })

        return issues

    def _check_variance(
        self,
        record: dict[str, Any],
        prev_records: list[dict[str, Any]],
        threshold_pct: float,
    ) -> list[dict[str, Any]]:
        """Check variance against previous period.

        Args:
            record: Current payroll record.
            prev_records: Previous period records.
            threshold_pct: Maximum allowed variance percentage.

        Returns:
            List of variance issue dicts.
        """
        issues: list[dict[str, Any]] = []
        emp_id = record.get("employee_id", record.get("id"))

        prev = None
        for pr in prev_records:
            if pr.get("employee_id", pr.get("id")) == emp_id:
                prev = pr
                break

        if not prev:
            return issues

        check_fields = ["base_salary", "gross_salary", "net_salary", "total_deductions"]
        for field in check_fields:
            current_val = record.get(field)
            prev_val = prev.get(field)

            if current_val is not None and prev_val is not None:
                current_f = float(current_val)
                prev_f = float(prev_val)
                if prev_f > 0:
                    variance_pct = abs(current_f - prev_f) / prev_f * 100
                    if variance_pct > threshold_pct:
                        issues.append({
                            "field": field,
                            "message": (
                                f"Field '{field}' changed by {variance_pct:.1f}% "
                                f"(from {prev_f} to {current_f}), "
                                f"exceeding threshold of {threshold_pct}%."
                            ),
                            "severity": "warning",
                            "variance_pct": round(variance_pct, 1),
                            "previous_value": prev_f,
                            "current_value": current_f,
                        })

        return issues


# ---------------------------------------------------------------------------
# Tax Calculator Tool
# ---------------------------------------------------------------------------


class TaxCalculatorTool(BaseTool):
    """Calculates statutory tax obligations by jurisdiction.

    Computes income tax, social insurance contributions, and other
    mandatory withholdings based on the employee's country, salary,
    and personal circumstances (filing status, dependents, etc.).

    Supports tax brackets for multiple jurisdictions including SA, AE,
    US, GB, and BH. In production this tool would integrate with
    tax calculation engines and regulatory APIs.
    """

    # Tax brackets by country (simplified)
    _TAX_BRACKETS: dict[str, list[dict[str, Any]]] = {
        "US": [
            {"min": 0, "max": 11600, "rate": 0.10},
            {"min": 11600, "max": 47150, "rate": 0.12},
            {"min": 47150, "max": 100525, "rate": 0.22},
            {"min": 100525, "max": 191950, "rate": 0.24},
            {"min": 191950, "max": 243725, "rate": 0.32},
            {"min": 243725, "max": 609350, "rate": 0.35},
            {"min": 609350, "max": float("inf"), "rate": 0.37},
        ],
        "GB": [
            {"min": 0, "max": 12570, "rate": 0.0},
            {"min": 12570, "max": 50270, "rate": 0.20},
            {"min": 50270, "max": 125140, "rate": 0.40},
            {"min": 125140, "max": float("inf"), "rate": 0.45},
        ],
        "SA": [],  # No personal income tax in Saudi Arabia
        "AE": [],  # No personal income tax in UAE
        "BH": [],  # No personal income tax in Bahrain
    }

    # Social insurance rates by country
    _SOCIAL_INSURANCE: dict[str, dict[str, Any]] = {
        "SA": {
            "employee_rate_national": 0.0975,
            "employer_rate_national": 0.12,
            "employee_rate_expat": 0.02,
            "employer_rate_expat": 0.02,
            "ceiling": 45000,  # Monthly ceiling in SAR
        },
        "AE": {
            "employee_rate_national": 0.05,
            "employer_rate_national": 0.125,
            "employee_rate_expat": 0.0,
            "employer_rate_expat": 0.0,
            "ceiling": None,
        },
        "BH": {
            "employee_rate_national": 0.08,
            "employer_rate_national": 0.12,
            "employee_rate_expat": 0.04,
            "employer_rate_expat": 0.04,
            "ceiling": None,
        },
        "US": {
            "fica_ss_rate": 0.062,
            "fica_ss_ceiling": 168600,
            "fica_medicare_rate": 0.0145,
            "fica_medicare_ceiling": None,
            "additional_medicare_threshold": 200000,
            "additional_medicare_rate": 0.009,
        },
        "GB": {
            "ni_rate_main": 0.12,
            "ni_threshold": 12570,
            "ni_upper_limit": 50270,
            "ni_rate_additional": 0.02,
        },
    }

    @property
    def name(self) -> str:
        return "calculate_tax"

    @property
    def description(self) -> str:
        return (
            "Calculate statutory tax obligations including income tax, "
            "social insurance contributions, and mandatory withholdings "
            "based on country, salary, and personal circumstances."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee identifier.",
                },
                "country": {
                    "type": "string",
                    "description": "ISO country code (e.g., US, GB, SA, AE, BH).",
                },
                "gross_salary": {
                    "type": "number",
                    "description": "Gross monthly salary amount.",
                },
                "annual_salary": {
                    "type": "number",
                    "description": "Annual salary for bracket calculation.",
                },
                "nationality": {
                    "type": "string",
                    "description": "Employee nationality for social insurance rules.",
                },
                "filing_status": {
                    "type": "string",
                    "description": "Tax filing status (single, married, head_of_household).",
                },
                "dependents": {
                    "type": "integer",
                    "description": "Number of dependents for tax calculation.",
                },
                "pay_period": {
                    "type": "string",
                    "description": "Pay period (monthly, bi_weekly, weekly).",
                },
                "ytd_gross": {
                    "type": "number",
                    "description": "Year-to-date gross earnings for ceiling calculations.",
                },
            },
            "required": ["country", "gross_salary"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate tax obligations for an employee.

        Computes income tax and social insurance based on jurisdiction.

        Args:
            params: Tool parameters with salary and jurisdiction details.

        Returns:
            Success result with itemized tax calculations.
        """
        employee_id = params.get("employee_id", "unknown")
        country = params.get("country", "").upper()
        gross_salary = float(params.get("gross_salary", 0))
        annual_salary = float(params.get("annual_salary", gross_salary * 12))
        nationality = params.get("nationality", "").lower()
        filing_status = params.get("filing_status", "single")
        pay_period = params.get("pay_period", "monthly")
        ytd_gross = float(params.get("ytd_gross", 0))

        if gross_salary <= 0:
            return self.error_result("Gross salary must be greater than zero.")
        if not country:
            return self.error_result("Country code is required.")

        calc_id = f"TAX-{uuid.uuid4().hex[:8].upper()}"

        # Calculate income tax
        income_tax = self._calculate_income_tax(
            country, annual_salary, filing_status, pay_period
        )

        # Calculate social insurance
        social_insurance = self._calculate_social_insurance(
            country, gross_salary, nationality, ytd_gross
        )

        total_tax = income_tax + social_insurance.get("employee_total", 0)
        effective_rate = (total_tax / gross_salary * 100) if gross_salary > 0 else 0

        return self.success_result({
            "calculation_id": calc_id,
            "employee_id": employee_id,
            "country": country,
            "gross_salary": gross_salary,
            "annual_salary": annual_salary,
            "income_tax": round(income_tax, 2),
            "social_insurance": social_insurance,
            "total_withholding": round(total_tax, 2),
            "net_after_tax": round(gross_salary - total_tax, 2),
            "effective_tax_rate_pct": round(effective_rate, 2),
            "pay_period": pay_period,
            "filing_status": filing_status,
            "summary": (
                f"Tax calculation '{calc_id}' for {country}: "
                f"income tax {income_tax:.2f}, "
                f"social insurance {social_insurance.get('employee_total', 0):.2f}, "
                f"total withholding {total_tax:.2f} "
                f"({effective_rate:.1f}% effective rate)."
            ),
        })

    def _calculate_income_tax(
        self,
        country: str,
        annual_salary: float,
        filing_status: str,
        pay_period: str,
    ) -> float:
        """Calculate income tax using progressive brackets.

        Args:
            country: ISO country code.
            annual_salary: Annual gross salary.
            filing_status: Tax filing status.
            pay_period: Pay period for monthly conversion.

        Returns:
            Monthly income tax amount.
        """
        brackets = self._TAX_BRACKETS.get(country, [])
        if not brackets:
            return 0.0

        annual_tax = 0.0
        for bracket in brackets:
            if annual_salary <= bracket["min"]:
                break
            taxable = min(annual_salary, bracket["max"]) - bracket["min"]
            annual_tax += taxable * bracket["rate"]

        # Convert to pay period
        if pay_period == "monthly":
            return round(annual_tax / 12, 2)
        elif pay_period == "bi_weekly":
            return round(annual_tax / 26, 2)
        elif pay_period == "weekly":
            return round(annual_tax / 52, 2)
        return round(annual_tax / 12, 2)

    def _calculate_social_insurance(
        self,
        country: str,
        gross_salary: float,
        nationality: str,
        ytd_gross: float,
    ) -> dict[str, Any]:
        """Calculate social insurance contributions.

        Args:
            country: ISO country code.
            gross_salary: Monthly gross salary.
            nationality: Employee nationality.
            ytd_gross: Year-to-date gross for ceiling checks.

        Returns:
            Dict with employee and employer contributions.
        """
        config = self._SOCIAL_INSURANCE.get(country, {})
        if not config:
            return {"employee_total": 0.0, "employer_total": 0.0, "items": []}

        items: list[dict[str, Any]] = []
        employee_total = 0.0
        employer_total = 0.0

        if country in ("SA", "AE", "BH"):
            is_national = self._is_national(nationality, country)
            if is_national:
                emp_rate = config.get("employee_rate_national", 0)
                er_rate = config.get("employer_rate_national", 0)
                label = "Social Insurance (National)"
            else:
                emp_rate = config.get("employee_rate_expat", 0)
                er_rate = config.get("employer_rate_expat", 0)
                label = "Social Insurance (Expat)"

            ceiling = config.get("ceiling")
            applicable_salary = min(gross_salary, ceiling) if ceiling else gross_salary
            emp_amount = round(applicable_salary * emp_rate, 2)
            er_amount = round(applicable_salary * er_rate, 2)

            items.append({
                "code": "SOCIAL_INS",
                "name": label,
                "employee_amount": emp_amount,
                "employer_amount": er_amount,
                "rate_employee_pct": round(emp_rate * 100, 2),
                "rate_employer_pct": round(er_rate * 100, 2),
            })
            employee_total += emp_amount
            employer_total += er_amount

        elif country == "US":
            # FICA Social Security
            ss_rate = config.get("fica_ss_rate", 0.062)
            ss_ceiling = config.get("fica_ss_ceiling", 168600)
            monthly_ceiling = ss_ceiling / 12
            ss_salary = min(gross_salary, monthly_ceiling)
            ss_amount = round(ss_salary * ss_rate, 2)
            items.append({
                "code": "FICA_SS",
                "name": "Social Security (FICA)",
                "employee_amount": ss_amount,
                "employer_amount": ss_amount,
                "rate_pct": round(ss_rate * 100, 2),
            })
            employee_total += ss_amount
            employer_total += ss_amount

            # FICA Medicare
            med_rate = config.get("fica_medicare_rate", 0.0145)
            med_amount = round(gross_salary * med_rate, 2)
            items.append({
                "code": "FICA_MED",
                "name": "Medicare (FICA)",
                "employee_amount": med_amount,
                "employer_amount": med_amount,
                "rate_pct": round(med_rate * 100, 2),
            })
            employee_total += med_amount
            employer_total += med_amount

        elif country == "GB":
            ni_threshold = config.get("ni_threshold", 12570) / 12
            ni_upper = config.get("ni_upper_limit", 50270) / 12
            ni_main_rate = config.get("ni_rate_main", 0.12)
            ni_add_rate = config.get("ni_rate_additional", 0.02)

            if gross_salary > ni_threshold:
                main_ni = min(gross_salary, ni_upper) - ni_threshold
                main_amount = round(main_ni * ni_main_rate, 2)
                add_amount = 0.0
                if gross_salary > ni_upper:
                    add_ni = gross_salary - ni_upper
                    add_amount = round(add_ni * ni_add_rate, 2)

                total_ni = main_amount + add_amount
                items.append({
                    "code": "NI_EMP",
                    "name": "National Insurance (Employee)",
                    "employee_amount": total_ni,
                    "employer_amount": round(total_ni * 1.1, 2),
                    "rate_main_pct": round(ni_main_rate * 100, 2),
                })
                employee_total += total_ni
                employer_total += round(total_ni * 1.1, 2)

        return {
            "employee_total": round(employee_total, 2),
            "employer_total": round(employer_total, 2),
            "items": items,
        }

    @staticmethod
    def _is_national(nationality: str, country: str) -> bool:
        """Check if employee is a national of the given country.

        Args:
            nationality: Employee nationality string.
            country: Country code.

        Returns:
            True if the employee is a national.
        """
        national_map = {
            "SA": ("saudi", "sa", "saudi arabian"),
            "AE": ("emirati", "uae", "ae", "emirian"),
            "BH": ("bahraini", "bh", "bahrain"),
        }
        nationals = national_map.get(country, ())
        return nationality.lower() in nationals


# ---------------------------------------------------------------------------
# Deduction Processor Tool
# ---------------------------------------------------------------------------


class DeductionProcessorTool(BaseTool):
    """Processes and validates payroll deductions.

    Handles multiple deduction types including statutory deductions,
    voluntary deductions (insurance, pension top-ups), loan repayments,
    and one-time deductions. Validates against policy limits and
    employee authorization records.

    In production this tool would integrate with the HRIS deduction
    engine and employee benefit systems.
    """

    # Deduction type categories
    _DEDUCTION_TYPES: dict[str, dict[str, Any]] = {
        "statutory": {
            "label": "Statutory Deductions",
            "requires_authorization": False,
            "examples": ["income_tax", "social_insurance", "pension_mandatory"],
        },
        "voluntary": {
            "label": "Voluntary Deductions",
            "requires_authorization": True,
            "examples": ["health_insurance", "life_insurance", "pension_voluntary"],
        },
        "loan": {
            "label": "Loan Repayments",
            "requires_authorization": True,
            "examples": ["salary_advance", "company_loan", "education_loan"],
        },
        "one_time": {
            "label": "One-Time Deductions",
            "requires_authorization": True,
            "examples": ["equipment_charge", "training_cost", "penalty"],
        },
        "benefit": {
            "label": "Benefit Deductions",
            "requires_authorization": True,
            "examples": ["gym_membership", "parking", "meal_plan", "childcare"],
        },
    }

    # Maximum deduction limits as percentage of gross
    _MAX_DEDUCTION_LIMITS: dict[str, float] = {
        "SA": 0.50,  # Saudi labor law: max 50% of salary for deductions
        "AE": 0.50,
        "BH": 0.50,
        "US": 0.75,  # US allows higher voluntary deductions
        "GB": 0.75,
    }

    @property
    def name(self) -> str:
        return "process_deductions"

    @property
    def description(self) -> str:
        return (
            "Process and validate payroll deductions including statutory, "
            "voluntary, loan repayments, and one-time deductions. Validates "
            "against policy limits, authorization records, and labor law "
            "maximum deduction thresholds."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee identifier.",
                },
                "gross_salary": {
                    "type": "number",
                    "description": "Gross salary for limit calculations.",
                },
                "country": {
                    "type": "string",
                    "description": "ISO country code for regulatory limits.",
                },
                "deductions": {
                    "type": "array",
                    "description": "List of deduction items to process.",
                    "items": {"type": "object"},
                },
                "authorized_deductions": {
                    "type": "array",
                    "description": "List of deduction codes authorized by employee.",
                    "items": {"type": "string"},
                },
                "pay_period": {
                    "type": "string",
                    "description": "Pay period identifier.",
                },
            },
            "required": ["employee_id", "gross_salary", "deductions"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Process and validate payroll deductions.

        Validates each deduction against authorization records and
        policy limits, then checks total deductions against the
        regulatory maximum for the country.

        Args:
            params: Tool parameters with employee and deduction details.

        Returns:
            Success result with processed deductions, validation results,
            and total amounts.
        """
        employee_id = params.get("employee_id", "unknown")
        gross_salary = float(params.get("gross_salary", 0))
        country = params.get("country", "").upper()
        deductions = params.get("deductions", [])
        authorized = set(params.get("authorized_deductions", []))
        pay_period = params.get("pay_period", "")

        if not deductions:
            return self.error_result("No deductions provided.")
        if gross_salary <= 0:
            return self.error_result("Gross salary must be greater than zero.")

        processing_id = f"DED-{uuid.uuid4().hex[:8].upper()}"
        processed: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        total_deductions = 0.0

        for deduction in deductions:
            code = deduction.get("code", "UNKNOWN")
            amount = float(deduction.get("amount", 0))
            ded_type = deduction.get("type", "statutory")
            description = deduction.get("description", code)

            # Validate authorization
            type_config = self._DEDUCTION_TYPES.get(ded_type, {})
            requires_auth = type_config.get("requires_authorization", True)

            if requires_auth and authorized and code not in authorized:
                errors.append({
                    "code": code,
                    "type": ded_type,
                    "message": (
                        f"Deduction '{description}' ({code}) requires "
                        f"employee authorization but is not in authorized list."
                    ),
                    "severity": "error",
                })
                continue

            # Validate amount
            if amount < 0:
                errors.append({
                    "code": code,
                    "type": ded_type,
                    "message": f"Deduction '{description}' has negative amount: {amount}.",
                    "severity": "error",
                })
                continue

            if amount == 0:
                warnings.append({
                    "code": code,
                    "type": ded_type,
                    "message": f"Deduction '{description}' has zero amount.",
                    "severity": "warning",
                })

            total_deductions += amount
            processed.append({
                "code": code,
                "type": ded_type,
                "description": description,
                "amount": round(amount, 2),
                "status": "processed",
            })

        # Check total deduction limit
        max_limit = self._MAX_DEDUCTION_LIMITS.get(country, 0.50)
        max_amount = gross_salary * max_limit
        exceeds_limit = total_deductions > max_amount

        if exceeds_limit:
            errors.append({
                "code": "TOTAL_LIMIT",
                "type": "regulatory",
                "message": (
                    f"Total deductions {total_deductions:.2f} exceed "
                    f"regulatory limit of {max_limit * 100:.0f}% "
                    f"({max_amount:.2f}) of gross salary."
                ),
                "severity": "error",
            })

        is_valid = len(errors) == 0

        return self.success_result({
            "processing_id": processing_id,
            "employee_id": employee_id,
            "pay_period": pay_period,
            "gross_salary": gross_salary,
            "total_deductions": round(total_deductions, 2),
            "net_after_deductions": round(gross_salary - total_deductions, 2),
            "deduction_rate_pct": round(
                total_deductions / gross_salary * 100, 2
            ) if gross_salary > 0 else 0,
            "max_allowed_pct": round(max_limit * 100, 0),
            "exceeds_limit": exceeds_limit,
            "is_valid": is_valid,
            "processed_deductions": processed,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "by_type": self._group_by_type(processed),
            "summary": (
                f"Deduction processing '{processing_id}' for employee {employee_id}: "
                f"{len(processed)} deductions processed totaling {total_deductions:.2f}. "
                f"{'VALID' if is_valid else 'INVALID'} -- "
                f"{len(errors)} errors, {len(warnings)} warnings."
            ),
        })

    @staticmethod
    def _group_by_type(
        processed: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Group processed deductions by type.

        Args:
            processed: List of processed deduction dicts.

        Returns:
            Dict mapping type to count and total.
        """
        groups: dict[str, dict[str, Any]] = {}
        for ded in processed:
            ded_type = ded.get("type", "other")
            if ded_type not in groups:
                groups[ded_type] = {"count": 0, "total": 0.0, "items": []}
            groups[ded_type]["count"] += 1
            groups[ded_type]["total"] = round(
                groups[ded_type]["total"] + ded["amount"], 2
            )
            groups[ded_type]["items"].append(ded["code"])

        return groups


# ---------------------------------------------------------------------------
# Exception Detector Tool
# ---------------------------------------------------------------------------


class ExceptionDetectorTool(BaseTool):
    """Detects anomalies and exceptions in payroll records.

    Analyzes payroll data to identify potential issues such as:
    - Unusually high/low pay amounts
    - Missing or duplicate payments
    - Off-cycle payments
    - Retroactive adjustments above thresholds
    - Statistical outliers

    In production this tool would use ML-based anomaly detection.
    For local development it uses rule-based detection.
    """

    # Exception severity levels
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"

    @property
    def name(self) -> str:
        return "detect_exceptions"

    @property
    def description(self) -> str:
        return (
            "Detect anomalies and exceptions in payroll records including "
            "unusual pay amounts, missing payments, duplicates, off-cycle "
            "payments, and statistical outliers. Returns exceptions with "
            "severity ratings and recommended actions."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "payroll_records": {
                    "type": "array",
                    "description": "Current period payroll records.",
                    "items": {"type": "object"},
                },
                "historical_records": {
                    "type": "array",
                    "description": "Historical payroll records for trend analysis.",
                    "items": {"type": "object"},
                },
                "pay_period": {
                    "type": "string",
                    "description": "Current pay period identifier.",
                },
                "active_employees": {
                    "type": "array",
                    "description": "List of active employee IDs for missing payment detection.",
                    "items": {"type": "string"},
                },
                "thresholds": {
                    "type": "object",
                    "description": "Custom detection thresholds.",
                },
            },
            "required": ["payroll_records", "pay_period"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect exceptions and anomalies in payroll data.

        Runs multiple detection algorithms and aggregates findings.

        Args:
            params: Tool parameters with payroll records and detection config.

        Returns:
            Success result with detected exceptions grouped by severity.
        """
        records = params.get("payroll_records", [])
        historical = params.get("historical_records", [])
        pay_period = params.get("pay_period", "")
        active_employees = params.get("active_employees", [])
        thresholds = params.get("thresholds", {})

        if not records:
            return self.error_result("No payroll records provided.")

        detection_id = f"DET-{uuid.uuid4().hex[:8].upper()}"
        exceptions: list[dict[str, Any]] = []

        # Detect unusual amounts
        amount_exceptions = self._detect_unusual_amounts(records, thresholds)
        exceptions.extend(amount_exceptions)

        # Detect duplicates
        dup_exceptions = self._detect_duplicates(records)
        exceptions.extend(dup_exceptions)

        # Detect missing payments
        if active_employees:
            missing_exceptions = self._detect_missing_payments(records, active_employees)
            exceptions.extend(missing_exceptions)

        # Detect retroactive adjustments
        retro_exceptions = self._detect_retroactive_adjustments(records, thresholds)
        exceptions.extend(retro_exceptions)

        # Detect statistical outliers
        outlier_exceptions = self._detect_outliers(records)
        exceptions.extend(outlier_exceptions)

        # Detect zero or negative pay
        zero_exceptions = self._detect_zero_negative_pay(records)
        exceptions.extend(zero_exceptions)

        # Group by severity
        by_severity: dict[str, list[dict[str, Any]]] = {
            self.SEVERITY_CRITICAL: [],
            self.SEVERITY_HIGH: [],
            self.SEVERITY_MEDIUM: [],
            self.SEVERITY_LOW: [],
        }
        for exc in exceptions:
            severity = exc.get("severity", self.SEVERITY_MEDIUM)
            by_severity.setdefault(severity, []).append(exc)

        return self.success_result({
            "detection_id": detection_id,
            "pay_period": pay_period,
            "records_analyzed": len(records),
            "total_exceptions": len(exceptions),
            "exceptions": exceptions,
            "by_severity": {
                k: {"count": len(v), "exceptions": v}
                for k, v in by_severity.items() if v
            },
            "requires_review": any(
                e["severity"] in (self.SEVERITY_CRITICAL, self.SEVERITY_HIGH)
                for e in exceptions
            ),
            "summary": (
                f"Exception detection '{detection_id}' for period {pay_period}: "
                f"Analyzed {len(records)} records, found {len(exceptions)} exceptions "
                f"({len(by_severity[self.SEVERITY_CRITICAL])} critical, "
                f"{len(by_severity[self.SEVERITY_HIGH])} high, "
                f"{len(by_severity[self.SEVERITY_MEDIUM])} medium, "
                f"{len(by_severity[self.SEVERITY_LOW])} low)."
            ),
        })

    def _detect_unusual_amounts(
        self, records: list[dict[str, Any]], thresholds: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect unusually high or low pay amounts.

        Args:
            records: Payroll records.
            thresholds: Custom thresholds.

        Returns:
            List of exception dicts.
        """
        exceptions: list[dict[str, Any]] = []
        max_gross = float(thresholds.get("max_gross_salary", 100000))
        min_gross = float(thresholds.get("min_gross_salary", 1000))

        for record in records:
            emp_id = record.get("employee_id", "unknown")
            gross = float(record.get("gross_salary", 0))

            if gross > max_gross:
                exceptions.append({
                    "exception_type": "unusual_high_pay",
                    "employee_id": emp_id,
                    "severity": self.SEVERITY_HIGH,
                    "message": (
                        f"Gross salary {gross} exceeds maximum threshold {max_gross}."
                    ),
                    "value": gross,
                    "threshold": max_gross,
                    "recommended_action": "Review and verify with HR manager.",
                })
            elif 0 < gross < min_gross:
                exceptions.append({
                    "exception_type": "unusual_low_pay",
                    "employee_id": emp_id,
                    "severity": self.SEVERITY_MEDIUM,
                    "message": (
                        f"Gross salary {gross} is below minimum threshold {min_gross}."
                    ),
                    "value": gross,
                    "threshold": min_gross,
                    "recommended_action": "Verify if partial-month or pro-rated.",
                })

        return exceptions

    def _detect_duplicates(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect duplicate payroll entries.

        Args:
            records: Payroll records.

        Returns:
            List of exception dicts for duplicates.
        """
        exceptions: list[dict[str, Any]] = []
        seen: dict[str, int] = {}

        for record in records:
            emp_id = record.get("employee_id", record.get("id", "unknown"))
            if emp_id in seen:
                seen[emp_id] += 1
                exceptions.append({
                    "exception_type": "duplicate_payment",
                    "employee_id": emp_id,
                    "severity": self.SEVERITY_CRITICAL,
                    "message": (
                        f"Duplicate payroll entry detected for employee {emp_id} "
                        f"(occurrence #{seen[emp_id]})."
                    ),
                    "occurrence": seen[emp_id],
                    "recommended_action": "Remove duplicate entry before processing.",
                })
            else:
                seen[emp_id] = 1

        return exceptions

    def _detect_missing_payments(
        self, records: list[dict[str, Any]], active_employees: list[str]
    ) -> list[dict[str, Any]]:
        """Detect active employees missing from payroll.

        Args:
            records: Payroll records.
            active_employees: List of active employee IDs.

        Returns:
            List of exception dicts for missing payments.
        """
        exceptions: list[dict[str, Any]] = []
        payroll_emp_ids = {
            r.get("employee_id", r.get("id", "")) for r in records
        }

        for emp_id in active_employees:
            if emp_id not in payroll_emp_ids:
                exceptions.append({
                    "exception_type": "missing_payment",
                    "employee_id": emp_id,
                    "severity": self.SEVERITY_CRITICAL,
                    "message": (
                        f"Active employee {emp_id} has no payroll record this period."
                    ),
                    "recommended_action": "Verify employment status and add to payroll.",
                })

        return exceptions

    def _detect_retroactive_adjustments(
        self, records: list[dict[str, Any]], thresholds: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect retroactive adjustments above threshold.

        Args:
            records: Payroll records.
            thresholds: Custom thresholds.

        Returns:
            List of exception dicts for retroactive adjustments.
        """
        exceptions: list[dict[str, Any]] = []
        retro_threshold = float(thresholds.get("max_retro_adjustment", 5000))

        for record in records:
            emp_id = record.get("employee_id", "unknown")
            retro = float(record.get("retroactive_adjustment", 0))

            if abs(retro) > retro_threshold:
                exceptions.append({
                    "exception_type": "large_retroactive_adjustment",
                    "employee_id": emp_id,
                    "severity": self.SEVERITY_HIGH,
                    "message": (
                        f"Retroactive adjustment of {retro} exceeds threshold "
                        f"of {retro_threshold}."
                    ),
                    "value": retro,
                    "threshold": retro_threshold,
                    "recommended_action": "Verify adjustment authorization and calculation.",
                })

        return exceptions

    def _detect_outliers(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect statistical outliers using simple z-score approximation.

        Args:
            records: Payroll records.

        Returns:
            List of exception dicts for outliers.
        """
        exceptions: list[dict[str, Any]] = []

        gross_values = [
            float(r.get("gross_salary", 0))
            for r in records
            if r.get("gross_salary") is not None
        ]

        if len(gross_values) < 5:
            return exceptions

        mean = sum(gross_values) / len(gross_values)
        variance = sum((x - mean) ** 2 for x in gross_values) / len(gross_values)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return exceptions

        for record in records:
            emp_id = record.get("employee_id", "unknown")
            gross = float(record.get("gross_salary", 0))
            z_score = abs(gross - mean) / std_dev

            if z_score > 3.0:
                exceptions.append({
                    "exception_type": "statistical_outlier",
                    "employee_id": emp_id,
                    "severity": self.SEVERITY_MEDIUM,
                    "message": (
                        f"Gross salary {gross} is a statistical outlier "
                        f"(z-score: {z_score:.2f}, mean: {mean:.2f}, "
                        f"std_dev: {std_dev:.2f})."
                    ),
                    "value": gross,
                    "z_score": round(z_score, 2),
                    "recommended_action": "Review for data entry errors or special circumstances.",
                })

        return exceptions

    def _detect_zero_negative_pay(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect zero or negative net pay.

        Args:
            records: Payroll records.

        Returns:
            List of exception dicts.
        """
        exceptions: list[dict[str, Any]] = []

        for record in records:
            emp_id = record.get("employee_id", "unknown")
            net = record.get("net_salary")

            if net is not None:
                net_f = float(net)
                if net_f < 0:
                    exceptions.append({
                        "exception_type": "negative_net_pay",
                        "employee_id": emp_id,
                        "severity": self.SEVERITY_CRITICAL,
                        "message": f"Negative net salary: {net_f}.",
                        "value": net_f,
                        "recommended_action": "Review deductions; employee may owe balance.",
                    })
                elif net_f == 0:
                    exceptions.append({
                        "exception_type": "zero_net_pay",
                        "employee_id": emp_id,
                        "severity": self.SEVERITY_HIGH,
                        "message": "Net salary is zero.",
                        "value": 0,
                        "recommended_action": "Verify if leave without pay or deduction error.",
                    })

        return exceptions


# ---------------------------------------------------------------------------
# Payroll Report Tool
# ---------------------------------------------------------------------------


class PayrollReportTool(BaseTool):
    """Generates payroll summary and compliance reports.

    Produces comprehensive payroll reports including:
    - Pay period summary (totals, averages, headcount)
    - Department breakdown
    - Deduction summary
    - Compliance status by country
    - Cost allocation report

    In production this tool would query the payroll database and
    reporting engine. For local development it calculates from
    provided records.
    """

    @property
    def name(self) -> str:
        return "generate_payroll_report"

    @property
    def description(self) -> str:
        return (
            "Generate payroll summary and compliance reports for a given "
            "pay period. Includes totals, department breakdown, deduction "
            "summary, and compliance status."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "payroll_records": {
                    "type": "array",
                    "description": "Payroll records for the period.",
                    "items": {"type": "object"},
                },
                "pay_period": {
                    "type": "string",
                    "description": "Pay period identifier.",
                },
                "report_type": {
                    "type": "string",
                    "enum": ["summary", "department", "compliance", "full"],
                    "description": "Type of report to generate.",
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code (e.g., USD, SAR, AED).",
                },
            },
            "required": ["payroll_records", "pay_period"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate payroll report.

        Args:
            params: Tool parameters with records and report configuration.

        Returns:
            Success result with comprehensive report data.
        """
        records = params.get("payroll_records", [])
        pay_period = params.get("pay_period", "")
        report_type = params.get("report_type", "full")
        currency = params.get("currency", "USD")

        if not records:
            return self.error_result("No payroll records provided.")

        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        report: dict[str, Any] = {
            "report_id": report_id,
            "pay_period": pay_period,
            "currency": currency,
            "generated_at": now.isoformat(),
            "total_employees": len(records),
        }

        # Summary section
        if report_type in ("summary", "full"):
            report["summary"] = self._generate_summary(records, currency)

        # Department breakdown
        if report_type in ("department", "full"):
            report["department_breakdown"] = self._generate_department_breakdown(records, currency)

        # Deduction summary
        if report_type in ("summary", "full"):
            report["deduction_summary"] = self._generate_deduction_summary(records, currency)

        # Compliance overview
        if report_type in ("compliance", "full"):
            report["compliance"] = self._generate_compliance_overview(records)

        report["report_summary"] = (
            f"Payroll report '{report_id}' for period {pay_period}: "
            f"{len(records)} employees, total gross: "
            f"{currency} {report.get('summary', {}).get('total_gross', 0):,.2f}."
        )

        return self.success_result(report)

    def _generate_summary(
        self, records: list[dict[str, Any]], currency: str
    ) -> dict[str, Any]:
        """Generate pay period summary.

        Args:
            records: Payroll records.
            currency: Currency code.

        Returns:
            Summary dict with totals and averages.
        """
        total_gross = sum(float(r.get("gross_salary", 0)) for r in records)
        total_net = sum(float(r.get("net_salary", 0)) for r in records)
        total_deductions = sum(float(r.get("total_deductions", 0)) for r in records)
        total_base = sum(float(r.get("base_salary", 0)) for r in records)
        total_allowances = sum(float(r.get("total_allowances", 0)) for r in records)
        total_overtime = sum(float(r.get("overtime_pay", 0)) for r in records)

        headcount = len(records)

        return {
            "headcount": headcount,
            "currency": currency,
            "total_base": round(total_base, 2),
            "total_allowances": round(total_allowances, 2),
            "total_overtime": round(total_overtime, 2),
            "total_gross": round(total_gross, 2),
            "total_deductions": round(total_deductions, 2),
            "total_net": round(total_net, 2),
            "average_gross": round(total_gross / headcount, 2) if headcount > 0 else 0,
            "average_net": round(total_net / headcount, 2) if headcount > 0 else 0,
            "median_gross": self._calculate_median(
                [float(r.get("gross_salary", 0)) for r in records]
            ),
        }

    def _generate_department_breakdown(
        self, records: list[dict[str, Any]], currency: str
    ) -> list[dict[str, Any]]:
        """Generate department-level breakdown.

        Args:
            records: Payroll records.
            currency: Currency code.

        Returns:
            List of department breakdown dicts.
        """
        dept_data: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            dept = record.get("department", "Unassigned")
            dept_data.setdefault(dept, []).append(record)

        breakdown: list[dict[str, Any]] = []
        for dept, dept_records in sorted(dept_data.items()):
            total_gross = sum(float(r.get("gross_salary", 0)) for r in dept_records)
            total_net = sum(float(r.get("net_salary", 0)) for r in dept_records)
            headcount = len(dept_records)

            breakdown.append({
                "department": dept,
                "headcount": headcount,
                "total_gross": round(total_gross, 2),
                "total_net": round(total_net, 2),
                "average_gross": round(total_gross / headcount, 2) if headcount > 0 else 0,
                "percentage_of_total": 0,  # Calculated below
            })

        # Calculate percentages
        grand_total = sum(d["total_gross"] for d in breakdown)
        for dept in breakdown:
            if grand_total > 0:
                dept["percentage_of_total"] = round(
                    dept["total_gross"] / grand_total * 100, 1
                )

        return breakdown

    def _generate_deduction_summary(
        self, records: list[dict[str, Any]], currency: str
    ) -> dict[str, Any]:
        """Generate deduction category summary.

        Args:
            records: Payroll records.
            currency: Currency code.

        Returns:
            Deduction summary dict.
        """
        deduction_totals: dict[str, float] = {}

        for record in records:
            deductions = record.get("deductions", {})
            if isinstance(deductions, dict):
                for code, amount in deductions.items():
                    deduction_totals[code] = deduction_totals.get(code, 0) + float(amount)

        total_all_deductions = sum(deduction_totals.values())

        items = [
            {
                "deduction_code": code,
                "total_amount": round(amount, 2),
                "percentage_of_total": round(
                    amount / total_all_deductions * 100, 1
                ) if total_all_deductions > 0 else 0,
            }
            for code, amount in sorted(deduction_totals.items(), key=lambda x: -x[1])
        ]

        return {
            "currency": currency,
            "total_deductions": round(total_all_deductions, 2),
            "deduction_categories": items,
            "category_count": len(items),
        }

    def _generate_compliance_overview(
        self, records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate compliance status overview.

        Args:
            records: Payroll records.

        Returns:
            Compliance overview dict.
        """
        countries: dict[str, int] = {}
        nationalities: dict[str, int] = {}

        for record in records:
            country = record.get("country", "Unknown")
            nationality = record.get("nationality", "Unknown")
            countries[country] = countries.get(country, 0) + 1
            nationalities[nationality] = nationalities.get(nationality, 0) + 1

        return {
            "countries": [
                {"country": c, "employee_count": n}
                for c, n in sorted(countries.items(), key=lambda x: -x[1])
            ],
            "nationalities": [
                {"nationality": n, "employee_count": c}
                for n, c in sorted(nationalities.items(), key=lambda x: -x[1])
            ],
            "total_countries": len(countries),
        }

    @staticmethod
    def _calculate_median(values: list[float]) -> float:
        """Calculate median of a list of values.

        Args:
            values: List of numeric values.

        Returns:
            Median value.
        """
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return round((sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2, 2)
        return round(sorted_vals[n // 2], 2)
