"""F-J: F-7 replaces the protected AGENTS.base.md only through a controlled step.

The step verifies the pre-update hash, binds the new content to the framework
commit being adopted, and rewrites only the ``sha256.AGENTS.base.md`` line of
``.governance/baseline.yaml``.  Every test here drives the real updater against
a local Git framework repository and a synthetic submodule consumer.
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from unittest import mock

import pytest

import governance_tools.external_governance_submodule_updater as updater_module
import governance_tools.f7_full_update as f7_full_update
import governance_tools.protected_base_sync as sync_module
from governance_tools.external_governance_submodule_updater import (
    _git_env,
    _refresh_repo_local_instructions,
    format_human,
    update_governance_submodule,
)
from governance_tools.governance_drift_checker import check_governance_drift
from governance_tools.protected_file_hash import sha256_canonical_lf_bytes

BASE_V1 = "# AGENTS.base.md\n<!-- governance-baseline: protected -->\nrule v1\n"
BASE_V2 = "# AGENTS.base.md\n<!-- governance-baseline: protected -->\nrule v2\nnew rule\n"
STALE = "0" * 63 + "1"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_env(),
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _h(text: str) -> str:
    return sha256_canonical_lf_bytes(text.encode("utf-8"))


def _write_framework(framework: Path, base_text: str) -> None:
    baseline = framework / "baselines" / "repo-min"
    baseline.mkdir(parents=True, exist_ok=True)
    (baseline / "AGENTS.base.md").write_bytes(base_text.encode("utf-8"))
    (baseline / "AGENTS.md").write_text(
        "# AGENTS.md\n\n## AI Governance Update Intent Rule\n\nintent rule\n\n"
        "## Repo-Specific Risk Levels\n\nN/A\n",
        encoding="utf-8",
    )
    hooks = framework / "scripts" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / "pre-commit").write_text(
        "#!/usr/bin/env bash\n# pre-commit hook — AI Governance Framework\n"
        'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"\n',
        encoding="utf-8",
    )
    (hooks / "pre-push").write_text("#!/usr/bin/env bash\n# pre-push\n", encoding="utf-8")


def _baseline_bytes(*, base_hash: str, plan: str, contract: str, agents: str) -> bytes:
    # Same layout adopt_governance writes, with CRLF line endings and a BOM-free
    # trailer so a byte-exact comparison also covers line endings.
    lines = [
        "# .governance/baseline.yaml",
        "# Written by governance_tools/adopt_governance.py — do not edit manually.",
        "",
        'schema_version: "1"',
        "baseline_version: v1.2.0",
        "source_commit: " + "a" * 40,
        "framework_root: ../ai-governance-framework",
        "initialized_at: 2026-10-01T00:00:00+00:00",
        "initialized_by: governance_tools/adopt_governance.py",
        "",
        "# sha256.<file>: canonical-LF hash recorded at init/refresh time",
        f"sha256.AGENTS.base.md: {base_hash}",
        f"sha256.PLAN.md: {plan}",
        f"sha256.contract.yaml: {contract}",
        f"sha256.AGENTS.md: {agents}",
        "overridable.AGENTS.base.md: protected",
        "overridable.PLAN.md: overridable",
        "overridable.contract.yaml: overridable",
        "overridable.AGENTS.md: overridable",
        "",
        "plan_section_inventory:",
        '  - "## Current Phase"',
        "",
    ]
    return "\r\n".join(lines).encode("utf-8")


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(updater_module, "_governance_maturity_stage", lambda *_a: {})
    monkeypatch.setattr(f7_full_update, "_governance_maturity_stage", lambda *_a: {})


def _make_consumer(
    tmp_path: Path,
    *,
    with_baseline: bool = True,
    stale_other_hashes: bool = False,
) -> tuple[Path, Path, str, str]:
    framework = tmp_path / "fw"
    consumer = tmp_path / "c"
    _init_repo(framework)
    _write_framework(framework, BASE_V1)
    v1 = _commit_all(framework, "framework v1")
    _write_framework(framework, BASE_V2)
    v2 = _commit_all(framework, "framework v2: new AGENTS.base.md")

    _init_repo(consumer)
    _git(consumer, "-c", "protocol.file.allow=always", "submodule", "add", str(framework),
         "ai-governance-framework")
    _git(consumer / "ai-governance-framework", "checkout", v1)
    (consumer / "AGENTS.base.md").write_bytes(BASE_V1.encode("utf-8"))
    plan = "# PLAN\n\n## Current Phase\n\nwork\n"
    contract = "name: c\nframework_interface_version: \"1\"\n"
    agents = "# AGENTS.md\n\n## AI Governance Update Intent Rule\n\nold\n\n## Repo-Specific Risk Levels\n\nN/A\n"
    (consumer / "PLAN.md").write_bytes(plan.encode("utf-8"))
    (consumer / "contract.yaml").write_bytes(contract.encode("utf-8"))
    (consumer / "AGENTS.md").write_bytes(agents.encode("utf-8"))
    if with_baseline:
        others = (STALE, STALE, STALE) if stale_other_hashes else (_h(plan), _h(contract), _h(agents))
        (consumer / ".governance").mkdir()
        (consumer / ".governance" / "baseline.yaml").write_bytes(
            _baseline_bytes(base_hash=_h(BASE_V1), plan=others[0], contract=others[1], agents=others[2])
        )
    _commit_all(consumer, "pin framework v1")
    return consumer, framework, v1, v2


def _baseline(consumer: Path) -> Path:
    return consumer / ".governance" / "baseline.yaml"


def _journal(consumer: Path) -> Path:
    return consumer / ".git" / sync_module.JOURNAL_NAME


def _apply(consumer: Path, **kwargs):
    return update_governance_submodule(repo=consumer, fetch_ref="main", dry_run=False, **kwargs)


# --- (a) authorized update syncs exactly the BASE hash ----------------------


def test_a_update_syncs_base_and_its_hash_and_reports_item(tmp_path: Path, fast) -> None:
    consumer, framework, v1, v2 = _make_consumer(tmp_path)
    before = _baseline(consumer).read_bytes()

    result = _apply(consumer)

    assert result.ok is True, result.errors
    assert result.after_head == v2
    assert (consumer / "AGENTS.base.md").read_text(encoding="utf-8") == BASE_V2
    after = _baseline(consumer).read_bytes()
    assert after == before.replace(
        f"sha256.AGENTS.base.md: {_h(BASE_V1)}".encode(),
        f"sha256.AGENTS.base.md: {_h(BASE_V2)}".encode(),
    )
    drift = check_governance_drift(consumer, framework_root=consumer / "ai-governance-framework")
    assert drift.checks["protected_files_unmodified"] is True
    stage = result.full_update_stage_report
    assert stage["protected_hash_sync"] == "synced"
    assert stage["final_status"] != "blocked"
    item = asdict(result)["full_update_stage_report"]["details"]["protected_hash_sync"]
    assert item["old_hash"] == _h(BASE_V1)
    assert item["new_hash"] == _h(BASE_V2)
    assert item["framework_commit"] == v2
    assert item["file"] == "AGENTS.base.md"
    assert item["changed_files"] == ["AGENTS.base.md", ".governance/baseline.yaml"]
    rendered = format_human(result)
    assert "- protected_hash_sync=synced" in rendered
    assert "[protected_hash_sync]" in rendered
    assert f"old_hash={_h(BASE_V1)}" in rendered
    assert f"new_hash={_h(BASE_V2)}" in rendered
    assert f"framework_commit={v2}" in rendered
    assert not _journal(consumer).exists()


def test_a_stage_mode_stages_baseline_with_base(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)

    result = _apply(consumer, stage=True)

    assert result.ok is True, result.errors
    assert ".governance/baseline.yaml" in result.staged_files
    assert "AGENTS.base.md" in result.staged_files


def test_a_f7_reports_protected_hash_sync_as_own_item(tmp_path: Path, fast, monkeypatch) -> None:
    consumer, framework, _v1, v2 = _make_consumer(tmp_path)
    monkeypatch.setattr(
        f7_full_update,
        "install_governance_hooks",
        mock.Mock(return_value=mock.Mock(ok=True, changed_files=[], backups=[], errors=[], warnings=[])),
    )

    result = f7_full_update.run_f7_full_update(
        repo_root=consumer, framework_root=consumer / "ai-governance-framework", apply=True
    )

    assert result.stages["protected_hash_sync"] == "synced"
    assert ".governance/baseline.yaml" in result.changed_files
    payload = json.loads(json.dumps(asdict(result), default=str))
    item = payload["stages"]["details"]["protected_hash_sync"]
    assert (item["old_hash"], item["new_hash"], item["framework_commit"]) == (
        _h(BASE_V1), _h(BASE_V2), v2,
    )
    rendered = f7_full_update.format_human(result)
    assert "[protected_hash_sync]" in rendered
    assert f"framework_commit={v2}" in rendered


# --- (b) unknown pre-existing mismatch -> HOLD ------------------------------


def test_b_preexisting_mismatch_holds_and_rewrites_nothing(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    tampered = BASE_V1 + "consumer edit\n"
    (consumer / "AGENTS.base.md").write_bytes(tampered.encode("utf-8"))
    _commit_all(consumer, "unknown edit to protected file")
    base_before = (consumer / "AGENTS.base.md").read_bytes()
    baseline_before = _baseline(consumer).read_bytes()

    result = _apply(consumer)

    assert result.ok is False
    assert (consumer / "AGENTS.base.md").read_bytes() == base_before
    assert _baseline(consumer).read_bytes() == baseline_before
    stage = result.full_update_stage_report
    assert stage["protected_hash_sync"] == "hold"
    assert stage["final_status"] == "blocked"
    assert any("pre-existing AGENTS.base.md hash mismatch" in e for e in result.errors)
    assert result.staged_files == [] and result.committed is False
    assert "protected_hash_sync=hold" in format_human(result)


def test_b_f7_hold_is_not_full_completion(tmp_path: Path, fast, monkeypatch) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    (consumer / "AGENTS.base.md").write_bytes((BASE_V1 + "x\n").encode("utf-8"))
    _commit_all(consumer, "unknown edit")
    monkeypatch.setattr(
        f7_full_update,
        "install_governance_hooks",
        mock.Mock(return_value=mock.Mock(ok=True, changed_files=[], backups=[], errors=[], warnings=[])),
    )

    result = f7_full_update.run_f7_full_update(
        repo_root=consumer, framework_root=consumer / "ai-governance-framework", apply=True
    )

    assert result.ok is False
    assert result.f7_final_status == "blocked"
    assert result.stages["protected_hash_sync"] == "hold"


def test_b_unproven_half_state_without_journal_holds(tmp_path: Path, fast) -> None:
    """The F6 state: BASE already replaced by an unsynced update, hash still old."""
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    (consumer / "AGENTS.base.md").write_bytes(BASE_V2.encode("utf-8"))
    _commit_all(consumer, "earlier F-7 replaced BASE without the hash")
    baseline_before = _baseline(consumer).read_bytes()

    result = _apply(consumer)

    assert result.ok is False
    assert _baseline(consumer).read_bytes() == baseline_before
    assert result.full_update_stage_report["protected_hash_sync"] == "hold"
    assert any("cannot be proven" in e for e in result.errors)


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda b: b.replace(b"sha256.AGENTS.base.md:", b"sha256.AGENTS_base:"), "no sha256.AGENTS.base.md line"),
        (lambda b: b + b"sha256.AGENTS.base.md: " + b"f" * 64 + b"\r\n", "lines"),
    ],
    ids=["missing_line", "duplicated_line"],
)
def test_b_malformed_baseline_holds(tmp_path: Path, fast, mutate, expected) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    _baseline(consumer).write_bytes(mutate(_baseline(consumer).read_bytes()))
    _commit_all(consumer, "baseline edited")
    base_before = (consumer / "AGENTS.base.md").read_bytes()
    baseline_before = _baseline(consumer).read_bytes()

    result = _apply(consumer)

    assert result.ok is False
    assert (consumer / "AGENTS.base.md").read_bytes() == base_before
    assert _baseline(consumer).read_bytes() == baseline_before
    assert result.full_update_stage_report["protected_hash_sync"] == "hold"
    assert any(expected in e for e in result.errors)


def test_b_unbound_source_holds(tmp_path: Path, fast) -> None:
    consumer, framework, _v1, _v2 = _make_consumer(tmp_path)
    checkout = consumer / "ai-governance-framework"
    _git(checkout, "checkout", "main")
    (checkout / "baselines/repo-min/AGENTS.base.md").write_text("# not the commit\n", encoding="utf-8")
    base_before = (consumer / "AGENTS.base.md").read_bytes()
    baseline_before = _baseline(consumer).read_bytes()

    report = _refresh_repo_local_instructions(consumer, checkout)

    assert (consumer / "AGENTS.base.md").read_bytes() == base_before
    assert _baseline(consumer).read_bytes() == baseline_before
    assert report["status"] == "blocked"
    assert report["protected_hash_sync"]["status"] == "hold"


# --- (c) other hashes are never refreshed ------------------------------------


def test_c_other_stale_hash_lines_stay_byte_identical(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path, stale_other_hashes=True)
    before = _baseline(consumer).read_bytes()

    result = _apply(consumer)

    after = _baseline(consumer).read_bytes()
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    assert len(before_lines) == len(after_lines)
    changed = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
    assert len(changed) == 1
    assert after_lines[changed[0]] == f"sha256.AGENTS.base.md: {_h(BASE_V2)}\r\n".encode()
    for key in (b"sha256.PLAN.md", b"sha256.contract.yaml", b"sha256.AGENTS.md"):
        assert [l for l in after_lines if l.startswith(key)] == [
            key + b": " + STALE.encode() + b"\r\n"
        ]
    assert result.full_update_stage_report["protected_hash_sync"] == "synced", result.errors


# --- (d) idempotent ----------------------------------------------------------


def test_d_same_version_twice_makes_no_baseline_diff(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    first = _apply(consumer)
    assert first.full_update_stage_report["protected_hash_sync"] == "synced", first.errors
    _commit_all(consumer, "commit F-7 result")
    after_first = _baseline(consumer).read_bytes()
    base_after_first = (consumer / "AGENTS.base.md").read_bytes()

    second = _apply(consumer)

    assert second.ok is True, second.errors
    assert second.update_mode == "already_current"
    assert second.full_update_stage_report["protected_hash_sync"] == "verified"
    assert _baseline(consumer).read_bytes() == after_first
    assert (consumer / "AGENTS.base.md").read_bytes() == base_after_first


# --- (e) interruption --------------------------------------------------------


def test_e_failure_between_base_and_baseline_write_restores(tmp_path: Path, fast, monkeypatch) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    base_before = (consumer / "AGENTS.base.md").read_bytes()
    baseline_before = _baseline(consumer).read_bytes()

    def boom(_path, _payload):
        raise OSError("injected: crash before baseline write")

    monkeypatch.setattr(sync_module, "_write_baseline_bytes", boom)
    result = _apply(consumer)

    assert (consumer / "AGENTS.base.md").read_bytes() == base_before
    assert _baseline(consumer).read_bytes() == baseline_before
    assert result.ok is False
    assert result.full_update_stage_report["protected_hash_sync"] == "failed_restored"
    assert result.full_update_stage_report["final_status"] == "blocked"
    assert not _journal(consumer).exists()


def test_e_failure_inside_baseline_write_restores(tmp_path: Path, fast, monkeypatch) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    base_before = (consumer / "AGENTS.base.md").read_bytes()
    baseline_before = _baseline(consumer).read_bytes()

    def partial(path, payload):
        path.write_bytes(payload[: len(payload) // 2])
        raise OSError("injected: torn baseline write")

    monkeypatch.setattr(sync_module, "_write_baseline_bytes", partial)
    result = _apply(consumer)

    assert (consumer / "AGENTS.base.md").read_bytes() == base_before
    assert _baseline(consumer).read_bytes() == baseline_before
    assert result.ok is False
    assert result.full_update_stage_report["protected_hash_sync"] == "failed_restored"


def test_e_failed_restore_is_detected_and_next_run_fails_closed(
    tmp_path: Path, fast, monkeypatch
) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    baseline_before = _baseline(consumer).read_bytes()

    def boom(_path, _payload):
        raise OSError("injected")

    monkeypatch.setattr(sync_module, "_write_baseline_bytes", boom)
    monkeypatch.setattr(sync_module, "_restore_bytes", boom)
    first = _apply(consumer)

    assert first.ok is False
    assert first.full_update_stage_report["protected_hash_sync"] == "incomplete"
    assert _journal(consumer).exists()
    # Half-done: BASE at the new source, baseline hash still old.
    assert (consumer / "AGENTS.base.md").read_text(encoding="utf-8") == BASE_V2
    assert _baseline(consumer).read_bytes() == baseline_before

    monkeypatch.undo()
    monkeypatch.setattr(updater_module, "_governance_maturity_stage", lambda *_a: {})
    base_mid = (consumer / "AGENTS.base.md").read_bytes()
    second = _apply(consumer)

    assert second.ok is False
    assert any("protected-hash sync incomplete" in e for e in second.errors)
    assert second.full_update_stage_report["protected_hash_sync"] == "incomplete"
    assert second.full_update_stage_report["final_status"] == "blocked"
    assert (consumer / "AGENTS.base.md").read_bytes() == base_mid
    assert _baseline(consumer).read_bytes() == baseline_before
    assert _journal(consumer).exists()


def test_e_stale_journal_with_original_files_is_cleared(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    base = (consumer / "AGENTS.base.md").read_bytes()
    baseline = _baseline(consumer).read_bytes()
    _journal(consumer).write_text(
        json.dumps(
            {
                "new_hash": _h(BASE_V2),
                "expected_baseline_sha256": hashlib.sha256(b"x").hexdigest(),
                "original_base_b64": base64.b64encode(base).decode(),
                "original_baseline_b64": base64.b64encode(baseline).decode(),
            }
        ),
        encoding="utf-8",
    )

    result = _apply(consumer)

    assert result.full_update_stage_report["protected_hash_sync"] == "synced", result.errors
    assert not _journal(consumer).exists()


# --- no baseline.yaml: unchanged behaviour ----------------------------------


def test_no_baseline_yaml_keeps_plain_replacement(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path, with_baseline=False)

    result = _apply(consumer)

    assert result.ok is True, result.errors
    assert (consumer / "AGENTS.base.md").read_text(encoding="utf-8") == BASE_V2
    assert not _baseline(consumer).exists()
    item = result.full_update_stage_report["details"]["protected_hash_sync"]
    # F-J 1A: compatible replacement, named for what it is.
    assert item["status"] == "UNPROTECTED_BASE_REPLACEMENT"
    assert "NOT verified against a protected hash" in item["reason"]


# --- review fixes -------------------------------------------------------------

STOP = "Do not run adopt_governance --refresh and do not edit the hash by hand"


def _tamper(consumer: Path) -> None:
    (consumer / "AGENTS.base.md").write_bytes((BASE_V1 + "unknown edit\n").encode("utf-8"))
    _commit_all(consumer, "unknown edit to protected file")


def test_fix1_sync_resolves_checkout_owned_by_another_user(
    tmp_path: Path, fast, monkeypatch
) -> None:
    consumer, _framework, _v1, v2 = _make_consumer(tmp_path)
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")

    result = _apply(consumer)

    assert result.after_head == v2
    item = result.full_update_stage_report["details"]["protected_hash_sync"]
    assert item["status"] == "synced", item["reason"]
    assert (consumer / "AGENTS.base.md").read_text(encoding="utf-8") == BASE_V2


def test_fix2_hold_message_says_files_untouched(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    _tamper(consumer)

    result = _apply(consumer)

    assert "left untouched" in result.message


def test_fix2_failed_restored_message_says_written_then_restored(
    tmp_path: Path, fast, monkeypatch
) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)

    def boom(_path, _payload):
        raise OSError("injected")

    monkeypatch.setattr(sync_module, "_write_baseline_bytes", boom)
    result = _apply(consumer)

    assert "written and then restored to their pre-sync bytes" in result.message
    assert "left untouched" not in result.message


def test_fix2_incomplete_message_reports_disk_state_and_journal(
    tmp_path: Path, fast, monkeypatch
) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)

    def boom(_path, _payload):
        raise OSError("injected")

    monkeypatch.setattr(sync_module, "_write_baseline_bytes", boom)
    monkeypatch.setattr(sync_module, "_restore_bytes", boom)
    result = _apply(consumer)

    assert "left untouched" not in result.message
    assert "AGENTS.base.md=authorized_source" in result.message
    assert ".governance/baseline.yaml=original" in result.message
    assert f"journal kept at {_journal(consumer)}" in result.message
    item = result.full_update_stage_report["details"]["protected_hash_sync"]
    assert item["incomplete_state"] == {"agents_base": "authorized_source", "baseline": "original"}


def test_fix3_hold_does_not_write_an_updated_receipt(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    _tamper(consumer)
    receipt = consumer / "governance" / ".update-receipt.json"
    assert not receipt.exists()

    result = _apply(consumer)

    assert not receipt.exists()
    assert result.update_receipt["status"] == "not_written"
    assert "protected-hash sync hold" in result.update_receipt["reason"]


def test_fix4_hold_tells_the_agent_to_stop(tmp_path: Path, fast, monkeypatch) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)
    _tamper(consumer)
    monkeypatch.setattr(
        f7_full_update,
        "install_governance_hooks",
        mock.Mock(return_value=mock.Mock(ok=True, changed_files=[], backups=[], errors=[], warnings=[])),
    )

    result = f7_full_update.run_f7_full_update(
        repo_root=consumer, framework_root=consumer / "ai-governance-framework", apply=True
    )

    item = result.stages["details"]["protected_hash_sync"]
    assert STOP in item["reason"]
    assert STOP in item["operator_instruction"]
    assert any(STOP in error for error in result.errors)
    assert STOP in f7_full_update.format_human(result)
    assert "hand this HOLD to the owner" in json.dumps(asdict(result), default=str)


def test_fix4_incomplete_next_run_tells_the_agent_to_stop(
    tmp_path: Path, fast, monkeypatch
) -> None:
    consumer, _framework, _v1, _v2 = _make_consumer(tmp_path)

    def boom(_path, _payload):
        raise OSError("injected")

    monkeypatch.setattr(sync_module, "_write_baseline_bytes", boom)
    monkeypatch.setattr(sync_module, "_restore_bytes", boom)
    first = _apply(consumer)
    monkeypatch.undo()
    monkeypatch.setattr(updater_module, "_governance_maturity_stage", lambda *_a: {})

    second = _apply(consumer)

    assert STOP in first.message
    assert STOP in format_human(first)
    assert any(STOP in error for error in second.errors)
    assert STOP in format_human(second)


def test_fix5_head_not_at_framework_commit_holds(tmp_path: Path, fast) -> None:
    consumer, framework, _v1, v2 = _make_consumer(tmp_path)
    # v3 changes nothing under baselines/, so the checked-out source still
    # equals the v2 blob: only the HEAD binding can tell the two commits apart.
    (framework / "README.md").write_text("v3\n", encoding="utf-8")
    v3 = _commit_all(framework, "framework v3: README only")
    checkout = consumer / "ai-governance-framework"
    _git(checkout, "fetch", "-q", "origin")
    _git(checkout, "checkout", "-q", v3)
    base_before = (consumer / "AGENTS.base.md").read_bytes()
    baseline_before = _baseline(consumer).read_bytes()

    report = _refresh_repo_local_instructions(consumer, checkout, framework_commit=v2)

    assert (consumer / "AGENTS.base.md").read_bytes() == base_before
    assert _baseline(consumer).read_bytes() == baseline_before
    assert report["protected_hash_sync"]["status"] == "hold"
    assert "is not the authorized framework commit" in report["protected_hash_sync"]["reason"]


# --- 1A: no baseline.yaml -> UNPROTECTED_BASE_REPLACEMENT, still source-bound --

UNPROTECTED = "UNPROTECTED_BASE_REPLACEMENT"


def _drop_baseline_fixture(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """A consumer without baseline.yaml whose BASE is the v1 framework blob."""
    return _make_consumer(tmp_path, with_baseline=False)


# compatibility (positive)


def test_1a_compat_base_equal_to_previous_pin_blob_is_replaced_and_reported_unprotected(
    tmp_path: Path, fast
) -> None:
    consumer, _framework, v1, v2 = _drop_baseline_fixture(tmp_path)

    result = _apply(consumer)

    assert (consumer / "AGENTS.base.md").read_text(encoding="utf-8") == BASE_V2
    item = result.full_update_stage_report["details"]["protected_hash_sync"]
    assert item["status"] == UNPROTECTED
    assert result.full_update_stage_report["protected_hash_sync"] == UNPROTECTED
    assert (item["framework_commit"], item["previous_commit"]) == (v2, v1)
    assert item["new_hash"] == _h(BASE_V2) and item["old_hash"] == _h(BASE_V1)
    assert "NOT verified against a protected hash" in item["reason"]
    assert "NOT verified against a protected hash" in item["claim_boundary"]
    rendered = format_human(result)
    assert f"- protected_hash_sync={UNPROTECTED}" in rendered
    assert f"status={UNPROTECTED}" in rendered
    assert "status=verified" not in rendered and "status=synced" not in rendered
    payload = json.dumps(asdict(result), default=str)
    assert UNPROTECTED in payload


def test_1a_compat_first_install_without_base_is_unprotected(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _drop_baseline_fixture(tmp_path)
    _git(consumer, "rm", "-q", "AGENTS.base.md")
    _git(consumer, "commit", "-q", "-m", "no AGENTS.base.md yet")

    result = _apply(consumer)

    assert (consumer / "AGENTS.base.md").read_text(encoding="utf-8") == BASE_V2
    assert result.full_update_stage_report["protected_hash_sync"] == UNPROTECTED


# strict (negative)


def test_1a_no_baseline_dirty_base_holds(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, v2 = _drop_baseline_fixture(tmp_path)
    checkout = consumer / "ai-governance-framework"
    _git(checkout, "checkout", "-q", v2)
    (consumer / "AGENTS.base.md").write_bytes((BASE_V1 + "uncommitted edit\n").encode("utf-8"))
    before = (consumer / "AGENTS.base.md").read_bytes()

    report = _refresh_repo_local_instructions(
        consumer, checkout, framework_commit=v2, previous_commit=_v1
    )

    assert (consumer / "AGENTS.base.md").read_bytes() == before
    item = report["protected_hash_sync"]
    assert item["status"] == "hold"
    assert "uncommitted local changes" in item["reason"]
    assert STOP in item["reason"]


def test_1a_no_baseline_committed_custom_base_holds(tmp_path: Path, fast) -> None:
    consumer, _framework, _v1, _v2 = _drop_baseline_fixture(tmp_path)
    custom = BASE_V1 + "consumer rule committed on purpose\n"
    (consumer / "AGENTS.base.md").write_bytes(custom.encode("utf-8"))
    _commit_all(consumer, "custom AGENTS.base.md")
    before = (consumer / "AGENTS.base.md").read_bytes()

    result = _apply(consumer)

    assert (consumer / "AGENTS.base.md").read_bytes() == before
    assert result.ok is False
    assert result.full_update_stage_report["protected_hash_sync"] == "hold"
    assert result.full_update_stage_report["final_status"] == "blocked"
    assert any("differs from the framework source at the previous pin" in e for e in result.errors)
    assert STOP in format_human(result)


@pytest.mark.parametrize("previous", [None, "0" * 40], ids=["unknown_pin", "pin_blob_unavailable"])
def test_1a_no_baseline_undeterminable_previous_pin_holds(tmp_path: Path, fast, previous) -> None:
    consumer, _framework, _v1, v2 = _drop_baseline_fixture(tmp_path)
    checkout = consumer / "ai-governance-framework"
    _git(checkout, "checkout", "-q", v2)
    before = (consumer / "AGENTS.base.md").read_bytes()

    report = _refresh_repo_local_instructions(
        consumer, checkout, framework_commit=v2, previous_commit=previous
    )

    assert (consumer / "AGENTS.base.md").read_bytes() == before
    assert report["protected_hash_sync"]["status"] == "hold"
    assert report["status"] == "blocked"


def test_1a_no_baseline_unbound_source_holds(tmp_path: Path, fast) -> None:
    consumer, _framework, v1, _v2 = _drop_baseline_fixture(tmp_path)
    checkout = consumer / "ai-governance-framework"
    (checkout / "baselines/repo-min/AGENTS.base.md").write_text("# not the commit\n", encoding="utf-8")
    before = (consumer / "AGENTS.base.md").read_bytes()

    report = _refresh_repo_local_instructions(
        consumer, checkout, framework_commit=v1, previous_commit=v1
    )

    assert (consumer / "AGENTS.base.md").read_bytes() == before
    assert report["protected_hash_sync"]["status"] == "hold"
    assert "refusing an unbound source" in report["protected_hash_sync"]["reason"]
