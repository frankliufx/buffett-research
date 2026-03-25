"""用户数据访问层 — 关注列表 / 投资日志 / 个人设置

优先级：Supabase（多用户隔离）> 本地文件（单机降级）

所有函数都接受 uid: str 参数，uid = username（来自 auth.py）
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from src.db import get_client

logger = logging.getLogger(__name__)

# 本地降级路径
_DATA_DIR = Path(__file__).parent.parent / "data"


# ══════════════════════════════════════════════════════════════════════════════
# WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════

def _watchlist_fallback_path(uid: str) -> Path:
    return _DATA_DIR / "watchlist_{}.json".format(uid)


def load_watchlist(uid: str) -> dict:
    """加载用户关注列表，返回 {'us': [...], 'hk': [...], 'a_share': [...]}

    每项格式: {'symbol': 'AAPL', 'name': 'Apple'}
    """
    db = get_client()
    if db is not None:
        try:
            resp = db.table("user_watchlists").select("market,symbol,name") \
                .eq("uid", uid).execute()
            rows = resp.data or []
            result = {"us": [], "hk": [], "a_share": []}
            for row in rows:
                m = row.get("market", "us")
                if m in result:
                    result[m].append({
                        "symbol": row["symbol"],
                        "name": row.get("name", row["symbol"]),
                    })
            return result
        except Exception as e:
            logger.warning("Supabase load_watchlist failed for %s: %s", uid, e)

    # 本地降级
    path = _watchlist_fallback_path(uid)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"us": [], "hk": [], "a_share": []}


def add_to_watchlist(uid: str, market: str, symbol: str, name: str = "") -> bool:
    """添加股票到用户关注列表"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_watchlists").upsert({
                "uid": uid, "market": market,
                "symbol": symbol, "name": name or symbol,
            }, on_conflict="uid,market,symbol").execute()
            return True
        except Exception as e:
            logger.warning("Supabase add_to_watchlist failed: %s", e)

    # 本地降级
    wl = load_watchlist(uid)
    market_list = wl.setdefault(market, [])
    if not any(s["symbol"] == symbol for s in market_list):
        market_list.append({"symbol": symbol, "name": name or symbol})
        _save_watchlist_local(uid, wl)
    return True


def remove_from_watchlist(uid: str, market: str, symbol: str) -> bool:
    """从用户关注列表移除股票"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_watchlists").delete() \
                .eq("uid", uid).eq("market", market).eq("symbol", symbol).execute()
            return True
        except Exception as e:
            logger.warning("Supabase remove_from_watchlist failed: %s", e)

    # 本地降级
    wl = load_watchlist(uid)
    if market in wl:
        wl[market] = [s for s in wl[market] if s["symbol"] != symbol]
        _save_watchlist_local(uid, wl)
    return True


def save_watchlist(uid: str, watchlist: dict) -> bool:
    """整体保存关注列表（用于批量操作）"""
    db = get_client()
    if db is not None:
        try:
            # 先删除该用户所有记录，再批量插入
            db.table("user_watchlists").delete().eq("uid", uid).execute()
            rows = []
            for market, items in watchlist.items():
                for item in items:
                    rows.append({
                        "uid": uid, "market": market,
                        "symbol": item["symbol"],
                        "name": item.get("name", item["symbol"]),
                    })
            if rows:
                db.table("user_watchlists").insert(rows).execute()
            return True
        except Exception as e:
            logger.warning("Supabase save_watchlist failed: %s", e)

    return _save_watchlist_local(uid, watchlist)


def _save_watchlist_local(uid: str, watchlist: dict) -> bool:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _watchlist_fallback_path(uid).write_text(
            json.dumps(watchlist, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.warning("Local watchlist save failed: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# JOURNAL
# ══════════════════════════════════════════════════════════════════════════════

def _journal_fallback_path(uid: str) -> Path:
    return _DATA_DIR / "journal_{}.json".format(uid)


def load_journal(uid: str) -> List[dict]:
    """加载用户投资日志"""
    db = get_client()
    if db is not None:
        try:
            resp = db.table("user_journals").select("*") \
                .eq("uid", uid).order("created_at", desc=True).execute()
            rows = resp.data or []
            # 统一格式，与旧文件格式兼容
            entries = []
            for row in rows:
                entries.append({
                    "id": row.get("id", ""),
                    "type": row.get("entry_type", "note"),
                    "title": row.get("title", ""),
                    "content": row.get("content", ""),
                    "symbol": row.get("symbol", ""),
                    "date": str(row.get("created_at", ""))[:10],
                })
            return entries
        except Exception as e:
            logger.warning("Supabase load_journal failed for %s: %s", uid, e)

    # 本地降级
    path = _journal_fallback_path(uid)
    # 兼容旧版全局 journal.json（uid=anonymous 时读旧文件）
    if not path.exists():
        old_path = _DATA_DIR / "journal.json"
        if old_path.exists():
            path = old_path
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def save_journal_entry(uid: str, entry: dict) -> bool:
    """新增一条日志"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_journals").insert({
                "uid": uid,
                "entry_type": entry.get("type", "note"),
                "title": entry.get("title", ""),
                "content": entry.get("content", ""),
                "symbol": entry.get("symbol", ""),
            }).execute()
            return True
        except Exception as e:
            logger.warning("Supabase save_journal_entry failed: %s", e)

    # 本地降级：追加到 list
    entries = load_journal(uid)
    entries.insert(0, entry)
    return _save_journal_local(uid, entries)


def delete_journal_entry(uid: str, entry_id: str) -> bool:
    """删除一条日志（by id）"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_journals").delete().eq("uid", uid).eq("id", entry_id).execute()
            return True
        except Exception as e:
            logger.warning("Supabase delete_journal_entry failed: %s", e)

    # 本地降级
    entries = load_journal(uid)
    entries = [e for e in entries if e.get("id") != entry_id]
    return _save_journal_local(uid, entries)


def save_all_journal(uid: str, entries: List[dict]) -> bool:
    """整体替换日志（用于 import）"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_journals").delete().eq("uid", uid).execute()
            rows = [{
                "uid": uid,
                "entry_type": e.get("type", "note"),
                "title": e.get("title", ""),
                "content": e.get("content", ""),
                "symbol": e.get("symbol", ""),
            } for e in entries]
            if rows:
                db.table("user_journals").insert(rows).execute()
            return True
        except Exception as e:
            logger.warning("Supabase save_all_journal failed: %s", e)

    return _save_journal_local(uid, entries)


def _save_journal_local(uid: str, entries: List[dict]) -> bool:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _journal_fallback_path(uid).write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.warning("Local journal save failed: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# USER SETTINGS（API provider 选择、策略参数等）
# ══════════════════════════════════════════════════════════════════════════════

def load_user_settings(uid: str) -> dict:
    """加载用户个性化设置"""
    db = get_client()
    if db is not None:
        try:
            resp = db.table("user_settings").select("settings_json") \
                .eq("uid", uid).execute()
            rows = resp.data or []
            if rows:
                raw = rows[0].get("settings_json", {})
                return raw if isinstance(raw, dict) else json.loads(raw)
        except Exception as e:
            logger.warning("Supabase load_user_settings failed for %s: %s", uid, e)

    # 本地降级：读 user-specific settings 文件
    path = _DATA_DIR / "settings_{}.json".format(uid)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_user_settings(uid: str, settings: dict) -> bool:
    """保存用户个性化设置"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_settings").upsert({
                "uid": uid,
                "settings_json": settings,
            }, on_conflict="uid").execute()
            return True
        except Exception as e:
            logger.warning("Supabase save_user_settings failed: %s", e)

    # 本地降级
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = _DATA_DIR / "settings_{}.json".format(uid)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.warning("Local settings save failed: %s", e)
        return False
