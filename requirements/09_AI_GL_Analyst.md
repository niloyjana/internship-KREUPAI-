# AI Worker: General Ledger Analyst
**Department:** Finance & Procurement
**Worker ID:** `ai-gl-analyst`
**Version:** 1.0.0
**Subscription Tier:** Standard — $300/month

---

## 1. Role Overview

The AI GL Analyst supports accounting teams with journal entry suggestions, account code classification, ledger anomaly detection, reconciliation assistance, and month-end close task management. It accelerates the close cycle, reduces posting errors, and ensures finance controllers have a clean, auditable ledger without the manual grind.

### Core Promise
> "Faster month-end close, cleaner ledger, and every anomalous posting caught before the books are closed."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Transaction Classification | Suggests account codes and cost centers for unclassified transactions | Advisory |
| Journal Entry Suggestion | Proposes journal entries based on transaction context and history | Advisory (accountant approves) |
| Anomaly Detection | Identifies unusual amounts, accounts, or timing in posted entries | Full |
| Duplicate Posting Detection | Catches same transaction posted twice | Full |
| Account Reconciliation Support | Compares ledger balances to sub-ledgers, bank, and intercompany | Full |
| Month-End Closing Checklist | Tracks and manages close tasks across the finance team | Full |
| Variance Analysis | Compares actuals to budget, prior period, and forecast | Full |
| Closing Entry Preparation | Prepares period-end adjustments (accruals, prepayments, depreciation) | Advisory |
| Intercompany Reconciliation | Identifies intercompany mismatches across entities | Full |
| Audit-Ready Report Generation | Exports GL summaries with source documentation links | Full |

### Extended Capabilities (Phase 2)
- Automated accrual suggestion based on expense patterns
- Multi-entity consolidation support
- IFRS/GAAP compliance flag on posting patterns
- Natural language GL query ("Show me all entries above $10K in cost center 420 last month")

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| ERP / Accounting System | General ledger access (read + advisory write) |
| Chart of Accounts | Account classification reference |

### Recommended
| System | Purpose |
|---|---|
| Bank Feeds | Bank reconciliation data |
| AP & AR Modules | Sub-ledger reconciliation |
| Fixed Assets Module | Depreciation schedule |
| Budgeting Tool | Budget vs actual variance data |

---

## 4. Workflow Definitions

### Workflow 1: Transaction Classification & Journal Suggestion

```
TRIGGER: New unclassified transaction OR accountant requests suggestion
════════════════════════════════════════════════════════════════════════
Step 1: ANALYZE TRANSACTION
  Description, amount, vendor/customer, date, department

Step 2: MATCH TO CHART OF ACCOUNTS
  Pattern matching vs:
    ├── Historical similar transactions (same vendor/description)
    ├── Chart of accounts definition
    └── Department-specific cost rules

Step 3: SUGGEST
  Account code: GL account recommendation with confidence
  Cost center: department/project allocation
  Tax code: VAT/applicable tax treatment
  Supporting rationale (1–2 sentences)

Step 4: ACCOUNTANT REVIEW
  Suggestion displayed with "Accept / Modify / Reject"
  Accepted suggestions improve future recommendations
  Learning loop: corrections fed back to classification model
```

### Workflow 2: Ledger Anomaly Detection

```
TRIGGER: Scheduled daily + on-demand during close period
══════════════════════════════════════════════════════════
Step 1: SCAN RECENT POSTINGS
  Compare each entry against:
    ├── Historical average for same account/period
    ├── Expected range for transaction type
    └── Unusual account combinations (debit/credit)

Step 2: ANOMALY TYPES DETECTED
  ├── Round-number postings (multiples of 1000 above threshold)
  ├── Entries posted outside business hours
  ├── Reversals of large entries without explanation
  ├── Account normally credited being debited
  ├── Month-end spike entries > 2σ above average
  └── Entries with no source document reference

Step 3: FLAG & ROUTE
  LOW: Informational note on entry
  MEDIUM: Flag for accountant review within 48h
  HIGH: Immediate alert to finance controller

Step 4: LOG
  Every flagged entry logged with: rule triggered, amount, account, timestamp
  Cleared/resolved status tracked
```

### Workflow 3: Month-End Close Management

```
TRIGGER: Month-end close initiated by finance manager
═══════════════════════════════════════════════════════
Step 1: ACTIVATE CHECKLIST
  Generate close checklist from template:
    ├── Post accruals (by department due date)
    ├── Reconcile bank accounts
    ├── Clear AP/AR sub-ledger variances
    ├── Post depreciation entries
    ├── Intercompany matching
    └── Final trial balance review

Step 2: TRACK PROGRESS
  Real-time status per task: pending | in_progress | complete | blocked
  Assigned accountant visibility per task

Step 3: AUTOMATED SUPPORTS
  Pull bank statement → compare to ledger → flag differences
  Pull AP balance → compare to GL → flag variance
  Pull AR balance → compare to GL → flag variance
  Suggest accrual entries based on expense history

Step 4: CLOSE READINESS REPORT
  All tasks complete? → "Ready to close" status
  Open items? → List with blocker details and responsible owner
  Finance manager signs off to lock the period
```

---

## 5. Policy Configuration

```yaml
anomaly_detection:
  round_number_threshold: 10000           # Flag round numbers above $10K
  off_hours_posting_alert: true
  unusual_account_combination_check: true
  historical_lookback_months: 12

journal_suggestion:
  confidence_threshold_for_suggestion: 0.80
  require_human_approval: true           # Always — no autonomous posting
  learning_from_corrections: true

close_management:
  close_day_of_month: 5                  # Close completed by 5th of next month
  reminder_days_before: [3, 1]
  auto_generate_accrual_suggestions: true

reconciliation:
  bank_reconciliation_frequency: "daily"
  intercompany_check: true
  tolerance_amount: 1.00                 # $1.00 tolerance for rounding
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| Month-End Close Cycle Reduction | > 30% faster vs pre-AI baseline |
| Journal Suggestion Acceptance Rate | > 75% (quality signal) |
| Anomaly Detection Accuracy | > 95% (true positives vs false flags) |
| Reconciliation Completion Rate | 100% before close |
| Open Exceptions at Close | < 5% of line items |
| Audit Findings Related to GL | Zero AI-caused posting errors |

---

## 7. Guardrails

```
✓ Journal entries always require human accountant approval before posting
✓ Period lock/unlock only authorized by finance controller — never AI-initiated
✓ Audit trail covers all AI suggestions, whether accepted or rejected
✓ No write-offs or large adjustments auto-proposed without management threshold review
✓ Intercompany entries: never resolved autonomously — always flagged to both entity accountants
✓ Chart of accounts modifications never made autonomously
```

---

## 8. Setup Checklist

```
[ ] ERP accounting module connected (read + draft-write)
[ ] Chart of accounts imported
[ ] Historical transactions loaded (12 months minimum for ML baseline)
[ ] Close checklist template configured per entity
[ ] Bank feed connected for reconciliation
[ ] Accountant user mapping (who owns which entities/cost centers)
[ ] Anomaly detection thresholds configured
[ ] Finance controller escalation routing set
[ ] Test: load 1 prior month's transactions, validate suggestions and anomaly flags
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Finance & Procurement | Role: General Ledger Analyst*
