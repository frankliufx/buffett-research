"""Database access layer.

Architecture:
    fetch_fundamentals(...)            ← public API, signature unchanged
            │
            └─ get_or_fetch_fundamentals(...)   ← DB-first wrapper
                    │
                    ├─ 1. Redis hot cache (5min)
                    ├─ 2. PostgreSQL fresh data (24h)
                    └─ 3. fall through to original fetch_fundamentals
                              + write back raw_payload + parsed rows to DB
                              + populate Redis

Design principles enforced:
    稳定 — wrapper is opt-in via DB_FIRST_ENABLED env flag, falls back gracefully
    真实 — every fetch writes raw_payload to raw_fundamentals (immutable)
    准确 — multi-source rows preserved separately, consensus computed on read
"""
from pathlib import Path

# Defensive .env loading so this package works even when imported
# before src.config (e.g. in standalone scripts).
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)
except ImportError:
    pass

from .session import get_engine, get_session, session_scope
from .cache import get_redis

# Legacy Supabase client (used by user_data, tracker for user-state persistence).
# Kept as-is for backward compatibility; unrelated to the new Postgres/Redis layer above.
from ._supabase import get_client, is_available

__all__ = [
    "get_engine", "get_session", "session_scope", "get_redis",
    "get_client", "is_available",
]
