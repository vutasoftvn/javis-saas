import asyncio
from datetime import datetime, timezone
from enum import Enum
import logging
import random
from typing import Any, Callable, Dict, Optional, TypeVar
from pydantic import BaseModel

from cosa_core.reliability.model_profiles import ModelProfile

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, fast-fail without calling connector
    HALF_OPEN = "HALF_OPEN"# Trial request to test if connector has recovered


class CircuitBreaker:
    """Circuit breaker for protecting downstream external connectors and LLM providers from cascading failures."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.last_state_change: datetime = datetime.now(timezone.utc)

    def can_execute(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.state == CircuitState.OPEN:
            elapsed = (now - self.last_state_change).total_seconds()
            if elapsed >= self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                logger.info(f"[CircuitBreaker:{self.name}] Transitioned to HALF_OPEN trial state.")
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info(f"[CircuitBreaker:{self.name}] Service recovered. Transitioned to CLOSED.")
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_state_change = datetime.now(timezone.utc)

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        now = datetime.now(timezone.utc)
        if self.state == CircuitState.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = now
            logger.warning(f"[CircuitBreaker:{self.name}] Threshold exceeded ({self.consecutive_failures} fails). Transitioned to OPEN.")


class RetryPolicy:
    """Configurable exponential backoff retry runner for transient network and rate limit errors."""

    DEFAULT_DELAYS = [0.1, 0.2, 0.5, 1.0] # test/fast default; prod uses 2s, 5s, 15s, 30s

    @staticmethod
    def is_transient_error(exc: Exception) -> bool:
        """Determines whether an exception is transient (safe to retry) or permanent (abort immediately)."""
        msg = str(exc).lower()
        transient_indicators = (
            "429", "rate limit", "too many requests",
            "502", "503", "504", "bad gateway", "service unavailable", "gateway timeout",
            "timeout", "timed out", "connection reset", "connection refused", "econnreset",
        )
        # Business/Validation/Policy/Auth errors are NEVER transient
        if any(perm in msg for perm in ("401", "403", "unauthorized", "forbidden", "permission", "policy violation", "not found")):
            return False
        return any(ind in msg for ind in transient_indicators) or isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError))

    @classmethod
    async def execute_with_backoff(
        cls,
        fn: Callable[..., Any],
        delays: Optional[list[float]] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        schedule = delays or cls.DEFAULT_DELAYS
        last_exc = None

        for attempt, delay in enumerate(schedule, start=1):
            if circuit_breaker and not circuit_breaker.can_execute():
                raise ConnectionError(f"Circuit breaker '{circuit_breaker.name}' is OPEN. Fast-failing request.")

            try:
                result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
                if circuit_breaker:
                    circuit_breaker.record_success()
                return result
            except Exception as exc:
                last_exc = exc
                if circuit_breaker:
                    circuit_breaker.record_failure()

                if not cls.is_transient_error(exc) or attempt >= len(schedule):
                    logger.warning(f"[RetryPolicy] Non-transient error or max retries exceeded ({attempt}/{len(schedule)}): {exc}")
                    raise exc

                # Exponential backoff with small jitter
                jitter = random.uniform(0.01, 0.05)
                wait_time = delay + jitter
                logger.info(f"[RetryPolicy] Transient error on attempt {attempt}/{len(schedule)}: {exc}. Retrying in {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

        if last_exc:
            raise last_exc


class CostTracker:
    """Calculates token costs per run and enforces domain budget ceilings."""

    @staticmethod
    def calculate_cost(
        profile: ModelProfile,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        input_cost = (input_tokens / 1000.0) * profile.cost_per_1k_input
        output_cost = (output_tokens / 1000.0) * profile.cost_per_1k_output
        return round(input_cost + output_cost, 6)
