from __future__ import annotations

from pathlib import Path

from governance_tools.checkpoint_memory_baseline_compare import compare_payloads, format_human


def _baseline(findings: list[dict]) -> dict:
    by_code: dict[str, int] = {}
    dispositions: dict[tuple[str, str], list[str]] = {}
    for finding in findings:
        by_code[finding["code"]] = by_code.get(finding["code"], 0) + 1
        key = (finding["code"], finding["disposition"])
        dispositions.setdefault(key, []).append(finding["subject"])
    return {
        "baseline_id": "test-baseline",
        "source_head": "base",
        "source_window": "--last 5",
        "summary": {"total": len(findings), "by_code": by_code},
        "dispositions": [
            {"code": code, "disposition": disposition, "subjects": subjects}
            for (code, disposition), subjects in dispositions.items()
        ],
    }


def _current(findings: list[dict]) -> dict:
    by_code: dict[str, int] = {}
    for finding in findings:
        by_code[finding["code"]] = by_code.get(finding["code"], 0) + 1
    return {
        "scope": {"repo": "fixture", "window": "--last 5"},
        "summary": {"total": len(findings), "by_code": by_code, "clean": not findings},
        "findings": [
            {
                "code": finding["code"],
                "subject": finding["subject"],
                "evidence": "fixture",
                "suggested_action": "review",
                "severity": "advisory",
            }
            for finding in findings
        ],
    }


def _lookup(_repo: Path, commit: str) -> str:
    subjects = {
        "mem123": "docs(memory): record checkpoint baseline push",
        "feat123": "feat(governance): change claim surface",
    }
    return subjects.get(commit, "")


def _write_memory_entry(
    repo: Path,
    *,
    commit_hash: str,
    memory_binding: str,
    what_changed: str,
) -> None:
    memory = repo / "memory" / "2026-06-19.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    existing = memory.read_text(encoding="utf-8") if memory.exists() else "# 2026-06-19\n\n"
    memory.write_text(
        existing
        + "- memory_type: session-derived\n"
        + "  record_format_version: 1.0\n"
        + "  writer: governance_tools.memory_record\n"
        + f"  what_changed: {what_changed}\n"
        + f"  commit: {commit_hash}\n"
        + f"  commit_hash: {commit_hash}\n"
        + "  session_id: test-session\n"
        + f"  memory_binding: {memory_binding}\n"
        + "  test_evidence: PASS: command only\n"
        + "  next_step: none\n"
        + "  plan_reconciliation: not_applicable\n\n",
        encoding="utf-8",
    )


def test_no_new_drift_preserves_baseline_disposition(tmp_path: Path) -> None:
    findings = [
        {
            "code": "unreceipted_validation",
            "subject": "2026-06-03.md:70",
            "disposition": "baseline_debt",
        }
    ]

    payload = compare_payloads(
        baseline=_baseline(findings),
        current=_current(findings),
        repo=tmp_path,
        commit_subject_lookup=_lookup,
    )

    assert payload["blocking"] is False
    assert payload["delta"]["new_total"] == 0
    assert payload["delta"]["by_disposition"]["baseline_debt"] == 1
    assert payload["new_findings"] == []


def test_new_memory_commit_is_expected_noise(tmp_path: Path) -> None:
    payload = compare_payloads(
        baseline=_baseline([]),
        current=_current([{"code": "commit_without_memory", "subject": "mem123"}]),
        repo=tmp_path,
        commit_subject_lookup=_lookup,
    )

    assert payload["delta"]["new_total"] == 1
    assert payload["new_findings"][0]["disposition"] == "expected_noise"
    assert payload["delta"]["by_disposition"]["expected_noise"] == 1


def test_new_claim_bearing_drift_is_reported_without_blocking(tmp_path: Path) -> None:
    payload = compare_payloads(
        baseline=_baseline([]),
        current=_current([{"code": "commit_without_memory", "subject": "feat123"}]),
        repo=tmp_path,
        commit_subject_lookup=_lookup,
    )

    assert payload["blocking"] is False
    assert payload["delta"]["new_total"] == 1
    assert payload["new_findings"][0]["disposition"] == "new_drift"
    assert "new_total=1" in format_human(payload)


def test_worktree_record_with_later_bound_commit_is_workflow_residue(tmp_path: Path) -> None:
    _write_memory_entry(
        tmp_path,
        commit_hash="WORKTREE",
        memory_binding="unbound",
        what_changed="Implemented advisory observation packet.",
    )
    _write_memory_entry(
        tmp_path,
        commit_hash="abc1234",
        memory_binding="bound",
        what_changed="Post-push record: pushed advisory observation packet.",
    )

    payload = compare_payloads(
        baseline=_baseline([]),
        current=_current([{"code": "stale_no_commit_memory", "subject": "2026-06-19.md:3"}]),
        repo=tmp_path,
        commit_subject_lookup=_lookup,
    )

    assert payload["new_findings"][0]["disposition"] == "workflow_residue"
    assert payload["delta"]["by_disposition"]["workflow_residue"] == 1


def test_post_push_command_only_pass_is_receipt_shape_residue(tmp_path: Path) -> None:
    _write_memory_entry(
        tmp_path,
        commit_hash="abc1234",
        memory_binding="bound",
        what_changed="Post-push record: pushed advisory observation packet.",
    )

    payload = compare_payloads(
        baseline=_baseline([]),
        current=_current([{"code": "unreceipted_validation", "subject": "2026-06-19.md:3"}]),
        repo=tmp_path,
        commit_subject_lookup=_lookup,
    )

    assert payload["new_findings"][0]["disposition"] == "receipt_shape_residue"
    assert payload["delta"]["by_disposition"]["receipt_shape_residue"] == 1
