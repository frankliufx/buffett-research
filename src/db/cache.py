"""Redis hot cache for high-frequency reads (5 min TTL by default)."""
from __future__ import annotations

import logging
import os
from typing import Optional

try:
    import redis
except ImportError as _e:
    raise ImportError("redis package is required for the cache layer.") from _e

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    global _client
    if _client is not None:
        return _client

    host = os.environ.get("REDIS_HOST", "")
    if not host:
        return None

    _client = redis.Redis(
        host=host,
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        _client.ping()
        logger.info("Redis connected: %s:%s", host, os.environ.get("REDIS_PORT", "6379"))
    except Exception as e:
        logger.warning("Redis unreachable: %s", e)
        _client = None
    return _client


def cache_available() -> bool:
    try:
        client = get_redis()
        if client is None:
            return False
        client.ping()
        return True
    except Exception:
        return False
