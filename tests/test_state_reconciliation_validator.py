from __future__ import annotations

from pathlib import Path
import shutil

from governance_tools.phase_d_closeout_writer import write_phase_d_closeout
from governance_tools.state_reconciliation_validator import (
    validate_state_reconciliation,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_state_reconciliation_validator" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _write_full_readiness(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Write all four Phase C surface readiness files. Returns (release, p2, p3, auth)."""
    release_surface = tmp_path / "release_surface_overview.py"
    phase2_gate = tmp_path / "phase2_aggregation_consumer.py"
    phase3_gate = tmp_path / "phase3_promotion_gate.py"
    authority_writer = tmp_path / "escalation_authority_writer.py"
    _write(
        release_surface,
        "precedence_applied = True\nlifecycle_effective_by_escalation = {}\n",
    )
    _write(
        phase2_gate,
        'authority_summary = {"precedence_applied": True, "lifecycle_effective_by_escalation": {}}\n',
    )
    _write(phase3_gate, 'authority = payload.get("authority_summary")\n')
    _write(
        authority_writer,
        "lifecycle_effective_by_escalation = {}\n"
        "reason_a = 'authority_precedence_active_blocks_release'\n"
        "reason_b = 'authority_precedence_active_register_overrides_resolved_confirmed'\n",
    )
    return release_surface, phase2_gate, phase3_gate, authority_writer


# ---------------------------------------------------------------------------
# Existing tests: Phase C surface gap detection
# ---------------------------------------------------------------------------


def test_fails_when_phase_d_completed_but_release_surface_precedence_pending():
    tmp_path = _tmp_dir("phase_d_completed_release_pending")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    release_surface = tmp_path / "release_surface_overview.py"
    phase2_gate = tmp_path / "phase2_aggregation_consumer.py"
    phase3_gate = tmp_path / "phase3_promotion_gate.py"
    authority_writer = tmp_path / "escalation_authority_writer.py"
    closeout = tmp_path / "closeout.json"  # absent → closeout_ok=False

    _write(plan, "- [x] Phase D : closeout\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: passed\n")
    _write(release_surface, "def assess_release_surface():\n    return {}\n")
    _write(phase2_gate, "def build_phase2_gate():\n    return {}\n")
    _write(phase3_gate, "def evaluate_phase3_promotion_entry():\n    return {}\n")
    _write(authority_writer, "def assess_authority_directory():\n    return {}\n")

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["ok"] is False
    assert (
        "plan_marks_phase_d_completed_while_phase_c_release_surface_precedence_pending"
        in result["violations"]
    )
    assert (
        "state_marks_phase_d_completed_while_phase_c_release_surface_precedence_pending"
        in result["violations"]
    )
    # Also violated: no closeout artifact
    assert "phase_d_completed_without_reviewer_closeout_artifact" in result["violations"]


def test_passes_when_phase_d_completed_and_release_surface_precedence_ready():
    tmp_path = _tmp_dir("phase_d_completed_release_ready")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"

    _write(plan, "- [x] Phase D : closeout\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: passed\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)
    write_phase_d_closeout(
        closeout,
        reviewer_id="tier1_reviewer_a",
        confirmed_conditions=[
            "reviewer_independent_of_author",
            "phase_c_surface_gap_resolved",
            "validator_output_reviewed",
            "fail_closed_semantics_accepted",
            "no_unresolved_blocking_conditions",
        ],
        confirmed_at="2026-04-28T10:00:00+00:00",
    )

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["ok"] is True
    assert result["violations"] == []
    assert result["closeout_ok"] is True
    assert result["closeout_reviewer_id"] == "tier1_reviewer_a"
    assert result["recommended_phase_d_status"] == "completed"


def test_fails_when_phase_d_still_pending_even_if_original_block_reason_resolved():
    tmp_path = _tmp_dir("phase_d_not_completed_release_pending")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"  # absent — not required when phase_d != passed

    _write(plan, "- [ ] Phase D : reopened\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: pending\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["ok"] is False
    assert (
        "plan_phase_d_still_blocked_while_original_block_reason_resolved"
        in result["violations"]
    )
    assert (
        "state_phase_d_still_blocked_while_original_block_reason_resolved"
        in result["violations"]
    )
    assert result["recommended_phase_d_status"] == "resumable"


# ---------------------------------------------------------------------------
# Closeout gate tests
# ---------------------------------------------------------------------------


def test_fails_when_phase_d_passed_without_closeout_artifact():
    """Phase D = passed, all Phase C signals ready, but no closeout → violation."""
    tmp_path = _tmp_dir("passed_no_closeout")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"  # absent

    _write(plan, "- [x] Phase D : closeout\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: passed\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["ok"] is False
    assert "phase_d_completed_without_reviewer_closeout_artifact" in result["violations"]
    assert result["closeout_ok"] is False
    assert result["closeout_available"] is False


def test_fails_when_phase_d_passed_with_untrusted_closeout():
    """Phase D = passed, closeout file present but writer untrusted → violation."""
    import json

    tmp_path = _tmp_dir("passed_untrusted_closeout")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"

    _write(plan, "- [x] Phase D : closeout\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: passed\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)
    closeout.write_text(
        json.dumps(
            {
                "closeout_schema": "governance.phase_d.closeout.v1",
                "writer_id": "evil.writer",
                "writer_version": "1.0",
                "written_at": "2026-04-28T00:00:00+00:00",
                "phase_completed": "D",
                "reviewer_id": "r",
                "confirmed_at": "2026-04-28T00:00:00+00:00",
                "confirmed_conditions": ["c"],
                "reviewer_confirmation": "explicit",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["ok"] is False
    assert "phase_d_completed_without_reviewer_closeout_artifact" in result["violations"]
    assert result["closeout_ok"] is False


def test_recommended_status_is_resumable_when_phase_c_ready_but_no_closeout():
    """Phase C gap resolved + no closeout → recommended = 'resumable' (not completed)."""
    tmp_path = _tmp_dir("resumable_no_closeout")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"  # absent

    _write(plan, "- [ ] Phase D : reopened (resumable: original_reopen_reason_resolved)\n")
    _write(state, "gate_status:\n  PhaseD: resumable\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["recommended_phase_d_status"] == "resumable"
    assert result["closeout_ok"] is False


def test_recommended_status_is_completed_when_phase_c_ready_and_closeout_present():
    """Phase C gap resolved + valid closeout → recommended = 'completed'."""
    tmp_path = _tmp_dir("recommended_completed")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"

    _write(plan, "- [ ] Phase D : reopened (resumable: original_reopen_reason_resolved)\n")
    _write(state, "gate_status:\n  PhaseD: resumable\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)
    write_phase_d_closeout(
        closeout,
        reviewer_id="reviewer_b",
        confirmed_conditions=[
            "reviewer_independent_of_author",
            "phase_c_surface_gap_resolved",
            "validator_output_reviewed",
            "fail_closed_semantics_accepted",
            "no_unresolved_blocking_conditions",
        ],
    )

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert result["recommended_phase_d_status"] == "completed"
    assert result["closeout_ok"] is True
    assert result["closeout_reviewer_id"] == "reviewer_b"


def test_closeout_not_required_when_phase_d_resumable():
    """Phase D = resumable + no closeout → no closeout violation (only required for 'passed')."""
    tmp_path = _tmp_dir("resumable_no_closeout_no_violation")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    closeout = tmp_path / "closeout.json"  # absent

    _write(plan, "- [ ] Phase D : reopened (resumable: original_reopen_reason_resolved)\n")
    _write(state, "gate_status:\n  PhaseD: resumable\n")
    release_surface, phase2_gate, phase3_gate, authority_writer = _write_full_readiness(tmp_path)

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
        closeout_path=closeout,
    )

    assert "phase_d_completed_without_reviewer_closeout_artifact" not in result["violations"]
    assert result["ok"] is True  # resumable + gap resolved = no violations
