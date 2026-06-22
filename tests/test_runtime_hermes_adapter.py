from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime_hooks.adapters.hermes.normalize_event import normalize_event

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "runtime_hooks" / "examples" / "hermes"

REQUIRED = ("event_type", "project_root", "risk", "oversight", "memory_mode")
RISK = {"low", "medium", "high"}
OVERSIGHT = {"auto", "review-required", "human-approval"}
EVENT_TYPES = {"session_start", "pre_task", "post_task"}


def _native(event_type: str) -> dict:
    return json.loads((EXAMPLES / f"{event_type}.native.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("event_type", sorted(EVENT_TYPES))
def test_hermes_fixture_normalizes_to_valid_shared_event(event_type: str) -> None:
    normalized = normalize_event(_native(event_type), event_type)
    for field in REQUIRED:
        assert normalized.get(field) not in (None, ""), f"missing required field {field}"
    assert normalized["event_type"] == event_type
    assert normalized["risk"] in RISK
    assert normalized["oversight"] in OVERSIGHT
    assert normalized["metadata"]["harness"] == "hermes"
    # The accepted-input note is not a contract field and must not leak through.
    assert "_note" not in normalized


def test_hermes_post_task_has_response_file() -> None:
    # event_schema.json requires response_file for post_task; output_file maps to it.
    normalized = normalize_event(_native("post_task"), "post_task")
    assert normalized.get("response_file") not in (None, "")


def test_hermes_native_aliases_map_to_canonical_fields() -> None:
    normalized = normalize_event(_native("pre_task"), "pre_task")
    # workspace->project_root, request->task, rule_packs->rules, run_id->session_id
    assert normalized["project_root"] == "."
    assert normalized["task"]
    assert normalized["rules"] == ["common", "python"]
    assert normalized["metadata"]["session_id"] == "hermes-run-01"


def test_hermes_cron_artifact_fixture_maps_to_response_file() -> None:
    normalized = normalize_event(_native("post_task.cron_artifact"), "post_task")
    assert normalized["project_root"] == "."
    assert normalized["task"] == "Validate Hermes cron artifact attestation mapping"
    assert normalized["rules"] == ["common", "python"]
    assert normalized["risk"] == "medium"
    assert normalized["oversight"] == "review-required"
    assert normalized["memory_mode"] == "candidate"
    assert normalized["response_file"] == "runtime_hooks/examples/hermes/cron_output.5bf23ff.md"
    assert normalized["metadata"]["session_id"] == "hermes-session-5bf23ff-cron-01"
    assert normalized["metadata"]["native_event_type"] == "post_task"
