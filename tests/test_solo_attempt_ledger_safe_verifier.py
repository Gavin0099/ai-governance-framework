from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.solo_attempt_ledger_safe_verifier import (
    OUTPUT_KEYS,
    render_result,
    verify_pre_attempt_ledger,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_LEDGER = (
    REPO_ROOT
    / "artifacts"
    / "evidence"
    / "solo-evaluation-20260831"
    / "attempt-ledger.ndjson"
)
REAL_LEDGER_SHA256 = "596e798868adae1f9b0fd7d33d6eef6505d947415b95b748381951f3e32e04ab"
SENTINEL_SECRET = "deadc0dedeadc0dedeadc0dedeadc0de"
SECOND_LABEL = "0123456789abcdef0123456789abcdef"


def _synthetic_event() -> dict[str, object]:
    return {
        "schema_version": "solo_attempt_ledger.v1",
        "event_seq": 1,
        "event_id": "11111111-1111-4111-8111-111111111111",
        "event_type": "PAIR_CREATED",
        "timestamp_utc": "2026-08-31T00:00:00Z",
        "pair_id": "solo-pair0-11111111-1111-4111-8111-111111111111",
        "attempt_id": None,
        "slot": "Pair 0",
        "category": "shakedown/simple",
        "repository": "synthetic",
        "arm": None,
        "pair_record": {
            "planned_arms": [
                {
                    "arm": "CONTROL",
                    "anonymous_scoring_label": SENTINEL_SECRET,
                    "treatment_state": "ABSENT",
                    "canonical_attempt_id": None,
                },
                {
                    "arm": "TREATMENT",
                    "anonymous_scoring_label": SECOND_LABEL,
                    "treatment_state": "PACKET_FROZEN",
                    "canonical_attempt_id": None,
                },
            ],
            "label_mapping_scope": "CONTROLLER_ONLY",
            "execution_context_mapping_access": "DENIED",
            "scoring_context_mapping_access": "DENIED",
        },
        "execution_contract": {
            "execution_authorization": "NOT_AUTHORIZED",
            "attempt_id_creation": "DENIED",
        },
        "admission": {
            "execution_authorization": "ABSENT",
            "attempt_id_creation": "BLOCKED",
            "task_exposure": "NOT_EXPOSED",
        },
        "execution": {"arm_executions": 0},
    }


def _write_ledger(path: Path, event: dict[str, object]) -> None:
    path.write_text(
        json.dumps(event, ensure_ascii=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _run_cli(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.solo_attempt_ledger_safe_verifier",
            "--ledger",
            str(path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_no_sensitive_output(completed: subprocess.CompletedProcess[str]) -> None:
    combined = completed.stdout + completed.stderr
    if SENTINEL_SECRET in combined or SECOND_LABEL in combined:
        pytest.fail("SAFE_VERIFIER_EMITTED_SENTINEL", pytrace=False)
    assert "CONTROL" not in combined
    assert "TREATMENT" not in combined
    assert "pair_record" not in combined
    assert "anonymous_scoring_label" not in combined
    assert completed.stderr == ""


def _assert_fixed_flat_output(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    assert tuple(payload.keys()) == OUTPUT_KEYS
    assert all(
        not isinstance(value, (dict, list, tuple, set)) for value in payload.values()
    )
    return payload


def test_success_path_emits_only_allowlisted_scalars(tmp_path: Path) -> None:
    ledger = tmp_path / "success.ndjson"
    _write_ledger(ledger, _synthetic_event())

    completed = _run_cli(ledger)

    assert completed.returncode == 0
    _assert_no_sensitive_output(completed)
    payload = _assert_fixed_flat_output(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["code"] == "OK"
    assert payload["pair_count"] == 1
    assert payload["attempt_count"] == 0
    assert payload["arm_execution_count"] == 0
    assert payload["controller_mapping_structure_present"] is True


def test_failure_path_does_not_emit_nested_sentinel(tmp_path: Path) -> None:
    ledger = tmp_path / "failure.ndjson"
    event = _synthetic_event()
    pair_record = event["pair_record"]
    assert isinstance(pair_record, dict)
    pair_record["label_mapping_scope"] = "INVALID"
    _write_ledger(ledger, event)

    completed = _run_cli(ledger)

    assert completed.returncode == 1
    _assert_no_sensitive_output(completed)
    payload = _assert_fixed_flat_output(completed.stdout)
    assert payload["status"] == "FAIL"
    assert payload["code"] == "MAPPING_STRUCTURE_ERROR"
    assert payload["controller_mapping_structure_present"] is False


def test_real_pair0_ledger_is_safe_and_still_pre_attempt() -> None:
    raw = REAL_LEDGER.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == REAL_LEDGER_SHA256
    event = json.loads(raw.decode("utf-8"))
    pair_record = event["pair_record"]
    labels = [record["anonymous_scoring_label"] for record in pair_record["planned_arms"]]

    result = verify_pre_attempt_ledger(REAL_LEDGER)
    output = render_result(result)

    if any(label in output for label in labels):
        pytest.fail("SAFE_VERIFIER_EMITTED_REAL_CONTROLLER_VALUE", pytrace=False)
    assert result["status"] == "PASS"
    assert result["pair_count"] == 1
    assert result["attempt_count"] == 0
    assert result["arm_execution_count"] == 0
    assert result["task_exposure_count"] == 0
