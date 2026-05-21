"""Thread-safe token-bucket rate limiter for LLM calls.

Used by hedge-fund (13 masters) and committee (5 masters) parallel voting to
respect upstream RPM caps (OpenRouter free tier ≈ 60/min, DeepSeek ≈ 60/min,
Anthropic varies). Without this, a single click can burst 13 requests and hit
HTTP 429 mid-vote.

Design:
- One TokenBucket per (provider_type, api_key_prefix) — keys differ per provider
- Bucket cached at module scope (thread-safe via _buckets_lock)
- `acquire(max_wait)` blocks up to max_wait seconds; returns True on success
- If max_wait exceeded the call still proceeds (we prefer late delivery over
  silently swallowing a master's vote); upstream 429 will be reported normally
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Final

logger = logging.getLogger(__name__)


class TokenBucket:
    """Classic token bucket: capacity tokens, refilled at rate/sec."""

    def __init__(self, rate_per_min: int, burst: int) -> None:
        if rate_per_min <= 0 or burst <= 0:
            raise ValueError("rate_per_min and burst must be positive")
        self.capacity: Final[int] = burst
        self.refill_rate: Final[float] = rate_per_min / 60.0  # tokens/sec
        self.tokens: float = float(burst)
        self.last_refill: float = time.monotonic()
        self.lock = threading.Lock()

    def _refill_locked(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(float(self.capacity), self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

    def acquire(self, tokens: int = 1, max_wait: float = 30.0) -> bool:
        """Block until `tokens` are available or `max_wait` elapses.

        Returns True if acquired within max_wait, False otherwise (caller may
        still proceed — see module docstring).
        """
        deadline = time.monotonic() + max_wait
        while True:
            with self.lock:
                self._refill_locked()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                shortfall = tokens - self.tokens
                wait = shortfall / self.refill_rate

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "rate-limit wait exceeded max_wait=%ss; proceeding anyway", max_wait
                )
                return False
            time.sleep(min(wait, remaining, 0.5))


_buckets: dict[str, TokenBucket] = {}
_buckets_lock = threading.Lock()


def get_rate_limiter(key: str, rate_per_min: int, burst: int) -> TokenBucket:
    """Return a per-key bucket. Re-creates if rate or burst changed."""
    with _buckets_lock:
        bucket = _buckets.get(key)
        if (
            bucket is None
            or bucket.capacity != burst
            or abs(bucket.refill_rate * 60 - rate_per_min) > 1e-6
        ):
            bucket = TokenBucket(rate_per_min=rate_per_min, burst=burst)
            _buckets[key] = bucket
        return bucket


def reset_rate_limiters() -> None:
    """Clear all buckets — for tests only."""
    with _buckets_lock:
        _buckets.clear()
