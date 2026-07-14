from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from governance_tools import processed_closeout_check as checker


BASE_TIME = datetime(2026, 7, 14, 8, 0, 0, tzinfo=timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_closeout(
    project_root: Path,
    *,
    text: str = "driver handoff\n",
    mtime: datetime = BASE_TIME,
) -> Path:
    closeout = project_root / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(text, encoding="utf-8")
    timestamp = mtime.timestamp()
    os.utime(closeout, (timestamp, timestamp))
    return closeout


def _write_receipt(
    project_root: Path,
    *,
    closeout: Path,
    timestamp: datetime = BASE_TIME + timedelta(seconds=10),
    filename: str = "closeout_receipt_current.json",
    schema_version: str = "1.3",
    entrypoint: str = checker.CANONICAL_ENTRYPOINT,
    closeout_artifact_path: str | None = None,
    checksum: str | None = None,
    exit_code: int = 0,
    eligibility_evaluated: bool = True,
    write_required: bool = False,
    write_performed: bool = False,
    write_verified: bool = False,
    receipt_mtime: datetime | None = None,
) -> Path:
    receipt_dir = project_root / checker.DEFAULT_RECEIPT_DIR
    receipt_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": schema_version,
        "timestamp": timestamp.isoformat(),
        "agent_id": "test-agent",
        "trigger_mode": "unknown",
        "entrypoint": entrypoint,
        "exit_code": exit_code,
        "closeout_artifact_path": closeout_artifact_path or str(closeout.resolve()),
        "checksum_of_cleaned_path": checksum if checksum is not None else _sha256(closeout),
        "memory_eligibility_evaluated": eligibility_evaluated,
        "memory_write_required": write_required,
        "memory_write_performed": write_performed,
        "memory_eligibility_reason": "test",
        "memory_write_claim_verified": write_verified,
    }
    receipt = receipt_dir / filename
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    if receipt_mtime is not None:
        value = receipt_mtime.timestamp()
        os.utime(receipt, (value, value))
    return receipt


def _snapshot_files(project_root: Path) -> list[tuple[str, int, int, str]]:
    snapshot = []
    for path in sorted(item for item in project_root.rglob("*") if item.is_file()):
        stat = path.stat()
        snapshot.append(
            (
                path.relative_to(project_root).as_posix(),
                stat.st_mtime_ns,
                stat.st_size,
                _sha256(path),
            )
        )
    return snapshot


def test_missing_closeout_is_incomplete_and_nonblocking(tmp_path: Path) -> None:
    report = checker.build_processed_closeout_report(tmp_path)

    assert report["report_only"] is True
    assert report["closeout_handoff_complete"] is False
    assert report["reason_code"] == "closeout_artifact_not_present"
    assert checker.main(["--project-root", str(tmp_path), "--format", "json"]) == 0


def test_non_regular_closeout_is_incomplete(tmp_path: Path) -> None:
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.mkdir(parents=True)

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_exists"] is True
    assert report["reason_code"] == "closeout_artifact_not_regular_file"


def test_closeout_without_receipts_is_incomplete(tmp_path: Path) -> None:
    _create_closeout(tmp_path)

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is False
    assert report["reason_code"] == "matching_receipt_not_present"
    assert report["matching_receipt_path"] == ""


def test_unrelated_path_and_noncanonical_entrypoint_are_ignored(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    other = tmp_path / "artifacts" / "other-closeout.txt"
    other.write_text("other\n", encoding="utf-8")
    _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_other_path.json",
        closeout_artifact_path=str(other.resolve()),
    )
    _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_other_entrypoint.json",
        entrypoint="some.other.entrypoint",
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["reason_code"] == "matching_receipt_not_present"


def test_matching_failed_receipt_is_incomplete(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(tmp_path, closeout=closeout, exit_code=7)

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["reason_code"] == "matching_receipt_failed"
    assert report["receipt_exit_code"] == 7


def test_receipt_older_than_closeout_is_incomplete_even_when_checksum_matches(
    tmp_path: Path,
) -> None:
    closeout = _create_closeout(tmp_path, mtime=BASE_TIME + timedelta(seconds=20))
    _write_receipt(tmp_path, closeout=closeout, timestamp=BASE_TIME + timedelta(seconds=10))

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["checksum_matches"] is True
    assert report["reason_code"] == "closeout_newer_than_receipt"


def test_newer_receipt_with_changed_content_reports_checksum_mismatch(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(
        tmp_path,
        closeout=closeout,
        timestamp=BASE_TIME + timedelta(seconds=20),
        checksum="0" * 64,
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["checksum_matches"] is False
    assert report["reason_code"] == "closeout_checksum_mismatch"


@pytest.mark.parametrize("schema_version", sorted(checker.SUPPORTED_RECEIPT_SCHEMAS))
def test_supported_receipt_without_required_memory_write_is_complete(
    tmp_path: Path,
    schema_version: str,
) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(
        tmp_path,
        closeout=closeout,
        schema_version=schema_version,
        write_required=False,
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is True
    assert report["reason_code"] == "closeout_handoff_complete"
    assert report["matching_receipt_schema_version"] == schema_version


@pytest.mark.parametrize(
    ("eligibility", "required", "performed", "verified", "reason"),
    [
        (False, False, False, False, "memory_eligibility_not_evaluated"),
        (True, True, False, False, "required_memory_write_not_performed"),
        (True, True, True, False, "memory_write_claim_not_verified"),
    ],
)
def test_memory_outcome_failures_remain_incomplete(
    tmp_path: Path,
    eligibility: bool,
    required: bool,
    performed: bool,
    verified: bool,
    reason: str,
) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(
        tmp_path,
        closeout=closeout,
        eligibility_evaluated=eligibility,
        write_required=required,
        write_performed=performed,
        write_verified=verified,
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is False
    assert report["reason_code"] == reason


def test_required_performed_and_verified_memory_write_is_complete(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(
        tmp_path,
        closeout=closeout,
        write_required=True,
        write_performed=True,
        write_verified=True,
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is True
    assert report["memory_write_required"] is True
    assert report["memory_write_performed"] is True
    assert report["memory_write_claim_verified"] is True


def test_malformed_and_unsupported_receipts_are_visible_without_hiding_valid_receipt(
    tmp_path: Path,
) -> None:
    closeout = _create_closeout(tmp_path)
    valid = _write_receipt(tmp_path, closeout=closeout, filename="closeout_receipt_valid.json")
    receipt_dir = valid.parent
    (receipt_dir / "closeout_receipt_malformed.json").write_text("{", encoding="utf-8")
    (receipt_dir / "closeout_receipt_invalid_utf8.json").write_bytes(b"\xff")
    _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_schema_1_0.json",
        schema_version="1.0",
        timestamp=BASE_TIME + timedelta(seconds=20),
    )
    _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_schema_unknown.json",
        schema_version="9.9",
        timestamp=BASE_TIME + timedelta(seconds=30),
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is True
    assert report["matching_receipt_path"] == str(valid.resolve())
    assert report["ignored_malformed_receipt_count"] == 2
    assert report["ignored_unsupported_receipt_count"] == 2


def test_naive_receipt_timestamp_is_malformed_diagnostic(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    receipt = _write_receipt(tmp_path, closeout=closeout)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["timestamp"] = "2026-07-14T08:00:10"
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["reason_code"] == "matching_receipt_not_present"
    assert report["ignored_malformed_receipt_count"] == 1


def test_schema_1_1_without_claim_verification_field_is_malformed(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    receipt = _write_receipt(tmp_path, closeout=closeout, schema_version="1.1")
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    del payload["memory_write_claim_verified"]
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is False
    assert report["reason_code"] == "matching_receipt_not_present"
    assert report["ignored_malformed_receipt_count"] == 1


def test_latest_selection_uses_payload_timestamp_not_filename_or_file_mtime(
    tmp_path: Path,
) -> None:
    closeout = _create_closeout(tmp_path)
    older = _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_zzz.json",
        timestamp=BASE_TIME + timedelta(seconds=10),
        checksum="0" * 64,
        receipt_mtime=BASE_TIME + timedelta(seconds=100),
    )
    newer = _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_aaa.json",
        timestamp=BASE_TIME + timedelta(seconds=20),
        receipt_mtime=BASE_TIME + timedelta(seconds=50),
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert older.name > newer.name
    assert older.stat().st_mtime > newer.stat().st_mtime
    assert report["matching_receipt_path"] == str(newer.resolve())
    assert report["closeout_handoff_complete"] is True


def test_equal_payload_timestamp_uses_normalized_receipt_path_tie_breaker(
    tmp_path: Path,
) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_aaa.json",
        timestamp=BASE_TIME + timedelta(seconds=20),
    )
    selected = _write_receipt(
        tmp_path,
        closeout=closeout,
        filename="closeout_receipt_zzz.json",
        timestamp=BASE_TIME + timedelta(seconds=20),
        checksum="0" * 64,
    )

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["matching_receipt_path"] == str(selected.resolve())
    assert report["reason_code"] == "closeout_checksum_mismatch"


@pytest.mark.skipif(os.name != "nt", reason="Windows path equivalence is Windows-specific")
def test_windows_equivalent_path_case_and_separators_match(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    equivalent = str(closeout.resolve()).swapcase().replace("\\", "/")
    _write_receipt(tmp_path, closeout=closeout, closeout_artifact_path=equivalent)

    report = checker.build_processed_closeout_report(tmp_path)

    assert report["closeout_handoff_complete"] is True


def test_two_runs_are_identical_and_create_no_files(tmp_path: Path) -> None:
    closeout = _create_closeout(tmp_path)
    _write_receipt(tmp_path, closeout=closeout)
    before = _snapshot_files(tmp_path)

    first = checker.build_processed_closeout_report(tmp_path)
    middle = _snapshot_files(tmp_path)
    second = checker.build_processed_closeout_report(tmp_path)
    after = _snapshot_files(tmp_path)

    assert first == second
    assert before == middle == after


def test_human_output_leads_with_plain_conclusion_and_keeps_raw_fields(tmp_path: Path) -> None:
    _create_closeout(tmp_path)
    report = checker.build_processed_closeout_report(tmp_path)

    output = checker.format_human_report(report)

    assert output.splitlines()[0].startswith("Closeout handoff is not complete:")
    assert '"reason_code": "matching_receipt_not_present"' in output
    assert '"report_only": true' in output


def test_json_output_contains_minimum_contract_fields(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _create_closeout(tmp_path)

    exit_code = checker.main(["--project-root", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    minimum_fields = {
        "report_only",
        "closeout_handoff_complete",
        "reason_code",
        "project_root",
        "closeout_artifact_path",
        "closeout_exists",
        "closeout_mtime_utc",
        "closeout_sha256",
        "matching_receipt_path",
        "matching_receipt_timestamp_utc",
        "matching_receipt_schema_version",
        "receipt_exit_code",
        "checksum_matches",
        "memory_eligibility_evaluated",
        "memory_write_required",
        "memory_write_performed",
        "memory_write_claim_verified",
        "ignored_malformed_receipt_count",
        "ignored_unsupported_receipt_count",
    }
    assert exit_code == 0
    assert minimum_fields <= payload.keys()


def test_invalid_cli_usage_exits_two() -> None:
    with pytest.raises(SystemExit) as exc_info:
        checker.main(["--format", "xml"])

    assert exc_info.value.code == 2


def test_unexpected_io_error_exits_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    closeout = _create_closeout(tmp_path)
    receipt = _write_receipt(tmp_path, closeout=closeout)
    original_read_text = Path.read_text

    def fail_for_receipt(path: Path, *args: object, **kwargs: object) -> str:
        if path == receipt:
            raise PermissionError("denied by test")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_for_receipt)

    exit_code = checker.main(["--project-root", str(tmp_path), "--format", "json"])

    assert exit_code == 1
    assert "processed-closeout check failed" in capsys.readouterr().err
