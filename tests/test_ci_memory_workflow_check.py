from __future__ import annotations

import subprocess
from pathlib import Path

from governance_tools.ci_memory_workflow_check import check
from governance_tools.memory_provenance import _is_closeout_companion_path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _canonical_entry() -> str:
    return (
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: test\n"
        "  commit: abc1234\n"
        "  commit_hash: abc1234\n"
        "  session_id: test-session\n"
        "  memory_binding: bound\n"
        "  test_evidence: test\n"
        "  next_step: none\n"
    )


def _canonical_bound_entry(commit: str) -> str:
    return (
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: closeout companion\n"
        f"  commit: {commit}\n"
        f"  commit_hash: {commit}\n"
        "  session_id: test-session\n"
        "  memory_binding: bound\n"
        "  test_evidence: NOT RUN: scope classification fixture\n"
        "  next_step: review\n"
        "  plan_reconciliation: not_applicable\n"
    )


def _init_git_repo(repo: Path) -> str:
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test User"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "seed"],
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_all(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", message],
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_closeout_companion_allowlist_is_narrow() -> None:
    cited = {"artifacts/evidence/test-results/custom-receipt.json"}

    assert _is_closeout_companion_path(
        "memory/2026-07-27.md",
        plan_updated=False,
        cited_artifacts=cited,
    )
    assert _is_closeout_companion_path(
        "PLAN.md",
        plan_updated=True,
        cited_artifacts=cited,
    )
    assert not _is_closeout_companion_path(
        "PLAN.md",
        plan_updated=False,
        cited_artifacts=cited,
    )
    assert _is_closeout_companion_path(
        "artifacts/evidence/test-results/receipt-session.json",
        plan_updated=False,
        cited_artifacts=cited,
    )
    assert _is_closeout_companion_path(
        "artifacts/runtime/closeouts/session.json",
        plan_updated=False,
        cited_artifacts=cited,
    )
    assert _is_closeout_companion_path(
        "artifacts/evidence/test-results/custom-receipt.json",
        plan_updated=False,
        cited_artifacts=cited,
    )
    assert not _is_closeout_companion_path(
        "CHANGELOG.md",
        plan_updated=False,
        cited_artifacts=cited,
    )
    assert not _is_closeout_companion_path(
        "artifacts/release/candidate.zip",
        plan_updated=False,
        cited_artifacts=cited,
    )


def test_blocks_current_diff_active_non_canonical_writer(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory" / "2026-06-12.md",
        "- memory_type: session-derived\n"
        "  what_changed: direct write\n"
        "  commit: abc1234\n",
    )

    result = check(tmp_path, changed_files=["memory/2026-06-12.md"])

    assert result.clean is False
    assert result.current_diff_active_non_canonical_writer_count == 1
    assert result.blockers == [
        {
            "code": "active_non_canonical_writer",
            "file": "memory/2026-06-12.md",
            "reason": "session_derived_entry_not_written_by_memory_record",
        }
    ]


def test_historical_active_debt_does_not_block_unrelated_diff(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory" / "2026-06-12.md",
        "- memory_type: session-derived\n"
        "  what_changed: direct write\n"
        "  commit: abc1234\n",
    )

    result = check(tmp_path, changed_files=["README.md"])

    assert result.clean is True
    assert result.active_non_canonical_writer_count == 1
    assert result.current_diff_active_non_canonical_writer_count == 0
    assert result.blockers == []


def test_clean_canonical_memory_diff_does_not_block(tmp_path: Path) -> None:
    _write(tmp_path / "memory" / "2026-06-12.md", _canonical_entry())

    result = check(tmp_path, changed_files=["memory/2026-06-12.md"])

    assert result.clean is True
    assert result.blockers == []
    assert result.current_diff_active_non_canonical_writer_count == 0


def test_historical_warning_window_does_not_block_current_diff(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory" / "2026-05-20.md",
        "- what_changed: legacy direct write\n"
        "  commit: abc1234\n",
    )

    result = check(tmp_path, changed_files=["memory/2026-05-20.md"])

    assert result.clean is True
    assert result.blockers == []
    assert result.current_diff_active_non_canonical_writer_count == 0


def test_ci_surfaces_test_evidence_provenance_warning_without_blocking(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "memory" / "2026-07-05.md",
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: provenance warning fixture\n"
        "  test_evidence: PASS: 67 passed\n"
        "  next_step: none\n",
    )

    result = check(tmp_path, changed_files=["memory/2026-07-05.md"])

    assert result.clean is True
    assert result.blockers == []
    assert "test_evidence_provenance_not_found=1" in result.warnings


def test_ci_reports_mixed_scope_binding_without_blocking(tmp_path: Path) -> None:
    seed = _init_git_repo(tmp_path)
    _write(tmp_path / "memory" / "2026-07-27.md", _canonical_bound_entry(seed))
    _write(tmp_path / "artifacts" / "release" / "cfu-candidate.zip", "fixture\n")
    mixed = _commit_all(tmp_path, "mixed CFU release and closeout")

    result = check(
        tmp_path,
        changed_files=[
            "memory/2026-07-27.md",
            "artifacts/release/cfu-candidate.zip",
        ],
        base_ref=seed,
        head_ref=mixed,
    )

    assert result.clean is True
    assert result.blockers == []
    assert "mixed_scope_memory_binding=1" in result.warnings
    assert result.mixed_scope_memory_binding_count == 1
    assert result.mixed_scope_findings[0]["enforcement"] == "report_only"
    assert result.mixed_scope_findings[0]["disallowed_paths"] == [
        "artifacts/release/cfu-candidate.zip"
    ]


def test_ci_accepts_product_commit_then_memory_closeout_commit(tmp_path: Path) -> None:
    seed = _init_git_repo(tmp_path)
    _write(tmp_path / "governance_tools" / "product_change.py", "VALUE = 1\n")
    product_commit = _commit_all(tmp_path, "product change")
    _write(
        tmp_path / "memory" / "2026-07-27.md",
        _canonical_bound_entry(product_commit),
    )
    closeout_commit = _commit_all(tmp_path, "memory closeout")

    result = check(
        tmp_path,
        changed_files=[
            "governance_tools/product_change.py",
            "memory/2026-07-27.md",
        ],
        base_ref=seed,
        head_ref=closeout_commit,
    )

    assert result.clean is True
    assert result.blockers == []
    assert "mixed_scope_memory_binding=1" not in result.warnings
    assert result.mixed_scope_memory_binding_count == 0
    assert result.mixed_scope_findings == []
    assert "closeout_companion_not_observed=1" not in result.warnings
    assert result.closeout_companion_not_observed_count == 0
    assert result.closeout_companion_findings == []


def test_ci_reports_product_range_without_new_closeout_companion(
    tmp_path: Path,
) -> None:
    seed = _init_git_repo(tmp_path)
    _write(
        tmp_path / "memory" / "2026-07-27.md",
        _canonical_bound_entry(seed),
    )
    base = _commit_all(tmp_path, "existing daily memory")
    _write(tmp_path / "governance_tools" / "product_change.py", "VALUE = 1\n")
    product_commit = _commit_all(tmp_path, "product change without closeout")

    result = check(
        tmp_path,
        changed_files=["governance_tools/product_change.py"],
        base_ref=base,
        head_ref=product_commit,
    )

    assert result.clean is True
    assert result.blockers == []
    assert "closeout_companion_not_observed=1" in result.warnings
    assert result.closeout_companion_not_observed_count == 1
    assert result.closeout_companion_findings == [
        {
            "code": "closeout_companion_not_observed",
            "enforcement": "report_only",
            "scope_ref": f"{base}..{product_commit}",
            "non_closeout_commits": [product_commit],
            "non_closeout_paths": ["governance_tools/product_change.py"],
            "observed_bound_commits": [],
            "reason": (
                "the inspected commit range changes non-closeout paths, but no "
                "added canonical memory entry binds a non-closeout commit in "
                "that range"
            ),
        }
    ]


def test_changed_file_list_without_refs_does_not_infer_closeout_gap(
    tmp_path: Path,
) -> None:
    result = check(
        tmp_path,
        changed_files=["governance_tools/product_change.py"],
    )

    assert result.clean is True
    assert result.blockers == []
    assert "closeout_companion_not_observed=1" not in result.warnings
    assert result.closeout_companion_not_observed_count == 0
    assert result.closeout_companion_findings == []


def test_ci_does_not_accept_closeout_entry_bound_outside_range(
    tmp_path: Path,
) -> None:
    seed = _init_git_repo(tmp_path)
    _write(tmp_path / "governance_tools" / "product_change.py", "VALUE = 1\n")
    product_commit = _commit_all(tmp_path, "product change")
    _write(
        tmp_path / "memory" / "2026-07-27.md",
        _canonical_bound_entry(seed),
    )
    closeout_commit = _commit_all(tmp_path, "misbound memory closeout")

    result = check(
        tmp_path,
        changed_files=[
            "governance_tools/product_change.py",
            "memory/2026-07-27.md",
        ],
        base_ref=seed,
        head_ref=closeout_commit,
    )

    assert result.clean is True
    assert result.blockers == []
    assert "closeout_companion_not_observed=1" in result.warnings
    assert result.closeout_companion_not_observed_count == 1
    assert result.closeout_companion_findings[0]["non_closeout_commits"] == [
        product_commit
    ]
    assert result.closeout_companion_findings[0]["observed_bound_commits"] == [
        seed
    ]
