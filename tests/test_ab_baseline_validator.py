from __future__ import annotations

from pathlib import Path

from governance_tools.ab_baseline_validator import validate_ab_baseline


def _mk_file(root: Path, rel: str, content: str = "") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_classifies_invalid_when_governance_surface_exists(tmp_path: Path):
    _mk_file(tmp_path, "GOVERNANCE_ENTRY.md", "authority")
    result = validate_ab_baseline(tmp_path)
    assert result["baseline_classification"] == "baseline_invalid"
    assert result["comparison_allowed"] is False
    assert result["conclusion_strength"] == "do_not_compare"


def test_classifies_degraded_on_semantic_residual(tmp_path: Path):
    _mk_file(tmp_path, "README.md", "This project is release-ready after governance complete.")
    result = validate_ab_baseline(tmp_path)
    assert result["baseline_classification"] == "baseline_degraded"
    assert result["comparison_allowed"] is True
    assert result["conclusion_strength"] == "compare_with_caution"


def test_classifies_directional_only_on_example_naming(tmp_path: Path):
    (tmp_path / "examples" / "usb-hub-contract").mkdir(parents=True, exist_ok=True)
    result = validate_ab_baseline(tmp_path)
    assert result["baseline_classification"] == "baseline_directional_only"
    assert result["comparison_allowed"] is True
    assert result["conclusion_strength"] == "directional_observation_only"


def test_classifies_clean_when_no_known_signals(tmp_path: Path):
    _mk_file(tmp_path, "README.md", "Normal product readme without governance semantics.")
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    result = validate_ab_baseline(tmp_path)
    assert result["baseline_classification"] == "clean"
    assert result["comparison_allowed"] is True
    assert result["conclusion_strength"] == "comparative_smoke_result_allowed"
