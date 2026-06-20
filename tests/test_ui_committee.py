"""Unit tests for committee member card HTML rendering."""
import pytest
from src.ui_committee import render_committee_page


MINIMAL_MEMBER = {
    "icon": "📊",
    "name_cn": "价值投资者",
    "style": "Value",
    "signal": "bullish",
    "confidence": 75,
    "reasoning": "Strong FCF and low P/B.",
    "key_evidence": None,
    "main_concern": None,
}


def _build_committee(member_overrides: dict) -> dict:
    member = {**MINIMAL_MEMBER, **member_overrides}
    return {
        "members": [member],
        "consensus": {"signal": "bullish", "verdict": "BUY", "unanimity": "High"},
        "weighted_score": 60,
        "bullish_count": 1,
        "bearish_count": 0,
        "neutral_count": 0,
    }


class TestMemberCardEvidenceAndConcern:
    def test_no_evidence_section_when_key_evidence_absent(self):
        committee = _build_committee({"key_evidence": None})
        html = render_committee_page(committee=committee)
        assert "m-evidence" not in html

    def test_evidence_section_rendered_when_key_evidence_present(self):
        committee = _build_committee({"key_evidence": "FCF yield 8.2% over 5Y avg."})
        html = render_committee_page(committee=committee)
        assert "m-evidence" in html
        assert "FCF yield 8.2% over 5Y avg." in html

    def test_no_concern_section_when_main_concern_absent(self):
        committee = _build_committee({"main_concern": None})
        html = render_committee_page(committee=committee)
        assert "m-concern" not in html

    def test_concern_section_rendered_when_main_concern_present(self):
        committee = _build_committee({"main_concern": "Leverage ratio elevated at 3.2x."})
        html = render_committee_page(committee=committee)
        assert "m-concern" in html
        assert "Leverage ratio elevated at 3.2x." in html

    def test_concern_includes_warning_icon(self):
        committee = _build_committee({"main_concern": "Revenue declining."})
        html = render_committee_page(committee=committee)
        assert "&#9888;" in html

    def test_both_evidence_and_concern_render_together(self):
        committee = _build_committee({
            "key_evidence": "ROE 25% for 10 consecutive years.",
            "main_concern": "High capex requirement limits FCF.",
        })
        html = render_committee_page(committee=committee)
        assert "m-evidence" in html
        assert "m-concern" in html
        assert "ROE 25% for 10 consecutive years." in html
        assert "High capex requirement limits FCF." in html

    def test_existing_reasoning_still_present(self):
        committee = _build_committee({"reasoning": "Durable moat confirmed."})
        html = render_committee_page(committee=committee)
        assert "Durable moat confirmed." in html
        assert "m-reason" in html
