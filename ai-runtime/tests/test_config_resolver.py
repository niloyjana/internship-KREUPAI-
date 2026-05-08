"""Tests for ConfigResolver.

Verifies default config resolution, deep merge with agent and tenant
overrides, and extraction helpers for escalation, approval, LLM, and
PII configuration.
"""

import pytest

from orchestrator.config_resolver import ConfigResolver, SYSTEM_DEFAULTS


# ---------------------------------------------------------------------------
# Default resolution
# ---------------------------------------------------------------------------


class TestDefaultResolution:
    """Tests for resolving with defaults only."""

    def test_resolve_returns_defaults_when_no_overrides(self):
        """resolve() with no overrides returns system defaults."""
        resolver = ConfigResolver()

        config = resolver.resolve()

        assert config["llm"]["provider"] == "openai"
        assert config["llm"]["model"] == "gpt-4o"
        assert config["llm"]["temperature"] == 0.2
        assert config["pii_redaction"]["enabled"] is True
        assert config["escalation"]["enabled"] is True
        assert config["retry"]["profile"] == "llm_call"

    def test_resolve_returns_copy(self):
        """resolve() returns a copy, not a reference to defaults."""
        resolver = ConfigResolver()

        config = resolver.resolve()
        config["llm"]["model"] = "gpt-3.5-turbo"

        fresh = resolver.resolve()
        assert fresh["llm"]["model"] == "gpt-4o"

    def test_custom_defaults(self):
        """ConfigResolver accepts custom system defaults."""
        custom = {"llm": {"provider": "anthropic", "model": "claude-sonnet"}}
        resolver = ConfigResolver(defaults=custom)

        config = resolver.resolve()

        assert config["llm"]["provider"] == "anthropic"
        assert config["llm"]["model"] == "claude-sonnet"


# ---------------------------------------------------------------------------
# Deep merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    """Tests for deep merge with agent + tenant overrides."""

    def test_agent_policy_overrides_defaults(self):
        """Agent policy overrides default values."""
        resolver = ConfigResolver()

        config = resolver.resolve(
            agent_policy={"llm": {"temperature": 0.8}},
        )

        assert config["llm"]["temperature"] == 0.8
        # Other defaults preserved
        assert config["llm"]["provider"] == "openai"

    def test_tenant_config_overrides_agent(self):
        """Tenant config overrides agent policy values."""
        resolver = ConfigResolver()

        config = resolver.resolve(
            agent_policy={"llm": {"model": "gpt-3.5-turbo"}},
            tenant_config={"llm": {"model": "claude-sonnet-4-20250514"}},
        )

        # Tenant wins
        assert config["llm"]["model"] == "claude-sonnet-4-20250514"

    def test_nested_merge_preserves_sibling_keys(self):
        """Deep merge preserves sibling keys in nested dicts."""
        resolver = ConfigResolver()

        config = resolver.resolve(
            agent_policy={
                "approval": {
                    "thresholds": {"max_cost_usd": 5.00},
                },
            },
        )

        # Overridden key
        assert config["approval"]["thresholds"]["max_cost_usd"] == 5.00
        # Sibling keys preserved from defaults
        assert config["approval"]["auto_approve"] is False

    def test_new_keys_added(self):
        """Keys not in defaults are added to the result."""
        resolver = ConfigResolver()

        config = resolver.resolve(
            agent_policy={"custom_feature": {"enabled": True, "value": 42}},
        )

        assert config["custom_feature"]["enabled"] is True
        assert config["custom_feature"]["value"] == 42

    def test_list_override_replaces(self):
        """List values in overrides replace the base list entirely."""
        resolver = ConfigResolver()

        config = resolver.resolve(
            agent_policy={
                "escalation": {"error_types": ["CustomError", "SpecialError"]},
            },
        )

        assert config["escalation"]["error_types"] == ["CustomError", "SpecialError"]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


class TestExtractionHelpers:
    """Tests for policy extraction helper methods."""

    def test_get_escalation_rules_defaults(self):
        """get_escalation_rules returns defaults when no policy."""
        resolver = ConfigResolver()

        rules = resolver.get_escalation_rules()

        assert rules["enabled"] is True
        assert rules["max_consecutive_failures"] == 3

    def test_get_escalation_rules_with_policy(self):
        """get_escalation_rules merges policy overrides."""
        resolver = ConfigResolver()

        rules = resolver.get_escalation_rules(
            agent_policy={"escalation": {"max_consecutive_failures": 5}},
        )

        assert rules["max_consecutive_failures"] == 5
        assert rules["enabled"] is True  # preserved from defaults

    def test_get_approval_thresholds_defaults(self):
        """get_approval_thresholds returns defaults when no policy."""
        resolver = ConfigResolver()

        approval = resolver.get_approval_thresholds()

        assert approval["auto_approve"] is False
        assert approval["thresholds"]["max_cost_usd"] == 1.00

    def test_get_approval_thresholds_with_policy(self):
        """get_approval_thresholds merges policy overrides."""
        resolver = ConfigResolver()

        approval = resolver.get_approval_thresholds(
            agent_policy={"approval": {"auto_approve": True}},
        )

        assert approval["auto_approve"] is True
        assert approval["thresholds"]["max_cost_usd"] == 1.00

    def test_get_llm_config(self):
        """get_llm_config resolves LLM settings with overrides."""
        resolver = ConfigResolver()

        llm = resolver.get_llm_config(
            agent_policy={"llm": {"temperature": 0.5}},
            tenant_config={"llm": {"max_tokens": 8192}},
        )

        assert llm["temperature"] == 0.5
        assert llm["max_tokens"] == 8192
        assert llm["provider"] == "openai"

    def test_get_pii_config_defaults(self):
        """get_pii_config returns defaults when no policy."""
        resolver = ConfigResolver()

        pii = resolver.get_pii_config()

        assert pii["enabled"] is True
        assert pii["enabled_patterns"] is None

    def test_get_pii_config_with_policy(self):
        """get_pii_config merges policy overrides."""
        resolver = ConfigResolver()

        pii = resolver.get_pii_config(
            agent_policy={"pii_redaction": {"enabled_patterns": ["email", "phone_intl"]}},
        )

        assert pii["enabled_patterns"] == ["email", "phone_intl"]
        assert pii["enabled"] is True
