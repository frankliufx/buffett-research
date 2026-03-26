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


# ══════════════════════════════════════════════════════════════════════════════
# PLAN & USAGE（免费/付费 + 用量追踪）
# ══════════════════════════════════════════════════════════════════════════════

FREE_MONTHLY_LIMIT = 3  # 免费用户每月分析次数


def get_user_plan(uid: str) -> str:
    """返回 'free' 或 'premium'"""
    settings = load_user_settings(uid)
    return settings.get("plan", "free")


def get_monthly_usage(uid: str) -> int:
    """返回当月已使用的分析次数"""
    from datetime import datetime
    settings = load_user_settings(uid)
    usage = settings.get("monthly_usage", {})
    month_key = datetime.now().strftime("%Y-%m")
    return usage.get(month_key, 0)


def increment_usage(uid: str) -> int:
    """增加一次使用计数，返回当月累计"""
    from datetime import datetime
    settings = load_user_settings(uid)
    usage = settings.get("monthly_usage", {})
    month_key = datetime.now().strftime("%Y-%m")
    count = usage.get(month_key, 0) + 1
    usage[month_key] = count
    # 清理旧月份（只保留最近 3 个月）
    all_months = sorted(usage.keys())
    if len(all_months) > 3:
        for old_key in all_months[:-3]:
            usage.pop(old_key, None)
    settings["monthly_usage"] = usage
    save_user_settings(uid, settings)
    return count


def can_analyze(uid: str, role: str = "viewer") -> tuple:
    """检查用户是否可以执行分析

    Returns: (allowed: bool, remaining: int, plan: str)
    """
    if role == "admin":
        return True, 999, "admin"
    plan = get_user_plan(uid)
    if plan == "premium":
        return True, 999, "premium"
    used = get_monthly_usage(uid)
    remaining = max(0, FREE_MONTHLY_LIMIT - used)
    return remaining > 0, remaining, "free"


def set_user_plan(uid: str, plan: str) -> bool:
    """设置用户计划（admin 用）"""
    settings = load_user_settings(uid)
    settings["plan"] = plan
    return save_user_settings(uid, settings)


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO（持仓追踪）
# ══════════════════════════════════════════════════════════════════════════════

def _portfolio_fallback_path(uid: str) -> Path:
    return _DATA_DIR / "portfolio_{}.json".format(uid)


def load_portfolio(uid: str) -> List[dict]:
    """加载用户持仓"""
    db = get_client()
    if db is not None:
        try:
            resp = db.table("user_portfolio").select("*") \
                .eq("uid", uid).order("created_at", desc=True).execute()
            return resp.data or []
        except Exception as e:
            logger.warning("Supabase load_portfolio failed for %s: %s", uid, e)

    path = _portfolio_fallback_path(uid)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def add_position(uid: str, position: dict) -> bool:
    """新增一条持仓记录"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_portfolio").insert({
                "uid": uid,
                "symbol": position["symbol"],
                "name": position.get("name", position["symbol"]),
                "market": position.get("market", "us"),
                "shares": position.get("shares", 0),
                "cost_price": position.get("cost_price", 0),
                "buy_date": position.get("buy_date", ""),
                "note": position.get("note", ""),
            }).execute()
            return True
        except Exception as e:
            logger.warning("Supabase add_position failed: %s", e)

    # 本地降级
    positions = load_portfolio(uid)
    positions.insert(0, position)
    return _save_portfolio_local(uid, positions)


def delete_position(uid: str, position_id: str) -> bool:
    """删除一条持仓"""
    db = get_client()
    if db is not None:
        try:
            db.table("user_portfolio").delete().eq("uid", uid).eq("id", position_id).execute()
            return True
        except Exception as e:
            logger.warning("Supabase delete_position failed: %s", e)

    positions = load_portfolio(uid)
    positions = [p for p in positions if p.get("id") != position_id]
    return _save_portfolio_local(uid, positions)


def _save_portfolio_local(uid: str, positions: List[dict]) -> bool:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _portfolio_fallback_path(uid).write_text(
            json.dumps(positions, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.warning("Local portfolio save failed: %s", e)
        return False


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


# ══════════════════════════════════════════════════════════════════════════════
# PRICE ALERTS（目标价提醒）
# ══════════════════════════════════════════════════════════════════════════════

def _alerts_fallback_path(uid: str) -> Path:
    return _DATA_DIR / "alerts_{}.json".format(uid)


def load_price_alerts(uid: str) -> List[dict]:
    """加载用户全部价格提醒（包括已触发的）"""
    db = get_client()
    if db is not None:
        try:
            resp = db.table("price_alerts").select("*") \
                .eq("uid", uid).order("created_at", desc=True).execute()
            return resp.data or []
        except Exception as e:
            logger.warning("Supabase load_price_alerts failed: %s", e)

    path = _alerts_fallback_path(uid)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def add_price_alert(
    uid: str, symbol: str, market: str, name: str,
    alert_type: str, target_price: float,
) -> bool:
    """新增价格提醒。alert_type: 'below'（跌到）或 'above'（涨到）"""
    from datetime import datetime, timezone
    record = {
        "uid": uid, "symbol": symbol, "market": market,
        "name": name or symbol,
        "alert_type": alert_type,
        "target_price": round(float(target_price), 4),
        "triggered": False,
        "triggered_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db = get_client()
    if db is not None:
        try:
            db.table("price_alerts").insert(record).execute()
            return True
        except Exception as e:
            logger.warning("Supabase add_price_alert failed: %s", e)

    alerts = load_price_alerts(uid)
    alerts.insert(0, record)
    return _save_alerts_local(uid, alerts)


def delete_price_alert(uid: str, alert_id) -> bool:
    """删除一条提醒（按 id）"""
    db = get_client()
    if db is not None:
        try:
            db.table("price_alerts").delete().eq("uid", uid).eq("id", str(alert_id)).execute()
            return True
        except Exception as e:
            logger.warning("Supabase delete_price_alert failed: %s", e)

    alerts = load_price_alerts(uid)
    alerts = [a for a in alerts if str(a.get("id", "")) != str(alert_id)]
    return _save_alerts_local(uid, alerts)


def check_price_alerts(uid: str, current_prices: dict) -> List[dict]:
    """检查哪些提醒被触发，返回触发列表并标记 triggered=True。

    current_prices: {'{market}:{symbol}': price}
    """
    from datetime import datetime, timezone
    alerts = load_price_alerts(uid)
    triggered = []
    updated = False

    for alert in alerts:
        if alert.get("triggered"):
            continue
        key = "{}:{}".format(alert["market"], alert["symbol"])
        cur = current_prices.get(key)
        if cur is None:
            continue
        tp = alert.get("target_price", 0)
        hit = (alert["alert_type"] == "below" and cur <= tp) or \
              (alert["alert_type"] == "above" and cur >= tp)
        if hit:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
            triggered.append(alert)
            updated = True

    if updated:
        # Try to persist updated state
        db = get_client()
        if db is not None:
            for a in triggered:
                try:
                    if "id" in a:
                        db.table("price_alerts").upsert(
                            {"id": a["id"], "triggered": True,
                             "triggered_at": a["triggered_at"]},
                            on_conflict="id",
                        ).execute()
                except Exception:
                    pass
        else:
            _save_alerts_local(uid, alerts)

    return triggered


def _save_alerts_local(uid: str, alerts: List[dict]) -> bool:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _alerts_fallback_path(uid).write_text(
            json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.warning("Local alerts save failed: %s", e)
        return False
