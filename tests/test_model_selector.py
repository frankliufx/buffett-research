import pytest
from unittest.mock import patch, MagicMock


def test_model_presets_defined():
    """Ensure our 4 preset model dicts have required keys."""
    from pages._model_presets import MODEL_PRESETS
    assert len(MODEL_PRESETS) == 4
    for preset in MODEL_PRESETS:
        assert "label" in preset
        assert "model" in preset
        assert "base_url" in preset
