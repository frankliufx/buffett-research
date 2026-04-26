"""Browser-only API key management.

Architecture (per user's stated principle):

  user's hand → browser localStorage → server session_state (transient, in-memory)
                                       → outbound request to OpenRouter / Anthropic / etc.

  Server's filesystem (config.yaml, .env, logs)  ←  NEVER

The flow:
  1. On every Streamlit script run, `hydrate_keys_from_browser()` is called
     once. It uses streamlit-local-storage to fetch keys from the user's
     browser (if previously saved) and merges them into st.session_state.config.
  2. `save_keys_to_browser()` is called by the Settings UI when the user
     clicks "Save in browser" — it pushes the keys back to localStorage.
  3. `clear_keys()` wipes both session_state and localStorage.
  4. `save_config()` continues to strip api_key before yaml write (already
     in src.config.save_config).

Crucially: session_state lives in server RAM only for the lifetime of
the Streamlit session. When the user closes the tab, server-side memory
is reclaimed; the only persistent copy is in their browser.

Public API:
    hydrate_keys_from_browser(config)   → idempotent, called once per script run
    save_keys_to_browser(config)        → called from the Settings "Save" button
    clear_keys(config)                  → called from the Settings "Clear" button
    is_persisted_in_browser(provider_id)→ for UI status badge
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

# Browser localStorage key prefix. We namespace per-provider so 'anthropic',
# 'openai_compatible / openrouter', 'deepseek' etc. each get their own slot.
_LS_PREFIX = "ai_buffett_provider_key__"
_LS_BASE_URL_PREFIX = "ai_buffett_provider_base_url__"


def _ls_handle():
    """Return a streamlit-local-storage handle, or None if unavailable."""
    try:
        from streamlit_local_storage import LocalStorage
        # Reuse a single handle across reruns to avoid re-mounting the iframe.
        if "_ls_handle" not in st.session_state:
            st.session_state["_ls_handle"] = LocalStorage()
        return st.session_state["_ls_handle"]
    except Exception as e:
        logger.warning("streamlit-local-storage unavailable: %s", e)
        return None


def _provider_storage_id(provider) -> str:
    """Stable id for a provider's localStorage slot.

    Combines provider type + name so a user's "MyOpenRouter" and another
    "MyDeepSeek" don't collide. Falls back gracefully on bare provider type.
    """
    name = (getattr(provider, "name", "") or "").strip().lower().replace(" ", "_")
    ptype = (getattr(provider, "provider", "") or "").strip().lower()
    return f"{ptype}__{name}" if name else ptype


def hydrate_keys_from_browser(config) -> int:
    """Read each provider's api_key + base_url from localStorage and merge into config.

    Called once per Streamlit script run, BEFORE any LLM request.
    Returns count of providers hydrated (for debugging / status display).

    Idempotent: subsequent calls within the same run do nothing extra.
    """
    if st.session_state.get("_keys_hydrated_this_run"):
        return st.session_state.get("_keys_hydrated_count", 0)

    ls = _ls_handle()
    if ls is None:
        st.session_state["_keys_hydrated_this_run"] = True
        st.session_state["_keys_hydrated_count"] = 0
        return 0

    hydrated = 0
    for p in getattr(config.api, "providers", []):
        # Only hydrate if no key is present yet (env / secrets take precedence)
        if p.api_key:
            continue
        slot = _provider_storage_id(p)
        try:
            stored_key = ls.getItem(_LS_PREFIX + slot)
        except Exception:
            stored_key = None
        if stored_key:
            p.api_key = stored_key
            hydrated += 1

        # Base URL (optional — only meaningful for openai_compatible providers)
        try:
            stored_url = ls.getItem(_LS_BASE_URL_PREFIX + slot)
        except Exception:
            stored_url = None
        if stored_url and not p.base_url:
            p.base_url = stored_url

    st.session_state["_keys_hydrated_this_run"] = True
    st.session_state["_keys_hydrated_count"] = hydrated
    return hydrated


def save_keys_to_browser(config) -> int:
    """Write each provider's current api_key + base_url to localStorage.

    Called by the Settings "Save in browser" button. Returns the number
    of slots written.

    Crucially, this NEVER writes to disk — the keys stay in the user's
    browser. The server's config.yaml has these fields blanked out by
    src.config.save_config().
    """
    ls = _ls_handle()
    if ls is None:
        return 0

    written = 0
    for p in getattr(config.api, "providers", []):
        slot = _provider_storage_id(p)
        if p.api_key:
            try:
                ls.setItem(_LS_PREFIX + slot, p.api_key, key=f"set_key_{slot}")
                written += 1
            except Exception as e:
                logger.warning("localStorage set failed for %s: %s", slot, e)
        if p.base_url:
            try:
                ls.setItem(_LS_BASE_URL_PREFIX + slot, p.base_url, key=f"set_url_{slot}")
            except Exception:
                pass
    return written


def clear_keys(config) -> None:
    """Wipe API keys from session_state AND from the user's browser localStorage."""
    ls = _ls_handle()
    for p in getattr(config.api, "providers", []):
        p.api_key = ""
        slot = _provider_storage_id(p)
        if ls is not None:
            try:
                ls.deleteItem(_LS_PREFIX + slot, key=f"del_key_{slot}")
                ls.deleteItem(_LS_BASE_URL_PREFIX + slot, key=f"del_url_{slot}")
            except Exception:
                pass


def is_persisted_in_browser(provider) -> bool:
    """True if this provider's key is stored in the user's localStorage."""
    ls = _ls_handle()
    if ls is None:
        return False
    slot = _provider_storage_id(provider)
    try:
        return bool(ls.getItem(_LS_PREFIX + slot))
    except Exception:
        return False


def mask(key: Optional[str]) -> str:
    """Display-safe masking for an API key (for logs / status panels)."""
    if not key:
        return ""
    s = str(key)
    if len(s) <= 8:
        return "·" * len(s)
    return f"{s[:4]}…{s[-4:]}"
