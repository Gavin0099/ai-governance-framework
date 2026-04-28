from __future__ import annotations

from pathlib import Path
import shutil

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


def test_fails_when_phase_d_completed_but_release_surface_precedence_pending():
    tmp_path = _tmp_dir("phase_d_completed_release_pending")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    release_surface = tmp_path / "release_surface_overview.py"
    phase2_gate = tmp_path / "phase2_aggregation_consumer.py"
    phase3_gate = tmp_path / "phase3_promotion_gate.py"
    authority_writer = tmp_path / "escalation_authority_writer.py"

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


def test_passes_when_phase_d_completed_and_release_surface_precedence_ready():
    tmp_path = _tmp_dir("phase_d_completed_release_ready")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    release_surface = tmp_path / "release_surface_overview.py"
    phase2_gate = tmp_path / "phase2_aggregation_consumer.py"
    phase3_gate = tmp_path / "phase3_promotion_gate.py"
    authority_writer = tmp_path / "escalation_authority_writer.py"

    _write(plan, "- [x] Phase D : closeout\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: passed\n")
    _write(
        release_surface,
        "precedence_applied = True\n"
        "lifecycle_effective_by_escalation = {}\n",
    )
    _write(
        phase2_gate,
        'authority_summary = {"precedence_applied": True, "lifecycle_effective_by_escalation": {}}\n',
    )
    _write(
        phase3_gate,
        'authority = payload.get("authority_summary")\n',
    )
    _write(
        authority_writer,
        "lifecycle_effective_by_escalation = {}\n"
        "reason_a = 'authority_precedence_active_blocks_release'\n"
        "reason_b = 'authority_precedence_active_register_overrides_resolved_confirmed'\n",
    )

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
    )

    assert result["ok"] is True
    assert result["violations"] == []


def test_fails_when_phase_d_still_pending_even_if_original_block_reason_resolved():
    tmp_path = _tmp_dir("phase_d_not_completed_release_pending")
    plan = tmp_path / "PLAN.md"
    state = tmp_path / ".governance-state.yaml"
    release_surface = tmp_path / "release_surface_overview.py"
    phase2_gate = tmp_path / "phase2_aggregation_consumer.py"
    phase3_gate = tmp_path / "phase3_promotion_gate.py"
    authority_writer = tmp_path / "escalation_authority_writer.py"

    _write(plan, "- [ ] Phase D : reopened\n- [>] Phase E : runtime\n")
    _write(state, "gate_status:\n  PhaseD: pending\n")
    _write(
        release_surface,
        "precedence_applied = True\n"
        "lifecycle_effective_by_escalation = {}\n",
    )
    _write(
        phase2_gate,
        'authority_summary = {"precedence_applied": True, "lifecycle_effective_by_escalation": {}}\n',
    )
    _write(
        phase3_gate,
        'authority = payload.get("authority_summary")\n',
    )
    _write(
        authority_writer,
        "lifecycle_effective_by_escalation = {}\n"
        "reason_a = 'authority_precedence_active_blocks_release'\n"
        "reason_b = 'authority_precedence_active_register_overrides_resolved_confirmed'\n",
    )

    result = validate_state_reconciliation(
        plan_path=plan,
        state_path=state,
        release_surface_path=release_surface,
        phase2_gate_path=phase2_gate,
        phase3_gate_path=phase3_gate,
        authority_writer_path=authority_writer,
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
