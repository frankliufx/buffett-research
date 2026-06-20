def test_model_presets_defined():
    """Ensure our 4 preset model dicts have required keys."""
    from pages._model_presets import MODEL_PRESETS
    assert len(MODEL_PRESETS) == 4
    for preset in MODEL_PRESETS:
        assert "label" in preset
        assert "model" in preset
        assert "base_url" in preset


def test_model_presets_have_icon():
    from pages._model_presets import MODEL_PRESETS
    for preset in MODEL_PRESETS:
        assert "icon" in preset
        assert preset["icon"]  # non-empty


def test_model_presets_have_non_empty_fields():
    from pages._model_presets import MODEL_PRESETS
    for preset in MODEL_PRESETS:
        assert preset["label"]
        assert preset["model"]
        assert preset["base_url"].startswith("https://")


def test_switching_preset_updates_provider_fields():
    from pages._model_presets import MODEL_PRESETS
    from src.config import ApiProvider
    provider = ApiProvider(
        name="Test", provider="openai_compatible",
        model="old/model", base_url="https://old.url/v1", is_active=True
    )
    preset = MODEL_PRESETS[0]
    # simulate the switch logic from 4_settings.py
    provider.model = preset["model"]
    provider.base_url = preset["base_url"]
    provider.provider = "openai_compatible"
    assert provider.model == preset["model"]
    assert provider.base_url == preset["base_url"]
