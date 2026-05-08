import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.memory_significance import (  # noqa: E402
    L3_EVENT_TYPES,
    build_advisory,
    build_candidate,
    classify_significance,
)
from governance_tools.session_end_hook import run_session_end_hook  # noqa: E402


_FIXTURE_ROOT = Path(__file__).parent / "_tmp_memory_significance_v02"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_valid_closeout(repo: Path, task_intent: str = "contract enforcement update") -> None:
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    touched = repo / "src" / "main.cpp"
    touched.parent.mkdir(parents=True, exist_ok=True)
    touched.write_text("int main(){return 0;}\n", encoding="utf-8")
    closeout.write_text(
        "\n".join(
            [
                f"TASK_INTENT: {task_intent}",
                "WORK_COMPLETED: updated src/main.cpp and validated closeout bridge",
                "FILES_TOUCHED: src/main.cpp",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: one week observation window",
                "RECOMMENDED_MEMORY_UPDATE: keep closeout generation enabled",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_l3_event_type_closed_enum_only() -> None:
    level, event_type, _ = classify_significance(
        "architecture contract and enforcement update", {"closeout_status": "valid"}
    )
    assert level == "L3"
    assert event_type in L3_EVENT_TYPES


def test_non_enum_labels_are_not_emitted_as_l3_event_type() -> None:
    # Noisy labels must never leak as L3 event_type values.
    level, event_type, _ = classify_significance(
        "architecture_change_minor contract_update_note", {"closeout_status": "valid"}
    )
    assert not (level == "L3" and event_type not in L3_EVENT_TYPES)
    assert event_type not in {"architecture_change_minor", "contract_update_note"}


def test_advisory_only_is_always_true() -> None:
    candidate = build_candidate(
        repo_root=Path("."),
        session_id="session-x",
        commit_hash="abc1234",
        task_intent="contract enforcement update",
        checks={"closeout_status": "valid"},
    )
    advisory = build_advisory(candidate)
    assert advisory["advisory_only"] is True


def test_candidate_contains_v02_required_fields() -> None:
    candidate = build_candidate(
        repo_root=Path("."),
        session_id="session-y",
        commit_hash="def5678",
        task_intent="incident root cause analysis",
        checks={"closeout_status": "valid"},
    )
    required = {
        "schema_version",
        "candidate_id",
        "repo",
        "session_id",
        "commit_hash",
        "generated_at_utc",
        "significance_level",
        "event_type",
        "why_significant",
        "evidence_links",
        "promotion_state",
        "authority_flags",
        "validation",
    }
    assert required.issubset(candidate.keys())
    assert candidate["schema_version"] == "0.2"
    assert isinstance(candidate["evidence_links"], list)
    assert "canonical_review_required" in candidate["authority_flags"]
    assert "l3_enum_valid" in candidate["validation"]


def test_session_end_hook_memory_significance_failure_does_not_change_gate_outcome(monkeypatch) -> None:
    repo_baseline = _reset_fixture("baseline")
    _write_valid_closeout(repo_baseline)
    baseline = run_session_end_hook(repo_baseline)

    repo_fail = _reset_fixture("forced_failure")
    _write_valid_closeout(repo_fail)

    def _raise(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("forced memory significance failure")

    monkeypatch.setattr("governance_tools.session_end_hook.write_candidate_and_advisory", _raise)
    failed = run_session_end_hook(repo_fail)

    assert failed["closeout_status"] == baseline["closeout_status"] == "valid"
    assert failed["gate_policy"]["blocked"] == baseline["gate_policy"]["blocked"]
    assert failed["ok"] == baseline["ok"]
    assert any("[memory_significance] advisory generation failed:" in w for w in failed["warnings"])

