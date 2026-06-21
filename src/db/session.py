"""SQLAlchemy engine + session management.

Reads connection details from .env (loaded via src.config).
Provides a context manager `session_scope()` for safe transaction handling.

SQLAlchemy imports are lazy (inside functions) so this module does not crash
on import when sqlalchemy is unavailable (e.g. Streamlit Cloud without psycopg2).
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Optional

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_engine: Optional[Any] = None
_SessionLocal: Optional[Any] = None


def _build_dsn() -> str:
    return (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )


def get_engine() -> "Engine":
    """Return a process-wide singleton engine."""
    from sqlalchemy import create_engine  # lazy import
    from sqlalchemy.orm import sessionmaker

    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            _build_dsn(),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,           # detect stale connections (SSH tunnel may flap)
            pool_recycle=1800,            # recycle every 30 min
            future=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
        logger.info("DB engine initialized: %s:%s/%s",
                    os.environ.get("DB_HOST"), os.environ.get("DB_PORT"), os.environ.get("DB_NAME"))
    return _engine


def get_session() -> "Session":
    from sqlalchemy.orm import Session  # noqa: F401 — imported for type resolution

    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def session_scope() -> Iterator[Any]:
    """Context manager for transactional scope. Commits on success, rolls back on error."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_available() -> bool:
    """Quick health check — returns True if DB reachable."""
    try:
        from sqlalchemy import text
        with session_scope() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("DB unavailable: %s", e)
        return False
