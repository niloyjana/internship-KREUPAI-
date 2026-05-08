"""Error Classifier -- categorises errors into P6-spec failure categories A–F.

Classification is used by the FailureHandler to determine retry eligibility,
escalation requirements, and backoff parameters.
"""

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """Failure categories per P6 spec Section 1."""

    TRANSIENT = "TRANSIENT"  # A — network timeout, connection reset, DNS failure
    RATE_LIMIT = "RATE_LIMIT"  # B — API throttle, quota exceeded
    BUSINESS_RULE = "BUSINESS_RULE"  # C — validation failure, policy violation
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"  # D — service unavailable, auth expired
    AI_FAILURE = "AI_FAILURE"  # E — hallucination, token limit, model unavailable
    INFRASTRUCTURE = "INFRASTRUCTURE"  # F — DB pool, Kafka broker, Redis, disk


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

_CLASSIFICATION_RULES: list[dict[str, Any]] = [
    # Category A — Transient
    {
        "category": ErrorCategory.TRANSIENT,
        "patterns": [
            "connectionerror",
            "timeout",
            "econnreset",
            "etimedout",
            "econnrefused",
            "enotfound",
            "enetunreach",
            "socket hang up",
            "network timeout",
            "connection reset",
            "dns failure",
            "aborterror",
            "apiconnectionerror",
            "apitimeouterror",
        ],
        "retry_eligible": True,
        "max_retries": 3,
        "base_delay_s": 2.0,
        "escalation_required": False,
    },
    # Category B — Rate Limit
    {
        "category": ErrorCategory.RATE_LIMIT,
        "patterns": [
            "rate limit",
            "ratelimiterror",
            "too many requests",
            "throttl",
            "quota exceeded",
            "429",
        ],
        "retry_eligible": True,
        "max_retries": 3,
        "base_delay_s": 5.0,
        "escalation_required": False,
    },
    # Category C — Business Rule
    {
        "category": ErrorCategory.BUSINESS_RULE,
        "patterns": [
            "validation",
            "policy violation",
            "data conflict",
            "business rule",
            "constraint violation",
            "duplicate entry",
            "bad request",
            "policyviolationerror",
            "budgetexceedederror",
        ],
        "retry_eligible": False,
        "max_retries": 0,
        "base_delay_s": 0,
        "escalation_required": False,
    },
    # Category D — External System
    {
        "category": ErrorCategory.EXTERNAL_SYSTEM,
        "patterns": [
            "service unavailable",
            "serviceunavailableerror",
            "bad gateway",
            "gateway timeout",
            "auth expired",
            "token expired",
            "unauthorized",
            "forbidden",
            "circuitbreakeropenerror",
            "httperror",
            "internalservererror",
        ],
        "retry_eligible": True,
        "max_retries": 3,
        "base_delay_s": 2.0,
        "escalation_required": False,
    },
    # Category E — AI Failure
    {
        "category": ErrorCategory.AI_FAILURE,
        "patterns": [
            "hallucination",
            "token limit",
            "context length",
            "context_length_exceeded",
            "model unavailable",
            "model_not_found",
            "safety filter",
            "content filter",
            "content_policy",
            "max_tokens",
        ],
        "retry_eligible": True,
        "max_retries": 2,
        "base_delay_s": 5.0,
        "escalation_required": False,
    },
    # Category F — Infrastructure
    {
        "category": ErrorCategory.INFRASTRUCTURE,
        "patterns": [
            "connection pool",
            "pool exhausted",
            "kafka broker",
            "redis connection",
            "disk space",
            "operationalerror",
            "interfaceerror",
            "brokernotavailable",
        ],
        "retry_eligible": True,
        "max_retries": 3,
        "base_delay_s": 0.5,
        "escalation_required": True,
    },
]

# Default when no rule matches
_DEFAULT_CLASSIFICATION: dict[str, Any] = {
    "category": ErrorCategory.TRANSIENT,
    "retry_eligible": False,
    "max_retries": 0,
    "base_delay_s": 0,
    "escalation_required": True,
}


def classify_error(error: Exception) -> dict[str, Any]:
    """Classify an error into one of the 6 P6-spec failure categories.

    Returns a dict with:
      - category (ErrorCategory)
      - retry_eligible (bool)
      - max_retries (int)
      - base_delay_s (float)
      - escalation_required (bool)
    """
    error_type = type(error).__name__.lower()
    error_message = str(error).lower()
    search_text = f"{error_type} {error_message}"

    for rule in _CLASSIFICATION_RULES:
        matched = any(pattern in search_text for pattern in rule["patterns"])
        if matched:
            return {
                "category": rule["category"],
                "retry_eligible": rule["retry_eligible"],
                "max_retries": rule["max_retries"],
                "base_delay_s": rule["base_delay_s"],
                "escalation_required": rule["escalation_required"],
            }

    return dict(_DEFAULT_CLASSIFICATION)
