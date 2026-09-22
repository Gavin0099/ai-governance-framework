from __future__ import annotations

import json
import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from governance_tools import onboard_latest_governance as onboard
from governance_tools.governance_update_reporting import (
    build_ai_governance_update_result,
    build_final_report_requirement,
    build_final_report_table_required,
)


def _sample_maturity_summary() -> dict[str, object]:
    return {
        "report_only": True,
        "user_facing_status": {"value": "partial", "reasons": ["test"]},
        "human_readable_adoption_summary": [
            "[human_readable_adoption_summary]",
            "| 功能 | 狀態 | 這個功能是做什麼 |",
            "| --- | --- | --- |",
            "| 版本帳實一致性（Lock vs checkout consistency） | 不一致 | 比對 lock 與 checkout。 |",
        ],
    }


def _sample_payload() -> dict[str, object]:
    maturity = _sample_maturity_summary()
    return {
        "mode": "plan",
        "repo": "E:/repo",
        "snapshot": "E:/snapshot.json",
        "classification_before": "repo_native_candidate",
        "classification_after": "repo_native_candidate",
        "stopped_for_human_required": False,
        "acceptance_after": {
            "hooks": False,
            "fw": True,
            "agents": True,
            "evidence": False,
            "head_ok": False,
            "ts_ok": False,
            "repo_native_verified": False,
            "detector_errors": 0,
            "signal_details": {},
        },
        "actions": [],
        "governance_maturity_summary": maturity,
        "final_report_requirement": build_final_report_requirement(maturity),
        "final_report_table_required": build_final_report_table_required(
            build_final_report_requirement(maturity)
        ),
        "ai_governance_update_result": build_ai_governance_update_result(
            framework_update_status="not_verified",
            framework_update_source="onboard_latest_governance",
            governance_maturity_summary=maturity,
            final_report_requirement=build_final_report_requirement(maturity),
            cannot_claim=[
                "repo_native_verified as full governance adoption",
                "framework update freshness",
            ],
        ),
    }


def _write_snapshot(project_root: Path, repo: Path) -> Path:
    snapshot_dir = project_root / "artifacts" / "session"
    snapshot_dir.mkdir(parents=True)
    snapshot = snapshot_dir / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "evidence_window_days": 7,
                "operational_maturity": {
                    "remediation_suggestions": [
                        {
                            "repo": str(repo),
                            "classification": "repo_native_candidate",
                            "suggestions": [],
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return snapshot


def test_attach_reporting_surfaces_builds_summary_and_requirement(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(onboard, "build_governance_maturity_summary", lambda repo, framework_root: object())
    monkeypatch.setattr(onboard, "governance_maturity_summary_to_dict", lambda summary: _sample_maturity_summary())

    payload: dict[str, object] = {}
    onboard._attach_reporting_surfaces(payload, tmp_path / "repo", tmp_path / "framework")

    assert payload["governance_maturity_summary"] == _sample_maturity_summary()
    requirement = payload["final_report_requirement"]
    assert isinstance(requirement, dict)
    assert requirement["status"] == "required"
    assert "table rows as a table" in requirement["instruction"]
    assert "[human_readable_adoption_summary]" in requirement["human_readable_adoption_summary"]
    table = payload["final_report_table_required"]
    assert isinstance(table, dict)
    assert table["status"] == "required"
    assert table["must_relay_as"] == "table_rows_verbatim"
    assert "[human_readable_adoption_summary]" in table["table_rows"]
    envelope = payload["ai_governance_update_result"]
    assert envelope["report_only"] is True
    assert envelope["framework_update_status"] == {
        "value": "not_verified",
        "source": "onboard_latest_governance",
    }
    assert envelope["adoption_status"]["value"] == "partial"
    assert envelope["final_report_requirement"] == {
        "value": "present",
        "source": "onboard_latest_governance",
    }
    assert "repo_native_verified as full governance adoption" in envelope["cannot_claim"]


def test_render_summary_includes_adoption_summary_and_final_requirement() -> None:
    rendered = onboard._render_summary(_sample_payload())

    assert "[governance_maturity_summary]" in rendered
    assert "[ai_governance_update_result]" in rendered
    assert "framework_update_status=not_verified" in rendered
    assert "adoption_status=partial" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "| 版本帳實一致性（Lock vs checkout consistency） | 不一致 |" in rendered
    assert "[final_report_requirement]" in rendered
    assert "Final AI Governance update reports must relay" in rendered


def test_onboard_update_result_reports_blocked_when_actions_stop() -> None:
    payload = {
        **_sample_payload(),
        "stopped_for_human_required": True,
        "actions": [{"status": "stopped_human_required"}],
    }

    envelope = onboard._build_onboard_update_result(payload)

    assert envelope["framework_update_status"] == {
        "value": "blocked",
        "source": "onboard_latest_governance",
    }


def test_maturity_summary_failure_has_explicit_claim_boundary(monkeypatch, tmp_path: Path) -> None:
    def boom(repo_path: Path, framework_root: Path) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(onboard, "build_governance_maturity_summary", boom)

    payload: dict[str, object] = {}
    onboard._attach_reporting_surfaces(payload, tmp_path / "repo", tmp_path / "framework")
    rendered = onboard._render_summary(
        {
            **_sample_payload(),
            "governance_maturity_summary": payload["governance_maturity_summary"],
            "final_report_requirement": payload["final_report_requirement"],
            "final_report_table_required": payload["final_report_table_required"],
            "ai_governance_update_result": payload["ai_governance_update_result"],
        }
    )

    assert payload["governance_maturity_summary"]["status"] == "not_available"
    assert payload["ai_governance_update_result"]["governance_maturity_summary"][
        "value"
    ] == "not_available"
    assert payload["ai_governance_update_result"]["human_readable_adoption_summary"][
        "value"
    ] == "not_reported"
    assert payload["governance_maturity_summary"]["claim_boundary"] == (
        "summary unavailable; no maturity claim is supported"
    )
    assert "claim_boundary=summary unavailable; no maturity claim is supported" in rendered
    assert "governance_maturity_summary=not_available" in rendered
    assert "claim_boundary=None" not in rendered


def test_write_report_json_contains_reporting_surfaces(monkeypatch, tmp_path: Path, capsys) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    project_root = tmp_path / "framework"
    snapshot = _write_snapshot(project_root, repo)

    monkeypatch.setattr(onboard, "_compute_acceptance", lambda repo_path, window_days: _sample_payload()["acceptance_after"])
    monkeypatch.setattr(onboard, "compute_codeburn_token_summary", lambda repo_path: "not_checked")
    monkeypatch.setattr(onboard, "build_governance_maturity_summary", lambda repo_path, framework_root: object())
    monkeypatch.setattr(onboard, "governance_maturity_summary_to_dict", lambda summary: _sample_maturity_summary())

    rc = onboard.run(
        [
            "--repo",
            str(repo),
            "--project-root",
            str(project_root),
            "--snapshot",
            str(snapshot),
            "--mode",
            "plan",
            "--format",
            "json",
            "--write-report",
        ]
    )

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    report_path = Path(output["report_path"])
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    for payload in (output, report_payload):
        assert payload["governance_maturity_summary"]["report_only"] is True
        assert payload["ai_governance_update_result"]["report_only"] is True
        assert payload["ai_governance_update_result"]["framework_update_status"] == {
            "value": "not_verified",
            "source": "onboard_latest_governance",
        }
        assert payload["ai_governance_update_result"]["adoption_status"]["value"] == "partial"
        assert payload["final_report_requirement"]["status"] == "required"
        assert "[human_readable_adoption_summary]" in payload["final_report_requirement"]["human_readable_adoption_summary"]
        assert payload["final_report_table_required"]["status"] == "required"
        assert payload["final_report_table_required"]["must_relay_as"] == "table_rows_verbatim"
        assert "[human_readable_adoption_summary]" in payload["final_report_table_required"]["table_rows"]


def test_brief_output_relays_final_report_requirement_boundary(monkeypatch, tmp_path: Path, capsys) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    project_root = tmp_path / "framework"
    snapshot = _write_snapshot(project_root, repo)

    monkeypatch.setattr(onboard, "_compute_acceptance", lambda repo_path, window_days: _sample_payload()["acceptance_after"])
    monkeypatch.setattr(onboard, "compute_codeburn_token_summary", lambda repo_path: "not_checked")
    monkeypatch.setattr(onboard, "build_governance_maturity_summary", lambda repo_path, framework_root: object())
    monkeypatch.setattr(onboard, "governance_maturity_summary_to_dict", lambda summary: _sample_maturity_summary())

    rc = onboard.run(
        [
            "--repo",
            str(repo),
            "--project-root",
            str(project_root),
            "--snapshot",
            str(snapshot),
            "--mode",
            "plan",
            "--brief",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "run=plan" in output
    assert "ai_governance_update_result=report_only" in output
    assert "framework_update_status=not_verified" in output
    assert "adoption_status=partial" in output
    assert "final_report_requirement=required" in output
    assert "required_marker=[human_readable_adoption_summary]" in output
    assert "brief_claim_boundary=marker_only_not_final_report_use_full_human_or_json_report_for_table_rows" in output
    assert "| 版本帳實一致性（Lock vs checkout consistency） | 不一致 |" not in output


@pytest.fixture
def acceptance_repo(tmp_path: Path, monkeypatch):
    """Real receipt/text/audit files; isolate unrelated hook and Git detectors."""
    repo = tmp_path / "consumer"
    (repo / "governance").mkdir(parents=True)
    (repo / "governance/framework.lock.json").write_text("{}", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# Consumer", encoding="utf-8")
    receipts = repo / "artifacts/runtime/closeout-receipts"
    receipts.mkdir(parents=True)
    artifact = repo / "artifacts/session-closeout.txt"
    artifact.write_text("WORK_COMPLETED: Fixed the bounded parser bug.\n", encoding="utf-8")
    now = datetime.now(timezone.utc)
    receipt = {
        "schema_version": "1.3",
        "timestamp": now.isoformat(),
        "agent_id": "codex",
        "session_id": "session-a",
        "trigger_mode": "native_hook",
        "entrypoint": "governance_tools.session_closeout_entry",
        "exit_code": 0,
        "linked_head_commit": "a" * 40,
        "closeout_artifact_path": "artifacts/session-closeout.txt",
        "checksum_of_cleaned_path": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "memory_eligibility_evaluated": True,
        "memory_write_required": False,
        "memory_write_performed": False,
        "memory_eligibility_reason": "no durable update required",
    }
    audit = {
        "timestamp": (now - timedelta(seconds=1)).isoformat(),
        "session_id": receipt["session_id"],
        "linked_head_commit": receipt["linked_head_commit"],
        "gate_blocked": False,
    }
    receipt_path = receipts / "closeout_receipt_current.json"
    audit_path = repo / "artifacts/runtime/canonical-audit-log.jsonl"

    def write():
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        audit_path.write_text(json.dumps(audit) + "\n", encoding="utf-8")

    write()
    monkeypatch.setattr(onboard, "_signal_hooks", lambda root: (True, onboard._signal("Y")))
    monkeypatch.setattr(onboard, "_run_powershell_command", lambda command, root: (0, "a" * 40, ""))
    return repo, receipt, audit, receipt_path, audit_path, write


def _accept(fixture):
    return onboard._compute_acceptance(fixture[0], 7)


@pytest.mark.parametrize("version", ["1.3", "1.5"])
def test_acceptance_valid_receipt_and_matching_gate_observation(acceptance_repo, version):
    repo, receipt, _, _, _, write = acceptance_repo
    receipt["schema_version"] = version
    if version == "1.5":
        receipt.update(
            runtime_detection_status="unknown", sample_origin="natural_task",
            memory_write_required=True, daily_memory_write_attempted=True,
            daily_memory_write_status="already_present", daily_memory_state_status="satisfied",
            daily_memory_path="memory/2026-09-22.md", daily_memory_record_identity="b" * 64,
            daily_memory_writer="governance_tools.memory_record", daily_memory_write_error="",
        )
    write()
    before = {str(p.relative_to(repo)): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in repo.rglob("*") if p.is_file()}
    result = _accept(acceptance_repo)
    after = {str(p.relative_to(repo)): (p.read_bytes(), p.stat().st_mtime_ns)
             for p in repo.rglob("*") if p.is_file()}
    assert result["repo_native_verified"] is True
    assert before == after


@pytest.mark.parametrize("exit_code", [1, None, False, "0"])
def test_acceptance_rejects_failed_or_invalid_exit_code(acceptance_repo, exit_code):
    acceptance_repo[1]["exit_code"] = exit_code
    acceptance_repo[5]()
    assert _accept(acceptance_repo)["repo_native_verified"] is False


@pytest.mark.parametrize("case", ["missing_receipt", "malformed_receipt", "receipt_list",
                                 "missing_exit", "missing_artifact", "changed_artifact"])
def test_acceptance_rejects_unproven_receipt(acceptance_repo, case):
    repo, receipt, _, receipt_path, _, write = acceptance_repo
    if case == "missing_receipt":
        receipt_path.unlink()
    elif case == "malformed_receipt":
        receipt_path.write_text("{", encoding="utf-8")
    elif case == "receipt_list":
        receipt_path.write_text("[]", encoding="utf-8")
    elif case == "missing_exit":
        receipt.pop("exit_code")
        write()
    elif case == "missing_artifact":
        (repo / receipt["closeout_artifact_path"]).unlink()
    else:
        (repo / receipt["closeout_artifact_path"]).write_text("changed", encoding="utf-8")
    assert _accept(acceptance_repo)["repo_native_verified"] is False


@pytest.mark.parametrize("case", ["blocked", "missing", "malformed", "unknown_gate",
                                 "string_gate", "foreign_session", "foreign_head", "after_receipt"])
def test_acceptance_requires_bound_gate_observation(acceptance_repo, case):
    _, receipt, audit, _, audit_path, write = acceptance_repo
    if case == "blocked":
        audit["gate_blocked"] = True
    elif case == "unknown_gate":
        audit.pop("gate_blocked")
    elif case == "string_gate":
        audit["gate_blocked"] = "false"
    elif case == "foreign_session":
        audit["session_id"] = "session-b"
    elif case == "foreign_head":
        audit["linked_head_commit"] = "b" * 40
    elif case == "after_receipt":
        audit["timestamp"] = (datetime.fromisoformat(receipt["timestamp"]) + timedelta(seconds=1)).isoformat()
    write()
    if case == "missing":
        audit_path.unlink()
    elif case == "malformed":
        audit_path.write_text("{", encoding="utf-8")
    assert _accept(acceptance_repo)["repo_native_verified"] is False


def test_foreign_success_cannot_rescue_blocked_session(acceptance_repo):
    _, _, audit, _, audit_path, write = acceptance_repo
    audit["gate_blocked"] = True
    write()
    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({**audit, "session_id": "other", "gate_blocked": False}) + "\n")
    assert _accept(acceptance_repo)["repo_native_verified"] is False


@pytest.mark.parametrize("malformed", [False, True])
def test_latest_invalid_receipt_does_not_fall_back_to_old_success(acceptance_repo, malformed):
    _, receipt, _, receipt_path, _, _ = acceptance_repo
    older = receipt_path.with_name("closeout_receipt_old.json")
    older.write_bytes(receipt_path.read_bytes())
    os.utime(older, (1, 1))
    receipt["exit_code"] = 1
    receipt_path.write_text("{" if malformed else json.dumps(receipt), encoding="utf-8")
    assert _accept(acceptance_repo)["repo_native_verified"] is False


@pytest.mark.parametrize("case", ["head_mismatch", "stale", "future"])
def test_acceptance_preserves_head_and_time_rejection(acceptance_repo, case):
    _, receipt, audit, _, _, write = acceptance_repo
    if case == "head_mismatch":
        receipt["linked_head_commit"] = audit["linked_head_commit"] = "b" * 40
    else:
        days = 8 if case == "stale" else -365
        receipt["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        audit["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=days, seconds=1)).isoformat()
    write()
    assert _accept(acceptance_repo)["repo_native_verified"] is False


def test_report_does_not_keep_snapshot_verified_after_current_evidence_fails(acceptance_repo, monkeypatch, capsys, tmp_path):
    repo, _, audit, _, _, write = acceptance_repo
    audit["gate_blocked"] = True
    write()
    framework = tmp_path / "framework"
    snapshot = _write_snapshot(framework, repo)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["operational_maturity"]["remediation_suggestions"][0]["classification"] = "repo_native_verified"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(onboard, "compute_codeburn_token_summary", lambda root: "not_checked")
    monkeypatch.setattr(onboard, "_attach_reporting_surfaces", lambda *args: None)
    assert onboard.run(["--repo", str(repo), "--project-root", str(framework),
                        "--snapshot", str(snapshot), "--mode", "plan", "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["acceptance_after"]["repo_native_verified"] is False
    assert result["classification_before"] == "repo_native_verified"
    assert result["classification_after"] != "repo_native_verified"


@pytest.mark.parametrize("exit_code,blocked,expected", [(0, False, True), (0, True, False), (1, False, False)])
@pytest.mark.parametrize("entrypoint", ["governance_tools.session_closeout_entry", "governance_tools.closeout_handoff"])
def test_acceptance_with_existing_receipt_and_audit_producers(acceptance_repo, monkeypatch, exit_code, blocked, expected, entrypoint):
    from governance_tools import session_closeout_entry as entry
    from governance_tools import session_end_hook as hook

    repo, _, _, receipt_path, audit_path, _ = acceptance_repo
    receipt_path.unlink()
    audit_path.unlink()
    monkeypatch.setattr(entry, "_resolve_head_commit", lambda root: "a" * 40)
    monkeypatch.setattr(hook, "_get_repo_head", lambda root: "a" * 40)
    hook._append_canonical_audit_log(
        repo, session_id="session-a", artifact_state="ok",
        canonical_path_audit={}, gate_blocked=blocked, policy_source="repo",
        policy_path=str(repo / "governance/gate_policy.yaml"),
        fallback_used=False, repo_policy_present=True,
    )
    entry._write_closeout_receipt(
        repo, agent_id="codex", session_id="session-a", trigger_mode="native_hook",
        entrypoint=entrypoint, exit_code=exit_code,
        closeout_artifact_path=str(repo / "artifacts/session-closeout.txt"),
        memory_eligibility_evaluated=True, memory_write_required=False,
        memory_write_performed=False, memory_eligibility_reason="no durable update required",
    )
    assert _accept(acceptance_repo)["repo_native_verified"] is expected
