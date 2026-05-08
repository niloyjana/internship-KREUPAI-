# AI Worker: Payroll Analyst
**Department:** HR & People Operations
**Worker ID:** `ai-payroll-analyst`
**Version:** 1.0.0
**Subscription Tier:** Standard — $280/month

---

## 1. Role Overview

The AI Payroll Analyst handles the pre-processing, validation, and anomaly detection phases of payroll — the most error-prone and time-consuming parts. It collects payroll inputs from attendance, leave, and allowance systems, validates consistency, detects anomalies before release, prepares summaries for payroll managers, and answers employee payslip queries. Final payroll release remains a human-controlled step.

### Core Promise
> "Payroll errors caught before they reach employees — not after."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Payroll Input Collection | Aggregates attendance, leave, overtime, allowances from source systems | Full |
| Data Validation | Checks for missing, inconsistent, or out-of-range values | Full |
| Anomaly Detection | Identifies unusual salary changes, duplicate payments, spikes | Full |
| Variance Analysis | Compares current payroll to previous cycle and flags deviations | Full |
| Payroll Summary Preparation | Generates pre-processing report for payroll manager review | Full |
| Employee Query Handling | Answers payslip and deduction questions for employees | Full (scoped) |
| Statutory Calculation Assistance | Assists with GOSI, SOCSO, EPF, income tax checks by region | Advisory |
| Payslip Distribution Trigger | Triggers payslip delivery post-approval | Full |
| Exception Report Generation | Categorizes and exports all detected anomalies | Full |
| Audit Trail Maintenance | Records every validation check and exception with timestamps | Full |
| Month-End Close Support | Tracks payroll processing tasks against close checklist | Full |

### Extended Capabilities (Phase 2)
- Integration with biometric attendance devices
- Automated leave balance reconciliation at year-end
- Multi-currency payroll support (for international entities)
- Tax filing preparation assistant (per jurisdiction)
- Real-time payroll cost dashboard for finance team

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| HRMS | Employee master data, salary records |
| Attendance / Time System | Working hours, overtime, absences |
| Leave Management | Approved leave, leave without pay |
| Payroll Software | Input data feed and output validation |

### Recommended
| System | Purpose |
|---|---|
| Finance / ERP | Cost center allocation, journal entries |
| Employee Self-Service Portal | Employee payslip queries |
| Bank Integration | Payment file generation validation |
| Statutory Portals | GOSI (KSA/Bahrain), WPS (UAE) submission tracking |

---

## 4. Workflow Definitions

### Workflow 1: Payroll Input Validation (Pre-Processing)

```
TRIGGER: Payroll period close — processing initiated by payroll manager
══════════════════════════════════════════════════════════════════════════
Step 1: COLLECT INPUTS
  Pull from attendance system:
    ├── Working days per employee
    ├── Overtime hours logged
    └── Absences (authorized vs unauthorized)

  Pull from leave system:
    ├── Approved leave taken
    ├── Leave without pay (LWP) flags
    └── Leave encashment if applicable

  Pull from HRMS:
    ├── Active employee list
    ├── Salary components (basic, housing, transport)
    ├── New hires this period (pro-rata?)
    └── Leavers this period (final settlement)

Step 2: VALIDATION CHECKS
  ├── Every active employee has attendance record?
  ├── Overtime hours within policy limits?
  ├── Leave days ≤ available balance?
  ├── New joiners flagged for pro-rata?
  ├── Leavers flagged for end-of-service?
  └── Any salary change > 10% this cycle? (flag for review)

Step 3: ANOMALY DETECTION
  ├── Employee paid twice in same period?
  ├── Salary value outside ±2σ of last 6-month average?
  ├── Inactive employee still in payroll run?
  ├── Allowance above configurable cap?
  └── Cost center mismatch vs HR records?

Step 4: GENERATE VALIDATION REPORT
  Summary: total headcount, total gross, total net vs prior month
  Exceptions table: employee, field, issue, severity (critical/warning/info)
  Recommended actions per exception

Step 5: DELIVER TO PAYROLL MANAGER
  Report in portal + email notification
  Critical exceptions flagged in RED — must resolve before processing
  Warnings in AMBER — review recommended
  No autonomous payroll release — human sign-off required
```

### Workflow 2: Employee Payslip Query Handling

```
TRIGGER: Employee submits payroll query via portal/email
════════════════════════════════════════════════════════
Step 1: AUTHENTICATE ACCESS
  Verify employee identity (session-based authentication)
  Confirm query is about their own payslip only

Step 2: RETRIEVE PAYSLIP DATA
  Pull current and last 3 payslips from system
  Load salary structure (basic, allowances, deductions breakdown)

Step 3: ANSWER QUERY
  Common queries handled autonomously:
    ├── "Why is my salary different this month?" → Explain deduction/addition
    ├── "What is the housing allowance?" → Explain component
    ├── "How many leave days deducted?" → Show leave record
    └── "What is GOSI deduction?" → Explain statutory calculation

  Escalate to HR payroll team:
    ├── Dispute over attendance records
    ├── Claim of incorrect salary grade
    └── Legal/contractual disputes

Step 4: LOG INTERACTION
  Query type, employee ID (anonymized in logs), resolution status
```

---

## 5. Policy Configuration

```yaml
anomaly_detection:
  salary_variance_threshold_percent: 10  # Flag if change > 10% vs last cycle
  overtime_cap_hours_per_month: 60       # Flag if OT > 60 hours
  inactive_employee_check: true
  duplicate_payment_check: true

validation_rules:
  critical:                              # Block payroll processing until resolved
    - "duplicate_employee_payment"
    - "inactive_employee_in_run"
    - "missing_attendance_record"
  warning:                              # Review recommended, not blocking
    - "salary_variance_above_threshold"
    - "overtime_above_cap"
    - "allowance_above_maximum"

statutory_config:
  region: "bahrain"                     # Options: bahrain | ksa | uae | global
  gosi_employee_rate: 0.07              # Employee GOSI contribution 7%
  gosi_employer_rate: 0.12             # Employer GOSI contribution 12%

employee_query_policy:
  self_service_scope:
    - "payslip_explanation"
    - "deduction_breakdown"
    - "leave_deduction"
    - "overtime_payment"
  escalate_to_human:
    - "salary_dispute"
    - "attendance_dispute"
    - "legal_query"
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| Pre-Processing Error Detection Rate | > 99% | All anomalies caught before processing |
| Payroll Exception Resolution Time | < 4 hours | Avg time from flag to HR resolution |
| Employee Query Resolution Rate | > 80% self-service | Queries resolved without HR ticket |
| Payslip Query Response Time | < 5 minutes | From query to answer |
| Payroll Processing Cycle Time | Reduced by 60% vs manual | Benchmark from client baseline |
| Zero Unauthorized Payments | 100% | No payment without human sign-off |

---

## 7. Guardrails

```
✓ Payroll never processed without explicit payroll manager approval
✓ AI never accesses or reveals another employee's salary data
✓ Salary adjustments only reflected if HRMS record confirms — no manual overrides
✓ Bank file generation is advisory only — final file generated by payroll software
✓ Statutory deduction calculations flagged as advisory, not authoritative (verify with accountant)
✓ Employee query scope strictly limited to own payslip data
✓ All anomaly flags include reasoning — no black-box rejections
```

---

## 8. Acceptance Criteria

- ✅ All payroll inputs collected and validated before manager review
- ✅ Missing or abnormal values clearly flagged with severity
- ✅ Validation report generated with employee-level exception details
- ✅ Employee payslip questions answered accurately without creating HR ticket
- ✅ Sensitive financial questions requiring HR review are escalated
- ✅ No payroll is released autonomously — human approval gate enforced

---

## 9. Setup Checklist

```
[ ] HRMS connected (employee master, salary structure)
[ ] Attendance system connected (daily/monthly records)
[ ] Leave management system connected
[ ] Payroll software connected (read for validation, write for data feed)
[ ] Statutory configuration set (region, GOSI/EPF/tax rates)
[ ] Anomaly thresholds configured
[ ] Employee self-service portal linked (for query channel)
[ ] Payroll manager notification workflow set up
[ ] Critical vs warning exception categories defined
[ ] Test: run validation on prior month's payroll data, review report accuracy
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: HR & People Operations | Role: Payroll Analyst*
