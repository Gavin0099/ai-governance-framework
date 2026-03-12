import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.session_end import run_session_end


@pytest.fixture
def local_project_root():
    path = Path("tests") / "_tmp_session_end"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _contract(**overrides):
    contract = {
        "task": "Runtime governance closeout",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "candidate",
    }
    contract.update(overrides)
    return contract


def test_session_end_auto_promotes_low_risk_candidate(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-01",
        runtime_contract=_contract(),
        checks={"ok": True, "errors": []},
        event_log=[{"event_type": "post_task"}],
        response_text="runtime output",
        summary="Low-risk session",
    )

    assert result["ok"] is True
    assert result["decision"] == "AUTO_PROMOTE"
    assert result["snapshot"] is not None
    assert result["curated"] is not None
    assert result["promotion"] is not None

    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    assert summary_payload["promoted"] is True
    curated_payload = json.loads(Path(result["curated_artifact"]).read_text(encoding="utf-8"))
    assert curated_payload["curation_status"] == "CURATED"


def test_session_end_requires_review_for_high_risk(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-02",
        runtime_contract=_contract(risk="high", oversight="review-required"),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
        summary="High-risk session",
    )

    assert result["ok"] is True
    assert result["decision"] == "REVIEW_REQUIRED"
    assert result["snapshot"] is not None
    assert result["curated"] is not None
    assert result["promotion"] is None


def test_session_end_does_not_promote_stateless_session(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-03",
        runtime_contract=_contract(memory_mode="stateless"),
        checks={"ok": True, "errors": []},
        response_text="runtime output",
    )

    assert result["ok"] is True
    assert result["decision"] == "DO_NOT_PROMOTE"
    assert result["snapshot"] is None


def test_session_end_blocks_missing_contract_fields(local_project_root):
    result = run_session_end(
        project_root=local_project_root,
        session_id="2026-03-12-04",
        runtime_contract={"task": "Broken session", "rules": []},
        checks={"ok": True, "errors": []},
        response_text="runtime output",
    )

    assert result["ok"] is False
    assert any("runtime_contract missing required fields" in error for error in result["errors"])
