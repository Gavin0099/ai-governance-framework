from __future__ import annotations

import json

import governance_tools.review_artifact_linter as linter
from governance_tools.review_artifact_linter import lint_text


def _claim_types(text: str) -> set[str]:
    return {v["claim_type"] for v in lint_text(text)["violations"]}


def test_explicit_violation_detected():
    text = "這已足以 support promote，readiness 已成立，可視為穩定。"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    assert {"readiness_claim", "promotion_claim", "stability_claim"} <= _claim_types(text)
    assert all("severity" in v for v in result["violations"])


def test_wrapped_violation_detected():
    text = "看起來已經成熟很多，目前趨勢偏正向，整體狀態令人安心。"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    assert "quality_verdict" in _claim_types(text)


def test_laundering_violation_detected():
    text = "雖然不能直接下結論，但大致上可視為穩定；不構成正式依據，但已呈現健康訊號。"
    result = lint_text(text)
    assert result["status"] == "non-clean"
    assert "confidence_laundering" in _claim_types(text)
    assert any(v["layer"] == "layer2_argument" for v in result["violations"])


def test_false_positive_guard_clean_text_passes():
    text = (
        "本報告僅提供 observation，不支援 readiness 判讀。"
        "未進 interpretation phase，故不作穩定性結論。"
    )
    result = lint_text(text)
    assert result["status"] == "clean"
    assert result["violation_count"] == 0


def test_cli_non_clean_exit_and_json(monkeypatch, capsys):
    monkeypatch.setattr(linter, "_read_input", lambda _p: "可作為後續升格參考。")
    rc = linter.main(["--input", "-", "--json"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "non-clean"
    assert payload["violation_count"] >= 1

