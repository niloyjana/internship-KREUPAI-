"""Governance, Risk & Control Tools -- integration tools for GRC department agents.

Provides five tools used by the Governance, Risk & Control agents:
  - ComplianceCheckerTool: Checks actions against regulatory frameworks (SOC2, GDPR, HIPAA)
  - ContractAnalyzerTool: Extracts clauses, identifies risks, checks completeness
  - ThreatIntelTool: Queries threat intelligence feeds, CVSS scoring
  - RiskScorerTool: Calculates risk scores using probability x impact matrices
  - RequirementsTrackerTool: Tracks requirements traceability, coverage gaps

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with GRC platforms, threat
intelligence feeds, contract management systems, and risk registers.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ── Shared utilities ──────────────────────────────────────────────────

MAX_TEXT_INPUT_LENGTH = 50_000  # Guard against oversized inputs

SEVERITY_ORDER: dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_WEIGHTS: dict[str, float] = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    """Return keywords found in the lowercased text."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw in text_lower]


def _get_risk_level(score: float) -> str:
    """Map a 0-10 risk score to a human-readable level."""
    if score >= 8.0:
        return "Critical"
    if score >= 6.0:
        return "High"
    if score >= 4.0:
        return "Medium"
    return "Low"


def _clamp_int(value: Any, low: int, high: int, default: int) -> int:
    """Safely clamp a value to [low, high], using default if not numeric."""
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _truncate(text: str, max_len: int = MAX_TEXT_INPUT_LENGTH) -> str:
    """Truncate text to max_len characters."""
    return text[:max_len] if len(text) > max_len else text


# ---------------------------------------------------------------------------
# Compliance Checker Tool
# ---------------------------------------------------------------------------


class ComplianceCheckerTool(BaseTool):
    """Checks actions and processes against regulatory frameworks.

    Evaluates business actions, transactions, or system configurations
    against configured regulatory frameworks including SOC2, GDPR, HIPAA,
    ISO 27001, and SAMA. Identifies violations, calculates severity, and
    provides remediation guidance.

    In production this tool would integrate with a GRC platform and
    regulatory rule engine. For local development it uses keyword-based
    compliance checking against common control patterns.
    """

    @property
    def name(self) -> str:
        return "check_compliance"

    @property
    def description(self) -> str:
        return (
            "Check an action, transaction, or process against configured "
            "regulatory frameworks (SOC2, GDPR, HIPAA, ISO 27001, SAMA). "
            "Returns compliance status, violations found, severity ratings, "
            "and remediation guidance."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action_description": {
                    "type": "string",
                    "description": "Description of the action, transaction, or process to check.",
                },
                "frameworks": {
                    "type": "array",
                    "description": (
                        "List of regulatory frameworks to check against. "
                        "Supported: SOC2, GDPR, HIPAA, ISO_27001, SAMA, PDPL."
                    ),
                    "items": {"type": "string"},
                },
                "control_area": {
                    "type": "string",
                    "description": (
                        "Specific control area to check (e.g., 'access_control', "
                        "'data_protection', 'change_management', 'incident_response')."
                    ),
                },
                "entity_type": {
                    "type": "string",
                    "description": (
                        "Type of entity being checked: 'transaction', 'process', "
                        "'system', 'policy', 'employee_action'."
                    ),
                },
                "context": {
                    "type": "object",
                    "description": "Additional context such as department, data classification, region.",
                },
            },
            "required": ["action_description"],
        }

    # Framework control definitions for compliance checking
    _FRAMEWORK_CONTROLS: dict[str, dict[str, Any]] = {
        "SOC2": {
            "access_control": {
                "controls": [
                    "CC6.1 - Logical and physical access controls",
                    "CC6.2 - System credentials management",
                    "CC6.3 - Access removal on termination",
                ],
                "keywords": [
                    "access", "login", "authentication", "authorization",
                    "password", "mfa", "privilege", "admin", "root",
                ],
            },
            "change_management": {
                "controls": [
                    "CC8.1 - Change management process",
                    "CC7.1 - System monitoring",
                ],
                "keywords": [
                    "deploy", "release", "change", "update", "patch",
                    "configuration", "modify", "upgrade",
                ],
            },
            "data_protection": {
                "controls": [
                    "CC6.7 - Data transmission encryption",
                    "CC6.1 - Data access restrictions",
                ],
                "keywords": [
                    "data", "encrypt", "transfer", "storage", "backup",
                    "pii", "sensitive", "personal",
                ],
            },
            "incident_response": {
                "controls": [
                    "CC7.3 - Security incident management",
                    "CC7.4 - Incident response procedures",
                ],
                "keywords": [
                    "incident", "breach", "alert", "response", "recovery",
                    "notification", "forensic",
                ],
            },
        },
        "GDPR": {
            "data_protection": {
                "controls": [
                    "Art.5 - Data processing principles",
                    "Art.6 - Lawfulness of processing",
                    "Art.25 - Data protection by design",
                    "Art.32 - Security of processing",
                ],
                "keywords": [
                    "personal data", "consent", "data subject", "processing",
                    "controller", "processor", "transfer", "eu", "eea",
                ],
            },
            "data_subject_rights": {
                "controls": [
                    "Art.15 - Right of access",
                    "Art.17 - Right to erasure",
                    "Art.20 - Right to data portability",
                ],
                "keywords": [
                    "access request", "deletion", "erasure", "portability",
                    "rectification", "objection", "restrict",
                ],
            },
            "breach_notification": {
                "controls": [
                    "Art.33 - Notification to supervisory authority",
                    "Art.34 - Communication to data subject",
                ],
                "keywords": [
                    "breach", "notification", "72 hours", "supervisory",
                    "authority", "data loss",
                ],
            },
        },
        "HIPAA": {
            "privacy": {
                "controls": [
                    "164.502 - Uses and disclosures of PHI",
                    "164.508 - Authorization for uses and disclosures",
                    "164.514 - De-identification of PHI",
                ],
                "keywords": [
                    "phi", "health", "patient", "medical", "protected",
                    "disclosure", "authorization", "hipaa",
                ],
            },
            "security": {
                "controls": [
                    "164.312(a) - Access controls",
                    "164.312(c) - Integrity controls",
                    "164.312(e) - Transmission security",
                ],
                "keywords": [
                    "access", "encrypt", "audit", "integrity", "transmission",
                    "electronic", "safeguard",
                ],
            },
        },
        "ISO_27001": {
            "access_control": {
                "controls": [
                    "A.9.1 - Business requirements of access control",
                    "A.9.2 - User access management",
                    "A.9.4 - System and application access control",
                ],
                "keywords": [
                    "access", "user management", "privilege", "authentication",
                    "segregation", "duty",
                ],
            },
            "asset_management": {
                "controls": [
                    "A.8.1 - Responsibility for assets",
                    "A.8.2 - Information classification",
                ],
                "keywords": [
                    "asset", "classification", "inventory", "ownership",
                    "labeling", "handling",
                ],
            },
        },
        "SAMA": {
            "cybersecurity": {
                "controls": [
                    "SAMA CSF 3.3 - Cyber risk management",
                    "SAMA CSF 3.4 - Cybersecurity operations",
                ],
                "keywords": [
                    "cyber", "risk", "security operations", "monitoring",
                    "threat", "vulnerability",
                ],
            },
            "data_protection": {
                "controls": [
                    "SAMA CSF 3.5 - Third party management",
                    "SAMA CSF 3.3.7 - Data protection",
                ],
                "keywords": [
                    "data", "third party", "vendor", "outsourcing",
                    "protection", "classification",
                ],
            },
        },
    }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check an action against regulatory frameworks for compliance.

        Evaluates the action description against the control keywords and
        rules for each specified framework. Identifies potential violations
        and assigns severity ratings.

        Args:
            params: Tool parameters with action_description, frameworks,
                    control_area, entity_type, and context.

        Returns:
            Success result with compliance status, violations found,
            applicable controls, and remediation guidance.
        """
        action_description = params.get("action_description", "")
        frameworks = params.get("frameworks", ["SOC2", "GDPR"])
        control_area = params.get("control_area", "")
        entity_type = params.get("entity_type", "process")
        context = params.get("context", {})

        if not action_description:
            return self.error_result("No action description provided for compliance check.")

        try:
            action_lower = action_description.lower()
            violations: list[dict[str, Any]] = []
            applicable_controls: list[dict[str, Any]] = []
            recommendations: list[str] = []

            for framework in frameworks:
                fw_controls = self._FRAMEWORK_CONTROLS.get(framework, {})

                for area_name, area_data in fw_controls.items():
                    # If control_area specified, only check that area
                    if control_area and area_name != control_area:
                        continue

                    keywords = area_data.get("keywords", [])
                    controls = area_data.get("controls", [])
                    matched_keywords = [kw for kw in keywords if kw in action_lower]

                    if matched_keywords:
                        for ctrl in controls:
                            applicable_controls.append({
                                "framework": framework,
                                "control_area": area_name,
                                "control_id": ctrl,
                                "matched_keywords": matched_keywords,
                            })

                        # Check for potential violations based on risk indicators
                        violation = self._check_violation_indicators(
                            action_lower, framework, area_name, matched_keywords
                        )
                        if violation:
                            violations.append(violation)

            # Generate recommendations based on findings
            if violations:
                for v in violations:
                    recommendations.append(
                        f"[{v['framework']}] {v['control_area']}: {v['remediation']}"
                    )
            else:
                recommendations.append(
                    "No violations detected. Continue monitoring as part of "
                    "regular compliance program."
                )

            overall_status = "compliant"
            if any(v.get("severity") == "critical" for v in violations):
                overall_status = "non_compliant_critical"
            elif any(v.get("severity") == "high" for v in violations):
                overall_status = "non_compliant_high"
            elif violations:
                overall_status = "non_compliant_medium"

            return self.success_result({
                "compliance_status": overall_status,
                "frameworks_checked": frameworks,
                "entity_type": entity_type,
                "violations": violations,
                "violation_count": len(violations),
                "applicable_controls": applicable_controls,
                "recommendations": recommendations,
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": (
                    f"Compliance check completed across {len(frameworks)} framework(s). "
                    f"Found {len(violations)} violation(s). "
                    f"Status: {overall_status}."
                ),
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")

    @staticmethod
    def _check_violation_indicators(
        action_lower: str,
        framework: str,
        area_name: str,
        matched_keywords: list[str],
    ) -> dict[str, Any] | None:
        """Check for specific violation indicators in the action description.

        Args:
            action_lower: Lowercased action description.
            framework: Regulatory framework being checked.
            area_name: Control area being evaluated.
            matched_keywords: Keywords that matched from the control area.

        Returns:
            Violation dict if indicators found, None otherwise.
        """
        violation_indicators = {
            "without approval": ("high", "Ensure proper approval workflow is followed."),
            "no encryption": ("critical", "Implement encryption for data at rest and in transit."),
            "shared password": ("critical", "Implement individual credentials and MFA."),
            "unencrypted": ("critical", "Apply encryption standards per framework requirements."),
            "no audit": ("high", "Enable audit logging for all critical operations."),
            "bypass": ("high", "Remove bypass mechanisms and enforce control procedures."),
            "no consent": ("critical", "Obtain proper consent before data processing."),
            "unauthorized": ("critical", "Investigate and remediate unauthorized access immediately."),
            "no backup": ("high", "Implement backup procedures per data protection requirements."),
            "default password": ("critical", "Change all default credentials immediately."),
            "public access": ("high", "Restrict access to authorized personnel only."),
            "no monitoring": ("high", "Implement continuous monitoring and alerting."),
            "manual process": ("medium", "Consider automation to reduce human error risk."),
            "no documentation": ("medium", "Document all procedures and maintain version control."),
        }

        for indicator, (severity, remediation) in violation_indicators.items():
            if indicator in action_lower:
                return {
                    "violation_id": f"VIO-{uuid.uuid4().hex[:8].upper()}",
                    "framework": framework,
                    "control_area": area_name,
                    "severity": severity,
                    "indicator": indicator,
                    "matched_keywords": matched_keywords,
                    "remediation": remediation,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }

        return None


# ---------------------------------------------------------------------------
# Contract Analyzer Tool
# ---------------------------------------------------------------------------


class ContractAnalyzerTool(BaseTool):
    """Analyzes contracts to extract clauses, identify risks, and check completeness.

    Extracts key commercial and legal terms from contract text, compares
    clauses against company standards, flags high-risk provisions, and
    assesses overall contract completeness.

    In production this tool would integrate with a contract management
    system and NLP pipeline. For local development it uses keyword-based
    clause extraction and risk identification.
    """

    @property
    def name(self) -> str:
        return "analyze_contract"

    @property
    def description(self) -> str:
        return (
            "Analyze a contract document to extract clauses, identify risks, "
            "assess completeness, and compare against standard terms. "
            "Returns clause-level analysis with risk ratings."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "contract_text": {
                    "type": "string",
                    "description": "The full text of the contract to analyze.",
                },
                "contract_type": {
                    "type": "string",
                    "description": (
                        "Type of contract: 'nda', 'service_agreement', "
                        "'supply_contract', 'employment', 'lease'."
                    ),
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Governing law jurisdiction (e.g., 'Bahrain', 'UAE', 'UK').",
                },
                "standard_clauses": {
                    "type": "array",
                    "description": "List of company standard clause templates for comparison.",
                    "items": {"type": "object"},
                },
                "analysis_depth": {
                    "type": "string",
                    "description": "Depth of analysis: 'summary', 'standard', 'detailed'.",
                },
            },
            "required": ["contract_text"],
        }

    # Standard clause categories expected in most contracts
    _STANDARD_CLAUSE_CATEGORIES: list[dict[str, Any]] = [
        {
            "category": "parties",
            "keywords": ["party", "parties", "between", "hereinafter", "contractor", "client"],
            "required": True,
        },
        {
            "category": "term_and_duration",
            "keywords": ["term", "duration", "effective date", "commencement", "expiry", "renewal"],
            "required": True,
        },
        {
            "category": "payment_terms",
            "keywords": ["payment", "fee", "compensation", "invoice", "price", "cost"],
            "required": True,
        },
        {
            "category": "termination",
            "keywords": ["termination", "terminate", "cancellation", "end of agreement"],
            "required": True,
        },
        {
            "category": "liability",
            "keywords": ["liability", "liable", "limitation", "damages", "indemnify", "indemnification"],
            "required": True,
        },
        {
            "category": "confidentiality",
            "keywords": ["confidential", "non-disclosure", "proprietary", "secret", "nda"],
            "required": True,
        },
        {
            "category": "intellectual_property",
            "keywords": ["intellectual property", "ip", "patent", "copyright", "trademark", "ownership"],
            "required": False,
        },
        {
            "category": "data_protection",
            "keywords": ["data protection", "privacy", "gdpr", "pdpl", "personal data", "processing"],
            "required": False,
        },
        {
            "category": "dispute_resolution",
            "keywords": ["dispute", "arbitration", "mediation", "litigation", "court", "jurisdiction"],
            "required": True,
        },
        {
            "category": "force_majeure",
            "keywords": ["force majeure", "act of god", "unforeseeable", "beyond control"],
            "required": False,
        },
        {
            "category": "governing_law",
            "keywords": ["governing law", "applicable law", "governed by", "laws of"],
            "required": True,
        },
    ]

    # Risk indicators for contract analysis
    _RISK_INDICATORS: dict[str, dict[str, Any]] = {
        "unlimited_liability": {
            "keywords": ["unlimited liability", "no limitation on liability", "without limit"],
            "severity": "critical",
            "description": "Contract contains unlimited liability exposure.",
        },
        "auto_renewal_no_notice": {
            "keywords": ["automatically renew", "auto-renewal", "auto renewal"],
            "severity": "high",
            "description": "Auto-renewal clause detected -- verify notice period exists.",
        },
        "one_sided_indemnity": {
            "keywords": ["shall indemnify", "agrees to indemnify", "hold harmless"],
            "severity": "high",
            "description": "One-sided indemnification clause detected.",
        },
        "ip_assignment": {
            "keywords": ["assigns all", "transfer of ip", "ip assignment", "work for hire"],
            "severity": "high",
            "description": "IP assignment to counterparty detected.",
        },
        "non_compete": {
            "keywords": ["non-compete", "non compete", "restrictive covenant"],
            "severity": "medium",
            "description": "Non-compete or restrictive covenant clause detected.",
        },
        "penalty_clause": {
            "keywords": ["penalty", "liquidated damages", "penalty clause"],
            "severity": "medium",
            "description": "Penalty or liquidated damages clause detected.",
        },
    }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze a contract for clause extraction, risk identification, and completeness.

        Args:
            params: Tool parameters with contract_text, contract_type,
                    jurisdiction, standard_clauses, and analysis_depth.

        Returns:
            Success result with extracted clauses, risk findings,
            completeness assessment, and recommendations.
        """
        contract_text = params.get("contract_text", "")
        contract_type = params.get("contract_type", "service_agreement")
        jurisdiction = params.get("jurisdiction", "")
        analysis_depth = params.get("analysis_depth", "standard")

        if not contract_text:
            return self.error_result("No contract text provided for analysis.")

        try:
            text_lower = contract_text.lower()

            # Extract clauses
            extracted_clauses = self._extract_clauses(text_lower)

            # Identify risks
            risk_findings = self._identify_risks(text_lower)

            # Check completeness
            completeness = self._check_completeness(text_lower, contract_type)

            # Calculate overall risk score
            overall_risk = self._calculate_risk_score(risk_findings, completeness)

            return self.success_result({
                "contract_type": contract_type,
                "jurisdiction": jurisdiction,
                "analysis_depth": analysis_depth,
                "extracted_clauses": extracted_clauses,
                "clauses_found": len(extracted_clauses),
                "risk_findings": risk_findings,
                "risk_count": len(risk_findings),
                "completeness": completeness,
                "overall_risk_score": overall_risk,
                "overall_risk_level": (
                    "critical" if overall_risk >= 8
                    else "high" if overall_risk >= 6
                    else "medium" if overall_risk >= 4
                    else "low"
                ),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": (
                    f"Contract analysis complete. Found {len(extracted_clauses)} clause(s), "
                    f"{len(risk_findings)} risk finding(s). "
                    f"Completeness: {completeness['completeness_pct']}%. "
                    f"Overall risk score: {overall_risk}/10."
                ),
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")

    def _extract_clauses(self, text_lower: str) -> list[dict[str, Any]]:
        """Extract clause categories present in the contract text.

        Args:
            text_lower: Lowercased contract text.

        Returns:
            List of extracted clause dicts with category and matched keywords.
        """
        clauses: list[dict[str, Any]] = []
        for clause_def in self._STANDARD_CLAUSE_CATEGORIES:
            matched = [kw for kw in clause_def["keywords"] if kw in text_lower]
            if matched:
                clauses.append({
                    "category": clause_def["category"],
                    "present": True,
                    "required": clause_def["required"],
                    "matched_keywords": matched,
                    "keyword_count": len(matched),
                })
        return clauses

    def _identify_risks(self, text_lower: str) -> list[dict[str, Any]]:
        """Identify risk indicators in the contract text.

        Args:
            text_lower: Lowercased contract text.

        Returns:
            List of risk finding dicts with severity and description.
        """
        findings: list[dict[str, Any]] = []
        for risk_id, risk_def in self._RISK_INDICATORS.items():
            matched = [kw for kw in risk_def["keywords"] if kw in text_lower]
            if matched:
                findings.append({
                    "risk_id": risk_id,
                    "severity": risk_def["severity"],
                    "description": risk_def["description"],
                    "matched_keywords": matched,
                })
        return findings

    def _check_completeness(
        self, text_lower: str, contract_type: str
    ) -> dict[str, Any]:
        """Check contract completeness against expected clause categories.

        Args:
            text_lower: Lowercased contract text.
            contract_type: Type of contract being analyzed.

        Returns:
            Dict with completeness percentage, present and missing clauses.
        """
        required_categories = [
            c for c in self._STANDARD_CLAUSE_CATEGORIES if c["required"]
        ]
        present = []
        missing = []

        for clause_def in required_categories:
            matched = any(kw in text_lower for kw in clause_def["keywords"])
            if matched:
                present.append(clause_def["category"])
            else:
                missing.append(clause_def["category"])

        total = len(required_categories)
        pct = round((len(present) / total) * 100, 1) if total > 0 else 0.0

        return {
            "completeness_pct": pct,
            "required_clauses_total": total,
            "present_clauses": present,
            "missing_clauses": missing,
            "missing_count": len(missing),
        }

    @staticmethod
    def _calculate_risk_score(
        risk_findings: list[dict[str, Any]],
        completeness: dict[str, Any],
    ) -> float:
        """Calculate an overall contract risk score from 0-10.

        Args:
            risk_findings: List of identified risk findings.
            completeness: Completeness assessment dict.

        Returns:
            Risk score as a float from 0.0 to 10.0.
        """
        severity_weights = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}
        risk_score = 0.0

        for finding in risk_findings:
            risk_score += severity_weights.get(finding.get("severity", "low"), 0.5)

        # Penalize for missing required clauses
        missing_count = completeness.get("missing_count", 0)
        risk_score += missing_count * 0.5

        return min(round(risk_score, 1), 10.0)


# ---------------------------------------------------------------------------
# Threat Intelligence Tool
# ---------------------------------------------------------------------------


class ThreatIntelTool(BaseTool):
    """Queries threat intelligence feeds and provides CVSS scoring.

    Looks up indicators of compromise (IOCs) -- IP addresses, domains,
    file hashes -- against threat intelligence feeds. Provides CVSS
    scoring for vulnerabilities and enrichment data for security analysts.

    In production this tool would integrate with threat intelligence
    platforms (VirusTotal, MISP, etc.). For local development it returns
    mock threat intelligence data.
    """

    @property
    def name(self) -> str:
        return "query_threat_intel"

    @property
    def description(self) -> str:
        return (
            "Query threat intelligence feeds for IOC enrichment and CVSS "
            "scoring. Supports IP addresses, domains, file hashes, and "
            "CVE identifiers. Returns threat context, reputation scores, "
            "and recommended actions."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "indicator": {
                    "type": "string",
                    "description": (
                        "The indicator of compromise to look up: IP address, "
                        "domain, file hash (MD5/SHA1/SHA256), or CVE ID."
                    ),
                },
                "indicator_type": {
                    "type": "string",
                    "description": (
                        "Type of indicator: 'ip', 'domain', 'hash', 'cve', 'url'."
                    ),
                },
                "feeds": {
                    "type": "array",
                    "description": (
                        "Specific threat feeds to query. Default: all configured feeds."
                    ),
                    "items": {"type": "string"},
                },
                "include_cvss": {
                    "type": "boolean",
                    "description": "Include CVSS scoring for CVE indicators.",
                },
            },
            "required": ["indicator", "indicator_type"],
        }

    # Mock threat reputation database
    _THREAT_REPUTATION: dict[str, dict[str, Any]] = {
        "malicious_ip": {
            "reputation": "malicious",
            "confidence": 0.95,
            "threat_types": ["c2_server", "brute_force"],
            "first_seen": "2024-01-15T08:00:00Z",
            "last_seen": "2025-03-01T14:30:00Z",
            "geo": {"country": "RU", "city": "Moscow"},
        },
        "suspicious_domain": {
            "reputation": "suspicious",
            "confidence": 0.72,
            "threat_types": ["phishing", "domain_generation_algorithm"],
            "first_seen": "2025-02-20T12:00:00Z",
            "last_seen": "2025-03-05T09:15:00Z",
            "registrar": "unknown",
        },
        "clean": {
            "reputation": "clean",
            "confidence": 0.88,
            "threat_types": [],
            "first_seen": None,
            "last_seen": None,
        },
    }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Look up an indicator of compromise against threat intelligence feeds.

        Args:
            params: Tool parameters with indicator, indicator_type,
                    feeds, and include_cvss flag.

        Returns:
            Success result with reputation data, CVSS score (if CVE),
            threat context, and recommended actions.
        """
        indicator = params.get("indicator", "")
        indicator_type = params.get("indicator_type", "")
        feeds = params.get("feeds", ["virustotal", "misp", "internal_ioc_list"])
        include_cvss = params.get("include_cvss", True)

        if not indicator:
            return self.error_result("No indicator provided for threat intelligence lookup.")
        if not indicator_type:
            return self.error_result("Indicator type must be specified (ip, domain, hash, cve, url).")

        try:
            # CVE lookup with CVSS scoring
            if indicator_type == "cve":
                return self._lookup_cve(indicator, include_cvss)

            # IOC lookup
            return self._lookup_ioc(indicator, indicator_type, feeds)
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")

    def _lookup_ioc(
        self, indicator: str, indicator_type: str, feeds: list[str]
    ) -> dict[str, Any]:
        """Look up an IOC (IP, domain, hash, URL) against threat feeds.

        Args:
            indicator: The indicator value.
            indicator_type: Type of indicator.
            feeds: Threat feeds to query.

        Returns:
            Success result with IOC reputation and enrichment data.
        """
        # Simulate threat lookup -- in production this queries external APIs
        # Use hash of indicator to deterministically select mock result
        indicator_hash = hash(indicator) % 3
        if indicator_hash == 0:
            mock_data = dict(self._THREAT_REPUTATION["malicious_ip"])
        elif indicator_hash == 1:
            mock_data = dict(self._THREAT_REPUTATION["suspicious_domain"])
        else:
            mock_data = dict(self._THREAT_REPUTATION["clean"])

        reputation = mock_data.get("reputation", "unknown")

        # Determine recommended actions based on reputation
        if reputation == "malicious":
            recommended_actions = [
                "Block indicator at firewall/proxy immediately.",
                "Search SIEM for historical connections to this indicator.",
                "Isolate any systems that communicated with this indicator.",
                "Create incident ticket for investigation.",
            ]
            risk_level = "critical"
        elif reputation == "suspicious":
            recommended_actions = [
                "Add to watchlist for enhanced monitoring.",
                "Search SIEM for any connections to this indicator.",
                "Review associated user activity for anomalies.",
            ]
            risk_level = "high"
        else:
            recommended_actions = [
                "No action required. Indicator appears clean.",
                "Continue standard monitoring.",
            ]
            risk_level = "low"

        return self.success_result({
            "indicator": indicator,
            "indicator_type": indicator_type,
            "reputation": reputation,
            "confidence": mock_data.get("confidence", 0.5),
            "threat_types": mock_data.get("threat_types", []),
            "first_seen": mock_data.get("first_seen"),
            "last_seen": mock_data.get("last_seen"),
            "risk_level": risk_level,
            "feeds_queried": feeds,
            "feeds_with_hits": [feeds[0]] if reputation != "clean" else [],
            "enrichment": mock_data,
            "recommended_actions": recommended_actions,
            "lookup_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"IOC lookup for {indicator_type} '{indicator}': "
                f"reputation={reputation}, confidence={mock_data.get('confidence', 0.5):.2f}, "
                f"risk_level={risk_level}."
            ),
        })

    @staticmethod
    def _lookup_cve(cve_id: str, include_cvss: bool) -> dict[str, Any]:
        """Look up a CVE identifier and return CVSS scoring.

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-1234).
            include_cvss: Whether to include CVSS scoring details.

        Returns:
            Success result with CVE details and CVSS scores.
        """
        # Mock CVE data -- in production this queries NVD/MITRE
        cvss_score = 7.5 + (hash(cve_id) % 25) / 10.0  # 7.5-10.0 range for mock
        cvss_score = min(round(cvss_score, 1), 10.0)

        if cvss_score >= 9.0:
            severity = "critical"
        elif cvss_score >= 7.0:
            severity = "high"
        elif cvss_score >= 4.0:
            severity = "medium"
        else:
            severity = "low"

        result_data: dict[str, Any] = {
            "cve_id": cve_id,
            "description": f"Mock vulnerability description for {cve_id}.",
            "severity": severity,
            "published_date": "2025-01-15T00:00:00Z",
            "last_modified": "2025-02-28T00:00:00Z",
            "affected_products": [
                {"vendor": "example_vendor", "product": "example_product", "versions": "< 2.5.0"},
            ],
            "references": [
                f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={cve_id}",
            ],
            "recommended_actions": [
                "Apply vendor patch if available.",
                "Implement compensating controls if patch not available.",
                "Monitor for exploitation attempts.",
            ],
            "lookup_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if include_cvss:
            result_data["cvss"] = {
                "version": "3.1",
                "base_score": cvss_score,
                "severity": severity,
                "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                "attack_vector": "Network",
                "attack_complexity": "Low",
                "privileges_required": "None",
                "user_interaction": "None",
                "scope": "Unchanged",
                "confidentiality_impact": "High",
                "integrity_impact": "High",
                "availability_impact": "High",
            }

        result_data["summary"] = (
            f"CVE {cve_id}: severity={severity}, "
            f"CVSS={cvss_score}/10.0. "
            f"Patch recommended."
        )

        return {"success": True, "data": result_data}


# ---------------------------------------------------------------------------
# Risk Scorer Tool
# ---------------------------------------------------------------------------


class RiskScorerTool(BaseTool):
    """Calculates risk scores using probability x impact matrices.

    Implements a configurable risk scoring methodology based on
    probability (likelihood) and impact assessment across multiple
    dimensions. Supports standard 5x5 risk matrices and custom
    scoring configurations.

    In production this tool would integrate with a risk register
    and enterprise risk management system. For local development
    it provides standalone risk scoring calculations.
    """

    @property
    def name(self) -> str:
        return "score_risk"

    @property
    def description(self) -> str:
        return (
            "Calculate a risk score using probability x impact matrix. "
            "Supports multiple impact dimensions (financial, operational, "
            "reputational, compliance) and returns composite risk scores "
            "with risk level classification."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "risk_description": {
                    "type": "string",
                    "description": "Description of the risk being scored.",
                },
                "risk_category": {
                    "type": "string",
                    "description": (
                        "Risk category: 'operational', 'financial', 'compliance', "
                        "'strategic', 'reputational', 'technology', 'cyber'."
                    ),
                },
                "probability": {
                    "type": "integer",
                    "description": "Probability/likelihood score (1-5). 1=Rare, 5=Almost Certain.",
                },
                "impact_scores": {
                    "type": "object",
                    "description": (
                        "Impact scores by dimension (each 1-5). Keys: 'financial', "
                        "'operational', 'reputational', 'compliance', 'safety'."
                    ),
                },
                "existing_controls": {
                    "type": "array",
                    "description": "List of existing control descriptions that mitigate this risk.",
                    "items": {"type": "string"},
                },
                "control_effectiveness": {
                    "type": "string",
                    "description": (
                        "Effectiveness of existing controls: "
                        "'effective', 'partially_effective', 'ineffective', 'none'."
                    ),
                },
            },
            "required": ["risk_description", "probability"],
        }

    # Risk level thresholds for 5x5 matrix (score range 1-25)
    _RISK_LEVELS: dict[str, dict[str, Any]] = {
        "critical": {"min_score": 20, "color": "red", "response": "immediate_action"},
        "high": {"min_score": 12, "color": "orange", "response": "management_attention"},
        "medium": {"min_score": 6, "color": "yellow", "response": "monitor_and_plan"},
        "low": {"min_score": 1, "color": "green", "response": "accept_and_monitor"},
    }

    # Control effectiveness multipliers for residual risk
    _CONTROL_EFFECTIVENESS: dict[str, float] = {
        "effective": 0.3,           # Controls reduce risk by 70%
        "partially_effective": 0.6, # Controls reduce risk by 40%
        "ineffective": 0.9,         # Controls reduce risk by only 10%
        "none": 1.0,                # No controls -- full inherent risk
    }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate risk scores using probability x impact methodology.

        Args:
            params: Tool parameters with risk_description, risk_category,
                    probability, impact_scores, existing_controls, and
                    control_effectiveness.

        Returns:
            Success result with inherent risk score, residual risk score,
            risk levels, and mitigation recommendations.
        """
        risk_description = params.get("risk_description", "")
        risk_category = params.get("risk_category", "operational")
        probability = params.get("probability", 3)
        impact_scores = params.get("impact_scores", {})
        existing_controls = params.get("existing_controls", [])
        control_effectiveness = params.get("control_effectiveness", "none")

        if not risk_description:
            return self.error_result("No risk description provided.")

        try:
            # Validate probability
            probability = max(1, min(5, probability))

            # Calculate impact -- use maximum across dimensions or default
            if impact_scores:
                max_impact = max(
                    max(1, min(5, v)) for v in impact_scores.values()
                )
                avg_impact = round(
                    sum(max(1, min(5, v)) for v in impact_scores.values())
                    / len(impact_scores),
                    1,
                )
            else:
                max_impact = 3  # Default medium impact
                avg_impact = 3.0
                impact_scores = {
                    "financial": 3,
                    "operational": 3,
                    "reputational": 3,
                    "compliance": 3,
                }

            # Calculate inherent risk score (probability x max impact)
            inherent_score = probability * max_impact

            # Calculate residual risk score (after controls)
            effectiveness_multiplier = self._CONTROL_EFFECTIVENESS.get(
                control_effectiveness, 1.0
            )
            residual_score = round(inherent_score * effectiveness_multiplier, 1)

            # Determine risk levels
            inherent_level = self._get_risk_level(inherent_score)
            residual_level = self._get_risk_level(residual_score)

            # Generate mitigation recommendations
            recommendations = self._generate_recommendations(
                risk_category, probability, max_impact,
                control_effectiveness, inherent_level
            )

            return self.success_result({
                "risk_description": risk_description,
                "risk_category": risk_category,
                "probability": probability,
                "probability_label": self._get_probability_label(probability),
                "impact_scores": impact_scores,
                "max_impact": max_impact,
                "max_impact_label": self._get_impact_label(max_impact),
                "average_impact": avg_impact,
                "inherent_risk_score": inherent_score,
                "inherent_risk_level": inherent_level,
                "existing_controls": existing_controls,
                "control_count": len(existing_controls),
                "control_effectiveness": control_effectiveness,
                "effectiveness_multiplier": effectiveness_multiplier,
                "residual_risk_score": residual_score,
                "residual_risk_level": residual_level,
                "risk_response": self._RISK_LEVELS.get(
                    inherent_level, {}
                ).get("response", "monitor_and_plan"),
                "recommendations": recommendations,
                "scored_at": datetime.now(timezone.utc).isoformat(),
                "summary": (
                    f"Risk '{risk_description[:80]}': "
                    f"inherent={inherent_score} ({inherent_level}), "
                    f"residual={residual_score} ({residual_level}). "
                    f"Controls: {control_effectiveness}."
                ),
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")

    def _get_risk_level(self, score: float) -> str:
        """Determine risk level from a numeric score.

        Args:
            score: Risk score (1-25 scale).

        Returns:
            Risk level string: critical, high, medium, or low.
        """
        for level_name in ("critical", "high", "medium", "low"):
            level_def = self._RISK_LEVELS[level_name]
            if score >= level_def["min_score"]:
                return level_name
        return "low"

    @staticmethod
    def _get_probability_label(probability: int) -> str:
        """Get human-readable label for probability score.

        Args:
            probability: Probability score (1-5).

        Returns:
            Probability label string.
        """
        labels = {1: "Rare", 2: "Unlikely", 3: "Possible", 4: "Likely", 5: "Almost Certain"}
        return labels.get(probability, "Unknown")

    @staticmethod
    def _get_impact_label(impact: int) -> str:
        """Get human-readable label for impact score.

        Args:
            impact: Impact score (1-5).

        Returns:
            Impact label string.
        """
        labels = {1: "Negligible", 2: "Minor", 3: "Moderate", 4: "Major", 5: "Catastrophic"}
        return labels.get(impact, "Unknown")

    @staticmethod
    def _generate_recommendations(
        risk_category: str,
        probability: int,
        max_impact: int,
        control_effectiveness: str,
        inherent_level: str,
    ) -> list[str]:
        """Generate mitigation recommendations based on risk assessment.

        Args:
            risk_category: Category of the risk.
            probability: Probability score.
            max_impact: Maximum impact score.
            control_effectiveness: Current control effectiveness.
            inherent_level: Inherent risk level.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        if inherent_level in ("critical", "high"):
            recommendations.append(
                "Escalate to risk committee for immediate review and action planning."
            )

        if control_effectiveness in ("ineffective", "none"):
            recommendations.append(
                "Implement or strengthen controls to reduce risk exposure."
            )
        elif control_effectiveness == "partially_effective":
            recommendations.append(
                "Review and enhance existing controls to improve effectiveness."
            )

        if probability >= 4:
            recommendations.append(
                "High likelihood -- consider risk transfer (insurance) or avoidance strategies."
            )

        if max_impact >= 4:
            recommendations.append(
                "High impact -- ensure business continuity and disaster recovery plans are current."
            )

        category_recs = {
            "cyber": "Conduct penetration testing and vulnerability assessment.",
            "compliance": "Review regulatory requirements and update control procedures.",
            "financial": "Implement financial controls and reconciliation processes.",
            "operational": "Review operational procedures and implement process improvements.",
            "strategic": "Align risk response with strategic objectives and board risk appetite.",
            "reputational": "Prepare communications plan and stakeholder management strategy.",
            "technology": "Review technology architecture and implement redundancy measures.",
        }
        if risk_category in category_recs:
            recommendations.append(category_recs[risk_category])

        if not recommendations:
            recommendations.append(
                "Continue monitoring risk as part of regular risk management cycle."
            )

        return recommendations


# ---------------------------------------------------------------------------
# Requirements Tracker Tool
# ---------------------------------------------------------------------------


class RequirementsTrackerTool(BaseTool):
    """Tracks requirements traceability and identifies coverage gaps.

    Maintains a requirements traceability matrix, identifies missing
    coverage, tracks requirement status, and detects ambiguous or
    conflicting requirements.

    In production this tool would integrate with requirements management
    platforms (Jira, Azure DevOps, etc.). For local development it
    works with requirements data provided in parameters.
    """

    @property
    def name(self) -> str:
        return "track_requirements"

    @property
    def description(self) -> str:
        return (
            "Track requirements traceability, identify coverage gaps, "
            "detect ambiguities, and assess requirements completeness. "
            "Supports functional, non-functional, and compliance requirements."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array",
                    "description": (
                        "List of requirement objects with id, description, type, "
                        "status, source, and linked_items."
                    ),
                    "items": {"type": "object"},
                },
                "analysis_type": {
                    "type": "string",
                    "description": (
                        "Type of analysis: 'traceability', 'coverage', "
                        "'ambiguity', 'completeness', 'all'."
                    ),
                },
                "source_document": {
                    "type": "string",
                    "description": "Reference to source document for traceability.",
                },
                "project_id": {
                    "type": "string",
                    "description": "Project identifier for filtering requirements.",
                },
            },
            "required": ["requirements"],
        }

    # Ambiguity indicator words
    _AMBIGUITY_INDICATORS: list[str] = [
        "appropriate", "adequate", "sufficient", "reasonable",
        "as needed", "if possible", "etc", "and/or", "may",
        "should", "could", "might", "some", "several", "few",
        "many", "various", "flexible", "user-friendly", "intuitive",
        "fast", "efficient", "robust", "scalable", "seamless",
    ]

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze requirements for traceability, coverage, and quality.

        Args:
            params: Tool parameters with requirements list, analysis_type,
                    source_document, and project_id.

        Returns:
            Success result with traceability matrix, coverage assessment,
            ambiguity findings, and completeness metrics.
        """
        requirements = params.get("requirements", [])
        analysis_type = params.get("analysis_type", "all")
        source_document = params.get("source_document", "")
        project_id = params.get("project_id", "")

        if not requirements:
            return self.error_result("No requirements provided for tracking.")

        results: dict[str, Any] = {
            "project_id": project_id,
            "source_document": source_document,
            "total_requirements": len(requirements),
            "analysis_type": analysis_type,
        }

        if analysis_type in ("traceability", "all"):
            results["traceability"] = self._analyze_traceability(requirements)

        if analysis_type in ("coverage", "all"):
            results["coverage"] = self._analyze_coverage(requirements)

        if analysis_type in ("ambiguity", "all"):
            results["ambiguity"] = self._analyze_ambiguity(requirements)

        if analysis_type in ("completeness", "all"):
            results["completeness"] = self._analyze_completeness(requirements)

        # Calculate overall health score
        results["health_score"] = self._calculate_health_score(results)
        results["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()
        results["summary"] = (
            f"Requirements analysis complete for {len(requirements)} requirement(s). "
            f"Health score: {results['health_score']}/100."
        )

        return self.success_result(results)

    def _analyze_traceability(
        self, requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze requirements traceability -- which requirements link back to sources.

        Args:
            requirements: List of requirement dicts.

        Returns:
            Traceability analysis results.
        """
        traced = 0
        untraced: list[str] = []

        for req in requirements:
            req_id = req.get("id", "unknown")
            source = req.get("source", "")
            linked_items = req.get("linked_items", [])

            if source or linked_items:
                traced += 1
            else:
                untraced.append(req_id)

        total = len(requirements)
        trace_pct = round((traced / total) * 100, 1) if total > 0 else 0.0

        return {
            "traced_count": traced,
            "untraced_count": len(untraced),
            "traceability_pct": trace_pct,
            "untraced_requirements": untraced,
        }

    @staticmethod
    def _analyze_coverage(
        requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze requirements coverage by type and status.

        Args:
            requirements: List of requirement dicts.

        Returns:
            Coverage analysis results with breakdowns by type and status.
        """
        type_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        uncovered: list[str] = []

        for req in requirements:
            req_type = req.get("type", "unclassified")
            req_status = req.get("status", "draft")
            req_id = req.get("id", "unknown")

            type_counts[req_type] = type_counts.get(req_type, 0) + 1
            status_counts[req_status] = status_counts.get(req_status, 0) + 1

            # A requirement is "uncovered" if it has no test cases or acceptance criteria
            if not req.get("test_cases") and not req.get("acceptance_criteria"):
                uncovered.append(req_id)

        total = len(requirements)
        covered = total - len(uncovered)
        coverage_pct = round((covered / total) * 100, 1) if total > 0 else 0.0

        return {
            "coverage_pct": coverage_pct,
            "covered_count": covered,
            "uncovered_count": len(uncovered),
            "uncovered_requirements": uncovered,
            "by_type": type_counts,
            "by_status": status_counts,
        }

    def _analyze_ambiguity(
        self, requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Detect ambiguous language in requirements.

        Args:
            requirements: List of requirement dicts.

        Returns:
            Ambiguity analysis results with flagged requirements.
        """
        flagged: list[dict[str, Any]] = []

        for req in requirements:
            req_id = req.get("id", "unknown")
            description = (req.get("description", "") or "").lower()

            found_indicators: list[str] = [
                ind for ind in self._AMBIGUITY_INDICATORS
                if ind in description
            ]

            if found_indicators:
                flagged.append({
                    "requirement_id": req_id,
                    "ambiguous_terms": found_indicators,
                    "term_count": len(found_indicators),
                    "recommendation": (
                        "Replace ambiguous terms with specific, measurable criteria."
                    ),
                })

        total = len(requirements)
        clean_count = total - len(flagged)
        clarity_pct = round((clean_count / total) * 100, 1) if total > 0 else 0.0

        return {
            "clarity_pct": clarity_pct,
            "ambiguous_count": len(flagged),
            "clean_count": clean_count,
            "flagged_requirements": flagged,
        }

    @staticmethod
    def _analyze_completeness(
        requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Assess requirement completeness based on required fields.

        Args:
            requirements: List of requirement dicts.

        Returns:
            Completeness analysis results.
        """
        required_fields = ["id", "description", "type", "priority", "source"]
        incomplete: list[dict[str, Any]] = []

        for req in requirements:
            req_id = req.get("id", "unknown")
            missing_fields = [
                f for f in required_fields
                if not req.get(f)
            ]
            if missing_fields:
                incomplete.append({
                    "requirement_id": req_id,
                    "missing_fields": missing_fields,
                    "fields_present": len(required_fields) - len(missing_fields),
                    "fields_required": len(required_fields),
                })

        total = len(requirements)
        complete_count = total - len(incomplete)
        completeness_pct = round((complete_count / total) * 100, 1) if total > 0 else 0.0

        return {
            "completeness_pct": completeness_pct,
            "complete_count": complete_count,
            "incomplete_count": len(incomplete),
            "incomplete_requirements": incomplete,
            "required_fields": required_fields,
        }

    @staticmethod
    def _calculate_health_score(results: dict[str, Any]) -> int:
        """Calculate an overall requirements health score from 0-100.

        Args:
            results: Combined analysis results dict.

        Returns:
            Health score as an integer from 0 to 100.
        """
        scores: list[float] = []

        if "traceability" in results:
            scores.append(results["traceability"].get("traceability_pct", 0))
        if "coverage" in results:
            scores.append(results["coverage"].get("coverage_pct", 0))
        if "ambiguity" in results:
            scores.append(results["ambiguity"].get("clarity_pct", 0))
        if "completeness" in results:
            scores.append(results["completeness"].get("completeness_pct", 0))

        if not scores:
            return 0

        return round(sum(scores) / len(scores))


# ---------------------------------------------------------------------------
# Compliance Officer Tools
# ---------------------------------------------------------------------------


class ControlMonitorTool(BaseTool):
    """Monitors control effectiveness across compliance frameworks.

    Evaluates whether internal controls are operating effectively,
    identifies control gaps, and tracks control testing results.
    Generates per-control test outcomes, calculates effectiveness
    percentages, and flags deficiencies with remediation guidance.

    In production this tool would integrate with a GRC platform and
    automated control-testing pipelines. For local development it
    generates realistic mock control inventories and test results
    based on the requested framework and control area.
    """

    @property
    def name(self) -> str:
        return "monitor_controls"

    @property
    def description(self) -> str:
        return (
            "Monitor and evaluate control effectiveness across compliance "
            "frameworks. Returns control status, test results, and gap analysis."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "framework": {
                    "type": "string",
                    "description": "Compliance framework to monitor (e.g., SOC2, GDPR, HIPAA).",
                },
                "control_area": {
                    "type": "string",
                    "description": "Specific control area to evaluate.",
                },
                "scope": {
                    "type": "string",
                    "description": "Scope of monitoring: 'full', 'targeted', or 'continuous'.",
                },
            },
            "required": ["framework"],
        }

    # Control inventories by framework and area
    _CONTROL_INVENTORY: dict[str, dict[str, list[dict[str, Any]]]] = {
        "SOC2": {
            "access_control": [
                {"id": "SOC2-AC-001", "title": "User provisioning and de-provisioning", "weight": 3},
                {"id": "SOC2-AC-002", "title": "Multi-factor authentication enforcement", "weight": 3},
                {"id": "SOC2-AC-003", "title": "Quarterly access reviews", "weight": 2},
                {"id": "SOC2-AC-004", "title": "Privileged access management", "weight": 3},
                {"id": "SOC2-AC-005", "title": "Session timeout and lockout policies", "weight": 1},
            ],
            "change_management": [
                {"id": "SOC2-CM-001", "title": "Change approval workflow", "weight": 3},
                {"id": "SOC2-CM-002", "title": "Pre-deployment testing requirements", "weight": 2},
                {"id": "SOC2-CM-003", "title": "Rollback procedures documented", "weight": 2},
                {"id": "SOC2-CM-004", "title": "Segregation of duties in deployments", "weight": 3},
            ],
            "data_protection": [
                {"id": "SOC2-DP-001", "title": "Encryption at rest (AES-256)", "weight": 3},
                {"id": "SOC2-DP-002", "title": "Encryption in transit (TLS 1.2+)", "weight": 3},
                {"id": "SOC2-DP-003", "title": "Data classification and labeling", "weight": 2},
                {"id": "SOC2-DP-004", "title": "Backup and recovery testing", "weight": 2},
                {"id": "SOC2-DP-005", "title": "Data loss prevention controls", "weight": 2},
            ],
            "incident_response": [
                {"id": "SOC2-IR-001", "title": "Incident response plan documented", "weight": 3},
                {"id": "SOC2-IR-002", "title": "Incident detection and alerting", "weight": 3},
                {"id": "SOC2-IR-003", "title": "Post-incident review process", "weight": 2},
                {"id": "SOC2-IR-004", "title": "Communication and escalation procedures", "weight": 2},
            ],
        },
        "GDPR": {
            "data_protection": [
                {"id": "GDPR-DP-001", "title": "Lawful basis for processing documented", "weight": 3},
                {"id": "GDPR-DP-002", "title": "Privacy impact assessments conducted", "weight": 3},
                {"id": "GDPR-DP-003", "title": "Data processing register maintained", "weight": 2},
                {"id": "GDPR-DP-004", "title": "Data minimization enforcement", "weight": 2},
                {"id": "GDPR-DP-005", "title": "Cross-border transfer safeguards", "weight": 3},
            ],
            "data_subject_rights": [
                {"id": "GDPR-DSR-001", "title": "Subject access request process", "weight": 3},
                {"id": "GDPR-DSR-002", "title": "Right to erasure procedures", "weight": 3},
                {"id": "GDPR-DSR-003", "title": "Data portability capability", "weight": 2},
                {"id": "GDPR-DSR-004", "title": "Consent management and withdrawal", "weight": 3},
            ],
            "breach_notification": [
                {"id": "GDPR-BN-001", "title": "72-hour breach notification process", "weight": 3},
                {"id": "GDPR-BN-002", "title": "Breach severity assessment criteria", "weight": 2},
                {"id": "GDPR-BN-003", "title": "Data subject notification procedures", "weight": 2},
            ],
        },
        "HIPAA": {
            "privacy": [
                {"id": "HIPAA-PR-001", "title": "PHI access controls and audit trails", "weight": 3},
                {"id": "HIPAA-PR-002", "title": "Minimum necessary standard enforcement", "weight": 2},
                {"id": "HIPAA-PR-003", "title": "Business associate agreement management", "weight": 3},
                {"id": "HIPAA-PR-004", "title": "Patient authorization workflows", "weight": 2},
            ],
            "security": [
                {"id": "HIPAA-SC-001", "title": "ePHI encryption at rest and in transit", "weight": 3},
                {"id": "HIPAA-SC-002", "title": "Workstation and device security", "weight": 2},
                {"id": "HIPAA-SC-003", "title": "Audit logging and monitoring", "weight": 3},
                {"id": "HIPAA-SC-004", "title": "Contingency plan and disaster recovery", "weight": 3},
            ],
        },
    }

    # Known deficiency patterns for mock testing results
    _DEFICIENCY_PATTERNS: list[dict[str, Any]] = [
        {
            "trigger_keywords": ["access review", "quarterly"],
            "finding": "Access review process not executed within the required quarterly cadence",
            "severity": "medium",
            "remediation": "Implement automated quarterly access review with calendar-based triggers",
        },
        {
            "trigger_keywords": ["encryption", "rest"],
            "finding": "Encryption at rest not enabled on secondary or archive storage tiers",
            "severity": "high",
            "remediation": "Enable AES-256 encryption on all storage tiers including archive buckets",
        },
        {
            "trigger_keywords": ["segregation", "duties"],
            "finding": "Same engineer approving and deploying changes in 12% of cases",
            "severity": "high",
            "remediation": "Enforce mandatory dual-approval in CI/CD pipeline configuration",
        },
        {
            "trigger_keywords": ["backup", "recovery"],
            "finding": "Last disaster recovery test was 14 months ago (policy requires annual)",
            "severity": "medium",
            "remediation": "Schedule and execute DR test within 30 days; update test calendar",
        },
        {
            "trigger_keywords": ["breach", "notification"],
            "finding": "Breach notification runbook lacks clear authority-contact phone numbers",
            "severity": "medium",
            "remediation": "Update runbook with 24/7 contact details for DPA and legal counsel",
        },
        {
            "trigger_keywords": ["consent", "management"],
            "finding": "Consent withdrawal requests not reflected in downstream systems within 48 hours",
            "severity": "high",
            "remediation": "Implement event-driven consent propagation across all data processors",
        },
        {
            "trigger_keywords": ["audit", "logging"],
            "finding": "Audit log retention set to 60 days instead of required 365 days",
            "severity": "high",
            "remediation": "Increase log retention to 365 days and archive to immutable storage",
        },
    ]

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Monitor control effectiveness across a compliance framework.

        Evaluates each control in the requested framework/area, simulates
        test outcomes, identifies deficiencies, and computes an overall
        effectiveness percentage.

        Args:
            params: Tool parameters with framework, control_area, and scope.

        Returns:
            Success result with per-control test results, effectiveness
            metrics, deficiency details, and remediation guidance.
        """
        framework = params.get("framework", "SOC2")
        control_area = params.get("control_area", "")
        scope = params.get("scope", "full")

        if not framework:
            return self.error_result("No compliance framework specified for monitoring.")

        try:
            now = datetime.now(timezone.utc)

            # Gather controls to evaluate
            fw_controls = self._CONTROL_INVENTORY.get(framework, {})
            if not fw_controls:
                # Generate generic controls for unknown frameworks
                fw_controls = self._generate_generic_controls(framework)

            controls_to_test: list[dict[str, Any]] = []
            areas_evaluated: list[str] = []

            for area_name, area_controls in fw_controls.items():
                if control_area and area_name != control_area:
                    continue
                areas_evaluated.append(area_name)
                controls_to_test.extend(area_controls)

            if not controls_to_test:
                # Fall back: if control_area didn't match, test all
                for area_name, area_controls in fw_controls.items():
                    areas_evaluated.append(area_name)
                    controls_to_test.extend(area_controls)

            # Simulate control testing
            test_results: list[dict[str, Any]] = []
            effective_count = 0
            deficient_count = 0
            gaps: list[dict[str, Any]] = []

            for ctrl in controls_to_test:
                ctrl_id = ctrl["id"]
                ctrl_title = ctrl["title"]
                ctrl_title_lower = ctrl_title.lower()

                # Determine if this control has a deficiency
                deficiency = None
                for pattern in self._DEFICIENCY_PATTERNS:
                    if any(kw in ctrl_title_lower for kw in pattern["trigger_keywords"]):
                        # Use deterministic selection based on control ID
                        if hash(ctrl_id) % 3 == 0:
                            deficiency = pattern
                            break

                if deficiency:
                    deficient_count += 1
                    status = "deficient"
                    test_outcome = "fail"
                    gaps.append({
                        "control_id": ctrl_id,
                        "control_title": ctrl_title,
                        "finding": deficiency["finding"],
                        "severity": deficiency["severity"],
                        "remediation": deficiency["remediation"],
                        "gap_id": f"GAP-{uuid.uuid4().hex[:8].upper()}",
                        "identified_date": now.isoformat(),
                    })
                else:
                    effective_count += 1
                    status = "effective"
                    test_outcome = "pass"

                # Determine last tested date (mock: stagger across recent weeks)
                days_ago = hash(ctrl_id) % 45 + 1
                last_tested = (now - timedelta(days=days_ago)).isoformat()

                test_results.append({
                    "control_id": ctrl_id,
                    "control_title": ctrl_title,
                    "status": status,
                    "test_outcome": test_outcome,
                    "last_tested": last_tested,
                    "next_test_due": (now + timedelta(days=90 - days_ago)).isoformat(),
                    "evidence_count": max(1, hash(ctrl_id) % 5),
                })

            total = len(controls_to_test)
            effectiveness_pct = round((effective_count / total) * 100, 1) if total > 0 else 0.0

            # Classify overall health
            if effectiveness_pct >= 95:
                overall_health = "excellent"
            elif effectiveness_pct >= 80:
                overall_health = "good"
            elif effectiveness_pct >= 60:
                overall_health = "needs_improvement"
            else:
                overall_health = "critical_attention"

            return self.success_result({
                "framework": framework,
                "control_areas_evaluated": areas_evaluated,
                "scope": scope,
                "controls_evaluated": total,
                "controls_effective": effective_count,
                "controls_deficient": deficient_count,
                "effectiveness_pct": effectiveness_pct,
                "overall_health": overall_health,
                "test_results": test_results,
                "gaps": gaps,
                "gap_count": len(gaps),
                "high_severity_gaps": sum(1 for g in gaps if g["severity"] in ("high", "critical")),
                "monitoring_timestamp": now.isoformat(),
                "next_full_assessment_due": (now + timedelta(days=90)).isoformat(),
                "summary": (
                    f"Control monitoring for {framework} complete. "
                    f"Evaluated {total} controls across {len(areas_evaluated)} area(s). "
                    f"Effectiveness: {effectiveness_pct}% ({overall_health}). "
                    f"Found {len(gaps)} gap(s), "
                    f"{sum(1 for g in gaps if g['severity'] in ('high', 'critical'))} high/critical."
                ),
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")

    @staticmethod
    def _generate_generic_controls(framework: str) -> dict[str, list[dict[str, Any]]]:
        """Generate generic controls for frameworks not in the inventory.

        Args:
            framework: Framework identifier.

        Returns:
            Dict mapping 'general' to a list of generic control dicts.
        """
        return {
            "general": [
                {"id": f"{framework}-GEN-{i:03d}", "title": title, "weight": 2}
                for i, title in enumerate([
                    "Access control policy enforcement",
                    "Security awareness training completion",
                    "Vulnerability scanning schedule adherence",
                    "Incident response plan currency",
                    "Data classification and handling",
                    "Third-party risk assessment",
                    "Change management procedures",
                    "Audit logging and monitoring",
                ], start=1)
            ],
        }


class ViolationDetectorTool(BaseTool):
    """Scans for policy and regulatory violations.

    Detects violations of internal policies, regulatory requirements,
    and contractual obligations across systems and processes. Uses
    keyword-based pattern matching against a violation rule library
    to identify issues and assign severity ratings.

    In production this tool would integrate with policy engines,
    DLP systems, and audit log analytics. For local development it
    uses keyword matching against configurable violation rules to
    generate realistic detection results.
    """

    @property
    def name(self) -> str:
        return "detect_violations"

    @property
    def description(self) -> str:
        return (
            "Scan systems, processes, and actions for policy and regulatory "
            "violations. Returns detected violations with severity and context."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scan_target": {
                    "type": "string",
                    "description": "Target to scan for violations (system, process, or action description).",
                },
                "policy_domains": {
                    "type": "array",
                    "description": "Policy domains to check against.",
                    "items": {"type": "string"},
                },
                "time_range_hours": {
                    "type": "integer",
                    "description": "How far back to scan in hours.",
                },
            },
            "required": ["scan_target"],
        }

    # Violation rule library organized by policy domain
    _VIOLATION_RULES: dict[str, list[dict[str, Any]]] = {
        "data_retention": [
            {
                "rule_id": "DR-001",
                "policy": "Data Retention Policy v2.1",
                "keywords": ["retention", "retained", "old data", "archive", "expired", "storage"],
                "violation_template": "Data retained beyond maximum retention period of {period}",
                "severity": "medium",
                "regulation": "GDPR Art.5(1)(e)",
            },
            {
                "rule_id": "DR-002",
                "policy": "Data Retention Policy v2.1",
                "keywords": ["delete", "purge", "removal", "dispose"],
                "violation_template": "Deletion process not executed per scheduled purge cycle",
                "severity": "medium",
                "regulation": "SOC2 CC6.5",
            },
        ],
        "access_control": [
            {
                "rule_id": "AC-001",
                "policy": "Access Management Policy v3.0",
                "keywords": ["shared account", "shared password", "generic account", "shared credentials"],
                "violation_template": "Shared account or credentials detected in use",
                "severity": "critical",
                "regulation": "SOC2 CC6.1",
            },
            {
                "rule_id": "AC-002",
                "policy": "Access Management Policy v3.0",
                "keywords": ["terminated", "offboarded", "former employee", "deactivated user"],
                "violation_template": "Active account found for terminated or offboarded user",
                "severity": "high",
                "regulation": "SOC2 CC6.3",
            },
            {
                "rule_id": "AC-003",
                "policy": "Privileged Access Policy v1.4",
                "keywords": ["admin", "root", "superuser", "privilege", "elevated"],
                "violation_template": "Excessive privileged access without documented justification",
                "severity": "high",
                "regulation": "ISO 27001 A.9.2.3",
            },
        ],
        "data_protection": [
            {
                "rule_id": "DP-001",
                "policy": "Encryption Standards Policy v2.0",
                "keywords": ["unencrypted", "plain text", "no encryption", "cleartext", "http://"],
                "violation_template": "Sensitive data transmitted or stored without encryption",
                "severity": "critical",
                "regulation": "GDPR Art.32",
            },
            {
                "rule_id": "DP-002",
                "policy": "Data Classification Policy v1.8",
                "keywords": ["unclassified", "no label", "unlabeled", "no classification"],
                "violation_template": "Data assets lacking mandatory classification labels",
                "severity": "medium",
                "regulation": "ISO 27001 A.8.2",
            },
            {
                "rule_id": "DP-003",
                "policy": "Privacy Policy v4.0",
                "keywords": ["no consent", "without consent", "opt-out", "tracking"],
                "violation_template": "Personal data processed without documented lawful basis or consent",
                "severity": "critical",
                "regulation": "GDPR Art.6",
            },
        ],
        "change_management": [
            {
                "rule_id": "CM-001",
                "policy": "Change Management Policy v2.5",
                "keywords": ["unapproved", "without approval", "bypass", "emergency change"],
                "violation_template": "System change deployed without required approval workflow",
                "severity": "high",
                "regulation": "SOC2 CC8.1",
            },
            {
                "rule_id": "CM-002",
                "policy": "Change Management Policy v2.5",
                "keywords": ["production", "direct", "hotfix", "manual deploy"],
                "violation_template": "Direct modification to production without change ticket",
                "severity": "high",
                "regulation": "SOC2 CC8.1",
            },
        ],
        "incident_management": [
            {
                "rule_id": "IM-001",
                "policy": "Incident Response Policy v3.2",
                "keywords": ["unreported", "not reported", "delayed notification", "late report"],
                "violation_template": "Security incident not reported within mandatory timeframe",
                "severity": "high",
                "regulation": "GDPR Art.33",
            },
        ],
        "third_party": [
            {
                "rule_id": "TP-001",
                "policy": "Vendor Management Policy v2.0",
                "keywords": ["vendor", "third party", "supplier", "contractor", "outsource"],
                "violation_template": "Third-party access granted without completed risk assessment",
                "severity": "high",
                "regulation": "SAMA CSF 3.5",
            },
        ],
    }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Scan for policy and regulatory violations.

        Evaluates the scan target description against violation rules
        across the specified policy domains. Identifies matching violations,
        assigns severity, and provides regulatory references.

        Args:
            params: Tool parameters with scan_target, policy_domains,
                    and time_range_hours.

        Returns:
            Success result with detected violations, severity breakdown,
            and scan summary.
        """
        scan_target = params.get("scan_target", "")
        policy_domains = params.get("policy_domains", [])
        time_range_hours = params.get("time_range_hours", 24)

        if not scan_target:
            return self.error_result("No scan target provided for violation detection.")

        try:
            now = datetime.now(timezone.utc)
            scan_id = str(uuid.uuid4())
            target_lower = scan_target.lower()

            # Determine which domains to scan
            if not policy_domains:
                domains_to_scan = list(self._VIOLATION_RULES.keys())
            else:
                domains_to_scan = [
                    d for d in policy_domains
                    if d in self._VIOLATION_RULES
                ]
                # Also include any domains whose keywords match the target
                for domain, rules in self._VIOLATION_RULES.items():
                    if domain not in domains_to_scan:
                        for rule in rules:
                            if any(kw in target_lower for kw in rule["keywords"]):
                                domains_to_scan.append(domain)
                                break

            violations: list[dict[str, Any]] = []
            rules_evaluated = 0

            for domain in domains_to_scan:
                domain_rules = self._VIOLATION_RULES.get(domain, [])
                for rule in domain_rules:
                    rules_evaluated += 1
                    matched_keywords = [kw for kw in rule["keywords"] if kw in target_lower]

                    if matched_keywords:
                        # Compute a detection confidence based on keyword match density
                        confidence = min(0.99, 0.60 + len(matched_keywords) * 0.10)
                        detected_time = now - timedelta(
                            hours=hash(rule["rule_id"]) % max(1, time_range_hours)
                        )

                        violations.append({
                            "violation_id": f"VIO-{uuid.uuid4().hex[:8].upper()}",
                            "rule_id": rule["rule_id"],
                            "policy": rule["policy"],
                            "policy_domain": domain,
                            "description": rule["violation_template"],
                            "severity": rule["severity"],
                            "regulation": rule["regulation"],
                            "matched_indicators": matched_keywords,
                            "confidence": round(confidence, 2),
                            "detected_at": detected_time.isoformat(),
                            "affected_entity": scan_target[:200],
                            "status": "open",
                            "requires_immediate_action": rule["severity"] in ("critical", "high"),
                        })

            # Severity breakdown
            severity_breakdown = {
                "critical": sum(1 for v in violations if v["severity"] == "critical"),
                "high": sum(1 for v in violations if v["severity"] == "high"),
                "medium": sum(1 for v in violations if v["severity"] == "medium"),
                "low": sum(1 for v in violations if v["severity"] == "low"),
            }

            # Sort violations by severity
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            violations.sort(key=lambda v: severity_order.get(v["severity"], 99))

            return self.success_result({
                "scan_id": scan_id,
                "scan_target": scan_target[:200],
                "policy_domains_scanned": domains_to_scan,
                "rules_evaluated": rules_evaluated,
                "time_range_hours": time_range_hours,
                "violations_found": len(violations),
                "severity_breakdown": severity_breakdown,
                "violations": violations,
                "immediate_actions_required": severity_breakdown["critical"] + severity_breakdown["high"],
                "scan_started_at": (now - timedelta(seconds=rules_evaluated * 2)).isoformat(),
                "scan_completed_at": now.isoformat(),
                "summary": (
                    f"Violation scan of '{scan_target[:60]}' complete. "
                    f"Evaluated {rules_evaluated} rules across {len(domains_to_scan)} domain(s). "
                    f"Detected {len(violations)} violation(s): "
                    f"{severity_breakdown['critical']} critical, "
                    f"{severity_breakdown['high']} high, "
                    f"{severity_breakdown['medium']} medium."
                ),
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class EvidenceCollectorTool(BaseTool):
    """Gathers and catalogs compliance evidence artifacts.

    Collects evidence artifacts from systems, logs, configurations,
    and documents to support compliance audits and control testing.
    Maintains chain-of-custody metadata and integrity hashes for
    each artifact collected.

    In production this tool would integrate with SIEM, configuration
    management databases, document management systems, and audit
    platforms. For local development it generates realistic mock
    evidence artifacts with proper metadata and integrity tracking.
    """

    @property
    def name(self) -> str:
        return "collect_evidence"

    @property
    def description(self) -> str:
        return (
            "Collect and catalog compliance evidence for audits and control "
            "testing. Returns evidence artifacts with metadata and chain of custody."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "control_id": {
                    "type": "string",
                    "description": "Control ID to collect evidence for.",
                },
                "evidence_type": {
                    "type": "string",
                    "description": "Type of evidence: 'log', 'config', 'screenshot', 'document', 'attestation'.",
                },
                "framework": {
                    "type": "string",
                    "description": "Compliance framework context.",
                },
            },
            "required": ["control_id"],
        }

    # Evidence templates by type with realistic sources and descriptions
    _EVIDENCE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
        "log": [
            {
                "source": "aws_cloudtrail",
                "description": "CloudTrail API activity logs for the control period",
                "format": "json",
                "size_kb": 2450,
                "record_count": 15832,
            },
            {
                "source": "siem_splunk",
                "description": "SIEM correlation events related to access control monitoring",
                "format": "csv",
                "size_kb": 1120,
                "record_count": 4567,
            },
            {
                "source": "application_audit_log",
                "description": "Application-level audit trail for user actions",
                "format": "json",
                "size_kb": 890,
                "record_count": 8921,
            },
        ],
        "config": [
            {
                "source": "aws_config",
                "description": "AWS Config snapshot showing security group configurations",
                "format": "json",
                "size_kb": 340,
                "record_count": 48,
            },
            {
                "source": "terraform_state",
                "description": "Infrastructure-as-code state file showing encryption settings",
                "format": "json",
                "size_kb": 1560,
                "record_count": 127,
            },
            {
                "source": "iam_policy_export",
                "description": "IAM policy and role configuration export",
                "format": "json",
                "size_kb": 780,
                "record_count": 95,
            },
        ],
        "screenshot": [
            {
                "source": "admin_console",
                "description": "Screenshot of MFA enforcement settings in admin console",
                "format": "png",
                "size_kb": 245,
                "record_count": 1,
            },
            {
                "source": "monitoring_dashboard",
                "description": "Screenshot of security monitoring dashboard showing alert coverage",
                "format": "png",
                "size_kb": 380,
                "record_count": 1,
            },
        ],
        "document": [
            {
                "source": "policy_repository",
                "description": "Current approved version of the information security policy",
                "format": "pdf",
                "size_kb": 520,
                "record_count": 1,
            },
            {
                "source": "procedure_manual",
                "description": "Access review procedure document with approval signatures",
                "format": "pdf",
                "size_kb": 340,
                "record_count": 1,
            },
            {
                "source": "training_records",
                "description": "Security awareness training completion records for current period",
                "format": "xlsx",
                "size_kb": 180,
                "record_count": 342,
            },
        ],
        "attestation": [
            {
                "source": "management_attestation",
                "description": "Signed management attestation of control operating effectiveness",
                "format": "pdf",
                "size_kb": 120,
                "record_count": 1,
            },
            {
                "source": "vendor_soc2_report",
                "description": "Third-party SOC 2 Type II report from service provider",
                "format": "pdf",
                "size_kb": 4200,
                "record_count": 1,
            },
        ],
    }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Collect and catalog compliance evidence artifacts.

        Gathers evidence of the requested type for the specified control,
        generates integrity hashes, and maintains chain-of-custody metadata.

        Args:
            params: Tool parameters with control_id, evidence_type,
                    and framework.

        Returns:
            Success result with collected artifacts, integrity metadata,
            chain of custody, and collection summary.
        """
        control_id = params.get("control_id", "")
        evidence_type = params.get("evidence_type", "")
        framework = params.get("framework", "")

        if not control_id:
            return self.error_result("No control ID provided for evidence collection.")

        try:
            now = datetime.now(timezone.utc)
            evidence_id = f"EV-{uuid.uuid4().hex[:8].upper()}"

            # Determine which evidence templates to use
            if evidence_type and evidence_type in self._EVIDENCE_TEMPLATES:
                templates = self._EVIDENCE_TEMPLATES[evidence_type]
            else:
                # Collect across multiple types when no specific type requested
                templates = []
                for etype in ("log", "config", "document"):
                    type_templates = self._EVIDENCE_TEMPLATES.get(etype, [])
                    if type_templates:
                        # Pick one from each type deterministically
                        idx = hash(control_id + etype) % len(type_templates)
                        templates.append({**type_templates[idx], "_evidence_type": etype})

            # Generate artifacts from templates
            artifacts: list[dict[str, Any]] = []
            total_size_kb = 0
            total_records = 0

            for i, template in enumerate(templates):
                artifact_type = template.get("_evidence_type", evidence_type or "log")
                collection_offset = timedelta(seconds=i * 15 + hash(control_id) % 30)
                artifact_hash = uuid.uuid4().hex
                size = template.get("size_kb", 100)
                records = template.get("record_count", 1)
                total_size_kb += size
                total_records += records

                artifacts.append({
                    "artifact_id": f"ART-{uuid.uuid4().hex[:6].upper()}",
                    "evidence_type": artifact_type,
                    "source_system": template["source"],
                    "description": template["description"],
                    "format": template["format"],
                    "size_kb": size,
                    "record_count": records,
                    "collection_period": {
                        "start": (now - timedelta(days=90)).isoformat(),
                        "end": now.isoformat(),
                    },
                    "collected_at": (now - collection_offset).isoformat(),
                    "integrity": {
                        "hash_algorithm": "SHA-256",
                        "hash_value": f"sha256:{artifact_hash}",
                        "verified": True,
                    },
                    "storage_location": f"s3://compliance-evidence/{framework or 'general'}/{control_id}/{artifact_hash[:12]}",
                    "retention_until": (now + timedelta(days=2555)).strftime("%Y-%m-%d"),
                })

            # Assess evidence sufficiency
            evidence_categories = set()
            for art in artifacts:
                evidence_categories.add(art["evidence_type"])

            sufficiency_score = min(100, len(artifacts) * 20 + len(evidence_categories) * 15)

            if sufficiency_score >= 80:
                sufficiency_assessment = "sufficient"
            elif sufficiency_score >= 50:
                sufficiency_assessment = "partially_sufficient"
            else:
                sufficiency_assessment = "insufficient"

            # Determine what additional evidence might be needed
            recommended_additional: list[str] = []
            if "attestation" not in evidence_categories:
                recommended_additional.append(
                    "Collect management attestation to strengthen evidence package"
                )
            if "log" not in evidence_categories:
                recommended_additional.append(
                    "Include system audit logs covering the full control period"
                )
            if "config" not in evidence_categories:
                recommended_additional.append(
                    "Add configuration snapshots to demonstrate control implementation"
                )

            return self.success_result({
                "evidence_id": evidence_id,
                "control_id": control_id,
                "framework": framework or "general",
                "evidence_types_collected": sorted(evidence_categories),
                "artifacts_collected": len(artifacts),
                "total_size_kb": total_size_kb,
                "total_records": total_records,
                "artifacts": artifacts,
                "sufficiency": {
                    "score": sufficiency_score,
                    "assessment": sufficiency_assessment,
                    "recommended_additional": recommended_additional,
                },
                "chain_of_custody": {
                    "collection_id": evidence_id,
                    "collected_by": "ai-compliance-officer",
                    "collector_role": "automated_evidence_collection",
                    "collected_at": now.isoformat(),
                    "integrity_verified": True,
                    "verification_method": "SHA-256 hash comparison",
                    "tamper_evident": True,
                    "custody_log": [
                        {
                            "action": "collected",
                            "actor": "ai-compliance-officer",
                            "timestamp": now.isoformat(),
                            "notes": f"Automated evidence collection for control {control_id}",
                        },
                        {
                            "action": "integrity_verified",
                            "actor": "evidence-integrity-service",
                            "timestamp": (now + timedelta(seconds=5)).isoformat(),
                            "notes": "All artifact hashes verified against source systems",
                        },
                        {
                            "action": "cataloged",
                            "actor": "evidence-catalog-service",
                            "timestamp": (now + timedelta(seconds=10)).isoformat(),
                            "notes": f"Evidence package cataloged under {evidence_id}",
                        },
                    ],
                },
                "collection_timestamp": now.isoformat(),
                "summary": (
                    f"Evidence collection for control {control_id} complete. "
                    f"Collected {len(artifacts)} artifact(s) across "
                    f"{len(evidence_categories)} type(s). "
                    f"Total size: {total_size_kb} KB. "
                    f"Sufficiency: {sufficiency_assessment} ({sufficiency_score}/100)."
                ),
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class RemediationTrackerTool(BaseTool):
    """Tracks remediation actions and SLA adherence.

    Manages remediation plans for identified violations and control
    deficiencies, tracking progress, task completion, SLA compliance,
    and escalation status. Supports create, status check, update,
    and close operations.

    In production this tool would integrate with a GRC ticketing
    system, Jira, or ServiceNow for remediation workflow management.
    For local development it simulates remediation lifecycle states
    with realistic timelines and task breakdowns.
    """

    @property
    def name(self) -> str:
        return "track_remediation"

    @property
    def description(self) -> str:
        return (
            "Track remediation actions for compliance violations and control "
            "deficiencies. Returns remediation status, SLA adherence, and progress."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "violation_id": {
                    "type": "string",
                    "description": "Violation or finding ID to track remediation for.",
                },
                "action": {
                    "type": "string",
                    "description": "Action: 'status', 'create', 'update', or 'close'.",
                },
                "remediation_plan": {
                    "type": "object",
                    "description": "Remediation plan details (for create/update).",
                },
            },
            "required": ["violation_id"],
        }

    # SLA definitions by severity
    _SLA_DEFINITIONS: dict[str, dict[str, Any]] = {
        "critical": {"days": 7, "escalation_after_days": 3, "approver": "ciso"},
        "high": {"days": 14, "escalation_after_days": 7, "approver": "security-manager"},
        "medium": {"days": 30, "escalation_after_days": 14, "approver": "compliance-lead"},
        "low": {"days": 90, "escalation_after_days": 45, "approver": "team-lead"},
    }

    # Mock remediation task templates
    _TASK_TEMPLATES: list[dict[str, str]] = [
        {"title": "Root cause analysis", "owner": "security-analyst", "status": "completed"},
        {"title": "Develop remediation approach", "owner": "security-engineer", "status": "completed"},
        {"title": "Implement technical fix", "owner": "devops-engineer", "status": "in_progress"},
        {"title": "Validate fix in staging", "owner": "qa-engineer", "status": "pending"},
        {"title": "Deploy to production", "owner": "devops-engineer", "status": "pending"},
        {"title": "Post-implementation verification", "owner": "compliance-analyst", "status": "pending"},
        {"title": "Update documentation and policies", "owner": "compliance-lead", "status": "pending"},
    ]

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track remediation for a violation or control deficiency.

        Handles create, status, update, and close actions for
        remediation plans, generating realistic task breakdowns,
        SLA tracking, and progress metrics.

        Args:
            params: Tool parameters with violation_id, action,
                    and optional remediation_plan.

        Returns:
            Success result with remediation details, task breakdown,
            SLA status, and progress metrics.
        """
        violation_id = params.get("violation_id", "")
        action = params.get("action", "status")
        remediation_plan = params.get("remediation_plan", {})

        if not violation_id:
            return self.error_result("No violation ID provided for remediation tracking.")

        try:
            now = datetime.now(timezone.utc)
            remediation_id = f"REM-{uuid.uuid4().hex[:8].upper()}"

            # Determine severity from violation_id or plan
            severity = remediation_plan.get("severity", "medium")
            sla_def = self._SLA_DEFINITIONS.get(severity, self._SLA_DEFINITIONS["medium"])

            if action == "create":
                return self._handle_create(
                    violation_id, remediation_id, remediation_plan, severity, sla_def, now
                )
            elif action == "close":
                return self._handle_close(violation_id, remediation_id, now)
            elif action == "update":
                return self._handle_update(
                    violation_id, remediation_id, remediation_plan, severity, sla_def, now
                )
            else:
                # Default: status check
                return self._handle_status(violation_id, remediation_id, severity, sla_def, now)
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")

    def _handle_create(
        self,
        violation_id: str,
        remediation_id: str,
        plan: dict[str, Any],
        severity: str,
        sla_def: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        """Handle remediation plan creation."""
        deadline = now + timedelta(days=sla_def["days"])
        escalation_date = now + timedelta(days=sla_def["escalation_after_days"])

        tasks = [
            {
                "task_id": f"TSK-{uuid.uuid4().hex[:6].upper()}",
                "title": t["title"],
                "assigned_to": t["owner"],
                "status": "pending",
                "created_at": now.isoformat(),
                "due_date": (now + timedelta(days=i * (sla_def["days"] // 7 + 1) + 1)).strftime("%Y-%m-%d"),
            }
            for i, t in enumerate(self._TASK_TEMPLATES)
        ]

        return self.success_result({
            "violation_id": violation_id,
            "remediation_id": remediation_id,
            "action": "create",
            "status": "open",
            "severity": severity,
            "title": plan.get("title", f"Remediation plan for {violation_id}"),
            "description": plan.get(
                "description",
                f"Address {severity}-severity finding identified in {violation_id}",
            ),
            "assigned_to": plan.get("assigned_to", sla_def["approver"]),
            "created_at": now.isoformat(),
            "progress_pct": 0,
            "tasks": tasks,
            "task_count": len(tasks),
            "sla": {
                "severity": severity,
                "deadline": deadline.isoformat(),
                "days_remaining": sla_def["days"],
                "escalation_date": escalation_date.isoformat(),
                "on_track": True,
                "approver": sla_def["approver"],
            },
            "audit_trail": [
                {
                    "action": "created",
                    "actor": "ai-compliance-officer",
                    "timestamp": now.isoformat(),
                    "notes": f"Remediation plan created for {violation_id}",
                },
            ],
            "summary": (
                f"Remediation plan {remediation_id} created for {violation_id}. "
                f"Severity: {severity}. Deadline: {deadline.strftime('%Y-%m-%d')}. "
                f"{len(tasks)} tasks assigned."
            ),
        })

    def _handle_status(
        self,
        violation_id: str,
        remediation_id: str,
        severity: str,
        sla_def: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        """Handle remediation status check."""
        # Simulate an in-progress remediation with partial completion
        created_at = now - timedelta(days=hash(violation_id) % sla_def["days"] + 3)
        deadline = created_at + timedelta(days=sla_def["days"])
        days_remaining = max(0, (deadline - now).days)
        days_elapsed = (now - created_at).days

        # Generate task list with partial completion
        tasks = []
        completed_tasks = 0
        for i, template in enumerate(self._TASK_TEMPLATES):
            # Determine status based on position
            if i < 2:
                status = "completed"
                completed_tasks += 1
            elif i == 2:
                status = "in_progress"
            else:
                status = "pending"

            tasks.append({
                "task_id": f"TSK-{uuid.uuid4().hex[:6].upper()}",
                "title": template["title"],
                "assigned_to": template["owner"],
                "status": status,
                "due_date": (created_at + timedelta(days=(i + 1) * (sla_def["days"] // 7 + 1))).strftime("%Y-%m-%d"),
            })

        total_tasks = len(tasks)
        progress_pct = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
        on_track = days_remaining > 0 and progress_pct >= (days_elapsed / sla_def["days"]) * 50

        return self.success_result({
            "violation_id": violation_id,
            "remediation_id": remediation_id,
            "action": "status",
            "status": "in_progress",
            "severity": severity,
            "assigned_to": sla_def["approver"],
            "created_at": created_at.isoformat(),
            "progress_pct": progress_pct,
            "tasks": tasks,
            "tasks_completed": completed_tasks,
            "tasks_in_progress": sum(1 for t in tasks if t["status"] == "in_progress"),
            "tasks_pending": sum(1 for t in tasks if t["status"] == "pending"),
            "task_count": total_tasks,
            "sla": {
                "severity": severity,
                "deadline": deadline.isoformat(),
                "days_remaining": days_remaining,
                "days_elapsed": days_elapsed,
                "on_track": on_track,
                "escalated": not on_track,
                "approver": sla_def["approver"],
            },
            "last_updated": (now - timedelta(hours=hash(violation_id) % 24 + 1)).isoformat(),
            "audit_trail": [
                {
                    "action": "created",
                    "actor": "ai-compliance-officer",
                    "timestamp": created_at.isoformat(),
                    "notes": f"Remediation plan created for {violation_id}",
                },
                {
                    "action": "task_completed",
                    "actor": "security-analyst",
                    "timestamp": (created_at + timedelta(days=2)).isoformat(),
                    "notes": "Root cause analysis completed",
                },
                {
                    "action": "task_completed",
                    "actor": "security-engineer",
                    "timestamp": (created_at + timedelta(days=5)).isoformat(),
                    "notes": "Remediation approach documented and approved",
                },
            ],
            "summary": (
                f"Remediation {remediation_id} for {violation_id}: "
                f"{progress_pct}% complete ({completed_tasks}/{total_tasks} tasks). "
                f"SLA: {days_remaining} days remaining. "
                f"{'On track' if on_track else 'AT RISK - escalation required'}."
            ),
        })

    def _handle_update(
        self,
        violation_id: str,
        remediation_id: str,
        plan: dict[str, Any],
        severity: str,
        sla_def: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        """Handle remediation plan update."""
        created_at = now - timedelta(days=hash(violation_id) % sla_def["days"] + 3)
        deadline = created_at + timedelta(days=sla_def["days"])
        progress_pct = min(85, 45 + hash(violation_id) % 30)

        return self.success_result({
            "violation_id": violation_id,
            "remediation_id": remediation_id,
            "action": "update",
            "status": "in_progress",
            "severity": severity,
            "progress_pct": progress_pct,
            "updates_applied": {
                "fields_updated": list(plan.keys()) if plan else ["status"],
                "updated_at": now.isoformat(),
                "updated_by": "ai-compliance-officer",
            },
            "sla": {
                "deadline": deadline.isoformat(),
                "days_remaining": max(0, (deadline - now).days),
                "on_track": True,
            },
            "last_updated": now.isoformat(),
            "summary": (
                f"Remediation {remediation_id} updated. "
                f"Progress: {progress_pct}%. "
                f"Fields updated: {', '.join(plan.keys()) if plan else 'status'}."
            ),
        })

    def _handle_close(
        self,
        violation_id: str,
        remediation_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        """Handle remediation closure."""
        created_at = now - timedelta(days=hash(violation_id) % 25 + 5)

        return self.success_result({
            "violation_id": violation_id,
            "remediation_id": remediation_id,
            "action": "close",
            "status": "closed",
            "progress_pct": 100,
            "resolution": "remediated",
            "created_at": created_at.isoformat(),
            "closed_at": now.isoformat(),
            "resolution_time_days": (now - created_at).days,
            "verification": {
                "verified": True,
                "verified_by": "compliance-lead",
                "verified_at": now.isoformat(),
                "verification_method": "Control re-testing and evidence review",
            },
            "audit_trail": [
                {
                    "action": "closed",
                    "actor": "ai-compliance-officer",
                    "timestamp": now.isoformat(),
                    "notes": f"Remediation verified and closed for {violation_id}",
                },
            ],
            "summary": (
                f"Remediation {remediation_id} for {violation_id} closed. "
                f"Resolved in {(now - created_at).days} days. "
                f"Verification: passed."
            ),
        })


# ---------------------------------------------------------------------------
# Legal Contract Analyst Tools (stubs)
# ---------------------------------------------------------------------------


class ContractParserTool(BaseTool):
    """Parses and ingests contract documents.

    Extracts structured data from contract documents including parties,
    dates, values, and document structure.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "parse_contract"

    @property
    def description(self) -> str:
        return (
            "Parse and ingest a contract document. Extracts parties, dates, "
            "values, and document structure into a structured format."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "Raw text content of the contract document.",
                },
                "document_type": {
                    "type": "string",
                    "description": "Type of contract: 'MSA', 'NDA', 'SOW', 'SLA', 'amendment', 'other'.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional document metadata.",
                },
            },
            "required": ["document_text"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("ContractParserTool.execute called with params=%s", params)
            doc_type = params.get("document_type", "MSA")
            return self.success_result({
                "document_id": f"DOC-{uuid.uuid4().hex[:8].upper()}",
                "document_type": doc_type,
                "parties": [
                    {"name": "Acme Corp", "role": "provider"},
                    {"name": "Client Inc", "role": "recipient"},
                ],
                "effective_date": "2025-01-15",
                "expiration_date": "2026-01-14",
                "total_value": 250000.00,
                "currency": "USD",
                "sections_identified": 12,
                "clauses_extracted": 34,
                "parsed_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class ClauseExtractorTool(BaseTool):
    """Extracts and classifies contract clauses.

    Identifies individual clauses within a contract, classifies them
    by type, and assesses their terms and conditions.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "extract_clauses"

    @property
    def description(self) -> str:
        return (
            "Extract and classify clauses from a contract document. Returns "
            "identified clauses with type, risk level, and key terms."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "ID of the parsed contract document.",
                },
                "clause_types": {
                    "type": "array",
                    "description": "Types of clauses to extract (e.g., 'indemnity', 'liability', 'termination').",
                    "items": {"type": "string"},
                },
                "document_text": {
                    "type": "string",
                    "description": "Raw contract text if document_id is not available.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("ClauseExtractorTool.execute called with params=%s", params)
            document_id = params.get("document_id", "DOC-UNKNOWN")
            return self.success_result({
                "document_id": document_id,
                "clauses_found": 3,
                "clauses": [
                    {
                        "clause_id": f"CLS-{uuid.uuid4().hex[:6].upper()}",
                        "type": "indemnity",
                        "section": "Section 8.1",
                        "summary": "Mutual indemnification for third-party claims",
                        "risk_level": "medium",
                        "key_terms": ["mutual", "third-party claims", "negligence"],
                    },
                    {
                        "clause_id": f"CLS-{uuid.uuid4().hex[:6].upper()}",
                        "type": "limitation_of_liability",
                        "section": "Section 9.2",
                        "summary": "Liability capped at 12 months of fees",
                        "risk_level": "low",
                        "key_terms": ["cap", "12 months", "direct damages only"],
                    },
                    {
                        "clause_id": f"CLS-{uuid.uuid4().hex[:6].upper()}",
                        "type": "termination",
                        "section": "Section 11.1",
                        "summary": "Either party may terminate with 30 days notice",
                        "risk_level": "low",
                        "key_terms": ["30 days", "written notice", "cure period"],
                    },
                ],
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class ContractRiskScorerTool(BaseTool):
    """Scores contract risk across multiple dimensions.

    Evaluates a contract's risk profile across legal, financial,
    operational, and compliance dimensions.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "score_contract_risk"

    @property
    def description(self) -> str:
        return (
            "Score a contract's risk across legal, financial, operational, "
            "and compliance dimensions. Returns risk scores and recommendations."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "ID of the parsed contract document.",
                },
                "clauses": {
                    "type": "array",
                    "description": "Extracted clauses to score.",
                    "items": {"type": "object"},
                },
                "context": {
                    "type": "object",
                    "description": "Business context for risk evaluation.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("ContractRiskScorerTool.execute called with params=%s", params)
            document_id = params.get("document_id", "DOC-UNKNOWN")
            return self.success_result({
                "document_id": document_id,
                "overall_risk_score": 42,
                "risk_level": "medium",
                "dimensions": {
                    "legal": {"score": 35, "level": "low"},
                    "financial": {"score": 50, "level": "medium"},
                    "operational": {"score": 40, "level": "medium"},
                    "compliance": {"score": 30, "level": "low"},
                },
                "high_risk_clauses": [],
                "recommendations": [
                    "Consider negotiating a lower liability cap",
                    "Add data processing addendum for GDPR compliance",
                ],
                "scored_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class ObligationTrackerTool(BaseTool):
    """Tracks contractual obligations and deadlines.

    Monitors active obligations from contracts, tracks compliance
    with deadlines, and generates renewal and expiration alerts.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "track_obligations"

    @property
    def description(self) -> str:
        return (
            "Track contractual obligations, deadlines, and renewals. Returns "
            "active obligations, upcoming deadlines, and compliance status."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Contract document ID to track obligations for.",
                },
                "action": {
                    "type": "string",
                    "description": "Action: 'list', 'status', 'upcoming', or 'overdue'.",
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days ahead to look for upcoming obligations.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("ObligationTrackerTool.execute called with params=%s", params)
            document_id = params.get("document_id", "DOC-UNKNOWN")
            action = params.get("action", "list")
            return self.success_result({
                "document_id": document_id,
                "action": action,
                "total_obligations": 5,
                "obligations": [
                    {
                        "obligation_id": f"OBL-{uuid.uuid4().hex[:6].upper()}",
                        "type": "payment",
                        "description": "Quarterly service fee payment",
                        "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "status": "pending",
                        "party": "Client Inc",
                    },
                    {
                        "obligation_id": f"OBL-{uuid.uuid4().hex[:6].upper()}",
                        "type": "reporting",
                        "description": "Monthly SLA compliance report",
                        "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d"),
                        "status": "pending",
                        "party": "Acme Corp",
                    },
                ],
                "upcoming_count": 2,
                "overdue_count": 0,
                "tracked_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


# ---------------------------------------------------------------------------
# Cybersecurity Analyst Tools (stubs)
# ---------------------------------------------------------------------------


class AlertTriageTool(BaseTool):
    """Prioritizes and deduplicates security alerts.

    Processes incoming security alerts, assigns priority based on
    severity and context, and deduplicates related alerts.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "triage_alerts"

    @property
    def description(self) -> str:
        return (
            "Triage and prioritize security alerts. Deduplicates related "
            "alerts and assigns priority based on severity and context."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "alerts": {
                    "type": "array",
                    "description": "List of alert objects to triage.",
                    "items": {"type": "object"},
                },
                "alert_source": {
                    "type": "string",
                    "description": "Source of alerts: 'SIEM', 'IDS', 'EDR', 'WAF', 'cloud_trail'.",
                },
                "time_range_hours": {
                    "type": "integer",
                    "description": "Time range in hours for alert retrieval.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("AlertTriageTool.execute called with params=%s", params)
            alert_source = params.get("alert_source", "SIEM")
            return self.success_result({
                "source": alert_source,
                "total_alerts_processed": 24,
                "deduplicated_count": 18,
                "priority_breakdown": {
                    "critical": 1,
                    "high": 3,
                    "medium": 8,
                    "low": 6,
                    "informational": 6,
                },
                "top_alerts": [
                    {
                        "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
                        "title": "Unusual outbound data transfer detected",
                        "severity": "critical",
                        "source": alert_source,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "triage_priority": 1,
                        "recommended_action": "Immediate investigation required",
                    },
                    {
                        "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
                        "title": "Multiple failed login attempts from external IP",
                        "severity": "high",
                        "source": alert_source,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "triage_priority": 2,
                        "recommended_action": "Block IP and investigate account",
                    },
                ],
                "triaged_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class ThreatAssessorTool(BaseTool):
    """Evaluates threat severity with intelligence feeds.

    Assesses identified threats using threat intelligence data,
    MITRE ATT&CK mapping, and contextual risk factors.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "assess_threat"

    @property
    def description(self) -> str:
        return (
            "Assess threat severity using threat intelligence feeds, MITRE "
            "ATT&CK mapping, and contextual risk factors."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "threat_description": {
                    "type": "string",
                    "description": "Description of the threat to assess.",
                },
                "indicators": {
                    "type": "array",
                    "description": "Indicators of compromise (IOCs).",
                    "items": {"type": "string"},
                },
                "affected_systems": {
                    "type": "array",
                    "description": "List of affected or potentially affected systems.",
                    "items": {"type": "string"},
                },
            },
            "required": ["threat_description"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("ThreatAssessorTool.execute called with params=%s", params)
            threat_description = params.get("threat_description", "Unknown threat")
            return self.success_result({
                "threat_id": f"THR-{uuid.uuid4().hex[:8].upper()}",
                "description": threat_description,
                "severity": "high",
                "cvss_score": 7.8,
                "mitre_attack": {
                    "tactic": "Exfiltration",
                    "technique": "T1048 - Exfiltration Over Alternative Protocol",
                    "sub_technique": "T1048.002 - Exfiltration Over Asymmetric Encrypted Non-C2 Protocol",
                },
                "threat_intel": {
                    "known_threat_actor": False,
                    "campaign_match": None,
                    "ioc_matches": 0,
                },
                "risk_factors": {
                    "exploitability": "high",
                    "data_sensitivity": "medium",
                    "exposure": "internal",
                },
                "recommended_actions": [
                    "Isolate affected systems",
                    "Capture forensic evidence",
                    "Escalate to incident response team",
                ],
                "assessed_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")


class ImpactAnalyzerTool(BaseTool):
    """Analyzes potential business and regulatory impact of security events.

    Evaluates the business, regulatory, financial, and reputational
    impact of security incidents and threats.

    Stub implementation -- returns placeholder data for local development.
    """

    @property
    def name(self) -> str:
        return "analyze_impact"

    @property
    def description(self) -> str:
        return (
            "Analyze the potential business, regulatory, financial, and "
            "reputational impact of a security event or threat."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "event_description": {
                    "type": "string",
                    "description": "Description of the security event or threat.",
                },
                "affected_assets": {
                    "type": "array",
                    "description": "List of affected business assets or systems.",
                    "items": {"type": "string"},
                },
                "data_classification": {
                    "type": "string",
                    "description": "Classification of affected data: 'public', 'internal', 'confidential', 'restricted'.",
                },
            },
            "required": ["event_description"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            logger.info("ImpactAnalyzerTool.execute called with params=%s", params)
            event_description = params.get("event_description", "Unknown event")
            data_classification = params.get("data_classification", "internal")
            return self.success_result({
                "event": event_description,
                "impact_id": f"IMP-{uuid.uuid4().hex[:8].upper()}",
                "overall_impact": "moderate",
                "impact_score": 55,
                "dimensions": {
                    "business": {
                        "score": 50,
                        "level": "moderate",
                        "details": "Potential service disruption for 2-4 hours",
                    },
                    "regulatory": {
                        "score": 60,
                        "level": "moderate",
                        "details": f"Notification may be required for {data_classification} data",
                    },
                    "financial": {
                        "score": 40,
                        "level": "low",
                        "details": "Estimated remediation cost: $10,000-$50,000",
                    },
                    "reputational": {
                        "score": 45,
                        "level": "low",
                        "details": "Limited external visibility expected",
                    },
                },
                "affected_regulations": ["GDPR Art. 33", "SOC2 CC7.3"],
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "stub": True,
            })
        except Exception as exc:
            return self.error_result(f"Internal error in {self.__class__.__name__}: {exc}")
