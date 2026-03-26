"""Supabase 客户端单例 — 带降级支持

若未配置 SUPABASE_URL / SUPABASE_KEY，所有操作静默降级到文件系统。
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_initialized = False


def _get_supabase_credentials():
    """从环境变量或 Streamlit secrets 读取 Supabase 凭证"""
    url, key = "", ""
    # 优先从环境变量读取
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        try:
            import streamlit as st
            secrets = dict(st.secrets) if hasattr(st, "secrets") else {}
            url = url or secrets.get("SUPABASE_URL", "")
            key = key or secrets.get("SUPABASE_KEY", "")
        except Exception:
            pass

    return url.strip(), key.strip()


def get_client():
    """返回 Supabase 客户端，未配置时返回 None"""
    global _client, _initialized
    if _initialized:
        return _client

    _initialized = True
    url, key = _get_supabase_credentials()
    if not url or not key:
        logger.info("Supabase not configured, using file-based fallback")
        _client = None
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialized: %s", url[:40])
    except ImportError:
        logger.warning("supabase package not installed, falling back to file system")
        _client = None
    except Exception as e:
        logger.error("Supabase init failed: %s", e)
        _client = None

    return _client


def is_available() -> bool:
    return get_client() is not None
