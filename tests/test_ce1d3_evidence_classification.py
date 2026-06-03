"""CE-1D.3: audit evidence classification.

Validates:
- runtime_completeness_audit classifies sessions by raw packet location:
    claim_binding_runtime_only  — gitignored runtime path only
    claim_binding_legacy_only   — legacy tracked path only
    claim_binding_both_paths    — both paths present (migration overlap)
    claim_binding_missing_for_invoked_session — no raw evidence at either path
- closeout_audit._evaluate_claim_binding returns runtime/legacy count breakdown
- format_human_result includes the classification summary lines
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.closeout_audit import build_closeout_audit
from governance_tools.runtime_completeness_audit import (
    build_runtime_completeness_audit,
    format_human_result,
)


NEW_RAW_ROOT_REL = "artifacts/session/claim-enforcement"
OLD_RAW_ROOT_REL = "artifacts/claim-enforcement"


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "memory").mkdir()
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def _write_verdict(repo: Path, session_id: str) -> None:
    verdict_dir = repo / "artifacts" / "runtime" / "verdicts"
    verdict_dir.mkdir(parents=True, exist_ok=True)
    (verdict_dir / f"{session_id}.json").write_text(
        json.dumps({"session_id": session_id}), encoding="utf-8"
    )


def _write_packet(repo: Path, session_id: str, root_rel: str) -> Path:
    packet = repo / root_rel / session_id / "claim-enforcement-check.json"
    packet.parent.mkdir(parents=True, exist_ok=True)
    packet.write_text(json.dumps({"enforcement_action": "allow"}), encoding="utf-8")
    return packet


# ---------------------------------------------------------------------------
# runtime_completeness_audit: per-session evidence classification
# ---------------------------------------------------------------------------


def test_runtime_only_session_classified_correctly(tmp_project):
    sid = "ce1d3-runtime-only"
    _write_verdict(tmp_project, sid)
    _write_packet(tmp_project, sid, NEW_RAW_ROOT_REL)

    result = build_runtime_completeness_audit(tmp_project)
    assert sid in result["claim_binding_runtime_only"], (
        "session with runtime-path-only packet must be in claim_binding_runtime_only"
    )
    assert sid not in result["claim_binding_missing_for_invoked_session"]
    assert sid not in result["claim_binding_legacy_only"]
    assert sid not in result["claim_binding_both_paths"]


def test_legacy_only_session_classified_correctly(tmp_project):
    sid = "ce1d3-legacy-only"
    _write_verdict(tmp_project, sid)
    _write_packet(tmp_project, sid, OLD_RAW_ROOT_REL)

    result = build_runtime_completeness_audit(tmp_project)
    assert sid in result["claim_binding_legacy_only"], (
        "session with legacy-path-only packet must be in claim_binding_legacy_only"
    )
    assert sid not in result["claim_binding_missing_for_invoked_session"]
    assert sid not in result["claim_binding_runtime_only"]
    assert sid not in result["claim_binding_both_paths"]


def test_both_paths_session_classified_correctly(tmp_project):
    sid = "ce1d3-both-paths"
    _write_verdict(tmp_project, sid)
    _write_packet(tmp_project, sid, NEW_RAW_ROOT_REL)
    _write_packet(tmp_project, sid, OLD_RAW_ROOT_REL)

    result = build_runtime_completeness_audit(tmp_project)
    assert sid in result["claim_binding_both_paths"], (
        "session with packet at both paths must be in claim_binding_both_paths"
    )
    assert sid not in result["claim_binding_missing_for_invoked_session"]
    assert sid not in result["claim_binding_runtime_only"]
    assert sid not in result["claim_binding_legacy_only"]


def test_missing_session_still_in_missing_list(tmp_project):
    sid = "ce1d3-absent"
    _write_verdict(tmp_project, sid)
    # No packet at either path

    result = build_runtime_completeness_audit(tmp_project)
    assert sid in result["claim_binding_missing_for_invoked_session"], (
        "session with no packet at either path must remain in claim_binding_missing"
    )
    assert sid not in result["claim_binding_runtime_only"]
    assert sid not in result["claim_binding_legacy_only"]
    assert sid not in result["claim_binding_both_paths"]


def test_mixed_sessions_all_classified(tmp_project):
    sessions = {
        "ce1d3-mix-runtime": NEW_RAW_ROOT_REL,
        "ce1d3-mix-legacy": OLD_RAW_ROOT_REL,
        "ce1d3-mix-absent": None,
    }
    for sid, root in sessions.items():
        _write_verdict(tmp_project, sid)
        if root:
            _write_packet(tmp_project, sid, root)

    result = build_runtime_completeness_audit(tmp_project)
    assert "ce1d3-mix-runtime" in result["claim_binding_runtime_only"]
    assert "ce1d3-mix-legacy" in result["claim_binding_legacy_only"]
    assert "ce1d3-mix-absent" in result["claim_binding_missing_for_invoked_session"]


def test_classification_fields_present_when_empty(tmp_project):
    """Return dict must always include classification keys, even when all are empty."""
    result = build_runtime_completeness_audit(tmp_project)
    assert "claim_binding_runtime_only" in result
    assert "claim_binding_legacy_only" in result
    assert "claim_binding_both_paths" in result
    assert isinstance(result["claim_binding_runtime_only"], list)
    assert isinstance(result["claim_binding_legacy_only"], list)
    assert isinstance(result["claim_binding_both_paths"], list)


# ---------------------------------------------------------------------------
# format_human_result: classification summary lines
# ---------------------------------------------------------------------------


def test_format_human_result_includes_runtime_only_count(tmp_project):
    sid = "ce1d3-fmt-runtime"
    _write_verdict(tmp_project, sid)
    _write_packet(tmp_project, sid, NEW_RAW_ROOT_REL)

    result = build_runtime_completeness_audit(tmp_project)
    output = format_human_result(result)
    assert "claim_binding_runtime_only_count=1" in output


def test_format_human_result_includes_legacy_only_count(tmp_project):
    sid = "ce1d3-fmt-legacy"
    _write_verdict(tmp_project, sid)
    _write_packet(tmp_project, sid, OLD_RAW_ROOT_REL)

    result = build_runtime_completeness_audit(tmp_project)
    output = format_human_result(result)
    assert "claim_binding_legacy_only_count=1" in output


def test_format_human_result_zero_counts_when_empty(tmp_project):
    result = build_runtime_completeness_audit(tmp_project)
    output = format_human_result(result)
    assert "claim_binding_runtime_only_count=0" in output
    assert "claim_binding_legacy_only_count=0" in output
    assert "claim_binding_both_paths_count=0" in output


# ---------------------------------------------------------------------------
# closeout_audit: runtime/legacy count breakdown
# ---------------------------------------------------------------------------


def _write_closeout(repo: Path, session_id: str) -> None:
    closeout_dir = repo / "artifacts" / "runtime" / "closeouts"
    closeout_dir.mkdir(parents=True, exist_ok=True)
    (closeout_dir / f"{session_id}.json").write_text(
        json.dumps({
            "session_id": session_id,
            "closed_at": "2026-06-03T00:00:00+00:00",
            "closeout_status": "valid",
            "task_intent": "test",
            "work_summary": "test",
            "evidence_summary": {"tools_used": [], "artifacts_referenced": []},
            "open_risks": [],
        }),
        encoding="utf-8",
    )


def test_closeout_audit_runtime_count_for_runtime_packet(tmp_project):
    _write_closeout(tmp_project, "ce1d3-ca-runtime")
    _write_packet(tmp_project, "ce1d3-ca-runtime", NEW_RAW_ROOT_REL)

    result = build_closeout_audit(tmp_project)
    assert result["claim_enforcement_runtime_count"] >= 1
    assert result["claim_enforcement_legacy_count"] == 0


def test_closeout_audit_legacy_count_for_legacy_packet(tmp_project):
    _write_closeout(tmp_project, "ce1d3-ca-legacy")
    _write_packet(tmp_project, "ce1d3-ca-legacy", OLD_RAW_ROOT_REL)

    result = build_closeout_audit(tmp_project)
    assert result["claim_enforcement_legacy_count"] >= 1
    assert result["claim_enforcement_runtime_count"] == 0


def test_closeout_audit_both_counts_when_mixed(tmp_project):
    _write_closeout(tmp_project, "ce1d3-ca-mixed-r")
    _write_closeout(tmp_project, "ce1d3-ca-mixed-l")
    _write_packet(tmp_project, "ce1d3-ca-mixed-r", NEW_RAW_ROOT_REL)
    _write_packet(tmp_project, "ce1d3-ca-mixed-l", OLD_RAW_ROOT_REL)

    result = build_closeout_audit(tmp_project)
    assert result["claim_enforcement_runtime_count"] >= 1
    assert result["claim_enforcement_legacy_count"] >= 1
    assert result["claim_enforcement_check_count"] == (
        result["claim_enforcement_runtime_count"]
        + result["claim_enforcement_legacy_count"]
    )


def test_closeout_audit_classification_keys_always_present(tmp_project):
    result = build_closeout_audit(tmp_project)
    assert "claim_enforcement_runtime_count" in result
    assert "claim_enforcement_legacy_count" in result
    assert isinstance(result["claim_enforcement_runtime_count"], int)
    assert isinstance(result["claim_enforcement_legacy_count"], int)
