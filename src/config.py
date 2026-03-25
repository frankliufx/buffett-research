"""配置加载与验证"""

import os
from pathlib import Path
from typing import Optional, List
import yaml
from pydantic import BaseModel


class StockItem(BaseModel):
    symbol: str
    name: str


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
    providers: List[ApiProvider] = [
        ApiProvider(
            name="OpenRouter (默认)",
            provider="openai_compatible",
            base_url="https://openrouter.ai/api/v1",
            model="anthropic/claude-haiku-4-5-20251001",
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


class AppConfig(BaseModel):
    api: ApiConfig = ApiConfig()
    watchlist: Watchlist = Watchlist()
    buffett_strategy: BuffettStrategy = BuffettStrategy()
    technical: TechnicalConfig = TechnicalConfig()
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
    else:
        _config = AppConfig()

    # 环境变量 / secrets 注入
    _resolve_api_keys(_config)
    return _config


def save_config(config: AppConfig, path: Optional[Path] = None):
    """保存配置到文件"""
    p = path or CONFIG_PATH
    data = config.model_dump()
    # 不保存空 api_key 到文件（安全考虑，key 可在 UI 中输入）
    with open(p, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_active_provider(config: AppConfig) -> Optional[ApiProvider]:
    """获取当前激活的 API provider"""
    for p in config.api.providers:
        if p.is_active and p.api_key:
            return p
    return None


def get_config() -> AppConfig:
    return load_config()
