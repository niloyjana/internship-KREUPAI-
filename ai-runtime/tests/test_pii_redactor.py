"""Tests for PIIRedactor.

Verifies detection and redaction of all 8 PII pattern types (email, phone,
credit card, passport, IBAN, SSN, GCC national ID, IP address),
policy-based pattern filtering, and scan-only mode.

@see P5_Security_Secrets_Spec.md Section 5
"""

import pytest

from orchestrator.pii_redactor import PIIRedactor


# ---------------------------------------------------------------------------
# Individual pattern tests
# ---------------------------------------------------------------------------


class TestPatternRedaction:
    """Tests for redacting specific PII pattern categories."""

    def test_email_redaction(self):
        """Emails are replaced with [EMAIL_REDACTED]."""
        r = PIIRedactor()
        text = "Contact john.doe@example.com for support"
        redacted, types = r.redact(text)

        assert "[EMAIL_REDACTED]" in redacted
        assert "john.doe@example.com" not in redacted
        assert "email" in types

    def test_phone_redaction(self):
        """International phone numbers are replaced with [PHONE_REDACTED]."""
        r = PIIRedactor()
        text = "Call us at +14155551234 or +442071234567"
        redacted, types = r.redact(text)

        assert "[PHONE_REDACTED]" in redacted
        assert "+14155551234" not in redacted
        assert "phone_intl" in types

    def test_ssn_redaction(self):
        """US SSNs are replaced with [SSN_REDACTED]."""
        r = PIIRedactor()
        text = "SSN: 123-45-6789"
        redacted, types = r.redact(text)

        assert "[SSN_REDACTED]" in redacted
        assert "123-45-6789" not in redacted
        assert "ssn_us" in types

    def test_credit_card_redaction(self):
        """Credit card numbers are replaced with [CARD_REDACTED]."""
        r = PIIRedactor()
        text = "Card: 4111 1111 1111 1111"
        redacted, types = r.redact(text)

        assert "[CARD_REDACTED]" in redacted
        assert "4111 1111 1111 1111" not in redacted
        assert "credit_card" in types

    def test_ip_address_redaction(self):
        """IP addresses are replaced with [IP_REDACTED]."""
        r = PIIRedactor()
        text = "Connecting from 192.168.1.100"
        redacted, types = r.redact(text)

        assert "[IP_REDACTED]" in redacted
        assert "192.168.1.100" not in redacted
        assert "ip_address" in types

    def test_passport_redaction(self):
        """Passport numbers are replaced with [PASSPORT_REDACTED]."""
        r = PIIRedactor()
        text = "Passport number: AB1234567"
        redacted, types = r.redact(text)

        assert "[PASSPORT_REDACTED]" in redacted
        assert "AB1234567" not in redacted
        assert "passport" in types

    def test_national_id_gcc_redaction(self):
        """GCC national IDs (9-12 digits) are replaced with [ID_REDACTED]."""
        r = PIIRedactor()
        text = "National ID: 123456789012"
        redacted, types = r.redact(text)

        assert "[ID_REDACTED]" in redacted
        assert "123456789012" not in redacted
        assert "national_id_gcc" in types

    def test_iban_redaction(self):
        """IBAN numbers are replaced with [IBAN_REDACTED]."""
        r = PIIRedactor()
        text = "IBAN: GB29NWBK60161331926819"
        redacted, types = r.redact(text)

        assert "[IBAN_REDACTED]" in redacted
        assert "GB29NWBK60161331926819" not in redacted
        assert "iban" in types

    def test_multiple_pii_types(self):
        """Multiple PII types are redacted in a single text."""
        r = PIIRedactor()
        text = "Email: test@example.com, IP: 10.0.0.1"
        redacted, types = r.redact(text)

        assert "[EMAIL_REDACTED]" in redacted
        assert "[IP_REDACTED]" in redacted
        assert "email" in types
        assert "ip_address" in types

    def test_no_pii_returns_unchanged(self):
        """Text without PII is returned unchanged."""
        r = PIIRedactor()
        text = "Hello, how can I help you today?"
        redacted, types = r.redact(text)

        assert redacted == text
        assert types == []

    def test_empty_text(self):
        """Empty text returns empty with no detected types."""
        r = PIIRedactor()
        redacted, types = r.redact("")
        assert redacted == ""
        assert types == []

    def test_all_8_patterns_count(self):
        """Verify all 8 P5-spec PII patterns are registered."""
        r = PIIRedactor()
        expected = {
            "email", "phone_intl", "credit_card", "passport",
            "iban", "ssn_us", "national_id_gcc", "ip_address",
        }
        assert set(r.PII_PATTERNS.keys()) == expected
        assert set(r.REDACTION_TOKENS.keys()) == expected


# ---------------------------------------------------------------------------
# Policy-based redaction
# ---------------------------------------------------------------------------


class TestPolicyBasedRedaction:
    """Tests for policy-controlled PII redaction."""

    def test_disabled_redaction_returns_original(self):
        """When pii_redaction.enabled is False, text is unchanged."""
        r = PIIRedactor()
        policy = {"pii_redaction": {"enabled": False}}
        text = "Email: user@test.com"

        redacted, types = r.redact(text, agent_policy=policy)

        assert redacted == text
        assert types == []

    def test_enabled_patterns_filter(self):
        """Only enabled patterns are applied when enabled_patterns is set."""
        r = PIIRedactor()
        policy = {
            "pii_redaction": {
                "enabled": True,
                "enabled_patterns": ["email"],
            },
        }
        text = "Email: user@test.com, IP: 192.168.1.1"

        redacted, types = r.redact(text, agent_policy=policy)

        assert "[EMAIL_REDACTED]" in redacted
        # IP should NOT be redacted since it's not in enabled_patterns
        assert "192.168.1.1" in redacted
        assert "email" in types
        assert "ip_address" not in types

    def test_disabled_patterns_exclusion(self):
        """Patterns in disabled_patterns are skipped."""
        r = PIIRedactor()
        policy = {
            "pii_redaction": {
                "enabled": True,
                "disabled_patterns": ["ip_address"],
            },
        }
        text = "Email: user@test.com, IP: 192.168.1.1"

        redacted, types = r.redact(text, agent_policy=policy)

        assert "[EMAIL_REDACTED]" in redacted
        assert "192.168.1.1" in redacted  # IP not redacted
        assert "ip_address" not in types

    def test_no_policy_redacts_all(self):
        """Without a policy, all PII patterns are active."""
        r = PIIRedactor()
        text = "user@test.com from 10.0.0.1"

        redacted, types = r.redact(text, agent_policy=None)

        assert "[EMAIL_REDACTED]" in redacted
        assert "[IP_REDACTED]" in redacted


# ---------------------------------------------------------------------------
# JSON redaction
# ---------------------------------------------------------------------------


class TestRedactJson:
    """Tests for recursive JSON/dict redaction."""

    def test_redact_nested_dict(self):
        """PII in nested dicts is recursively redacted."""
        r = PIIRedactor()
        data = {
            "customer": {
                "email": "john@example.com",
                "message": "Hello",
            },
            "count": 42,
        }

        redacted = r.redact_json(data)

        assert redacted["customer"]["email"] == "[EMAIL_REDACTED]"
        assert redacted["customer"]["message"] == "Hello"
        assert redacted["count"] == 42

    def test_redact_list_values(self):
        """PII in list items is redacted."""
        r = PIIRedactor()
        data = ["john@test.com", "no-pii-here", 123]

        redacted = r.redact_json(data)

        assert redacted[0] == "[EMAIL_REDACTED]"
        assert redacted[1] == "no-pii-here"
        assert redacted[2] == 123


# ---------------------------------------------------------------------------
# Scan mode
# ---------------------------------------------------------------------------


class TestScan:
    """Tests for PIIRedactor.scan (detection without redaction)."""

    def test_scan_finds_pii(self):
        """scan returns detected PII types and matched values."""
        r = PIIRedactor()
        findings = r.scan("Contact user@test.com or 192.168.1.1")

        assert "email" in findings
        assert "ip_address" in findings
        assert "user@test.com" in findings["email"]

    def test_scan_empty_text(self):
        """scan returns empty dict for empty text."""
        r = PIIRedactor()
        assert r.scan("") == {}

    def test_scan_no_pii(self):
        """scan returns empty dict when no PII is present."""
        r = PIIRedactor()
        assert r.scan("Just a normal message") == {}

    def test_scan_respects_policy(self):
        """scan respects policy-based pattern filtering."""
        r = PIIRedactor()
        policy = {"pii_redaction": {"enabled_patterns": ["email"]}}

        findings = r.scan("user@test.com 192.168.1.1", agent_policy=policy)

        assert "email" in findings
        assert "ip_address" not in findings
