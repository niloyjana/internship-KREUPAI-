"""AI Data Analyst Assistant Agent -- manages data analysis workflows end-to-end.

Implements the 4-step data analysis workflow:
  1. QUERY BUILDING -- Build and validate data queries from natural language
  2. DATA AGGREGATION -- Aggregate data from multiple sources
  3. ANOMALY DETECTION -- Detect statistical anomalies in datasets
  4. INSIGHT GENERATION -- Generate actionable insights from analysis

Also handles direct query building, data aggregation, anomaly detection,
and data source queries.

Worker ID: ai-data-analyst-assistant
Department: Delivery & Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.delivery_ops.tools import (
    AnomalyDetectorTool,
    DataAggregatorTool,
    QueryBuilderTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "data_access": {
        "allowed_sources": [
            "sales_warehouse",
            "operations_db",
            "hr_analytics",
            "finance_ledger",
            "customer_360",
        ],
        "restricted_sources": [
            "payroll_db",
            "executive_compensation",
        ],
        "require_approval_for_pii": True,
        "max_rows_per_query": 100000,
        "default_row_limit": 1000,
    },
    "anomaly_thresholds": {
        "default_z_score_threshold": 2.0,
        "critical_z_score_threshold": 3.0,
        "sensitivity": "medium",
        "min_data_points_for_detection": 30,
        "auto_alert_on_critical": True,
    },
    "query_limits": {
        "max_execution_seconds": 300,
        "max_concurrent_queries": 5,
        "timeout_warning_seconds": 60,
        "max_query_complexity": "high",
        "cache_results_minutes": 15,
    },
    "insight_confidence": {
        "min_confidence_threshold": 0.7,
        "high_confidence_threshold": 0.9,
        "require_human_review_below": 0.6,
        "include_methodology": True,
        "max_insights_per_analysis": 10,
    },
    "sla": {
        "query_response_seconds": 30,
        "aggregation_response_seconds": 60,
        "full_analysis_minutes": 10,
        "insight_delivery_minutes": 5,
    },
}


class DataAnalystAssistantAgent(BaseAgent):
    """AI Data Analyst Assistant Agent -- manages data analysis workflows.

    Executes a four-step workflow for data analysis:
      1. Build and validate data queries from natural language requests
      2. Aggregate data from multiple sources
      3. Detect statistical anomalies in datasets
      4. Generate actionable insights from the analysis

    Also supports direct operations via task type routing:
      - ``build_query``: Build structured data queries
      - ``aggregate_data``: Aggregate data from sources
      - ``detect_anomalies``: Detect anomalies in data
      - ``generate_insights`` (default): Full 4-step analysis workflow
      - ``data_query``: Query data sources and metadata

    Attributes:
        _query_builder: Tool for building and validating data queries.
        _data_aggregator: Tool for aggregating data from sources.
        _anomaly_detector: Tool for detecting statistical anomalies.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Data Analyst Assistant agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-data-analyst-assistant", llm_gateway, pii_redactor)
        self.name = "AI Data Analyst Assistant"
        self._query_builder = QueryBuilderTool()
        self._data_aggregator = DataAggregatorTool()
        self._anomaly_detector = AnomalyDetectorTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "natural_language_query",
            "query_building",
            "query_validation",
            "data_aggregation",
            "cross_source_analysis",
            "anomaly_detection",
            "outlier_identification",
            "trend_analysis",
            "insight_generation",
            "statistical_analysis",
            "data_visualization_recommendations",
            "report_generation",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``generate_insights`` (default): Full 4-step analysis workflow
          - ``build_query``: Build structured data queries
          - ``aggregate_data``: Aggregate data from sources
          - ``detect_anomalies``: Detect anomalies in data
          - ``data_query``: Query data sources and metadata

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "generate_insights")

        if task_type == "generate_insights":
            return await self._handle_analysis_workflow(task_payload, context)
        elif task_type == "build_query":
            return await self._handle_build_query(task_payload, context)
        elif task_type == "aggregate_data":
            return await self._handle_aggregate_data(task_payload, context)
        elif task_type == "detect_anomalies":
            return await self._handle_detect_anomalies(task_payload, context)
        elif task_type == "data_query":
            return await self._handle_data_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full analysis workflow
    # ------------------------------------------------------------------

    async def _handle_analysis_workflow(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step data analysis workflow.

        Steps:
          1. Build and validate the data query
          2. Aggregate data from specified sources
          3. Detect anomalies in the aggregated data
          4. Generate actionable insights

        Args:
            task_payload: Analysis request with query, data sources,
                          and analysis parameters.
            context: Execution context with data, access permissions,
                     and policy overrides.

        Returns:
            Standardized result dict with comprehensive analysis output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", str(uuid.uuid4()))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Query Building
        query_result = await self._step_build_query(task_payload, context, policy)
        audit_events.append(self._audit_event(
            "data.query.executed",
            tenant_id,
            execution_id,
            detail="Data query built and validated",
        ))

        # Step 2: Data Aggregation
        aggregation_result = await self._step_aggregate_data(
            task_payload, context, query_result, policy
        )

        # Step 3: Anomaly Detection
        anomaly_result = await self._step_detect_anomalies(
            task_payload, context, aggregation_result, policy
        )
        audit_events.append(self._audit_event(
            "data.anomaly.detected",
            tenant_id,
            execution_id,
            detail="Anomaly detection completed",
            anomalies_detected=anomaly_result.get("anomalies_detected", 0),
        ))

        # Step 4: Insight Generation
        insight_result = await self._step_generate_insights(
            task_payload, context, query_result, aggregation_result,
            anomaly_result, policy
        )
        total_tokens += insight_result.get("tokens_used", 0)
        total_cost += insight_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "data.report.generated",
            tenant_id,
            execution_id,
            detail="Insights generated and report assembled",
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "query": {
                "query_id": query_result.get("query_id", ""),
                "structured_query": query_result.get("structured_query", ""),
                "data_source": query_result.get("data_source", ""),
                "is_valid": query_result.get("is_valid", True),
            },
            "aggregation": {
                "total_records": aggregation_result.get("total_records", 0),
                "data_sources": aggregation_result.get("data_sources", []),
                "statistics": aggregation_result.get("statistics", {}),
            },
            "anomalies": {
                "total_detected": anomaly_result.get("anomalies_detected", 0),
                "anomalies": anomaly_result.get("anomalies", []),
                "detection_method": anomaly_result.get("method", "z_score"),
            },
            "insights": insight_result.get("insights", []),
            "analysis_summary": insight_result.get("summary", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Only approved datasets queried. PII queries blocked. "
                "Row-level security enforced. No speculation beyond data."
            ),
        }

        # Determine result status
        anomaly_count = anomaly_result.get("anomalies_detected", 0)
        has_critical = any(
            a.get("severity") == "critical"
            for a in anomaly_result.get("anomalies", [])
        )

        if has_critical:
            result_status = "escalated"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if has_critical:
            next_action = "human_review"
        elif anomaly_count > 0:
            next_action = "investigation_recommended"
        elif insight_result.get("low_confidence_insights", 0) > 0:
            next_action = "validation_recommended"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "query_id": query_result.get("query_id", ""),
                "data_source": query_result.get("data_source", ""),
                "total_records": aggregation_result.get("total_records", 0),
                "anomalies_detected": anomaly_count,
                "insights_generated": len(insight_result.get("insights", [])),
            },
        )

        # Set fields for orchestration engine
        if has_critical:
            result["risk_level"] = "high"
            result["confidence"] = 0.9
        elif anomaly_count > 3:
            result["risk_level"] = "medium"
            result["confidence"] = 0.85
        else:
            result["risk_level"] = "low"
            result["confidence"] = 0.9

        return result

    # ------------------------------------------------------------------
    # Step 1: Query Building
    # ------------------------------------------------------------------

    async def _step_build_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Build and validate the data query.

        Translates the natural language request into a structured query,
        validates against access permissions and complexity limits.

        Args:
            task_payload: Task payload with query description.
            context: Execution context with data source access.
            policy: Resolved policy configuration.

        Returns:
            Dict with structured query, validation status, and complexity.
        """
        nl_query = (
            task_payload.get("query", "")
            or task_payload.get("question", "")
            or task_payload.get("natural_language_query", "")
        )
        data_source = task_payload.get("data_source", "default_warehouse")
        output_format = task_payload.get("output_format", "table")
        time_range = task_payload.get("time_range", {})
        filters = task_payload.get("filters", {})

        data_access = policy.get("data_access", {})
        query_limits = policy.get("query_limits", {})

        # Check data source access
        allowed_sources = data_access.get("allowed_sources", [])
        restricted_sources = data_access.get("restricted_sources", [])

        access_allowed = True
        access_notes: list[str] = []

        if restricted_sources and data_source in restricted_sources:
            access_allowed = False
            access_notes.append(
                f"Data source '{data_source}' is restricted. "
                f"Approval required."
            )

        if allowed_sources and data_source not in allowed_sources:
            access_notes.append(
                f"Data source '{data_source}' is not in the allowed list. "
                f"Query may be limited."
            )

        limit = task_payload.get(
            "limit",
            data_access.get("default_row_limit", 1000),
        )
        max_rows = data_access.get("max_rows_per_query", 100000)
        if limit > max_rows:
            limit = max_rows
            access_notes.append(
                f"Row limit capped at {max_rows} per policy."
            )

        if not nl_query:
            return {
                "query_id": "",
                "natural_language": "",
                "structured_query": "",
                "data_source": data_source,
                "is_valid": False,
                "access_allowed": False,
                "complexity": {},
                "details": "No query description provided.",
            }

        result = await self._query_builder.execute({
            "natural_language_query": nl_query,
            "data_source": data_source,
            "output_format": output_format,
            "time_range": time_range,
            "filters": filters,
            "limit": limit,
        })

        if not result.get("success"):
            return {
                "query_id": "",
                "natural_language": nl_query,
                "structured_query": "",
                "data_source": data_source,
                "is_valid": False,
                "access_allowed": access_allowed,
                "complexity": {},
                "details": f"Query building failed: {result.get('error')}",
            }

        data = result["data"]

        # Check complexity against policy limits
        complexity = data.get("complexity", {})
        max_complexity = query_limits.get("max_query_complexity", "high")
        complexity_levels = {"low": 0, "medium": 1, "high": 2}
        query_complexity = complexity.get("level", "low")

        complexity_allowed = (
            complexity_levels.get(query_complexity, 0)
            <= complexity_levels.get(max_complexity, 2)
        )

        if not complexity_allowed:
            access_notes.append(
                f"Query complexity '{query_complexity}' exceeds maximum "
                f"'{max_complexity}' allowed by policy."
            )

        return {
            "query_id": data.get("query_id", ""),
            "natural_language": nl_query,
            "structured_query": data.get("structured_query", ""),
            "data_source": data_source,
            "output_format": output_format,
            "is_valid": data.get("validation", {}).get("is_valid", True) and complexity_allowed,
            "access_allowed": access_allowed,
            "access_notes": access_notes,
            "validation": data.get("validation", {}),
            "complexity": complexity,
            "estimated_rows": data.get("estimated_rows", 0),
            "estimated_seconds": data.get("estimated_execution_seconds", 0),
            "details": data.get("summary", "Query built successfully."),
        }

    # ------------------------------------------------------------------
    # Step 2: Data Aggregation
    # ------------------------------------------------------------------

    async def _step_aggregate_data(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        query_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate data from specified sources.

        Executes the data aggregation based on the built query and
        source configuration.

        Args:
            task_payload: Task payload with aggregation parameters.
            context: Execution context with data.
            query_result: Result from the query building step.
            policy: Resolved policy configuration.

        Returns:
            Dict with aggregated data, statistics, and metadata.
        """
        data_sources = task_payload.get(
            "data_sources",
            [query_result.get("data_source", "default")],
        )
        aggregation_type = task_payload.get("aggregation_type", "summary")
        group_by = task_payload.get("group_by", [])
        metrics = task_payload.get("metrics", [])
        time_granularity = task_payload.get("time_granularity", "daily")
        data = context.get("data", task_payload.get("data", []))

        result = await self._data_aggregator.execute({
            "data_sources": data_sources,
            "aggregation_type": aggregation_type,
            "group_by": group_by,
            "metrics": metrics,
            "time_granularity": time_granularity,
            "data": data,
        })

        if not result.get("success"):
            return {
                "total_records": 0,
                "data_sources": data_sources,
                "statistics": {},
                "results": [],
                "details": f"Data aggregation failed: {result.get('error')}",
            }

        agg_data = result["data"]

        return {
            "total_records": agg_data.get("total_records", 0),
            "aggregation_type": agg_data.get("aggregation_type", aggregation_type),
            "data_sources": agg_data.get("data_sources", data_sources),
            "time_granularity": agg_data.get("time_granularity", time_granularity),
            "period": agg_data.get("period", {}),
            "results": agg_data.get("results", []),
            "statistics": agg_data.get("statistics", {}),
            "details": agg_data.get("summary", "Data aggregation completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Anomaly Detection
    # ------------------------------------------------------------------

    async def _step_detect_anomalies(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        aggregation_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Detect statistical anomalies in the aggregated data.

        Applies anomaly detection methods to the aggregated data using
        policy-defined thresholds and sensitivity settings.

        Args:
            task_payload: Task payload with detection parameters.
            context: Execution context.
            aggregation_result: Result from data aggregation step.
            policy: Resolved policy configuration.

        Returns:
            Dict with detected anomalies, severity, and statistical context.
        """
        anomaly_config = policy.get("anomaly_thresholds", {})
        threshold = task_payload.get(
            "threshold",
            anomaly_config.get("default_z_score_threshold", 2.0),
        )
        method = task_payload.get("method", "z_score")
        metric_field = task_payload.get("metric_field", "value")
        sensitivity = task_payload.get(
            "sensitivity",
            anomaly_config.get("sensitivity", "medium"),
        )

        # Prepare data for anomaly detection
        data = context.get("data", task_payload.get("data", []))

        # If no raw data, use aggregation results
        if not data and aggregation_result.get("results"):
            data = aggregation_result["results"]

        min_points = anomaly_config.get("min_data_points_for_detection", 30)

        result = await self._anomaly_detector.execute({
            "data": data,
            "metric_field": metric_field,
            "threshold": threshold,
            "method": method,
            "sensitivity": sensitivity,
        })

        if not result.get("success"):
            return {
                "anomalies_detected": 0,
                "anomalies": [],
                "statistics": {},
                "method": method,
                "threshold": threshold,
                "details": f"Anomaly detection failed: {result.get('error')}",
            }

        anom_data = result["data"]

        # Check for critical anomalies
        critical_threshold = anomaly_config.get("critical_z_score_threshold", 3.0)
        critical_anomalies = [
            a for a in anom_data.get("anomalies", [])
            if a.get("z_score", 0) > critical_threshold
        ]

        # Auto-alert check
        auto_alert = (
            anomaly_config.get("auto_alert_on_critical", True)
            and len(critical_anomalies) > 0
        )

        return {
            "anomalies_detected": anom_data.get("anomalies_detected", 0),
            "anomalies": anom_data.get("anomalies", []),
            "critical_anomalies": critical_anomalies,
            "critical_count": len(critical_anomalies),
            "statistics": anom_data.get("statistics", {}),
            "method": method,
            "threshold": threshold,
            "sensitivity": sensitivity,
            "total_data_points": anom_data.get("total_data_points", 0),
            "auto_alert_triggered": auto_alert,
            "sufficient_data": anom_data.get("total_data_points", 0) >= min_points,
            "details": anom_data.get("summary", "Anomaly detection completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: Insight Generation
    # ------------------------------------------------------------------

    async def _step_generate_insights(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        query_result: dict[str, Any],
        aggregation_result: dict[str, Any],
        anomaly_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate actionable insights from the analysis using the LLM.

        Synthesizes query, aggregation, and anomaly data into
        business-relevant insights with confidence levels.

        Args:
            task_payload: Original task payload.
            context: Execution context.
            query_result: Query building result.
            aggregation_result: Data aggregation result.
            anomaly_result: Anomaly detection result.
            policy: Resolved policy configuration.

        Returns:
            Dict with insights, summary, tokens_used, and cost_usd.
        """
        insight_config = policy.get("insight_confidence", {})
        max_insights = insight_config.get("max_insights_per_analysis", 10)

        analysis_context = json.dumps(
            {
                "query": {
                    "description": query_result.get("natural_language", ""),
                    "data_source": query_result.get("data_source", ""),
                },
                "aggregation": {
                    "total_records": aggregation_result.get("total_records", 0),
                    "statistics": aggregation_result.get("statistics", {}),
                    "top_results": aggregation_result.get("results", [])[:5],
                },
                "anomalies": {
                    "total_detected": anomaly_result.get("anomalies_detected", 0),
                    "critical_count": anomaly_result.get("critical_count", 0),
                    "top_anomalies": anomaly_result.get("anomalies", [])[:5],
                    "statistics": anomaly_result.get("statistics", {}),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Data Analyst Assistant. Generate actionable "
                    "data insights based on the analysis context below. "
                    "Follow these rules:\n"
                    "- Provide 3-5 key insights from the data\n"
                    "- Each insight should have: title, description, confidence, "
                    "category, and recommended action\n"
                    "- Highlight anomalies and their business implications\n"
                    "- Identify trends and patterns\n"
                    "- Suggest follow-up analyses when applicable\n"
                    "- Use data-driven language with specific numbers\n"
                    "- Be concise but thorough\n"
                    "- Respond in JSON with keys: insights (array), summary, "
                    "follow_up_analyses\n"
                    f"- Maximum {max_insights} insights"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analysis request: "
                    f"{task_payload.get('query', task_payload.get('question', 'General analysis'))}\n\n"
                    f"Analysis data:\n{analysis_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        insights: list[dict[str, Any]] = []
        summary = ""
        follow_up: list[str] = []

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                insights = parsed.get("insights", [])
                summary = parsed.get("summary", "")
                follow_up = parsed.get("follow_up_analyses", [])
            except json.JSONDecodeError:
                pass

        # Fallback insights
        if not insights:
            insights = self._generate_fallback_insights(
                query_result, aggregation_result, anomaly_result
            )

        if not summary:
            summary = self._generate_fallback_summary(
                aggregation_result, anomaly_result, insights
            )

        # Assess insight confidence
        min_confidence = insight_config.get("min_confidence_threshold", 0.7)
        low_confidence_count = sum(
            1 for i in insights
            if i.get("confidence", 0.8) < min_confidence
        )

        return {
            "insights": insights[:max_insights],
            "total_insights": len(insights),
            "summary": summary,
            "follow_up_analyses": follow_up,
            "low_confidence_insights": low_confidence_count,
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _generate_fallback_insights(
        query_result: dict[str, Any],
        aggregation_result: dict[str, Any],
        anomaly_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate fallback insights when LLM parsing fails.

        Args:
            query_result: Query building result.
            aggregation_result: Data aggregation result.
            anomaly_result: Anomaly detection result.

        Returns:
            List of insight dicts.
        """
        insights: list[dict[str, Any]] = []

        # Insight from aggregation statistics
        statistics = aggregation_result.get("statistics", {})
        total_records = aggregation_result.get("total_records", 0)

        if total_records > 0:
            insights.append({
                "title": "Data Volume Assessment",
                "description": (
                    f"Analysis covers {total_records:,} records across "
                    f"{len(aggregation_result.get('data_sources', []))} source(s). "
                    f"Dataset is {'large' if total_records > 10000 else 'moderate' if total_records > 1000 else 'small'}."
                ),
                "confidence": 0.95,
                "category": "data_quality",
                "recommended_action": (
                    "Verify data completeness and recency before drawing conclusions."
                ),
            })

        # Insight from statistics
        for metric_name, stats in statistics.items():
            if isinstance(stats, dict) and "average" in stats:
                insights.append({
                    "title": f"{metric_name.replace('_', ' ').title()} Analysis",
                    "description": (
                        f"The '{metric_name}' metric shows an average of "
                        f"{stats.get('average', 0):,.2f} (range: "
                        f"{stats.get('min', 0):,.2f} to {stats.get('max', 0):,.2f})."
                    ),
                    "confidence": 0.85,
                    "category": "statistical",
                    "recommended_action": (
                        f"Investigate variations in {metric_name} across segments."
                    ),
                })

        # Insight from anomalies
        anomaly_count = anomaly_result.get("anomalies_detected", 0)
        if anomaly_count > 0:
            critical = anomaly_result.get("critical_count", 0)
            insights.append({
                "title": "Anomaly Alert",
                "description": (
                    f"{anomaly_count} anomaly(ies) detected in the dataset"
                    + (f", including {critical} critical" if critical > 0 else "")
                    + ". These represent statistically significant deviations "
                    f"from expected patterns."
                ),
                "confidence": 0.90,
                "category": "anomaly",
                "recommended_action": (
                    "Investigate root causes of detected anomalies. "
                    + ("Critical anomalies require immediate review." if critical > 0 else "")
                ),
            })
        else:
            insights.append({
                "title": "Data Stability",
                "description": (
                    "No statistically significant anomalies detected. "
                    "Data patterns are within expected ranges."
                ),
                "confidence": 0.85,
                "category": "data_quality",
                "recommended_action": "Continue regular monitoring cadence.",
            })

        return insights

    @staticmethod
    def _generate_fallback_summary(
        aggregation_result: dict[str, Any],
        anomaly_result: dict[str, Any],
        insights: list[dict[str, Any]],
    ) -> str:
        """Generate a fallback analysis summary.

        Args:
            aggregation_result: Data aggregation result.
            anomaly_result: Anomaly detection result.
            insights: Generated insights.

        Returns:
            Summary string.
        """
        total_records = aggregation_result.get("total_records", 0)
        anomaly_count = anomaly_result.get("anomalies_detected", 0)
        insight_count = len(insights)

        return (
            f"Analysis of {total_records:,} records complete. "
            f"{anomaly_count} anomaly(ies) detected. "
            f"{insight_count} insight(s) generated. "
            + (
                "Critical anomalies require attention. "
                if anomaly_result.get("critical_count", 0) > 0
                else "No critical issues found. "
            )
        )

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_build_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct query building request.

        Builds a structured data query from natural language without
        running the full analysis workflow.

        Args:
            task_payload: Query building parameters.
            context: Execution context.

        Returns:
            Standardized result with built query and validation.
        """
        policy = self._resolve_policy(context)

        query_result = await self._step_build_query(task_payload, context, policy)

        if not query_result.get("is_valid"):
            return self.format_result(
                status="completed",
                output={
                    **query_result,
                    "warning": "Query validation issues detected.",
                },
                tokens_used=0,
                cost_usd=0.0,
                next_action="query_review" if not query_result.get("access_allowed") else None,
            )

        # Generate LLM explanation of the query
        llm_result = await self._generate_query_explanation(query_result)

        return self.format_result(
            status="completed",
            output={
                **query_result,
                "query_explanation": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    async def _handle_aggregate_data(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct data aggregation request.

        Aggregates data from specified sources without the full
        analysis workflow.

        Args:
            task_payload: Aggregation parameters.
            context: Execution context with data.

        Returns:
            Standardized result with aggregated data.
        """
        result = await self._data_aggregator.execute({
            "data_sources": task_payload.get("data_sources", ["default"]),
            "aggregation_type": task_payload.get("aggregation_type", "summary"),
            "group_by": task_payload.get("group_by", []),
            "metrics": task_payload.get("metrics", []),
            "time_granularity": task_payload.get("time_granularity", "daily"),
            "data": context.get("data", task_payload.get("data", [])),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Data aggregation failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM insight
        llm_result = await self._generate_aggregation_insight(data)

        return self.format_result(
            status="completed",
            output={
                **data,
                "aggregation_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    async def _handle_detect_anomalies(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct anomaly detection request.

        Detects anomalies in provided data without the full workflow.

        Args:
            task_payload: Anomaly detection parameters.
            context: Execution context with data.

        Returns:
            Standardized result with anomaly detection results.
        """
        policy = self._resolve_policy(context)
        anomaly_config = policy.get("anomaly_thresholds", {})

        result = await self._anomaly_detector.execute({
            "data": context.get("data", task_payload.get("data", [])),
            "metric_field": task_payload.get("metric_field", "value"),
            "threshold": task_payload.get(
                "threshold",
                anomaly_config.get("default_z_score_threshold", 2.0),
            ),
            "method": task_payload.get("method", "z_score"),
            "sensitivity": task_payload.get(
                "sensitivity",
                anomaly_config.get("sensitivity", "medium"),
            ),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Anomaly detection failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Check for critical anomalies
        critical_threshold = anomaly_config.get("critical_z_score_threshold", 3.0)
        critical_anomalies = [
            a for a in data.get("anomalies", [])
            if a.get("z_score", 0) > critical_threshold
        ]

        auto_alert = (
            anomaly_config.get("auto_alert_on_critical", True)
            and len(critical_anomalies) > 0
        )

        # Generate LLM insight
        llm_result = await self._generate_anomaly_insight(data, policy)

        return self.format_result(
            status="escalated" if auto_alert else "completed",
            output={
                **data,
                "critical_anomalies": critical_anomalies,
                "critical_count": len(critical_anomalies),
                "auto_alert_triggered": auto_alert,
                "anomaly_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="human_review" if auto_alert else None,
        )

    async def _handle_data_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle data source and metadata query.

        Returns information about available data sources, schemas,
        and recent query history.

        Args:
            task_payload: Data query parameters.
            context: Execution context.

        Returns:
            Standardized result with data source information.
        """
        policy = self._resolve_policy(context)
        query_type = task_payload.get("query_type", "sources")
        data_access = policy.get("data_access", {})

        if query_type == "sources":
            sources = self._get_available_sources(data_access)

            # Generate LLM insight
            llm_result = await self._generate_source_insight(sources, data_access)

            return self.format_result(
                status="completed",
                output={
                    "available_sources": sources,
                    "total_sources": len(sources),
                    "restricted_sources": data_access.get("restricted_sources", []),
                    "source_insight": llm_result.get("content", ""),
                    "details": f"{len(sources)} data source(s) available.",
                },
                tokens_used=llm_result.get("tokens_used", 0),
                cost_usd=llm_result.get("cost_usd", 0.0),
            )

        if query_type == "schema":
            source_name = task_payload.get("data_source", "")
            schema = self._get_mock_schema(source_name)
            return self.format_result(
                status="completed",
                output={
                    "data_source": source_name,
                    "schema": schema,
                    "details": f"Schema for '{source_name}'.",
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        if query_type == "capabilities":
            return self.format_result(
                status="completed",
                output={
                    "capabilities": self.get_capabilities(),
                    "supported_methods": ["z_score", "iqr", "moving_average"],
                    "supported_aggregations": [
                        "sum", "count", "average", "min", "max",
                        "percentile", "group_by",
                    ],
                    "output_formats": ["table", "json", "csv", "chart"],
                    "details": "Data analysis capabilities overview.",
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        return self.format_result(
            status="completed",
            output={
                "query_type": query_type,
                "details": f"Query type '{query_type}' not recognized. "
                           f"Supported: sources, schema, capabilities.",
            },
            tokens_used=0,
            cost_usd=0.0,
        )

    @staticmethod
    def _get_available_sources(
        data_access: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Get list of available data sources.

        Args:
            data_access: Data access policy configuration.

        Returns:
            List of data source information dicts.
        """
        allowed = data_access.get("allowed_sources", [])

        source_info = {
            "sales_warehouse": {
                "name": "Sales Data Warehouse",
                "type": "data_warehouse",
                "description": "Historical sales transactions, revenue, and order data.",
                "tables": ["orders", "products", "customers", "revenue"],
                "refresh_frequency": "hourly",
            },
            "operations_db": {
                "name": "Operations Database",
                "type": "operational_db",
                "description": "Operational metrics, logistics, and inventory data.",
                "tables": ["shipments", "inventory", "warehouses", "routes"],
                "refresh_frequency": "real_time",
            },
            "hr_analytics": {
                "name": "HR Analytics",
                "type": "analytics_db",
                "description": "Team performance, headcount, and utilization data.",
                "tables": ["employees", "performance", "utilization", "hiring"],
                "refresh_frequency": "daily",
            },
            "finance_ledger": {
                "name": "Finance Ledger",
                "type": "financial_db",
                "description": "Financial transactions, budgets, and forecasts.",
                "tables": ["transactions", "budgets", "forecasts", "expenses"],
                "refresh_frequency": "daily",
            },
            "customer_360": {
                "name": "Customer 360",
                "type": "analytics_db",
                "description": "Customer profiles, interactions, and satisfaction data.",
                "tables": ["profiles", "interactions", "satisfaction", "segments"],
                "refresh_frequency": "hourly",
            },
        }

        sources = []
        for source_id in allowed:
            info = source_info.get(source_id, {
                "name": source_id.replace("_", " ").title(),
                "type": "unknown",
                "description": f"Data source: {source_id}",
                "tables": [],
                "refresh_frequency": "unknown",
            })
            sources.append({
                "source_id": source_id,
                **info,
                "access": "allowed",
            })

        return sources

    @staticmethod
    def _get_mock_schema(source_name: str) -> dict[str, Any]:
        """Get mock schema for a data source.

        Args:
            source_name: Data source name.

        Returns:
            Schema description dict.
        """
        schemas = {
            "sales_warehouse": {
                "orders": {
                    "order_id": "VARCHAR(50) PRIMARY KEY",
                    "customer_id": "VARCHAR(50)",
                    "order_date": "TIMESTAMP",
                    "total_amount": "DECIMAL(10,2)",
                    "status": "VARCHAR(20)",
                    "region": "VARCHAR(50)",
                },
                "products": {
                    "product_id": "VARCHAR(50) PRIMARY KEY",
                    "name": "VARCHAR(200)",
                    "category": "VARCHAR(50)",
                    "price": "DECIMAL(10,2)",
                    "stock_quantity": "INTEGER",
                },
            },
            "operations_db": {
                "shipments": {
                    "shipment_id": "VARCHAR(50) PRIMARY KEY",
                    "order_id": "VARCHAR(50)",
                    "carrier": "VARCHAR(50)",
                    "status": "VARCHAR(20)",
                    "origin": "VARCHAR(100)",
                    "destination": "VARCHAR(100)",
                    "created_at": "TIMESTAMP",
                },
            },
        }

        return schemas.get(source_name, {
            "note": f"Schema not available for '{source_name}'. "
                    f"Contact data engineering team."
        })

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_query_explanation(
        self,
        query_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a human-readable query explanation using the LLM.

        Args:
            query_result: Query building result.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Data Analyst Assistant. Explain the "
                    "generated query in 2-3 sentences for a non-technical "
                    "audience. Include what data will be retrieved, from "
                    "which source, and any filters applied."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query_result.get('natural_language', 'N/A')}\n"
                    f"Structured query:\n{query_result.get('structured_query', 'N/A')}\n"
                    f"Data source: {query_result.get('data_source', 'N/A')}\n"
                    f"Estimated rows: {query_result.get('estimated_rows', 'N/A')}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("explanation", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            content = (
                f"This query retrieves data from "
                f"'{query_result.get('data_source', 'N/A')}' based on your request: "
                f"'{query_result.get('natural_language', 'N/A')}'. "
                f"Estimated result: {query_result.get('estimated_rows', 'N/A')} rows."
            )

        llm_result["content"] = content
        return llm_result

    async def _generate_aggregation_insight(
        self,
        aggregation_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate aggregation insight using the LLM.

        Args:
            aggregation_data: Aggregation result data.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Data Analyst Assistant. Provide a brief "
                    "insight (2-3 sentences) about the aggregated data. "
                    "Highlight key metrics and notable patterns."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Records: {aggregation_data.get('total_records', 0):,}\n"
                    f"Sources: {aggregation_data.get('data_sources', [])}\n"
                    f"Statistics: {json.dumps(aggregation_data.get('statistics', {}), default=str)}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("insight", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            total = aggregation_data.get("total_records", 0)
            content = (
                f"Aggregated {total:,} records from "
                f"{len(aggregation_data.get('data_sources', []))} source(s). "
                f"Review the statistics for detailed metrics."
            )

        llm_result["content"] = content
        return llm_result

    async def _generate_anomaly_insight(
        self,
        anomaly_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate anomaly detection insight using the LLM.

        Args:
            anomaly_data: Anomaly detection data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Data Analyst Assistant. Summarize the "
                    "anomaly detection results in 2-3 sentences. Highlight "
                    "the most significant anomalies and their potential "
                    "business impact."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Data points: {anomaly_data.get('total_data_points', 0)}\n"
                    f"Anomalies: {anomaly_data.get('anomalies_detected', 0)}\n"
                    f"Method: {anomaly_data.get('detection_config', {}).get('method', 'z_score')}\n"
                    f"Mean: {anomaly_data.get('statistics', {}).get('mean', 'N/A')}\n"
                    f"Std Dev: {anomaly_data.get('statistics', {}).get('std_dev', 'N/A')}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("insight", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            count = anomaly_data.get("anomalies_detected", 0)
            total = anomaly_data.get("total_data_points", 0)
            content = (
                f"Analyzed {total} data points: {count} anomaly(ies) detected. "
            )
            if count > 0:
                content += "Review flagged data points for potential issues."
            else:
                content += "Data is within expected ranges."

        llm_result["content"] = content
        return llm_result

    async def _generate_source_insight(
        self,
        sources: list[dict[str, Any]],
        data_access: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate data source insight using the LLM.

        Args:
            sources: Available data sources.
            data_access: Data access policy.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Data Analyst Assistant. Briefly describe "
                    "the available data sources (1-2 sentences). Mention the "
                    "variety of data and any access restrictions."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Available sources: {len(sources)}\n"
                    f"Types: {', '.join(set(s.get('type', '') for s in sources))}\n"
                    f"Restricted: {len(data_access.get('restricted_sources', []))}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("insight", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            restricted = len(data_access.get("restricted_sources", []))
            content = (
                f"{len(sources)} data source(s) available for analysis. "
                f"{restricted} source(s) are restricted and require approval."
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

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(event_type, tenant_id, execution_id, **extra):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-data-analyst-assistant",
        }
        event.update(extra)
        return event
