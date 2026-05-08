# AI Worker: Account Executive Assistant
**Department:** Sales & Marketing
**Worker ID:** `ai-account-exec-assistant`
**Version:** 1.0.0
**Subscription Tier:** Standard — $250/month

---

## 1. Role Overview

The AI Account Executive Assistant works alongside human Account Executives (AEs) to eliminate administrative burden from the sales process. It keeps deals moving by preparing opportunity summaries, drafting follow-up communications, tracking stage progression, identifying stalled deals, and ensuring no opportunity is forgotten. The AE focuses on relationships and closing; the AI handles everything else.

### Core Promise
> "Your AEs spend 100% of their time selling — not updating CRM, not writing follow-ups, not chasing their own pipeline."

---

## 2. Capabilities

### 2.1 Functional Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Opportunity Summarization | Generates up-to-date deal summaries from CRM, email, meetings | Full |
| Proposal Draft Generation | Creates first-draft proposals using templates and opportunity data | Draft (AE reviews) |
| Follow-up Email Drafting | Drafts post-meeting and post-proposal follow-up emails | Draft (AE sends) |
| Stalled Deal Detection | Flags deals with no activity beyond configurable threshold | Full |
| Stage Progression Tracking | Monitors CRM stage movement, flags stagnation | Full |
| Next Action Suggestion | Recommends next best step per opportunity | Full |
| Meeting Prep Briefing | Compiles contact history, deal status, open items before meeting | Full |
| Contract Drafting Support | Fills standard contract templates from deal data | Draft (legal reviews) |
| Competitive Intelligence Briefing | Surfaces known competitor info relevant to the deal | Full |
| Win/Loss Analysis | Analyzes closed deals for patterns and lessons | Full |
| Forecast Contribution | Contributes AI-based close probability scores to CRM | Full |

### 2.2 Extended Capabilities (Phase 2)

- Call transcript analysis: extracts action items from recorded sales calls
- Automated proposal versioning and client portal publishing
- Multi-stakeholder mapping (identify champions, blockers, influencers)
- Real-time deal health scoring (green/amber/red)
- Revenue intelligence: forecasting accuracy improvement over time

---

## 3. System Integrations

### Required
| System | Purpose | Integration Type |
|---|---|---|
| CRM | Opportunity data, contacts, activities, stages | Salesforce / HubSpot / Zoho API |
| Email | Read AE email threads, draft follow-ups | Gmail / Outlook API |
| Calendar | Meeting history, upcoming meetings | Google / Outlook Calendar API |

### Recommended
| System | Purpose | Integration Type |
|---|---|---|
| Document Management | Store proposals, contracts | Google Drive / SharePoint / S3 |
| E-Signature | Send contracts for signing | DocuSign / Adobe Sign API |
| Meeting Recording | Auto-transcription and action item extraction | Gong / Chorus / Teams / Zoom |
| Proposal Tool | Dynamic proposal generation | PandaDoc / Proposify / native |

### Optional
| System | Purpose |
|---|---|
| Revenue Intelligence | AI-powered deal analytics (Clari, Aviso) |
| CPQ Tool | Pricing configuration if product catalog complex |
| LinkedIn | Stakeholder research enrichment |

---

## 4. Workflow Definitions

### Workflow 1: Opportunity Summary (On-Demand or Scheduled)

```
TRIGGER: AE requests summary OR new meeting added to calendar
══════════════════════════════════════════════════════════════
Step 1: GATHER DATA
  Pull from CRM:
    ├── Company info, contacts, deal value, stage, close date
    ├── Last 10 activity log entries
    ├── Open tasks and overdue items
    └── Associated notes and attachments

  Pull from Email:
    ├── Last 5 threads with account contacts
    └── Extract: topics discussed, commitments made, open questions

  Pull from Calendar:
    ├── Last 3 meetings with account
    └── Next scheduled meeting

Step 2: SYNTHESIZE
  Generate structured summary:
    Company overview (1 sentence)
    Current stage and close probability
    Key stakeholders and their positions
    Main value drivers and pain points discussed
    Last interaction summary
    Open action items (by owner)
    Risks and blockers
    Recommended next action

Step 3: DELIVER
  Push to CRM as pinned note
  Send to AE via email/Slack (if configured)
  Available in deal view in tenant portal
```

### Workflow 2: Stalled Deal Detection & Recovery

```
TRIGGER: Scheduled daily job (checks all open opportunities)
══════════════════════════════════════════════════════════════
Step 1: SCAN PIPELINE
  For each open opportunity:
    Days since last activity (email, call, meeting, note)?
    Days in current stage vs avg days for this stage?
    Close date approaching with no activity?

Step 2: CLASSIFY RISK
  GREEN:  Activity ≤ 7 days ago
  AMBER:  Activity 8–21 days ago or stage stagnant > avg
  RED:    Activity > 21 days ago or close date past

Step 3: GENERATE RECOVERY SUGGESTION
  RED deal: suggest specific outreach angle
    "Last discussed [topic] on [date]. Suggest referencing [trigger event]
     or sending [relevant case study]."

Step 4: ALERT AE
  Amber: Weekly digest in deal dashboard
  Red:   Immediate alert via email/push + draft recovery email ready

Step 5: ESCALATE
  If AE does not act on RED within 3 days → alert Sales Manager
```

### Workflow 3: Post-Meeting Follow-Up Draft

```
TRIGGER: Meeting completed (calendar event ended)
══════════════════════════════════════════════════
Step 1: RETRIEVE CONTEXT
  Calendar invite: attendees, agenda, duration
  Meeting notes (from AE or auto-transcript if available)
  CRM: deal stage, previous commitments

Step 2: GENERATE DRAFT EMAIL
  Opening: reference meeting and express thanks
  Summary: 3–4 bullet points of what was discussed
  Action items: specific, owner-assigned, dated
  Next step: proposed next meeting or deliverable
  Closing: professional sign-off with AE name

Step 3: STAGE IN OUTBOX
  Draft saved in AE's email (not sent automatically)
  Notification to AE: "Your follow-up for [Company] is ready to review"
  One-click send or edit mode

Step 4: VERSION CONTROL
  All drafts stored with timestamp
  AE edits tracked (not overwritten)
```

---

## 5. Policy Configuration

```yaml
stalled_deal_policy:
  amber_threshold_days: 8
  red_threshold_days: 21
  manager_escalation_after_days: 3      # After red alert, if no AE action
  close_date_warning_days: 14           # Flag when close date within 14 days
  no_activity_types_ignored: ["crm_system_update"]

proposal_policy:
  require_ae_review_before_send: true   # Always — proposals never sent autonomously
  template_library: "approved_templates_v2"
  auto_populate_fields: ["company_name", "contact_name", "deal_value", "products"]
  legal_clauses_locked: true            # Locked sections cannot be AI-edited

follow_up_policy:
  draft_within_hours: 2                 # Draft ready 2h after meeting ends
  ae_review_required: true
  default_tone: "professional_warm"
  include_action_items: true

forecasting:
  ai_close_probability: true            # Enable AI probability score in CRM
  weight_vs_human_estimate: 0.4         # Blended: 40% AI, 60% AE input
```

---

## 6. Data Schema

```prisma
model OpportunitySummary {
  id                String   @id @default(cuid())
  tenantId          String
  opportunityId     String   // CRM opportunity ID
  companyName       String
  dealValue         Decimal?
  stage             String
  closeProbability  Float?
  daysInStage       Int?
  lastActivityDate  DateTime?
  riskLevel         String   // green | amber | red
  summaryText       Json     // structured summary fields
  openActionItems   Json?
  nextRecommendedAction String?
  generatedAt       DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@index([tenantId, opportunityId])
  @@index([tenantId, riskLevel])
  @@map("opportunity_summaries")
}

model DraftCommunication {
  id             String   @id @default(cuid())
  tenantId       String
  aeUserId       String
  opportunityId  String?
  type           String   // follow_up | proposal | contract | intro
  subject        String
  bodyDraft      String
  status         String   // draft | reviewed | sent | discarded
  sentAt         DateTime?
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt

  @@index([tenantId, aeUserId])
  @@map("draft_communications")
}
```

---

## 7. Performance Metrics (KPIs)

| KPI | Target | Measurement |
|---|---|---|
| AE Time Saved per Week | > 5 hours | Self-reported + activity log analysis |
| Deal Summary Accuracy | > 90% rated useful | AE feedback score |
| Stalled Deal Detection | 100% flagged | Deals going cold caught vs missed |
| Follow-up Draft Usage Rate | > 70% | % of drafts used (sent/edited) by AE |
| Pipeline Coverage | > 95% deals with active summary | Deals with AI summary / total open |
| Forecast Accuracy Improvement | > 10% vs AE-only | Close probability vs actual close |
| CRM Data Completeness | > 95% | Key fields populated on all opportunities |

---

## 8. Guardrails & Safety Rules

```
DEAL INTEGRITY GUARDRAILS
  ✓ Pricing and discount terms never autonomously committed — AE approval required
  ✓ Contract clauses locked — no AI modification of legal sections
  ✓ Win/Loss data anonymized before analysis (no client-identifying in insights)

COMMUNICATION GUARDRAILS
  ✓ Proposals and contracts never sent without explicit AE action
  ✓ Follow-up emails always in AE's draft — never auto-sent
  ✓ AI never communicates to client directly (assists AE only)

DATA GUARDRAILS
  ✓ Client deal data not used to train global model without consent
  ✓ Deal financials visible only to AE + manager roles
  ✓ Competitive intelligence sourced only from approved internal battlecards
```

---

## 9. Audit Trail Events

| Event | Logged Fields |
|---|---|
| `ae_assist.summary.generated` | opportunity_id, data_sources_used, timestamp |
| `ae_assist.stall.detected` | opportunity_id, risk_level, days_inactive |
| `ae_assist.stall.escalated` | opportunity_id, escalated_to, reason |
| `ae_assist.draft.created` | type, opportunity_id, ae_user_id |
| `ae_assist.draft.sent` | draft_id, sent_by, timestamp |
| `ae_assist.proposal.generated` | template_used, fields_auto_filled |
| `ae_assist.forecast.scored` | opportunity_id, ai_probability, ae_probability |

---

## 10. Acceptance Criteria

### Story 1 — AE wants instant deal summary
- ✅ Summary includes company, contacts, stage, deal value, objections, last interaction
- ✅ Generated from CRM + email + meeting data
- ✅ Missing fields explicitly flagged ("No budget confirmed")
- ✅ Refreshes automatically when new interaction occurs

### Story 2 — AE needs a follow-up email
- ✅ Draft ready within 2 hours of meeting completion
- ✅ Uses correct tone, includes action items, references deal details
- ✅ AE can edit or send with one click
- ✅ Version history stored

### Story 3 — Sales manager wants stall visibility
- ✅ All stalled deals (amber/red) visible in dashboard
- ✅ Risk level calculated by configurable thresholds
- ✅ AI suggests next action per stalled deal
- ✅ Alerts reach AE and manager within defined SLA

---

## 11. Setup Checklist

```
ACTIVATION PREREQUISITES
═════════════════════════
[ ] CRM connected (opportunity + contact + activity read/write)
[ ] Email connected for AE accounts (read-only drafting)
[ ] Calendar connected (meeting history)
[ ] Proposal templates uploaded (minimum 1 per product line)
[ ] Stall threshold configured (amber/red days)
[ ] AE user mapping: each AE linked to their CRM user
[ ] Manager notification routing configured
[ ] Approved product/pricing KB loaded for proposal auto-fill
[ ] Test opportunity run through full summary workflow
[ ] AE team briefed on draft review process
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Sales & Marketing | Role: Account Executive Assistant*
