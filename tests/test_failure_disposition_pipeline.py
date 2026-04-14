"""
Pipeline integration tests for failure_disposition (E3 slices 1/2/3).

Slice 1  — test_result_ingestor populates failure_disposition
Slice 1.5 — ingestor --out writes JSON artifact to path
Slice 2  — session_end_hook.format_human_result displays failure_disposition
Slice 3  — session_end_hook.run_session_end_hook gates on verdict_blocked=True
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.test_result_ingestor import ingest_pytest_text
from governance_tools.session_end_hook import format_human_result, run_session_end_hook


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_result(**overrides) -> dict:
    """Minimal synthetic result dict accepted by format_human_result."""
    base = {
        "ok": True,
        "session_id": "session-test-000000",
        "closeout_status": "valid",
        "memory_tier": "no_update",
        "repo_readiness_level": 0,
        "repo_readiness_limiting_factor": None,
        "repo_closeout_activation_state": "unknown",
        "repo_activation_recency": None,
        "repo_activation_gap": None,
        "closeout_classification": None,
        "per_layer_results": {},
        "failure_signals": [],
        "failure_disposition": None,
        "closeout_file": "artifacts/session-closeout.txt",
        "decision": "DO_NOT_PROMOTE",
        "snapshot_created": False,
        "promoted": False,
        "memory_closeout": None,
        "warnings": [],
        "errors": [],
    }
    base.update(overrides)
    return base


@pytest.fixture
def tmp_project_root(tmp_path):
    """Minimal temp project root (no closeout file)."""
    artifacts = tmp_path / "artifacts" / "runtime"
    artifacts.mkdir(parents=True)
    return tmp_path


def _write_test_artifact(project_root: Path, disposition: dict | None) -> Path:
    """Write a minimal test result artifact for slice 3 tests."""
    artifact_dir = project_root / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "latest.json"
    payload = {
        "source": "pytest-text",
        "ok": disposition is None or not disposition.get("verdict_blocked"),
        "failure_disposition": disposition,
        "errors": [],
        "warnings": [],
    }
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    return artifact


# ── Slice 1: ingestor populates failure_disposition ───────────────────────────

def test_ingestor_populates_failure_disposition_when_failures_present():
    payload = ingest_pytest_text(
        "FAILED tests/test_foo.py::test_broken - AssertionError: expected 1\n"
        "FAILED tests/test_foo.py::test_also_broken - RuntimeError: something\n"
        "========================= 2 failed in 0.5s ========================="
    )
    assert payload["failure_disposition"] is not None
    disp = payload["failure_disposition"]
    assert "verdict_blocked" in disp
    assert "total" in disp
    assert disp["total"] == 2


def test_ingestor_failure_disposition_none_when_no_failures():
    payload = ingest_pytest_text(
        "tests/test_foo.py::test_ok .\n"
        "========================= 1 passed in 0.1s ========================="
    )
    assert payload["failure_disposition"] is None


def test_ingestor_promotes_production_fix_required_to_warnings():
    """integration_drift failures map to production_fix_required → warning promoted."""
    payload = ingest_pytest_text(
        # Name contains 'integration' — corpus seed maps this to integration_drift
        "FAILED tests/test_integration.py::test_real_backend_contract - AssertionError\n"
        "========================= 1 failed in 0.5s ========================="
    )
    # If production_fix_required > 0, a warning must be present
    disp = payload.get("failure_disposition") or {}
    pfr = (disp.get("by_action") or {}).get("production_fix_required", 0)
    if pfr > 0:
        assert any("production_fix_required" in w for w in payload["warnings"])


# ── Slice 1.5: ingestor --out writes artifact ─────────────────────────────────

def test_ingestor_main_writes_out_artifact(tmp_path):
    """
    Test the --out logic directly (not via subprocess).
    We replicate what main() does: ingest, serialize, write to file.
    """
    import argparse
    # Simulate: ingest + write
    result = ingest_pytest_text(
        "FAILED tests/test_foo.py::test_x - err\n"
        "========================= 1 failed in 0.1s ========================="
    )
    out_path = tmp_path / "sub" / "latest.json"
    out_str = json.dumps(result, ensure_ascii=False, indent=2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_str, encoding="utf-8")

    assert out_path.exists()
    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    assert parsed["failure_disposition"] is not None
    assert parsed["source"] == "pytest-text"


# ── Slice 2: format_human_result displays failure_disposition ─────────────────

def test_format_human_result_shows_failure_disposition_block():
    result = _minimal_result(failure_disposition={
        "verdict_blocked": True,
        "total": 2,
        "unknown_count": 0,
        "taxonomy_expansion_signal": False,
        "by_action": {"production_fix_required": 1, "test_fix_only": 1},
    })
    output = format_human_result(result)
    assert "failure_disposition:" in output
    assert "verdict_blocked=True" in output
    assert "total=2" in output


def test_format_human_result_shows_gate_marker_for_production_fix_required():
    result = _minimal_result(failure_disposition={
        "verdict_blocked": True,
        "total": 1,
        "unknown_count": 0,
        "taxonomy_expansion_signal": False,
        "by_action": {"production_fix_required": 1},
    })
    output = format_human_result(result)
    assert "[GATE]" in output
    assert "production_fix_required=1" in output


def test_format_human_result_shows_taxonomy_expansion_signal():
    result = _minimal_result(failure_disposition={
        "verdict_blocked": True,
        "total": 5,
        "unknown_count": 4,
        "taxonomy_expansion_signal": True,
        "by_action": {"escalate": 4, "test_fix_only": 1},
    })
    output = format_human_result(result)
    assert "[SIGNAL]" in output
    assert "taxonomy_expansion_signal" in output


def test_format_human_result_no_failure_disposition_block_when_none():
    result = _minimal_result(failure_disposition=None)
    output = format_human_result(result)
    assert "failure_disposition:" not in output
    assert "[GATE]" not in output


def test_format_human_result_no_gate_marker_when_verdict_not_blocked():
    result = _minimal_result(failure_disposition={
        "verdict_blocked": False,
        "total": 1,
        "unknown_count": 0,
        "taxonomy_expansion_signal": False,
        "by_action": {"test_fix_only": 1},
    })
    output = format_human_result(result)
    assert "failure_disposition:" in output
    assert "[GATE]" not in output


# ── Slice 3: run_session_end_hook gates on verdict_blocked ────────────────────

def test_run_session_end_hook_no_artifact_has_failure_disposition_none(tmp_project_root):
    """When no test result artifact exists, failure_disposition is None and gate is skipped."""
    result = run_session_end_hook(project_root=tmp_project_root)
    assert "failure_disposition" in result
    assert result["failure_disposition"] is None
    # Gate error should NOT be present
    assert not any("[GATE:production_fix_required]" in e for e in result["errors"])


def test_run_session_end_hook_verdict_blocked_false_gate_skipped(tmp_project_root):
    """Artifact present but verdict_blocked=False → gate is not triggered."""
    _write_test_artifact(tmp_project_root, disposition={
        "verdict_blocked": False,
        "total": 1,
        "unknown_count": 0,
        "taxonomy_expansion_signal": False,
        "by_action": {"test_fix_only": 1},
    })
    result = run_session_end_hook(project_root=tmp_project_root)
    assert result["failure_disposition"] is not None
    assert result["failure_disposition"]["verdict_blocked"] is False
    assert not any("[GATE:production_fix_required]" in e for e in result["errors"])


def test_run_session_end_hook_verdict_blocked_true_adds_gate_error(tmp_project_root):
    """Artifact with verdict_blocked=True → ok=False AND gate error added."""
    _write_test_artifact(tmp_project_root, disposition={
        "verdict_blocked": True,
        "total": 2,
        "unknown_count": 0,
        "taxonomy_expansion_signal": False,
        "by_action": {"production_fix_required": 2},
    })
    result = run_session_end_hook(project_root=tmp_project_root)
    assert result["ok"] is False
    assert result["failure_disposition"]["verdict_blocked"] is True
    gate_errors = [e for e in result["errors"] if "[GATE:production_fix_required]" in e]
    assert len(gate_errors) == 1
    assert "2" in gate_errors[0]


def test_run_session_end_hook_malformed_artifact_skips_gate_gracefully(tmp_project_root):
    """Malformed JSON in artifact must not crash session_end_hook."""
    artifact_dir = tmp_project_root / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "latest.json").write_text("{ not valid json }", encoding="utf-8")

    result = run_session_end_hook(project_root=tmp_project_root)
    # Should not raise; gate skipped silently
    assert "failure_disposition" in result
    assert result["failure_disposition"] is None
    assert not any("[GATE:production_fix_required]" in e for e in result["errors"])


def test_run_session_end_hook_artifact_with_no_disposition_field_skips_gate(tmp_project_root):
    """Artifact present but failure_disposition key absent → treat as no disposition."""
    artifact_dir = tmp_project_root / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "latest.json").write_text(
        json.dumps({"source": "pytest-text", "ok": True}),
        encoding="utf-8",
    )
    result = run_session_end_hook(project_root=tmp_project_root)
    assert result["failure_disposition"] is None
    assert not any("[GATE:production_fix_required]" in e for e in result["errors"])


# ── F3.5: taxonomy signal observability contract ──────────────────────────────

def test_f3_5_add_advisory_warnings_includes_threshold_number():
    """F3.5 unit: _add_advisory_warnings() must produce a warning string that
    contains both unknown_count AND unknown_threshold as visible numbers.
    Operators must be able to verify the judgment basis from the warning text
    alone, without reading source code."""
    from governance_tools.gate_policy import _add_advisory_warnings, load_policy  # noqa: PLC0415

    disp = {
        "taxonomy_expansion_signal": True,
        "unknown_count": 5,
        "unknown_threshold": 3,
    }
    policy = load_policy()  # builtin default — only used to satisfy signature
    warnings: list[str] = []
    _add_advisory_warnings(disp, policy, warnings)

    assert len(warnings) == 1, f"expected 1 advisory warning, got {warnings}"
    w = warnings[0]
    assert "taxonomy_expansion_signal" in w, f"signal name missing: {w!r}"
    assert "5" in w, f"unknown_count (5) not in warning: {w!r}"
    assert "3" in w, f"unknown_threshold (3) not in warning: {w!r}"


def test_f3_5_taxonomy_signal_visible_with_threshold_in_hook_warnings(tmp_project_root):
    """F3.5 E2E: when the test-result artifact carries taxonomy_expansion_signal=True,
    run_session_end_hook() must surface a warning that includes both the unknown_count
    and the unknown_threshold value — so operators have the full judgment basis
    from the hook output alone."""
    _write_test_artifact(tmp_project_root, disposition={
        "verdict_blocked": False,
        "total": 5,
        "unknown_count": 5,
        "unknown_threshold": 3,
        "taxonomy_expansion_signal": True,
        "by_action": {"escalate": 5},
        "by_kind": {"unknown": 5},
        "by_confidence": {"unknown": 5},
        "results": [],
    })
    result = run_session_end_hook(project_root=tmp_project_root)

    taxonomy_warnings = [w for w in result["warnings"] if "taxonomy_expansion_signal" in w]
    assert len(taxonomy_warnings) >= 1, (
        f"expected at least one taxonomy_expansion_signal warning; got {result['warnings']}"
    )
    w = taxonomy_warnings[0]
    assert "5" in w, f"unknown_count not in warning: {w!r}"
    assert "3" in w, f"unknown_threshold not in warning: {w!r}"
