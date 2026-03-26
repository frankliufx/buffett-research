"""飞轮追踪引擎 — 分析历史 · 投资笔记 · 战绩追踪

产品护城河的数据底座：
- 每次分析自动快照：评分 + 价格 + 时间戳
- 用户投资论点存档（买入理由 · 目标价 · 风险关注点）
- 历史评分 vs 实际价格表现 → 构建可验证的信用记录

数据优先级：Supabase（云端，多设备） > 本地文件（降级）
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.db import get_client

logger = logging.getLogger(__name__)
_DATA_DIR = Path(__file__).parent.parent / "data"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 内部工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _history_path(uid: str) -> Path:
    return _DATA_DIR / "tracker_{}.json".format(uid)

def _thesis_path(uid: str, symbol: str, market: str) -> Path:
    safe_sym = symbol.replace("/", "_").replace(".", "_")
    return _DATA_DIR / "thesis_{}_{}_{}".format(uid, market, safe_sym) + ".json"

def _load_local_history(uid: str) -> list:
    p = _history_path(uid)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def _save_local_history(uid: str, records: list) -> bool:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _history_path(uid).write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.warning("Local history save failed: %s", e)
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 分析历史 — 核心飞轮数据
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def save_analysis_record(
    uid: str,
    symbol: str,
    market: str,
    name: str,
    price: float,
    moat_result: dict,
    brief: Optional[dict] = None,
    fundamentals: Optional[dict] = None,
) -> bool:
    """每次分析完成后自动调用，存档评分快照。

    这是飞轮的启动点：积累足够多的记录后，
    系统可以计算"高分股票的平均实际回报"，
    形成可验证的信用资产。
    """
    scores = moat_result.get("scores", {})

    def _s(name):
        d = scores.get(name, {})
        return d.get("score", 0)

    fund = fundamentals or {}
    record = {
        "uid":              uid,
        "symbol":           symbol,
        "market":           market,
        "name":             name,
        "analyzed_at":      _now_iso(),
        "price":            round(float(price), 4) if price else None,
        "score_total":      moat_result.get("percentage", 0),
        "score_earnings":   _s("盈利质量"),
        "score_moat":       _s("护城河深度"),
        "score_fortress":   _s("财务堡垒"),
        "score_growth":     _s("成长确定性"),
        "score_opportunity": _s("市场先生机会"),
        "grade":            moat_result.get("grade", ""),
        "verdict":          brief.get("verdict", "") if brief else "",
        "confidence":       brief.get("confidence", "") if brief else "",
        "roe":              fund.get("roe"),
        "pe":               fund.get("pe_trailing"),
        "profit_margin":    fund.get("profit_margin"),
    }

    # ── Supabase ──
    db = get_client()
    if db is not None:
        try:
            db.table("analysis_history").insert(record).execute()
            return True
        except Exception as e:
            logger.warning("Supabase save_analysis_record failed: %s", e)

    # ── 本地降级 ──
    records = _load_local_history(uid)
    records.insert(0, record)
    records = records[:500]          # 最多保留500条
    return _save_local_history(uid, records)


def load_user_analysis_history(uid: str, limit: int = 100) -> list:
    """加载用户全部分析历史，按时间倒序。"""
    db = get_client()
    if db is not None:
        try:
            resp = (
                db.table("analysis_history")
                .select("*")
                .eq("uid", uid)
                .order("analyzed_at", desc=True)
                .execute()
            )
            return (resp.data or [])[:limit]
        except Exception as e:
            logger.warning("Supabase load_user_analysis_history failed: %s", e)

    records = _load_local_history(uid)
    return records[:limit]


def get_stock_analysis_history(uid: str, symbol: str, market: str, limit: int = 10) -> list:
    """获取某只股票的历史分析记录（最新在前）。"""
    all_records = load_user_analysis_history(uid, limit=500)
    matched = [
        r for r in all_records
        if r.get("symbol") == symbol and r.get("market") == market
    ]
    return matched[:limit]


def get_latest_analysis(uid: str, symbol: str, market: str) -> Optional[dict]:
    """获取某只股票最近一次分析快照，用于展示'上次分析'上下文。"""
    history = get_stock_analysis_history(uid, symbol, market, limit=1)
    return history[0] if history else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 投资论点 — 用户记忆层
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def save_stock_thesis(
    uid: str,
    symbol: str,
    market: str,
    buy_thesis: str = "",
    target_price: Optional[float] = None,
    risk_watch: str = "",
    notes: str = "",
) -> bool:
    """保存用户对某只股票的投资论点。

    这是用户记忆层的核心：买入理由 + 目标价 + 风险关注点。
    积累这些记录后，用户越来越难以离开——这是转换成本护城河。
    """
    data = {
        "uid":          uid,
        "symbol":       symbol,
        "market":       market,
        "buy_thesis":   buy_thesis.strip(),
        "target_price": round(float(target_price), 4) if target_price else None,
        "risk_watch":   risk_watch.strip(),
        "notes":        notes.strip(),
        "updated_at":   _now_iso(),
    }

    db = get_client()
    if db is not None:
        try:
            db.table("stock_thesis").upsert(
                data, on_conflict="uid,symbol,market"
            ).execute()
            return True
        except Exception as e:
            logger.warning("Supabase save_stock_thesis failed: %s", e)

    # 本地降级
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _thesis_path(uid, symbol, market).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.warning("Local thesis save failed: %s", e)
        return False


def load_stock_thesis(uid: str, symbol: str, market: str) -> Optional[dict]:
    """加载用户对某只股票的投资论点。"""
    db = get_client()
    if db is not None:
        try:
            resp = (
                db.table("stock_thesis")
                .select("*")
                .eq("uid", uid)
                .eq("symbol", symbol)
                .eq("market", market)
                .execute()
            )
            rows = resp.data or []
            return rows[0] if rows else None
        except Exception as e:
            logger.warning("Supabase load_stock_thesis failed: %s", e)

    p = _thesis_path(uid, symbol, market)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 战绩统计 — 可信度引擎
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_track_record(records: list, current_prices: dict) -> dict:
    """
    基于历史分析记录 + 当前价格，计算战绩统计。

    current_prices: {"{market}:{symbol}": current_price}

    Returns dict:
      total_analyzed   — 总分析次数
      unique_stocks    — 覆盖股票数
      high_score_avg   — 高分(≥80)股票平均回报%
      mid_score_avg    — 中分(60-79)股票平均回报%
      beat_market_pct  — 回报>0的比例
      records_with_return — 每条记录加上 return_pct 字段
    """
    enriched = []
    for r in records:
        key = "{}:{}".format(r.get("market", ""), r.get("symbol", ""))
        cur = current_prices.get(key)
        entry_price = r.get("price")
        ret = None
        if cur and entry_price and entry_price > 0:
            ret = round((cur - entry_price) / entry_price * 100, 2)
        enriched.append({**r, "return_pct": ret, "current_price": cur})

    with_return = [e for e in enriched if e["return_pct"] is not None]

    def avg_return(subset):
        rets = [e["return_pct"] for e in subset if e["return_pct"] is not None]
        return round(sum(rets) / len(rets), 2) if rets else None

    high = [e for e in with_return if e.get("score_total", 0) >= 80]
    mid  = [e for e in with_return if 60 <= e.get("score_total", 0) < 80]
    low  = [e for e in with_return if e.get("score_total", 0) < 60]

    beat = [e for e in with_return if e["return_pct"] > 0]

    syms = set("{}:{}".format(r.get("market"), r.get("symbol")) for r in records)

    return {
        "total_analyzed":     len(records),
        "unique_stocks":      len(syms),
        "high_score_avg":     avg_return(high),
        "mid_score_avg":      avg_return(mid),
        "low_score_avg":      avg_return(low),
        "beat_market_pct":    round(len(beat) / len(with_return) * 100, 1) if with_return else None,
        "records_with_return": enriched,
        "high_count":         len(high),
        "mid_count":          len(mid),
        "low_count":          len(low),
    }


def build_history_context(prev: Optional[dict], current_price: float) -> str:
    """
    为 AI prompt 生成历史对比上下文段落。
    告诉 AI：上次分析时的评分和价格，现在发生了什么变化。
    """
    if not prev:
        return ""

    days_ago = 0
    try:
        analyzed_dt = datetime.fromisoformat(prev["analyzed_at"].replace("Z", "+00:00"))
        days_ago = (datetime.now(timezone.utc) - analyzed_dt).days
    except Exception:
        pass

    prev_price  = prev.get("price") or 0
    prev_score  = prev.get("score_total", 0)
    prev_roe    = prev.get("roe")
    prev_verdict = prev.get("verdict", "")

    price_chg = ""
    if prev_price and current_price:
        pct = (current_price - prev_price) / prev_price * 100
        price_chg = "价格从 {:.2f} 变为 {:.2f}（{:+.1f}%）".format(
            prev_price, current_price, pct
        )

    roe_note = ""
    if prev_roe:
        roe_note = "，当时 ROE {:.1f}%".format(prev_roe)

    lines = [
        "## 历史分析对比",
        "本用户 {} 天前已分析过此股票".format(days_ago) if days_ago else "用户曾分析过此股票",
        "上次总评分：{}/100，AI 结论：{}{}".format(prev_score, prev_verdict, roe_note),
    ]
    if price_chg:
        lines.append(price_chg)
    lines.append("请在分析中指出与上次相比的关键变化，评分是否应调整及原因。")

    return "\n".join(lines)
