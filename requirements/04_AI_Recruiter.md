# AI Worker: Recruiter
**Department:** HR & People Operations
**Worker ID:** `ai-recruiter`
**Version:** 1.0.0
**Subscription Tier:** Standard — $250/month

---

## 1. Role Overview

The AI Recruiter manages the full top-of-funnel recruitment process: screening incoming applications, ranking candidates against job requirements, coordinating interview scheduling, maintaining candidate communication, and feeding qualified shortlists to hiring managers. It eliminates the manual burden of high-volume recruiting while ensuring every candidate gets a professional experience.

### Core Promise
> "From hundreds of applicants to a ranked shortlist — in hours, not weeks."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Resume Parsing | Extracts qualifications, experience, skills from CVs | Full |
| Candidate Ranking | Scores applicants against JD criteria with explainable logic | Full |
| Duplicate Detection | Identifies repeat applicants across roles | Full |
| Mandatory Requirement Check | Flags missing must-have qualifications | Full |
| Candidate Communication | Acknowledgments, status updates, rejections | Full |
| Interview Scheduling | Coordinates interviewer calendars, sends invites | Full |
| Rescheduling Handling | Manages reschedule requests from candidates/interviewers | Full |
| ATS Data Entry | Populates applicant tracking system with structured data | Full |
| Job Board Posting | Publishes job postings to configured boards | Full |
| Offer Letter Drafting | Generates offer letters from approved templates | Draft (HR approves) |
| Diversity Signal Awareness | Removes bias indicators before scoring (blind screening mode) | Configurable |
| Reference Check Initiation | Sends reference check requests to referees | Full |

### Extended Capabilities (Phase 2)
- Video interview AI pre-screening (async video analysis)
- Passive candidate sourcing from LinkedIn (with integration)
- Predictive retention scoring based on candidate profile patterns
- Employer brand response templates for negative Glassdoor reviews

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| ATS (Applicant Tracking System) | Candidate records, stage management |
| Email | Candidate communication |
| Calendar | Interviewer scheduling |

### Recommended
| System | Purpose |
|---|---|
| HRMS | New hire onboarding handoff |
| LinkedIn / Job Boards | Job posting distribution |
| Document Storage | CV archive, offer letter storage |
| E-Signature | Offer letter acceptance |

---

## 4. Workflow Definitions

### Workflow 1: Application Screening & Ranking

```
TRIGGER: New application submitted via ATS / email / job board
════════════════════════════════════════════════════════════════
Step 1: PARSE RESUME
  Extract: name, contact, education, experience (years + companies),
  skills, certifications, languages, employment gaps

Step 2: SCORE AGAINST JD
  Mandatory requirements (pass/fail):
    ├── Years of experience ≥ minimum?
    ├── Required degree / certification present?
    └── Mandatory skills present?

  Scoring (weighted):
    ├── Role-relevant experience: 40 pts
    ├── Required skills match: 30 pts
    ├── Educational fit: 15 pts
    └── Additional value-adds (certs, awards): 15 pts

Step 3: BLIND SCREENING (if enabled)
  Redact: name, photo indicators, gender pronouns, graduation year
  before scoring to reduce unconscious bias

Step 4: RANK & SHORTLIST
  Top 20% → Shortlist (hiring manager review)
  20–60% → Waitlist (activate if shortlist depleted)
  Bottom 40% → Reject (with graceful notification)

Step 5: ATS UPDATE
  Create candidate record with score, ranking, notes
  Flag missing mandatory fields
  Send acknowledgment to candidate
```

### Workflow 2: Interview Scheduling

```
TRIGGER: Hiring manager approves candidate for interview
══════════════════════════════════════════════════════════
Step 1: DETERMINE INTERVIEW PANEL
  Pull interview panel from job template
  Check each interviewer's calendar availability

Step 2: OFFER SLOTS TO CANDIDATE
  Email with 3–5 timezone-aware options
  Include: interviewers, format (video/in-person), duration, prep tips

Step 3: CONFIRM & SEND INVITES
  On candidate selection:
    ├── Calendar invites to all parties
    ├── Video link (Zoom/Teams/Meet) if virtual
    └── Preparation guide attached

Step 4: MANAGE RESCHEDULES
  Candidate requests reschedule → offer new slots
  Interviewer drops out → find replacement or reschedule
  No-show → follow-up within 1 hour

Step 5: POST-INTERVIEW
  Feedback form sent to interviewers
  Status update sent to candidate (pending outcome)
```

---

## 5. Policy Configuration

```yaml
screening_policy:
  blind_mode: false                   # Enable to redact identifying info
  mandatory_knockout_fields:
    - "minimum_years_experience"
    - "required_certifications"
  scoring_weights:
    experience: 40
    skills: 30
    education: 15
    extras: 15
  shortlist_top_percent: 20

communication_policy:
  acknowledgment_within_hours: 2
  rejection_notification_days: 14     # Delay rejection until role is filled
  rejection_tone: "compassionate_professional"
  offer_requires_hr_approval: true

scheduling_policy:
  candidate_response_window_days: 3
  max_reschedules: 2
  no_show_follow_up_hours: 1
  timezone_detection: true
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| Time-to-Shortlist | < 4 hours from application close |
| Screening Accuracy | > 85% hiring manager agreement with shortlist |
| Candidate Communication SLA | 100% acknowledged within 2 hours |
| Interview Scheduling Time | < 24 hours from shortlist approval |
| Duplicate Detection Rate | > 99% |
| Offer Acceptance Rate (after AI screens) | > 75% (quality signal) |

---

## 7. Guardrails

```
✓ Mandatory requirements are always pass/fail — never scored around
✓ Offer letters never sent without explicit HR/hiring manager approval
✓ Rejection emails never sent until role is confirmed filled (prevent premature rejections)
✓ Salary/compensation discussions always escalated to human HR
✓ Legal compliance: no questions about age, nationality, religion in screening criteria
✓ Candidate data retained per data protection policy (e.g., 12 months then purged)
```

---

## 8. Acceptance Criteria

- ✅ AI ranks applicants with explainable scoring (not black-box)
- ✅ Required vs preferred skills clearly distinguished in results
- ✅ Shortlist visible in recruiter dashboard with reasoning
- ✅ Timely communication to all candidates at each stage
- ✅ Interview scheduling completed within 24h of approval
- ✅ Offer letter generated from approved template, not sent without sign-off

---

## 9. Setup Checklist

```
[ ] ATS connected (read + write)
[ ] Email configured for candidate communication
[ ] Interviewer calendars connected
[ ] Job description templates uploaded (per role type)
[ ] Scoring weights configured per department
[ ] Rejection email templates approved by HR
[ ] Blind screening mode decision made per role
[ ] Offer letter templates locked and loaded
[ ] Test: 10 sample applications processed and reviewed
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: HR & People Operations | Role: Recruiter*
