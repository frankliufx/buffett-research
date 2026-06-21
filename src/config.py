"""配置加载与验证"""

import os
from pathlib import Path
from typing import Optional, List
import yaml
from pydantic import BaseModel

# 从项目根目录的 .env 文件加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass


class StockItem(BaseModel):
    symbol: str
    name: str


def _default_us():
    return [
        StockItem(symbol="BRK-B",  name="Berkshire Hathaway"),
        StockItem(symbol="AAPL",   name="Apple"),
        StockItem(symbol="KO",     name="Coca-Cola"),
        StockItem(symbol="BAC",    name="Bank of America"),
        StockItem(symbol="OXY",    name="Occidental Petroleum"),
        StockItem(symbol="CVX",    name="Chevron"),
        StockItem(symbol="AXP",    name="American Express"),
        StockItem(symbol="MCO",    name="Moody's"),
        StockItem(symbol="V",      name="Visa"),
        StockItem(symbol="MSFT",   name="Microsoft"),
        StockItem(symbol="GOOGL",  name="Alphabet"),
        StockItem(symbol="JNJ",    name="Johnson & Johnson"),
        StockItem(symbol="JPM",    name="JPMorgan Chase"),
    ]


def _default_hk():
    return [
        StockItem(symbol="0700.HK", name="Tencent Holdings"),
        StockItem(symbol="0005.HK", name="HSBC Holdings"),
        StockItem(symbol="1299.HK", name="AIA Group"),
        StockItem(symbol="0941.HK", name="China Mobile"),
        StockItem(symbol="1211.HK", name="BYD Company"),
        StockItem(symbol="9988.HK", name="Alibaba Group"),
        StockItem(symbol="0388.HK", name="HK Exchanges"),
        StockItem(symbol="2318.HK", name="Ping An Insurance"),
        StockItem(symbol="0883.HK", name="CNOOC"),
    ]


def _default_a():
    return [
        StockItem(symbol="sh600519", name="贵州茅台"),
        StockItem(symbol="sh601318", name="中国平安"),
        StockItem(symbol="sz000858", name="五粮液"),
        StockItem(symbol="sh600036", name="招商银行"),
        StockItem(symbol="sh601888", name="中国中免"),
        StockItem(symbol="sh600900", name="长江电力"),
        StockItem(symbol="sz002594", name="比亚迪"),
        StockItem(symbol="sh688599", name="天合光能"),
        StockItem(symbol="sh601166", name="兴业银行"),
        StockItem(symbol="sz000568", name="泸州老窖"),
        StockItem(symbol="sh600030", name="中信证券"),
        StockItem(symbol="sh601012", name="隆基绿能"),
        StockItem(symbol="sz300124", name="汇川技术"),
        StockItem(symbol="sh688256", name="寒武纪"),
        StockItem(symbol="sh688981", name="中芯国际"),
    ]


class Watchlist(BaseModel):
    us: List[StockItem] = []
    hk: List[StockItem] = []
    a_share: List[StockItem] = []


class ApiProvider(BaseModel):
    name: str = ""           # 显示名称
    provider: str = "anthropic"  # anthropic / openai / deepseek / custom
    api_key: str = ""
    base_url: str = ""       # 自定义 base_url（兼容 OpenAI 格式的第三方）
    model: str = ""          # 模型名
    is_active: bool = False  # 当前是否激活


class ApiConfig(BaseModel):
    # 高级分析模型（用于 AI 洞察卡片等需要深度分析的场景）
    premium_model: str = "deepseek/deepseek-chat-v3-0324"
    # Financial Datasets AI — US stocks premium data source
    financial_datasets_api_key: str = ""
    providers: List[ApiProvider] = [
        ApiProvider(
            name="OpenRouter (默认)",
            provider="openai_compatible",
            base_url="https://openrouter.ai/api/v1",
            model="deepseek/deepseek-chat-v3-0324",
            is_active=True,
        ),
        ApiProvider(
            name="Claude Haiku (低成本)",
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
        ),
        ApiProvider(
            name="Claude Sonnet (均衡)",
            provider="anthropic",
            model="claude-sonnet-4-6",
        ),
        ApiProvider(
            name="Claude Opus (最强)",
            provider="anthropic",
            model="claude-opus-4-6",
        ),
        ApiProvider(
            name="DeepSeek",
            provider="openai_compatible",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        ),
        ApiProvider(
            name="自定义 (OpenAI 兼容)",
            provider="openai_compatible",
            model="",
        ),
    ]


class PriceAlert(BaseModel):
    symbol: str
    name: str = ""
    market: str = "us"          # us / hk / a_share
    target_price: float = 0.0
    direction: str = "below"    # "below": alert when price <= target; "above": when >= target
    enabled: bool = True
    note: str = ""


class NotifyConfig(BaseModel):
    enabled: bool = False
    method: str = "email"             # email / webhook
    # 邮件
    smtp_server: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""           # 授权码
    email_to: str = ""
    # Webhook (钉钉/飞书/企业微信/Telegram)
    webhook_url: str = ""
    # 推送频率
    schedule_time: str = "08:00"      # 每日推送时间
    schedule_days: str = "mon-fri"    # 推送日（工作日）
    # 推送内容
    push_grade_change: bool = True    # 评级变化时推送
    push_daily_summary: bool = True   # 每日摘要
    push_alert_threshold: float = 80  # 评分超过此值时特别提醒
    # 价格提醒
    price_alerts: List[PriceAlert] = []


class BuffettStrategy(BaseModel):
    min_roe: float = 15
    roe_consistency_years: int = 5
    max_debt_to_equity: float = 0.5
    min_current_ratio: float = 1.5
    min_interest_coverage: float = 5
    margin_of_safety: float = 0.25
    max_pe: float = 25
    max_pb: float = 3
    min_revenue_growth: float = 5
    min_earnings_growth: float = 8
    min_dividend_years: int = 5
    min_payout_ratio: float = 0.2


class TechnicalConfig(BaseModel):
    sma_periods: List[int] = [20, 50, 200]
    rsi_period: int = 14
    lookback_days: int = 250


class RateLimitConfig(BaseModel):
    """LLM RPM caps to prevent 429s on hedge-fund / committee bursts.

    Conservative defaults match OpenRouter / DeepSeek free tiers. Increase if
    you have a paid plan with higher limits.
    """
    enabled: bool = True
    requests_per_min: int = 60   # per (provider_type, api_key) bucket
    burst: int = 13              # immediate parallel burst (covers 13 masters)
    max_wait_seconds: float = 30.0


class ParallelConfig(BaseModel):
    """Centralized ThreadPoolExecutor max_workers settings.

    Tune these to balance throughput vs upstream rate-limits (yfinance / akshare /
    LLM providers). Higher = faster but more likely to be throttled.
    """
    dashboard_workers: int = 8     # pages/1_dashboard.py — watchlist quote fan-out
    portfolio_workers: int = 8     # pages/5_portfolio.py — live price fan-out
    scan_workers: int = 4          # pages/2_analysis.py — single-market scanner
    scan_all_workers: int = 6      # pages/2_analysis.py — cross-market scanner
    financial_workers: int = 5     # src/data/financial.py — multi-year fundamentals
    committee_workers: int = 5     # src/ai/committee.py — 5-master LLM votes
    hedgefund_workers: int = 6     # src/ai/hedge_fund_runner.py — 13-master LLM votes


class AppConfig(BaseModel):
    api: ApiConfig = ApiConfig()
    watchlist: Watchlist = Watchlist()
    buffett_strategy: BuffettStrategy = BuffettStrategy()
    technical: TechnicalConfig = TechnicalConfig()
    parallel: ParallelConfig = ParallelConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    notify: NotifyConfig = NotifyConfig()


_config: Optional[AppConfig] = None
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _resolve_api_keys(config: AppConfig):
    """从环境变量 / Streamlit secrets 注入 API Key（优先级高于 config.yaml）

    支持的环境变量:
    - OPENROUTER_API_KEY  → 匹配 name 含 "OpenRouter" 的 provider
    - ANTHROPIC_API_KEY   → 匹配 provider == "anthropic"
    - DEEPSEEK_API_KEY    → 匹配 name 含 "DeepSeek"
    - AI_API_KEY          → 通用兜底，注入到第一个 is_active 的 provider
    """
    # 尝试从 Streamlit secrets 读取（Streamlit Cloud 部署用）
    secrets = {}
    try:
        import streamlit as st
        secrets = dict(st.secrets) if hasattr(st, "secrets") else {}
    except Exception:
        pass

    def _get(key: str) -> str:
        return os.environ.get(key, "") or secrets.get(key, "")

    env_map = {
        "OPENROUTER_API_KEY": lambda p: "openrouter" in p.name.lower(),
        "ANTHROPIC_API_KEY": lambda p: p.provider == "anthropic",
        "DEEPSEEK_API_KEY": lambda p: "deepseek" in p.name.lower(),
    }

    for env_key, matcher in env_map.items():
        val = _get(env_key)
        if val:
            for p in config.api.providers:
                if matcher(p):
                    p.api_key = val

    # Financial Datasets AI
    fd_key = _get("FINANCIAL_DATASETS_API_KEY")
    if fd_key:
        config.api.financial_datasets_api_key = fd_key

    # 通用兜底
    fallback = _get("AI_API_KEY")
    if fallback:
        for p in config.api.providers:
            if p.is_active and not p.api_key:
                p.api_key = fallback
                break


def load_config(path: Optional[Path] = None) -> AppConfig:
    global _config
    if _config is not None:
        return _config
    p = path or CONFIG_PATH
    if p.exists():
        with open(p) as f:
            data = yaml.safe_load(f) or {}
        # 兼容旧配置格式
        if "api_keys" in data and "api" not in data:
            old_key = data.pop("api_keys", {}).get("anthropic", "")
            if old_key:
                data.setdefault("api", {}).setdefault("providers", [{}])[0]["api_key"] = old_key
        if "ai" in data:
            data.pop("ai", None)
        data.pop("schedule", None)
        _config = AppConfig(**data)
        # 若 config.yaml 中 watchlist 为空，填入默认股票列表
        wl = _config.watchlist
        if not wl.us:
            wl.us = _default_us()
        if not wl.hk:
            wl.hk = _default_hk()
        if not wl.a_share:
            wl.a_share = _default_a()
    else:
        _config = AppConfig(
            watchlist=Watchlist(
                us=_default_us(),
                hk=_default_hk(),
                a_share=_default_a(),
            )
        )

    # 环境变量 / secrets 注入
    _resolve_api_keys(_config)
    return _config


def save_config(config: AppConfig, path: Optional[Path] = None):
    """保存配置到文件（api_key 不写入磁盘，仅通过环境变量/Secrets 注入）"""
    p = path or CONFIG_PATH
    data = config.model_dump()
    # 安全：清除所有 api_key，防止明文泄露到磁盘
    for provider in data.get("api", {}).get("providers", []):
        provider["api_key"] = ""
    with open(p, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_active_provider(config: AppConfig) -> Optional[ApiProvider]:
    """获取当前激活的 API provider"""
    for p in config.api.providers:
        if p.is_active and p.api_key:
            return p
    return None


def get_premium_provider(config: AppConfig) -> Optional[ApiProvider]:
    """获取高级推理模型 provider（用于 AI 洞察等深度分析）

    复用当前激活 provider 的 API key 和 base_url，替换为 premium_model。
    """
    base = get_active_provider(config)
    if not base:
        return None
    premium_model = config.api.premium_model
    if not premium_model:
        return base
    return ApiProvider(
        name="Premium Analysis",
        provider=base.provider,
        api_key=base.api_key,
        base_url=base.base_url,
        model=premium_model,
        is_active=True,
    )


def get_config() -> AppConfig:
    return load_config()
