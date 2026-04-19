from __future__ import annotations

from governance_tools.review_artifact_linter import lint_text


def _claim_types(text: str) -> set[str]:
    return {v["claim_type"] for v in lint_text(text)["violations"]}


def test_conservative_wording_with_readiness_hint_is_detected():
    text = (
        "本次僅做 observation，不進 interpretation；"
        "但已具備 readiness 基礎，可作為後續判讀起點。"
    )
    result = lint_text(text)
    assert result["status"] == "non-clean"
    assert "readiness_claim" in _claim_types(text)


def test_procedural_wording_with_stability_claim_is_detected():
    text = "依流程先觀測後決策，目前可視為穩定，建議維持這個狀態。"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    assert "stability_claim" in _claim_types(text)


def test_review_suggestion_with_promotion_laundering_is_detected():
    text = "不構成正式 promote 依據，但建議可往升格討論前進。"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    types = _claim_types(text)
    assert "confidence_laundering" in types or "promotion_claim" in types


def test_pressure_false_positive_guard_clean_when_explicitly_non_interpretive():
    text = (
        "依流程先觀測後決策，未進 interpretation phase，"
        "故不作 readiness / stability / promotion 結論。"
    )
    result = lint_text(text)
    assert result["status"] == "clean"
    assert result["violation_count"] == 0


def test_surface_drift_mixed_language_is_detected():
    text = "目前看起來 stable，可往下一步；Next: move toward interpretation."
    result = lint_text(text)
    assert result["status"] == "non-clean"
    types = _claim_types(text)
    assert "stability_claim" in types or "directional_interpretation" in types


def test_surface_drift_abbreviation_shortcodes_are_detected():
    text = "Status: R4R, GTG. Promo candidate."
    result = lint_text(text)
    assert result["status"] == "non-clean"
    types = _claim_types(text)
    assert "readiness_claim" in types
    assert "promotion_claim" in types


def test_surface_drift_heading_labels_are_detected():
    text = "Overall Stability\nPromotion Context\nStatus: healthy"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    types = _claim_types(text)
    assert "stability_claim" in types
    assert "promotion_claim" in types
    assert "quality_verdict" in types


def test_surface_drift_short_chinese_labels_are_detected():
    text = "狀態: 穩。建議: 可升。"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    types = _claim_types(text)
    assert "stability_claim" in types
    assert "promotion_claim" in types


def test_surface_drift_false_positive_guard_for_policy_only_status_words():
    text = (
        "本文件列出禁用標籤：Status: stable、Status: healthy、Promo candidate。"
        "以上僅作政策說明，不作 readiness / promotion / stability 結論。"
    )
    result = lint_text(text)
    assert result["status"] == "clean"
