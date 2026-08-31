from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools.solo_attempt_ledger_v2_safe_verifier import (
    OUTPUT_KEYS,
    render_result,
    verify_public_ledger,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_V1_LEDGER = (
    REPO_ROOT
    / "artifacts"
    / "evidence"
    / "solo-evaluation-20260831"
    / "attempt-ledger.ndjson"
)
REAL_V2_LEDGER = REPO_ROOT / ledger.PUBLIC_LEDGER_PATH
V1_VERIFIER = REPO_ROOT / "governance_tools" / "solo_attempt_ledger_safe_verifier.py"
V1_VERIFIER_SHA256 = (
    "4ef745a4106d98db4a2fbc4323036e421aee8ffd6ffa0a9f55a196726e3310d7"
)
SENTINEL = "SECRET-CONTROLLER-MAPPING-SENTINEL"


def _uuid(number: int) -> str:
    return str(UUID(int=number, version=4))


def _genesis() -> dict[str, object]:
    return {
        "schema_version": ledger.LEDGER_SCHEMA,
        "event_seq": 1,
        "event_type": "V2_GENESIS",
        "event_id": _uuid(1),
        "timestamp_utc": "2026-08-31T00:00:00Z",
        "evaluation_id": _uuid(2),
        "predecessor_digest": ledger.V1_LEDGER_SHA256,
        "adopted_protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
        "adopted_contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
        "adopted_schema_id": ledger.ADOPTED_SCHEMA_ID,
        "legacy_pair_id": ledger.LEGACY_PAIR_ID,
        "legacy_pair_state_at_v1": "PAIR_CREATED",
        "legacy_pair_attempts_used": 0,
        "legacy_pair_disposition": "PRE_ATTEMPT_TERMINATION",
        "attempt_ceiling_total": ledger.ATTEMPT_CEILING_TOTAL,
        "attempt_ceiling_breakdown": dict(ledger.ATTEMPT_CEILING_BREAKDOWN),
    }


def _write_genesis(path: Path) -> None:
    path.write_bytes(ledger.encode_event(_genesis()))


def _run_v2_cli(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.solo_attempt_ledger_v2_safe_verifier",
            "--ledger",
            str(path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_fixed_flat_output(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    assert tuple(payload.keys()) == OUTPUT_KEYS
    assert all(
        not isinstance(value, (dict, list, tuple, set)) for value in payload.values()
    )
    return payload


def test_success_emits_only_fixed_public_scalar_counts(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-v2.ndjson"
    _write_genesis(path)

    completed = _run_v2_cli(path)

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = _assert_fixed_flat_output(completed.stdout)
    assert payload == {
        "verifier_schema": "solo_attempt_ledger_v2_safe_verifier.v1",
        "status": "PASS",
        "code": "OK",
        "schema_version": ledger.LEDGER_SCHEMA,
        "ledger_event_count": 1,
        "pair_count": 0,
        "admitted_attempt_count": 0,
        "initiated_attempt_count": 0,
        "terminal_execution_count": 0,
        "scoring_record_count": 0,
        "unblinding_record_count": 0,
        "attempt_ceiling_total": 14,
        "next_event_seq": 2,
        "public_schema_closed": True,
    }


def test_invalid_closed_schema_genesis_never_passes(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-invalid-genesis-v2.ndjson"
    genesis = _genesis()
    genesis["attempt_ceiling_total"] = 14.0
    path.write_bytes(ledger.encode_event(genesis))

    completed = _run_v2_cli(path)

    assert completed.returncode == 1
    assert completed.stderr == ""
    payload = _assert_fixed_flat_output(completed.stdout)
    assert payload["status"] == "FAIL"
    assert payload["code"] == ledger.LEDGER_SCHEMA_FAILURE


@pytest.mark.parametrize(
    "raw",
    [
        ("{not-json:" + SENTINEL + "}\n").encode(),
        json.dumps({**_genesis(), "controller_state": SENTINEL}).encode() + b"\n",
        (json.dumps(_genesis()) + "\r\n" + SENTINEL).encode(),
    ],
)
def test_failure_never_echoes_raw_or_secret_like_values(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "synthetic-invalid-v2.ndjson"
    path.write_bytes(raw)

    completed = _run_v2_cli(path)

    assert completed.returncode == 1
    assert completed.stderr == ""
    assert SENTINEL not in completed.stdout
    assert "controller_state" not in completed.stdout
    assert "CONTROL" not in completed.stdout
    assert "TREATMENT" not in completed.stdout
    payload = _assert_fixed_flat_output(completed.stdout)
    assert payload["status"] == "FAIL"
    assert payload["code"] in {
        ledger.LEDGER_PARSE_FAILURE,
        ledger.LEDGER_SCHEMA_FAILURE,
    }


def test_missing_ledger_and_bad_arguments_use_fixed_codes(tmp_path: Path) -> None:
    missing = _run_v2_cli(tmp_path / "missing.ndjson")
    assert missing.returncode == 1
    assert missing.stderr == ""
    assert _assert_fixed_flat_output(missing.stdout)["code"] == ledger.LEDGER_PARSE_FAILURE

    completed = subprocess.run(
        [sys.executable, "-m", "governance_tools.solo_attempt_ledger_v2_safe_verifier"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert completed.stderr == ""
    assert _assert_fixed_flat_output(completed.stdout)["code"] == "ARGUMENT_ERROR"


def test_renderer_rejects_added_keys_and_nested_output() -> None:
    result = verify_public_ledger(Path("does-not-exist"))
    result["attempt_handle"] = "e" * 64
    with pytest.raises(ValueError, match="SAFE_OUTPUT_KEY_MISMATCH"):
        render_result(result)

    result = verify_public_ledger(Path("does-not-exist"))
    result["code"] = {"raw": SENTINEL}
    with pytest.raises(ValueError, match="SAFE_OUTPUT_NESTING_REJECTED"):
        render_result(result)


def test_v1_verifier_bytes_and_real_behavior_are_unchanged() -> None:
    assert hashlib.sha256(V1_VERIFIER.read_bytes()).hexdigest() == V1_VERIFIER_SHA256
    assert hashlib.sha256(REAL_V1_LEDGER.read_bytes()).hexdigest() == ledger.V1_LEDGER_SHA256

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.solo_attempt_ledger_safe_verifier",
            "--ledger",
            str(REAL_V1_LEDGER),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["verifier_schema"] == "solo_attempt_ledger_safe_verifier.v1"
    assert payload["status"] == "PASS"
    assert payload["attempt_count"] == 0


def test_canonical_v2_ledger_has_not_been_created() -> None:
    assert not REAL_V2_LEDGER.exists()
