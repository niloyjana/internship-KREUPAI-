# AI Worker: Accounts Payable Officer
**Department:** Finance & Procurement
**Worker ID:** `ai-ap-officer`
**Version:** 1.0.0
**Subscription Tier:** Standard — $300/month

---

## 1. Role Overview

The AI Accounts Payable Officer processes the entire supplier invoice lifecycle: capturing and extracting invoice data, performing 2-way and 3-way matching against purchase orders and goods receipts, detecting duplicates and fraud signals, preparing validated payment batches, and handling vendor queries. Finance retains full control over payment release while the AI eliminates manual processing.

### Core Promise
> "Every invoice processed accurately, every duplicate caught, every payment batch clean — before a human ever touches it."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Invoice Capture | Ingests invoices from email, portal, PDF, EDI | Full |
| Data Extraction | Extracts vendor, amount, tax, line items, invoice no, dates | Full |
| Confidence Scoring | Rates extraction accuracy — flags low-confidence fields for review | Full |
| 2-Way Matching | Matches invoice vs Purchase Order (quantity, price, vendor) | Full |
| 3-Way Matching | Matches invoice vs PO vs Goods Receipt Note | Full |
| Tolerance Checking | Applies configurable tolerance for price/quantity variances | Full |
| Duplicate Detection | Detects same invoice by multiple signals (no, amount, vendor, date) | Full |
| Near-Duplicate Detection | Catches slightly modified duplicate attempts | Full |
| Risk Scoring | Assigns fraud risk score to each invoice | Full |
| Payment Batch Preparation | Groups matched invoices into payment batch for approval | Full |
| Vendor Query Handling | Answers vendor payment status queries | Full |
| Discrepancy Escalation | Routes mismatched invoices to relevant team with explanation | Full |
| Early Payment Discount Flagging | Identifies discounts available for early settlement | Full |

### Extended Capabilities (Phase 2)
- OCR enhancement with layout intelligence (complex multi-page invoices)
- Supplier portal self-service (vendor tracks own invoice status)
- ERP direct posting of matched invoices
- Cash flow impact analysis per payment batch
- Vendor performance scoring (payment terms compliance)

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| Email | Invoice ingestion from vendor emails |
| ERP / Finance System | PO data, GRN data, payment posting |
| Document Storage | Invoice archive |

### Recommended
| System | Purpose |
|---|---|
| Accounts Payable Portal | Vendor invoice upload self-service |
| Payment Gateway / Bank | Payment execution (post-approval) |
| Tax System | VAT/GST validation |
| Vendor Master Database | Vendor verification, bank details |

---

## 4. Workflow Definitions

### Workflow 1: Invoice Processing & Matching

```
TRIGGER: Invoice received (email / portal upload / EDI)
════════════════════════════════════════════════════════
Step 1: CAPTURE
  Detect invoice from email attachment or portal upload
  Classify document type: invoice | credit note | proforma | statement

Step 2: EXTRACT DATA
  Using OCR + LLM extraction:
    ├── Vendor name and ID
    ├── Invoice number
    ├── Invoice date and due date
    ├── Line items (description, quantity, unit price)
    ├── Subtotal, tax (VAT/GST), total amount
    └── Payment terms and bank details

  Assign confidence score per field (0–1.0)
  Flag fields below 0.85 for human review

Step 3: VALIDATE VENDOR
  Check vendor name/ID against approved vendor master
  If new vendor or unrecognized → hold for AP manager approval
  Verify IBAN/bank details match vendor master

Step 4: DUPLICATE CHECK
  Check across dimensions:
    ├── Exact match: same invoice number + vendor + amount
    ├── Near-duplicate: same vendor + amount ± 1% within 30 days
    └── Previously rejected/cancelled invoice re-submitted?
  Match → Block, flag, alert AP manager

Step 5: PO MATCHING
  2-Way: Match invoice line items vs PO:
    ├── Vendor match?
    ├── Item/description match?
    ├── Quantity within tolerance?
    └── Price within tolerance?

  3-Way (if GRN available): Add:
    ├── Goods actually received (GRN quantity)?
    └── Receipt date before invoice date?

  Tolerance rules:
    ├── Price variance ≤ configurable % → PASS
    ├── Quantity variance ≤ configurable % → PASS
    └── Outside tolerance → FLAG with variance details

Step 6: OUTCOME ROUTING
  Fully matched → Add to payment batch queue
  Partial match (within tolerance) → Add with note
  Mismatch → Route to AP manager with variance explanation
  Fraud risk HIGH → Block + escalate to finance controller
  No PO found → Hold, request PO from requester

Step 7: PAYMENT BATCH PREP
  Group approved invoices by:
    ├── Payment due date (prioritize early discount deadlines)
    ├── Currency
    └── Bank/payment method

  Generate batch summary for finance approval
  Human approves → payment executed
```

### Workflow 2: Vendor Query Handling

```
TRIGGER: Vendor emails or calls about invoice/payment status
════════════════════════════════════════════════════════════
Step 1: IDENTIFY VENDOR & INVOICE
  Match vendor email/name to vendor master
  Locate referenced invoice in system

Step 2: RETRIEVE STATUS
  Processing status: received | under review | matched | approved | paid | on hold

Step 3: RESPOND
  Paid: "Invoice [no] for [amount] was paid on [date] via [method]. Ref: [txn]."
  Approved, pending payment: "Invoice approved. Payment scheduled for [date]."
  On hold: "Invoice is on hold due to [reason — non-sensitive]. Contact [team]."
  Not found: "Please re-send invoice to [AP inbox] or upload via vendor portal."

Step 4: LOG
  Interaction logged in AP system against vendor and invoice records
```

---

## 5. Policy Configuration

```yaml
matching_policy:
  two_way_matching_default: true
  three_way_matching_above_amount: 5000   # 3-way for invoices > $5,000
  price_tolerance_percent: 2              # ±2% price variance accepted
  quantity_tolerance_percent: 1           # ±1% quantity variance accepted
  currency_rounding_tolerance: 0.05       # $0.05 rounding difference accepted

fraud_detection:
  duplicate_window_days: 90              # Look back 90 days for duplicates
  near_duplicate_amount_tolerance: 0.01  # 1% amount tolerance for near-dupe
  new_vendor_hold: true                  # Hold new vendor invoices for review
  bank_detail_change_alert: true         # Alert if vendor bank details changed

payment_policy:
  auto_approve_below_amount: 0           # Never auto-approve — always human sign-off
  early_discount_flag_days: 7            # Flag early payment discounts ≥ 7 days before deadline
  payment_batch_frequency: "weekly"      # weekly | twice_monthly | monthly

extraction_confidence:
  minimum_confidence_auto_process: 0.90  # Below 90% → human review required
  ocr_fallback_to_manual: true
```

---

## 6. Data Schema

```prisma
model Invoice {
  id                String   @id @default(cuid())
  tenantId          String
  vendorId          String?
  vendorName        String
  invoiceNumber     String
  invoiceDate       DateTime
  dueDate           DateTime?
  subtotal          Decimal
  taxAmount         Decimal  @default(0)
  totalAmount       Decimal
  currency          String   @default("USD")
  status            String   // received | matching | matched | on_hold | approved | paid | rejected
  matchingType      String?  // 2way | 3way
  poReference       String?
  grnReference      String?
  priceVariance     Float?
  quantityVariance  Float?
  riskScore         Float?   // 0.0 = clean, 1.0 = high risk
  duplicateFlag     Boolean  @default(false)
  extractionConfidence Float?
  paymentBatchId    String?
  paidAt            DateTime?
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@unique([tenantId, vendorId, invoiceNumber])
  @@index([tenantId, status])
  @@index([tenantId, dueDate])
  @@map("invoices")
}
```

---

## 7. KPIs

| KPI | Target |
|---|---|
| Invoice Processing Time | < 2 hours (from receipt to match result) |
| Straight-Through Processing Rate | > 70% (matched with no human touch) |
| Duplicate Detection Accuracy | > 99.5% |
| Extraction Accuracy | > 95% on structured invoices |
| Payment On-Time Rate | > 98% (approved invoices paid within terms) |
| AP Query Resolution Rate | > 85% vendor queries self-served |
| Early Discount Capture Rate | > 80% of available early payment discounts |

---

## 8. Guardrails

```
✓ No invoice ever paid without explicit finance manager approval
✓ New vendor invoices always held for human verification of bank details
✓ Vendor bank detail changes trigger mandatory alert before any payment
✓ Fraud-risk scored invoices never auto-cleared — escalation mandatory
✓ Payment file generation is preparation only — bank submission by human
✓ Vendor account data (bank details, IBAN) encrypted — never in AI context plain text
✓ Duplicate block cannot be overridden without documented justification
```

---

## 9. Acceptance Criteria

- ✅ AI reads structured and semi-structured invoices with confidence scoring
- ✅ Vendor, amount, tax, and invoice number extracted and visible for review
- ✅ 2-way and 3-way matching with configurable tolerance applied
- ✅ Mismatches highlighted with specific variance details (not just "mismatch")
- ✅ Duplicate and near-duplicate detection covers all defined patterns
- ✅ Risk score assigned and high-risk invoices blocked pending review
- ✅ Payment batch grouped and ready for single-click approval

---

## 10. Setup Checklist

```
[ ] AP inbox connected (email ingestion)
[ ] ERP connected (PO data, GRN data, vendor master)
[ ] Document storage configured for invoice archive
[ ] Vendor master imported (name, ID, bank details)
[ ] Matching rules configured (2-way vs 3-way thresholds)
[ ] Tolerance settings defined (price, quantity, currency)
[ ] Fraud risk rules configured
[ ] Approval workflow mapped (AP manager → finance controller)
[ ] Vendor query response templates reviewed
[ ] Test: 20 real invoices (mix of clean, duplicate, mismatch) processed and validated
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Finance & Procurement | Role: Accounts Payable Officer*
