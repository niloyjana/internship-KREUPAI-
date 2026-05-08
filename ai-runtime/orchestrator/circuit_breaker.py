"""Circuit Breaker pattern for AI Runtime.

Provides per-provider circuit breakers that prevent cascading failures
by tracking consecutive errors and temporarily blocking calls to
failing providers.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_timeout_s: float = 30.0
    half_open_max_attempts: int = 2


# Per-provider configs matching P6 spec Section 3
PROVIDER_CONFIGS: dict[str, CircuitBreakerConfig] = {
    "OPENAI": CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=45.0, half_open_max_attempts=2),
    "ANTHROPIC": CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=45.0, half_open_max_attempts=2),
    "AZURE_OPENAI": CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=45.0, half_open_max_attempts=2),
}

DEFAULT_CONFIG = CircuitBreakerConfig()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN and rejecting calls."""
    pass


class CircuitBreaker:
    """Circuit breaker with CLOSED -> OPEN -> HALF_OPEN state machine."""

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self._config = config or DEFAULT_CONFIG
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0
        self._last_failure_time: float | None = None

    @classmethod
    def for_provider(cls, provider: str) -> "CircuitBreaker":
        config = PROVIDER_CONFIGS.get(provider, DEFAULT_CONFIG)
        return cls(config)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute fn through the circuit breaker."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._half_open_attempts = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Retry after {self._config.reset_timeout_s}s."
                )

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_attempts >= self._config.half_open_max_attempts:
                self._state = CircuitState.OPEN
                self._last_failure_time = time.monotonic()
                raise CircuitBreakerOpenError(
                    f"Circuit breaker moved to OPEN after exhausting "
                    f"{self._config.half_open_max_attempts} half-open attempt(s)."
                )
            self._half_open_attempts += 1

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0
        self._last_failure_time = None

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return False
        return (time.monotonic() - self._last_failure_time) >= self._config.reset_timeout_s

    def _on_success(self) -> None:
        self._failure_count = 0
        self._half_open_attempts = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if (
            self._failure_count >= self._config.failure_threshold
            or self._state == CircuitState.HALF_OPEN
        ):
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures", self._failure_count
            )
