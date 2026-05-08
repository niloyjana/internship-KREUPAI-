"""Config Resolver -- loads and merges tenant + agent policy configuration.

Resolves the final runtime configuration by deep-merging:
  1. Platform defaults  (AgentDefinition.defaultPolicyJson)
  2. Tenant overrides   (AgentConfig.policyJson)
  3. Department overrides (policyJson.departmentOverrides[dept])

Also provides helpers for extracting escalation rules and approval
thresholds from the merged configuration.

@see P4_Tenant_Configuration_Model.md
"""

import copy
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System defaults (internal — used when no platform default is set)
# ---------------------------------------------------------------------------

SYSTEM_DEFAULTS: dict[str, Any] = {
    "llm": {
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "pii_redaction": {
        "enabled": True,
        "enabled_patterns": None,  # None = all patterns active
        "disabled_patterns": [],
    },
    "escalation": {
        "enabled": True,
        "error_types": [],
        "keywords": [],
        "auto_escalate_on_budget_exceeded": True,
        "max_consecutive_failures": 3,
    },
    "approval": {
        "auto_approve": False,
        "thresholds": {
            "max_cost_usd": 1.00,
            "max_tokens": 100_000,
            "max_actions": 10,
        },
    },
    "retry": {
        "profile": "llm_call",
    },
    "memory": {
        "working_memory_ttl_seconds": 3600,
        "max_episodes": 100,
    },
}

# Redis TTL for cached configs (seconds) — P4 spec: 5 minutes
_CACHE_TTL_SECONDS = 300


class ConfigResolver:
    """Resolves agent configuration for execution context.

    Performs a deep merge of platform defaults, tenant overrides, and
    department overrides to produce the final runtime configuration
    used during agent execution.

    Supports two modes:
      1. resolve(tenant_id, agent_id, department_context)
         — P4-spec mode: loads configs from DB, caches in Redis, merges
      2. resolve_from_dicts(tenant_config, agent_policy, defaults)
         — Legacy/test mode: merges pre-loaded dicts directly
    """

    def __init__(
        self,
        defaults: Optional[dict[str, Any]] = None,
        db=None,
        redis=None,
        agent_registry=None,
    ):
        """Initialize with optional dependencies.

        Args:
            defaults: Custom system defaults. Uses SYSTEM_DEFAULTS if None.
            db: Database client for loading AgentConfig. If None, only
                resolve_from_dicts() is available.
            redis: Redis client for caching. If None, caching is skipped.
            agent_registry: Service for loading AgentDefinition defaults.
        """
        self._defaults = defaults or copy.deepcopy(SYSTEM_DEFAULTS)
        self._db = db
        self._redis = redis
        self._agent_registry = agent_registry

    # ------------------------------------------------------------------
    # P4-spec resolver (with DB + Redis)
    # ------------------------------------------------------------------

    def resolve(
        self,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        department_context: Optional[str] = None,
        # Legacy overload — if these are provided, use dict-based resolution
        tenant_config: Optional[dict[str, Any]] = None,
        agent_policy: Optional[dict[str, Any]] = None,
        defaults: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Resolve effective agent config.

        P4-spec mode (tenant_id + agent_id provided):
          1. Load platform default from agent registry
          2. Load tenant config from DB (cached in Redis for 5 min)
          3. Extract department override if department_context is set
          4. Deep merge: platform → tenant → department

        Legacy mode (dict args provided):
          Deep-merge defaults → agent_policy → tenant_config

        Returns:
            Deep-merged configuration dict.
        """
        # --- P4-spec path: load from DB + cache ---
        if tenant_id and agent_id:
            return self._resolve_from_db(
                tenant_id, agent_id, department_context
            )

        # --- Legacy / test path: merge pre-loaded dicts ---
        return self._resolve_from_dicts(
            tenant_config=tenant_config,
            agent_policy=agent_policy,
            defaults=defaults,
        )

    def _resolve_from_db(
        self,
        tenant_id: str,
        agent_id: str,
        department_context: Optional[str] = None,
    ) -> dict[str, Any]:
        """P4-spec resolution: DB → Redis cache → deep merge."""

        # 1. Load platform default
        platform_default = copy.deepcopy(self._defaults)
        if self._agent_registry:
            try:
                agent_default = self._agent_registry.get_default_policy(
                    agent_id
                )
                if agent_default:
                    platform_default = self._deep_merge(
                        platform_default, agent_default
                    )
            except Exception:
                logger.warning(
                    "Failed to load default policy for agent %s", agent_id
                )

        # 2. Load tenant override from DB (cached in Redis for 5 min)
        cache_key = f"config:{tenant_id}:{agent_id}"
        tenant_config = self._get_cached(cache_key)
        if tenant_config is None:
            tenant_config = self._load_tenant_config(tenant_id, agent_id)
            self._set_cached(cache_key, tenant_config)

        # 3. Extract department override
        dept_config: dict[str, Any] = {}
        if department_context and isinstance(tenant_config, dict):
            dept_overrides = tenant_config.get("departmentOverrides")
            if isinstance(dept_overrides, dict):
                dept_config = dept_overrides.get(department_context, {})

        # 4. Deep merge: platform → tenant (excluding departmentOverrides) → dept
        tenant_policy = {}
        if isinstance(tenant_config, dict):
            tenant_policy = {
                k: v
                for k, v in tenant_config.items()
                if k != "departmentOverrides"
            }

        effective = copy.deepcopy(platform_default)
        if tenant_policy:
            effective = self._deep_merge(effective, tenant_policy)
        if dept_config:
            effective = self._deep_merge(effective, dept_config)

        logger.debug("Resolved config for %s/%s: %s", tenant_id, agent_id, effective)
        return effective

    def _resolve_from_dicts(
        self,
        tenant_config: Optional[dict[str, Any]] = None,
        agent_policy: Optional[dict[str, Any]] = None,
        defaults: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Legacy dict-based resolution."""
        base = copy.deepcopy(defaults or self._defaults)

        if agent_policy:
            base = self._deep_merge(base, agent_policy)

        if tenant_config:
            base = self._deep_merge(base, tenant_config)

        logger.debug("Resolved config: %s", base)
        return base

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cached(self, key: str) -> Optional[dict[str, Any]]:
        if not self._redis:
            return None
        try:
            raw = self._redis.get(key)
            if raw:
                return json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        except Exception:
            logger.warning("Redis cache read failed for %s", key)
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        if not self._redis:
            return
        try:
            raw = json.dumps(value) if not isinstance(value, (str, bytes)) else value
            self._redis.setex(key, _CACHE_TTL_SECONDS, raw)
        except Exception:
            logger.warning("Redis cache write failed for %s", key)

    def _load_tenant_config(
        self, tenant_id: str, agent_id: str
    ) -> dict[str, Any]:
        """Load tenant's policyJson from DB."""
        if not self._db:
            return {}
        try:
            config = self._db.get_agent_config(tenant_id, agent_id)
            if isinstance(config, dict):
                return config.get("policyJson", config)
            return {}
        except Exception:
            logger.warning(
                "Failed to load tenant config for %s/%s", tenant_id, agent_id
            )
            return {}

    def invalidate_cache(self, tenant_id: str, agent_id: str) -> None:
        """Invalidate cached config. Called on tenant.config.updated Kafka event."""
        if not self._redis:
            return
        cache_key = f"config:{tenant_id}:{agent_id}"
        try:
            self._redis.delete(cache_key)
            logger.info("Cache invalidated for %s", cache_key)
        except Exception:
            logger.warning("Cache invalidation failed for %s", cache_key)

    # ------------------------------------------------------------------
    # Policy extraction helpers
    # ------------------------------------------------------------------

    def get_escalation_rules(
        self,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Extract escalation rules from an agent policy."""
        defaults = copy.deepcopy(self._defaults.get("escalation", {}))

        if agent_policy is None:
            return defaults

        policy_escalation = agent_policy.get("escalation")
        if policy_escalation is None:
            return defaults

        return self._deep_merge(defaults, policy_escalation)

    def get_approval_thresholds(
        self,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Extract auto-approve thresholds from an agent policy."""
        defaults = copy.deepcopy(self._defaults.get("approval", {}))

        if agent_policy is None:
            return defaults

        policy_approval = agent_policy.get("approval")
        if policy_approval is None:
            return defaults

        return self._deep_merge(defaults, policy_approval)

    def get_llm_config(
        self,
        agent_policy: Optional[dict[str, Any]] = None,
        tenant_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Extract LLM configuration from the resolved config."""
        resolved = self._resolve_from_dicts(
            tenant_config=tenant_config,
            agent_policy=agent_policy,
        )
        return resolved.get("llm", copy.deepcopy(self._defaults.get("llm", {})))

    def get_pii_config(
        self,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Extract PII redaction configuration from agent policy."""
        defaults = copy.deepcopy(self._defaults.get("pii_redaction", {}))

        if agent_policy is None:
            return defaults

        policy_pii = agent_policy.get("pii_redaction")
        if policy_pii is None:
            return defaults

        return self._deep_merge(defaults, policy_pii)

    # ------------------------------------------------------------------
    # Deep merge utility
    # ------------------------------------------------------------------

    @staticmethod
    def _deep_merge(
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Recursively deep-merge *override* into *base*.

        - Dict values are merged recursively.
        - List values in override replace the base list entirely.
        - Scalar values in override replace base values.
        - Keys in override that don't exist in base are added.
        """
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                ConfigResolver._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)
        return base
