"""
test_manual_receipt_writer.py — manual_fallback receipt path for non-native-hook agents

Tests:
  Enforcement parity (choke point not bypassed):
    1.  test_manual_fallback_receipt_uses_output_mode_enforcer
    2.  test_manual_fallback_does_not_recompute_ceiling
    3.  test_manual_fallback_block_is_non_compliant
    4.  test_manual_fallback_degrade_is_non_compliant_for_block_decisions

  Consequence tier recorded:
    5.  test_manual_fallback_receipt_records_consequence_tier
    6.  test_consequence_tier_absent_when_not_provided

  Enforcement identity fields locked:
    7.  test_enforcement_source_is_locked
    8.  test_fallback_weakens_enforcement_is_always_false

  Compliance check (non-native agent cannot skip choke point):
    9.  test_missing_enforcement_source_is_not_compliant_for_non_native_agent
    10. test_missing_manual_receipt_fields_is_not_compliant
    11. test_block_decision_is_not_compliant
    12. test_native_hook_receipt_out_of_scope_for_compliance_check

  Receipt schema completeness:
    13. test_receipt_contains_all_required_fields
    14. test_trigger_mode_is_manual_fallback
    15. test_schema_version_is_v1_1

  Caller contract violations:
    16. test_empty_agent_id_raises
    17. test_empty_fallback_reason_raises

  File output:
    18. test_receipt_written_to_output_path
    19. test_receipt_is_valid_json_on_disk
    20. test_returned_dict_matches_file_content
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.manual_receipt_writer import (
    write_manual_receipt,
    is_compliant_for_non_native_agent,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _full_record(
    existence=True,
    eligibility_evaluated=True,
    compliance_present=True,
    semantics_reviewed=True,
    causal_present=True,
    cross_layer=True,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "admissibility_state": {
            "existence": existence,
            "eligibility_evaluated": eligibility_evaluated,
            "compliance_present": compliance_present,
            "semantics_reviewed": semantics_reviewed,
        }
    }
    if causal_present is not None:
        record["causal_chain"] = {"present": causal_present, "cross_layer": cross_layer}
    return record


def _base_kwargs(tmp_path: Path, mode="governance_adequate") -> dict[str, Any]:
    return dict(
        record=_full_record(),
        requested_mode=mode,
        output_path=str(tmp_path / "receipt.json"),
        agent_id="copilot-test",
        entrypoint="manual_closeout.py",
        closeout_artifact_path="artifacts/closeout.json",
        checksum_of_cleaned_path="abc123",
        memory_eligibility_evaluated=True,
        memory_write_required=False,
        memory_write_performed=False,
        memory_eligibility_reason="session below threshold",
        manual_fallback_reason="non_native_hook_agent",
    )


# ── 1. Uses output_mode_enforcer ──────────────────────────────────────────────

def test_manual_fallback_receipt_uses_output_mode_enforcer(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    assert receipt["enforcement_source"] == "output_mode_enforcer"
    # enforcer result fields must be present and non-empty
    assert receipt["output_mode_requested"] == "governance_adequate"
    assert receipt["output_mode_decision"] in ("allow", "degrade", "block")


# ── 2. Does not recompute ceiling locally ─────────────────────────────────────

def test_manual_fallback_does_not_recompute_ceiling(tmp_path):
    # If ceiling were recomputed locally the field would still be present, but
    # we verify the decision matches what enforce_output_mode would return for
    # the same inputs — proving the writer delegates rather than re-derives.
    from governance_tools.output_mode_enforcer import enforce_output_mode

    record = _full_record()
    mode = "governance_adequate"
    expected = enforce_output_mode(record, mode)

    kwargs = _base_kwargs(tmp_path, mode=mode)
    kwargs["record"] = record
    receipt = write_manual_receipt(**kwargs)

    assert receipt["output_mode_ceiling"] == expected["ceiling"]
    assert receipt["output_mode_effective"] == expected["actual_mode"]
    assert receipt["output_mode_decision"] == expected["enforcement_action"]


# ── 3. Block decision → non-compliant ────────────────────────────────────────

def test_manual_fallback_block_is_non_compliant(tmp_path):
    # governance_effective is permanently prohibited → decision=block
    kwargs = _base_kwargs(tmp_path, mode="governance_effective")
    receipt = write_manual_receipt(**kwargs)
    assert receipt["output_mode_decision"] == "block"
    compliant, reason = is_compliant_for_non_native_agent(receipt)
    assert compliant is False
    assert "block" in reason


# ── 4. Degrade (not block) is compliant for compliance check ─────────────────

# degrade = enforcer permitted a lower mode (ceiling); this is valid.
# Only "block" constitutes non-compliance.
def test_degrade_decision_is_compliant(tmp_path):
    record = {"admissibility_state": {"existence": False}}
    kwargs = _base_kwargs(tmp_path, mode="closeout_recorded")
    kwargs["record"] = record
    receipt = write_manual_receipt(**kwargs)
    assert receipt["output_mode_decision"] == "degrade"
    compliant, _ = is_compliant_for_non_native_agent(receipt)
    assert compliant is True


# ── 5. Consequence tier recorded when provided ────────────────────────────────

def test_manual_fallback_receipt_records_consequence_tier(tmp_path):
    kwargs = _base_kwargs(tmp_path)
    kwargs["consequence_tier"] = 1
    kwargs["consequence_materiality_reason"] = "claim ceiling bounded in artifact"
    receipt = write_manual_receipt(**kwargs)
    assert receipt["consequence_tier"] == 1
    assert receipt["consequence_materiality_reason"] == "claim ceiling bounded in artifact"


# ── 6. Consequence tier absent when not provided ─────────────────────────────

def test_consequence_tier_absent_when_not_provided(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    assert "consequence_tier" not in receipt
    assert "consequence_materiality_reason" not in receipt


# ── 7. enforcement_source locked ─────────────────────────────────────────────

def test_enforcement_source_is_locked(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    assert receipt["enforcement_source"] == "output_mode_enforcer"


# ── 8. fallback_weakens_enforcement always False ─────────────────────────────

def test_fallback_weakens_enforcement_is_always_false(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    assert receipt["fallback_weakens_enforcement"] is False


# ── 9. Missing enforcement_source → non-compliant ────────────────────────────

def test_missing_enforcement_source_is_not_compliant_for_non_native_agent():
    bad_receipt = {
        "trigger_mode": "manual_fallback",
        "output_mode_requested": "governance_adequate",
        "output_mode_effective": "governance_adequate",
        "output_mode_decision": "allow",
        "fallback_weakens_enforcement": False,
        # enforcement_source deliberately absent
    }
    compliant, reason = is_compliant_for_non_native_agent(bad_receipt)
    assert compliant is False
    assert "enforcement_source" in reason


# ── 10. Missing output_mode fields → non-compliant ───────────────────────────

def test_missing_manual_receipt_fields_is_not_compliant():
    bad_receipt = {
        "trigger_mode": "manual_fallback",
        "enforcement_source": "output_mode_enforcer",
        "fallback_weakens_enforcement": False,
        # output_mode_requested and output_mode_effective deliberately absent
    }
    compliant, reason = is_compliant_for_non_native_agent(bad_receipt)
    assert compliant is False
    assert "output_mode_requested" in reason or "output_mode_effective" in reason


# ── 11. Block decision → non-compliant ───────────────────────────────────────

def test_block_decision_is_not_compliant():
    blocked_receipt = {
        "trigger_mode": "manual_fallback",
        "enforcement_source": "output_mode_enforcer",
        "fallback_weakens_enforcement": False,
        "output_mode_requested": "governance_effective",
        "output_mode_effective": "governance_adequate",
        "output_mode_decision": "block",
    }
    compliant, reason = is_compliant_for_non_native_agent(blocked_receipt)
    assert compliant is False
    assert "block" in reason


# ── 12. Native hook receipt → out of scope ────────────────────────────────────

def test_native_hook_receipt_out_of_scope_for_compliance_check():
    native_receipt = {
        "trigger_mode": "native_hook",
        "output_mode_decision": "block",  # would be non-compliant if manual_fallback
    }
    compliant, reason = is_compliant_for_non_native_agent(native_receipt)
    assert compliant is True
    assert reason == "not_manual_fallback"


# ── 13. Required fields present ───────────────────────────────────────────────

def test_receipt_contains_all_required_fields(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    required = {
        "schema_version", "timestamp", "agent_id", "trigger_mode",
        "entrypoint", "exit_code", "closeout_artifact_path",
        "checksum_of_cleaned_path", "memory_eligibility_evaluated",
        "memory_write_required", "memory_write_performed",
        "memory_eligibility_reason",
        "output_mode_requested", "output_mode_effective",
        "output_mode_decision", "output_mode_ceiling",
        "enforcement_source", "fallback_weakens_enforcement",
        "manual_fallback_reason",
    }
    assert required <= receipt.keys()


# ── 14. trigger_mode is manual_fallback ──────────────────────────────────────

def test_trigger_mode_is_manual_fallback(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    assert receipt["trigger_mode"] == "manual_fallback"


# ── 15. Schema version is v1.1 ───────────────────────────────────────────────

def test_schema_version_is_v1_1(tmp_path):
    receipt = write_manual_receipt(**_base_kwargs(tmp_path))
    assert receipt["schema_version"] == "1.1"


# ── 16. Empty agent_id raises ────────────────────────────────────────────────

def test_empty_agent_id_raises(tmp_path):
    kwargs = _base_kwargs(tmp_path)
    kwargs["agent_id"] = ""
    with pytest.raises(ValueError, match="agent_id"):
        write_manual_receipt(**kwargs)


# ── 17. Empty fallback_reason raises ─────────────────────────────────────────

def test_empty_fallback_reason_raises(tmp_path):
    kwargs = _base_kwargs(tmp_path)
    kwargs["manual_fallback_reason"] = ""
    with pytest.raises(ValueError, match="manual_fallback_reason"):
        write_manual_receipt(**kwargs)


# ── 18. File written to output_path ──────────────────────────────────────────

def test_receipt_written_to_output_path(tmp_path):
    path = str(tmp_path / "sub" / "receipt.json")
    write_manual_receipt(**{**_base_kwargs(tmp_path), "output_path": path})
    assert os.path.isfile(path)


# ── 19. File is valid JSON ────────────────────────────────────────────────────

def test_receipt_is_valid_json_on_disk(tmp_path):
    path = str(tmp_path / "receipt.json")
    write_manual_receipt(**{**_base_kwargs(tmp_path), "output_path": path})
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict)
    assert data["trigger_mode"] == "manual_fallback"


# ── 20. Returned dict matches file ───────────────────────────────────────────

def test_returned_dict_matches_file_content(tmp_path):
    path = str(tmp_path / "receipt.json")
    returned = write_manual_receipt(**{**_base_kwargs(tmp_path), "output_path": path})
    with open(path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert returned == on_disk


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_degrade_receipt_appends_session_audit_trace(tmp_path):
    trace_path = tmp_path / "artifacts" / "audit" / "session-output-mode-trace.ndjson"
    record = {
        "session_id": "session-abc",
        "record_id": "rec-001",
        "agent_type": "copilot",
        "admissibility_state": {"existence": False},  # forces degrade for requested closeout_recorded
    }
    kwargs = _base_kwargs(tmp_path, mode="closeout_recorded")
    kwargs["record"] = record
    kwargs["session_output_mode_trace_path"] = str(trace_path)
    receipt = write_manual_receipt(**kwargs)

    assert trace_path.exists()
    rows = _read_ndjson(trace_path)
    assert len(rows) == 1
    assert rows[0]["session_id"] == "session-abc"
    assert rows[0]["output_mode_decision"] == "degrade"
    assert rows[0]["receipt_path"] == kwargs["output_path"]
    assert rows[0]["enforcement_source"] == "output_mode_enforcer"
    assert rows[0]["output_mode_decision"] == receipt["output_mode_decision"]


def test_session_trace_preserves_consequence_tier(tmp_path):
    trace_path = tmp_path / "artifacts" / "audit" / "session-output-mode-trace.ndjson"
    record = {
        "session_id": "session-tier",
        "record_id": "rec-tier",
        "agent_type": "gemini",
        "admissibility_state": {"existence": False},
    }
    kwargs = _base_kwargs(tmp_path, mode="closeout_recorded")
    kwargs["record"] = record
    kwargs["consequence_tier"] = 1
    kwargs["session_output_mode_trace_path"] = str(trace_path)
    write_manual_receipt(**kwargs)

    rows = _read_ndjson(trace_path)
    assert rows[-1]["consequence_tier"] == 1


def test_trace_decision_matches_receipt_decision(tmp_path):
    trace_path = tmp_path / "artifacts" / "audit" / "session-output-mode-trace.ndjson"
    record = {
        "session_id": "session-match",
        "record_id": "rec-match",
        "agent_type": "unknown",
        "admissibility_state": {"existence": True},
        "causal_chain": {"present": True, "cross_layer": True},
    }
    kwargs = _base_kwargs(tmp_path, mode="procedural_compliance_observed")
    kwargs["record"] = record
    kwargs["session_output_mode_trace_path"] = str(trace_path)
    receipt = write_manual_receipt(**kwargs)

    rows = _read_ndjson(trace_path)
    assert rows[-1]["output_mode_decision"] == receipt["output_mode_decision"]
    assert rows[-1]["output_mode_requested"] == receipt["output_mode_requested"]
    assert rows[-1]["output_mode_effective"] == receipt["output_mode_effective"]
