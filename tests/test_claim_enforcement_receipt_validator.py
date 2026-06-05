"""Tests for CE-1C.3: compact claim-enforcement receipt read-side validator.

Validates:
- parse_receipts: valid NDJSON, malformed lines, empty file
- analyse_row: missing fields, policy deviations, presence mismatch
- detect_unreceipted_packets: raw packet exists with/without receipt
- validate_receipts: overall report structure and overall_valid flag
"""

import json
import tempfile
from pathlib import Path

import pytest

from governance_tools.claim_enforcement_receipt_writer import build_receipt, append_receipt
from governance_tools.claim_enforcement_receipt_validator import (
    ALLOWED_EVIDENCE_SCOPE,
    ALLOWED_RAW_PACKET_POLICY,
    ALLOWED_REPO_EVIDENCE_STATUS,
    _RECEIPTS_RELATIVE,
    analyse_row,
    default_raw_packet_roots,
    detect_unreceipted_packets,
    parse_receipts,
    validate_receipts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_receipts(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _good_receipt(session_id: str = "s1") -> dict:
    return build_receipt(
        session_id=session_id,
        source_packet_dir=f"artifacts/claim-enforcement/{session_id}",
        claim_enforcement_check_present=False,
        recorded_at="2026-06-02T10:00:00Z",
    )


# ---------------------------------------------------------------------------
# parse_receipts
# ---------------------------------------------------------------------------


def test_parse_receipts_valid_ndjson():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "receipts.ndjson"
        _write_receipts(path, [_good_receipt("s1"), _good_receipt("s2")])
        rows, errors = parse_receipts(path)
    assert len(rows) == 2
    assert errors == []


def test_parse_receipts_missing_file_returns_empty():
    path = Path("/nonexistent/receipts.ndjson")
    rows, errors = parse_receipts(path)
    assert rows == []
    assert errors == []


def test_parse_receipts_detects_malformed_line():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "receipts.ndjson"
        path.write_text('{"valid": true}\nnot-json\n{"valid": true}\n', encoding="utf-8")
        rows, errors = parse_receipts(path)
    assert len(rows) == 2
    assert len(errors) == 1
    assert errors[0]["line_number"] == 2


def test_parse_receipts_ignores_blank_lines():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "receipts.ndjson"
        path.write_text('\n{"schema_version":"0.1"}\n\n', encoding="utf-8")
        rows, errors = parse_receipts(path)
    assert len(rows) == 1
    assert errors == []


# ---------------------------------------------------------------------------
# analyse_row
# ---------------------------------------------------------------------------


def test_analyse_row_valid_receipt_no_raw_packet(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    row = _good_receipt("s1")
    # source_packet_dir points somewhere that doesn't exist
    result = analyse_row(row, ce_root)
    assert result["missing_fields"] == []
    assert result["policy_deviations"] == []
    assert result["raw_packet_present"] is False
    assert result["receipt_claims_present"] is False
    assert result["presence_mismatch"] is False
    assert result["valid"] is True


def test_analyse_row_presence_mismatch_detected(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    # Build receipt claiming present=True but raw packet doesn't exist
    row = build_receipt(
        session_id="s1",
        source_packet_dir=str(ce_root / "s1"),
        claim_enforcement_check_present=True,
        recorded_at="2026-06-02T10:00:00Z",
    )
    result = analyse_row(row, ce_root)
    assert result["presence_mismatch"] is True
    assert result["valid"] is False


def test_analyse_row_presence_match_when_packet_present(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    packet_dir = ce_root / "s1"
    packet_dir.mkdir(parents=True)
    (packet_dir / "claim-enforcement-check.json").write_text("{}", encoding="utf-8")

    row = build_receipt(
        session_id="s1",
        source_packet_dir=str(packet_dir),
        claim_enforcement_check_present=True,
        recorded_at="2026-06-02T10:00:00Z",
    )
    result = analyse_row(row, ce_root)
    assert result["raw_packet_present"] is True
    assert result["presence_mismatch"] is False
    assert result["valid"] is True


def test_analyse_row_bad_policy_field(tmp_path):
    row = _good_receipt("s1")
    row["raw_packet_policy"] = "unknown_policy"
    result = analyse_row(row, tmp_path)
    assert result["policy_deviations"]
    assert result["valid"] is False


def test_analyse_row_bad_repo_evidence_status(tmp_path):
    row = _good_receipt("s1")
    row["repo_evidence_status"] = "legacy_raw"
    result = analyse_row(row, tmp_path)
    assert result["policy_deviations"]
    assert result["valid"] is False


def test_analyse_row_bad_evidence_scope(tmp_path):
    row = _good_receipt("s1")
    row["evidence_scope"] = "cross_session"
    result = analyse_row(row, tmp_path)
    assert result["policy_deviations"]
    assert result["valid"] is False


def test_analyse_row_missing_required_field(tmp_path):
    row = _good_receipt("s1")
    del row["session_id"]
    result = analyse_row(row, tmp_path)
    assert "session_id" in result["missing_fields"]
    assert result["valid"] is False


# ---------------------------------------------------------------------------
# detect_unreceipted_packets
# ---------------------------------------------------------------------------


def test_detect_unreceipted_no_raw_packets(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    ce_root.mkdir(parents=True)
    result = detect_unreceipted_packets(ce_root, set())
    assert result == []


def test_detect_unreceipted_finds_gap(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    (ce_root / "session-abc").mkdir(parents=True)
    (ce_root / "session-abc" / "claim-enforcement-check.json").write_text("{}", encoding="utf-8")
    result = detect_unreceipted_packets(ce_root, set())
    assert "session-abc" in result


def test_detect_unreceipted_skips_receipted_session(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    (ce_root / "session-abc").mkdir(parents=True)
    (ce_root / "session-abc" / "claim-enforcement-check.json").write_text("{}", encoding="utf-8")
    result = detect_unreceipted_packets(ce_root, {"session-abc"})
    assert result == []


def test_detect_unreceipted_skips_checker_tests(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    (ce_root / "checker-tests").mkdir(parents=True)
    (ce_root / "checker-tests" / "claim-enforcement-check.json").write_text("{}", encoding="utf-8")
    result = detect_unreceipted_packets(ce_root, set())
    assert result == []


def test_detect_unreceipted_skips_dir_without_check_file(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    (ce_root / "session-no-check").mkdir(parents=True)
    # No claim-enforcement-check.json
    result = detect_unreceipted_packets(ce_root, set())
    assert result == []


# ---------------------------------------------------------------------------
# validate_receipts (full report)
# ---------------------------------------------------------------------------


def test_validate_receipts_no_file(tmp_path):
    receipts = tmp_path / _RECEIPTS_RELATIVE
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    report = validate_receipts(receipts, ce_root)
    assert report["file_present"] is False
    assert report["overall_valid"] is False


def test_validate_receipts_valid_file_no_gaps(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    receipts = tmp_path / _RECEIPTS_RELATIVE
    row = _good_receipt("s1")
    _write_receipts(receipts, [row])
    report = validate_receipts(receipts, ce_root)
    assert report["file_present"] is True
    assert report["parse_errors"] == []
    assert report["invalid_rows"] == []
    assert report["unreceipted_packets"] == []
    assert report["overall_valid"] is True


def test_validate_receipts_reports_unreceipted_gap(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    receipts = tmp_path / _RECEIPTS_RELATIVE
    row = _good_receipt("s1")
    _write_receipts(receipts, [row])
    # Add unreceipted raw packet
    (ce_root / "session-orphan").mkdir(parents=True)
    (ce_root / "session-orphan" / "claim-enforcement-check.json").write_text("{}", encoding="utf-8")
    report = validate_receipts(receipts, ce_root)
    assert "session-orphan" in report["unreceipted_packets"]
    assert report["overall_valid"] is False


def test_validate_receipts_reports_parse_error(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    receipts = tmp_path / _RECEIPTS_RELATIVE
    receipts.parent.mkdir(parents=True, exist_ok=True)
    receipts.write_text('not-json\n', encoding="utf-8")
    report = validate_receipts(receipts, ce_root)
    assert len(report["parse_errors"]) == 1
    assert report["overall_valid"] is False


def test_validate_receipts_reports_invalid_row(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    receipts = tmp_path / _RECEIPTS_RELATIVE
    bad_row = _good_receipt("s1")
    bad_row["raw_packet_policy"] = "invalid"
    _write_receipts(receipts, [bad_row])
    report = validate_receipts(receipts, ce_root)
    assert len(report["invalid_rows"]) == 1
    assert report["overall_valid"] is False


def test_default_raw_packet_roots_scans_runtime_before_legacy(tmp_path):
    roots = default_raw_packet_roots(tmp_path)
    assert roots == [
        tmp_path / "artifacts" / "session" / "claim-enforcement",
        tmp_path / "artifacts" / "claim-enforcement",
    ]


def test_validate_receipts_with_cli_default_roots_detects_runtime_gap(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    receipts = tmp_path / _RECEIPTS_RELATIVE
    row = _good_receipt("s1")
    _write_receipts(receipts, [row])

    runtime_root = tmp_path / "artifacts" / "session" / "claim-enforcement"
    (runtime_root / "session-runtime-orphan").mkdir(parents=True)
    (runtime_root / "session-runtime-orphan" / "claim-enforcement-check.json").write_text(
        "{}", encoding="utf-8"
    )

    report = validate_receipts(
        receipts,
        ce_root,
        raw_packet_roots=default_raw_packet_roots(tmp_path),
    )
    assert "session-runtime-orphan" in report["unreceipted_packets"]
    assert report["raw_packet_roots"] == [str(p) for p in default_raw_packet_roots(tmp_path)]
    assert report["overall_valid"] is False


def test_validate_receipts_library_default_remains_legacy_only(tmp_path):
    ce_root = tmp_path / "artifacts" / "claim-enforcement"
    receipts = tmp_path / _RECEIPTS_RELATIVE
    row = _good_receipt("s1")
    _write_receipts(receipts, [row])

    runtime_root = tmp_path / "artifacts" / "session" / "claim-enforcement"
    (runtime_root / "session-runtime-orphan").mkdir(parents=True)
    (runtime_root / "session-runtime-orphan" / "claim-enforcement-check.json").write_text(
        "{}", encoding="utf-8"
    )

    report = validate_receipts(receipts, ce_root)
    assert "session-runtime-orphan" not in report["unreceipted_packets"]
    assert report["raw_packet_roots"] == [str(ce_root)]
