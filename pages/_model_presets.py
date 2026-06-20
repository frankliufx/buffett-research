"""Hardcoded quick-switch model presets (all via OpenRouter)."""

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_PRESETS = [
    {
        "label": "DeepSeek Chat",
        "model": "deepseek/deepseek-chat-v3-0324",
        "base_url": _OPENROUTER_BASE_URL,
        "icon": "💬",
    },
    {
        "label": "DeepSeek R1",
        "model": "deepseek/deepseek-r1",
        "base_url": _OPENROUTER_BASE_URL,
        "icon": "🧠",
    },
    {
        "label": "GPT-4o",
        "model": "openai/gpt-4o",
        "base_url": _OPENROUTER_BASE_URL,
        "icon": "⚡",
    },
    {
        "label": "o1",
        "model": "openai/o1",
        "base_url": _OPENROUTER_BASE_URL,
        "icon": "🔬",
    },
]
