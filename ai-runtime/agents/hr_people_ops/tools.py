"""HR Recruiter Tools -- integration tools for the AI Recruiter agent.

Provides three tools used by the Recruiter agent during application screening:
  - ResumeParserTool: Extracts structured data from resume text
  - CandidateScorerTool: Scores candidate against job definition requirements
  - DuplicateCandidateCheckerTool: Checks for duplicate candidate applications

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with ATS, document parsing,
and candidate database systems.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resume Parser Tool
# ---------------------------------------------------------------------------


class ResumeParserTool(BaseTool):
    """Extracts structured data from resume text (PDF text, plain text, etc.).

    In production this tool would integrate with OCR and LLM extraction
    pipelines. For local development it parses pre-structured input fields
    and generates confidence scores, or returns mock extraction from raw text.
    """

    @property
    def name(self) -> str:
        return "parse_resume"

    @property
    def description(self) -> str:
        return (
            "Extract candidate name, contact information, education history, "
            "work experience, skills, and certifications from a resume document "
            "(PDF text, plain text, or pre-structured data)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "raw_content": {
                    "type": "string",
                    "description": "Raw text content of the resume (from OCR or plain text).",
                },
                "resume_data": {
                    "type": "object",
                    "description": "Pre-structured resume data (if already parsed).",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["pdf", "text", "docx", "structured"],
                    "description": "Source format of the resume.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract structured candidate data from raw or pre-structured input.

        If ``resume_data`` is provided (already structured), the tool
        validates completeness and assigns confidence scores. If only
        ``raw_content`` is provided, returns a mock extraction.

        Args:
            params: Tool parameters containing raw_content or resume_data.

        Returns:
            Success result with extracted fields and confidence scores,
            or error result if input is insufficient.
        """
        resume_data = params.get("resume_data", {})
        raw_content = params.get("raw_content", "")
        source_type = params.get("source_type", "structured")

        if resume_data:
            return self._extract_from_structured(resume_data, source_type)

        if raw_content:
            return self._extract_from_raw(raw_content, source_type)

        return self.error_result(
            "No resume data or raw content provided. "
            "Supply either 'resume_data' (structured) or 'raw_content' (raw text)."
        )

    def _extract_from_structured(
        self, data: dict[str, Any], source_type: str
    ) -> dict[str, Any]:
        """Validate pre-structured resume data and assign confidence scores.

        Args:
            data: Pre-structured resume fields.
            source_type: Source format of the resume.

        Returns:
            Success result with validated fields and per-field confidence scores.
        """
        field_configs = {
            "name": {"required": True, "base_confidence": 0.97},
            "email": {"required": True, "base_confidence": 0.98},
            "phone": {"required": False, "base_confidence": 0.95},
            "location": {"required": False, "base_confidence": 0.90},
            "education": {"required": True, "base_confidence": 0.93},
            "experience": {"required": True, "base_confidence": 0.92},
            "skills": {"required": True, "base_confidence": 0.94},
            "certifications": {"required": False, "base_confidence": 0.91},
            "languages": {"required": False, "base_confidence": 0.90},
            "summary": {"required": False, "base_confidence": 0.88},
        }

        extracted: dict[str, Any] = {}
        confidence_scores: dict[str, float] = {}
        low_confidence_fields: list[str] = []
        missing_required: list[str] = []

        for field, config in field_configs.items():
            value = data.get(field)
            if value is not None and value != "" and value != []:
                extracted[field] = value
                conf = config["base_confidence"]
                if source_type in ("pdf", "docx"):
                    conf -= 0.05  # Lower confidence for OCR-derived data
                confidence_scores[field] = round(conf, 2)
                if conf < 0.90:
                    low_confidence_fields.append(field)
            elif config["required"]:
                missing_required.append(field)
                confidence_scores[field] = 0.0

        # Calculate total years of experience from experience entries
        total_years = self._calculate_total_years(extracted.get("experience", []))
        extracted["total_years_experience"] = total_years

        # Calculate overall confidence
        scores = [v for v in confidence_scores.values() if v > 0]
        overall_confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

        return self.success_result({
            "extracted": extracted,
            "confidence_scores": confidence_scores,
            "overall_confidence": overall_confidence,
            "low_confidence_fields": low_confidence_fields,
            "missing_required_fields": missing_required,
            "source_type": source_type,
            "document_type": "resume",
            "extraction_complete": len(missing_required) == 0,
        })

    def _extract_from_raw(self, raw_content: str, source_type: str) -> dict[str, Any]:
        """Generate a mock extraction from raw text content.

        In production this would use OCR + LLM extraction. For local
        development it returns representative mock data.

        Args:
            raw_content: Raw text content of the resume.
            source_type: Source format of the resume.

        Returns:
            Success result with mock extracted fields and confidence scores.
        """
        mock_extracted = {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "+1-555-0100",
            "location": "San Francisco, CA",
            "education": [
                {
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "institution": "University of California, Berkeley",
                    "graduation_year": 2018,
                }
            ],
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "TechCorp Inc.",
                    "start_date": "2020-01",
                    "end_date": "present",
                    "years": 4,
                    "description": "Led backend development team of 5 engineers.",
                },
                {
                    "title": "Software Engineer",
                    "company": "StartupXYZ",
                    "start_date": "2018-06",
                    "end_date": "2019-12",
                    "years": 1.5,
                    "description": "Developed REST APIs and microservices.",
                },
            ],
            "skills": [
                "Python", "Java", "AWS", "Docker", "Kubernetes",
                "PostgreSQL", "REST APIs", "Agile",
            ],
            "certifications": [
                {
                    "name": "AWS Solutions Architect Associate",
                    "issuer": "Amazon Web Services",
                    "year": 2021,
                }
            ],
            "languages": ["English", "Spanish"],
            "summary": "Experienced software engineer with 5+ years in backend development.",
            "total_years_experience": 5.5,
        }

        mock_confidence = {
            "name": 0.92,
            "email": 0.95,
            "phone": 0.88,
            "location": 0.85,
            "education": 0.87,
            "experience": 0.84,
            "skills": 0.90,
            "certifications": 0.86,
            "languages": 0.82,
            "summary": 0.80,
        }

        low_conf = [k for k, v in mock_confidence.items() if v < 0.90]

        return self.success_result({
            "extracted": mock_extracted,
            "confidence_scores": mock_confidence,
            "overall_confidence": 0.87,
            "low_confidence_fields": low_conf,
            "missing_required_fields": [],
            "source_type": source_type,
            "document_type": "resume",
            "extraction_complete": True,
            "note": "Mock extraction from raw content -- configure LLM keys for real extraction.",
        })

    @staticmethod
    def _calculate_total_years(experience: list[dict[str, Any]]) -> float:
        """Calculate total years of experience from experience entries.

        Args:
            experience: List of experience entry dicts.

        Returns:
            Total years of experience as a float.
        """
        if not experience:
            return 0.0

        total = 0.0
        for entry in experience:
            if isinstance(entry, dict):
                years = entry.get("years", 0)
                if years:
                    total += float(years)
        return round(total, 1)


# ---------------------------------------------------------------------------
# Candidate Scorer Tool
# ---------------------------------------------------------------------------


class CandidateScorerTool(BaseTool):
    """Scores a candidate against job definition requirements.

    Performs mandatory requirements checking (pass/fail) and weighted
    scoring across experience, skills, education, certifications, and
    cultural fit dimensions. Returns a total score out of 100.

    In production this tool would integrate with the job definition
    database. For local development it works with data provided in
    the parameters.
    """

    @property
    def name(self) -> str:
        return "score_candidate"

    @property
    def description(self) -> str:
        return (
            "Score a candidate's resume against a job definition. Checks "
            "mandatory requirements (pass/fail) and calculates a weighted "
            "score across experience, skills, education, certifications, "
            "and cultural fit. Returns a total score out of 100."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "candidate": {
                    "type": "object",
                    "description": "Extracted candidate data from resume parsing.",
                },
                "job_definition": {
                    "type": "object",
                    "description": (
                        "Job definition with required_experience_years, required_degree, "
                        "mandatory_skills, preferred_skills, required_certifications, etc."
                    ),
                },
                "weights": {
                    "type": "object",
                    "description": (
                        "Custom scoring weights. Defaults: "
                        "experience=40, skills=30, education=15, certifications=10, cultural_fit=5."
                    ),
                },
            },
            "required": ["candidate", "job_definition"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Score candidate against job definition requirements.

        Performs two phases:
          1. Mandatory requirements check (pass/fail)
          2. Weighted scoring across five dimensions

        Args:
            params: Tool parameters with candidate data, job_definition,
                    and optional custom weights.

        Returns:
            Success result with total_score, mandatory_pass, dimension_scores,
            and detailed breakdown.
        """
        candidate = params.get("candidate", {})
        job_def = params.get("job_definition", {})
        weights = params.get("weights", {
            "experience": 40,
            "skills": 30,
            "education": 15,
            "certifications": 10,
            "cultural_fit": 5,
        })

        if not candidate:
            return self.error_result("No candidate data provided.")
        if not job_def:
            return self.error_result("No job definition provided.")

        # Phase 1: Mandatory requirements check
        mandatory_result = self._check_mandatory(candidate, job_def)

        # Phase 2: Weighted scoring
        dimension_scores = self._calculate_dimension_scores(candidate, job_def, weights)

        total_score = sum(dimension_scores.values())
        total_score = round(min(total_score, 100), 1)

        return self.success_result({
            "total_score": total_score,
            "mandatory_pass": mandatory_result["pass"],
            "mandatory_checks": mandatory_result["checks"],
            "missing_mandatory": mandatory_result["missing"],
            "dimension_scores": dimension_scores,
            "weights": weights,
            "candidate_name": candidate.get("name", "Unknown"),
            "job_title": job_def.get("title", "Unknown Position"),
            "summary": (
                f"Candidate '{candidate.get('name', 'Unknown')}' scored {total_score}/100 "
                f"for '{job_def.get('title', 'Unknown Position')}'. "
                f"Mandatory requirements: {'PASS' if mandatory_result['pass'] else 'FAIL'}."
            ),
        })

    def _check_mandatory(
        self, candidate: dict[str, Any], job_def: dict[str, Any]
    ) -> dict[str, Any]:
        """Check mandatory requirements (pass/fail).

        Args:
            candidate: Extracted candidate data.
            job_def: Job definition with mandatory requirements.

        Returns:
            Dict with pass (bool), checks (list of check results),
            and missing (list of failed requirements).
        """
        checks: list[dict[str, Any]] = []
        missing: list[str] = []

        # Years of experience
        required_years = job_def.get("required_experience_years", 0)
        candidate_years = float(candidate.get("total_years_experience", 0))
        years_pass = candidate_years >= required_years
        checks.append({
            "requirement": "years_of_experience",
            "required": required_years,
            "candidate_value": candidate_years,
            "pass": years_pass,
        })
        if not years_pass and required_years > 0:
            missing.append(
                f"Required {required_years} years experience, candidate has {candidate_years}"
            )

        # Required degree
        required_degree = job_def.get("required_degree")
        if required_degree:
            candidate_education = candidate.get("education", [])
            degree_pass = self._check_degree(candidate_education, required_degree)
            checks.append({
                "requirement": "required_degree",
                "required": required_degree,
                "candidate_value": [
                    e.get("degree", "") for e in candidate_education
                ] if isinstance(candidate_education, list) else [],
                "pass": degree_pass,
            })
            if not degree_pass:
                missing.append(f"Required degree: {required_degree}")

        # Mandatory skills
        mandatory_skills = job_def.get("mandatory_skills", [])
        if mandatory_skills:
            candidate_skills = [
                s.lower() for s in candidate.get("skills", [])
            ]
            matched_mandatory = [
                s for s in mandatory_skills if s.lower() in candidate_skills
            ]
            missing_skills = [
                s for s in mandatory_skills if s.lower() not in candidate_skills
            ]
            skills_pass = len(missing_skills) == 0
            checks.append({
                "requirement": "mandatory_skills",
                "required": mandatory_skills,
                "matched": matched_mandatory,
                "missing": missing_skills,
                "pass": skills_pass,
            })
            if not skills_pass:
                missing.append(f"Missing mandatory skills: {', '.join(missing_skills)}")

        all_pass = all(c["pass"] for c in checks)

        return {
            "pass": all_pass,
            "checks": checks,
            "missing": missing,
        }

    def _calculate_dimension_scores(
        self,
        candidate: dict[str, Any],
        job_def: dict[str, Any],
        weights: dict[str, int],
    ) -> dict[str, float]:
        """Calculate weighted scores across five dimensions.

        Args:
            candidate: Extracted candidate data.
            job_def: Job definition requirements.
            weights: Scoring weights per dimension.

        Returns:
            Dict with per-dimension weighted scores.
        """
        scores: dict[str, float] = {}

        # Experience score (0-1 ratio * weight)
        required_years = max(float(job_def.get("required_experience_years", 1)), 1)
        candidate_years = float(candidate.get("total_years_experience", 0))
        exp_ratio = min(candidate_years / required_years, 1.5) / 1.5
        scores["experience"] = round(exp_ratio * weights.get("experience", 40), 1)

        # Skills score
        preferred_skills = job_def.get("preferred_skills", [])
        mandatory_skills = job_def.get("mandatory_skills", [])
        all_required_skills = list(set(mandatory_skills + preferred_skills))
        candidate_skills = [s.lower() for s in candidate.get("skills", [])]

        if all_required_skills:
            matched = sum(
                1 for s in all_required_skills if s.lower() in candidate_skills
            )
            skills_ratio = matched / len(all_required_skills)
        else:
            skills_ratio = 0.5  # No skills specified, give average score

        scores["skills"] = round(skills_ratio * weights.get("skills", 30), 1)

        # Education score
        required_degree = job_def.get("required_degree", "")
        candidate_education = candidate.get("education", [])
        edu_score = self._score_education(candidate_education, required_degree)
        scores["education"] = round(edu_score * weights.get("education", 15), 1)

        # Certifications score
        required_certs = job_def.get("required_certifications", [])
        preferred_certs = job_def.get("preferred_certifications", [])
        all_certs = list(set(required_certs + preferred_certs))
        candidate_certs = candidate.get("certifications", [])

        if all_certs and candidate_certs:
            cert_names = [
                (c.get("name", "") if isinstance(c, dict) else str(c)).lower()
                for c in candidate_certs
            ]
            matched_certs = sum(
                1 for c in all_certs if c.lower() in " ".join(cert_names)
            )
            cert_ratio = matched_certs / len(all_certs)
        elif not all_certs:
            cert_ratio = 0.5  # No certs required, give average score
        else:
            cert_ratio = 0.0

        scores["certifications"] = round(cert_ratio * weights.get("certifications", 10), 1)

        # Cultural fit (estimated from keywords -- simplified for local dev)
        cultural_keywords = job_def.get("cultural_keywords", [])
        summary = (candidate.get("summary", "") or "").lower()
        if cultural_keywords:
            cf_matched = sum(1 for kw in cultural_keywords if kw.lower() in summary)
            cf_ratio = min(cf_matched / len(cultural_keywords), 1.0)
        else:
            cf_ratio = 0.5  # Default average

        scores["cultural_fit"] = round(cf_ratio * weights.get("cultural_fit", 5), 1)

        return scores

    @staticmethod
    def _check_degree(
        education: list[dict[str, Any]], required_degree: str
    ) -> bool:
        """Check if candidate has the required degree or higher.

        Args:
            education: List of education entries.
            required_degree: Required degree string.

        Returns:
            True if candidate meets the degree requirement.
        """
        if not education or not required_degree:
            return not required_degree  # Pass if no degree required

        degree_hierarchy = {
            "high school": 1,
            "diploma": 2,
            "associate": 3,
            "bachelor": 4,
            "master": 5,
            "mba": 5,
            "phd": 6,
            "doctorate": 6,
        }

        required_level = 0
        required_lower = required_degree.lower()
        for degree_name, level in degree_hierarchy.items():
            if degree_name in required_lower:
                required_level = level
                break

        for entry in education:
            if not isinstance(entry, dict):
                continue
            degree = (entry.get("degree", "") or "").lower()
            for degree_name, level in degree_hierarchy.items():
                if degree_name in degree and level >= required_level:
                    return True

        return False

    @staticmethod
    def _score_education(
        education: list[dict[str, Any]], required_degree: str
    ) -> float:
        """Score education level as a ratio.

        Args:
            education: List of education entries.
            required_degree: Required degree string.

        Returns:
            Score ratio between 0.0 and 1.0.
        """
        if not education:
            return 0.2 if not required_degree else 0.0

        degree_hierarchy = {
            "high school": 0.3,
            "diploma": 0.4,
            "associate": 0.5,
            "bachelor": 0.7,
            "master": 0.9,
            "mba": 0.9,
            "phd": 1.0,
            "doctorate": 1.0,
        }

        max_score = 0.3  # Default if no degree matched
        for entry in education:
            if not isinstance(entry, dict):
                continue
            degree = (entry.get("degree", "") or "").lower()
            for degree_name, score in degree_hierarchy.items():
                if degree_name in degree:
                    max_score = max(max_score, score)

        return max_score


# ---------------------------------------------------------------------------
# Duplicate Candidate Checker Tool
# ---------------------------------------------------------------------------


class DuplicateCandidateCheckerTool(BaseTool):
    """Checks for duplicate candidate applications.

    Compares a candidate against a list of existing candidates to detect
    duplicates by email, name, or phone number. Identifies if the candidate
    has applied for the same or other roles previously.

    In production this tool would query the ATS/candidate database. For
    local development it works with data provided in the parameters.
    """

    @property
    def name(self) -> str:
        return "check_duplicate_candidate"

    @property
    def description(self) -> str:
        return (
            "Check if a candidate has already applied for the same or other "
            "roles by comparing email, name, and phone number against existing "
            "candidate records. Returns match details and previous applications."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "candidate": {
                    "type": "object",
                    "description": "Candidate data with name, email, phone fields.",
                },
                "existing_candidates": {
                    "type": "array",
                    "description": "List of existing candidate records to check against.",
                    "items": {"type": "object"},
                },
                "job_id": {
                    "type": "string",
                    "description": "Current job ID the candidate is applying for.",
                },
            },
            "required": ["candidate"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check for duplicate candidate applications.

        Scans the provided list of existing candidates for matches by
        email (exact), name (case-insensitive), and phone (normalized).

        Args:
            params: Tool parameters with candidate data, existing_candidates list,
                    and current job_id.

        Returns:
            Success result with is_duplicate, match_type, matched_candidates,
            and previous application details.
        """
        candidate = params.get("candidate", {})
        existing = params.get("existing_candidates", [])
        current_job_id = params.get("job_id", "")

        candidate_email = (candidate.get("email") or "").strip().lower()
        candidate_name = (candidate.get("name") or "").strip().lower()
        candidate_phone = self._normalize_phone(candidate.get("phone", ""))

        email_matches: list[dict[str, Any]] = []
        name_matches: list[dict[str, Any]] = []
        phone_matches: list[dict[str, Any]] = []

        for rec in existing:
            rec_email = (rec.get("email") or "").strip().lower()
            rec_name = (rec.get("name") or "").strip().lower()
            rec_phone = self._normalize_phone(rec.get("phone", ""))
            rec_job_id = rec.get("job_id", "")

            same_role = rec_job_id == current_job_id if current_job_id else False

            match_info = {
                "candidate_id": rec.get("id", rec.get("candidate_id", "unknown")),
                "name": rec.get("name"),
                "email": rec.get("email"),
                "job_id": rec_job_id,
                "job_title": rec.get("job_title", ""),
                "applied_date": rec.get("applied_date", ""),
                "status": rec.get("status", "unknown"),
                "same_role": same_role,
            }

            # Email match (strongest signal)
            if candidate_email and rec_email and candidate_email == rec_email:
                match_info["match_field"] = "email"
                email_matches.append(match_info)
                continue

            # Phone match
            if candidate_phone and rec_phone and candidate_phone == rec_phone:
                match_info["match_field"] = "phone"
                phone_matches.append(match_info)
                continue

            # Name match (weakest signal -- could be coincidence)
            if candidate_name and rec_name and candidate_name == rec_name:
                match_info["match_field"] = "name"
                name_matches.append(match_info)

        # Determine duplicate status
        all_matches = email_matches + phone_matches + name_matches
        is_duplicate = len(all_matches) > 0

        # Determine match type
        if email_matches:
            match_type = "exact"  # Email is definitive
        elif phone_matches:
            match_type = "strong"  # Phone is strong signal
        elif name_matches:
            match_type = "weak"  # Name alone is weak
        else:
            match_type = None

        # Check for same-role applications
        same_role_applications = [m for m in all_matches if m.get("same_role")]
        other_role_applications = [m for m in all_matches if not m.get("same_role")]

        return self.success_result({
            "is_duplicate": is_duplicate,
            "match_type": match_type,
            "email_matches": email_matches,
            "phone_matches": phone_matches,
            "name_matches": name_matches,
            "total_matches": len(all_matches),
            "same_role_applications": same_role_applications,
            "other_role_applications": other_role_applications,
            "summary": (
                f"Found {len(all_matches)} matching candidate(s): "
                f"{len(email_matches)} by email, {len(phone_matches)} by phone, "
                f"{len(name_matches)} by name. "
                f"{len(same_role_applications)} applied for the same role."
            ),
        })

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize a phone number by removing non-digit characters.

        Args:
            phone: Raw phone number string.

        Returns:
            Normalized phone number with only digits.
        """
        if not phone:
            return ""
        return "".join(c for c in str(phone) if c.isdigit())
