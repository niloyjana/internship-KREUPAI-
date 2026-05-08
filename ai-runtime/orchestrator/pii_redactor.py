"""PII Redactor -- detects and redacts personally identifiable information.

Scans text for 8 PII pattern types (emails, phone numbers, credit cards,
passports, IBANs, SSNs, GCC national IDs, IP addresses) and replaces them
with redaction tokens before content is sent to an LLM provider.

Implements P5_Security_Secrets_Spec Section 5.
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PIIRedactor:
    """Detects and redacts PII from text before sending to LLM.

    Supports configurable per-agent policies that can enable or disable
    specific PII pattern categories. By default all patterns are active.
    """

    # Compiled PII patterns keyed by category name (P5 spec: 8 types)
    PII_PATTERNS: dict[str, re.Pattern[str]] = {
        "email": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        "phone_intl": re.compile(
            r"\+?[0-9]{10,15}"
        ),
        "credit_card": re.compile(
            r"\b(?:\d{4}[\s-]?){3}\d{4}\b"
        ),
        "passport": re.compile(
            r"\b[A-Z]{1,2}[0-9]{6,9}\b"
        ),
        "iban": re.compile(
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b"
        ),
        "ssn_us": re.compile(
            r"\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0{4})\d{4}\b"
        ),
        "national_id_gcc": re.compile(
            r"\b\d{9,12}\b"
        ),
        "ip_address": re.compile(
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ),
    }

    # Human-readable redaction replacement tokens (P5 spec format)
    REDACTION_TOKENS: dict[str, str] = {
        "email": "[EMAIL_REDACTED]",
        "phone_intl": "[PHONE_REDACTED]",
        "credit_card": "[CARD_REDACTED]",
        "passport": "[PASSPORT_REDACTED]",
        "iban": "[IBAN_REDACTED]",
        "ssn_us": "[SSN_REDACTED]",
        "national_id_gcc": "[ID_REDACTED]",
        "ip_address": "[IP_REDACTED]",
    }

    def redact(
        self,
        text: str,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> tuple[str, list[str]]:
        """Redact PII from a text string.

        Args:
            text: The input text to scan and redact.
            agent_policy: Optional agent policy dict. If it contains a
                ``pii_redaction`` key, only the pattern categories listed
                in ``pii_redaction.enabled_patterns`` will be applied.
                If ``pii_redaction.enabled`` is False, redaction is skipped.

        Returns:
            A tuple of (redacted_text, detected_pii_types) where
            detected_pii_types is a list of category names that were found.
        """
        if not text:
            return text, []

        # Determine which patterns to apply
        active_patterns = self._resolve_active_patterns(agent_policy)
        if not active_patterns:
            return text, []

        detected_types: list[str] = []
        result = text

        for pii_type in active_patterns:
            pattern = self.PII_PATTERNS.get(pii_type)
            if pattern is None:
                continue
            replacement = self.REDACTION_TOKENS.get(pii_type, "[REDACTED]")
            new_text, count = pattern.subn(replacement, result)
            if count > 0:
                detected_types.append(pii_type)
                logger.info(
                    "PII detected: type=%s occurrences=%d",
                    pii_type,
                    count,
                )
            result = new_text

        return result, detected_types

    def redact_json(
        self,
        data: Any,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Recursively redact PII from nested JSON-like structures.

        Handles dicts, lists, and string values. Non-string leaf values
        are returned unchanged.

        Args:
            data: A JSON-compatible Python object (dict, list, str, int, etc.).
            agent_policy: Optional agent policy for pattern selection.

        Returns:
            A copy of *data* with PII-bearing strings redacted.
        """
        if isinstance(data, str):
            redacted, _ = self.redact(data, agent_policy)
            return redacted
        elif isinstance(data, dict):
            return {
                key: self.redact_json(value, agent_policy)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self.redact_json(item, agent_policy) for item in data]
        else:
            # int, float, bool, None -- no redaction needed
            return data

    def scan(
        self,
        text: str,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> dict[str, list[str]]:
        """Scan text for PII without redacting.

        Args:
            text: Input text to scan.
            agent_policy: Optional agent policy.

        Returns:
            Dict mapping PII type to list of matched values.
        """
        if not text:
            return {}

        active_patterns = self._resolve_active_patterns(agent_policy)
        findings: dict[str, list[str]] = {}

        for pii_type in active_patterns:
            pattern = self.PII_PATTERNS.get(pii_type)
            if pattern is None:
                continue
            matches = pattern.findall(text)
            if matches:
                # findall may return tuples for patterns with groups
                findings[pii_type] = [
                    m if isinstance(m, str) else m[0] for m in matches
                ]

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_active_patterns(
        self,
        agent_policy: Optional[dict[str, Any]],
    ) -> list[str]:
        """Determine which PII patterns are active for the given policy.

        If no policy is provided, all patterns are active.

        Args:
            agent_policy: Optional agent policy dict.

        Returns:
            List of active PII pattern category names.
        """
        all_patterns = list(self.PII_PATTERNS.keys())

        if agent_policy is None:
            return all_patterns

        pii_config = agent_policy.get("pii_redaction")
        if pii_config is None:
            return all_patterns

        # Global enable/disable switch
        if not pii_config.get("enabled", True):
            return []

        # Selective pattern list
        enabled_patterns = pii_config.get("enabled_patterns")
        if enabled_patterns is not None:
            return [p for p in enabled_patterns if p in self.PII_PATTERNS]

        # Exclusion list
        disabled_patterns = pii_config.get("disabled_patterns", [])
        return [p for p in all_patterns if p not in disabled_patterns]
