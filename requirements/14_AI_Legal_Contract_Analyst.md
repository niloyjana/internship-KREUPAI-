# AI Worker: Legal Contract Analyst
**Department:** Governance, Risk & Control
**Worker ID:** `ai-legal-contract-analyst`
**Version:** 1.0.0
**Subscription Tier:** Standard — $350/month

---

## 1. Role Overview

The AI Legal Contract Analyst reviews, summarizes, and risk-scores contracts — accelerating legal review cycles without replacing legal judgment. It extracts key commercial and legal terms, compares clauses against company standards, flags high-risk provisions, and supports redline recommendations. Human counsel retains all approval authority.

### Core Promise
> "Contract review cycles cut from weeks to hours — with every high-risk clause highlighted before signing."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Contract Summarization | Extracts key terms: parties, duration, value, obligations, termination | Full |
| Clause-Level Analysis | Reviews each clause for content and risk | Full |
| Standard Clause Comparison | Compares contract to approved clause library | Full |
| Deviation Flagging | Highlights clauses that differ from company standard | Full |
| High-Risk Clause Detection | Flags unlimited liability, auto-renewal, data privacy, IP, indemnity | Full |
| Risk Score Assignment | Overall contract risk score with clause-level breakdown | Full |
| Redline Suggestion | Proposes alternative "fallback" language for deviant clauses | Advisory |
| Contract Metadata Extraction | Extracts dates, values, renewal triggers for contract register | Full |
| Obligation Tracking | Identifies ongoing obligations and milestone dates | Full |
| Counterparty Research | Pulls known information about contracting party | Full |
| Multi-Language Support | English and Arabic contract review | Full |

### Extended Capabilities (Phase 2)
- Portfolio risk analysis (risk across all active contracts)
- Contract lifecycle management: renewal and expiry alerts
- Precedent library: compare to previously negotiated terms
- E-signature workflow integration

---

## 3. Workflow Definitions

### Workflow 1: New Contract Review

```
TRIGGER: Contract document uploaded for review
═══════════════════════════════════════════════
Step 1: PARSE & CLASSIFY
  Document type: NDA | Service Agreement | Supply Contract | Employment | Lease
  Parties, effective date, governing law, jurisdiction

Step 2: EXTRACT KEY TERMS
  Duration and renewal terms (auto-renewal trigger? notice period?)
  Payment terms (amounts, milestones, penalties)
  Termination rights (for cause, convenience, force majeure)
  Liability caps (capped or unlimited?)
  Indemnification scope (mutual or one-sided?)
  Intellectual property (ownership, license grants)
  Data protection (GDPR/PDPL compliance clauses)
  Dispute resolution (arbitration vs litigation, seat)

Step 3: COMPARE TO STANDARD LIBRARY
  Each clause mapped to standard clause equivalent
  Deviation: Minor | Significant | Missing standard clause entirely

Step 4: RISK SCORE
  Per clause: LOW | MEDIUM | HIGH | CRITICAL
  Overall contract risk: weighted composite

Step 5: DELIVER REVIEW PACKAGE
  Executive summary (1 page): key dates, value, top 3 risks
  Clause-by-clause analysis with risk tags
  Suggested fallback language for HIGH/CRITICAL clauses
  Source references: [Page X, Clause Y] for every finding

Step 6: HUMAN LEGAL REVIEW
  Legal counsel reviews AI analysis
  Approves, modifies, or overrides each risk finding
  Final legal sign-off before execution
```

---

## 4. Policy Configuration

```yaml
risk_detection_rules:
  unlimited_liability: CRITICAL
  auto_renewal_without_notice: HIGH
  data_privacy_non_compliant: HIGH
  one_sided_indemnification: HIGH
  ip_assignment_to_counterparty: HIGH
  governing_law_foreign_unfavorable: MEDIUM
  payment_delay_penalty_high: MEDIUM
  termination_for_convenience_restricted: MEDIUM

standard_clause_library:
  version: "v3.2"
  fallback_language: true              # Include suggested alternatives for deviations
  enforce_governing_law: "Bahrain"     # Flag if not Bahrain or agreed jurisdiction

review_sla:
  standard_contract_hours: 4
  complex_contract_hours: 24
  nda_hours: 1
```

---

## 5. KPIs

| KPI | Target |
|---|---|
| Contract Review Cycle Time | > 70% reduction vs manual review |
| High-Risk Clause Detection Accuracy | > 90% (validated by legal counsel) |
| Clause Coverage | 100% (no clause unreviewed) |
| Redline Acceptance Rate | > 60% (fallback language adopted) |
| Contract Summary Accuracy | > 92% rated accurate by legal team |

---

## 6. Guardrails

```
✓ AI never auto-approves contracts — legal counsel sign-off always required
✓ Risk ratings are informational — legal counsel can override with reasoning
✓ Counterparty research sourced from approved public/internal sources only
✓ Contract terms never disclosed outside authorized users
✓ Signed contracts stored in secure document vault, not in AI context
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Governance, Risk & Control | Role: Legal Contract Analyst*
