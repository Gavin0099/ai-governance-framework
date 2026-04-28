"""
Tests for governance_tools/phase_d_closeout_writer.py.

write_phase_d_closeout: creates artifact with writer identity and reviewer fields.
assess_phase_d_closeout: reads and validates; fail-closed on absent/untrusted.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from governance_tools.phase_d_closeout_writer import (
    CLOSEOUT_SCHEMA,
    CLOSEOUT_WRITER_ID,
    CLOSEOUT_WRITER_VERSION,
    EXCEPTION_OVERRIDE_SUPPORTED,
    REQUIRED_CONDITIONS,
    RUNTIME_UNVERIFIABLE_CONDITIONS,
    assess_phase_d_closeout,
    write_phase_d_closeout,
)

# Canonical full conditions list for tests that need ok=True.
_FULL_CONDITIONS = sorted(REQUIRED_CONDITIONS)


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_phase_d_closeout_writer" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


# ---------------------------------------------------------------------------
# write_phase_d_closeout
# ---------------------------------------------------------------------------


def test_write_creates_valid_artifact():
    d = _tmp_dir("write_valid")
    path = d / "closeout.json"
    conditions = ["phase_c_surface_gap_resolved", "reviewer_independent_of_author"]

    result = write_phase_d_closeout(
        path,
        reviewer_id="tier1_reviewer_a",
        confirmed_conditions=conditions,
        confirmed_at="2026-04-28T10:00:00+00:00",
    )

    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == result
    assert on_disk["closeout_schema"] == CLOSEOUT_SCHEMA
    assert on_disk["writer_id"] == CLOSEOUT_WRITER_ID
    assert on_disk["writer_version"] == CLOSEOUT_WRITER_VERSION
    assert on_disk["phase_completed"] == "D"
    assert on_disk["verdict"] == "completed"
    assert on_disk["reviewer_id"] == "tier1_reviewer_a"
    assert on_disk["confirmed_at"] == "2026-04-28T10:00:00+00:00"
    assert on_disk["confirmed_conditions"] == conditions
    assert on_disk["reviewer_confirmation"] == "explicit"


def test_write_and_assess_roundtrip_ok():
    d = _tmp_dir("roundtrip")
    path = d / "closeout.json"

    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_x",
        confirmed_conditions=_FULL_CONDITIONS,
    )
    result = assess_phase_d_closeout(path)

    assert result["ok"] is True
    assert result["review_confirmed"] is True
    assert result["trusted_writer"] is True
    assert result["reviewer_id"] == "reviewer_x"
    assert set(result["confirmed_conditions"]) == REQUIRED_CONDITIONS
    assert result["release_block_reasons"] == []
    assert result["failures"] == []
    assert result["missing_required_conditions"] == []
    assert result["exception_override_supported"] is False
    assert result["runtime_unverifiable_conditions"] == RUNTIME_UNVERIFIABLE_CONDITIONS


def test_write_rejects_empty_reviewer_id():
    d = _tmp_dir("write_empty_reviewer")
    path = d / "closeout.json"

    with pytest.raises(ValueError, match="reviewer_id"):
        write_phase_d_closeout(path, reviewer_id="", confirmed_conditions=["cond_a"])


def test_write_rejects_whitespace_only_reviewer_id():
    d = _tmp_dir("write_whitespace_reviewer")
    path = d / "closeout.json"

    with pytest.raises(ValueError, match="reviewer_id"):
        write_phase_d_closeout(path, reviewer_id="   ", confirmed_conditions=["cond_a"])


def test_write_rejects_empty_confirmed_conditions():
    d = _tmp_dir("write_empty_conditions")
    path = d / "closeout.json"

    with pytest.raises(ValueError, match="confirmed_conditions"):
        write_phase_d_closeout(path, reviewer_id="reviewer_x", confirmed_conditions=[])


def test_write_rejects_non_list_confirmed_conditions():
    d = _tmp_dir("write_non_list_conditions")
    path = d / "closeout.json"

    with pytest.raises(ValueError, match="confirmed_conditions"):
        write_phase_d_closeout(
            path,
            reviewer_id="reviewer_x",
            confirmed_conditions="cond_a",  # type: ignore[arg-type]
        )


def test_write_creates_parent_directories():
    d = _tmp_dir("write_parents")
    path = d / "sub" / "deep" / "closeout.json"

    write_phase_d_closeout(path, reviewer_id="r", confirmed_conditions=["c"])

    assert path.is_file()


def test_write_strips_reviewer_id_whitespace():
    d = _tmp_dir("write_strips_whitespace")
    path = d / "closeout.json"

    result = write_phase_d_closeout(
        path, reviewer_id="  reviewer_y  ", confirmed_conditions=["c"]
    )

    assert result["reviewer_id"] == "reviewer_y"


# ---------------------------------------------------------------------------
# assess_phase_d_closeout
# ---------------------------------------------------------------------------


def test_assess_absent_artifact_fails_closed():
    """Absent artifact → ok=False, available=False (unconditional fail-closed)."""
    d = _tmp_dir("assess_absent")
    path = d / "nonexistent.json"

    result = assess_phase_d_closeout(path)

    assert result["available"] is False
    assert result["ok"] is False
    assert result["review_confirmed"] is False
    assert "phase_d_closeout_artifact_absent" in result["release_block_reasons"]


def test_assess_untrusted_writer_fails_closed():
    d = _tmp_dir("assess_untrusted")
    path = d / "closeout.json"
    path.write_text(
        json.dumps(
            {
                "closeout_schema": CLOSEOUT_SCHEMA,
                "writer_id": "evil.writer",
                "writer_version": CLOSEOUT_WRITER_VERSION,
                "written_at": "2026-04-28T00:00:00+00:00",
                "phase_completed": "D",
                "reviewer_id": "r",
                "confirmed_at": "2026-04-28T00:00:00+00:00",
                "confirmed_conditions": ["c"],
                "reviewer_confirmation": "explicit",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert result["trusted_writer"] is False
    assert "phase_d_closeout_writer_untrusted" in result["release_block_reasons"]


def test_assess_wrong_schema_fails_closed():
    d = _tmp_dir("assess_wrong_schema")
    path = d / "closeout.json"
    path.write_text(
        json.dumps(
            {
                "closeout_schema": "some.other.schema",
                "writer_id": CLOSEOUT_WRITER_ID,
                "writer_version": CLOSEOUT_WRITER_VERSION,
                "written_at": "2026-04-28T00:00:00+00:00",
                "phase_completed": "D",
                "reviewer_id": "r",
                "confirmed_at": "2026-04-28T00:00:00+00:00",
                "confirmed_conditions": ["c"],
                "reviewer_confirmation": "explicit",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert result["trusted_writer"] is False


def test_assess_wrong_phase_completed_fails_closed():
    d = _tmp_dir("assess_wrong_phase")
    path = d / "closeout.json"
    path.write_text(
        json.dumps(
            {
                "closeout_schema": CLOSEOUT_SCHEMA,
                "writer_id": CLOSEOUT_WRITER_ID,
                "writer_version": CLOSEOUT_WRITER_VERSION,
                "written_at": "2026-04-28T00:00:00+00:00",
                "phase_completed": "C",  # wrong phase
                "reviewer_id": "r",
                "confirmed_at": "2026-04-28T00:00:00+00:00",
                "confirmed_conditions": ["c"],
                "reviewer_confirmation": "explicit",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert result["trusted_writer"] is False


def test_assess_missing_reviewer_id_fails_closed():
    d = _tmp_dir("assess_missing_reviewer_id")
    path = d / "closeout.json"
    # Write a trusted artifact but with missing reviewer_id
    artifact = {
        "closeout_schema": CLOSEOUT_SCHEMA,
        "writer_id": CLOSEOUT_WRITER_ID,
        "writer_version": CLOSEOUT_WRITER_VERSION,
        "written_at": "2026-04-28T00:00:00+00:00",
        "phase_completed": "D",
        "reviewer_id": "",  # empty
        "confirmed_at": "2026-04-28T00:00:00+00:00",
        "confirmed_conditions": ["c"],
        "reviewer_confirmation": "explicit",
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert "phase_d_closeout_reviewer_id_missing" in result["release_block_reasons"]


def test_assess_empty_confirmed_conditions_fails_closed():
    d = _tmp_dir("assess_empty_conditions")
    path = d / "closeout.json"
    artifact = {
        "closeout_schema": CLOSEOUT_SCHEMA,
        "writer_id": CLOSEOUT_WRITER_ID,
        "writer_version": CLOSEOUT_WRITER_VERSION,
        "written_at": "2026-04-28T00:00:00+00:00",
        "phase_completed": "D",
        "reviewer_id": "r",
        "confirmed_at": "2026-04-28T00:00:00+00:00",
        "confirmed_conditions": [],  # empty
        "reviewer_confirmation": "explicit",
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert "phase_d_closeout_confirmed_conditions_empty" in result["release_block_reasons"]


def test_assess_invalid_json_fails_closed():
    d = _tmp_dir("assess_invalid_json")
    path = d / "closeout.json"
    path.write_text("not valid json", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["available"] is True
    assert result["ok"] is False


def test_assess_missing_confirmed_at_fails_closed():
    """confirmed_at absent → ok=False."""
    d = _tmp_dir("assess_missing_confirmed_at")
    path = d / "closeout.json"
    artifact = {
        "closeout_schema": CLOSEOUT_SCHEMA,
        "writer_id": CLOSEOUT_WRITER_ID,
        "writer_version": CLOSEOUT_WRITER_VERSION,
        "written_at": "2026-04-28T00:00:00+00:00",
        "phase_completed": "D",
        "verdict": "completed",
        "reviewer_id": "reviewer_x",
        # confirmed_at deliberately absent
        "confirmed_conditions": ["c"],
        "reviewer_confirmation": "explicit",
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert "phase_d_closeout_confirmed_at_missing" in result["release_block_reasons"]


def test_assess_empty_confirmed_at_fails_closed():
    """confirmed_at empty string → ok=False."""
    d = _tmp_dir("assess_empty_confirmed_at")
    path = d / "closeout.json"
    artifact = {
        "closeout_schema": CLOSEOUT_SCHEMA,
        "writer_id": CLOSEOUT_WRITER_ID,
        "writer_version": CLOSEOUT_WRITER_VERSION,
        "written_at": "2026-04-28T00:00:00+00:00",
        "phase_completed": "D",
        "verdict": "completed",
        "reviewer_id": "reviewer_x",
        "confirmed_at": "",
        "confirmed_conditions": ["c"],
        "reviewer_confirmation": "explicit",
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert "phase_d_closeout_confirmed_at_missing" in result["release_block_reasons"]


def test_assess_verdict_not_completed_fails_closed():
    """verdict present but not 'completed' → ok=False."""
    d = _tmp_dir("assess_verdict_not_completed")
    path = d / "closeout.json"
    artifact = {
        "closeout_schema": CLOSEOUT_SCHEMA,
        "writer_id": CLOSEOUT_WRITER_ID,
        "writer_version": CLOSEOUT_WRITER_VERSION,
        "written_at": "2026-04-28T00:00:00+00:00",
        "phase_completed": "D",
        "verdict": "pending",
        "reviewer_id": "reviewer_x",
        "confirmed_at": "2026-04-28T10:00:00+00:00",
        "confirmed_conditions": ["c"],
        "reviewer_confirmation": "explicit",
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert "phase_d_closeout_verdict_not_completed" in result["release_block_reasons"]
    assert result["verdict"] == "pending"


def test_assess_verdict_absent_fails_closed():
    """verdict field absent → ok=False."""
    d = _tmp_dir("assess_verdict_absent")
    path = d / "closeout.json"
    artifact = {
        "closeout_schema": CLOSEOUT_SCHEMA,
        "writer_id": CLOSEOUT_WRITER_ID,
        "writer_version": CLOSEOUT_WRITER_VERSION,
        "written_at": "2026-04-28T00:00:00+00:00",
        "phase_completed": "D",
        # verdict deliberately absent
        "reviewer_id": "reviewer_x",
        "confirmed_at": "2026-04-28T10:00:00+00:00",
        "confirmed_conditions": ["c"],
        "reviewer_confirmation": "explicit",
    }
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert "phase_d_closeout_verdict_not_completed" in result["release_block_reasons"]


# ---------------------------------------------------------------------------
# F10/F11: minimum required condition coverage
# ---------------------------------------------------------------------------


def test_assess_missing_required_conditions_fails_closed():
    """Conditions present but not covering REQUIRED_CONDITIONS → ok=False (F10/F11)."""
    d = _tmp_dir("assess_missing_required_conditions")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_x",
        confirmed_conditions=["phase_c_surface_gap_resolved"],  # only 1 of 5
    )

    result = assess_phase_d_closeout(path)

    assert result["ok"] is False
    assert len(result["missing_required_conditions"]) == 4
    missing = result["missing_required_conditions"]
    assert "fail_closed_semantics_accepted" in missing
    assert "no_unresolved_blocking_conditions" in missing
    assert "reviewer_independent_of_author" in missing
    assert "validator_output_reviewed" in missing
    # Each missing condition generates a failure code
    codes = [f["failure_code"] for f in result["failures"]]
    assert any("phase_d_closeout_required_condition_missing:fail_closed_semantics_accepted" == c for c in codes)


def test_assess_all_required_conditions_present_ok():
    """All 5 required conditions present → ok=True."""
    d = _tmp_dir("assess_all_required_conditions")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path,
        reviewer_id="human_reviewer_z",
        confirmed_conditions=_FULL_CONDITIONS,
        confirmed_at="2026-04-28T12:00:00+00:00",
    )

    result = assess_phase_d_closeout(path)

    assert result["ok"] is True
    assert result["missing_required_conditions"] == []
    assert result["failures"] == []


def test_assess_extra_conditions_beyond_required_ok():
    """Extra conditions beyond the required 5 are allowed."""
    d = _tmp_dir("assess_extra_conditions")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_y",
        confirmed_conditions=_FULL_CONDITIONS + ["phase_d_closeout_scope_accepted", "custom_note"],
        confirmed_at="2026-04-28T12:00:00+00:00",
    )

    result = assess_phase_d_closeout(path)

    assert result["ok"] is True
    assert result["missing_required_conditions"] == []


# ---------------------------------------------------------------------------
# Failure structure (FS-1 / FS-2)
# ---------------------------------------------------------------------------


def test_assess_absent_artifact_returns_structured_failure():
    """Absent artifact returns failure with failure_class=blocked."""
    d = _tmp_dir("absent_structured_failure")
    path = d / "nonexistent.json"

    result = assess_phase_d_closeout(path)

    assert result["failures"] == [
        {
            "failure_code": "phase_d_closeout_artifact_absent",
            "failure_class": "blocked",
            "remediation": "procedural_fix",
        }
    ]


def test_assess_failures_list_matches_release_block_reasons():
    """failures list failure_codes match release_block_reasons entries."""
    d = _tmp_dir("failures_match_reasons")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_x",
        confirmed_conditions=["phase_c_surface_gap_resolved"],  # 4 missing
    )

    result = assess_phase_d_closeout(path)

    failure_codes = {f["failure_code"] for f in result["failures"]}
    assert failure_codes == set(result["release_block_reasons"])


def test_assess_all_failures_have_required_fields():
    """Every entry in failures has failure_code, failure_class, remediation."""
    d = _tmp_dir("failure_fields")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_x",
        confirmed_conditions=["only_one"],  # triggers missing conditions
    )

    result = assess_phase_d_closeout(path)

    for entry in result["failures"]:
        assert "failure_code" in entry
        assert "failure_class" in entry
        assert "remediation" in entry
        assert entry["failure_class"] in {"blocked", "void", "presumptively_void"}


# ---------------------------------------------------------------------------
# Exception override (VRB-3 unsupported)
# ---------------------------------------------------------------------------


def test_assess_exception_override_always_false():
    """exception_override_supported is always False in this runtime."""
    d = _tmp_dir("exception_override_false_absent")
    path = d / "nonexistent.json"

    result = assess_phase_d_closeout(path)

    assert result["exception_override_supported"] is EXCEPTION_OVERRIDE_SUPPORTED
    assert result["exception_override_supported"] is False
    assert "VRB-3" in result["exception_override_note"]


def test_assess_exception_override_false_on_valid_artifact():
    """exception_override_supported is False even when artifact is valid."""
    d = _tmp_dir("exception_override_false_valid")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_z",
        confirmed_conditions=_FULL_CONDITIONS,
        confirmed_at="2026-04-28T12:00:00+00:00",
    )

    result = assess_phase_d_closeout(path)

    assert result["exception_override_supported"] is False


# ---------------------------------------------------------------------------
# Runtime-unverifiable conditions (RI-2, RI-4)
# ---------------------------------------------------------------------------


def test_assess_runtime_unverifiable_conditions_always_present():
    """runtime_unverifiable_conditions is always returned."""
    d = _tmp_dir("runtime_unverifiable_present")
    path = d / "nonexistent.json"

    result = assess_phase_d_closeout(path)

    assert result["runtime_unverifiable_conditions"] == RUNTIME_UNVERIFIABLE_CONDITIONS
    codes = [c["failure_code"] for c in result["runtime_unverifiable_conditions"]]
    assert "phase_d_closeout_proxy_review" in codes
    assert "phase_d_closeout_wrong_scope" in codes


def test_assess_runtime_unverifiable_entries_have_detectability():
    """Each runtime-unverifiable entry declares detectability and attestation."""
    d = _tmp_dir("runtime_unverifiable_fields")
    path = d / "closeout.json"
    write_phase_d_closeout(
        path, reviewer_id="r", confirmed_conditions=_FULL_CONDITIONS,
        confirmed_at="2026-04-28T12:00:00+00:00",
    )

    result = assess_phase_d_closeout(path)

    for entry in result["runtime_unverifiable_conditions"]:
        assert entry["detectability"] == "runtime-unverifiable"
        assert entry["attestation"] == "reviewer-attested"
        assert "audit_note" in entry
