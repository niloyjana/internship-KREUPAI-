# AI Worker: Inventory Planner
**Department:** Finance & Procurement
**Worker ID:** `ai-inventory-planner`
**Version:** 1.0.0
**Subscription Tier:** Standard — $280/month

---

## 1. Role Overview

The AI Inventory Planner continuously monitors stock levels, forecasts demand using historical patterns and seasonality, detects excess and dead stock, and generates proactive replenishment recommendations. It ensures businesses never run out of fast movers and never tie up capital in slow movers.

### Core Promise
> "Right stock, right place, right time — with capital not locked in warehouses unnecessarily."

---

## 2. Capabilities

| Capability | Description | Autonomy Level |
|---|---|---|
| Demand Forecasting | Predicts demand by SKU/location/period using ML | Full |
| Reorder Point Calculation | Calculates dynamic reorder points with safety stock | Full |
| Replenishment Recommendations | Suggests order quantities considering lead times | Advisory |
| Stockout Detection | Identifies items approaching zero stock | Full |
| Dead Stock Detection | Flags items with no movement in configurable period | Full |
| Excess Inventory Detection | Identifies overstocked items with value-at-risk | Full |
| Safety Stock Optimization | Recommends safety stock levels by demand variability | Advisory |
| Multi-Warehouse Support | Manages inventory across multiple locations | Full |
| Seasonal Adjustment | Adjusts forecasts for seasonal demand patterns | Full |
| Supplier Lead Time Tracking | Monitors and incorporates actual vs estimated lead times | Full |
| Inventory Valuation Summary | Reports FIFO/WMAC inventory value | Full |

### Extended Capabilities (Phase 2)
- Automatic replenishment PO creation (triggers Procurement Officer agent)
- IoT/RFID live stock level integration
- Vendor-managed inventory (VMI) support
- Returns and reverse logistics impact modeling

---

## 3. System Integrations

### Required
| System | Purpose |
|---|---|
| Warehouse Management / ERP | Real-time stock levels, movement history |
| Sales / Order Management | Demand history, open orders |

### Recommended
| System | Purpose |
|---|---|
| Procurement Module | Replenishment PO creation |
| Supplier System | Lead time data |
| Financial System | Inventory valuation, cost of goods |

---

## 4. Workflow Definitions

### Workflow 1: Daily Demand Forecast & Replenishment Check

```
TRIGGER: Scheduled daily job (configurable time)
═════════════════════════════════════════════════
Step 1: COLLECT DATA
  Current stock levels per SKU per warehouse
  Last 12 months demand history
  Open purchase orders (incoming stock)
  Open sales orders (committed stock)

Step 2: FORECAST DEMAND
  Short-term: 7-day demand forecast
  Medium-term: 30-day forecast
  Long-term: 90-day forecast
  Apply seasonal index if historical pattern exists

Step 3: CALCULATE REORDER NEED
  For each SKU:
    Days of stock remaining = current_stock / daily_demand_avg
    If days_remaining ≤ reorder_point_days → flag for replenishment
    Suggested order qty = (lead_time_demand + safety_stock) - on_order_qty

Step 4: GENERATE RECOMMENDATIONS
  Prioritized list: URGENT (< 7 days stock) | SOON (7–14 days) | PLANNED (14+ days)
  Include: SKU, location, current stock, recommended order qty, suggested supplier

Step 5: DELIVER TO PLANNER
  Dashboard view + email summary to inventory manager
  URGENT items: immediate alert
  Approved recommendations route to Procurement Officer agent for PO creation
```

### Workflow 2: Excess & Dead Stock Analysis

```
TRIGGER: Weekly analysis job
═════════════════════════════
Step 1: IDENTIFY DEAD STOCK
  Items with zero movement in last [configurable] days
  Calculate: quantity × unit cost = capital locked

Step 2: IDENTIFY EXCESS STOCK
  Items where current stock > forecast demand for next [X] months
  Calculate: excess qty × unit cost = excess capital

Step 3: GENERATE ACTIONS
  Dead stock: markdown, return to vendor, liquidate, redistribute to other location
  Excess stock: reduce next PO, promote to increase sell-through

Step 4: REPORT
  Dashboard with value-at-risk by category
  Drill-down by warehouse, SKU, age of stock
  Recommended disposal actions with financial impact estimate
```

---

## 5. Policy Configuration

```yaml
forecasting:
  method: "exponential_smoothing"        # Options: moving_avg | exponential_smoothing | ml_model
  seasonality_detection: true
  forecast_horizon_days: 90
  minimum_history_days: 30               # Minimum data needed to generate forecast

reorder_policy:
  safety_stock_method: "service_level"   # Options: fixed | service_level | demand_variability
  target_service_level: 0.95             # 95% service level (no stockout 95% of the time)
  lead_time_buffer_days: 2

dead_stock_policy:
  no_movement_days: 90                   # Flag if no movement in 90 days

excess_stock_policy:
  excess_months_of_stock: 6             # Flag if > 6 months of stock on hand
```

---

## 6. KPIs

| KPI | Target |
|---|---|
| Stockout Rate | < 2% of SKUs per month |
| Forecast Accuracy (MAPE) | < 15% Mean Absolute Percentage Error |
| Inventory Turnover Improvement | > 20% vs pre-AI baseline |
| Dead Stock Value Reduction | > 30% in 6 months |
| Excess Stock as % of Total | < 10% |
| Replenishment Lead Time Compliance | > 90% POs placed before stockout |

---

## 7. Guardrails

```
✓ Replenishment orders always require buyer approval — no autonomous purchasing
✓ Forecast overrides by planner always respected and logged
✓ Safety stock levels never reduced automatically — require planner confirmation
✓ Dead stock disposal recommendations require management approval
✓ Supplier minimum order quantities always respected in recommendations
```

---

## 8. Setup Checklist

```
[ ] Warehouse/ERP connected (real-time stock levels)
[ ] 12+ months demand/sales history loaded
[ ] SKU master imported (items, units, supplier, lead times, cost)
[ ] Reorder point method configured
[ ] Safety stock service level target set
[ ] Dead/excess stock thresholds defined
[ ] Multi-warehouse setup if applicable
[ ] Seasonal calendar defined (Ramadan, holiday periods)
[ ] Procurement Officer agent linked for PO creation workflow
[ ] Test: run forecast on 20 SKUs, validate reorder recommendations
```

---

*AI Digital Workforce Platform | Worker Specification v1.0*
*Department: Finance & Procurement | Role: Inventory Planner*
