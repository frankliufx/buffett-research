"""Unit tests for src.ai.rate_limiter.TokenBucket."""

from __future__ import annotations

import threading
import time

import pytest

from src.ai.rate_limiter import TokenBucket, get_rate_limiter, reset_rate_limiters


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_rate_limiters()
    yield
    reset_rate_limiters()


def test_burst_capacity_allows_immediate_acquires() -> None:
    bucket = TokenBucket(rate_per_min=60, burst=5)
    for _ in range(5):
        assert bucket.acquire(max_wait=0.01) is True


def test_exhausted_bucket_blocks_until_refill() -> None:
    bucket = TokenBucket(rate_per_min=600, burst=2)  # 10 tokens/sec
    assert bucket.acquire(max_wait=0.01) is True
    assert bucket.acquire(max_wait=0.01) is True

    t0 = time.monotonic()
    assert bucket.acquire(max_wait=1.0) is True
    elapsed = time.monotonic() - t0
    # Need 0.1s to refill 1 token at 10/sec
    assert 0.05 < elapsed < 0.5


def test_max_wait_exceeded_returns_false_but_does_not_raise() -> None:
    bucket = TokenBucket(rate_per_min=6, burst=1)  # 0.1 tokens/sec
    assert bucket.acquire(max_wait=0.01) is True
    # Bucket empty; refill would take ~10s, max_wait is 0.2s
    assert bucket.acquire(max_wait=0.2) is False


def test_concurrent_acquires_respect_capacity() -> None:
    bucket = TokenBucket(rate_per_min=60, burst=3)
    successes: list[bool] = []
    lock = threading.Lock()

    def _worker() -> None:
        ok = bucket.acquire(max_wait=0.05)
        with lock:
            successes.append(ok)

    threads = [threading.Thread(target=_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 3 fit in burst window; refill is 1/sec so within 50ms at most 3 acquire
    assert sum(successes) == 3


def test_factory_reuses_bucket_for_same_key() -> None:
    a = get_rate_limiter("openai:abc12345", rate_per_min=60, burst=5)
    b = get_rate_limiter("openai:abc12345", rate_per_min=60, burst=5)
    assert a is b


def test_factory_separates_keys() -> None:
    a = get_rate_limiter("openai:abc12345", rate_per_min=60, burst=5)
    b = get_rate_limiter("anthropic:xyz78901", rate_per_min=60, burst=5)
    assert a is not b


def test_factory_rebuilds_when_params_change() -> None:
    a = get_rate_limiter("openai:abc12345", rate_per_min=60, burst=5)
    b = get_rate_limiter("openai:abc12345", rate_per_min=120, burst=5)
    assert a is not b


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError):
        TokenBucket(rate_per_min=0, burst=1)
    with pytest.raises(ValueError):
        TokenBucket(rate_per_min=60, burst=0)
