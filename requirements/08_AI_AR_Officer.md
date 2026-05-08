# AI Worker: Accounts Receivable Officer
**Department:** Finance & Procurement
**Worker ID:** `ai-ar-officer`
**Version:** 1.0.0
**Subscription Tier:** Standard — $300/month

---

## 1. Role Overview

The AI AR Officer manages the full receivables lifecycle: monitoring outstanding invoices, executing structured collection follow-ups, aging analysis, payment prediction, and customer account health monitoring. It ensures cash flow remains healthy by keeping collections proactive rather than reactive — while maintaining professional customer relationships.

### Core Promise
> "Outstanding invoices get followed up on Day 1 — not when a human remembers."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Invoice Monitoring | Daily scan of all outstanding invoices by due date | Full |
| Aging Analysis | Categorizes receivables: current, 1–30, 31–60, 61–90, 90+ days | Full |
| Automated Follow-Up | Sends structured reminders at configured intervals | Full |
| Escalation Cadence | Escalates to senior collector/manager per aging bucket | Full |
| Payment Prediction | ML-based prediction of collection probability and delay risk | Full |
| High-Risk Flagging | Identifies customers with deteriorating payment patterns | Full |
| Payment Application | Matches received payments to invoices in ERP | Full |
| Dispute Logging | Captures and tracks customer-raised disputes | Full |
| Credit Hold Trigger | Recommends credit hold for chronic late payers | Policy-gated |
| Customer Statement | Generates account statements on request | Full |
| Cash Flow Reporting | Daily/weekly AR summary for finance leadership | Full |

### Extended Capabilities (Phase 2)
- Customer portal: self-service payment and statement access
- Dynamic dunning: adjust tone and urgency based on customer history
- Integration with credit bureaus for risk enrichment
- Multi-currency reconciliation automation

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| ERP / Finance System | Invoice data, payment records, customer accounts |
| Email | Customer follow-up communications |

### Recommended
| System | Purpose |
|---|---|
| CRM | Customer relationship context before collection calls |
| Payment Gateway | Confirm payment receipt in real-time |
| Banking Integration | Bank statement reconciliation |
| Customer Portal | Self-service payment and statement access |

---

## 4. Workflow Definitions

### Workflow 1: Daily AR Review & Follow-Up

```
TRIGGER: Scheduled daily job (09:00 tenant timezone)
════════════════════════════════════════════════════
Step 1: AGING SCAN
  Pull all open invoices
  Categorize by days past due:
    Current (not due) → No action
    1–7 days past due → Gentle first reminder
    8–30 days past due → Second reminder, firmer tone
    31–60 days past due → Escalation tone, cc manager
    61–90 days past due → Formal demand, legal reference
    91+ days past due → Escalate to Collections Manager

Step 2: GENERATE COMMUNICATIONS
  Personalized per customer:
    ├── Include: invoice number, amount, due date, payment link
    ├── Reference any prior communications
    └── Tone calibrated to aging bucket

Step 3: SEND & LOG
  Send emails (and/or SMS if configured)
  Log every touchpoint in ERP AR ledger
  Update follow-up history on customer record

Step 4: DAILY SUMMARY
  Report to AR manager: total outstanding, by bucket, by customer
  Flag new invoices entering 30+ day bucket
  Flag customers with no response after 3 contacts
```

### Workflow 2: Payment Prediction & Risk Flagging

```
TRIGGER: Weekly AI analysis job
═════════════════════════════════
Step 1: ANALYZE CUSTOMER HISTORY
  Per customer: average days to pay, payment pattern trends
  External signals: industry, company size, payment frequency

Step 2: PREDICT
  Probability of collection in next 30/60/90 days
  Expected payment date estimate
  Risk category: LOW | MEDIUM | HIGH | CRITICAL

Step 3: RECOMMEND ACTIONS
  HIGH risk: Recommend credit hold review, escalate to sales
  CRITICAL risk: Recommend legal escalation or collection agency referral

Step 4: REPORT TO FINANCE
  AR risk dashboard updated
  Cash flow projection adjusted
```

---

## 5. Policy Configuration

```yaml
dunning_schedule:
  day_0:  "friendly_reminder"
  day_7:  "second_reminder"
  day_15: "firm_reminder"
  day_30: "escalation_notice"
  day_45: "formal_demand"
  day_60: "escalate_to_manager"

credit_hold_policy:
  recommend_above_days_overdue: 60
  require_manager_approval: true
  auto_hold_enabled: false               # Never automatic — always human decision

collection_tone:
  current_to_7_days: "friendly_professional"
  8_to_30_days: "firm_professional"
  31_to_60_days: "formal_urgent"
  61_plus_days: "legal_reference_required"

payment_prediction:
  model_lookback_months: 12
  high_risk_threshold: 0.65              # Probability of non-payment > 65% = HIGH
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| Days Sales Outstanding (DSO) Reduction | > 15% vs pre-AI baseline |
| Collection Follow-Up Coverage | 100% (no invoice missed) |
| First Contact Resolution Rate | > 40% (payment after first reminder) |
| Cash Flow Forecast Accuracy | > 85% (AI prediction vs actual) |
| Dispute Resolution Time | < 5 business days |
| AR Aging >60 Days as % of Total | < 5% |

---

## 7. Guardrails

```
✓ Credit hold recommendations require manager approval before execution
✓ Legal demand letters reviewed by finance controller before sending
✓ Customer payment details (card, bank) never stored or exposed in AI context
✓ Collection communications never sent to contacts flagged as disputed/legal hold
✓ No write-off authorized without explicit human approval
```

---

## 8. Setup Checklist

```
[ ] ERP/finance system connected (invoice + payment data)
[ ] Customer email database imported
[ ] Dunning schedule configured per tenant policy
[ ] AR manager notification routing set up
[ ] Payment prediction model seeded with 12 months history
[ ] Credit hold approval workflow defined
[ ] Communication tone templates reviewed and approved
[ ] Test: 20 sample overdue invoices run through dunning workflow
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Finance & Procurement | Role: Accounts Receivable Officer*
