# AI Worker: Sales Development Representative (SDR)
**Department:** Sales & Marketing
**Worker ID:** `ai-sdr`
**Version:** 1.0.0
**Subscription Tier:** Standard — $250/month

---

## 1. Role Overview

The AI SDR is a tireless pipeline builder that qualifies inbound leads, executes outbound prospecting sequences, answers pre-sales questions, and schedules discovery calls — all without human intervention. It ensures no lead falls through the cracks and that sales reps receive warm, pre-qualified meetings ready to close.

### Core Promise
> "Every lead is touched, qualified, and progressed — so your sales team only talks to people ready to buy."

---

## 2. Capabilities

### 2.1 Functional Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Inbound Lead Capture | Extracts lead details from web forms, chat, email, and social | Full |
| Lead Qualification (BANT/MEDDIC) | Scores against configurable criteria (Budget, Authority, Need, Timeline) | Full |
| Lead Scoring | Assigns hot/warm/cold status with reasoning | Full |
| CRM Auto-Update | Creates/updates lead records, activities, and stages in CRM | Full |
| Outbound Sequences | Executes multi-step email/LinkedIn outreach cadences | Full |
| Pre-Sales Q&A | Answers product questions using approved knowledge base | Full |
| Demo Scheduling | Books meetings on sales rep calendar with timezone awareness | Full |
| Lead Nurturing | Sends drip sequences to not-yet-ready leads | Full |
| Opt-out Handling | Processes unsubscribes and suppresses future outreach | Full |
| Follow-up Reminders | Re-engages prospects who went silent | Configurable |
| Competitor Mention Handling | Detects competitor mentions and routes to senior SDR / AE | Policy-gated |
| ICP Matching | Compares lead profile against Ideal Customer Profile | Full |

### 2.2 Extended Capabilities (Phase 2)

- LinkedIn Sales Navigator integration for enrichment
- Intent data integration (Bombora, G2 signals)
- Voice prospecting (AI cold call via telephony)
- Account-based outreach (all contacts at target account)
- ROI calculator presentation during pre-sales

---

## 3. System Integrations

### Required
| System | Purpose | Integration Type |
|---|---|---|
| CRM | Lead/contact management, activity logging | Salesforce / HubSpot / Zoho API |
| Email Provider | Outbound sequences, inbound handling | Gmail / Outlook API |
| Calendar | Meeting scheduling | Google Calendar / Outlook Calendar |

### Recommended
| System | Purpose | Integration Type |
|---|---|---|
| Lead Enrichment | Auto-fill company/contact details | Clearbit / Apollo / ZoomInfo API |
| Meeting Scheduler | Frictionless booking page | Calendly / native calendar widget |
| Marketing Automation | Lead source tracking, campaign attribution | HubSpot / Marketo |
| Sequence Tool | Outbound email cadence execution | Outreach / Salesloft / native |

### Optional
| System | Purpose |
|---|---|
| LinkedIn API | Profile enrichment, InMail outreach |
| Website Analytics | Visitor deanonymization (Leadfeeder) |
| Chat Widget | Inbound pre-sales conversations |

---

## 4. Workflow Definitions

### Workflow 1: Inbound Lead Qualification

```
TRIGGER: New lead from form / chat / email / import
════════════════════════════════════════════════════
Step 1: CAPTURE & ENRICH
  Extract: name, email, company, role, message
  Enrich via integration: company size, industry, revenue, tech stack
  Deduplicate against existing CRM records

Step 2: ICP MATCH
  Score against Ideal Customer Profile:
    ├── Company size: match? (e.g., 50–5000 employees)
    ├── Industry: in target list?
    ├── Geography: in serviceable region?
    ├── Role: decision-maker or influencer?
    └── Intent signals: demo request = +30pts, newsletter = +5pts

Step 3: QUALIFY (BANT)
  Budget:    Any indicator of budget allocation or ARR?
  Authority: Is contact a decision-maker?
  Need:      Problem stated matches product value prop?
  Timeline:  Active evaluation or future planning?

Step 4: ASSIGN STATUS
  Score ≥ 80 → HOT: Assign to AE, book demo immediately
  Score 50–79 → WARM: Add to nurture sequence, AI continues engagement
  Score < 50 → COLD: Monthly newsletter, low-touch nurture

Step 5: CRM UPDATE
  Create/update lead record with: score, ICP match, BANT notes, status
  Log all activities chronologically
```

### Workflow 2: Outbound Prospecting Sequence

```
TRIGGER: Target account list uploaded OR ICP lead identified
════════════════════════════════════════════════════════════
Step 1: RESEARCH TARGET
  Pull company info from enrichment
  Identify relevant trigger events: funding round, hiring surge, product launch

Step 2: PERSONALIZE OUTREACH
  Generate message referencing:
    ├── Their industry/role specific pain point
    ├── A trigger event (e.g., "Congrats on your Series B")
    └── One relevant customer success story

Step 3: EXECUTE SEQUENCE (configurable cadence)
  Day 1:  Email 1 — Value-first introduction
  Day 4:  Email 2 — Problem-focused follow-up
  Day 8:  LinkedIn connection request (if integrated)
  Day 11: Email 3 — Social proof / case study
  Day 15: Email 4 — Break-up email / final ask

Step 4: RESPOND TO REPLIES
  Positive reply → Offer calendar link, book meeting
  Objection → Handle using approved objection library
  Not interested → Acknowledge, suppress for 90 days
  No reply after Day 15 → Mark as unresponsive, park in CRM

Step 5: LOG ALL TOUCHPOINTS
  Every email sent/opened/clicked → logged in CRM
  Reply sentiment classified
  Sequence outcome recorded
```

### Workflow 3: Demo Scheduling

```
TRIGGER: Lead requests demo OR meets hot lead threshold
═══════════════════════════════════════════════════════
Step 1: MATCH TO SALES REP
  By territory, industry expertise, language, availability

Step 2: PRESENT AVAILABILITY
  Pull 3–5 open slots from calendar
  Convert to lead's timezone
  Offer via email or chat

Step 3: CONFIRM BOOKING
  Send calendar invite (with video link: Zoom / Teams / Meet)
  Include: agenda, prep questions, product overview link
  Log in CRM: meeting type, attendees, expected deal size

Step 4: REMIND
  24h before: reminder to lead
  1h before: reminder to sales rep with lead briefing
  Post-meeting: follow-up task created in CRM
```

---

## 5. Policy Configuration

```yaml
qualification_criteria:
  icp_minimum_score: 50
  auto_assign_to_ae_above: 80
  bant_weight:
    budget: 30
    authority: 25
    need: 30
    timeline: 15

outreach_policy:
  max_sequence_emails: 5
  min_days_between_touches: 3
  blackout_hours: "20:00-08:00"      # No emails outside business hours
  unsubscribe_suppression_days: 365
  competitor_mention_escalate: true

scheduling_policy:
  meeting_buffer_minutes: 15          # Buffer between meetings
  advance_booking_hours: 24           # No same-day bookings
  timezone_detection: true
  preferred_slots: ["Tue-Thu 10:00-16:00"]

communication:
  tone: "professional_consultative"
  personalization_level: "high"       # high | medium | template
  max_email_length_words: 150
  use_prospect_first_name: true
```

---

## 6. Data Schema

```prisma
model LeadRecord {
  id               String   @id @default(cuid())
  tenantId         String
  contactName      String
  email            String
  company          String?
  role             String?
  source           String   // form | chat | email | import | outbound
  icpScore         Int?
  bantScore        Int?
  status           String   // hot | warm | cold | disqualified | converted
  sequenceId       String?
  sequenceStep     Int?
  meetingBooked    Boolean  @default(false)
  meetingAt        DateTime?
  assignedAeId     String?
  enrichmentData   Json?
  lastContactedAt  DateTime?
  createdAt        DateTime @default(now())
  updatedAt        DateTime @updatedAt

  @@index([tenantId, status])
  @@index([tenantId, email])
  @@map("lead_records")
}

model OutreachActivity {
  id          String   @id @default(cuid())
  tenantId    String
  leadId      String
  type        String   // email_sent | email_opened | email_clicked | reply | call | linkedin
  channel     String
  subject     String?
  sentimentScore Float?
  outcome     String?  // positive | negative | neutral | no_response
  createdAt   DateTime @default(now())

  @@index([tenantId, leadId])
  @@map("outreach_activities")
}
```

---

## 7. Performance Metrics (KPIs)

| KPI | Target | Measurement |
|---|---|---|
| Lead Response Time | < 5 minutes (inbound) | Time from lead capture to first touch |
| Lead Qualification Rate | > 60% of inbound leads scored | % of leads with completed BANT |
| Demo Booked Rate | > 25% of hot leads | Demos scheduled / hot leads |
| Email Open Rate | > 40% | Outbound sequence emails |
| Reply Rate | > 12% | Outbound sequence replies |
| Meeting Show Rate | > 85% | Booked meetings actually attended |
| Pipeline Generated (MQL→SQL) | Per tenant target | Value of SQLs created by AI SDR |
| CRM Data Quality | > 95% complete | Lead records with all key fields populated |

---

## 8. Guardrails & Safety Rules

```
COMMUNICATION GUARDRAILS
  ✓ Only send from approved sender domains
  ✓ Never impersonate a human sales rep by name (unless explicitly configured)
  ✓ Always include unsubscribe option in outbound emails
  ✓ Never make unauthorized pricing commitments
  ✓ Never invent product features or capabilities not in approved KB
  ✓ Competitor comparisons only using approved battlecards

LEGAL / COMPLIANCE
  ✓ GDPR / CAN-SPAM / CASL compliance: consent-based outreach only
  ✓ Opt-out processed within 10 seconds of receipt
  ✓ Suppression list checked before every send
  ✓ No outreach to contacts in suppressed/blocked lists

SCHEDULING GUARDRAILS
  ✓ Never double-book sales rep calendar
  ✓ Never book outside business hours without explicit lead request
  ✓ Always send confirmation and reminder for booked meetings
```

---

## 9. Audit Trail Events

| Event | Logged Fields |
|---|---|
| `sdr.lead.captured` | source, contact_id, timestamp |
| `sdr.lead.enriched` | enrichment_provider, fields_added |
| `sdr.lead.scored` | icp_score, bant_score, status_assigned |
| `sdr.email.sent` | lead_id, sequence_step, subject_hash |
| `sdr.email.reply_received` | lead_id, sentiment, intent_detected |
| `sdr.meeting.scheduled` | lead_id, ae_id, slot, timezone |
| `sdr.lead.escalated` | lead_id, reason, escalated_to |
| `sdr.lead.disqualified` | lead_id, reason |
| `sdr.optout.processed` | email_hash, timestamp |

---

## 10. Acceptance Criteria

### Story 1 — Inbound lead qualification
- ✅ AI captures lead details from all configured sources
- ✅ Lead is enriched, scored, and status assigned within 5 minutes
- ✅ CRM updated automatically with full qualification notes
- ✅ Hot leads immediately assigned and notified to AE

### Story 2 — Pre-sales questions answered
- ✅ AI responds using only approved product knowledge
- ✅ Unapproved or uncertain answers trigger escalation
- ✅ Demo booking offered at appropriate moment in conversation
- ✅ Full conversation history stored in CRM

### Story 3 — Demo meeting scheduled
- ✅ Calendar availability pulled in real-time
- ✅ Timezone conversion accurate for international prospects
- ✅ Meeting invite created with agenda and video link
- ✅ CRM activity logged with meeting details

### Story 4 — Lead nurture (not-yet-ready)
- ✅ Warm leads enter appropriate nurture sequence
- ✅ Cadence respects blackout hours and opt-out rules
- ✅ Lead status auto-updates when engagement signals change
- ✅ Long-cycle leads not lost — re-surfaced after trigger events

---

## 11. Setup Checklist

```
ACTIVATION PREREQUISITES
═════════════════════════
[ ] CRM connected (lead/contact write access confirmed)
[ ] Email account connected (outbound + inbound read)
[ ] Calendar connected (sales rep availability)
[ ] ICP definition uploaded (company size, industry, role criteria)
[ ] Product knowledge base uploaded (FAQ, features, pricing scope)
[ ] Objection handling library uploaded
[ ] Outreach sequence templates configured (or defaults used)
[ ] Qualification scoring weights set (BANT/MEDDIC)
[ ] AE assignment rules defined (by territory or round-robin)
[ ] Compliance: opt-out list imported, GDPR mode configured
[ ] Test run: 5 simulated leads validated end-to-end
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Sales & Marketing | Role: Sales Development Representative*
