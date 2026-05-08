# AI Worker: Procurement Officer
**Department:** Finance & Procurement
**Worker ID:** `ai-procurement-officer`
**Version:** 1.0.0
**Subscription Tier:** Standard — $300/month

---

## 1. Role Overview

The AI Procurement Officer automates the operational purchasing cycle: validating purchase requisitions against policy, comparing supplier quotes intelligently, drafting purchase orders, tracking deliveries, and monitoring spend compliance. Procurement managers gain strategic time back while the AI ensures every purchase is policy-compliant, competitively priced, and properly documented.

### Core Promise
> "Compliant POs created in minutes, not days — with the best supplier selected every time."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Requisition Validation | Checks PRs against budget, category policy, approval thresholds | Full |
| Supplier Quote Comparison | Multi-dimensional comparison: price, delivery, quality, terms | Full |
| Recommendation with Reasoning | Selects recommended supplier with documented rationale | Advisory |
| PO Draft Generation | Creates draft PO from approved requisition + supplier data | Draft (buyer approves) |
| Spend Analysis | Analyzes historical spend by category, supplier, department | Full |
| Price Trend Analysis | Tracks commodity/service price movements over time | Full |
| Supplier Shortlisting | Maintains and applies pre-qualified supplier lists | Full |
| Budget Check | Real-time budget availability check before PR approval | Full |
| Contract Compliance Check | Compares PO to existing contract terms | Full |
| Three-Bid Enforcement | Ensures policy-required competitive bids are obtained | Full |
| Supplier Performance Tracking | Logs delivery time, quality issues, invoice accuracy per supplier | Full |

### Extended Capabilities (Phase 2)
- Automated RFQ generation and distribution to suppliers
- Supplier onboarding workflow (registration, vetting, approval)
- Preferred supplier catalog for direct catalog-based ordering
- Tail spend analysis and consolidation recommendations
- ESG supplier scoring (sustainability, diversity)

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| ERP / Procurement Module | PR/PO management, supplier master |
| Finance System | Budget availability check |
| Email | Supplier communication, quote requests |

### Recommended
| System | Purpose |
|---|---|
| Contract Management | Contract terms compliance |
| Supplier Portal | Quote submission, invoice upload |
| Catalogue System | Preferred item/pricing catalog |
| Logistics System | Delivery tracking post-PO |

---

## 4. Workflow Definitions

### Workflow 1: Purchase Requisition Validation

```
TRIGGER: New purchase requisition submitted
═════════════════════════════════════════════
Step 1: POLICY VALIDATION
  ├── Requester has authority for this category?
  ├── Amount within requester's approval limit?
  ├── Budget available in cost center?
  ├── Category permitted (no restricted items)?
  └── Preferred supplier used (if contracted)?

Step 2: OUTCOME
  COMPLIANT → Advance to sourcing/PO creation
  NON-COMPLIANT → Return to requester with specific violation
  THRESHOLD EXCEEDED → Route to appropriate approval level

Step 3: LOG
  Validation result, rules checked, timestamp
  Notify requester and relevant approver
```

### Workflow 2: Supplier Quote Comparison

```
TRIGGER: Quotes received for a sourcing event
═════════════════════════════════════════════
Step 1: INGEST QUOTES
  Parse from email/portal: supplier name, line items, unit price, delivery time, payment terms, warranty

Step 2: NORMALIZE
  Convert to same currency, same units
  Extract delivery lead time in days

Step 3: SCORE (weighted matrix)
  Price:              40 pts (lowest normalized price = 40)
  Delivery time:      25 pts (fastest = 25)
  Supplier reliability: 20 pts (from supplier performance history)
  Payment terms:      10 pts (longest credit terms = 10)
  Compliance / certs: 5 pts (ISO, regulatory certifications)

Step 4: GENERATE COMPARISON TABLE
  Side-by-side table of all suppliers
  Recommended supplier highlighted with score reasoning
  "Lowest price" ≠ automatic winner (explicitly noted)

Step 5: DELIVER TO BUYER
  Comparison visible in procurement portal
  Buyer selects supplier → PO draft initiated
```

### Workflow 3: PO Draft Creation

```
TRIGGER: Buyer approves supplier selection
══════════════════════════════════════════
Step 1: PULL DATA
  Approved PR details
  Selected supplier master data (address, payment terms, bank)
  Contract terms if applicable

Step 2: GENERATE PO DRAFT
  PO header: date, PO number, entity, delivery address
  Line items: description, quantity, unit price, total
  Tax: applicable VAT/GST
  Delivery terms, payment terms
  Contract reference (if applicable)

Step 3: REVIEW & RELEASE
  Draft visible to buyer for review
  Buyer approves → PO sent to supplier
  Supplier receives via email/portal with acknowledgment request

Step 4: TRACK
  Supplier acknowledges? → Log
  Expected delivery date set → Monitor
  Invoice received? → Route to AP Officer agent
```

---

## 5. Policy Configuration

```yaml
approval_thresholds:
  requester_self_approve: 500
  department_head_approval: 5000
  procurement_manager_approval: 25000
  cfo_approval: 100000

three_bid_policy:
  minimum_bids_required: 3
  exceptions:
    - "sole_source_documented"
    - "emergency_procurement"
    - "below_threshold_500"

supplier_scoring_weights:
  price: 40
  delivery: 25
  reliability: 20
  payment_terms: 10
  compliance: 5

budget_check:
  real_time_check: true
  commit_budget_on_pr_approval: true    # Reserve budget when PR approved
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| PR-to-PO Cycle Time | < 24 hours (compliant PRs) |
| Policy Compliance Rate | > 99% (PRs validated before PO) |
| Three-Bid Compliance | 100% (where policy applies) |
| Cost Savings via Comparison | > 8% vs historical single-source pricing |
| Supplier On-Time Delivery Rate | Tracked per supplier via AI monitoring |
| PO First-Pass Accuracy | > 98% (no amendments needed post-issue) |

---

## 7. Guardrails

```
✓ POs never sent to supplier without buyer/approver sign-off
✓ Budget checks always performed — no PO if budget unavailable (unless override with documented reason)
✓ Sole-source decisions require documented justification — AI flags, never approves
✓ Supplier bank detail changes trigger verification before PO payment routing
✓ Recommendation is advisory — final supplier selection always human decision
```

---

## 8. Setup Checklist

```
[ ] ERP procurement module connected
[ ] Supplier master imported (name, address, bank, terms, certs)
[ ] Chart of accounts / cost centers loaded for budget check
[ ] Approval authority matrix configured
[ ] Category policy rules defined (restricted, preferred, open)
[ ] Scoring weights configured per tenant preference
[ ] PO templates configured per entity/region
[ ] Supplier quote intake channel set (email + portal)
[ ] Contract repository connected (for compliance checks)
[ ] Test: 5 sample PRs run through validation, 3 with quote comparison
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Finance & Procurement | Role: Procurement Officer*
