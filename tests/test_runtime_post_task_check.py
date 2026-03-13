import sys
from pathlib import Path
import shutil

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.post_task_check import run_post_task_check


def _contract(**overrides) -> str:
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
    body = "\n".join(f"{k} = {v}" for k, v in fields.items())
    return f"[Governance Contract]\n{body}\n"


@pytest.fixture
def local_memory_root():
    path = Path("tests") / "_tmp_post_task_memory"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_post_task_check_passes_for_compliant_output():
    result = run_post_task_check(_contract(), risk="medium", oversight="review-required")
    assert result["ok"] is True


def test_post_task_check_fails_without_contract():
    result = run_post_task_check("no contract here", risk="medium", oversight="review-required")
    assert result["ok"] is False
    assert any("Missing governance contract" in error for error in result["errors"])


def test_post_task_check_fails_high_risk_auto_oversight():
    result = run_post_task_check(_contract(OVERSIGHT="auto"), risk="high", oversight="auto")
    assert result["ok"] is False
    assert any("High-risk" in error for error in result["errors"])


def test_post_task_check_can_create_candidate_snapshot(local_memory_root):
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        memory_root=local_memory_root,
        snapshot_task="Runtime governance",
        snapshot_summary="Snapshot from post-task check",
        create_snapshot=True,
    )
    assert result["ok"] is True
    assert result["snapshot"] is not None
    assert Path(result["snapshot"]["snapshot_path"]).exists()


def test_post_task_check_blocks_durable_memory_without_oversight():
    result = run_post_task_check(
        _contract(MEMORY_MODE="durable", OVERSIGHT="auto"),
        risk="medium",
        oversight="auto",
    )
    assert result["ok"] is False
    assert any("Durable memory" in error for error in result["errors"])


def test_post_task_check_merges_runtime_check_errors():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "warnings": ["Rollback / cleanup coverage was not detected."],
            "errors": ["Missing required failure-test coverage: failure_path"],
        },
    )
    assert result["ok"] is False
    assert any("runtime-check: Missing required failure-test coverage: failure_path" in error for error in result["errors"])
    assert any("runtime-check: Rollback / cleanup coverage was not detected." in warning for warning in result["warnings"])


def test_post_task_check_applies_refactor_evidence_requirements():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_happy_path",
                "tests/test_service.py::test_cleanup_release",
            ],
            "warnings": [],
            "errors": [],
        },
    )
    assert result["ok"] is False
    assert result["refactor_evidence"] is not None
    assert any("refactor-evidence: Missing refactor evidence: regression-oriented test signal" in error for error in result["errors"])
    assert any("refactor-evidence: Missing refactor evidence: interface stability signal" in error for error in result["errors"])


def test_post_task_check_applies_failure_completeness_checks():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": ["tests/test_service.py::test_happy_path"],
            "warnings": [],
            "errors": [],
        },
    )
    assert result["ok"] is False
    assert result["failure_completeness"] is not None
    assert any("failure-completeness: Missing failure completeness evidence: failure-path signal" in error for error in result["errors"])
