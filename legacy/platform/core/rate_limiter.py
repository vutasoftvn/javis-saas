import time
from collections import defaultdict
from threading import Lock
from typing import Tuple, Dict


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter for public unauthenticated endpoints."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int = None, window_seconds: int = None) -> Tuple[bool, int]:
        """
        Check if request under `key` is allowed.
        Returns: (is_allowed, remaining_requests_in_window)
        """
        limit = max_requests if max_requests is not None else self.max_requests
        window = window_seconds if window_seconds is not None else self.window_seconds
        now = time.time()
        cutoff = now - window

        with self._lock:
            timestamps = self._requests[key]
            # Prune expired timestamps
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            self._requests[key] = valid_timestamps

            if len(valid_timestamps) >= limit:
                return False, 0

            valid_timestamps.append(now)
            remaining = limit - len(valid_timestamps)
            return True, remaining

    def reset(self):
        """Reset rate limiter state (useful for tests)."""
        with self._lock:
            self._requests.clear()


# Default global instance for public form submissions & event ingestion
public_rate_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=60)
