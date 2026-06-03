"""Tests for CE-1C.1: compact claim-enforcement receipt writer.

Validates:
- build_receipt() emits all CE-1B required fields
- append_receipt() produces valid append-only NDJSON
- write_receipt_for_session() resolves packet presence correctly
- validate_receipt_fields() catches missing fields
"""

import json
import tempfile
from pathlib import Path

import pytest

from governance_tools.claim_enforcement_receipt_writer import (
    CE1B_REQUIRED_FIELDS,
    ARTIFACT_TYPE,
    SCHEMA_VERSION,
    append_receipt,
    build_receipt,
    validate_receipt_fields,
    write_receipt_for_session,
)


# ---------------------------------------------------------------------------
# build_receipt
# ---------------------------------------------------------------------------


def test_build_receipt_contains_all_required_fields():
    receipt = build_receipt(
        session_id="test-session-001",
        source_packet_dir="artifacts/claim-enforcement/test-session-001",
        claim_enforcement_check_present=False,
    )
    missing = validate_receipt_fields(receipt)
    assert missing == [], f"Missing CE-1B fields: {missing}"


def test_build_receipt_fixed_values():
    receipt = build_receipt(
        session_id="test-session-001",
        source_packet_dir="artifacts/claim-enforcement/test-session-001",
        claim_enforcement_check_present=True,
    )
    assert receipt["schema_version"] == SCHEMA_VERSION
    assert receipt["artifact_type"] == ARTIFACT_TYPE
    assert receipt["raw_packet_policy"] == "session_local"
    assert receipt["repo_evidence_status"] == "compact_receipt"
    assert receipt["evidence_scope"] == "session_scoped"


def test_build_receipt_uses_provided_recorded_at():
    ts = "2026-06-02T10:00:00Z"
    receipt = build_receipt(
        session_id="s1",
        source_packet_dir="artifacts/claim-enforcement/s1",
        claim_enforcement_check_present=False,
        recorded_at=ts,
    )
    assert receipt["recorded_at"] == ts


def test_build_receipt_auto_recorded_at_is_utc_iso():
    receipt = build_receipt(
        session_id="s2",
        source_packet_dir="artifacts/claim-enforcement/s2",
        claim_enforcement_check_present=False,
    )
    # Should be parseable and end with Z
    ts = receipt["recorded_at"]
    assert ts.endswith("Z"), f"Expected UTC timestamp ending in Z, got: {ts!r}"


def test_build_receipt_check_present_true_and_false():
    r_true = build_receipt("s", "p", claim_enforcement_check_present=True)
    r_false = build_receipt("s", "p", claim_enforcement_check_present=False)
    assert r_true["claim_enforcement_check_present"] is True
    assert r_false["claim_enforcement_check_present"] is False


# ---------------------------------------------------------------------------
# validate_receipt_fields
# ---------------------------------------------------------------------------


def test_validate_receipt_fields_empty_dict_lists_all_required():
    missing = validate_receipt_fields({})
    assert set(missing) == CE1B_REQUIRED_FIELDS


def test_validate_receipt_fields_complete_receipt_returns_empty():
    receipt = build_receipt("s", "p", False)
    assert validate_receipt_fields(receipt) == []


def test_validate_receipt_fields_partial_missing():
    receipt = {"schema_version": "0.1", "artifact_type": "claim-enforcement-receipt"}
    missing = validate_receipt_fields(receipt)
    assert "session_id" in missing
    assert "schema_version" not in missing


# ---------------------------------------------------------------------------
# append_receipt (NDJSON append-only)
# ---------------------------------------------------------------------------


def test_append_receipt_creates_file_and_writes_valid_ndjson():
    receipt = build_receipt("s1", "artifacts/claim-enforcement/s1", False)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "receipts.ndjson"
        append_receipt(receipt, path)
        assert path.exists()
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["session_id"] == "s1"


def test_append_receipt_is_append_only():
    r1 = build_receipt("s1", "p1", False, recorded_at="2026-06-02T01:00:00Z")
    r2 = build_receipt("s2", "p2", True, recorded_at="2026-06-02T02:00:00Z")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "receipts.ndjson"
        append_receipt(r1, path)
        append_receipt(r2, path)
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["session_id"] == "s1"
        assert json.loads(lines[1])["session_id"] == "s2"


def test_append_receipt_each_line_is_valid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "receipts.ndjson"
        for i in range(3):
            r = build_receipt(f"session-{i}", f"p{i}", False)
            append_receipt(r, path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            obj = json.loads(line)
            assert validate_receipt_fields(obj) == []


def test_append_receipt_creates_parent_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        nested = Path(tmpdir) / "a" / "b" / "receipts.ndjson"
        receipt = build_receipt("s", "p", False)
        append_receipt(receipt, nested)
        assert nested.exists()


# ---------------------------------------------------------------------------
# write_receipt_for_session
# ---------------------------------------------------------------------------


def _make_fake_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repo structure."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "artifacts" / "claim-enforcement").mkdir(parents=True)
    return tmp_path


def test_write_receipt_for_session_packet_absent():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_fake_repo(Path(tmpdir))
        receipt = write_receipt_for_session("session-abc", repo_root=repo)
        assert receipt["claim_enforcement_check_present"] is False
        assert receipt["session_id"] == "session-abc"


def test_write_receipt_for_session_packet_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_fake_repo(Path(tmpdir))
        # CE-1D.2: raw packet now lives at the runtime-ignored path.
        packet_dir = repo / "artifacts" / "session" / "claim-enforcement" / "session-xyz"
        packet_dir.mkdir(parents=True)
        (packet_dir / "claim-enforcement-check.json").write_text("{}", encoding="utf-8")

        receipt = write_receipt_for_session("session-xyz", repo_root=repo)
        assert receipt["claim_enforcement_check_present"] is True


def test_write_receipt_for_session_appends_to_ndjson():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_fake_repo(Path(tmpdir))
        write_receipt_for_session("s1", repo_root=repo)
        write_receipt_for_session("s2", repo_root=repo)

        receipts_path = repo / "artifacts" / "claim-enforcement" / "claim-enforcement-receipts.ndjson"
        lines = receipts_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        ids = [json.loads(l)["session_id"] for l in lines]
        assert ids == ["s1", "s2"]


def test_write_receipt_for_session_all_required_fields_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_fake_repo(Path(tmpdir))
        receipt = write_receipt_for_session("session-check", repo_root=repo)
        assert validate_receipt_fields(receipt) == []
