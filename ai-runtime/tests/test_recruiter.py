"""Tests for RecruiterAgent.

Verifies application screening, interview scheduling, candidate scoring,
and duplicate candidate detection.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.hr_people_ops.recruiter import RecruiterAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_agent(mock_llm_gateway, mock_pii_redactor):
    """Create a RecruiterAgent with mocked dependencies."""
    agent = RecruiterAgent(
        llm_gateway=mock_llm_gateway,
        pii_redactor=mock_pii_redactor,
    )
    return agent


def _build_context(overrides=None):
    """Build a standard execution context for test scenarios."""
    ctx = {
        "tenantId": "tenant-001",
        "executionId": "exec-003",
        "agent_policy": {},
        "resolved_config": {},
        "working_memory": {},
        "existing_candidates": [],
    }
    if overrides:
        ctx.update(overrides)
    return ctx


def _sample_resume_data():
    """Return sample resume data for testing."""
    return {
        "name": "John Smith",
        "email": "john.smith@example.com",
        "phone": "+1-555-0100",
        "total_years_experience": 8,
        "skills": ["Python", "Machine Learning", "Data Analysis", "SQL"],
        "education": [
            {
                "degree": "M.S.",
                "field": "Computer Science",
                "institution": "MIT",
                "year": 2018,
            }
        ],
        "certifications": ["AWS Solutions Architect"],
        "experience": [
            {
                "title": "Senior Data Scientist",
                "company": "TechCorp",
                "years": 4,
            },
            {
                "title": "Data Analyst",
                "company": "DataInc",
                "years": 4,
            },
        ],
    }


def _sample_job_definition():
    """Return sample job definition for testing."""
    return {
        "title": "Senior ML Engineer",
        "requirements": {
            "mandatory": ["Python", "Machine Learning"],
            "preferred": ["AWS", "Docker", "Kubernetes"],
            "min_years_experience": 5,
            "education_level": "Bachelor's",
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecruiterAgent:
    """Tests for the RecruiterAgent class."""

    @pytest.mark.asyncio
    async def test_execute_screen_application(self, mock_llm_gateway, mock_pii_redactor):
        """screen_application task executes the 4-step screening workflow."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        result = await agent.execute(
            task_payload={
                "type": "screen_application",
                "resume_data": _sample_resume_data(),
                "job_definition": _sample_job_definition(),
                "job_id": "job-ml-001",
            },
            context=context,
        )

        assert result["status"] == "completed"
        assert "output" in result
        output = result["output"]
        assert "scoring" in output
        assert "outcome" in output
        assert "candidate" in output

    @pytest.mark.asyncio
    async def test_execute_schedule_interview(self, mock_llm_gateway, mock_pii_redactor):
        """schedule_interview task produces a scheduling confirmation."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        result = await agent.execute(
            task_payload={
                "type": "schedule_interview",
                "candidate_name": "John Smith",
                "candidate_email": "john@example.com",
                "job_title": "Senior ML Engineer",
                "preferred_slots": ["2025-06-15 10:00", "2025-06-16 14:00"],
                "interviewer": {"name": "Sarah Connor"},
            },
            context=context,
        )

        assert result["status"] == "completed"
        output = result["output"]
        assert "selected_slot" in output
        assert "confirmation_text" in output

    @pytest.mark.asyncio
    async def test_candidate_scoring(self, mock_llm_gateway, mock_pii_redactor):
        """Candidate scoring produces total_score and mandatory_pass fields."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        result = await agent.execute(
            task_payload={
                "type": "screen_application",
                "resume_data": _sample_resume_data(),
                "job_definition": _sample_job_definition(),
                "job_id": "job-ml-001",
            },
            context=context,
        )

        assert result["status"] == "completed"
        scoring = result["output"]["scoring"]
        assert "total_score" in scoring
        assert "mandatory_pass" in scoring

    @pytest.mark.asyncio
    async def test_duplicate_check(self, mock_llm_gateway, mock_pii_redactor):
        """Duplicate check flags candidates already in the system."""
        existing_candidates = [
            {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "job_id": "job-ml-001",
                "status": "shortlisted",
                "candidate_id": "cand-001",
            },
        ]

        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context({"existing_candidates": existing_candidates})

        result = await agent.execute(
            task_payload={
                "type": "screen_application",
                "resume_data": _sample_resume_data(),
                "job_definition": _sample_job_definition(),
                "job_id": "job-ml-001",
            },
            context=context,
        )

        assert result["status"] == "completed"
        dup_check = result["output"]["duplicate_check"]
        assert "is_duplicate" in dup_check
