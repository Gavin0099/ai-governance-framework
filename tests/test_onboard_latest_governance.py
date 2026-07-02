from __future__ import annotations

import json
from pathlib import Path

from governance_tools import onboard_latest_governance as onboard
from governance_tools.governance_update_reporting import build_final_report_requirement


def _sample_maturity_summary() -> dict[str, object]:
    return {
        "report_only": True,
        "user_facing_status": {"value": "partial", "reasons": ["test"]},
        "human_readable_adoption_summary": [
            "[human_readable_adoption_summary]",
            "| 功能 | 狀態 | 這個功能是做什麼 |",
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


def test_render_summary_includes_adoption_summary_and_final_requirement() -> None:
    rendered = onboard._render_summary(_sample_payload())

    assert "[governance_maturity_summary]" in rendered
    assert "[human_readable_adoption_summary]" in rendered
    assert "| 版本帳實一致性（Lock vs checkout consistency） | 不一致 |" in rendered
    assert "[final_report_requirement]" in rendered
    assert "Final AI Governance update reports must relay" in rendered


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
        }
    )

    assert payload["governance_maturity_summary"]["status"] == "not_available"
    assert payload["governance_maturity_summary"]["claim_boundary"] == (
        "summary unavailable; no maturity claim is supported"
    )
    assert "claim_boundary=summary unavailable; no maturity claim is supported" in rendered
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
        assert payload["final_report_requirement"]["status"] == "required"
        assert "[human_readable_adoption_summary]" in payload["final_report_requirement"]["human_readable_adoption_summary"]


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
    assert "final_report_requirement=required" in output
    assert "required_marker=[human_readable_adoption_summary]" in output
    assert "brief_claim_boundary=marker_only_not_final_report_use_full_human_or_json_report_for_table_rows" in output
    assert "| 版本帳實一致性（Lock vs checkout consistency） | 不一致 |" not in output
