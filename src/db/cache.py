"""Redis hot cache for high-frequency reads (5 min TTL by default)."""
from __future__ import annotations

import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.environ["REDIS_HOST"],
            port=int(os.environ["REDIS_PORT"]),
            password=os.environ["REDIS_PASSWORD"],
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            _client.ping()
            logger.info("Redis connected: %s:%s",
                        os.environ.get("REDIS_HOST"), os.environ.get("REDIS_PORT"))
        except Exception as e:
            logger.warning("Redis unreachable: %s", e)
    return _client


def cache_available() -> bool:
    try:
        get_redis().ping()
        return True
    except Exception:
        return False
