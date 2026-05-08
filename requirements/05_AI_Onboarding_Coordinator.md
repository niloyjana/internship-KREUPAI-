# AI Worker: Onboarding Coordinator
**Department:** HR & People Operations
**Worker ID:** `ai-onboarding-coordinator`
**Version:** 1.0.0
**Subscription Tier:** Standard — $230/month

---

## 1. Role Overview

The AI Onboarding Coordinator manages the new employee journey from the moment an offer is accepted through to the end of probation. It orchestrates document collection, system access provisioning, policy acknowledgments, orientation scheduling, and checklist tracking — ensuring every new hire has a complete, consistent, and welcoming experience without any HR admin manually chasing steps.

### Core Promise
> "Every new hire arrives on Day 1 fully prepared, fully equipped, and already feeling at home."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Welcome Communication | Sends personalized welcome messages post-offer accept | Full |
| Document Request & Collection | Requests and tracks required joining documents | Full |
| Policy Acknowledgment Tracking | Sends policies, tracks e-sign completion | Full |
| Checklist Orchestration | Creates and monitors role-specific onboarding checklists | Full |
| IT Access Request Trigger | Initiates system access workflows per role template | Full |
| Equipment Request | Triggers equipment provisioning (laptop, phone, access cards) | Full |
| Orientation Scheduling | Schedules Day 1 orientation, manager intro, team meetings | Full |
| Buddy Assignment Notification | Notifies assigned buddy with context and schedule | Full |
| Probation Task Tracking | Sends 30/60/90-day task reminders and checkpoints | Full |
| HR Dashboard Visibility | Real-time onboarding status visible to HR team | Full |
| Offboarding Trigger (if needed) | Pre-join withdrawal: graceful offboarding process | Full |
| Multi-Entity Support | Different onboarding flows per company entity/country | Full |

### Extended Capabilities (Phase 2)
- Digital ID verification and background check integration
- Benefits enrollment wizard (health, pension, leave)
- Org chart auto-update on new hire arrival
- 30/60/90 day manager feedback collection
- Culture & pulse survey dispatch at milestones

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| HRMS | Employee record creation, org structure |
| Email | All onboarding communications |
| Document Management | Policy documents, signed form storage |
| E-Signature | Policy and contract acknowledgment |

### Recommended
| System | Purpose |
|---|---|
| IT Service Management | Access request tickets (laptop, email, applications) |
| Calendar | Orientation and meeting scheduling |
| Background Check Provider | Identity / criminal record verification |
| Payroll System | Bank details, tax forms collection |

---

## 4. Workflow Definitions

### Workflow 1: Pre-Join Journey (Offer Accept → Day 1)

```
TRIGGER: Offer accepted in ATS / HRMS
══════════════════════════════════════
T-30 days (or immediately if < 30 days):
  → Send welcome email with portal login
  → Checklist created (role-specific template)
  → Document request: ID, bank details, educational certificates

T-21 days:
  → Follow-up if documents missing
  → Policy documents sent for e-sign (handbook, IT policy, NDA)
  → IT access request initiated (email, laptop, core apps)

T-14 days:
  → Confirm document collection complete
  → Orientation schedule sent (Day 1 agenda)
  → Manager notified with new hire profile

T-7 days:
  → Equipment provisioning status check
  → Building access / parking instructions sent
  → Buddy assigned and notified

T-1 day:
  → "See you tomorrow" email with Day 1 logistics
  → Emergency contacts collected

Day 1:
  → Welcome message with full Day 1 schedule
  → Manager prompt: "Your new team member arrives today — here's their profile"
  → HR checklist: confirm physical arrival
```

### Workflow 2: Post-Join Milestone Tracking (30/60/90 Days)

```
TRIGGER: Employee start date confirmed
══════════════════════════════════════
Day 30:
  → Check: all systems access confirmed?
  → Prompt: probation goal review with manager
  → Send 30-day check-in survey to new hire

Day 60:
  → Mid-probation reminder to manager
  → Training completion check
  → Flag any outstanding tasks

Day 90:
  → Probation end review prompt to manager
  → Final checklist: permanent employee transition
  → Benefits enrollment reminder (if applicable)
  → Celebrate milestone: congratulations message to new hire
```

### Workflow 3: Escalation & Exception Handling

```
TRIGGER: Checklist item overdue OR blocker detected
════════════════════════════════════════════════════
Scenario A — Document missing 5 days before start:
  → Escalate to HR manager with list of missing items
  → Send urgent reminder to new hire

Scenario B — IT access not provisioned by Day 1:
  → Alert IT manager + HR with specific access list
  → Track and update until resolved

Scenario C — New hire no-show Day 1:
  → Alert HR immediately
  → Pause all onboarding workflows
  → Await HR decision (proceed or offboard)
```

---

## 5. Policy Configuration

```yaml
onboarding_checklist:
  templates_by_role:
    - role: "engineer"
      items: ["laptop", "github_access", "jira_access", "vpn_setup", "codebase_intro"]
    - role: "finance"
      items: ["erp_access", "bank_system_access", "finance_policy_sign", "chart_of_accounts"]
    - role: "default"
      items: ["email", "hr_system", "building_access", "handbook_sign", "id_badge"]

  deadline_policy:
    documents_due_days_before_start: 14
    policy_sign_due_days_before_start: 7
    it_request_days_before_start: 10

escalation_policy:
  overdue_document_escalate_days: 3
  it_failure_escalate_hours: 24
  probation_reminder_days_before: 14

communication:
  welcome_tone: "warm_enthusiastic"
  reminder_tone: "friendly_urgent"
  manager_briefing: true
  buddy_notification: true
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| Day 1 Readiness Rate | > 98% (all access + equipment ready) |
| Document Collection Completion | 100% before start date |
| Policy Sign-off Rate | 100% within first week |
| Onboarding ENPS (Employee NPS) | > 60 |
| Time Saved per Hire (vs manual) | > 8 hours HR admin |
| 90-Day Checklist Completion | > 95% |

---

## 7. Guardrails

```
✓ Salary and compensation details never communicated by AI — always HR
✓ Offer letters and employment contracts not generated autonomously
✓ Background check results seen only by authorized HR personnel
✓ No onboarding communication sent if offer acceptance is unconfirmed
✓ Probation outcome decisions always made by humans — AI only tracks/reminds
✓ Personal data (ID copies, bank details) encrypted at rest, not exposed in AI context
```

---

## 8. Acceptance Criteria

- ✅ Onboarding checklist is role-specific and auto-created on hire confirmation
- ✅ AI sends reminders automatically — HR not required to chase manually
- ✅ IT access requests triggered with correct role-based access template
- ✅ HR dashboard shows real-time completion status per new hire
- ✅ New hire questions answered via chat/email from onboarding knowledge base
- ✅ Escalations fired for blockers before Day 1 — no surprises

---

## 9. Setup Checklist

```
[ ] HRMS connected (new hire triggers + employee record)
[ ] Email configured for onboarding communications
[ ] Document management system connected
[ ] E-signature tool integrated
[ ] IT service management connected (access request creation)
[ ] Checklist templates created per role (minimum: default template)
[ ] Policy documents uploaded for e-sign distribution
[ ] Manager notification workflows configured
[ ] Probation milestones (30/60/90) enabled
[ ] Test: sample new hire run through full pre-join workflow
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: HR & People Operations | Role: Onboarding Coordinator*
