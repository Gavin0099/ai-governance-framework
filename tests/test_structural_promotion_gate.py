from __future__ import annotations

from pathlib import Path

from governance_tools.structural_promotion_gate import evaluate_gate


def _write_closeout(path: Path, claim_boundary: str, degraded_reason: str = "") -> None:
    lines = [
        "# closeout",
        f"- claim_boundary: `{claim_boundary}`",
    ]
    if degraded_reason:
        lines.append(f"- test_execution_degraded_reason: `{degraded_reason}`")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_long_term(path: Path, authoritative: bool, with_all_markers: bool) -> None:
    if authoritative:
        body = [
            "## Section A",
            "<!-- promotion_status: authoritative -->",
            "<!-- promoted_by: Gavin / 2026-04-30 -->",
        ]
        if with_all_markers:
            body.append("<!-- promoted_at: 2026-04-30 -->")
            body.append("<!-- source_anchor: commit:abc1234 -->")
        body.append("content")
    else:
        body = [
            "## Section A",
            "<!-- promotion_status: candidate -->",
            "content",
        ]
    path.write_text("\n".join(["# Long-Term Memory", *body]), encoding="utf-8")


def test_runtime_verified_all_markers_allows_promotion(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    _write_long_term(memory_root / "00_long_term.md", authoritative=True, with_all_markers=True)
    closeout = tmp_path / "closeout.md"
    _write_closeout(closeout, "runtime_verified")

    result = evaluate_gate(memory_root, tmp_path, closeout)
    assert result["promotion_allowed"] is True
    assert result["ok"] is True
    assert result["blocked_reasons"] == []


def test_degraded_execution_blocks_promotion(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    _write_long_term(memory_root / "00_long_term.md", authoritative=True, with_all_markers=True)
    closeout = tmp_path / "closeout.md"
    _write_closeout(closeout, "runtime_verified", degraded_reason="pytest_basetemp_permission_error")

    result = evaluate_gate(memory_root, tmp_path, closeout)
    assert result["promotion_allowed"] is False
    assert "test_execution_degraded" in result["blocked_reasons"]
    assert result["failure_class"] == "runtime_unverifiable"


def test_missing_promoted_markers_blocks_promotion(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    _write_long_term(memory_root / "00_long_term.md", authoritative=True, with_all_markers=False)
    closeout = tmp_path / "closeout.md"
    _write_closeout(closeout, "runtime_verified")

    result = evaluate_gate(memory_root, tmp_path, closeout)
    assert result["promotion_allowed"] is False
    assert "missing_required_promotion_markers" in result["blocked_reasons"]


def test_structural_authority_rate_zero_blocks_promotion(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    _write_long_term(memory_root / "00_long_term.md", authoritative=False, with_all_markers=False)
    closeout = tmp_path / "closeout.md"
    _write_closeout(closeout, "runtime_verified")

    result = evaluate_gate(memory_root, tmp_path, closeout)
    assert result["promotion_allowed"] is False
    assert "missing_structural_promotions" in result["blocked_reasons"]
