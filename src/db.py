"""Supabase REST API 客户端 — 纯 requests 实现，零外部依赖

不使用 supabase Python SDK（在 Python 3.14 等新版本上不兼容）。
直接通过 PostgREST HTTP API 操作数据库。
若未配置 SUPABASE_URL / SUPABASE_KEY，所有操作静默降级到文件系统。
"""

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

_url = ""
_key = ""
_initialized = False
_REQUEST_TIMEOUT = 10


def _init():
    global _url, _key, _initialized
    if _initialized:
        return
    _initialized = True

    _url = os.environ.get("SUPABASE_URL", "")
    _key = os.environ.get("SUPABASE_KEY", "")

    if not _url or not _key:
        try:
            import streamlit as st
            secrets = dict(st.secrets) if hasattr(st, "secrets") else {}
            _url = _url or secrets.get("SUPABASE_URL", "")
            _key = _key or secrets.get("SUPABASE_KEY", "")
        except Exception:
            pass

    _url = _url.strip().rstrip("/")
    _key = _key.strip()

    if _url and _key:
        logger.info("Supabase REST configured: %s", _url[:40])
    else:
        logger.info("Supabase not configured, using file-based fallback")


def is_available():
    _init()
    return bool(_url and _key)


def _headers():
    return {
        "apikey": _key,
        "Authorization": "Bearer {}".format(_key),
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def get_client():
    """兼容旧接口 — 返回一个轻量包装对象或 None"""
    _init()
    if not _url or not _key:
        return None
    return _SupabaseRest(_url, _key)


class _SupabaseRest:
    """极简 Supabase REST wrapper，兼容 user_data.py 的调用模式"""

    def __init__(self, url, key):
        self._url = url
        self._key = key

    def table(self, name):
        return _TableQuery(self._url, self._key, name)


class _TableQuery:
    """链式查询构建器 — 模拟 supabase-py 的 .select().eq().execute() 模式"""

    def __init__(self, url, key, table):
        self._url = url
        self._key = key
        self._table = table
        self._method = "GET"
        self._params = {}
        self._body = None
        self._filters = []
        self._order_col = None
        self._order_desc = False
        self._select_cols = "*"

    def _headers(self):
        h = {
            "apikey": self._key,
            "Authorization": "Bearer {}".format(self._key),
            "Content-Type": "application/json",
        }
        if self._method in ("POST", "PATCH"):
            h["Prefer"] = "return=representation"
        if self._method == "DELETE":
            h["Prefer"] = "return=minimal"
        return h

    def select(self, columns="*"):
        self._method = "GET"
        self._select_cols = columns
        self._params["select"] = columns
        return self

    def insert(self, data):
        self._method = "POST"
        self._body = data
        return self

    def upsert(self, data, on_conflict=""):
        self._method = "POST"
        self._body = data
        self._params["on_conflict"] = on_conflict
        return self

    def delete(self):
        self._method = "DELETE"
        return self

    def eq(self, column, value):
        self._filters.append("{}=eq.{}".format(column, value))
        return self

    def order(self, column, desc=False):
        self._order_col = column
        self._order_desc = desc
        return self

    def execute(self):
        endpoint = "{}/rest/v1/{}".format(self._url, self._table)
        headers = self._headers()

        # Build query string
        params = dict(self._params)
        for f in self._filters:
            col, val = f.split("=", 1)
            params[col] = val
        if self._order_col:
            params["order"] = "{}.{}".format(
                self._order_col, "desc" if self._order_desc else "asc")

        try:
            if self._method == "GET":
                resp = requests.get(endpoint, headers=headers, params=params,
                                     timeout=_REQUEST_TIMEOUT)
            elif self._method == "POST":
                resp = requests.post(endpoint, headers=headers, params=params,
                                      json=self._body, timeout=_REQUEST_TIMEOUT)
            elif self._method == "PATCH":
                resp = requests.patch(endpoint, headers=headers, params=params,
                                       json=self._body, timeout=_REQUEST_TIMEOUT)
            elif self._method == "DELETE":
                resp = requests.delete(endpoint, headers=headers, params=params,
                                        timeout=_REQUEST_TIMEOUT)
            else:
                return _Result([])

            if resp.status_code in (200, 201):
                try:
                    return _Result(resp.json())
                except Exception:
                    return _Result([])
            elif resp.status_code == 204:
                return _Result([])
            else:
                logger.warning("Supabase REST %s %s: %d %s",
                             self._method, self._table, resp.status_code,
                             resp.text[:200])
                return _Result([])
        except Exception as e:
            logger.warning("Supabase REST error: %s", e)
            return _Result([])


class _Result:
    """模拟 supabase-py 的 execute() 返回值"""
    def __init__(self, data):
        self.data = data if isinstance(data, list) else [data] if data else []
