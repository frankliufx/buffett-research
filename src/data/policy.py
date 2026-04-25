"""A股政策数据引擎

功能：
1. 用 AKShare 获取东财政策相关概念板块成员（约20个关键概念，非全量）
2. 缓存到 data/cache/policy_concept_map.json（24h TTL）
3. get_stock_policy_tags(symbol) → 该股票所属政策概念列表
4. get_policy_news(limit=5) → 人民网 RSS 最新政策新闻
5. get_fifteen_five_alignment(symbol) → 十五五规划对齐分析
"""

import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

# ── 关键词分级 ──────────────────────────────────────────────────────────────
_TIER1_KEYWORDS = [
    "人工智能", "机器人", "新能源汽车", "光伏", "储能",
    "半导体", "创新药", "芯片", "大模型", "量子",
]

_TIER2_KEYWORDS = [
    "低空经济", "数据要素", "碳中和", "工业母机", "新质生产力",
    "卫星互联网", "氢能", "固态电池", "核能", "数字经济",
]

_ALL_POLICY_KEYWORDS = _TIER1_KEYWORDS + _TIER2_KEYWORDS

# ── 缓存配置 ────────────────────────────────────────────────────────────────
_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_CACHE_FILE = _CACHE_DIR / "policy_concept_map.json"
_CACHE_TTL = 24 * 3600  # 24h

# 人民网政治新闻 RSS
_PEOPLE_RSS_URL = "http://www.people.com.cn/rss/politics.xml"


# ── 缓存工具 ────────────────────────────────────────────────────────────────

def _cache_valid() -> bool:
    """检查缓存文件是否存在且未过期"""
    if not _CACHE_FILE.exists():
        return False
    age = time.time() - _CACHE_FILE.stat().st_mtime
    return age < _CACHE_TTL


def _load_cache() -> dict:
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── 概念板块数据获取 ─────────────────────────────────────────────────────────

def _fetch_policy_concept_map() -> dict:
    """
    从 AKShare 获取政策相关概念板块，构建反向映射。
    返回 {股票6位代码: [概念名称列表]}
    """
    try:
        import akshare as ak
        all_concepts_df = ak.stock_board_concept_name_em()
    except Exception:
        return {}

    # 过滤出政策相关概念
    try:
        name_col = "板块名称" if "板块名称" in all_concepts_df.columns else all_concepts_df.columns[0]
        concept_names = all_concepts_df[name_col].tolist()
    except Exception:
        return {}

    policy_concepts = []
    for name in concept_names:
        for kw in _ALL_POLICY_KEYWORDS:
            if kw in name:
                policy_concepts.append(name)
                break

    # 构建反向映射：股票代码 → 概念列表
    stock_to_concepts: dict = {}
    for concept_name in policy_concepts:
        try:
            import akshare as ak
            members_df = ak.stock_board_concept_cons_em(symbol=concept_name)
            # "代码" 列是6位股票代码
            code_col = "代码" if "代码" in members_df.columns else members_df.columns[0]
            codes = members_df[code_col].astype(str).tolist()
            for code in codes:
                code = code.zfill(6)
                stock_to_concepts.setdefault(code, [])
                if concept_name not in stock_to_concepts[code]:
                    stock_to_concepts[code].append(concept_name)
        except Exception:
            continue

    return stock_to_concepts


def _get_concept_map() -> dict:
    """获取概念映射（优先读缓存）"""
    if _cache_valid():
        data = _load_cache()
        if data:
            return data

    data = _fetch_policy_concept_map()
    if data:
        _save_cache(data)
    return data


# ── 公开接口 ─────────────────────────────────────────────────────────────────

def get_stock_policy_tags(symbol: str) -> list:
    """
    返回该股票所属的政策概念列表。

    参数:
        symbol: 格式如 "sh600519" 或 "sz000001"，提取6位代码
    返回:
        list[str] — 政策概念名称列表，无匹配时返回空列表
    """
    code = symbol.replace("sh", "").replace("sz", "").replace(".", "").strip()
    code = code[-6:] if len(code) >= 6 else code.zfill(6)

    # Fixture short-circuit (USE_FIXTURES=1)
    from src.data.fixtures import is_fixture_mode, get_a_share_stock
    if is_fixture_mode():
        fx = get_a_share_stock(code)
        if fx:
            return list(fx.get("concept_tags") or [])

    concept_map = _get_concept_map()
    return concept_map.get(code, [])


def get_policy_news(limit: int = 5) -> list:
    """
    从人民网 RSS 获取最新政策新闻。

    返回:
        list[dict] — 每项含 title, link, pubDate, source
    """
    results = []
    try:
        resp = requests.get(_PEOPLE_RSS_URL, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (compatible; StockAnalyst/1.0)"
        })
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return results

        items = channel.findall("item")
        for item in items[:limit]:
            title_el = item.find("title")
            link_el = item.find("link")
            date_el = item.find("pubDate")
            results.append({
                "title": title_el.text.strip() if title_el is not None and title_el.text else "",
                "link": link_el.text.strip() if link_el is not None and link_el.text else "",
                "pubDate": date_el.text.strip() if date_el is not None and date_el.text else "",
                "source": "人民网",
            })
    except Exception:
        pass
    return results


def get_policy_alignment(symbol: str):
    """Return a typed `PolicyAlignment` (schemas/policy.py) for the given stock.

    Companion to the legacy `get_fifteen_five_alignment` (which returns a dict).
    Sources the same concept-board data but scores against the curated YAML
    knowledge base in `data/cn_policy_themes.yaml` instead of hardcoded keywords.

    Fixture mode: when USE_FIXTURES=1 and the symbol is in the curated fixture
    file, sources the concept list from there instead of akshare.
    """
    from src.data.policy_themes import score_alignment
    code = symbol.replace("sh", "").replace("sz", "").replace(".", "").strip()
    code = code[-6:] if len(code) >= 6 else code.zfill(6)

    from src.data.fixtures import is_fixture_mode, get_a_share_stock
    if is_fixture_mode():
        fx = get_a_share_stock(code)
        if fx:
            return score_alignment(symbol, list(fx.get("concept_tags") or []))

    concepts = _get_concept_map().get(code, [])
    return score_alignment(symbol, concepts)


def get_fifteen_five_alignment(symbol: str) -> dict:
    """
    返回与十五五规划的对齐分析。

    参数:
        symbol: 格式如 "sh600519"
    返回:
        {
            "level": "核心主线" | "受益方向" | "暂无明显政策主题",
            "score": int,        # 0-15
            "color": str,        # hex color
            "tier1": list,       # 一级主线概念列表
            "tier2": list,       # 二级受益概念列表
            "all_tags": list,    # 全部概念标签
        }
    """
    all_tags = get_stock_policy_tags(symbol)

    tier1 = []
    tier2 = []
    for tag in all_tags:
        matched_t1 = any(kw in tag for kw in _TIER1_KEYWORDS)
        matched_t2 = any(kw in tag for kw in _TIER2_KEYWORDS)
        if matched_t1:
            tier1.append(tag)
        elif matched_t2:
            tier2.append(tag)

    # 评分：一级3分/个（上限12），二级1分/个（上限3），总计0-15
    score = min(len(tier1) * 3, 12) + min(len(tier2), 3)
    score = min(score, 15)

    if score >= 9:
        level = "核心主线"
        color = "#C9A962"
    elif score >= 3:
        level = "受益方向"
        color = "#5B8DB8"
    else:
        level = "暂无明显政策主题"
        color = "#5A5A6A"

    return {
        "level": level,
        "score": score,
        "color": color,
        "tier1": tier1,
        "tier2": tier2,
        "all_tags": all_tags,
    }
