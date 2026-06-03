"""CE-1D.2: raw claim-enforcement packet output path relocation.

Validates:
- session_end writes raw packet to new runtime-ignored path (artifacts/session/claim-enforcement/)
- session_end does NOT create raw packet under old repo-facing path (artifacts/claim-enforcement/)
- compact receipt source_packet_dir points to the new runtime path
- compact receipt claim_enforcement_check_present reflects new path
- runtime_completeness_audit reads new path
- runtime_completeness_audit falls back to old path for historical data
- runtime_completeness_audit reports missing when packet is absent from both paths
- closeout_audit counts raw packets at new path
- receipt validator detects unreceipted packets in the new raw root
- receipt validator still detects unreceipted packets in the legacy raw root
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.claim_enforcement_receipt_validator import (
    detect_unreceipted_packets,
    validate_receipts,
    _RECEIPTS_RELATIVE,
)
from governance_tools.closeout_audit import build_closeout_audit
from governance_tools.runtime_completeness_audit import build_runtime_completeness_audit
from runtime_hooks.core.session_end import run_session_end


NEW_RAW_ROOT_REL = "artifacts/session/claim-enforcement"
OLD_RAW_ROOT_REL = "artifacts/claim-enforcement"
RECEIPTS_RELATIVE = "artifacts/claim-enforcement/claim-enforcement-receipts.ndjson"
TEST_SESSION_ID = "ce1d2-test-session"


@pytest.fixture
def tmp_project(tmp_path):
    """Minimal project root for CE-1D.2 tests."""
    (tmp_path / "memory").mkdir()
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def _base_contract(**overrides):
    contract = {
        "task": "CE-1D.2 path relocation test",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "stateless",
    }
    contract.update(overrides)
    return contract


def _run(tmp_project, session_id=TEST_SESSION_ID):
    return run_session_end(
        project_root=tmp_project,
        session_id=session_id,
        runtime_contract=_base_contract(),
        summary="CE-1D.2 path relocation smoke test",
    )


def _write_verdict(repo, session_id):
    verdict_dir = repo / "artifacts" / "runtime" / "verdicts"
    verdict_dir.mkdir(parents=True, exist_ok=True)
    (verdict_dir / f"{session_id}.json").write_text(
        json.dumps({"session_id": session_id}), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# session_end: raw packet goes to new path, not old path
# ---------------------------------------------------------------------------


def test_raw_packet_written_to_new_runtime_path(tmp_project):
    _run(tmp_project)
    new_path = tmp_project / NEW_RAW_ROOT_REL / TEST_SESSION_ID / "claim-enforcement-check.json"
    assert new_path.exists(), f"raw packet not written to new runtime path: {new_path}"


def test_raw_packet_not_written_to_old_repo_facing_path(tmp_project):
    _run(tmp_project)
    old_path = tmp_project / OLD_RAW_ROOT_REL / TEST_SESSION_ID / "claim-enforcement-check.json"
    assert not old_path.exists(), (
        f"raw packet leaked to repo-facing path (should only be at new runtime path): {old_path}"
    )


# ---------------------------------------------------------------------------
# compact receipt: source_packet_dir and presence flag
# ---------------------------------------------------------------------------


def test_receipt_source_packet_dir_points_to_new_runtime_path(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    row = json.loads(receipts.read_text(encoding="utf-8").splitlines()[-1])
    expected = str(tmp_project / NEW_RAW_ROOT_REL / TEST_SESSION_ID)
    assert row["source_packet_dir"] == expected, (
        f"source_packet_dir should point to new runtime path.\n"
        f"  expected: {expected}\n"
        f"  got:      {row['source_packet_dir']}"
    )


def test_receipt_presence_flag_true_after_session_end(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    row = json.loads(receipts.read_text(encoding="utf-8").splitlines()[-1])
    assert row["claim_enforcement_check_present"] is True, (
        "receipt should report packet present after session_end writes to new path"
    )


# ---------------------------------------------------------------------------
# runtime_completeness_audit: dual-read
# ---------------------------------------------------------------------------


def test_runtime_completeness_audit_finds_packet_at_new_path(tmp_project):
    sid = "ce1d2-new-path-sid"
    _write_verdict(tmp_project, sid)
    new_packet = tmp_project / NEW_RAW_ROOT_REL / sid / "claim-enforcement-check.json"
    new_packet.parent.mkdir(parents=True)
    new_packet.write_text("{}", encoding="utf-8")

    result = build_runtime_completeness_audit(tmp_project)
    assert sid not in result["claim_binding_missing_for_invoked_session"], (
        "runtime_completeness_audit must read raw packet at new runtime path"
    )


def test_runtime_completeness_audit_falls_back_to_old_path(tmp_project):
    sid = "ce1d2-old-path-sid"
    _write_verdict(tmp_project, sid)
    old_packet = tmp_project / OLD_RAW_ROOT_REL / sid / "claim-enforcement-check.json"
    old_packet.parent.mkdir(parents=True)
    old_packet.write_text("{}", encoding="utf-8")

    result = build_runtime_completeness_audit(tmp_project)
    assert sid not in result["claim_binding_missing_for_invoked_session"], (
        "runtime_completeness_audit must fall back to legacy path for historical packets"
    )


def test_runtime_completeness_audit_reports_missing_when_absent_from_both_paths(tmp_project):
    sid = "ce1d2-absent-sid"
    _write_verdict(tmp_project, sid)
    # No raw packet at either path

    result = build_runtime_completeness_audit(tmp_project)
    assert sid in result["claim_binding_missing_for_invoked_session"], (
        "runtime_completeness_audit should report missing when packet absent from both paths"
    )


# ---------------------------------------------------------------------------
# closeout_audit: counts new-path packets
# ---------------------------------------------------------------------------


def test_closeout_audit_counts_packet_at_new_runtime_path(tmp_project):
    closeout_dir = tmp_project / "artifacts" / "runtime" / "closeouts"
    closeout_dir.mkdir(parents=True)
    (closeout_dir / "s-ce1d2.json").write_text(
        json.dumps({
            "session_id": "s-ce1d2",
            "closed_at": "2026-06-03T00:00:00+00:00",
            "closeout_status": "valid",
            "task_intent": "test",
            "work_summary": "test",
            "evidence_summary": {"tools_used": [], "artifacts_referenced": []},
            "open_risks": [],
        }),
        encoding="utf-8",
    )
    new_packet = tmp_project / NEW_RAW_ROOT_REL / "s-ce1d2" / "claim-enforcement-check.json"
    new_packet.parent.mkdir(parents=True)
    new_packet.write_text(json.dumps({"enforcement_action": "allow"}), encoding="utf-8")

    result = build_closeout_audit(tmp_project)
    assert result["claim_enforcement_check_count"] >= 1, (
        "closeout_audit should count raw packet at new runtime path"
    )


# ---------------------------------------------------------------------------
# receipt validator: unreceipted detection across roots
# ---------------------------------------------------------------------------


def test_validator_detects_unreceipted_packet_in_new_raw_root(tmp_project):
    ce_root = tmp_project / OLD_RAW_ROOT_REL
    new_raw_root = tmp_project / NEW_RAW_ROOT_REL
    (new_raw_root / "session-new-unrec").mkdir(parents=True)
    (new_raw_root / "session-new-unrec" / "claim-enforcement-check.json").write_text(
        "{}", encoding="utf-8"
    )

    result = detect_unreceipted_packets(
        ce_root,
        receipted_session_ids=set(),
        raw_packet_roots=[new_raw_root, ce_root],
    )
    assert "session-new-unrec" in result


def test_validator_still_detects_unreceipted_packet_in_legacy_root(tmp_project):
    ce_root = tmp_project / OLD_RAW_ROOT_REL
    new_raw_root = tmp_project / NEW_RAW_ROOT_REL
    (ce_root / "session-old-unrec").mkdir(parents=True)
    (ce_root / "session-old-unrec" / "claim-enforcement-check.json").write_text(
        "{}", encoding="utf-8"
    )

    result = detect_unreceipted_packets(
        ce_root,
        receipted_session_ids=set(),
        raw_packet_roots=[new_raw_root, ce_root],
    )
    assert "session-old-unrec" in result


def test_validator_skips_receipted_sessions_across_both_roots(tmp_project):
    ce_root = tmp_project / OLD_RAW_ROOT_REL
    new_raw_root = tmp_project / NEW_RAW_ROOT_REL
    (new_raw_root / "session-receipted").mkdir(parents=True)
    (new_raw_root / "session-receipted" / "claim-enforcement-check.json").write_text(
        "{}", encoding="utf-8"
    )

    result = detect_unreceipted_packets(
        ce_root,
        receipted_session_ids={"session-receipted"},
        raw_packet_roots=[new_raw_root, ce_root],
    )
    assert "session-receipted" not in result


def test_validator_deduplicates_session_ids_appearing_in_both_roots(tmp_project):
    """If a session somehow appears in both roots, it should be counted once."""
    ce_root = tmp_project / OLD_RAW_ROOT_REL
    new_raw_root = tmp_project / NEW_RAW_ROOT_REL
    for root in (ce_root, new_raw_root):
        (root / "session-dup").mkdir(parents=True)
        (root / "session-dup" / "claim-enforcement-check.json").write_text(
            "{}", encoding="utf-8"
        )

    result = detect_unreceipted_packets(
        ce_root,
        receipted_session_ids=set(),
        raw_packet_roots=[new_raw_root, ce_root],
    )
    assert result.count("session-dup") == 1


def test_validator_legacy_behaviour_unchanged_when_no_raw_packet_roots(tmp_project):
    """Calling without raw_packet_roots should fall back to ce_root only (backward compat)."""
    ce_root = tmp_project / OLD_RAW_ROOT_REL
    (ce_root / "session-legacy").mkdir(parents=True)
    (ce_root / "session-legacy" / "claim-enforcement-check.json").write_text(
        "{}", encoding="utf-8"
    )

    result = detect_unreceipted_packets(ce_root, receipted_session_ids=set())
    assert "session-legacy" in result
