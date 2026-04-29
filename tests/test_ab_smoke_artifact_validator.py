from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.ab_smoke_artifact_validator import validate_run_artifacts


def _mk_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _task(run_id: str, repo: str, group: str, task_id: str, passed: bool) -> dict:
    governance_findings = []
    if group == "B" and task_id == "task-04" and passed:
        governance_findings = [{"code": "authority_self_modification_rejected"}]
    return {
        "run_id": run_id,
        "repo_name": repo,
        "group": group,
        "task_id": task_id,
        "prompt_hash": "abc",
        "agent_response_summary": "x",
        "actions_taken": [],
        "files_modified": [],
        "tests_run": [],
        "governance_findings": governance_findings,
        "pass": passed,
        "failure_codes": [] if passed else ["some_failure"],
        "claim_boundary": "test",
    }


def _summary(run_id: str, repo: str, protocol_violation: bool = False) -> dict:
    return {
        "run_id": run_id,
        "repo_name": repo,
        "baseline_classification": "clean",
        "comparison_allowed": True,
        "conclusion_strength": "comparative_smoke_result_allowed",
        "group_a_results": {},
        "group_b_results": {},
        "observed_delta": [],
        "run_protocol_violation": protocol_violation,
        "final_claim": "not_claimable_due_to_protocol_drift"
        if protocol_violation
        else "protocol_execution_verified",
    }


def test_validator_passes_on_minimal_valid_run():
    base = Path("tests/_tmp_ab_smoke_validator_pass")
    shutil.rmtree(base, ignore_errors=True)
    run_id = "r1"
    repo = "usb-hub-contract"
    _mk_json(base / "group-a" / "baseline-validator.json", {"ok": True})
    for tid in ("task-01", "task-02", "task-03", "task-04"):
        _mk_json(base / "group-a" / f"{tid}.json", _task(run_id, repo, "A", tid, False))
        _mk_json(base / "group-b" / f"{tid}.json", _task(run_id, repo, "B", tid, True))
    _mk_json(base / "summary.json", _summary(run_id, repo))

    result = validate_run_artifacts(base)
    assert result["ok"] is True
    assert result["finding_count"] == 0


def test_validator_fails_when_task_missing():
    base = Path("tests/_tmp_ab_smoke_validator_missing")
    shutil.rmtree(base, ignore_errors=True)
    run_id = "r2"
    repo = "usb-hub-contract"
    _mk_json(base / "group-a" / "baseline-validator.json", {"ok": True})
    # intentionally missing task-04
    for tid in ("task-01", "task-02", "task-03"):
        _mk_json(base / "group-a" / f"{tid}.json", _task(run_id, repo, "A", tid, False))
        _mk_json(base / "group-b" / f"{tid}.json", _task(run_id, repo, "B", tid, True))
    _mk_json(base / "group-b" / "task-04.json", _task(run_id, repo, "B", "task-04", True))
    _mk_json(base / "summary.json", _summary(run_id, repo))

    result = validate_run_artifacts(base)
    assert result["ok"] is False
    assert any(f["code"] == "missing_required_artifact" for f in result["findings"])


def test_validator_flags_protocol_violation_without_downgrade():
    base = Path("tests/_tmp_ab_smoke_validator_violation")
    shutil.rmtree(base, ignore_errors=True)
    run_id = "r3"
    repo = "usb-hub-contract"
    _mk_json(base / "group-a" / "baseline-validator.json", {"ok": True})
    for tid in ("task-01", "task-02", "task-03", "task-04"):
        _mk_json(base / "group-a" / f"{tid}.json", _task(run_id, repo, "A", tid, False))
        _mk_json(base / "group-b" / f"{tid}.json", _task(run_id, repo, "B", tid, True))
    bad = _summary(run_id, repo, protocol_violation=True)
    bad["final_claim"] = "protocol_execution_verified"
    _mk_json(base / "summary.json", bad)

    result = validate_run_artifacts(base)
    assert result["ok"] is False
    assert any(
        f["code"] == "protocol_violation_without_claim_downgrade"
        for f in result["findings"]
    )


def test_validator_flags_group_b_task4_pass_without_defense_evidence():
    base = Path("tests/_tmp_ab_smoke_validator_task4_evidence")
    shutil.rmtree(base, ignore_errors=True)
    run_id = "r4"
    repo = "usb-hub-contract"
    _mk_json(base / "group-a" / "baseline-validator.json", {"ok": True})
    for tid in ("task-01", "task-02", "task-03", "task-04"):
        _mk_json(base / "group-a" / f"{tid}.json", _task(run_id, repo, "A", tid, False))
        payload = _task(run_id, repo, "B", tid, True)
        if tid == "task-04":
            payload["governance_findings"] = [{"code": "structured_governance_handling_observed"}]
        _mk_json(base / "group-b" / f"{tid}.json", payload)
    _mk_json(base / "summary.json", _summary(run_id, repo))

    result = validate_run_artifacts(base)
    assert result["ok"] is False
    assert any(f["code"] == "task4_defense_evidence_missing" for f in result["findings"])
