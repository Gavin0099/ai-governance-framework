from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.runtime_reliability_observation import (
    DETERMINISM_BOUNDARY_LOG,
    INCIDENT_LOG,
    RECOVERY_LOG,
    SIDE_EFFECT_JOURNAL,
    SCHEMA_VERSION,
    append_observation_event,
)


def _read_last_jsonl(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])


def test_append_observation_event_writes_required_observation_only_fields() -> None:
    tmp_path = Path(".pytest_tmp_runtime_obs")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    event_path = append_observation_event(
        tmp_path,
        INCIDENT_LOG,
        "unit_test_event",
        {"source": "test", "ok": True},
    )
    assert event_path.exists()
    payload = _read_last_jsonl(event_path)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["producer_mode"] == "observation_only"
    assert payload["decision_usage_allowed"] is False
    assert payload["gate_consumption_allowed"] is False
    assert payload["event_type"] == "unit_test_event"
    assert payload["source"] == "test"
    assert payload["ok"] is True
    assert "timestamp_utc" in payload
    shutil.rmtree(tmp_path)


def test_observation_log_paths_are_runtime_artifacts() -> None:
    assert str(INCIDENT_LOG).startswith("artifacts")
    assert str(RECOVERY_LOG).startswith("artifacts")
    assert str(SIDE_EFFECT_JOURNAL).startswith("artifacts")
    assert str(DETERMINISM_BOUNDARY_LOG).startswith("artifacts")


def test_observation_logs_not_consumed_by_gate_or_runtime_policy() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    candidate_files = [
        repo_root / "governance_tools" / "gate_policy.py",
        repo_root / "runtime_hooks" / "core" / "decision_policy_v1_runtime.py",
        repo_root / "governance_tools" / "session_end_hook.py",
    ]
    forbidden_tokens = [
        "incident-log.ndjson",
        "recovery-log.ndjson",
        "side-effect-journal.ndjson",
        "determinism-boundary-log.ndjson",
    ]
    for file in candidate_files:
        text = file.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in text, f"{file} must not consume observation-only artifact {token}"
