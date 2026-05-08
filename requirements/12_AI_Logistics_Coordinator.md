# AI Worker: Logistics Coordinator
**Department:** Delivery & Operations
**Worker ID:** `ai-logistics-coordinator`
**Version:** 1.0.0
**Subscription Tier:** Standard — $260/month

---

## 1. Role Overview

The AI Logistics Coordinator monitors all active shipments in real-time, proactively detects delivery exceptions, communicates status updates to customers, coordinates carrier responses, and recommends corrective actions during disruptions. It turns reactive logistics management into a proactive, data-driven operation.

### Core Promise
> "Problems with shipments are resolved before customers know they exist."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Real-Time Shipment Monitoring | Polls carrier APIs continuously for tracking updates | Full |
| ETA Recalculation | Dynamically updates expected delivery based on live data | Full |
| Delay Detection | Identifies shipments behind schedule before due date | Full |
| Exception Handling | Categorizes and responds to delays, damage, failed deliveries | Full |
| Customer Proactive Notification | Sends milestone and exception updates to customers | Full |
| Carrier Communication | Sends structured queries to carriers about exceptions | Full |
| Alternative Route/Carrier Suggestion | Recommends rerouting or alternative carriers during disruption | Advisory |
| Dispatch Updates | Updates dispatch team and warehouse on shipment changes | Full |
| Failed Delivery Management | Triggers redelivery requests and customer coordination | Full |
| SLA Monitoring | Tracks on-time delivery performance vs contracted SLAs | Full |
| Cost vs Delay Trade-off Analysis | Presents cost impact of alternative routing decisions | Full |

### Extended Capabilities (Phase 2)
- Multi-modal route optimization (sea/air/road blending)
- Customs clearance status monitoring and proactive flagging
- Carbon footprint tracking per shipment
- Predictive disruption detection (weather, port congestion, carrier strikes)

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| Carrier APIs | Shipment tracking (FedEx, DHL, Aramex, local carriers) |
| Order Management System | Shipment-to-order linking |
| Email / SMS | Customer and carrier notifications |

### Recommended
| System | Purpose |
|---|---|
| Warehouse Management | Dispatch confirmation, returns processing |
| Customer Portal | Self-service shipment tracking |
| ERP | Invoice and delivery note matching |
| Map/Route Intelligence | Route analysis and alternatives |

---

## 4. Workflow Definitions

### Workflow 1: Continuous Shipment Monitoring

```
TRIGGER: Active shipment in system (polling every 30–60 minutes)
═════════════════════════════════════════════════════════════════
Step 1: POLL CARRIER
  Request latest tracking status for all active shipments
  Parse status: in_transit | out_for_delivery | delivered | exception

Step 2: RECALCULATE ETA
  If carrier provides updated ETA → update system
  If delay detected → recalculate using route + carrier historical data

Step 3: CHECK AGAINST SLA
  Is current ETA still within promised delivery window?
  Is delay > threshold?

Step 4: ACT
  On-track → Customer milestone notification at key events
  Delayed (minor, < 24h) → Proactive customer notification with new ETA
  Delayed (major, > 24h) → Customer notification + carrier escalation
  Exception (damage, lost) → Immediate alert to ops manager + customer
```

### Workflow 2: Disruption Management

```
TRIGGER: Shipment flagged with major delay or exception
═══════════════════════════════════════════════════════
Step 1: ASSESS DISRUPTION
  Type: weather delay | carrier issue | customs hold | vehicle breakdown | lost
  Impact: how many shipments affected? Which customers?

Step 2: GENERATE OPTIONS
  Option A: Wait for carrier resolution (cost: $0, delay: +X days)
  Option B: Reroute via alternative carrier (cost: $Y, delay: +Z days)
  Option C: Air freight upgrade (cost: $W, delay: +0 days)

Step 3: RECOMMEND
  Best balance of cost and delay impact (based on configurable weighting)
  Show all options to ops manager for decision

Step 4: EXECUTE DECISION
  Once human approves → coordinate with carriers, update customer, log decision

Step 5: CUSTOMER COMMUNICATION
  Personalized, empathetic notification with:
    ├── Updated ETA
    ├── Explanation (without blaming carrier by name)
    └── Compensation action if applicable (per policy)
```

---

## 5. Policy Configuration

```yaml
monitoring:
  polling_interval_minutes: 30
  active_shipment_sla_hours: 48           # Flag if ETA exceeds order promise by 48h

notification_policy:
  milestone_updates:
    - "dispatched"
    - "in_transit_hub_scan"
    - "out_for_delivery"
    - "delivered"
  proactive_delay_threshold_hours: 4     # Notify customer if delay > 4h
  failed_delivery_follow_up_hours: 2

carrier_priority:
  primary: ["aramex", "dhl", "fedex"]
  fallback: ["local_courier_1", "local_courier_2"]

disruption_policy:
  reroute_cost_max_percent_of_shipment: 15   # Recommend reroute only if cost < 15% of shipment value
  ops_manager_approval_for_reroute: true
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| On-Time Delivery Rate | > 95% |
| Proactive Exception Notification Rate | 100% (customer notified before complaint) |
| Average Delay Resolution Time | < 4 hours |
| Customer CSAT for Delivery | > 4.3 / 5.0 |
| Exception-to-Resolution Cycle | < 24 hours |
| Failed Delivery Recovery Rate | > 90% re-delivered within 48h |

---

## 7. Guardrails

```
✓ Rerouting decisions always require ops manager approval
✓ Carrier compensation claims always escalated to finance/ops team
✓ Customer communication tone reviewed — never blame carrier by name
✓ Lost shipment claims: legal/insurance team involved automatically
✓ COD (cash on delivery) changes require customer service manager approval
```

---

## 8. Setup Checklist

```
[ ] Carrier API credentials configured (Aramex, DHL, FedEx, local)
[ ] Order management system connected
[ ] Customer notification templates created (delay, delivered, exception)
[ ] Carrier communication templates created
[ ] SLA windows configured per customer tier
[ ] Failed delivery redelivery policy defined
[ ] Disruption response workflow approved by ops manager
[ ] Ops manager escalation routing configured
[ ] Test: simulate 5 shipment scenarios (on-time, delay, lost, failed delivery, exception)
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Delivery & Operations | Role: Logistics Coordinator*
