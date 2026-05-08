"""AI Inventory Planner -- manages demand forecasting, reorder optimization, and stock alerts.

Implements the 4-step inventory planning workflow:
  1. DEMAND FORECAST -- Generate demand forecasts using historical data
  2. REORDER ANALYSIS -- Calculate reorder points and economic order quantities
  3. STOCK ALERTS -- Monitor stock levels and generate alerts
  4. PO RECOMMENDATION -- Recommend purchase orders for items needing replenishment

Also handles individual demand forecasting, reorder analysis, stock alerts,
and inventory queries as separate task types.

Worker ID: ai-inventory-planner
Department: Finance & Procurement
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.finance_procurement.tools import (
    DemandForecastTool,
    ReorderCalculatorTool,
    StockAlertTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "safety_stock": {
        "default_multiplier": 1.645,  # 95% service level
        "class_a_multiplier": 2.33,  # 99% service level
        "class_b_multiplier": 1.645,  # 95% service level
        "class_c_multiplier": 1.28,  # 90% service level
        "minimum_safety_stock_days": 3,
        "maximum_safety_stock_days": 30,
    },
    "reorder": {
        "default_service_level": 0.95,
        "class_a_service_level": 0.99,
        "class_b_service_level": 0.95,
        "class_c_service_level": 0.90,
        "default_lead_time_days": 14,
        "lead_time_buffer_percent": 10,
        "eoq_ordering_cost": 50,
        "eoq_holding_cost_percent": 25,
    },
    "abc_classification": {
        "class_a_percent_value": 80,
        "class_a_percent_items": 20,
        "class_b_percent_value": 15,
        "class_b_percent_items": 30,
        "class_c_percent_value": 5,
        "class_c_percent_items": 50,
        "reclassification_frequency_months": 6,
    },
    "alerts": {
        "critical_threshold_days": 3,
        "excess_threshold_days": 180,
        "slow_moving_days": 90,
        "expiry_alert_days": 30,
        "stockout_notification_channels": ["email", "dashboard"],
        "alert_frequency_hours": 4,
    },
    "forecasting": {
        "default_method": "weighted_moving_average",
        "lookback_periods": 6,
        "forecast_periods": 3,
        "seasonality_enabled": True,
        "minimum_history_periods": 3,
        "outlier_threshold_std_dev": 2.5,
    },
    "po_recommendation": {
        "auto_generate_pr_below": 5000,
        "consolidate_vendor_orders": True,
        "minimum_order_value": 100,
        "preferred_order_day": "Monday",
        "emergency_order_threshold_days": 2,
    },
}


class InventoryPlannerAgent(BaseAgent):
    """AI Inventory Planner -- manages demand forecasting, reorder, and stock alerts.

    Executes a four-step workflow for inventory planning:
      1. Generate demand forecasts using historical data
      2. Calculate reorder points and economic order quantities
      3. Monitor stock levels and generate alerts
      4. Recommend purchase orders for replenishment

    Also supports individual tasks for demand forecasting, reorder
    analysis, stock alerts, and inventory queries.

    Attributes:
        _demand_forecast: Tool for generating demand forecasts.
        _reorder_calculator: Tool for calculating reorder parameters.
        _stock_alert: Tool for monitoring stock levels.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Inventory Planner agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-inventory-planner", llm_gateway, pii_redactor)
        self.name = "AI Inventory Planner"
        self._demand_forecast = DemandForecastTool()
        self._reorder_calculator = ReorderCalculatorTool()
        self._stock_alert = StockAlertTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "demand_forecasting",
            "simple_moving_average",
            "weighted_moving_average",
            "exponential_smoothing",
            "seasonality_adjustment",
            "trend_analysis",
            "reorder_point_calculation",
            "safety_stock_calculation",
            "economic_order_quantity",
            "abc_classification",
            "stock_level_monitoring",
            "low_stock_alerting",
            "excess_stock_detection",
            "slow_moving_identification",
            "expiry_management",
            "purchase_order_recommendation",
            "vendor_consolidation",
            "inventory_reporting",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``demand_forecast``: Generate demand forecasts
          - ``reorder_analysis``: Calculate reorder parameters
          - ``stock_alert``: Monitor stock levels and generate alerts
          - ``inventory_query`` (default): Full 4-step inventory planning workflow

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "inventory_query")

        if task_type == "demand_forecast":
            return await self._handle_demand_forecast(task_payload, context)
        elif task_type == "reorder_analysis":
            return await self._handle_reorder_analysis(task_payload, context)
        elif task_type == "stock_alert":
            return await self._handle_stock_alert(task_payload, context)
        elif task_type == "inventory_query":
            return await self._inventory_planning_workflow(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full Inventory Planning workflow (4 steps)
    # ------------------------------------------------------------------

    async def _inventory_planning_workflow(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step inventory planning workflow.

        Steps:
          1. Demand Forecast -- generate forecasts for key items
          2. Reorder Analysis -- calculate reorder parameters
          3. Stock Alerts -- check stock levels and generate alerts
          4. PO Recommendation -- recommend replenishment orders

        Args:
            task_payload: Inventory planning parameters.
            context: Execution context with inventory_items, historical_demand,
                     and policy overrides.

        Returns:
            Standardized result dict with detailed planning output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", str(uuid.uuid4())))
        audit_events: list[dict[str, Any]] = []

        policy = self._resolve_policy(context)

        # Step 1: Demand Forecast
        forecast_results = await self._step_demand_forecast(context, policy)
        audit_events.append(self._audit_event(
            "inventory.forecast.generated",
            tenant_id,
            execution_id,
            items_forecasted=len(forecast_results),
        ))

        # Step 2: Reorder Analysis
        reorder_results = await self._step_reorder_analysis(context, policy, forecast_results)
        reorder_needed = sum(1 for r in reorder_results if r.get("needs_reorder"))
        audit_events.append(self._audit_event(
            "inventory.reorder.calculated",
            tenant_id,
            execution_id,
            items_analyzed=len(reorder_results),
            items_needing_reorder=reorder_needed,
        ))

        # Step 3: Stock Alerts
        alert_results = await self._step_stock_alerts(context, policy)

        stockout_items = [
            a for a in alert_results.get("alerts", [])
            if a.get("alert_type") in ("stockout", "critically_low")
        ]
        if stockout_items:
            audit_events.append(self._audit_event(
                "inventory.stockout.detected",
                tenant_id,
                execution_id,
                stockout_count=len(stockout_items),
                items=[a.get("item_id") for a in stockout_items],
            ))

        excess_items = [
            a for a in alert_results.get("alerts", [])
            if a.get("alert_type") in ("excess", "slow_moving")
        ]
        if excess_items:
            audit_events.append(self._audit_event(
                "inventory.excess.detected",
                tenant_id,
                execution_id,
                excess_count=len(excess_items),
                items=[a.get("item_id") for a in excess_items],
            ))

        # Step 4: PO Recommendations
        po_recommendations = await self._step_po_recommendation(
            reorder_results, alert_results, context, policy
        )
        if po_recommendations:
            audit_events.append(self._audit_event(
                "inventory.po.recommended",
                tenant_id,
                execution_id,
                po_count=len(po_recommendations),
                total_value=round(
                    sum(float(p.get("order_value", 0) or 0) for p in po_recommendations), 2
                ),
            ))

        # Generate LLM summary
        summary_result = await self._generate_planning_summary(
            forecast_results, reorder_results, alert_results, po_recommendations, policy
        )
        total_tokens += summary_result.get("tokens_used", 0)
        total_cost += summary_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "demand_forecasts": forecast_results,
            "reorder_analysis": reorder_results,
            "stock_alerts": alert_results,
            "po_recommendations": po_recommendations,
            "summary": summary_result.get("content", "Inventory planning complete."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Replenishment orders always require buyer approval. "
                "Safety stock levels never reduced automatically."
            ),
        }

        # Determine status
        critical_alerts = alert_results.get("critical_alerts", 0)
        needs_action = critical_alerts > 0 or len(po_recommendations) > 0

        next_action: Optional[str] = None
        if critical_alerts > 0:
            next_action = "human_review"

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "items_analyzed": len(forecast_results),
                "critical_alerts": critical_alerts,
                "reorder_items": sum(
                    1 for r in reorder_results if r.get("needs_reorder")
                ),
                "po_recommendations": len(po_recommendations),
            },
        )

        if critical_alerts > 0:
            result["risk_level"] = "high"
        elif needs_action:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Demand Forecast
    # ------------------------------------------------------------------

    async def _step_demand_forecast(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate demand forecasts for inventory items.

        Iterates through inventory items and generates forecasts
        using the DemandForecastTool.

        Args:
            context: Execution context with inventory_items and
                     historical_demand data.
            policy: Resolved policy configuration.

        Returns:
            List of forecast result dicts per item.
        """
        inventory_items = context.get("inventory_items", [])
        historical_demand = context.get("historical_demand", {})
        forecast_policy = policy.get("forecasting", {})

        method = forecast_policy.get("default_method", "weighted_moving_average")
        lookback = forecast_policy.get("lookback_periods", 6)
        periods = forecast_policy.get("forecast_periods", 3)
        min_history = forecast_policy.get("minimum_history_periods", 3)

        forecasts: list[dict[str, Any]] = []

        for item in inventory_items:
            item_id = item.get("item_id", item.get("id", ""))
            item_name = item.get("item_name", item.get("name", item_id))

            # Get historical demand for this item
            item_history = historical_demand.get(item_id, [])

            # Also check if historical data is embedded in the item
            if not item_history:
                item_history = item.get("historical_demand", [])

            # Skip items with insufficient history (they will get mock data)
            seasonality = float(item.get("seasonality_factor", 1.0))

            result = await self._demand_forecast.execute({
                "item_id": item_id,
                "item_name": item_name,
                "historical_demand": item_history,
                "forecast_periods": periods,
                "method": method,
                "lookback_periods": lookback,
                "seasonality_factor": seasonality,
            })

            if result.get("success"):
                forecast_data = result["data"]
                forecast_data["item_id"] = item_id
                forecast_data["item_name"] = item_name
                forecasts.append(forecast_data)
            else:
                forecasts.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "error": result.get("error", "Forecast failed."),
                    "forecasts": [],
                })

        return forecasts

    # ------------------------------------------------------------------
    # Step 2: Reorder Analysis
    # ------------------------------------------------------------------

    async def _step_reorder_analysis(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
        forecast_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Calculate reorder parameters for inventory items.

        Uses the ReorderCalculatorTool to compute safety stock,
        reorder points, and economic order quantities.

        Args:
            context: Execution context with inventory_items.
            policy: Resolved policy configuration.
            forecast_results: Demand forecast results from step 1.

        Returns:
            List of reorder calculation result dicts per item.
        """
        inventory_items = context.get("inventory_items", [])
        reorder_policy = policy.get("reorder", {})
        safety_policy = policy.get("safety_stock", {})

        # Build forecast lookup
        forecast_lookup: dict[str, dict[str, Any]] = {}
        for f in forecast_results:
            fid = f.get("item_id", "")
            if fid:
                forecast_lookup[fid] = f

        results: list[dict[str, Any]] = []

        for item in inventory_items:
            item_id = item.get("item_id", item.get("id", ""))
            item_name = item.get("item_name", item.get("name", item_id))
            abc_class = item.get("abc_class", "B")

            # Get demand stats from forecast or item data
            forecast = forecast_lookup.get(item_id, {})
            avg_daily = float(
                item.get("avg_daily_demand")
                or item.get("daily_demand")
                or forecast.get("historical_average", 0)
            )
            # Convert from period demand to daily if needed
            if avg_daily > 100 and forecast.get("historical_average"):
                # Assume period is monthly, convert to daily
                avg_daily = float(forecast.get("historical_average", 0)) / 30

            demand_sd = float(
                item.get("demand_std_dev")
                or forecast.get("historical_std_dev", avg_daily * 0.2)
            )

            # Lead time
            lead_time = float(
                item.get("lead_time_days")
                or reorder_policy.get("default_lead_time_days", 14)
            )
            lt_buffer = reorder_policy.get("lead_time_buffer_percent", 10)
            lead_time_adj = lead_time * (1 + lt_buffer / 100)
            lt_sd = float(item.get("lead_time_std_dev", lead_time * 0.1))

            # Service level based on ABC class
            service_levels = {
                "A": reorder_policy.get("class_a_service_level", 0.99),
                "B": reorder_policy.get("class_b_service_level", 0.95),
                "C": reorder_policy.get("class_c_service_level", 0.90),
            }
            service_level = service_levels.get(abc_class, 0.95)

            # Safety stock multiplier override based on ABC class
            ss_multipliers = {
                "A": safety_policy.get("class_a_multiplier"),
                "B": safety_policy.get("class_b_multiplier"),
                "C": safety_policy.get("class_c_multiplier"),
            }
            ss_multiplier = ss_multipliers.get(abc_class)

            unit_cost = float(item.get("unit_cost", 10))
            current_stock = item.get("current_stock", item.get("on_hand"))
            if current_stock is not None:
                current_stock = float(current_stock)

            result = await self._reorder_calculator.execute({
                "item_id": item_id,
                "item_name": item_name,
                "average_daily_demand": avg_daily if avg_daily > 0 else 1.0,
                "demand_std_dev": demand_sd,
                "lead_time_days": lead_time_adj,
                "lead_time_std_dev": lt_sd,
                "service_level": service_level,
                "unit_cost": unit_cost,
                "ordering_cost": reorder_policy.get("eoq_ordering_cost", 50),
                "holding_cost_percent": reorder_policy.get("eoq_holding_cost_percent", 25),
                "current_stock": current_stock,
                "safety_stock_multiplier": ss_multiplier,
                "abc_class": abc_class,
            })

            if result.get("success"):
                reorder_data = result["data"]
                results.append(reorder_data)
            else:
                results.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "error": result.get("error", "Reorder calculation failed."),
                    "needs_reorder": False,
                })

        return results

    # ------------------------------------------------------------------
    # Step 3: Stock Alerts
    # ------------------------------------------------------------------

    async def _step_stock_alerts(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Monitor stock levels and generate alerts.

        Delegates to the StockAlertTool to check all inventory items
        against configured thresholds.

        Args:
            context: Execution context with inventory_items.
            policy: Resolved policy configuration.

        Returns:
            Dict with alert summary and individual alerts.
        """
        inventory_items = context.get("inventory_items", [])
        alert_policy = policy.get("alerts", {})

        result = await self._stock_alert.execute({
            "inventory_items": inventory_items,
            "critical_threshold_days": alert_policy.get("critical_threshold_days", 3),
            "excess_threshold_days": alert_policy.get("excess_threshold_days", 180),
            "slow_moving_days": alert_policy.get("slow_moving_days", 90),
            "expiry_alert_days": alert_policy.get("expiry_alert_days", 30),
        })

        if result.get("success"):
            return result["data"]

        return {
            "total_items_scanned": len(inventory_items),
            "total_alerts": 0,
            "critical_alerts": 0,
            "warning_alerts": 0,
            "info_alerts": 0,
            "alerts": [],
            "error": result.get("error", "Stock alert check failed."),
            "summary": "Stock alert check could not be completed.",
        }

    # ------------------------------------------------------------------
    # Step 4: PO Recommendation
    # ------------------------------------------------------------------

    async def _step_po_recommendation(
        self,
        reorder_results: list[dict[str, Any]],
        alert_results: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate purchase order recommendations for items needing replenishment.

        Evaluates reorder analysis results and stock alerts to identify
        items that need replenishment and generates PO recommendations.

        Args:
            reorder_results: Reorder analysis results from step 2.
            alert_results: Stock alert results from step 3.
            context: Execution context.
            policy: Resolved policy configuration.

        Returns:
            List of PO recommendation dicts.
        """
        po_policy = policy.get("po_recommendation", {})
        min_order_value = po_policy.get("minimum_order_value", 100)
        consolidate = po_policy.get("consolidate_vendor_orders", True)
        emergency_days = po_policy.get("emergency_order_threshold_days", 2)

        recommendations: list[dict[str, Any]] = []
        vendor_orders: dict[str, list[dict[str, Any]]] = {}

        # Identify items needing reorder
        for reorder in reorder_results:
            if not reorder.get("needs_reorder"):
                continue

            item_id = reorder.get("item_id", "")
            item_name = reorder.get("item_name", item_id)
            eoq = float(reorder.get("economic_order_quantity", 0))
            unit_cost = float(reorder.get("unit_cost", 0))
            order_value = eoq * unit_cost
            days_of_stock = reorder.get("days_of_stock", 999)
            abc_class = reorder.get("abc_class", "B")

            if order_value < min_order_value:
                continue

            is_emergency = (
                days_of_stock is not None and days_of_stock <= emergency_days
            )

            urgency = "emergency" if is_emergency else "normal"
            if abc_class == "A" and not is_emergency:
                urgency = "high"
            elif abc_class == "C":
                urgency = "low"

            # Find preferred vendor from context
            vendor_map = context.get("item_vendor_map", {})
            preferred_vendor = vendor_map.get(item_id, {})
            vendor_name = preferred_vendor.get("vendor_name", "TBD")
            vendor_id = preferred_vendor.get("vendor_id", "")

            recommendation: dict[str, Any] = {
                "item_id": item_id,
                "item_name": item_name,
                "recommended_quantity": eoq,
                "unit_cost": unit_cost,
                "order_value": round(order_value, 2),
                "current_stock": reorder.get("current_stock"),
                "reorder_point": reorder.get("reorder_point"),
                "safety_stock": reorder.get("safety_stock"),
                "days_of_stock": days_of_stock,
                "abc_class": abc_class,
                "urgency": urgency,
                "vendor_name": vendor_name,
                "vendor_id": vendor_id,
                "lead_time_days": reorder.get("lead_time_days", 14),
            }

            recommendations.append(recommendation)

            # Group by vendor for consolidation
            if consolidate and vendor_id:
                if vendor_id not in vendor_orders:
                    vendor_orders[vendor_id] = []
                vendor_orders[vendor_id].append(recommendation)

        # Check alerts for additional items not in reorder results
        for alert in alert_results.get("alerts", []):
            alert_type = alert.get("alert_type")
            if alert_type in ("stockout", "critically_low"):
                item_id = alert.get("item_id")
                # Check if already in recommendations
                already_included = any(
                    r["item_id"] == item_id for r in recommendations
                )
                if not already_included:
                    recommendations.append({
                        "item_id": item_id,
                        "item_name": alert.get("item_name"),
                        "recommended_quantity": None,  # To be determined
                        "unit_cost": None,
                        "order_value": None,
                        "current_stock": alert.get("current_stock"),
                        "days_of_stock": alert.get("days_of_stock", 0),
                        "abc_class": alert.get("abc_class", ""),
                        "urgency": "emergency",
                        "vendor_name": "TBD",
                        "vendor_id": "",
                        "lead_time_days": None,
                        "alert_type": alert_type,
                        "alert_message": alert.get("message"),
                    })

        # Sort by urgency
        urgency_order = {"emergency": 0, "high": 1, "normal": 2, "low": 3}
        recommendations.sort(
            key=lambda x: urgency_order.get(x.get("urgency", "normal"), 2)
        )

        # Add consolidation info
        if consolidate:
            for rec in recommendations:
                vid = rec.get("vendor_id", "")
                if vid and vid in vendor_orders:
                    vendor_items = vendor_orders[vid]
                    if len(vendor_items) > 1:
                        rec["consolidation_group"] = vid
                        rec["consolidation_items"] = len(vendor_items)
                        rec["consolidation_total"] = round(
                            sum(i.get("order_value", 0) or 0 for i in vendor_items), 2
                        )

        return recommendations

    # ------------------------------------------------------------------
    # Individual task handlers
    # ------------------------------------------------------------------

    async def _handle_demand_forecast(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate demand forecast for a specific item.

        Args:
            task_payload: Forecast parameters with item_id and historical data.
            context: Execution context.

        Returns:
            Standardized result with forecast data.
        """
        policy = self._resolve_policy(context)
        forecast_policy = policy.get("forecasting", {})

        item_id = task_payload.get("item_id", "")
        item_name = task_payload.get("item_name", item_id)
        historical = task_payload.get("historical_demand", [])
        method = task_payload.get(
            "method", forecast_policy.get("default_method", "weighted_moving_average")
        )

        result = await self._demand_forecast.execute({
            "item_id": item_id,
            "item_name": item_name,
            "historical_demand": historical,
            "forecast_periods": task_payload.get(
                "forecast_periods", forecast_policy.get("forecast_periods", 3)
            ),
            "method": method,
            "lookback_periods": task_payload.get(
                "lookback_periods", forecast_policy.get("lookback_periods", 6)
            ),
            "seasonality_factor": task_payload.get("seasonality_factor", 1.0),
        })

        if not result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Demand forecast failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        forecast_data = result["data"]

        # Generate LLM analysis
        fcst_summary = json.dumps(
            {
                "item": item_name,
                "method": method,
                "trend": forecast_data.get("trend"),
                "variability": forecast_data.get("variability"),
                "avg_demand": forecast_data.get("historical_average"),
                "forecasts": forecast_data.get("forecasts", []),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Inventory Planner. Analyze the demand forecast "
                    "results and provide insights in 2-3 sentences. Cover:\n"
                    "- Demand trend and variability\n"
                    "- Forecast confidence\n"
                    "- Recommended actions (adjust safety stock, review suppliers, etc.)"
                ),
            },
            {
                "role": "user",
                "content": f"Demand forecast for {item_name}:\n{fcst_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            trend = forecast_data.get("trend", "stable")
            avg = forecast_data.get("historical_average", 0)
            forecasts = forecast_data.get("forecasts", [])
            next_qty = forecasts[0]["forecast_quantity"] if forecasts else avg
            summary = (
                f"Demand for {item_name}: avg {avg:.0f}, trend {trend}. "
                f"Next period forecast: {next_qty:.0f} units."
            )

        return self.format_result(
            status="completed",
            output={
                "forecast": forecast_data,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={
                "item_id": item_id,
                "method": method,
                "trend": forecast_data.get("trend"),
                "variability": forecast_data.get("variability"),
            },
        )

    async def _handle_reorder_analysis(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate reorder parameters for a specific item.

        Args:
            task_payload: Reorder parameters with item details.
            context: Execution context.

        Returns:
            Standardized result with reorder calculations.
        """
        policy = self._resolve_policy(context)
        reorder_policy = policy.get("reorder", {})
        safety_policy = policy.get("safety_stock", {})

        item_id = task_payload.get("item_id", "")
        item_name = task_payload.get("item_name", item_id)
        abc_class = task_payload.get("abc_class", "B")

        # Service level based on ABC class
        service_levels = {
            "A": reorder_policy.get("class_a_service_level", 0.99),
            "B": reorder_policy.get("class_b_service_level", 0.95),
            "C": reorder_policy.get("class_c_service_level", 0.90),
        }
        service_level = task_payload.get(
            "service_level", service_levels.get(abc_class, 0.95)
        )

        # Safety stock multiplier
        ss_multipliers = {
            "A": safety_policy.get("class_a_multiplier"),
            "B": safety_policy.get("class_b_multiplier"),
            "C": safety_policy.get("class_c_multiplier"),
        }
        ss_multiplier = task_payload.get(
            "safety_stock_multiplier", ss_multipliers.get(abc_class)
        )

        avg_demand = float(task_payload.get("average_daily_demand", 0))
        if avg_demand <= 0:
            return self.format_result(
                "failed",
                {"error": "Average daily demand must be positive."},
                tokens_used=0,
                cost_usd=0.0,
            )

        result = await self._reorder_calculator.execute({
            "item_id": item_id,
            "item_name": item_name,
            "average_daily_demand": avg_demand,
            "demand_std_dev": float(task_payload.get("demand_std_dev", avg_demand * 0.2)),
            "lead_time_days": float(
                task_payload.get("lead_time_days", reorder_policy.get("default_lead_time_days", 14))
            ),
            "lead_time_std_dev": float(task_payload.get("lead_time_std_dev", 1.0)),
            "service_level": service_level,
            "unit_cost": float(task_payload.get("unit_cost", 10)),
            "ordering_cost": float(
                task_payload.get("ordering_cost", reorder_policy.get("eoq_ordering_cost", 50))
            ),
            "holding_cost_percent": float(
                task_payload.get(
                    "holding_cost_percent",
                    reorder_policy.get("eoq_holding_cost_percent", 25),
                )
            ),
            "current_stock": task_payload.get("current_stock"),
            "safety_stock_multiplier": ss_multiplier,
            "abc_class": abc_class,
        })

        if not result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Reorder calculation failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        reorder_data = result["data"]

        # Generate LLM analysis
        reorder_summary = json.dumps(
            {
                "item": item_name,
                "abc_class": abc_class,
                "reorder_point": reorder_data.get("reorder_point"),
                "safety_stock": reorder_data.get("safety_stock"),
                "eoq": reorder_data.get("economic_order_quantity"),
                "current_stock": reorder_data.get("current_stock"),
                "needs_reorder": reorder_data.get("needs_reorder"),
                "days_of_stock": reorder_data.get("days_of_stock"),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Inventory Planner. Summarize the reorder analysis "
                    "in 2-3 sentences. Note the reorder point, safety stock level, "
                    "EOQ, and whether immediate action is needed."
                ),
            },
            {
                "role": "user",
                "content": f"Reorder analysis for {item_name}:\n{reorder_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            rop = reorder_data.get("reorder_point", 0)
            ss = reorder_data.get("safety_stock", 0)
            eoq = reorder_data.get("economic_order_quantity", 0)
            needs = reorder_data.get("needs_reorder", False)
            summary = (
                f"{item_name}: ROP={rop:.0f}, SS={ss:.0f}, EOQ={eoq:.0f}. "
                f"{'Reorder needed.' if needs else 'Stock adequate.'}"
            )

        return self.format_result(
            status="completed",
            output={
                "reorder_analysis": reorder_data,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="human_review" if reorder_data.get("needs_reorder") else None,
            metadata={
                "item_id": item_id,
                "needs_reorder": reorder_data.get("needs_reorder"),
                "reorder_point": reorder_data.get("reorder_point"),
                "eoq": reorder_data.get("economic_order_quantity"),
            },
        )

    async def _handle_stock_alert(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Check stock levels and generate alerts.

        Args:
            task_payload: Alert parameters and inventory items.
            context: Execution context.

        Returns:
            Standardized result with stock alerts.
        """
        policy = self._resolve_policy(context)
        alert_policy = policy.get("alerts", {})

        items = (
            task_payload.get("inventory_items")
            or context.get("inventory_items")
            or []
        )

        result = await self._stock_alert.execute({
            "inventory_items": items,
            "critical_threshold_days": task_payload.get(
                "critical_threshold_days",
                alert_policy.get("critical_threshold_days", 3),
            ),
            "excess_threshold_days": task_payload.get(
                "excess_threshold_days",
                alert_policy.get("excess_threshold_days", 180),
            ),
            "slow_moving_days": task_payload.get(
                "slow_moving_days",
                alert_policy.get("slow_moving_days", 90),
            ),
            "expiry_alert_days": task_payload.get(
                "expiry_alert_days",
                alert_policy.get("expiry_alert_days", 30),
            ),
        })

        if not result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Stock alert check failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        alert_data = result["data"]

        # Generate LLM summary
        alert_summary = json.dumps(
            {
                "total_scanned": alert_data.get("total_items_scanned"),
                "total_alerts": alert_data.get("total_alerts"),
                "critical": alert_data.get("critical_alerts"),
                "warning": alert_data.get("warning_alerts"),
                "info": alert_data.get("info_alerts"),
                "top_alerts": [
                    {
                        "item": a.get("item_name"),
                        "type": a.get("alert_type"),
                        "severity": a.get("severity"),
                        "message": a.get("message"),
                    }
                    for a in alert_data.get("alerts", [])[:5]
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Inventory Planner. Summarize the stock alert report "
                    "in 3-4 sentences. Prioritize critical alerts and recommend "
                    "immediate actions. Note any patterns (multiple items from same "
                    "category, seasonal impact, etc.)."
                ),
            },
            {
                "role": "user",
                "content": f"Stock alert report:\n{alert_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            critical = alert_data.get("critical_alerts", 0)
            total = alert_data.get("total_alerts", 0)
            scanned = alert_data.get("total_items_scanned", 0)
            summary = (
                f"Stock alert scan: {total} alerts from {scanned} items. "
                f"{critical} critical alert(s) require immediate attention."
            )

        has_critical = alert_data.get("critical_alerts", 0) > 0

        return self.format_result(
            status="completed",
            output={
                "alerts": alert_data,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="human_review" if has_critical else None,
            metadata={
                "total_alerts": alert_data.get("total_alerts", 0),
                "critical_alerts": alert_data.get("critical_alerts", 0),
                "items_scanned": alert_data.get("total_items_scanned", 0),
            },
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_planning_summary(
        self,
        forecast_results: list[dict[str, Any]],
        reorder_results: list[dict[str, Any]],
        alert_results: dict[str, Any],
        po_recommendations: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate inventory planning summary using the LLM.

        Args:
            forecast_results: Demand forecast results.
            reorder_results: Reorder analysis results.
            alert_results: Stock alert results.
            po_recommendations: PO recommendations.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        planning_data = json.dumps(
            {
                "forecasts": {
                    "items_forecasted": len(forecast_results),
                    "trends": self._count_by_field(forecast_results, "trend"),
                    "variability": self._count_by_field(forecast_results, "variability"),
                },
                "reorder": {
                    "items_analyzed": len(reorder_results),
                    "needs_reorder": sum(
                        1 for r in reorder_results if r.get("needs_reorder")
                    ),
                    "total_order_value": round(
                        sum(
                            float(r.get("economic_order_quantity", 0))
                            * float(r.get("unit_cost", 0))
                            for r in reorder_results
                            if r.get("needs_reorder")
                        ),
                        2,
                    ),
                },
                "alerts": {
                    "total": alert_results.get("total_alerts", 0),
                    "critical": alert_results.get("critical_alerts", 0),
                    "warning": alert_results.get("warning_alerts", 0),
                },
                "po_recommendations": {
                    "total": len(po_recommendations),
                    "emergency": sum(
                        1 for p in po_recommendations if p.get("urgency") == "emergency"
                    ),
                    "total_value": round(
                        sum(float(p.get("order_value", 0) or 0) for p in po_recommendations),
                        2,
                    ),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Inventory Planner. Generate a concise inventory "
                    "planning summary (4-6 sentences) covering:\n"
                    "- Demand forecast trends and reliability\n"
                    "- Items requiring reorder and total order value\n"
                    "- Critical stock alerts and immediate actions\n"
                    "- PO recommendations and priorities\n"
                    "Be data-driven and actionable."
                ),
            },
            {
                "role": "user",
                "content": f"Inventory planning results:\n{planning_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            reorder_count = sum(1 for r in reorder_results if r.get("needs_reorder"))
            critical = alert_results.get("critical_alerts", 0)
            total_value = sum(
                float(p.get("order_value", 0) or 0) for p in po_recommendations
            )

            content = (
                f"Inventory Planning Summary: Forecasted demand for "
                f"{len(forecast_results)} items. "
                f"{reorder_count} items need reorder (${total_value:,.2f} total value). "
                f"{critical} critical stock alerts. "
                f"{len(po_recommendations)} PO recommendations generated."
            )

        llm_result["content"] = content
        return llm_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge default policy with any overrides from the context.

        Args:
            context: Execution context potentially containing policy overrides.

        Returns:
            Merged policy configuration dict.
        """
        policy = dict(DEFAULT_POLICY)

        overrides = context.get("agent_policy", {}) or {}
        resolved = context.get("resolved_config", {}) or {}

        for section_key in DEFAULT_POLICY:
            section_override = overrides.get(section_key) or resolved.get(section_key)
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}

        return policy

    @staticmethod
    def _count_by_field(
        items: list[dict[str, Any]], field: str
    ) -> dict[str, int]:
        """Count items grouped by a field value.

        Args:
            items: List of dicts.
            field: Field name to group by.

        Returns:
            Dict mapping field values to counts.
        """
        counts: dict[str, int] = {}
        for item in items:
            value = str(item.get(field, "unknown"))
            counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict."""
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-inventory-planner",
        }
        event.update(extra)
        return event
