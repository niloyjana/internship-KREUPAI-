# ADWP UI Screen Specifications
## Frontend Screen Design — AI Digital Workforce Platform
**File:** `docs/architecture/ui-screen-specifications.md`
**Version:** 1.0.0

---

> This document defines layout, components, data requirements, and interaction patterns
> for the 12 most critical screens. Frontend engineers use this to build components;
> backend engineers use this to understand what data each screen consumes from the API.

---

## Design System Foundation

```
DESIGN TOKENS
══════════════
Primary Blue:     #2563EB    (actions, links, agent active state)
Success Green:    #16A34A    (completed, healthy)
Warning Amber:    #D97706    (pending, escalation)
Danger Red:       #DC2626    (failed, critical, blocked)
Neutral 50:       #F8FAFC    (page background)
Neutral 900:      #0F172A    (primary text)

TYPOGRAPHY
  Heading XL:   32px / 700 weight
  Heading L:    24px / 600 weight
  Heading M:    18px / 600 weight
  Body:         14px / 400 weight
  Caption:      12px / 400 weight
  Mono:         13px / 400 (code, IDs, logs)

SPACING GRID: 4px base unit
BORDER RADIUS: 8px (cards), 6px (inputs), 999px (badges/pills)

COMPONENT LIBRARY: shadcn/ui (Radix primitives + Tailwind)
ICONS: Lucide React
CHARTS: Recharts
```

---

## Screen 1: Main Dashboard (`/dashboard`)

**Purpose:** Single-screen situational awareness for tenant admin.
**Primary User:** Tenant Admin, Department Manager
**API Calls:** `GET /v1/analytics/dashboard`, `GET /v1/workflows/escalations?status=OPEN`, `GET /v1/workflows/human-tasks?status=PENDING&assignedTo=me`

### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HEADER: Logo | "Good morning, Sarah" | Search | Notifications (badge) │
├──────────┬──────────────────────────────────────────────────────────────┤
│          │                                                               │
│  SIDEBAR │  ┌─── KPI CARDS ROW ───────────────────────────────────────┐│
│  (fixed) │  │  Active    Tasks     Pending    Cost        Escal.      ││
│          │  │  Agents    Today     Approvals  Today       Open        ││
│  Dashboard│  │  7/9       312       12 🔴     $7.42       5 🟡        ││
│  Workforce│  └──────────────────────────────────────────────────────────┘│
│  Tasks    │                                                               │
│  Integr.  │  ┌─── AGENT STATUS GRID (2x4 or 3x3) ──────────────────────┐│
│  Analytics│  │  [AP Officer]    [Recruiter]    [Support Agent]          ││
│  Billing  │  │  🟢 Working      🟡 Escalating  🟢 Active               ││
│  Settings │  │  47 tasks today  2 pending      128 resolved             ││
│          │  │                                                            ││
│          │  │  [AR Officer]    [Compliance]   [SDR]    [GL Analyst]    ││
│          │  │  🟢 Active       🟢 Active      🟢 Active 🔵 Idle        ││
│          │  └──────────────────────────────────────────────────────────┘│
│          │                                                               │
│          │  ┌─── PENDING APPROVALS ──────────┐ ┌─── LIVE ACTIVITY ─────┐│
│          │  │  ⚠ Refund $520 — Support Agent │ │  AP Officer           ││
│          │  │  ⚠ Invoice hold — AP Officer   │ │  Matched INV-1234     ││
│          │  │  ⚠ Offer letter — Recruiter    │ │  2s ago               ││
│          │  │  [View all 12 →]               │ │                       ││
│          │  │                                │ │  Recruiter            ││
│          │  │                                │ │  Shortlisted 4/28     ││
│          │  │                                │ │  1m ago               ││
│          │  └────────────────────────────────┘ └───────────────────────┘│
└──────────┴──────────────────────────────────────────────────────────────┘
```

### Component Specs

**KPI Card:**
- Value (large, bold)
- Label (caption)
- Change vs yesterday (green ↑ / red ↓ with %)
- Color border: red if threshold breached

**Agent Status Card:**
- Agent name + department pill
- Status badge: Working (blue pulse) / Active (green) / Idle (grey) / Escalating (amber pulse)
- Today's task count
- Click → navigate to `/workforce/{agentId}`

**Pending Approvals Panel:**
- Max 5 visible, "View all N" link
- Each row: severity icon, description, agent name, time ago
- Click → opens task drawer (no navigation)

**Live Activity Feed:**
- Real-time via WebSocket
- Auto-scrolling, newest on top
- Max 20 events visible
- Each: agent name, action summary, time ago
- Completed = green check, Failed = red X

---

## Screen 2: Workforce Catalog (`/workforce/catalog`)

**Purpose:** Browse and subscribe to AI workers.
**API Calls:** `GET /v1/agents/catalog`, `GET /v1/subscriptions`

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Workforce  /  Catalog                                                  │
│  "Subscribe to AI workers for your team"                                │
│                                                                         │
│  [Department Filter Pills: All | Customer | Sales | HR | Finance | ... ]│
│                                                                         │
│  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐  │
│  │ 👤 AP Officer       │ │ 👤 AR Officer       │ │ 👤 GL Analyst       │  │
│  │ Finance & Proc.     │ │ Finance & Proc.     │ │ Finance & Proc.     │  │
│  │ ─────────────────  │ │ ─────────────────  │ │ ─────────────────  │  │
│  │ Invoice processing, │ │ Collections,        │ │ Journal entries,    │  │
│  │ PO matching,        │ │ aging analysis,     │ │ anomaly detection,  │  │
│  │ duplicate detection │ │ payment prediction  │ │ close management    │  │
│  │                    │ │                    │ │                    │  │
│  │ Required:          │ │ Required:          │ │ Required:          │  │
│  │ ✓ ERP  ✓ Email     │ │ ✓ ERP  ✓ Email     │ │ ✓ ERP              │  │
│  │                    │ │                    │ │                    │  │
│  │ $300/month          │ │ $300/month          │ │ $300/month          │  │
│  │ [✓ Subscribed]      │ │ [+ Subscribe]       │ │ [+ Subscribe]       │  │
│  └────────────────────┘ └────────────────────┘ └────────────────────┘  │
│                                                                         │
│  Bundle Discount: Subscribe 3+ agents → 15% off. You have 6 agents.    │
│  Bundle discount applied: -$450/month                                   │
└────────────────────────────────────────────────────────────────────────┘
```

### Interaction: Subscribe Flow

```
Click [+ Subscribe]
  → Confirm modal:
    "Subscribe to AI AP Officer — $300/month
     Required integrations: ERP, Email
     [Cancel]  [Subscribe & Configure →]"
  → On confirm: POST /v1/subscriptions/agents
  → Redirect to /workforce/{agentId}/setup (configuration wizard)
```

---

## Screen 3: Agent Profile (`/workforce/{agentId}`)

**Purpose:** Full agent performance view + configuration access.
**API Calls:** `GET /v1/agents/{agentId}/config`, `GET /v1/agents/{agentId}/status`, `GET /v1/analytics/agents/{agentId}/performance`

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Workforce / AP Officer                           [Pause Agent] [Config]│
│                                                                         │
│  👤 AI Accounts Payable Officer      🟢 WORKING                         │
│  Finance & Procurement               Last active: 2 minutes ago         │
│                                                                         │
│  ┌─── TODAY ─────────────────────────────────────────────────────────┐  │
│  │  92 Invoices   8 Escalated   2 On Hold   $22.40 Saved (discounts) │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── PERFORMANCE (30 days) ─────────────────────┐ ┌─── ACTIVITY ───┐  │
│  │  [Line chart: tasks per day]                  │ │ INV-1234       │  │
│  │                                               │ │ ✓ Matched      │  │
│  │  Avg processing time: 14.2s                   │ │ 2m ago         │  │
│  │  Straight-through rate: 74%                   │ │                │  │
│  │  Escalation rate: 4.2%                        │ │ INV-1233       │  │
│  │  Duplicate caught: 3                          │ │ ⚠ On Hold      │  │
│  └───────────────────────────────────────────────┘ │ No PO found    │  │
│                                                    │ 5m ago         │  │
│  ┌─── INTEGRATIONS ──────────────────────────────┐ └────────────────┘  │
│  │  ✅ SAP ERP          Connected                │                     │
│  │  ✅ AP Inbox (Gmail) Connected                │                     │
│  │  ⚠️  Vendor Portal   Token expiring in 2 days  │                     │
│  └────────────────────────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 4: Task Live Queue (`/tasks/live`)

**Purpose:** Real-time view of all active and pending tasks.
**API Calls:** `GET /v1/workflows/executions?status=RUNNING`, WebSocket subscription

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Tasks / Live Queue               [Filter: Agent ▼] [Status ▼]         │
│                                                                         │
│  ● 4 RUNNING   ○ 12 PENDING   ✓ 287 TODAY   ✗ 3 FAILED                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ RUNNING                                                         │   │
│  ├──────┬─────────────────────────────┬──────────┬────────┬───────┤   │
│  │AGENT │ TASK                        │ STEP     │ TIME   │STATUS │   │
│  ├──────┼─────────────────────────────┼──────────┼────────┼───────┤   │
│  │AP    │ Processing INV-1234 ($2,400)│ 3/5 PO   │ 14s    │●      │   │
│  │SDR   │ Qualifying: john@techco.io  │ 2/4 Score│ 8s     │●      │   │
│  │Recr. │ Screening: 24 applications  │ 12/24    │ 4m 20s │●      │   │
│  │AR    │ Dunning run: 47 invoices    │ 22/47    │ 1m 12s │●      │   │
│  ├──────┴─────────────────────────────┴──────────┴────────┴───────┤   │
│  │ PENDING HUMAN APPROVAL (12)                                     │   │
│  ├──────┬─────────────────────────────┬──────────┬────────┬───────┤   │
│  │AGENT │ TASK                        │ PRIORITY │ DUE    │ACTION │   │
│  ├──────┼─────────────────────────────┼──────────┼────────┼───────┤   │
│  │Supp. │ Refund $520 — Maria K.      │ 🔴 HIGH  │ 2h 14m │[Review│   │
│  │AP    │ Invoice on hold — ACME      │ 🟡 MED   │ 4h 00m │[Review│   │
│  │Recr. │ Offer letter — Ali Hassan   │ 🟡 MED   │ 6h 30m │[Review│   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 5: Task Detail (`/tasks/{taskId}`)

**Purpose:** Full execution trace for any completed or active task.
**API Calls:** `GET /v1/workflows/executions/{executionId}`, `GET /v1/workflows/executions/{executionId}/steps`

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Tasks / INV-1234 Processing                           [Export Audit]   │
│                                                                         │
│  AI Accounts Payable Officer   ✓ COMPLETED   14.2 seconds              │
│  Triggered by: invoice@email.com   10 March 2026 14:32:18              │
│                                                                         │
│  ┌─── WORKFLOW TIMELINE ──────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  ✓ Step 1: Capture & Extract          0.8s    [Details ▼]         │ │
│  │    Vendor: ACME Corp | Amount: $2,400 | Confidence: 98%           │ │
│  │                                                                    │ │
│  │  ✓ Step 2: Validate Vendor            0.2s    [Details ▼]         │ │
│  │    Matched vendor master: VND-0042                                 │ │
│  │                                                                    │ │
│  │  ✓ Step 3: Duplicate Check            0.1s    [Details ▼]         │ │
│  │    No duplicates found (90-day scan)                               │ │
│  │                                                                    │ │
│  │  ✓ Step 4: 3-Way Matching             2.1s    [Details ▼]         │ │
│  │    PO-4421 matched | GRN-0091 matched | Variance: 0%              │ │
│  │                                                                    │ │
│  │  ✓ Step 5: Payment Batch              0.4s    [Details ▼]         │ │
│  │    Added to batch BATCH-2026-03-14                                 │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── AUDIT TRAIL ────────────────────────────────────────────────────┐ │
│  │  14:32:18.000  SYSTEM   Execution started                         │ │
│  │  14:32:18.812  AI_AGENT Invoice captured from email                │ │
│  │  14:32:19.034  AI_AGENT Vendor validated: VND-0042                 │ │
│  │  14:32:19.142  AI_AGENT No duplicate detected                      │ │
│  │  14:32:21.264  AI_AGENT 3-way match: PASS (0% variance)           │ │
│  │  14:32:21.668  AI_AGENT Added to payment batch BATCH-2026-03-14   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 6: Human Task Resolution (`/tasks/queue` — drawer overlay)

**Purpose:** Allow humans to approve, reject, or modify agent decisions.
**API Calls:** `GET /v1/workflows/human-tasks/{taskId}`, `POST /v1/workflows/human-tasks/{taskId}/resolve`

### Drawer Layout

```
┌─── TASK REVIEW DRAWER (slides in from right, 480px wide) ─────────────┐
│                                                        [×] Close        │
│  ⚠ APPROVAL REQUIRED                           🔴 HIGH PRIORITY        │
│  Customer Refund Request — Maria Konstantinou                           │
│  Assigned to: You   |   Due in: 2h 14m   |   SLA: 4 hours             │
│                                                                         │
│  ┌─── CONTEXT (what the agent found) ─────────────────────────────────┐│
│  │  Customer: Maria Konstantinou (VIP)                                ││
│  │  Order: ORD-9912 | $520.00 | Placed: Feb 28, 2026                 ││
│  │  Order Status: Delivered (Mar 3, 2026)                            ││
│  │  Refund Reason: "Product defective on arrival"                    ││
│  │  Previous refunds: 0 in last 12 months                            ││
│  │  CRM flag: VIP Customer (Gold tier)                               ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  ┌─── AI RECOMMENDATION ──────────────────────────────────────────────┐│
│  │  💡 Recommend: APPROVE                                             ││
│  │  Reason: Within 30-day window. VIP customer. First refund.        ││
│  │  Amount $520 exceeds auto-approve limit ($100).                   ││
│  │  Policy: Full refund appropriate for defective items.             ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  Decision Note (optional):                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Approved. VIP customer, valid defect claim.                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [✓ Approve Full Refund]  [✗ Reject]  [✏ Modify Amount]  [→ Reassign]  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 7: Integrations (`/integrations`)

**Purpose:** Connect and manage external system integrations.
**API Calls:** `GET /v1/integrations/connections`, `GET /v1/integrations/catalog`

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Integrations                              [+ Add Integration]          │
│                                                                         │
│  ┌─── CONNECTED (4) ──────────────────────────────────────────────────┐│
│  │                                                                    ││
│  │  [HubSpot]  ✅ Connected  Last sync: 2 min ago  [Settings] [Test] ││
│  │  Used by: SDR, AE Assistant                                       ││
│  │                                                                    ││
│  │  [SAP ERP]  ✅ Connected  Last sync: 5 min ago  [Settings] [Test] ││
│  │  Used by: AP Officer, GL Analyst, Procurement                     ││
│  │                                                                    ││
│  │  [Gmail AP] ✅ Connected  Last sync: 1 min ago  [Settings] [Test] ││
│  │  Used by: AP Officer                                              ││
│  │                                                                    ││
│  │  [Outlook]  ⚠ Token expiring in 2 days  [Reconnect]              ││
│  │  Used by: Support Agent, Executive Assistant                      ││
│  │                                                                    ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  ┌─── REQUIRED (not connected) ────────────────────────────────────────┐│
│  │  AP Officer requires: Vendor Portal (optional) — [Connect]         ││
│  │  Recruiter requires: ATS — [Connect]                               ││
│  └────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 8: Analytics — Agent Performance (`/analytics/performance`)

**Purpose:** KPI deep-dive for each agent.
**API Calls:** `GET /v1/analytics/agents/{agentId}/performance?from=...&to=...`

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Analytics  /  Performance         [Agent: AP Officer ▼] [Mar 2026 ▼] │
│                                                                         │
│  ┌── HEADLINE KPIS ─────────────────────────────────────────────────┐  │
│  │  1,847 Tasks   74% STP Rate   4.2% Escalation   14.2s Avg Time  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌── TASKS PER DAY (bar chart) ────────────────────────────────────┐   │
│  │  [Bar chart showing daily task volume, colored by: ✓/⚠/✗]      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌── ESCALATION BREAKDOWN ────────┐ ┌── COST TREND ─────────────────┐  │
│  │  Pie: Reason types             │ │  Line: daily LLM cost         │  │
│  │  No PO: 42%                    │ │  Mar avg: $0.024/task         │  │
│  │  Variance: 31%                 │ │  vs $0.031 last month ↓       │  │
│  │  New vendor: 27%               │ │                               │  │
│  └────────────────────────────────┘ └───────────────────────────────┘  │
│                                                                         │
│  ┌── TOP ISSUES TABLE ─────────────────────────────────────────────┐   │
│  │  Issue              Count   % of Total  Avg Resolution Time     │   │
│  │  No PO found        38      2.1%        4.2 hours               │   │
│  │  Price variance     28      1.5%        1.8 hours               │   │
│  │  New vendor hold    22      1.2%        6.4 hours               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 9: Agent Configuration (`/workforce/{agentId}/config`)

**Purpose:** Configure agent policy, integrations, and escalation rules.
**API Calls:** `GET /v1/agents/{agentId}/config`, `PUT /v1/agents/{agentId}/config`

### Layout (Tabbed)

```
┌────────────────────────────────────────────────────────────────────────┐
│  Workforce / AP Officer / Configuration        [Discard] [Save Changes]│
│                                                                         │
│  [Identity] [Policy] [Escalation] [Integrations] [History]            │
│  ─────────── ┌───────────────────────────────────────────────────────┐ │
│  POLICY TAB: │                                                       │ │
│              │  ⚠ Changes take effect immediately on next task.      │ │
│              │                                                       │ │
│              │  Invoice Matching                                     │ │
│              │  Price tolerance:  [2] % (platform max: 5%)          │ │
│              │  Qty tolerance:    [1] %                              │ │
│              │  3-way matching above: [$5,000]                       │ │
│              │                                                       │ │
│              │  Fraud Detection                                      │ │
│              │  Duplicate window: [90] days                          │ │
│              │  [✓] Hold new vendor invoices for review              │ │
│              │  [✓] Alert on bank detail changes                     │ │
│              │                                                       │ │
│              │  Payment                                              │ │
│              │  Batch frequency: [Weekly ▼]                          │ │
│              │  Early discount flag: [7] days before deadline        │ │
│              │                                                       │ │
│              │  Auto-approve limit: $0 (always require approval)     │ │
│              │  [i] Cannot be changed — platform policy              │ │
│              └───────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 10: Escalations Center (`/tasks/escalations`)

**Purpose:** Manage all open escalations needing human attention.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Escalations                  [Filter: Severity ▼] [Filter: Agent ▼]  │
│  5 Open  2 In Review  41 Resolved this month                           │
│                                                                         │
│  ┌─── CRITICAL ──────────────────────────────────────────────────────┐ │
│  │  🔴 Cybersecurity: Unusual login from new country — admin user   │ │
│  │     AI Cybersecurity Analyst | 8 minutes ago | SLA: 7 min left   │ │
│  │     [View & Act →]                                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── HIGH ──────────────────────────────────────────────────────────┐ │
│  │  🟠 Compliance: Segregation of duties violation — payment posted  │ │
│  │     AI Compliance Officer | 45 min ago | SLA: 3h 15m left        │ │
│  │     [View & Act →]                                                │ │
│  │                                                                   │ │
│  │  🟠 Finance: Invoice from new vendor > $25,000 — bank unverified  │ │
│  │     AI AP Officer | 1h ago | SLA: 3h left                        │ │
│  │     [View & Act →]                                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 11: Billing & Subscription (`/billing`)

```
┌────────────────────────────────────────────────────────────────────────┐
│  Billing                                                                │
│                                                                         │
│  Current Plan: GROWTH   Next invoice: Apr 1, 2026                      │
│                                                                         │
│  ┌── YOUR AGENTS (6) ─────────────────────────────────────────────────┐│
│  │  AI AP Officer            $300/mo   ✓ Active                      ││
│  │  AI Recruiter             $250/mo   ✓ Active                      ││
│  │  AI Support Agent         $200/mo   ✓ Active                      ││
│  │  AI Compliance Officer    $350/mo   ✓ Active                      ││
│  │  AI SDR                   $250/mo   ✓ Active                      ││
│  │  AI GL Analyst            $300/mo   ✓ Active                      ││
│  │                                                                    ││
│  │  Subtotal: $1,650/mo                                              ││
│  │  Department Bundle Discount (-15%): -$247.50                      ││
│  │  Platform Fee: $499/mo                                            ││
│  │  ─────────────────────────                                        ││
│  │  Total: $1,901.50/month                                           ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  ┌── INVOICE HISTORY ─────────────────────────────────────────────────┐│
│  │  Mar 2026  $1,901.50  ✓ PAID   [Download PDF]                     ││
│  │  Feb 2026  $1,901.50  ✓ PAID   [Download PDF]                     ││
│  └────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 12: Audit Log (`/analytics/compliance`)

```
┌────────────────────────────────────────────────────────────────────────┐
│  Analytics  /  Audit Log                [Export CSV] [Export PDF]      │
│                                                                         │
│  Filter: [Date Range] [Agent ▼] [Actor Type ▼] [Action ▼] [Search...]  │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ TIME             │ ACTOR          │ ACTION               │ ENTITY  ││
│  ├──────────────────┼────────────────┼──────────────────────┼─────────┤│
│  │ 10 Mar 14:32:21  │ 🤖 AP Officer  │ invoice.matched      │ INV-1234││
│  │ 10 Mar 14:31:04  │ 👤 Sarah J.    │ task.approved        │ TSK-456 ││
│  │ 10 Mar 14:28:00  │ 🤖 Recruiter   │ candidate.shortlisted│ APP-789 ││
│  │ 10 Mar 14:25:11  │ 🤖 Compliance  │ violation.flagged    │ TXN-012 ││
│  │ 10 Mar 14:20:00  │ ⚙  System      │ config.updated       │ AGT-003 ││
│  └────────────────────────────────────────────────────────────────────┘│
│  Showing 1–50 of 8,421 entries                      [← Prev] [Next →] │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Navigation & Global Patterns

```
SIDEBAR NAVIGATION
  Dashboard       /dashboard
  Workforce       /workforce
    ├ Catalog     /workforce/catalog
    └ Active      /workforce/active
  Tasks           /tasks
    ├ Live Queue  /tasks/live
    ├ My Approvals/tasks/queue
    └ History     /tasks/history
  Integrations    /integrations
  Analytics       /analytics
    ├ Performance /analytics/performance
    └ Audit Log   /analytics/compliance
  Billing         /billing
  Settings        /settings

NOTIFICATION CENTER (top-right bell icon)
  Grouped by type: Escalations | Approvals | System
  Click → navigate to relevant screen
  Mark all read button
  Real-time badge count (WebSocket)

GLOBAL SEARCH (⌘K)
  Search across: tasks, agents, audit logs, invoices, candidates
  Recent searches stored in localStorage
  Keyboard navigation

EMPTY STATES (every list screen)
  No agents subscribed → CTA to /workforce/catalog
  No tasks → "Your agents are all caught up! 🎉"
  No integrations → CTA to /integrations
```

---

*AI Digital Workforce Platform | UI Screen Specifications v1.0.0*
*Wireframes are ASCII — use Figma for final designs based on these specs*
