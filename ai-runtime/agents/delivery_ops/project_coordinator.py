"""AI Project Coordinator Agent -- manages project execution and reporting.

Implements the 4-step project management workflow:
  1. TASK TRACKING -- Track and update project tasks and assignments
  2. MILESTONE MONITORING -- Monitor milestone progress and deadlines
  3. RISK DETECTION -- Assess and score project risks
  4. STATUS REPORTING -- Generate comprehensive project status reports

Also handles direct task updates, milestone checks, risk assessments,
and resource queries.

Worker ID: ai-project-coordinator
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
    MilestoneMonitorTool,
    ProjectRiskTool,
    TaskTrackerTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "methodology": {
        "type": "agile",
        "sprint_duration_weeks": 2,
        "sprint_start_day": "Monday",
        "ceremonies": [
            "daily_standup",
            "sprint_planning",
            "sprint_review",
            "retrospective",
        ],
        "allow_waterfall_fallback": True,
    },
    "sprint_settings": {
        "max_story_points_per_sprint": 60,
        "velocity_window_sprints": 5,
        "carry_over_limit_percent": 15,
        "auto_assign_unassigned": False,
        "require_estimation_before_sprint": True,
    },
    "milestone_warnings": {
        "warning_threshold_days": 7,
        "critical_threshold_days": 3,
        "overdue_escalation": True,
        "notify_stakeholders": True,
    },
    "risk_matrix": {
        "critical_threshold": 0.7,
        "high_threshold": 0.5,
        "medium_threshold": 0.3,
        "max_acceptable_risk_score": 0.6,
        "auto_escalate_critical": True,
    },
    "reporting": {
        "frequency": "weekly",
        "include_risk_summary": True,
        "include_burndown": True,
        "include_resource_utilization": True,
        "stakeholder_distribution": True,
    },
    "resource_utilization": {
        "target_utilization_pct": 80,
        "overallocation_threshold_pct": 100,
        "underallocation_threshold_pct": 50,
        "max_concurrent_tasks_per_person": 5,
    },
    "sla": {
        "status_report_delivery_hours": 4,
        "risk_assessment_frequency_days": 7,
        "task_update_frequency_hours": 24,
    },
}


class ProjectCoordinatorAgent(BaseAgent):
    """AI Project Coordinator Agent -- manages project execution and reporting.

    Executes a four-step workflow for project management:
      1. Track tasks to understand current work item status
      2. Monitor milestones against deadlines and progress targets
      3. Assess project risks using severity matrix
      4. Generate comprehensive status reports

    Also supports direct operations via task type routing:
      - ``update_tasks``: Update task status and assignments
      - ``check_milestones``: Check milestone deadlines and progress
      - ``assess_risks``: Perform project risk assessment
      - ``generate_status_report`` (default): Full 4-step workflow
      - ``resource_query``: Query resource utilization

    Attributes:
        _task_tracker: Tool for tracking and updating project tasks.
        _milestone_monitor: Tool for monitoring milestone deadlines.
        _project_risk: Tool for assessing project risks.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Project Coordinator agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-project-coordinator", llm_gateway, pii_redactor)
        self.name = "AI Project Coordinator"
        self._task_tracker = TaskTrackerTool()
        self._milestone_monitor = MilestoneMonitorTool()
        self._project_risk = ProjectRiskTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "task_tracking",
            "task_assignment",
            "milestone_monitoring",
            "deadline_management",
            "risk_assessment",
            "risk_scoring",
            "status_reporting",
            "resource_utilization_analysis",
            "burndown_tracking",
            "dependency_analysis",
            "stakeholder_notifications",
            "sprint_management",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on
        ``task_payload['task_type']`` (falls back to ``task_payload['type']``).
        Supported task types:
          - ``handle_inquiry`` (default): General project inquiry
          - ``plan_sprint``: Sprint planning and capacity allocation
          - ``track_milestones``: Milestone tracking and risk assessment
          - ``generate_status_report``: Full 4-step status report workflow
          - ``update_tasks``: Update task status and assignments
          - ``assess_risks``: Perform risk assessment
          - ``resource_query``: Query resource utilization

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get(
            "task_type", task_payload.get("type", "handle_inquiry")
        )

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "plan_sprint":
            return await self._handle_plan_sprint(task_payload, context)
        elif task_type == "track_milestones":
            return await self._handle_check_milestones(task_payload, context)
        elif task_type == "generate_status_report":
            return await self._handle_status_report_workflow(task_payload, context)
        elif task_type == "update_tasks":
            return await self._handle_update_tasks(task_payload, context)
        elif task_type == "assess_risks":
            return await self._handle_assess_risks(task_payload, context)
        elif task_type == "resource_query":
            return await self._handle_resource_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Handle general inquiry
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a general project management inquiry using the LLM.

        Answers questions about task status, project health, team workload,
        sprint progress, risk assessments, and methodology best practices.

        Args:
            task_payload: Inquiry payload with ``question`` or ``message``.
            context: Execution context with optional project data, tasks,
                     milestones, and team information.

        Returns:
            Standardized result dict with the inquiry response.
        """
        start_time = time.time()
        question = (
            task_payload.get("question")
            or task_payload.get("message")
            or task_payload.get("inquiry", "")
        )

        if not question:
            return self.format_result(
                "failed",
                {"error": "No question or message provided in task payload."},
                tokens_used=0,
                cost_usd=0.0,
            )

        policy = self._resolve_policy(context)

        # Gather context
        context_parts: list[str] = []

        tasks = context.get("tasks", [])
        if tasks:
            total = len(tasks)
            completed = sum(
                1 for t in tasks
                if (t.get("status") or "").lower() in ("completed", "done")
            )
            in_progress = sum(
                1 for t in tasks
                if (t.get("status") or "").lower() in ("in_progress", "active")
            )
            blocked = sum(
                1 for t in tasks
                if (t.get("status") or "").lower() == "blocked"
            )
            context_parts.append(
                f"Tasks: {total} total, {completed} completed, "
                f"{in_progress} in progress, {blocked} blocked"
            )

        milestones = context.get("milestones", [])
        if milestones:
            context_parts.append(
                f"Milestones: {len(milestones)} tracked"
            )
            for m in milestones[:5]:
                context_parts.append(
                    f"  - {m.get('name', 'N/A')}: {m.get('status', 'unknown')} "
                    f"(due: {m.get('due_date', 'N/A')})"
                )

        project = context.get("project", {})
        if project:
            context_parts.append(
                f"Project: {project.get('name', 'N/A')} | "
                f"Phase: {project.get('phase', 'N/A')} | "
                f"Budget: ${project.get('budget', 0):,.2f}"
            )

        context_str = (
            "\n".join(context_parts)
            if context_parts
            else "No project context available."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Project Coordinator for KreupAI. Answer "
                    "the user's project management inquiry based on the "
                    "context provided. Follow these rules:\n"
                    "- Be concise and professional\n"
                    "- Reference specific task and milestone data when available\n"
                    "- If you cannot answer from available context, say so "
                    "clearly and suggest what information is needed\n"
                    "- Never disclose internal system details or confidence "
                    "scores\n"
                    "- Respond in valid JSON with keys: response, confidence, "
                    "follow_up_needed, follow_up_questions"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Available context:\n{context_str}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        response_text = content
        confidence = 0.8
        follow_up_needed = False
        follow_up_questions: list[str] = []

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                response_text = parsed.get("response", content)
                confidence = parsed.get("confidence", 0.8)
                follow_up_needed = parsed.get("follow_up_needed", False)
                follow_up_questions = parsed.get("follow_up_questions", [])
            except json.JSONDecodeError:
                pass

        if not response_text or response_text.startswith("{"):
            response_text = (
                "I can help with your project management inquiry. Please "
                "provide more details such as the project ID, specific "
                "task or milestone you are asking about."
            )
            confidence = 0.5
            follow_up_needed = True

        duration_ms = int((time.time() - start_time) * 1000)

        output: dict[str, Any] = {
            "response": response_text,
            "inquiry_type": "project_general",
            "confidence": confidence,
            "follow_up_needed": follow_up_needed,
            "follow_up_questions": follow_up_questions,
            "context_used": bool(context_parts),
            "processing_duration_ms": duration_ms,
        }

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            next_action="follow_up" if follow_up_needed else None,
        )

        result["confidence"] = confidence
        result["risk_level"] = "low"
        return result

    # ------------------------------------------------------------------
    # Sprint planning handler
    # ------------------------------------------------------------------

    async def _handle_plan_sprint(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle sprint planning request.

        Analyses backlog, team velocity, and capacity to recommend
        sprint scope and task assignments.

        Args:
            task_payload: Sprint planning parameters including sprint_id,
                          backlog items, and team capacity.
            context: Execution context with project data.

        Returns:
            Standardized result with sprint plan and recommendations.
        """
        start_time = time.time()
        policy = self._resolve_policy(context)

        sprint_settings = policy.get("sprint_settings", {})
        max_points = sprint_settings.get("max_story_points_per_sprint", 60)
        carry_over_limit = sprint_settings.get("carry_over_limit_percent", 15)

        sprint_id = task_payload.get(
            "sprint_id",
            f"SPR-{uuid.uuid4().hex[:6].upper()}",
        )
        backlog = task_payload.get("backlog", context.get("backlog", []))
        team = context.get("team", [])
        velocity_history = context.get("velocity_history", [])

        # Calculate average velocity
        if velocity_history:
            window = sprint_settings.get("velocity_window_sprints", 5)
            recent = velocity_history[-window:]
            avg_velocity = sum(recent) / len(recent) if recent else max_points
        else:
            avg_velocity = max_points * 0.75  # Conservative default

        recommended_points = min(avg_velocity, max_points)

        # Sort backlog by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_backlog = sorted(
            backlog,
            key=lambda x: priority_order.get(
                (x.get("priority") or "medium").lower(), 2
            ),
        )

        # Select items for sprint
        selected: list[dict[str, Any]] = []
        total_points = 0
        carry_over: list[dict[str, Any]] = []

        for item in sorted_backlog:
            points = item.get("story_points", item.get("points", 0))
            is_carry_over = item.get("carry_over", False)

            if is_carry_over:
                carry_over.append(item)

            if total_points + points <= recommended_points:
                selected.append(item)
                total_points += points

        carry_over_points = sum(
            i.get("story_points", i.get("points", 0)) for i in carry_over
        )
        carry_over_percent = (
            (carry_over_points / recommended_points * 100)
            if recommended_points > 0
            else 0
        )
        carry_over_exceeded = carry_over_percent > carry_over_limit

        # Generate sprint plan summary using LLM
        sprint_context = json.dumps(
            {
                "sprint_id": sprint_id,
                "selected_items": len(selected),
                "total_points": total_points,
                "recommended_capacity": recommended_points,
                "average_velocity": avg_velocity,
                "carry_over_percent": carry_over_percent,
                "team_size": len(team),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Project Coordinator. Generate a sprint "
                    "planning summary in 3-5 sentences. Include recommended "
                    "capacity, key items, and any concerns about carry-over "
                    "or velocity trends. Be concise and actionable."
                ),
            },
            {
                "role": "user",
                "content": f"Sprint planning data:\n{sprint_context}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        plan_summary = content
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                plan_summary = parsed.get(
                    "summary", parsed.get("response", content)
                )
            except json.JSONDecodeError:
                pass

        if not plan_summary or plan_summary.startswith("{"):
            plan_summary = (
                f"Sprint {sprint_id}: {len(selected)} items selected "
                f"({total_points} points of {recommended_points} capacity). "
                f"Average velocity: {avg_velocity:.0f} points/sprint."
            )
            if carry_over_exceeded:
                plan_summary += (
                    f" WARNING: Carry-over at {carry_over_percent:.1f}% "
                    f"exceeds {carry_over_limit}% limit."
                )

        duration_ms = int((time.time() - start_time) * 1000)

        warnings: list[str] = []
        if carry_over_exceeded:
            warnings.append(
                f"Carry-over ({carry_over_percent:.1f}%) exceeds limit "
                f"({carry_over_limit}%)."
            )
        if total_points > recommended_points:
            warnings.append(
                f"Selected points ({total_points}) exceed recommended "
                f"capacity ({recommended_points})."
            )

        output: dict[str, Any] = {
            "sprint_id": sprint_id,
            "selected_items": [
                {
                    "task_id": i.get("task_id") or i.get("id", ""),
                    "name": i.get("name") or i.get("title", ""),
                    "points": i.get("story_points", i.get("points", 0)),
                    "priority": i.get("priority", "medium"),
                    "assignee": i.get("assignee", "Unassigned"),
                }
                for i in selected
            ],
            "total_points": total_points,
            "recommended_capacity": recommended_points,
            "average_velocity": round(avg_velocity, 1),
            "carry_over": {
                "items": len(carry_over),
                "points": carry_over_points,
                "percent": round(carry_over_percent, 1),
                "limit_exceeded": carry_over_exceeded,
            },
            "backlog_remaining": len(sorted_backlog) - len(selected),
            "plan_summary": plan_summary,
            "warnings": warnings,
            "processing_duration_ms": duration_ms,
        }

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            next_action="sprint_review" if warnings else None,
            metadata={
                "sprint_id": sprint_id,
                "total_points": total_points,
                "capacity": recommended_points,
            },
        )

        result["confidence"] = 0.85
        result["risk_level"] = "medium" if warnings else "low"
        return result

    # ------------------------------------------------------------------
    # Full status report workflow
    # ------------------------------------------------------------------

    async def _handle_status_report_workflow(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step project status reporting workflow.

        Steps:
          1. Track tasks to understand current work status
          2. Monitor milestones against deadlines
          3. Assess project risks
          4. Generate comprehensive status report

        Args:
            task_payload: Project data including project ID and filters.
            context: Execution context with tasks, milestones, risk factors,
                     and policy overrides.

        Returns:
            Standardized result dict with detailed project status output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", "unknown")
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Task Tracking
        task_result = await self._step_track_tasks(task_payload, context)
        audit_events.append(self._audit_event(
            "project.action.tracked", tenant_id, execution_id,
            total_tasks=task_result.get("total_tasks", 0),
            blocked_count=task_result.get("blocked_count", 0),
        ))

        # Step 2: Milestone Monitoring
        milestone_result = await self._step_monitor_milestones(
            task_payload, context, policy
        )

        # Step 3: Risk Detection
        risk_result = await self._step_assess_risks(
            task_payload, context, task_result, milestone_result, policy
        )
        audit_events.append(self._audit_event(
            "project.risk.detected", tenant_id, execution_id,
            overall_severity=risk_result.get("overall_severity", "low"),
            critical_risks=risk_result.get("critical_risks", 0),
            high_risks=risk_result.get("high_risks", 0),
        ))

        # Step 4: Status Reporting
        report_result = await self._step_generate_report(
            task_payload, context, task_result, milestone_result,
            risk_result, policy
        )
        total_tokens += report_result.get("tokens_used", 0)
        total_cost += report_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "project.status.generated", tenant_id, execution_id,
            report_type=report_result.get("report_type", "weekly"),
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "task_summary": {
                "total_tasks": task_result.get("total_tasks", 0),
                "by_status": task_result.get("by_status", {}),
                "by_priority": task_result.get("by_priority", {}),
                "blocked_tasks": task_result.get("blocked_tasks", []),
            },
            "milestone_summary": {
                "total_milestones": milestone_result.get("total_milestones", 0),
                "completed": milestone_result.get("completed", 0),
                "at_risk": milestone_result.get("at_risk_count", 0),
                "overall_progress": milestone_result.get("overall_progress", 0),
                "at_risk_milestones": milestone_result.get("at_risk", []),
            },
            "risk_summary": {
                "overall_risk_score": risk_result.get("overall_risk_score", 0),
                "overall_severity": risk_result.get("overall_severity", "low"),
                "total_risks": risk_result.get("total_risks", 0),
                "critical_risks": risk_result.get("critical_risks", 0),
                "high_risks": risk_result.get("high_risks", 0),
            },
            "status_report": report_result.get("report", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Project scope changes never auto-approved. "
                "Budget reallocation always requires PM approval."
            ),
        }

        # Determine result status
        overall_risk = risk_result.get("overall_severity", "low")
        at_risk_count = milestone_result.get("at_risk_count", 0)

        if overall_risk in ("critical",) or at_risk_count > 2:
            result_status = "escalated"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if overall_risk == "critical":
            next_action = "human_review"
        elif at_risk_count > 0:
            next_action = "stakeholder_notification"
        elif risk_result.get("high_risks", 0) > 0:
            next_action = "risk_mitigation"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "project_id": task_payload.get("project_id", ""),
                "overall_risk": overall_risk,
                "at_risk_milestones": at_risk_count,
                "total_tasks": task_result.get("total_tasks", 0),
                "report_generated": True,
            },
        )

        # Set fields for orchestration engine
        if overall_risk == "critical":
            result["risk_level"] = "critical"
            result["confidence"] = 0.6
        elif overall_risk == "high":
            result["risk_level"] = "high"
            result["confidence"] = 0.7
        else:
            result["risk_level"] = "low"
            result["confidence"] = 0.9

        return result

    # ------------------------------------------------------------------
    # Step 1: Task Tracking
    # ------------------------------------------------------------------

    async def _step_track_tasks(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Track project tasks and compile summary statistics.

        Delegates to the TaskTrackerTool to query tasks and generate
        summary statistics by status and priority.

        Args:
            task_payload: Task payload with project ID and filters.
            context: Execution context with task records.

        Returns:
            Dict with task statistics, blocked tasks, and summary.
        """
        project_id = task_payload.get("project_id", "")
        tasks = context.get("tasks", [])
        assignee_filter = task_payload.get("assignee", "")
        status_filter = task_payload.get("status_filter", "")

        # Get task summary
        summary_result = await self._task_tracker.execute({
            "action": "summary",
            "project_id": project_id,
            "tasks": tasks,
        })

        if not summary_result.get("success"):
            return {
                "total_tasks": 0,
                "by_status": {},
                "by_priority": {},
                "blocked_tasks": [],
                "tasks": [],
                "details": f"Task tracking failed: {summary_result.get('error')}",
            }

        summary_data = summary_result["data"]

        # Get detailed task list
        list_result = await self._task_tracker.execute({
            "action": "query",
            "project_id": project_id,
            "assignee": assignee_filter,
            "status_filter": status_filter,
            "tasks": tasks,
        })

        task_list = []
        blocked_tasks = []
        if list_result.get("success"):
            task_list = list_result["data"].get("tasks", [])
            blocked_tasks = [
                t for t in task_list
                if (t.get("status") or "").lower() == "blocked"
            ]

        return {
            "total_tasks": summary_data.get("total_tasks", 0),
            "by_status": summary_data.get("by_status", {}),
            "by_priority": summary_data.get("by_priority", {}),
            "blocked_tasks": blocked_tasks,
            "blocked_count": len(blocked_tasks),
            "tasks": task_list,
            "project_id": project_id,
            "details": summary_data.get("summary", "Task tracking completed."),
        }

    # ------------------------------------------------------------------
    # Step 2: Milestone Monitoring
    # ------------------------------------------------------------------

    async def _step_monitor_milestones(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Monitor milestones against deadlines and progress targets.

        Delegates to the MilestoneMonitorTool to check milestone status
        and identify at-risk items.

        Args:
            task_payload: Task payload with project ID.
            context: Execution context with milestone records.
            policy: Resolved policy configuration.

        Returns:
            Dict with milestone statuses, at-risk items, and progress.
        """
        project_id = task_payload.get("project_id", "")
        milestones = context.get("milestones", [])
        warning_days = policy.get(
            "milestone_warnings", {}
        ).get("warning_threshold_days", 7)

        result = await self._milestone_monitor.execute({
            "project_id": project_id,
            "milestones": milestones,
            "warning_threshold_days": warning_days,
        })

        if not result.get("success"):
            return {
                "total_milestones": 0,
                "completed": 0,
                "at_risk_count": 0,
                "at_risk": [],
                "milestones": [],
                "overall_progress": 0,
                "details": f"Milestone monitoring failed: {result.get('error')}",
            }

        data = result["data"]

        # Check if critical milestones need escalation
        critical_threshold = policy.get(
            "milestone_warnings", {}
        ).get("critical_threshold_days", 3)

        critically_at_risk = [
            ms for ms in data.get("at_risk", [])
            if (ms.get("days_remaining") is not None
                and ms["days_remaining"] <= critical_threshold)
        ]

        return {
            "total_milestones": data.get("total_milestones", 0),
            "completed": data.get("completed", 0),
            "at_risk_count": data.get("at_risk_count", 0),
            "at_risk": data.get("at_risk", []),
            "critically_at_risk": critically_at_risk,
            "milestones": data.get("milestones", []),
            "overall_progress": data.get("overall_progress", 0),
            "project_id": project_id,
            "needs_escalation": len(critically_at_risk) > 0,
            "details": data.get("summary", "Milestone monitoring completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Risk Detection
    # ------------------------------------------------------------------

    async def _step_assess_risks(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        task_result: dict[str, Any],
        milestone_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess project risks using the severity matrix.

        Combines explicit risk factors with risks inferred from task
        and milestone analysis.

        Args:
            task_payload: Task payload with project ID.
            context: Execution context with risk factors.
            task_result: Result from task tracking step.
            milestone_result: Result from milestone monitoring step.
            policy: Resolved policy configuration.

        Returns:
            Dict with risk assessments, scores, and mitigations.
        """
        project_id = task_payload.get("project_id", "")
        risk_factors = context.get("risk_factors", [])
        risk_matrix = policy.get("risk_matrix", {})

        # Infer additional risks from task and milestone data
        inferred_risks = self._infer_risks(task_result, milestone_result)

        # Combine explicit and inferred risks
        all_risks = risk_factors + inferred_risks

        result = await self._project_risk.execute({
            "project_id": project_id,
            "risk_factors": all_risks,
            "risk_matrix": risk_matrix,
        })

        if not result.get("success"):
            return {
                "overall_risk_score": 0,
                "overall_severity": "unknown",
                "total_risks": 0,
                "critical_risks": 0,
                "high_risks": 0,
                "risk_assessments": [],
                "details": f"Risk assessment failed: {result.get('error')}",
            }

        data = result["data"]

        # Check if auto-escalation is needed
        auto_escalate = (
            risk_matrix.get("auto_escalate_critical", True)
            and data.get("critical_risks", 0) > 0
        )

        max_acceptable = risk_matrix.get("max_acceptable_risk_score", 0.6)
        exceeds_threshold = (
            data.get("overall_risk_score", 0) > max_acceptable
        )

        return {
            "overall_risk_score": data.get("overall_risk_score", 0),
            "overall_severity": data.get("overall_severity", "low"),
            "total_risks": data.get("total_risks", 0),
            "critical_risks": data.get("critical_risks", 0),
            "high_risks": data.get("high_risks", 0),
            "risk_assessments": data.get("risk_assessments", []),
            "auto_escalate": auto_escalate,
            "exceeds_threshold": exceeds_threshold,
            "inferred_risk_count": len(inferred_risks),
            "project_id": project_id,
            "details": data.get("summary", "Risk assessment completed."),
        }

    @staticmethod
    def _infer_risks(
        task_result: dict[str, Any],
        milestone_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Infer risks from task and milestone analysis.

        Args:
            task_result: Task tracking result.
            milestone_result: Milestone monitoring result.

        Returns:
            List of inferred risk factor dicts.
        """
        inferred: list[dict[str, Any]] = []

        # Blocked tasks risk
        blocked_count = task_result.get("blocked_count", 0)
        if blocked_count > 0:
            inferred.append({
                "id": "INFERRED-BLOCKED",
                "category": "schedule",
                "description": (
                    f"{blocked_count} task(s) are currently blocked, "
                    f"potentially impacting project timeline."
                ),
                "likelihood": min(0.3 + (blocked_count * 0.15), 0.95),
                "impact": 0.6,
            })

        # At-risk milestones
        at_risk_count = milestone_result.get("at_risk_count", 0)
        if at_risk_count > 0:
            inferred.append({
                "id": "INFERRED-MILESTONES",
                "category": "schedule",
                "description": (
                    f"{at_risk_count} milestone(s) are at risk of missing "
                    f"their deadline."
                ),
                "likelihood": min(0.4 + (at_risk_count * 0.2), 0.95),
                "impact": 0.7,
            })

        # Low overall progress
        overall_progress = milestone_result.get("overall_progress", 100)
        if overall_progress < 30:
            inferred.append({
                "id": "INFERRED-PROGRESS",
                "category": "scope",
                "description": (
                    f"Overall project progress is only {overall_progress}%, "
                    f"indicating potential scope or capacity issues."
                ),
                "likelihood": 0.5,
                "impact": 0.5,
            })

        # High ratio of high-priority tasks
        by_priority = task_result.get("by_priority", {})
        total_tasks = task_result.get("total_tasks", 0)
        critical_tasks = by_priority.get("critical", 0) + by_priority.get("high", 0)
        if total_tasks > 0 and critical_tasks / total_tasks > 0.5:
            inferred.append({
                "id": "INFERRED-PRIORITY",
                "category": "resource",
                "description": (
                    f"{critical_tasks} of {total_tasks} tasks are high/critical "
                    f"priority, suggesting resource strain."
                ),
                "likelihood": 0.6,
                "impact": 0.5,
            })

        return inferred

    # ------------------------------------------------------------------
    # Step 4: Status Reporting
    # ------------------------------------------------------------------

    async def _step_generate_report(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        task_result: dict[str, Any],
        milestone_result: dict[str, Any],
        risk_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a comprehensive project status report using the LLM.

        Combines task, milestone, and risk data into a structured status
        report with insights and recommendations.

        Args:
            task_payload: Original task payload.
            context: Execution context.
            task_result: Task tracking result.
            milestone_result: Milestone monitoring result.
            risk_result: Risk assessment result.
            policy: Resolved policy configuration.

        Returns:
            Dict with report content, tokens_used, and cost_usd.
        """
        report_context = json.dumps(
            {
                "project_id": task_payload.get("project_id", "N/A"),
                "tasks": {
                    "total": task_result.get("total_tasks", 0),
                    "by_status": task_result.get("by_status", {}),
                    "blocked": task_result.get("blocked_count", 0),
                },
                "milestones": {
                    "total": milestone_result.get("total_milestones", 0),
                    "completed": milestone_result.get("completed", 0),
                    "at_risk": milestone_result.get("at_risk_count", 0),
                    "overall_progress": milestone_result.get("overall_progress", 0),
                },
                "risks": {
                    "overall_score": risk_result.get("overall_risk_score", 0),
                    "severity": risk_result.get("overall_severity", "low"),
                    "critical_count": risk_result.get("critical_risks", 0),
                    "high_count": risk_result.get("high_risks", 0),
                },
            },
            default=str,
        )

        reporting_policy = policy.get("reporting", {})

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Project Coordinator. Generate a structured "
                    "project status report based on the analysis data below. "
                    "Follow these rules:\n"
                    "- Start with an executive summary (2-3 sentences)\n"
                    "- Include task progress section with key metrics\n"
                    "- Highlight at-risk milestones with specific concerns\n"
                    "- Summarize risk landscape and top mitigation actions\n"
                    "- End with recommendations (2-3 bullet points)\n"
                    "- Use professional project management language\n"
                    "- Be concise but thorough\n"
                    "- Never share internal system scores directly"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Project: {task_payload.get('project_id', 'N/A')}\n"
                    f"Report type: {reporting_policy.get('frequency', 'weekly')}\n\n"
                    f"Analysis data:\n{report_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("report", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        # Fallback report
        if not content or content.startswith("{"):
            content = self._generate_fallback_report(
                task_payload, task_result, milestone_result, risk_result
            )

        return {
            "report": content,
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
            "report_type": reporting_policy.get("frequency", "weekly"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _generate_fallback_report(
        task_payload: dict[str, Any],
        task_result: dict[str, Any],
        milestone_result: dict[str, Any],
        risk_result: dict[str, Any],
    ) -> str:
        """Generate a fallback status report when LLM is unavailable.

        Args:
            task_payload: Original task payload.
            task_result: Task tracking result.
            milestone_result: Milestone monitoring result.
            risk_result: Risk assessment result.

        Returns:
            Formatted report string.
        """
        project_id = task_payload.get("project_id", "N/A")
        total_tasks = task_result.get("total_tasks", 0)
        by_status = task_result.get("by_status", {})
        blocked = task_result.get("blocked_count", 0)
        total_ms = milestone_result.get("total_milestones", 0)
        completed_ms = milestone_result.get("completed", 0)
        at_risk_ms = milestone_result.get("at_risk_count", 0)
        progress = milestone_result.get("overall_progress", 0)
        risk_severity = risk_result.get("overall_severity", "low")
        critical_risks = risk_result.get("critical_risks", 0)

        report = (
            f"PROJECT STATUS REPORT -- {project_id}\n"
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"EXECUTIVE SUMMARY\n"
            f"Project {project_id} is currently at {progress}% overall progress "
            f"with {total_tasks} active tasks and {total_ms} milestones tracked. "
            f"Overall risk level: {risk_severity}.\n\n"
            f"TASK PROGRESS\n"
            f"- Total tasks: {total_tasks}\n"
        )

        for status, count in by_status.items():
            report += f"  - {status}: {count}\n"

        if blocked > 0:
            report += f"- ALERT: {blocked} task(s) are currently blocked.\n"

        report += (
            f"\nMILESTONE STATUS\n"
            f"- Total milestones: {total_ms}\n"
            f"- Completed: {completed_ms}\n"
            f"- At risk: {at_risk_ms}\n"
            f"- Overall progress: {progress}%\n"
        )

        if at_risk_ms > 0:
            report += f"- WARNING: {at_risk_ms} milestone(s) at risk of missing deadlines.\n"

        report += (
            f"\nRISK ASSESSMENT\n"
            f"- Overall severity: {risk_severity}\n"
            f"- Critical risks: {critical_risks}\n"
        )

        report += (
            f"\nRECOMMENDATIONS\n"
            f"- {'Address blocked tasks immediately.' if blocked > 0 else 'Continue current pace.'}\n"
            f"- {'Escalate at-risk milestones to stakeholders.' if at_risk_ms > 0 else 'Monitor milestone progress.'}\n"
            f"- {'Activate risk mitigation plans for critical risks.' if critical_risks > 0 else 'Maintain risk monitoring cadence.'}\n"
        )

        return report

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_update_tasks(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct task update request.

        Updates one or more tasks with new status, assignments,
        or progress data.

        Args:
            task_payload: Task update parameters.
            context: Execution context.

        Returns:
            Standardized result with update confirmation.
        """
        task_id = task_payload.get("task_id", "")
        update_data = task_payload.get("update_data", {})
        action = task_payload.get("action", "update")

        if action == "create":
            result = await self._task_tracker.execute({
                "action": "create",
                "project_id": task_payload.get("project_id", ""),
                "update_data": update_data,
            })
        elif task_id:
            result = await self._task_tracker.execute({
                "action": "update",
                "task_id": task_id,
                "update_data": update_data,
            })
        else:
            # Query mode
            result = await self._task_tracker.execute({
                "action": "query",
                "project_id": task_payload.get("project_id", ""),
                "assignee": task_payload.get("assignee", ""),
                "status_filter": task_payload.get("status_filter", ""),
                "priority_filter": task_payload.get("priority_filter", ""),
                "tasks": context.get("tasks", []),
            })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Task operation failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        return self.format_result(
            status="completed",
            output=data,
            tokens_used=0,
            cost_usd=0.0,
        )

    async def _handle_check_milestones(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct milestone check request.

        Checks milestone deadlines and progress, identifying at-risk
        milestones.

        Args:
            task_payload: Milestone check parameters.
            context: Execution context with milestone data.

        Returns:
            Standardized result with milestone assessment.
        """
        policy = self._resolve_policy(context)
        warning_days = policy.get(
            "milestone_warnings", {}
        ).get("warning_threshold_days", 7)

        result = await self._milestone_monitor.execute({
            "project_id": task_payload.get("project_id", ""),
            "milestones": context.get("milestones", []),
            "warning_threshold_days": warning_days,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Milestone monitoring failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM insight
        llm_result = await self._generate_milestone_insight(data, policy)

        return self.format_result(
            status="completed",
            output={
                **data,
                "milestone_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=(
                "stakeholder_notification"
                if data.get("at_risk_count", 0) > 0
                else None
            ),
        )

    async def _handle_assess_risks(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct risk assessment request.

        Performs a standalone risk assessment for the project.

        Args:
            task_payload: Risk assessment parameters.
            context: Execution context with risk factors.

        Returns:
            Standardized result with risk assessment.
        """
        policy = self._resolve_policy(context)

        result = await self._project_risk.execute({
            "project_id": task_payload.get("project_id", ""),
            "risk_factors": context.get("risk_factors", []),
            "risk_matrix": policy.get("risk_matrix", {}),
            "project_data": task_payload.get("project_data", {}),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Risk assessment failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM insight
        llm_result = await self._generate_risk_insight(data, policy)

        # Determine if escalation needed
        auto_escalate = (
            policy.get("risk_matrix", {}).get("auto_escalate_critical", True)
            and data.get("critical_risks", 0) > 0
        )

        return self.format_result(
            status="escalated" if auto_escalate else "completed",
            output={
                **data,
                "risk_insight": llm_result.get("content", ""),
                "auto_escalated": auto_escalate,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="human_review" if auto_escalate else None,
        )

    async def _handle_resource_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle resource utilization query.

        Analyzes team resource utilization based on task assignments
        and workload distribution.

        Args:
            task_payload: Resource query parameters.
            context: Execution context with task and team data.

        Returns:
            Standardized result with resource utilization analysis.
        """
        policy = self._resolve_policy(context)
        resource_policy = policy.get("resource_utilization", {})
        tasks = context.get("tasks", [])
        team_members = context.get("team_members", [])

        target_util = resource_policy.get("target_utilization_pct", 80)
        over_threshold = resource_policy.get("overallocation_threshold_pct", 100)
        under_threshold = resource_policy.get("underallocation_threshold_pct", 50)
        max_concurrent = resource_policy.get("max_concurrent_tasks_per_person", 5)

        # Calculate utilization per team member
        if not team_members:
            team_members = self._extract_team_from_tasks(tasks)

        utilization = []
        for member in team_members:
            member_name = member if isinstance(member, str) else member.get("name", "")
            member_tasks = [
                t for t in tasks
                if member_name.lower() in (t.get("assignee") or "").lower()
                and (t.get("status") or "").lower() not in ("completed", "closed")
            ]

            active_count = len(member_tasks)
            util_pct = min(round((active_count / max(max_concurrent, 1)) * 100), 150)

            status = "optimal"
            if util_pct > over_threshold:
                status = "overallocated"
            elif util_pct < under_threshold:
                status = "underallocated"

            utilization.append({
                "name": member_name,
                "active_tasks": active_count,
                "utilization_pct": util_pct,
                "status": status,
                "at_capacity": active_count >= max_concurrent,
            })

        over_count = sum(1 for u in utilization if u["status"] == "overallocated")
        under_count = sum(1 for u in utilization if u["status"] == "underallocated")

        # Generate LLM insight
        llm_result = await self._generate_resource_insight(
            utilization, resource_policy
        )

        return self.format_result(
            status="completed",
            output={
                "team_utilization": utilization,
                "total_members": len(utilization),
                "overallocated": over_count,
                "underallocated": under_count,
                "optimal": len(utilization) - over_count - under_count,
                "target_utilization_pct": target_util,
                "resource_insight": llm_result.get("content", ""),
                "details": (
                    f"Team resource analysis: {len(utilization)} member(s), "
                    f"{over_count} overallocated, {under_count} underallocated."
                ),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=(
                "rebalance_workload" if over_count > 0 else None
            ),
        )

    @staticmethod
    def _extract_team_from_tasks(tasks: list[dict[str, Any]]) -> list[str]:
        """Extract unique team member names from tasks.

        Args:
            tasks: List of task records.

        Returns:
            List of unique assignee names.
        """
        members = set()
        for t in tasks:
            assignee = t.get("assignee", "")
            if assignee:
                members.add(assignee)

        if not members:
            members = {"Ahmed Al-Farsi", "Sara Mohammed", "Omar Khalid"}

        return sorted(members)

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_milestone_insight(
        self,
        milestone_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate milestone insight using the LLM.

        Args:
            milestone_data: Milestone monitoring data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        ms_context = json.dumps(
            {
                "total": milestone_data.get("total_milestones", 0),
                "completed": milestone_data.get("completed", 0),
                "at_risk": milestone_data.get("at_risk_count", 0),
                "progress": milestone_data.get("overall_progress", 0),
                "at_risk_details": [
                    {
                        "name": ms.get("name"),
                        "days_remaining": ms.get("days_remaining"),
                        "progress": ms.get("progress_percent"),
                    }
                    for ms in milestone_data.get("at_risk", [])
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Project Coordinator. Provide a brief "
                    "milestone status insight (2-3 sentences). Focus on "
                    "at-risk milestones and recommend immediate actions."
                ),
            },
            {
                "role": "user",
                "content": f"Milestone data:\n{ms_context}",
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
            at_risk = milestone_data.get("at_risk_count", 0)
            progress = milestone_data.get("overall_progress", 0)
            content = (
                f"Project is at {progress}% overall progress. "
            )
            if at_risk > 0:
                content += (
                    f"{at_risk} milestone(s) are at risk of missing deadlines. "
                    f"Recommend immediate review and resource reallocation."
                )
            else:
                content += "All milestones are on track."

        llm_result["content"] = content
        return llm_result

    async def _generate_risk_insight(
        self,
        risk_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate risk assessment insight using the LLM.

        Args:
            risk_data: Risk assessment data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        risk_context = json.dumps(
            {
                "overall_score": risk_data.get("overall_risk_score", 0),
                "severity": risk_data.get("overall_severity", "low"),
                "critical": risk_data.get("critical_risks", 0),
                "high": risk_data.get("high_risks", 0),
                "top_risks": [
                    {
                        "category": r.get("category"),
                        "severity": r.get("severity"),
                        "description": r.get("description"),
                    }
                    for r in risk_data.get("risk_assessments", [])[:3]
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Project Coordinator. Summarize the risk "
                    "assessment in 2-3 sentences. Highlight critical risks "
                    "and recommend mitigation priorities."
                ),
            },
            {
                "role": "user",
                "content": f"Risk assessment data:\n{risk_context}",
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
            severity = risk_data.get("overall_severity", "low")
            critical = risk_data.get("critical_risks", 0)
            content = (
                f"Overall project risk is {severity}. "
            )
            if critical > 0:
                content += (
                    f"{critical} critical risk(s) require immediate attention "
                    f"and executive review."
                )
            else:
                content += "No critical risks identified. Continue monitoring."

        llm_result["content"] = content
        return llm_result

    async def _generate_resource_insight(
        self,
        utilization: list[dict[str, Any]],
        resource_policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate resource utilization insight using the LLM.

        Args:
            utilization: Team utilization data.
            resource_policy: Resource policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        util_context = json.dumps(
            {
                "team": [
                    {
                        "name": u.get("name"),
                        "tasks": u.get("active_tasks"),
                        "utilization": u.get("utilization_pct"),
                        "status": u.get("status"),
                    }
                    for u in utilization
                ],
                "target": resource_policy.get("target_utilization_pct", 80),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Project Coordinator. Provide a brief "
                    "resource utilization insight (2-3 sentences). Identify "
                    "overallocated and underallocated team members and "
                    "recommend workload balancing actions."
                ),
            },
            {
                "role": "user",
                "content": f"Resource data:\n{util_context}",
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
            over = sum(1 for u in utilization if u["status"] == "overallocated")
            under = sum(1 for u in utilization if u["status"] == "underallocated")
            content = (
                f"Team of {len(utilization)} member(s): "
                f"{over} overallocated, {under} underallocated. "
            )
            if over > 0 and under > 0:
                content += "Recommend redistributing tasks from overallocated to underallocated members."
            elif over > 0:
                content += "Consider adding team capacity or deferring lower-priority tasks."
            else:
                content += "Team workload is balanced."

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
    def _audit_event(event_type, tenant_id, execution_id, **extra):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-project-coordinator",
        }
        event.update(extra)
        return event
