"""
Closeout receipt memory surface tests (E1 + E2).

E1: memory_write_claim_verified + memory_write_claim_verification_reason
  — verifies that memory_write_performed=True self-report is checked against
    the daily memory file for a session_id or commit hash anchor.

E2: memory_authority_guard_ran / memory_authority_scope /
    memory_authority_warning_codes / memory_unbound_count
  — verifies that the memory authority guard surface from run_session_end_hook()
    is forwarded into the receipt.

DONE criteria:
  1. _verify_memory_write_claim: performed=False  → verified=True, no_memory_write_claim
  2. _verify_memory_write_claim: performed=True, no file  → False, daily_memory_missing
  3. _verify_memory_write_claim: performed=True, session_id in file  → True, session_id_found
  4. _verify_memory_write_claim: performed=True, commit hash in file  → True, commit_hash_found
  5. _verify_memory_write_claim: performed=True, file exists but no anchor  → False, no_anchor
  6. Receipt contains all 6 new fields with correct defaults
  7. Receipt contains all 6 new fields with non-default values
  8. Schema version is "1.1"
  9. Field name stability snapshot

Non-goals:
  - Does not test enforcement/blocking
  - Does not test cross-day memory lookups (only today's daily file)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from governance_tools.session_closeout_entry import (
    CLOSEOUT_RECEIPT_SCHEMA_VERSION,
    _verify_memory_write_claim,
    _write_closeout_receipt,
)

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_receipt_memory_surface"


def _reset(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── E1: _verify_memory_write_claim ────────────────────────────────────────────

class TestVerifyMemoryWriteClaim:
    def test_not_performed_is_verified_no_claim(self, tmp_path: Path) -> None:
        """Criterion 1: performed=False → verified=True, reason=no_memory_write_claim."""
        verified, reason = _verify_memory_write_claim(tmp_path, False, "any-session-id")
        assert verified is True
        assert reason == "no_memory_write_claim"

    def test_performed_daily_memory_missing(self, tmp_path: Path) -> None:
        """Criterion 2: performed=True but daily memory file missing → False, daily_memory_missing."""
        # memory/ dir doesn't exist in tmp_path — no daily file
        verified, reason = _verify_memory_write_claim(tmp_path, True, "session-20260529T010101-aabbcc")
        assert verified is False
        assert reason == "daily_memory_missing"

    def test_performed_session_id_in_file(self, tmp_path: Path) -> None:
        """Criterion 3: performed=True, session_id found in daily memory → True, session_id_found."""
        sid = "session-20260529T010101-aabbcc"
        daily = tmp_path / "memory" / f"{_today()}.md"
        daily.parent.mkdir(parents=True, exist_ok=True)
        daily.write_text(
            f"# {_today()}\n\n"
            f"- what changed: added feature\n"
            f"- session: {sid}\n"
            f"- commit hash: pending\n",
            encoding="utf-8",
        )
        verified, reason = _verify_memory_write_claim(tmp_path, True, sid)
        assert verified is True
        assert reason == "session_id_found_in_daily_memory"

    def test_performed_commit_hash_in_file(self, tmp_path: Path) -> None:
        """Criterion 4: performed=True, commit hash anchor found → True, commit_hash_found."""
        daily = tmp_path / "memory" / f"{_today()}.md"
        daily.parent.mkdir(parents=True, exist_ok=True)
        daily.write_text(
            f"# {_today()}\n\n"
            "- what changed: added feature\n"
            "- commit hash: abc1234\n",
            encoding="utf-8",
        )
        verified, reason = _verify_memory_write_claim(tmp_path, True, "unrelated-session-id")
        assert verified is True
        assert reason == "commit_hash_found_in_daily_memory"

    def test_performed_file_exists_but_no_anchor(self, tmp_path: Path) -> None:
        """Criterion 5: performed=True, daily file exists but no session_id or commit hash → False."""
        daily = tmp_path / "memory" / f"{_today()}.md"
        daily.parent.mkdir(parents=True, exist_ok=True)
        daily.write_text(
            f"# {_today()}\n\n"
            "- what changed: something\n"
            "- commit hash: pending\n",
            encoding="utf-8",
        )
        verified, reason = _verify_memory_write_claim(tmp_path, True, "unknown-session")
        assert verified is False
        assert reason == "daily_memory_exists_but_no_session_or_commit_anchor"


# ── E2: receipt new fields ────────────────────────────────────────────────────

class TestReceiptNewFieldsDefaults:
    """Criterion 6: new fields present with correct defaults when not supplied."""

    def test_new_fields_present_with_defaults(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="manual_fallback",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=True,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["memory_write_claim_verified"] is False
        assert payload["memory_write_claim_verification_reason"] == ""
        assert payload["memory_authority_guard_ran"] is False
        assert payload["memory_authority_scope"] == ""
        assert payload["memory_authority_warning_codes"] == []
        assert payload["memory_unbound_count"] == 0


class TestReceiptNewFieldsWithValues:
    """Criterion 7: new fields carry through non-default values."""

    def test_new_fields_carry_through_values(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="native_hook",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=True,
            memory_write_required=True,
            memory_write_performed=True,
            memory_eligibility_reason="memory_candidate_signals_detected",
            memory_write_claim_verified=True,
            memory_write_claim_verification_reason="session_id_found_in_daily_memory",
            memory_authority_guard_ran=True,
            memory_authority_scope="repo",
            memory_authority_warning_codes=["unbound_memory"],
            memory_unbound_count=2,
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["memory_write_claim_verified"] is True
        assert payload["memory_write_claim_verification_reason"] == "session_id_found_in_daily_memory"
        assert payload["memory_authority_guard_ran"] is True
        assert payload["memory_authority_scope"] == "repo"
        assert payload["memory_authority_warning_codes"] == ["unbound_memory"]
        assert payload["memory_unbound_count"] == 2


# ── Schema version ────────────────────────────────────────────────────────────

class TestSchemaVersion:
    """Criterion 8: schema version is 1.1 after this change."""

    def test_schema_version_is_1_1(self) -> None:
        assert CLOSEOUT_RECEIPT_SCHEMA_VERSION == "1.1"

    def test_receipt_schema_version_field_is_1_1(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="manual_fallback",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=False,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "1.1"


# ── Snapshot stability ────────────────────────────────────────────────────────

_EXPECTED_NEW_FIELDS = frozenset({
    "memory_write_claim_verified",
    "memory_write_claim_verification_reason",
    "memory_authority_guard_ran",
    "memory_authority_scope",
    "memory_authority_warning_codes",
    "memory_unbound_count",
})


class TestSnapshotStability:
    """Criterion 9: all 6 new field names locked — renames are caught immediately."""

    def test_all_six_new_fields_present(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="manual_fallback",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=False,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert _EXPECTED_NEW_FIELDS <= set(payload.keys())
