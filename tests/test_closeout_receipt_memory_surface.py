"""Closeout receipt tests for exact canonical daily-memory outcomes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from governance_tools.memory_record import (
    WRITER_ID,
    append_session_derived_entry_with_outcome,
    build_session_derived_record,
)
from governance_tools.session_closeout_entry import (
    CLOSEOUT_RECEIPT_SCHEMA_VERSION,
    _verify_memory_write_claim,
    _write_closeout_receipt,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTCOME_FIELDS = frozenset(
    {
        "daily_memory_write_attempted",
        "daily_memory_write_status",
        "daily_memory_state_status",
        "daily_memory_path",
        "daily_memory_record_identity",
        "daily_memory_writer",
        "daily_memory_write_error",
    }
)


def _canonical_outcome(project_root: Path):
    record = build_session_derived_record(
        what_changed="receipt verifier test",
        commit="abc1234",
        session_id="session-verifier",
        memory_binding="bound",
        test_evidence="focused verifier test passed",
        next_step="review receipt",
        plan_reconciliation="not_applicable",
    )
    return append_session_derived_entry_with_outcome(
        project_root=project_root,
        record=record,
    )


class TestVerifyMemoryWriteClaim:
    def test_skipped_without_record_claim_is_verified(self, tmp_path: Path) -> None:
        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status="skipped",
            daily_memory_path=None,
            record_identity=None,
            writer=WRITER_ID,
            write_error=None,
        )
        assert verified is True
        assert reason == "write_skipped_no_record_claim"

    def test_failed_requires_sanitized_error(self, tmp_path: Path) -> None:
        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status="failed",
            daily_memory_path=None,
            record_identity=None,
            writer=WRITER_ID,
            write_error=None,
        )
        assert verified is False
        assert reason == "failed_outcome_missing_sanitized_error"

        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status="failed",
            daily_memory_path=None,
            record_identity=None,
            writer=WRITER_ID,
            write_error="RuntimeError: canonical memory writer failed",
        )
        assert verified is True
        assert reason == "writer_failure_reported"

    def test_written_verifies_exact_path_identity_and_writer(self, tmp_path: Path) -> None:
        outcome = _canonical_outcome(tmp_path)
        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status="written",
            daily_memory_path=str(outcome.path),
            record_identity=outcome.record_identity,
            writer=outcome.writer,
            write_error=None,
        )
        assert verified is True
        assert reason == "daily_memory_record_identity_verified"

    def test_already_present_verifies_satisfied_state(self, tmp_path: Path) -> None:
        first = _canonical_outcome(tmp_path)
        second = _canonical_outcome(tmp_path)
        assert first.status == "written"
        assert second.status == "already_present"

        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status=second.status,
            daily_memory_path=str(second.path),
            record_identity=second.record_identity,
            writer=second.writer,
            write_error=None,
        )
        assert verified is True
        assert reason == "daily_memory_record_identity_verified"

    def test_arbitrary_commit_text_does_not_verify(self, tmp_path: Path) -> None:
        daily = tmp_path / "memory" / "2099-01-01.md"
        daily.parent.mkdir(parents=True)
        daily.write_text(
            "# 2099-01-01\n\n- memory_type: session-derived\n"
            "  writer: governance_tools.memory_record\n"
            "  commit_hash: abc1234\n",
            encoding="utf-8",
        )
        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status="written",
            daily_memory_path=str(daily),
            record_identity="0" * 64,
            writer=WRITER_ID,
            write_error=None,
        )
        assert verified is False
        assert reason == "daily_memory_record_identity_not_found"

    def test_path_outside_repo_memory_is_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside.md"
        outside.write_text("not canonical\n", encoding="utf-8")
        verified, reason = _verify_memory_write_claim(
            tmp_path,
            write_status="written",
            daily_memory_path=str(outside),
            record_identity="0" * 64,
            writer=WRITER_ID,
            write_error=None,
        )
        assert verified is False
        assert reason == "daily_memory_path_outside_repo_memory"


class TestReceiptOutcomeSurface:
    def test_defaults_are_truthful_for_skipped_outcome(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="native_hook",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=True,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["daily_memory_write_attempted"] is False
        assert payload["daily_memory_write_status"] == "skipped"
        assert payload["daily_memory_state_status"] == "not_required"
        assert payload["daily_memory_path"] == ""
        assert payload["daily_memory_record_identity"] == ""
        assert payload["daily_memory_writer"] == WRITER_ID
        assert payload["daily_memory_write_error"] == ""

    def test_already_present_is_satisfied_but_not_performed(self, tmp_path: Path) -> None:
        outcome = _canonical_outcome(tmp_path)
        outcome = _canonical_outcome(tmp_path)
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="native_hook",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=True,
            memory_write_required=True,
            memory_write_performed=False,
            memory_eligibility_reason="memory_candidate_signals_detected",
            daily_memory_write_attempted=True,
            daily_memory_write_status=outcome.status,
            daily_memory_state_status="satisfied",
            daily_memory_path=str(outcome.path),
            daily_memory_record_identity=outcome.record_identity,
            daily_memory_writer=outcome.writer,
            memory_write_claim_verified=True,
            memory_write_claim_verification_reason="daily_memory_record_identity_verified",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["memory_write_performed"] is False
        assert payload["daily_memory_write_status"] == "already_present"
        assert payload["daily_memory_state_status"] == "satisfied"

    def test_authority_fields_still_carry_through(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="native_hook",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=True,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
            memory_authority_guard_ran=True,
            memory_authority_scope="repo",
            memory_authority_warning_codes=["unbound_memory"],
            memory_unbound_count=2,
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["memory_authority_guard_ran"] is True
        assert payload["memory_authority_scope"] == "repo"
        assert payload["memory_authority_warning_codes"] == ["unbound_memory"]
        assert payload["memory_unbound_count"] == 2


class TestSchemaVersion:
    def test_schema_version_is_1_5(self) -> None:
        assert CLOSEOUT_RECEIPT_SCHEMA_VERSION == "1.5"

    def test_emitted_receipt_contains_1_5_outcome_surface(self, tmp_path: Path) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="native_hook",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=False,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "closeout_receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )
        assert payload["schema_version"] == "1.5"
        assert _OUTCOME_FIELDS <= set(payload)
        assert set(payload) <= set(schema["properties"])
        Draft202012Validator(schema).validate(payload)

    def test_new_fields_are_conditional_to_1_5(self) -> None:
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "closeout_receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )
        assert not (_OUTCOME_FIELDS & set(schema["required"]))
        version_1_5_clause = next(
            clause
            for clause in schema["allOf"]
            if clause["if"]["properties"].get("schema_version", {}).get("const")
            == "1.5"
        )
        assert _OUTCOME_FIELDS == set(version_1_5_clause["then"]["required"])

    def test_legacy_1_4_receipt_does_not_require_1_5_fields(self) -> None:
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "closeout_receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )
        legacy = {
            "schema_version": "1.4",
            "timestamp": "2026-07-28T00:00:00+00:00",
            "agent_id": "legacy-test",
            "trigger_mode": "native_hook",
            "entrypoint": "governance_tools.session_closeout_entry",
            "exit_code": 0,
            "closeout_artifact_path": "",
            "checksum_of_cleaned_path": "",
            "memory_eligibility_evaluated": True,
            "memory_write_required": False,
            "memory_write_performed": False,
            "memory_eligibility_reason": "no_eligibility_trigger",
            "runtime_detection_status": "unknown",
            "sample_origin": "unknown",
        }
        Draft202012Validator(schema).validate(legacy)

    @pytest.mark.parametrize(
        "updates",
        [
            {
                "daily_memory_write_attempted": True,
                "daily_memory_write_status": "written",
                "daily_memory_state_status": "satisfied",
                "memory_write_performed": False,
                "daily_memory_path": "memory/2026-07-28.md",
                "daily_memory_record_identity": "a" * 64,
            },
            {
                "daily_memory_write_attempted": True,
                "daily_memory_write_status": "already_present",
                "daily_memory_state_status": "satisfied",
                "memory_write_performed": True,
                "daily_memory_path": "memory/2026-07-28.md",
                "daily_memory_record_identity": "a" * 64,
            },
            {
                "daily_memory_write_attempted": True,
                "daily_memory_write_status": "failed",
                "daily_memory_state_status": "satisfied",
                "memory_write_performed": False,
                "daily_memory_write_error": (
                    "RuntimeError: canonical memory writer failed"
                ),
            },
        ],
    )
    def test_1_5_rejects_cross_field_truth_mismatch(
        self,
        tmp_path: Path,
        updates: dict[str, object],
    ) -> None:
        receipt_path = _write_closeout_receipt(
            tmp_path,
            agent_id="test",
            trigger_mode="native_hook",
            entrypoint="governance_tools.session_closeout_entry",
            exit_code=0,
            closeout_artifact_path=None,
            memory_eligibility_evaluated=False,
            memory_write_required=False,
            memory_write_performed=False,
            memory_eligibility_reason="no_eligibility_trigger",
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        payload.update(updates)
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "closeout_receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )

        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(payload)
