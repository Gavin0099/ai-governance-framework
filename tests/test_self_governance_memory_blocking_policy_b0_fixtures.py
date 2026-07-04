"""B0 mutation fixtures for the memory blocking policy RFC.

Contract: docs/governance/self-governance-memory-blocking-policy-rfc-2026-07-04.md

These fixtures pin both sides of the B0 claim boundary:

* raw `memory_authority_guard` default behavior stays report-only;
* policy-backed `memory_workflow` / CI consumers selectively block
  `session_like_non_session_memory_type` when `governance/memory_blocking_policy.json`
  enables it.

Scenarios that remain intentionally report-only are pinned as such so future
enforcement changes require a conscious test update instead of a silent claim
upgrade.

Scenario map (RFC "Mutation Contract Required Before The Switch"):
  1. prose rewording           -> still detected (field-based, not prose-based)
  2. novel memory_type value   -> still detected
  3. pre-window file append    -> detected WITH diff context (changed_files);
                                  still missed without diff context (residual)
  4. hook bypass / CI parity   -> policy-backed workflow and CI block B0
  5. authority_override field  -> default guard inert; policy mode downgrades
  6. kill switch               -> raw guard default remains Phase 1 semantics
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.ci_memory_workflow_check import check as ci_check
from governance_tools.memory_authority_guard import (
    _ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM,
    load_blocking_policy,
    main,
    run_guard,
)
from governance_tools.memory_workflow import assess_memory_workflow

B0_CODE = "session_like_non_session_memory_type"

_IN_WINDOW_FILENAME = f"{_ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM}.md"
_PRE_WINDOW_FILENAME = "2026-01-01.md"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework_surface(repo: Path) -> None:
    _write(repo / "governance" / "MEMORY_PROTOCOL.md", "# Memory Protocol\n")
    _write(repo / "governance_tools" / "memory_record.py", "# writer\n")
    _write(repo / "governance_tools" / "memory_authority_guard.py", "# guard\n")


def _write_memory(repo: Path, filename: str, entry: str) -> None:
    _write(repo / "memory" / filename, entry)


def _b0_counts(repo: Path) -> dict[str, int]:
    result = run_guard(repo / "memory", repo, skip_git=True)
    return result["violation_counts_by_code"]


def test_b0_scenario1_prose_rewording_does_not_evade_detection(tmp_path: Path) -> None:
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: routine observations captured for later reference\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    assert _b0_counts(tmp_path)[B0_CODE] == 1


def test_b0_scenario1_minimal_session_field_residue_still_detected(tmp_path: Path) -> None:
    # Aggressive rewording: all anchors and evidence removed, only a single
    # session-shaped field (next_step) survives. Detection is field-based,
    # so one residue field is enough.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  what_changed: informal working notes, nothing session related here\n"
        "  next_step: continue tomorrow\n",
    )

    assert _b0_counts(tmp_path)[B0_CODE] == 1


def test_b0_scenario2_novel_memory_type_value_does_not_evade_detection(tmp_path: Path) -> None:
    # memory_type values are not matched against an allowlist; any non-session
    # value with session-shaped fields must keep triggering.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: reflection_shard\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: session entry hidden behind an invented type\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    assert _b0_counts(tmp_path)[B0_CODE] == 1


_PRE_WINDOW_B0_ENTRY = (
    "- memory_type: note\n"
    "  record_format_version: 1.0\n"
    "  writer: manual.editor\n"
    "  what_changed: session entry backdated into a pre-window file\n"
    "  commit: deadbee\n"
    "  memory_binding: bound\n"
    "  test_evidence: not relevant\n"
    "  next_step: none\n"
)


def test_b0_scenario3_pre_window_file_append_still_evades_full_scan(tmp_path: Path) -> None:
    # DOCUMENTED RESIDUAL: without diff context the active window is still
    # classified by daily filename date, so a backdated session-shaped entry
    # in a pre-window file is not reported by a bare full scan. This is also
    # the backcompat guarantee: untouched historical pre-window entries stay
    # silent. The bypass is closed only at the diff-aware surfaces below.
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    assert B0_CODE not in _b0_counts(tmp_path)


def test_b0_scenario3_modified_pre_window_file_detected_with_diff_context(tmp_path: Path) -> None:
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    result = run_guard(
        tmp_path / "memory",
        tmp_path,
        skip_git=True,
        changed_files=[f"memory/{_PRE_WINDOW_FILENAME}"],
    )

    assert result["violation_counts_by_code"][B0_CODE] == 1
    violation = [v for v in result["violations"] if v["code"] == B0_CODE][0]
    assert violation["reason"].startswith(
        "non_session_memory_type_with_session_fields_in_modified_pre_window_file:"
    )
    # Report-only semantics survive the new detection path.
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []
    assert result["claim_ceiling"] == "report_only_phase1"


def test_b0_scenario3_unrelated_diff_leaves_pre_window_history_silent(tmp_path: Path) -> None:
    # Backcompat: pre-window debt on disk is not reclassified just because
    # some other file changed.
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    result = run_guard(
        tmp_path / "memory",
        tmp_path,
        skip_git=True,
        changed_files=["docs/unrelated.md", "memory/00_long_term.md"],
    )

    assert B0_CODE not in result["violation_counts_by_code"]


def test_b0_scenario3_in_window_file_in_diff_is_not_double_counted(tmp_path: Path) -> None:
    # The regular daily scan already covers in-window files; the diff-aware
    # pass must skip them so one entry never yields two violations.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: in-window entry present in the diff\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    result = run_guard(
        tmp_path / "memory",
        tmp_path,
        skip_git=True,
        changed_files=[f"memory/{_IN_WINDOW_FILENAME}"],
    )

    assert result["violation_counts_by_code"][B0_CODE] == 1


def test_b0_scenario3_innocent_edit_of_legacy_file_surfaces_existing_debt(tmp_path: Path) -> None:
    # KNOWN NOISE CLASS (review finding, carried forward): the diff-aware pass
    # is a whole-file scan, not hunk-level append detection. Any modification
    # to a pre-window file — including an innocent typo fix — surfaces every
    # legacy B0-shaped entry already in that file. "Historical debt stays
    # silent" therefore means UNTOUCHED files only. Acceptable while
    # report-only; before B0 blocking may cover pre-window reasons, this must
    # be resolved (hunk-level detection or an explicit policy exclusion).
    legacy_entries = (
        "- memory_type: post-push\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: legacy entry one\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n"
        "- memory_type: implementation\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: legacy entry two\n"
        "  next_step: none\n"
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: legit session entry, not part of the noise class\n"
        "  commit: deadbee\n"
        "  next_step: none\n"
    )
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, legacy_entries)

    result = run_guard(
        tmp_path / "memory",
        tmp_path,
        skip_git=True,
        changed_files=[f"memory/{_PRE_WINDOW_FILENAME}"],
    )

    # Both legacy non-session entries surface, not just an appended one.
    assert result["violation_counts_by_code"][B0_CODE] == 2
    assert result["enforcement_action"] == "allow"


def test_b0_scenario3_guard_cli_accepts_changed_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Reviewer-facing surface parity: the guard CLI can replay the backdated
    # append detection with --changed-file, so verification does not require
    # going through the workflow or CI entrypoints.
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    with pytest.raises(SystemExit) as excinfo:
        main([
            "--memory-root", str(tmp_path / "memory"),
            "--project-root", str(tmp_path),
            "--skip-git",
            "--format", "json",
            "--changed-file", f"memory/{_PRE_WINDOW_FILENAME}",
        ])

    assert excinfo.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["violation_counts_by_code"][B0_CODE] == 1


def test_b0_scenario3_workflow_surface_reports_modified_pre_window_append(tmp_path: Path) -> None:
    # The pre-commit / CI entrypoint passes its diff context to the guard, so
    # the backdated append surfaces at the gate boundary, still report-only.
    _make_framework_surface(tmp_path)
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_PRE_WINDOW_FILENAME}"],
        run_guard_check=True,
    )

    assert workflow.guard_summary[B0_CODE] == 1
    assert B0_CODE in workflow.warnings
    assert workflow.blockers == []
    assert workflow.completion_claim_allowed is True


def test_b0_scenario4_guard_and_workflow_surfaces_report_same_verdict(tmp_path: Path) -> None:
    # Ownership rule: hook and CI must consume the same guard verdict. A hook
    # bypass via --no-verify is out of a test's reach, but surface parity is
    # not: the workflow entrypoint used by pre-commit and CI must report the
    # same B0 count as run_guard, and both must stay report-only.
    _make_framework_surface(tmp_path)
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: parity fixture entry\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    guard_counts = _b0_counts(tmp_path)
    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_IN_WINDOW_FILENAME}"],
        run_guard_check=True,
    )

    assert guard_counts[B0_CODE] == 1
    assert workflow.guard_summary[B0_CODE] == guard_counts[B0_CODE]
    assert B0_CODE in workflow.warnings
    assert workflow.blockers == []
    assert workflow.completion_claim_allowed is True


def test_b0_scenario5_authority_override_field_has_no_effect_in_phase1(tmp_path: Path) -> None:
    # The RFC defines authority_override as a future per-entry downgrade that
    # must emit authority_override_used. None of that exists yet: the field
    # must be inert, the violation still reported, and no override code
    # emitted. Implementing override semantics must consciously update this.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: override fixture entry\n"
        "  authority_override: reviewer-x pre-rfc-fixture\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    counts = _b0_counts(tmp_path)

    assert counts[B0_CODE] == 1
    assert "authority_override_used" not in counts


# ── RFC rollout step 3: selective blocking policy plumbing ───────────────────
# These tests exercise the direct policy input contract. Step 4 below verifies
# that workflow and CI consumers load the versioned policy file.


_IN_WINDOW_B0_ENTRY = (
    "- memory_type: note\n"
    "  record_format_version: 1.0\n"
    "  writer: manual.editor\n"
    "  what_changed: in-window session-shaped entry\n"
    "  commit: deadbee\n"
    "  memory_binding: bound\n"
    "  test_evidence: not relevant\n"
    "  next_step: none\n"
)


def test_policy_optin_b0_violation_blocks(tmp_path: Path) -> None:
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = run_guard(
        tmp_path / "memory", tmp_path, skip_git=True, blocking_codes=[B0_CODE]
    )

    assert result["ok"] is False
    assert result["ok_meaning"] == "guard_executed_selective_blocking_violation_present"
    assert result["enforcement_action"] == "block"
    assert result["blocking_violation_codes"] == [B0_CODE]
    assert result["claim_ceiling"] == "selective_blocking_phase2"
    assert "full_blocking_enforcement" in result["not_claimed"]
    assert result["blocking_policy"] == {
        "enabled_codes": [B0_CODE],
        "mode": "selective_blocking",
    }


def test_policy_optin_without_violation_allows(tmp_path: Path) -> None:
    (tmp_path / "memory").mkdir()

    result = run_guard(
        tmp_path / "memory", tmp_path, skip_git=True, blocking_codes=[B0_CODE]
    )

    assert result["ok"] is True
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []
    assert result["claim_ceiling"] == "selective_blocking_phase2"


def test_policy_optin_pre_window_reason_never_blocks(tmp_path: Path) -> None:
    # RFC backcompat: pre-activation-window content stays report-only even
    # under an enabled policy. This also guards the whole-file-scan noise
    # class: legacy entries surfaced by an innocent edit must not block.
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    result = run_guard(
        tmp_path / "memory",
        tmp_path,
        skip_git=True,
        changed_files=[f"memory/{_PRE_WINDOW_FILENAME}"],
        blocking_codes=[B0_CODE],
    )

    assert result["violation_counts_by_code"][B0_CODE] == 1
    assert result["ok"] is True
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []


def test_policy_optin_authority_override_downgrades_and_is_audited(tmp_path: Path) -> None:
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: overridden in-window entry\n"
        "  authority_override: reviewer-x accepted-scope-exception\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    result = run_guard(
        tmp_path / "memory", tmp_path, skip_git=True, blocking_codes=[B0_CODE]
    )

    assert result["ok"] is True
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []
    # The override is never silent: the original violation stays visible and
    # an audit record is added.
    assert result["violation_counts_by_code"][B0_CODE] == 1
    assert result["violation_counts_by_code"]["authority_override_used"] == 1
    audit = [
        v for v in result["violations"] if v["code"] == "authority_override_used"
    ][0]
    assert audit["reason"].startswith(f"downgraded_from:{B0_CODE}:")


def test_policy_optin_does_not_block_codes_outside_the_policy(tmp_path: Path) -> None:
    # An unbound entry fires unbound_memory, which is not in the enabled set;
    # selective blocking must not borrow enforcement for other codes.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: unbound session entry\n"
        "  commit: pending\n"
        "  next_step: none\n",
    )

    result = run_guard(
        tmp_path / "memory", tmp_path, skip_git=True, blocking_codes=[B0_CODE]
    )

    assert result["violation_counts_by_code"]["unbound_memory"] == 1
    assert result["ok"] is True
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []


def test_policy_optin_mixed_instances_keep_code_in_both_lists(tmp_path: Path) -> None:
    # One in-window B0 entry blocks; one pre-window B0 entry (surfaced via
    # diff context) stays report-only. The same code must appear in both
    # blocking_violation_codes and report_only_violation_codes, and only the
    # blocked instance carries the enforcement tag.
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)
    _write_memory(tmp_path, _PRE_WINDOW_FILENAME, _PRE_WINDOW_B0_ENTRY)

    result = run_guard(
        tmp_path / "memory",
        tmp_path,
        skip_git=True,
        changed_files=[f"memory/{_PRE_WINDOW_FILENAME}"],
        blocking_codes=[B0_CODE],
    )

    assert result["violation_counts_by_code"][B0_CODE] == 2
    assert result["blocking_violation_codes"] == [B0_CODE]
    assert B0_CODE in result["report_only_violation_codes"]
    b0_violations = [v for v in result["violations"] if v["code"] == B0_CODE]
    tags = sorted(str(v.get("enforcement")) for v in b0_violations)
    assert tags == ["None", "block"]


def test_policy_default_off_state_is_visible_in_output(tmp_path: Path) -> None:
    # Kill-switch visibility: a disabled policy must be readable from the
    # result so a disabled gate can never masquerade as a passing gate.
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = run_guard(tmp_path / "memory", tmp_path, skip_git=True)

    assert result["blocking_policy"] == {
        "enabled_codes": [],
        "mode": "report_only_default",
    }
    assert result["claim_ceiling"] == "report_only_phase1"


# ── RFC rollout step 4: versioned policy file wired into gate consumers ──────


def _write_policy(
    repo: Path,
    *,
    enabled: bool = True,
    codes: list[str] | None = None,
    schema: str = "memory_blocking_policy.v0.1",
    raw: str | None = None,
) -> None:
    path = repo / "governance" / "memory_blocking_policy.json"
    if raw is not None:
        _write(path, raw)
        return
    payload = {
        "policy_schema": schema,
        "enabled": enabled,
        "blocking_codes": codes if codes is not None else [B0_CODE],
    }
    _write(path, json.dumps(payload, indent=2) + "\n")


def test_policy_loader_missing_file_is_default_off(tmp_path: Path) -> None:
    policy = load_blocking_policy(tmp_path)

    assert policy == {
        "enabled_codes": [],
        "source": "default_off_no_policy_file",
        "error": None,
    }


def test_policy_loader_valid_file_enables_codes(tmp_path: Path) -> None:
    _write_policy(tmp_path, codes=[B0_CODE, B0_CODE, " "])

    policy = load_blocking_policy(tmp_path)

    assert policy["enabled_codes"] == [B0_CODE]
    assert policy["error"] is None


def test_policy_loader_enabled_false_is_kill_switch_without_error(tmp_path: Path) -> None:
    _write_policy(tmp_path, enabled=False)

    policy = load_blocking_policy(tmp_path)

    assert policy["enabled_codes"] == []
    assert policy["error"] is None


def test_policy_loader_invalid_file_disables_but_surfaces_error(tmp_path: Path) -> None:
    _write_policy(tmp_path, raw="{not json")

    policy = load_blocking_policy(tmp_path)

    assert policy["enabled_codes"] == []
    assert policy["error"] is not None
    assert policy["error"].startswith("blocking_policy_unreadable")


def test_policy_loader_schema_mismatch_disables_but_surfaces_error(tmp_path: Path) -> None:
    _write_policy(tmp_path, schema="memory_blocking_policy.v9.9")

    policy = load_blocking_policy(tmp_path)

    assert policy["enabled_codes"] == []
    assert policy["error"] == "blocking_policy_schema_mismatch"


def test_policy_loader_invalid_codes_disable_but_surface_error(tmp_path: Path) -> None:
    _write_policy(tmp_path, raw=json.dumps({
        "policy_schema": "memory_blocking_policy.v0.1",
        "enabled": True,
        "blocking_codes": "session_like_non_session_memory_type",
    }))

    policy = load_blocking_policy(tmp_path)

    assert policy["enabled_codes"] == []
    assert policy["error"] == "blocking_policy_codes_invalid"


def test_policy_loader_unknown_code_disables_but_surfaces_error(tmp_path: Path) -> None:
    # Red-team round 2: a typo'd code silently enabled selective-blocking
    # claims while blocking nothing. Unknown codes must fail visibly.
    _write_policy(tmp_path, codes=["session_like_non_session_memorytype"])

    policy = load_blocking_policy(tmp_path)

    assert policy["enabled_codes"] == []
    assert policy["error"] == (
        "blocking_policy_unknown_code:session_like_non_session_memorytype"
    )


def test_step4_workflow_blocks_b0_when_policy_file_enables_it(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write_policy(tmp_path)
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_IN_WINDOW_FILENAME}"],
        run_guard_check=True,
    )

    assert f"memory_authority_blocking:{B0_CODE}" in workflow.blockers
    assert workflow.completion_claim_allowed is False


def test_step4_workflow_kill_switch_restores_report_only(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write_policy(tmp_path, enabled=False)
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_IN_WINDOW_FILENAME}"],
        run_guard_check=True,
    )

    assert workflow.blockers == []
    assert B0_CODE in workflow.warnings
    assert workflow.completion_claim_allowed is True


def test_step4_workflow_broken_policy_is_itself_a_blocker(tmp_path: Path) -> None:
    # Red-team round 2 hardening: a corrupted policy file must fail the gate.
    # If it only warned, corrupting the file would be a silent kill switch.
    _make_framework_surface(tmp_path)
    _write_policy(tmp_path, raw="{not json")
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_IN_WINDOW_FILENAME}"],
        run_guard_check=True,
    )

    assert "blocking_policy_error" in workflow.blockers
    assert workflow.completion_claim_allowed is False
    assert any(w.startswith("blocking_policy_unreadable") for w in workflow.warnings)


def test_step4_ci_check_blocks_b0_when_policy_file_enables_it(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_IN_WINDOW_FILENAME}"]
    )

    assert result.clean is False
    blocker_codes = [b["code"] for b in result.blockers]
    assert f"memory_authority_blocking:{B0_CODE}" in blocker_codes


def test_step4_ci_check_stays_clean_without_policy_file(tmp_path: Path) -> None:
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_IN_WINDOW_FILENAME}"]
    )

    assert result.clean is True


def test_step4_ci_corrupted_policy_in_diff_fails_the_gate(tmp_path: Path) -> None:
    # Red-team round 2 probe 3: corrupting the policy in the same PR that
    # adds a B0 entry passed CI clean. A broken policy is now a blocker.
    _write_policy(tmp_path, raw="{corrupted")
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = ci_check(
        tmp_path,
        changed_files=[
            "governance/memory_blocking_policy.json",
            f"memory/{_IN_WINDOW_FILENAME}",
        ],
    )

    assert result.clean is False
    blocker_codes = [b["code"] for b in result.blockers]
    assert "blocking_policy_error" in blocker_codes


def test_step4_ci_policy_change_in_diff_is_loud(tmp_path: Path) -> None:
    # Red-team round 2 probe 4: disabling the policy in the same PR left no
    # trace in CI output. A valid policy change stays allowed (governance
    # action, owned by diff review) but must be announced.
    _write_policy(tmp_path, enabled=False)
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = ci_check(
        tmp_path,
        changed_files=[
            "governance/memory_blocking_policy.json",
            f"memory/{_IN_WINDOW_FILENAME}",
        ],
    )

    assert result.clean is True
    assert "blocking_policy_changed_in_current_diff" in result.warnings


def test_step4_ci_policy_deletion_in_diff_is_loud(tmp_path: Path) -> None:
    # Deleting the policy file is default-off (no error) but the diff that
    # removes the gate must still be announced.
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = ci_check(
        tmp_path,
        changed_files=[
            "governance/memory_blocking_policy.json",
            f"memory/{_IN_WINDOW_FILENAME}",
        ],
    )

    assert result.clean is True
    assert "blocking_policy_changed_in_current_diff" in result.warnings


def test_step4_ci_no_policy_announcement_without_policy_in_diff(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    _write_memory(tmp_path, _IN_WINDOW_FILENAME, _IN_WINDOW_B0_ENTRY)

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_IN_WINDOW_FILENAME}"]
    )

    assert "blocking_policy_changed_in_current_diff" not in result.warnings


def test_b0_scenario6_phase1_semantics_pinned_even_when_b0_fires(tmp_path: Path) -> None:
    # Kill-switch precondition: the current default must equal Phase 1
    # report-only semantics with no policy input. When the policy switch
    # lands, its default-off state must keep this exact shape.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: phase1 semantics fixture entry\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    result = run_guard(tmp_path / "memory", tmp_path, skip_git=True)

    assert result["ok"] is True
    assert result["ok_meaning"] == "guard_executed_report_only_not_authority_clean"
    assert result["phase"] == "phase1"
    assert result["mode"] == "warning"
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []
    assert result["claim_ceiling"] == "report_only_phase1"
    assert "blocking_enforcement" in result["not_claimed"]
    assert result["violation_counts_by_code"][B0_CODE] == 1
    assert B0_CODE in result["report_only_violation_codes"]
