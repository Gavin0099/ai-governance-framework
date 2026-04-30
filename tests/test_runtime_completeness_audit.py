import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.runtime_completeness_audit import build_runtime_completeness_audit

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_runtime_completeness_audit"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_integrity_ok_when_all_artifacts_present() -> None:
    repo = _reset_fixture("all_present")
    sid = "s1"
    _write_json(repo / "artifacts" / "runtime" / "verdicts" / f"{sid}.json", {"session_id": sid})
    _write_json(repo / "artifacts" / "runtime" / "closeouts" / f"{sid}.json", {"session_id": sid})
    _write_json(repo / "artifacts" / "claim-enforcement" / sid / "claim-enforcement-check.json", {"enforcement_action": "allow"})

    out = build_runtime_completeness_audit(repo)
    assert out["integrity_ok"] is True
    assert out["silent_drop_count"] == 0


def test_detects_silent_drop_when_claim_binding_missing() -> None:
    repo = _reset_fixture("claim_missing")
    sid = "s2"
    _write_json(repo / "artifacts" / "runtime" / "verdicts" / f"{sid}.json", {"session_id": sid})
    _write_json(repo / "artifacts" / "runtime" / "closeouts" / f"{sid}.json", {"session_id": sid})

    out = build_runtime_completeness_audit(repo)
    assert out["integrity_ok"] is False
    assert out["silent_drop_count"] == 1
    assert out["claim_binding_missing_for_invoked_session"] == [sid]


def test_detects_silent_drop_when_closeout_missing() -> None:
    repo = _reset_fixture("closeout_missing")
    sid = "s3"
    _write_json(repo / "artifacts" / "runtime" / "verdicts" / f"{sid}.json", {"session_id": sid})
    _write_json(repo / "artifacts" / "claim-enforcement" / sid / "claim-enforcement-check.json", {"enforcement_action": "allow"})

    out = build_runtime_completeness_audit(repo)
    assert out["integrity_ok"] is False
    assert out["silent_drop_count"] == 1
    assert out["closeout_missing_for_invoked_session"] == [sid]


def test_baseline_split_separates_historical_and_new_window() -> None:
    repo = _reset_fixture("baseline_split")
    old_sid = "old-001"
    new_sid = "new-001"
    _write_json(
        repo / "artifacts" / "runtime" / "verdicts" / f"{old_sid}.json",
        {"session_id": old_sid, "generated_at": "2026-04-29T00:00:00+00:00"},
    )
    _write_json(
        repo / "artifacts" / "runtime" / "verdicts" / f"{new_sid}.json",
        {"session_id": new_sid, "generated_at": "2026-04-30T00:00:00+00:00"},
    )
    _write_json(repo / "artifacts" / "runtime" / "closeouts" / f"{old_sid}.json", {"session_id": old_sid})
    _write_json(repo / "artifacts" / "runtime" / "closeouts" / f"{new_sid}.json", {"session_id": new_sid})
    _write_json(repo / "artifacts" / "claim-enforcement" / new_sid / "claim-enforcement-check.json", {"enforcement_action": "allow"})

    out = build_runtime_completeness_audit(
        repo,
        baseline_before="2026-04-30T00:00:00+00:00",
        only_new_sessions=False,
    )
    assert out["historical_silent_drop_count"] == 1
    assert out["new_window_silent_drop_count"] == 0
    assert out["new_window_integrity_ok"] is True


def test_only_new_sessions_scope() -> None:
    repo = _reset_fixture("only_new_scope")
    _write_json(
        repo / "artifacts" / "runtime" / "verdicts" / "old.json",
        {"session_id": "old", "generated_at": "2026-04-29T00:00:00+00:00"},
    )
    _write_json(
        repo / "artifacts" / "runtime" / "verdicts" / "new.json",
        {"session_id": "new", "generated_at": "2026-04-30T00:00:00+00:00"},
    )
    _write_json(repo / "artifacts" / "runtime" / "closeouts" / "old.json", {"session_id": "old"})
    _write_json(repo / "artifacts" / "runtime" / "closeouts" / "new.json", {"session_id": "new"})
    _write_json(repo / "artifacts" / "claim-enforcement" / "old" / "claim-enforcement-check.json", {"enforcement_action": "allow"})

    out = build_runtime_completeness_audit(
        repo,
        baseline_before="2026-04-30T00:00:00+00:00",
        only_new_sessions=True,
    )
    assert out["verdict_session_count"] == 1
    assert out["silent_drop_count"] == 1
    assert out["claim_binding_missing_for_invoked_session"] == ["new"]
