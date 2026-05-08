"""Data analytics tools for the AI Digital Workforce Platform.

Provides tools for running analytics queries, aggregating metrics, and
preparing chart-ready data structures. All tools return realistic mock
data for local development.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_TIME_SERIES: list[dict[str, Any]] = [
    {"date": "2026-03-01", "revenue": 42000, "deals_closed": 3, "new_leads": 18},
    {"date": "2026-03-02", "revenue": 15000, "deals_closed": 1, "new_leads": 12},
    {"date": "2026-03-03", "revenue": 67000, "deals_closed": 4, "new_leads": 22},
    {"date": "2026-03-04", "revenue": 28000, "deals_closed": 2, "new_leads": 15},
    {"date": "2026-03-05", "revenue": 53000, "deals_closed": 3, "new_leads": 20},
    {"date": "2026-03-06", "revenue": 91000, "deals_closed": 5, "new_leads": 25},
    {"date": "2026-03-07", "revenue": 34000, "deals_closed": 2, "new_leads": 14},
    {"date": "2026-03-08", "revenue": 0, "deals_closed": 0, "new_leads": 5},
    {"date": "2026-03-09", "revenue": 48000, "deals_closed": 3, "new_leads": 19},
    {"date": "2026-03-10", "revenue": 76000, "deals_closed": 4, "new_leads": 21},
]

_MOCK_AGGREGATION_DATA: dict[str, dict[str, Any]] = {
    "revenue": {
        "sum": 454000,
        "avg": 45400,
        "count": 10,
        "min": 0,
        "max": 91000,
    },
    "deals_closed": {
        "sum": 27,
        "avg": 2.7,
        "count": 10,
        "min": 0,
        "max": 5,
    },
    "new_leads": {
        "sum": 171,
        "avg": 17.1,
        "count": 10,
        "min": 5,
        "max": 25,
    },
    "support_tickets": {
        "sum": 89,
        "avg": 8.9,
        "count": 10,
        "min": 3,
        "max": 15,
    },
    "customer_satisfaction": {
        "sum": 43.5,
        "avg": 4.35,
        "count": 10,
        "min": 3.8,
        "max": 4.9,
    },
}

_MOCK_COMPARISON_DATA: dict[str, dict[str, Any]] = {
    "sales": {
        "current_period": {"revenue": 454000, "deals": 27, "avg_deal_size": 16815},
        "previous_period": {"revenue": 387000, "deals": 22, "avg_deal_size": 17590},
        "change_pct": {"revenue": 17.3, "deals": 22.7, "avg_deal_size": -4.4},
    },
    "marketing": {
        "current_period": {"leads": 171, "conversion_rate": 0.15, "cost_per_lead": 42},
        "previous_period": {"leads": 148, "conversion_rate": 0.12, "cost_per_lead": 51},
        "change_pct": {"leads": 15.5, "conversion_rate": 25.0, "cost_per_lead": -17.6},
    },
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class RunQueryTool(BaseTool):
    """Execute an analytics query against business data."""

    @property
    def name(self) -> str:
        return "run_query"

    @property
    def description(self) -> str:
        return (
            "Execute an analytics query against the business data warehouse. "
            "Supports aggregation queries, time-series queries, and period "
            "comparison queries. Returns structured result data."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["aggregation", "time_series", "comparison"],
                    "description": "Type of analytics query to run.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of metric names to include (e.g. 'revenue', 'deals_closed').",
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Dimensions to group by (e.g. 'date', 'region', 'product').",
                },
                "filters": {
                    "type": "object",
                    "description": "Filter criteria (e.g. {\"region\": \"north_america\"}).",
                },
                "date_range": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string", "description": "Start date (ISO 8601)."},
                        "to": {"type": "string", "description": "End date (ISO 8601)."},
                    },
                    "description": "Date range for the query.",
                },
            },
            "required": ["query_type", "metrics"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query_type = params.get("query_type")
        metrics = params.get("metrics", [])
        dimensions = params.get("dimensions", [])
        filters = params.get("filters", {})
        date_range = params.get("date_range", {})

        if not query_type:
            return self.error_result("query_type is required")
        if not metrics:
            return self.error_result("metrics is required and must be non-empty")

        logger.info(
            "Running %s query: metrics=%r dimensions=%r filters=%r",
            query_type,
            metrics,
            dimensions,
            filters,
        )

        if query_type == "time_series":
            # Filter time-series data to requested metrics
            rows: list[dict[str, Any]] = []
            for row in _MOCK_TIME_SERIES:
                filtered_row: dict[str, Any] = {"date": row["date"]}
                for metric in metrics:
                    if metric in row:
                        filtered_row[metric] = row[metric]
                rows.append(filtered_row)

            result: dict[str, Any] = {
                "query_type": query_type,
                "rows": rows,
                "row_count": len(rows),
                "metrics": metrics,
            }

        elif query_type == "comparison":
            comparison_results: dict[str, Any] = {}
            for metric in metrics:
                # Find matching comparison data
                for category, data in _MOCK_COMPARISON_DATA.items():
                    if metric in data["current_period"]:
                        comparison_results[metric] = {
                            "current": data["current_period"][metric],
                            "previous": data["previous_period"][metric],
                            "change_pct": data["change_pct"][metric],
                        }
                        break

            result = {
                "query_type": query_type,
                "comparisons": comparison_results,
                "metrics": metrics,
            }

        else:  # aggregation
            agg_results: dict[str, Any] = {}
            for metric in metrics:
                if metric in _MOCK_AGGREGATION_DATA:
                    agg_results[metric] = _MOCK_AGGREGATION_DATA[metric]
                else:
                    agg_results[metric] = {
                        "sum": 0,
                        "avg": 0,
                        "count": 0,
                        "min": 0,
                        "max": 0,
                    }

            result = {
                "query_type": query_type,
                "aggregations": agg_results,
                "metrics": metrics,
            }

        result["date_range"] = date_range or {
            "from": "2026-03-01",
            "to": "2026-03-10",
        }
        result["executed_at"] = datetime.utcnow().isoformat() + "Z"

        logger.info("Query complete: type=%s metrics=%d", query_type, len(metrics))
        return self.success_result({"query_result": result})


class AggregateMetricsTool(BaseTool):
    """Aggregate a single metric with grouping options."""

    @property
    def name(self) -> str:
        return "aggregate_metrics"

    @property
    def description(self) -> str:
        return (
            "Aggregate a specific metric using a chosen aggregation function "
            "(sum, average, count, min, max). Optionally group results by a "
            "dimension such as date, region, or product."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": "Name of the metric to aggregate (e.g. 'revenue', 'deals_closed').",
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["sum", "avg", "count", "min", "max"],
                    "description": "Aggregation function to apply.",
                },
                "group_by": {
                    "type": "string",
                    "description": "Dimension to group results by (e.g. 'date', 'region').",
                },
                "date_range": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "description": "Date range for the aggregation.",
                },
            },
            "required": ["metric_name", "aggregation"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        metric_name = params.get("metric_name")
        aggregation = params.get("aggregation")
        group_by = params.get("group_by")
        date_range = params.get("date_range", {})

        if not metric_name:
            return self.error_result("metric_name is required")
        if not aggregation:
            return self.error_result("aggregation is required")

        logger.info(
            "Aggregating metric %r using %s (group_by=%r)",
            metric_name,
            aggregation,
            group_by,
        )

        metric_data = _MOCK_AGGREGATION_DATA.get(metric_name)
        if not metric_data:
            return self.error_result(
                f"Metric '{metric_name}' not found",
                details={"available_metrics": list(_MOCK_AGGREGATION_DATA.keys())},
            )

        if group_by == "date":
            # Return per-day grouped data
            grouped_results: list[dict[str, Any]] = []
            for row in _MOCK_TIME_SERIES:
                if metric_name in row:
                    grouped_results.append({
                        "group": row["date"],
                        "value": row[metric_name],
                    })

            result: dict[str, Any] = {
                "metric_name": metric_name,
                "aggregation": aggregation,
                "group_by": group_by,
                "groups": grouped_results,
                "overall_value": metric_data[aggregation],
            }
        else:
            result = {
                "metric_name": metric_name,
                "aggregation": aggregation,
                "value": metric_data[aggregation],
                "sample_size": metric_data["count"],
            }

        result["date_range"] = date_range or {
            "from": "2026-03-01",
            "to": "2026-03-10",
        }
        result["computed_at"] = datetime.utcnow().isoformat() + "Z"

        logger.info(
            "Aggregation complete: %s(%s) = %s",
            aggregation,
            metric_name,
            result.get("value", "grouped"),
        )
        return self.success_result({"aggregation": result})


class GenerateChartDataTool(BaseTool):
    """Prepare data in a chart-ready format for visualization."""

    @property
    def name(self) -> str:
        return "generate_chart_data"

    @property
    def description(self) -> str:
        return (
            "Prepare data in a structure optimized for chart rendering. "
            "Supports bar, line, pie, and area chart types. Returns labels, "
            "datasets, and configuration suitable for front-end charting "
            "libraries."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "area"],
                    "description": "Type of chart to generate data for.",
                },
                "data_source": {
                    "type": "string",
                    "description": "Name of the data source or dataset to use.",
                },
                "x_axis": {
                    "type": "string",
                    "description": "Field to use for the X axis (e.g. 'date').",
                },
                "y_axis": {
                    "type": "string",
                    "description": "Field to use for the Y axis (e.g. 'revenue').",
                },
                "series": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiple series/metrics to plot (for multi-series charts).",
                },
            },
            "required": ["chart_type"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        chart_type = params.get("chart_type")
        data_source = params.get("data_source", "default")
        x_axis = params.get("x_axis", "date")
        y_axis = params.get("y_axis", "revenue")
        series = params.get("series", [y_axis])

        if not chart_type:
            return self.error_result("chart_type is required")

        logger.info(
            "Generating %s chart data: x=%r series=%r source=%r",
            chart_type,
            x_axis,
            series,
            data_source,
        )

        if chart_type == "pie":
            # Pie chart uses category breakdowns
            chart_data: dict[str, Any] = {
                "chart_type": "pie",
                "title": f"Distribution of {y_axis}",
                "labels": ["Engineering", "Marketing", "Operations", "Sales", "Support"],
                "datasets": [
                    {
                        "data": [35, 25, 20, 12, 8],
                        "label": y_axis,
                    }
                ],
                "options": {
                    "show_legend": True,
                    "show_percentages": True,
                },
            }
        elif chart_type in ("line", "area"):
            # Time-series data
            labels = [row["date"] for row in _MOCK_TIME_SERIES]
            datasets: list[dict[str, Any]] = []
            for s in series:
                values = [row.get(s, 0) for row in _MOCK_TIME_SERIES]
                datasets.append({
                    "label": s,
                    "data": values,
                    "fill": chart_type == "area",
                })

            chart_data = {
                "chart_type": chart_type,
                "title": f"{', '.join(series)} over time",
                "labels": labels,
                "datasets": datasets,
                "options": {
                    "x_axis_label": x_axis,
                    "y_axis_label": series[0] if len(series) == 1 else "value",
                    "show_legend": len(series) > 1,
                },
            }
        else:  # bar
            labels = [row["date"] for row in _MOCK_TIME_SERIES]
            datasets = []
            for s in series:
                values = [row.get(s, 0) for row in _MOCK_TIME_SERIES]
                datasets.append({
                    "label": s,
                    "data": values,
                })

            chart_data = {
                "chart_type": "bar",
                "title": f"{', '.join(series)} by {x_axis}",
                "labels": labels,
                "datasets": datasets,
                "options": {
                    "x_axis_label": x_axis,
                    "y_axis_label": series[0] if len(series) == 1 else "value",
                    "show_legend": len(series) > 1,
                    "stacked": False,
                },
            }

        chart_data["generated_at"] = datetime.utcnow().isoformat() + "Z"

        logger.info("Chart data generated: type=%s points=%d", chart_type, len(chart_data.get("labels", [])))
        return self.success_result({"chart": chart_data})
