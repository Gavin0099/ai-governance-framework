import json
import shutil
from pathlib import Path

import pytest

from governance_tools.runtime_phase_policy import build_phase_classification, load_runtime_phase_policy
from runtime_hooks.core.post_task_check import run_post_task_check
from runtime_hooks.core.pre_task_check import run_pre_task_check
from runtime_hooks.core.session_end import run_session_end


class _FreshnessStub:
    def __init__(self, status="FRESH", days_since_update=0, threshold_days=7):
        self.status = status
        self.days_since_update = days_since_update
        self.threshold_days = threshold_days


@pytest.fixture()
def local_phase_root():
    path = Path("tests") / "_tmp_runtime_phase_execution_policy"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _contract_text(**overrides) -> str:
    fields = {
        "LANG": "C++",
        "LEVEL": "L2",
        "SCOPE": "feature",
        "PLAN": "PLAN.md",
        "LOADED": "SYSTEM_PROMPT, HUMAN-OVERSIGHT",
        "CONTEXT": "repo -> runtime-governance; NOT: platform rewrite",
        "PRESSURE": "SAFE (20/200)",
        "RULES": "common,python",
        "RISK": "medium",
        "OVERSIGHT": "review-required",
        "MEMORY_MODE": "candidate",
    }
    fields.update(overrides)
    return "[Governance Contract]\n" + "\n".join(f"{k} = {v}" for k, v in fields.items()) + "\n"


def _runtime_contract(**overrides) -> dict:
    payload = {
        "task": "Runtime phase summary",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "candidate",
    }
    payload.update(overrides)
    return payload


def test_runtime_phase_policy_loader_and_classifier() -> None:
    policy = load_runtime_phase_policy()
    assert policy["schema_version"] == "0.1"
    assert policy["rules"]["sync_gate_blocks_execution"] is True

    classification = build_phase_classification(
        action_ids=["precondition_gate", "required_evidence_missing", "reviewer_promotion_decision"],
        hook="test_hook",
    )
    assert classification["phase_summary"]["sync_gate"] == ["precondition_gate"]
    assert classification["phase_summary"]["sync_advisory"] == ["required_evidence_missing"]
    assert classification["phase_summary"]["manual_review_only"] == ["reviewer_promotion_decision"]


def test_pre_task_check_emits_phase_classification(local_phase_root, monkeypatch) -> None:
    monkeypatch.setattr("runtime_hooks.core.pre_task_check.check_freshness", lambda _: _FreshnessStub())
    (local_phase_root / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = run_pre_task_check(
        local_phase_root,
        rules="common",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
    )

    phase_summary = result["phase_classification"]["phase_summary"]
    assert phase_summary["sync_gate"] == ["precondition_gate"]


def test_post_task_check_emits_phase_classification_for_required_evidence_missing() -> None:
    result = run_post_task_check(
        _contract_text(),
        risk="medium",
        oversight="review-required",
        checks={
            "required_runtime_evidence": ["public-api-diff"],
            "warnings": [],
            "errors": [],
        },
    )

    phase_summary = result["phase_classification"]["phase_summary"]
    assert phase_summary["sync_advisory"] == ["required_evidence_missing"]


def test_session_end_writes_runtime_phase_summary_artifact(local_phase_root) -> None:
    result = run_session_end(
        project_root=local_phase_root,
        session_id="2026-04-24-phase-policy",
        runtime_contract=_runtime_contract(),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
        summary="Runtime phase execution policy",
        session_start_phase_classification={
            "schema_version": "0.1",
            "hook": "pre_task_check",
            "actions": [{"action": "precondition_gate", "phase": "sync_gate"}],
            "phase_summary": {"sync_gate": ["precondition_gate"]},
            "rules": {"sync_gate_blocks_execution": True},
            "unknown_actions": [],
        },
    )

    artifact_path = Path(result["runtime_phase_summary_artifact"])
    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["phase_summary"]["sync_gate"] == ["precondition_gate"]
    assert payload["phase_summary"]["async_closeout"] == ["canonical_closeout", "daily_memory_append"]
    assert payload["phase_summary"]["async_audit"] == ["memory_candidate_snapshot", "memory_promotion_candidate"]
