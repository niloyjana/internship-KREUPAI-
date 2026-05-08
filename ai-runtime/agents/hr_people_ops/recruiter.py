"""AI Recruiter -- screens job applications end-to-end.

Implements the 4-step application screening workflow:
  1. PARSE RESUME -- Extract structured candidate data from resume
  2. SCORE AGAINST JD -- Score candidate against job definition requirements
  3. DUPLICATE CHECK -- Check for duplicate candidate applications
  4. OUTCOME ROUTING -- Route to shortlist, maybe_list, or reject

Also handles interview scheduling and candidate status inquiries.

Worker ID: ai-recruiter
Department: HR & People Operations
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.hr_people_ops.tools import (
    CandidateScorerTool,
    DuplicateCandidateCheckerTool,
    ResumeParserTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "scoring": {
        "minimum_score_shortlist": 70,
        "minimum_score_review": 50,
        "shortlist_top_percent": 20,
        "weights": {
            "experience": 40,
            "skills": 30,
            "education": 15,
            "extras": 15,
        },
    },
    "screening": {
        "blind_mode": False,
        "mandatory_knockout_fields": [
            "minimum_years_experience",
            "required_certifications",
        ],
        "auto_reject_below": 30,
    },
    "communication": {
        "auto_acknowledge": True,
        "acknowledgment_within_hours": 2,
        "rejection_notification_days": 14,
        "rejection_tone": "compassionate_professional",
        "offer_requires_hr_approval": True,
    },
    "scheduling": {
        "candidate_response_window_days": 3,
        "max_reschedules": 2,
        "no_show_follow_up_hours": 1,
        "timezone_detection": True,
    },
}

# Keywords that trigger salary/compensation escalation (guardrail)
_SALARY_KEYWORDS = [
    "salary", "compensation", "pay", "wage", "bonus", "equity",
    "stock option", "benefits package", "offer amount", "pay scale",
]


class RecruiterAgent(BaseAgent):
    """AI Recruiter -- screens job applications end-to-end.

    Executes a four-step workflow for every inbound application:
      1. Parse resume and extract structured candidate data
      2. Score candidate against job definition requirements
      3. Check for duplicate applications
      4. Route outcome (shortlist, maybe_list, or reject)

    Also supports interview scheduling via the ``schedule_interview``
    task type and candidate status inquiries via ``candidate_query``.

    Attributes:
        _resume_parser: Tool for extracting structured resume data.
        _candidate_scorer: Tool for scoring candidates against job definitions.
        _duplicate_checker: Tool for detecting duplicate applications.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Recruiter agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-recruiter", llm_gateway, pii_redactor)
        self.name = "AI Recruiter"
        self._resume_parser = ResumeParserTool()
        self._candidate_scorer = CandidateScorerTool()
        self._duplicate_checker = DuplicateCandidateCheckerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "resume_parsing",
            "candidate_ranking",
            "duplicate_detection",
            "mandatory_requirement_check",
            "candidate_communication",
            "interview_scheduling",
            "rescheduling_handling",
            "ats_data_entry",
            "job_board_posting",
            "offer_letter_drafting",
            "blind_screening",
            "reference_check_initiation",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``screen_application`` (default): Full 4-step screening workflow
          - ``schedule_interview``: Schedule an interview for a candidate
          - ``candidate_query``: Respond to a candidate status inquiry

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "screen_application")

        if task_type == "screen_application":
            return await self._screen_application(task_payload, context)
        elif task_type == "schedule_interview":
            return await self._schedule_interview(task_payload, context)
        elif task_type == "candidate_query":
            return await self._handle_candidate_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Application screening workflow
    # ------------------------------------------------------------------

    async def _screen_application(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step application screening workflow.

        Steps:
          1. Parse resume and extract structured candidate data
          2. Score candidate against job definition
          3. Check for duplicate applications
          4. Route outcome based on score and checks

        Args:
            task_payload: Application data including resume and job definition.
            context: Execution context with existing_candidates, job_definition,
                     and policy overrides.

        Returns:
            Standardized result dict with detailed screening output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0
        audit_events: list[dict[str, Any]] = []

        tenant_id = context.get("tenant_id", context.get("tenantId", ""))
        execution_id = context.get(
            "execution_id", context.get("executionId", str(uuid.uuid4()))
        )

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        # Guardrail: detect salary/compensation discussion → escalate
        query_text = task_payload.get("query", task_payload.get("message", ""))
        if self._contains_salary_discussion(query_text):
            audit_events.append(self._audit_event(
                "recruiter.salary.escalated", tenant_id, execution_id,
                reason="Salary/compensation discussion detected",
            ))
            return self.format_result(
                status="escalated",
                output={
                    "reason": "Salary and compensation discussions must be handled by human HR.",
                    "escalation_type": "salary_discussion",
                    "audit_events": audit_events,
                },
                tokens_used=0, cost_usd=0.0,
                next_action="escalate_to_hr",
            )

        # Audit: application received
        audit_events.append(self._audit_event(
            "recruiter.application.received", tenant_id, execution_id,
            source=task_payload.get("source_type", "structured"),
        ))

        # Step 1: Parse Resume
        parse_result = await self._step_parse_resume(task_payload, policy)
        if not parse_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Resume parsing failed",
                    "details": parse_result.get("error"),
                    "step": "parse_resume",
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        extracted = parse_result["data"]["extracted"]
        extraction_confidence = parse_result["data"]["overall_confidence"]
        low_confidence_fields = parse_result["data"]["low_confidence_fields"]
        missing_fields = parse_result["data"]["missing_required_fields"]

        # Audit: resume parsed
        audit_events.append(self._audit_event(
            "recruiter.resume.parsed", tenant_id, execution_id,
            confidence=extraction_confidence,
            missing_fields=missing_fields,
        ))

        # Apply blind mode if configured
        scoring_candidate = extracted
        if policy["screening"].get("blind_mode", False):
            scoring_candidate = self._apply_blind_mode(extracted)

        # Step 2: Score Against JD
        job_definition = task_payload.get("job_definition") or context.get("job_definition", {})
        score_result = await self._step_score_candidate(
            scoring_candidate, job_definition, policy
        )

        # Audit: candidate scored
        audit_events.append(self._audit_event(
            "recruiter.candidate.scored", tenant_id, execution_id,
            total_score=score_result.get("total_score", 0),
            mandatory_pass=score_result.get("mandatory_pass", False),
        ))

        # Step 3: Duplicate Check
        dup_result = await self._step_duplicate_check(extracted, context, task_payload)

        # Audit: duplicate checked
        if dup_result.get("is_duplicate"):
            audit_events.append(self._audit_event(
                "recruiter.duplicate.detected", tenant_id, execution_id,
                match_type=dup_result.get("match_type"),
            ))

        # Step 4: Outcome Routing
        outcome_result = await self._step_outcome_routing(
            extracted, score_result, dup_result, policy
        )

        # Audit: outcome determined
        outcome = outcome_result.get("outcome", "unknown")
        if outcome == "shortlist":
            audit_events.append(self._audit_event(
                "recruiter.candidate.shortlisted", tenant_id, execution_id,
                total_score=score_result.get("total_score", 0),
            ))
        elif outcome == "reject":
            audit_events.append(self._audit_event(
                "recruiter.candidate.rejected", tenant_id, execution_id,
                reason=outcome_result.get("reason", ""),
            ))

        # Use LLM to generate a human-readable summary
        llm_result = await self._generate_screening_summary(
            extracted, score_result, dup_result, outcome_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "candidate": {
                "name": extracted.get("name"),
                "email": extracted.get("email"),
                "total_years_experience": extracted.get("total_years_experience"),
                "skills": extracted.get("skills", []),
            },
            "extraction": {
                "confidence": extraction_confidence,
                "low_confidence_fields": low_confidence_fields,
                "missing_fields": missing_fields,
            },
            "scoring": score_result,
            "duplicate_check": dup_result,
            "outcome": outcome_result,
            "summary": llm_result.get("content", "Application screening complete."),
            "audit_events": audit_events,
            "processing_duration_ms": duration_ms,
        }

        status = outcome_result.get("outcome", "completed")
        if status == "reject":
            result_status = "completed"
        elif status == "shortlist":
            result_status = "completed"
        elif status == "maybe_list":
            result_status = "completed"
        elif status == "duplicate_flag":
            result_status = "completed"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if status == "shortlist":
            next_action = "schedule_interview"
        elif status == "maybe_list":
            next_action = "human_review"
        elif status == "reject":
            next_action = "send_rejection"
        elif status == "duplicate_flag":
            next_action = "human_review"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "total_score": score_result.get("total_score", 0),
                "mandatory_pass": score_result.get("mandatory_pass", False),
                "confidence": extraction_confidence,
                "outcome": outcome_result.get("outcome"),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = extraction_confidence
        total_score = score_result.get("total_score", 0)
        if total_score >= 70:
            result["risk_level"] = "low"
        elif total_score >= 50:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Parse Resume
    # ------------------------------------------------------------------

    async def _step_parse_resume(
        self, task_payload: dict[str, Any], policy: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract and validate candidate data from resume.

        Uses the ResumeParserTool to parse raw or structured resume
        data. Returns extracted fields with per-field confidence scores.

        Args:
            task_payload: The incoming task payload with resume_data or raw_content.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with extracted data, confidence scores, and flags.
        """
        resume_data = task_payload.get("resume_data", {})
        raw_content = task_payload.get("raw_content", "")
        source_type = task_payload.get("source_type", "structured")

        tool_params: dict[str, Any] = {"source_type": source_type}

        if resume_data:
            tool_params["resume_data"] = resume_data
        elif raw_content:
            tool_params["raw_content"] = raw_content
        else:
            # Treat the entire payload as resume data (minus known keys)
            exclude_keys = {"type", "job_definition", "job_id"}
            fallback_data = {
                k: v for k, v in task_payload.items() if k not in exclude_keys
            }
            if fallback_data:
                tool_params["resume_data"] = fallback_data
            else:
                return {
                    "success": False,
                    "error": "No resume data or raw content in payload.",
                }

        result = await self._resume_parser.execute(tool_params)
        return result

    # ------------------------------------------------------------------
    # Step 2: Score Against JD
    # ------------------------------------------------------------------

    async def _step_score_candidate(
        self,
        candidate: dict[str, Any],
        job_definition: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Score candidate against job definition requirements.

        Delegates to the CandidateScorerTool with the candidate data
        and job definition. Uses scoring weights from the policy.

        Args:
            candidate: Extracted candidate data.
            job_definition: Job definition with requirements.
            policy: Resolved policy configuration with scoring weights.

        Returns:
            Dict with total_score, mandatory_pass, dimension_scores, and details.
        """
        scoring_policy = policy.get("scoring", {})
        weights = scoring_policy.get("weights", {
            "experience": 40,
            "skills": 30,
            "education": 15,
            "certifications": 10,
            "cultural_fit": 5,
        })

        result = await self._candidate_scorer.execute({
            "candidate": candidate,
            "job_definition": job_definition,
            "weights": weights,
        })

        if not result.get("success"):
            return {
                "total_score": 0,
                "mandatory_pass": False,
                "missing_mandatory": [],
                "dimension_scores": {},
                "details": f"Scoring failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "total_score": data.get("total_score", 0),
            "mandatory_pass": data.get("mandatory_pass", False),
            "mandatory_checks": data.get("mandatory_checks", []),
            "missing_mandatory": data.get("missing_mandatory", []),
            "dimension_scores": data.get("dimension_scores", {}),
            "details": data.get("summary", "Scoring completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Duplicate Check
    # ------------------------------------------------------------------

    async def _step_duplicate_check(
        self,
        candidate: dict[str, Any],
        context: dict[str, Any],
        task_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Check for duplicate candidate applications.

        Delegates to the DuplicateCandidateCheckerTool with existing
        candidates from the execution context.

        Args:
            candidate: Extracted candidate data.
            context: Execution context containing existing_candidates.
            task_payload: Task payload with job_id.

        Returns:
            Dict with is_duplicate, match_type, matched_candidates, and details.
        """
        existing_candidates: list[dict[str, Any]] = context.get(
            "existing_candidates", []
        )
        job_id = task_payload.get("job_id", "")

        result = await self._duplicate_checker.execute({
            "candidate": candidate,
            "existing_candidates": existing_candidates,
            "job_id": job_id,
        })

        if not result.get("success"):
            return {
                "is_duplicate": False,
                "match_type": None,
                "matched_candidates": [],
                "same_role_applications": [],
                "other_role_applications": [],
                "details": f"Duplicate check failed: {result.get('error')}",
            }

        data = result["data"]
        all_matches = (
            data.get("email_matches", [])
            + data.get("phone_matches", [])
            + data.get("name_matches", [])
        )

        return {
            "is_duplicate": data.get("is_duplicate", False),
            "match_type": data.get("match_type"),
            "matched_candidates": all_matches,
            "same_role_applications": data.get("same_role_applications", []),
            "other_role_applications": data.get("other_role_applications", []),
            "details": data.get("summary", "Duplicate check completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: Outcome Routing
    # ------------------------------------------------------------------

    async def _step_outcome_routing(
        self,
        candidate: dict[str, Any],
        score_result: dict[str, Any],
        dup_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine final outcome based on scoring and duplicate checks.

        Outcomes:
          - ``shortlist``: Score >= threshold, recommend for interview
          - ``maybe_list``: Score in review range, hold for review
          - ``reject``: Score below threshold or missing mandatory requirements
          - ``duplicate_flag``: Candidate is a duplicate, note previous application

        Args:
            candidate: Extracted candidate data.
            score_result: Result from candidate scoring step.
            dup_result: Result from duplicate check step.
            policy: Resolved policy configuration.

        Returns:
            Dict with outcome, reason, flags, and details.
        """
        scoring_policy = policy.get("scoring", {})
        screening_policy = policy.get("screening", {})
        communication_policy = policy.get("communication", {})

        shortlist_threshold = scoring_policy.get("minimum_score_shortlist", 70)
        review_threshold = scoring_policy.get("minimum_score_review", 50)
        auto_reject_below = screening_policy.get("auto_reject_below", 30)

        total_score = score_result.get("total_score", 0)
        mandatory_pass = score_result.get("mandatory_pass", False)

        flags: list[str] = []
        reasons: list[str] = []

        # --- Evaluate duplicate check ---
        if dup_result.get("is_duplicate"):
            same_role = dup_result.get("same_role_applications", [])
            other_role = dup_result.get("other_role_applications", [])

            if same_role:
                flags.append("duplicate_same_role")
                prev = same_role[0]
                reasons.append(
                    f"Candidate previously applied for the same role "
                    f"(candidate ID: {prev.get('candidate_id')}, "
                    f"status: {prev.get('status')})."
                )
            if other_role:
                flags.append("duplicate_other_role")
                prev = other_role[0]
                reasons.append(
                    f"Candidate previously applied for another role: "
                    f"'{prev.get('job_title', prev.get('job_id'))}' "
                    f"(status: {prev.get('status')})."
                )

        # --- Evaluate mandatory requirements ---
        if not mandatory_pass:
            missing = score_result.get("missing_mandatory", [])
            flags.append("mandatory_fail")
            reasons.append(
                f"Missing mandatory requirements: {'; '.join(missing)}."
                if missing
                else "Failed mandatory requirements check."
            )

        # --- Evaluate score ---
        if total_score >= shortlist_threshold:
            flags.append("high_score")
        elif total_score >= review_threshold:
            flags.append("medium_score")
        elif total_score < auto_reject_below:
            flags.append("very_low_score")
        else:
            flags.append("low_score")

        # --- Determine outcome ---
        outcome: str
        if "duplicate_same_role" in flags:
            outcome = "duplicate_flag"
            reasons.append("Flagged as duplicate application for the same role.")
        elif not mandatory_pass:
            outcome = "reject"
            reasons.append(
                "Rejected due to missing mandatory requirements."
            )
        elif total_score < auto_reject_below:
            outcome = "reject"
            reasons.append(
                f"Auto-rejected: score {total_score} is below "
                f"auto-reject threshold {auto_reject_below}."
            )
        elif total_score >= shortlist_threshold:
            outcome = "shortlist"
            reasons.append(
                f"Shortlisted: score {total_score} meets shortlist "
                f"threshold {shortlist_threshold}. Recommended for interview."
            )
        elif total_score >= review_threshold:
            outcome = "maybe_list"
            reasons.append(
                f"Added to review list: score {total_score} is between "
                f"review threshold {review_threshold} and shortlist "
                f"threshold {shortlist_threshold}."
            )
        else:
            outcome = "reject"
            reasons.append(
                f"Rejected: score {total_score} is below review "
                f"threshold {review_threshold}."
            )

        # Build communication guidance
        communication: dict[str, Any] = {}
        if outcome == "reject":
            communication = {
                "type": "rejection",
                "delay_days": communication_policy.get("rejection_notification_days", 14),
                "message": self._generate_rejection_message(
                    candidate, score_result, flags
                ),
            }
        elif outcome == "shortlist":
            communication = {
                "type": "interview_invitation",
                "message": (
                    f"Dear {candidate.get('name', 'Candidate')}, we are pleased to inform you "
                    f"that your application has been shortlisted. Our team will contact you "
                    f"shortly to schedule an interview."
                ),
            }
        elif communication_policy.get("auto_acknowledge", True):
            communication = {
                "type": "acknowledgement",
                "message": (
                    f"Dear {candidate.get('name', 'Candidate')}, thank you for your application. "
                    f"We are currently reviewing your profile and will be in touch soon."
                ),
            }

        reason_summary = " ".join(reasons) if reasons else "Screening completed."

        return {
            "outcome": outcome,
            "reason": reason_summary,
            "total_score": total_score,
            "mandatory_pass": mandatory_pass,
            "flags": flags,
            "communication": communication,
            "details": {
                "candidate_name": candidate.get("name"),
                "total_score": total_score,
                "shortlist_threshold": shortlist_threshold,
                "review_threshold": review_threshold,
                "is_duplicate": dup_result.get("is_duplicate", False),
            },
        }

    # ------------------------------------------------------------------
    # Interview Scheduling Handler
    # ------------------------------------------------------------------

    async def _schedule_interview(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Schedule an interview for a shortlisted candidate.

        Uses the LLM to generate an appropriate interview scheduling
        response based on the candidate and interviewer availability.

        Args:
            task_payload: Scheduling details including candidate info,
                          preferred_slots, and interviewer details.
            context: Execution context with calendar availability.

        Returns:
            Standardized result with scheduling details and confirmation.
        """
        candidate_name = task_payload.get("candidate_name", "")
        candidate_email = task_payload.get("candidate_email", "")
        job_title = task_payload.get("job_title", "")
        preferred_slots = task_payload.get("preferred_slots", [])
        interviewer = task_payload.get("interviewer", {})

        # Available slots from context
        available_slots = context.get("available_slots", preferred_slots)

        # Select the best slot (first available match or first available)
        selected_slot = None
        if preferred_slots and available_slots:
            for slot in preferred_slots:
                if slot in available_slots:
                    selected_slot = slot
                    break

        if not selected_slot and available_slots:
            selected_slot = available_slots[0]

        if not selected_slot:
            selected_slot = (
                datetime.now(timezone.utc) + timedelta(days=3)
            ).strftime("%Y-%m-%d 10:00")

        # Generate confirmation using LLM
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Recruiter. Generate a professional, concise "
                    "interview scheduling confirmation email for a candidate. "
                    "Include: candidate name, job title, interview date/time, "
                    "interviewer name (if available), and any preparation tips. "
                    "Be warm and professional."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Candidate: {candidate_name or 'Candidate'}\n"
                    f"Email: {candidate_email or 'Not provided'}\n"
                    f"Position: {job_title or 'Open Position'}\n"
                    f"Interview Slot: {selected_slot}\n"
                    f"Interviewer: {interviewer.get('name', 'Hiring Manager')}\n"
                    f"Interview Type: {task_payload.get('interview_type', 'Video Call')}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)

        confirmation_text = llm_result.get("content", "")

        # Handle mock JSON responses
        if confirmation_text.startswith("{"):
            try:
                parsed = json.loads(confirmation_text)
                confirmation_text = parsed.get(
                    "response", parsed.get("summary", "")
                )
            except json.JSONDecodeError:
                pass

        # Fallback if LLM response is not useful
        if not confirmation_text or confirmation_text.startswith("{"):
            confirmation_text = (
                f"Dear {candidate_name or 'Candidate'},\n\n"
                f"We are pleased to confirm your interview for the "
                f"{job_title or 'open position'} role.\n\n"
                f"Date/Time: {selected_slot}\n"
                f"Interviewer: {interviewer.get('name', 'Our Hiring Manager')}\n"
                f"Format: {task_payload.get('interview_type', 'Video Call')}\n\n"
                f"Please ensure you are available 5 minutes before the scheduled time.\n\n"
                f"Best regards,\nThe Recruitment Team"
            )

        # Audit: interview scheduled
        tenant_id = context.get("tenant_id", context.get("tenantId", ""))
        execution_id = context.get(
            "execution_id", context.get("executionId", str(uuid.uuid4()))
        )
        interview_audit = self._audit_event(
            "recruiter.interview.scheduled", tenant_id, execution_id,
            candidate_email=candidate_email,
            job_title=job_title,
            slot=selected_slot,
        )

        return self.format_result(
            status="completed",
            output={
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "job_title": job_title,
                "selected_slot": selected_slot,
                "interviewer": interviewer,
                "interview_type": task_payload.get("interview_type", "Video Call"),
                "confirmation_text": confirmation_text,
                "status": "scheduled",
                "audit_events": [interview_audit],
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="send_confirmation",
        )

    # ------------------------------------------------------------------
    # Candidate Query Handler
    # ------------------------------------------------------------------

    async def _handle_candidate_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a candidate inquiry about their application status.

        Uses the LLM to generate an appropriate response based on the
        candidate's application data in the context.

        Args:
            task_payload: Query details including candidate identifiers and query text.
            context: Execution context with candidate records.

        Returns:
            Standardized result with response text and application details.
        """
        candidate_name = task_payload.get("candidate_name", "")
        candidate_email = task_payload.get("candidate_email", "")
        query_text = task_payload.get("query", "")

        # Search for matching applications in context
        all_candidates: list[dict[str, Any]] = context.get(
            "existing_candidates", []
        )
        matched_applications: list[dict[str, Any]] = []

        for cand in all_candidates:
            cand_name = (cand.get("name") or "").strip().lower()
            cand_email = (cand.get("email") or "").strip().lower()

            name_match = (
                candidate_name
                and cand_name == candidate_name.strip().lower()
            )
            email_match = (
                candidate_email
                and cand_email == candidate_email.strip().lower()
            )

            if name_match or email_match:
                matched_applications.append(cand)

        # Generate response using LLM
        app_summary = json.dumps(
            matched_applications[:10], indent=2, default=str
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Recruiter. A candidate is inquiring about "
                    "their application status. Generate a professional, helpful "
                    "response based on the application data provided. Follow these rules:\n"
                    "- For shortlisted candidates: congratulate and mention next steps\n"
                    "- For under review: assure the candidate their application is being reviewed\n"
                    "- For rejected candidates: be empathetic, encourage future applications\n"
                    "- For not found: ask them to provide their application reference\n"
                    "- Never disclose internal scores or ranking information\n"
                    "- Be concise and professional"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Candidate: {candidate_name or candidate_email or 'Unknown'}\n"
                    f"Query: {query_text or 'What is the status of my application?'}\n\n"
                    f"Matching applications found ({len(matched_applications)}):\n"
                    f"{app_summary}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)

        response_text = llm_result.get("content", "")

        # Handle mock JSON responses
        if response_text.startswith("{"):
            try:
                parsed = json.loads(response_text)
                response_text = parsed.get(
                    "response",
                    parsed.get(
                        "summary",
                        "Thank you for your inquiry. We are reviewing your application.",
                    ),
                )
            except json.JSONDecodeError:
                pass

        # Fallback response
        if not response_text or response_text.startswith("{"):
            if matched_applications:
                app = matched_applications[0]
                status = app.get("status", "under review")
                response_text = (
                    f"Dear {candidate_name or 'Candidate'}, thank you for your inquiry. "
                    f"Your application for '{app.get('job_title', 'the position')}' "
                    f"is currently '{status}'. "
                )
                if status == "shortlisted":
                    response_text += (
                        "Congratulations! Our team will reach out to you shortly "
                        "to schedule the next steps."
                    )
                elif status in ("under_review", "under review"):
                    response_text += (
                        "Our hiring team is carefully reviewing all applications. "
                        "We appreciate your patience."
                    )
                elif status == "rejected":
                    response_text += (
                        "Unfortunately, we have decided to move forward with other "
                        "candidates at this time. We encourage you to apply for "
                        "future openings."
                    )
                else:
                    response_text += (
                        "We will update you as soon as there is progress."
                    )
            else:
                response_text = (
                    "Thank you for your inquiry. We could not locate an application "
                    "matching the details provided. Please share your application "
                    "reference number or the email you used to apply."
                )

        return self.format_result(
            status="completed",
            output={
                "response_text": response_text,
                "matched_applications": [
                    {
                        "job_title": app.get("job_title"),
                        "job_id": app.get("job_id"),
                        "status": app.get("status"),
                        "applied_date": app.get("applied_date"),
                    }
                    for app in matched_applications[:10]
                ],
                "applications_found": len(matched_applications),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_screening_summary(
        self,
        candidate: dict[str, Any],
        score_result: dict[str, Any],
        dup_result: dict[str, Any],
        outcome_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a human-readable screening summary using the LLM.

        Args:
            candidate: Extracted candidate data.
            score_result: Candidate scoring result.
            dup_result: Duplicate check result.
            outcome_result: Outcome routing result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        screening_data = json.dumps(
            {
                "candidate": {
                    "name": candidate.get("name"),
                    "total_years_experience": candidate.get("total_years_experience"),
                    "skills_count": len(candidate.get("skills", [])),
                },
                "total_score": score_result.get("total_score"),
                "mandatory_pass": score_result.get("mandatory_pass"),
                "is_duplicate": dup_result.get("is_duplicate"),
                "outcome": outcome_result.get("outcome"),
                "flags": outcome_result.get("flags", []),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Recruiter. Generate a brief, professional "
                    "summary (2-3 sentences) of the application screening result. "
                    "Include: candidate name, total score, mandatory requirements "
                    "status, and the final outcome (shortlist, maybe_list, reject, "
                    "or duplicate_flag). If there are notable flags, mention them."
                ),
            },
            {
                "role": "user",
                "content": f"Application screening results:\n{screening_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        # Fallback to a generated summary if LLM response is not useful
        if not content or content.startswith("{"):
            outcome = outcome_result.get("outcome", "unknown")
            name = candidate.get("name", "Unknown candidate")
            total_score = score_result.get("total_score", 0)
            mandatory = score_result.get("mandatory_pass", False)

            content = (
                f"Application from {name}: Score {total_score}/100, "
                f"mandatory requirements {'PASS' if mandatory else 'FAIL'}. "
                f"Outcome: {outcome}."
            )

            flags = outcome_result.get("flags", [])
            if flags:
                content += f" Flags: {', '.join(flags)}."

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
    def _apply_blind_mode(candidate: dict[str, Any]) -> dict[str, Any]:
        """Remove identifying information for blind screening.

        Strips name, email, phone, and location from candidate data
        to reduce unconscious bias in scoring.

        Args:
            candidate: Full extracted candidate data.

        Returns:
            Copy of candidate data with identifying fields removed.
        """
        blind_candidate = dict(candidate)
        for field in (
            "name", "email", "phone", "location",
            "graduation_year", "gender", "photo", "photo_url",
        ):
            blind_candidate.pop(field, None)
        return blind_candidate

    @staticmethod
    def _generate_rejection_message(
        candidate: dict[str, Any],
        score_result: dict[str, Any],
        flags: list[str],
    ) -> str:
        """Generate a professional rejection message.

        Args:
            candidate: Extracted candidate data.
            score_result: Scoring result.
            flags: Outcome flags.

        Returns:
            Rejection message string.
        """
        name = candidate.get("name", "Candidate")

        if "mandatory_fail" in flags:
            missing = score_result.get("missing_mandatory", [])
            specific_reason = (
                " Specifically, we found that some of the key requirements "
                "for this role were not met."
            )
        else:
            specific_reason = ""

        return (
            f"Dear {name},\n\n"
            f"Thank you for your interest in the position and for taking the time "
            f"to submit your application.{specific_reason}\n\n"
            f"After careful consideration, we have decided to move forward with "
            f"other candidates whose qualifications more closely align with the "
            f"current requirements for this role.\n\n"
            f"We encourage you to apply for future positions that match your "
            f"skills and experience. We wish you all the best in your career.\n\n"
            f"Best regards,\nThe Recruitment Team"
        )

    # ------------------------------------------------------------------
    # Guardrail helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _contains_salary_discussion(text: str) -> bool:
        """Detect salary/compensation discussion in candidate message.

        Guardrail: salary discussions always escalated to human HR.

        Args:
            text: Message text to check.

        Returns:
            True if salary-related keywords are detected.
        """
        if not text:
            return False
        lower = text.lower()
        return any(kw in lower for kw in _SALARY_KEYWORDS)

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict.

        Args:
            event_type: Audit event type identifier.
            tenant_id: Tenant that owns this execution.
            execution_id: Workflow execution identifier.
            **extra: Additional event-specific fields.

        Returns:
            Flat dict with all audit event fields.
        """
        return {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-recruiter",
            **extra,
        }
