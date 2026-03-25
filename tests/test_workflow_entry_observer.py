from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from governance_tools.workflow_entry_observer import observe_workflow_entry


def _artifact(
    *,
    artifact_type: str,
    skill: str,
    status: str,
    project_root: Path,
    task_text: str,
    content: dict,
    timestamp: datetime | None = None,
    provenance: dict | None = None,
) -> dict:
    return {
        "artifact_type": artifact_type,
        "skill": skill,
        "scope": {
            "task_text": task_text,
            "repo_root": str(project_root.resolve()),
            "changed_surfaces": ["docs/entry-layer-contract.md"],
        },
        "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        "status": status,
        "provenance": provenance or {
            "producer": skill,
            "repository_path": str(project_root.resolve()),
            "framework_version": "1.0.0",
        },
        "content": content,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_observer_reports_missing_artifacts_when_no_files_exist(tmp_path: Path) -> None:
    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text="Add loop")
    assert result["observation_coverage"] == 0.0
    assert "workflow_score" not in result
    assert result["coverage_metric"] == "observation_coverage"
    assert result["state_counts"]["missing"] == 3
    assert result["artifact_observations"]["tech_spec"]["state"] == "missing"
    assert result["artifact_observations"]["tech_spec"]["diagnostics"]["failure_source_class"] == "no_artifact_present"


def test_observer_recognizes_full_closed_loop(tmp_path: Path) -> None:
    task_text = "Add loop"
    task_dir = tmp_path / "artifacts" / "add-loop"
    _write_json(
        task_dir / "tech_spec.json",
        _artifact(
            artifact_type="tech_spec",
            skill="tech-spec",
            status="completed",
            project_root=tmp_path,
            task_text=task_text,
            content={
                "task": task_text,
                "problem": "Need plan",
                "scope": ["x"],
                "non_goals": ["y"],
                "evidence_plan": ["z"],
            },
        ),
    )
    _write_json(
        task_dir / "validation_evidence.json",
        _artifact(
            artifact_type="validation_evidence",
            skill="precommit",
            status="passed",
            project_root=tmp_path,
            task_text=task_text,
            content={
                "entrypoint": "scripts/run-runtime-governance.sh",
                "mode": "enforce",
                "result": "pass",
                "summary": "focused gate passed",
            },
        ),
    )
    _write_json(
        task_dir / "pr_handoff.json",
        _artifact(
            artifact_type="pr_handoff",
            skill="create-pr",
            status="completed",
            project_root=tmp_path,
            task_text=task_text,
            content={
                "change_summary": "Added loop",
                "scope_included": ["a"],
                "scope_excluded": ["b"],
                "risk_summary": "low",
                "evidence_summary": ["focused tests"],
            },
        ),
    )

    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text=task_text)
    assert result["observation_coverage"] == 1.0
    assert result["recognized_artifact_count"] == 3
    assert result["state_counts"]["recognized"] == 3
    assert result["semantic_boundary"]["artifact_recognizer_only"] is True
    assert result["semantic_boundary"]["not_a_workflow_fact"] is True


def test_observer_marks_scope_mismatch_as_unverifiable(tmp_path: Path) -> None:
    task_dir = tmp_path / "artifacts" / "add-loop"
    _write_json(
        task_dir / "tech_spec.json",
        _artifact(
            artifact_type="tech_spec",
            skill="tech-spec",
            status="completed",
            project_root=tmp_path,
            task_text="Different task",
            content={
                "task": "Different task",
                "problem": "Need plan",
                "scope": ["x"],
                "non_goals": ["y"],
                "evidence_plan": ["z"],
            },
        ),
    )
    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text="Add loop")
    assert result["artifact_observations"]["tech_spec"]["state"] == "unverifiable"
    assert result["state_counts"]["unverifiable"] == 1
    assert (
        result["artifact_observations"]["tech_spec"]["diagnostics"]["failure_source_class"]
        == "artifact_present_but_trust_linkage_unavailable"
    )


def test_observer_marks_partial_artifact_as_incomplete(tmp_path: Path) -> None:
    task_text = "Add loop"
    task_dir = tmp_path / "artifacts" / "add-loop"
    _write_json(
        task_dir / "validation_evidence.json",
        _artifact(
            artifact_type="validation_evidence",
            skill="precommit",
            status="partial",
            project_root=tmp_path,
            task_text=task_text,
            content={
                "entrypoint": "scripts/run-runtime-governance.sh",
                "mode": "enforce",
                "result": "partial",
                "summary": "smoke ran but pytest skipped",
            },
        ),
    )
    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text=task_text)
    assert result["artifact_observations"]["validation_evidence"]["state"] == "incomplete"
    assert result["state_counts"]["incomplete"] == 1


def test_observer_marks_old_artifact_as_stale(tmp_path: Path) -> None:
    task_text = "Add loop"
    task_dir = tmp_path / "artifacts" / "add-loop"
    _write_json(
        task_dir / "pr_handoff.json",
        _artifact(
            artifact_type="pr_handoff",
            skill="create-pr",
            status="completed",
            project_root=tmp_path,
            task_text=task_text,
            timestamp=datetime.now(timezone.utc) - timedelta(days=30),
            content={
                "change_summary": "Added loop",
                "scope_included": ["a"],
                "scope_excluded": ["b"],
                "risk_summary": "low",
                "evidence_summary": ["focused tests"],
            },
        ),
    )
    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text=task_text)
    assert result["artifact_observations"]["pr_handoff"]["state"] == "stale"
    assert result["state_counts"]["stale"] == 1


def test_observer_surfaces_consumer_guardrails_for_missing_and_unverifiable(tmp_path: Path) -> None:
    task_text = "Add loop"
    task_dir = tmp_path / "artifacts" / "add-loop"
    _write_json(
        task_dir / "tech_spec.json",
        _artifact(
            artifact_type="tech_spec",
            skill="tech-spec",
            status="completed",
            project_root=tmp_path,
            task_text="Different task",
            content={
                "task": "Different task",
                "problem": "Need plan",
                "scope": ["x"],
                "non_goals": ["y"],
                "evidence_plan": ["z"],
            },
        ),
    )

    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text=task_text)
    missing_policy = result["artifact_observations"]["validation_evidence"]["state_policy"]
    unverifiable_policy = result["artifact_observations"]["tech_spec"]["state_policy"]

    assert "task is non-compliant" in missing_policy["forbidden_interpretations"]
    assert "block" in missing_policy["forbidden_consequences"]
    assert "intentional bypass occurred" in unverifiable_policy["forbidden_interpretations"]
    assert "mark_intentional_bypass" in unverifiable_policy["forbidden_consequences"]
    assert result["semantic_boundary"]["consumer_defaults"]["allowed_consequence_levels"] == [
        "hint",
        "advisory_note",
        "reviewer_visible_banner",
    ]
    assert "policy_violation_judgment" in result["semantic_boundary"]["consumer_defaults"]["forbidden_observation_only_conclusions"]
    assert result["semantic_boundary"]["diagnostic_fields"]["failure_source_class"]["role"] == "diagnostic_aid"
    assert "failure_source_class" not in missing_policy
    assert "failure_source_class" not in unverifiable_policy
    assert result["artifact_observations"]["validation_evidence"]["diagnostics"]["failure_source_class"] == "no_artifact_present"
    assert result["artifact_observations"]["tech_spec"]["diagnostics"]["failure_source_class"] == "artifact_present_but_trust_linkage_unavailable"


def test_observer_does_not_let_stale_mask_scope_mismatch(tmp_path: Path) -> None:
    task_text = "Add loop"
    task_dir = tmp_path / "artifacts" / "add-loop"
    _write_json(
        task_dir / "pr_handoff.json",
        _artifact(
            artifact_type="pr_handoff",
            skill="create-pr",
            status="completed",
            project_root=tmp_path,
            task_text="Different task",
            timestamp=datetime.now(timezone.utc) - timedelta(days=30),
            content={
                "change_summary": "Added loop",
                "scope_included": ["a"],
                "scope_excluded": ["b"],
                "risk_summary": "low",
                "evidence_summary": ["focused tests"],
            },
        ),
    )

    result = observe_workflow_entry(project_root=tmp_path, artifacts_root=tmp_path / "artifacts", task_text=task_text)
    observation = result["artifact_observations"]["pr_handoff"]

    assert observation["state"] == "unverifiable"
    assert observation["diagnostics"]["failure_source_class"] == "artifact_present_but_trust_linkage_unavailable"
    assert "scope does not match the current observable context" in observation["reasons"]
