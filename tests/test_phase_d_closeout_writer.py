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
    assess_phase_d_closeout,
    write_phase_d_closeout,
)


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
    assert on_disk["reviewer_id"] == "tier1_reviewer_a"
    assert on_disk["confirmed_conditions"] == conditions
    assert on_disk["reviewer_confirmation"] == "explicit"


def test_write_and_assess_roundtrip_ok():
    d = _tmp_dir("roundtrip")
    path = d / "closeout.json"

    write_phase_d_closeout(
        path,
        reviewer_id="reviewer_x",
        confirmed_conditions=["condition_a"],
    )
    result = assess_phase_d_closeout(path)

    assert result["ok"] is True
    assert result["review_confirmed"] is True
    assert result["trusted_writer"] is True
    assert result["reviewer_id"] == "reviewer_x"
    assert result["confirmed_conditions"] == ["condition_a"]
    assert result["release_block_reasons"] == []


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
