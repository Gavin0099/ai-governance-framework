"""Shared parser compatibility and layout regression fixtures."""
from pathlib import Path

import pytest

from governance_tools import state_generator as parser


def test_sprint_nested_sections_keep_all_states_and_full_continuations():
    text = ("## Current Sprint\n### Live\n- [x] Complete\n- [>] Active\n"
            "  if approved\n- [~] Active too\n- [ ] Pending\n"
            "## Other\n- [ ] Outside\n")
    assert parser.parse_sprint_tasks(text) == [
        {"name": "Complete", "done": True}, {"name": "Active\n  if approved", "done": False},
        {"name": "Active too", "done": False}, {"name": "Pending", "done": False},
    ]


def test_backlog_nested_markdown_priorities_and_unreported_group_reset():
    text = ("## Backlog\n### P0\n- [ ] First\n  - [ ] Nested\n### P1\n"
            "- [>] Active, not unchecked\n- [ ] Second\n### P3\n- [ ] Other\n"
            "### Notes\n- [ ] No inherited priority\n## Else\n- [ ] Outside\n")
    assert parser.parse_backlog_counts(text) == {"P0": 2, "P1": 1, "P2": 0}


def test_priority_text_does_not_change_group_and_legacy_view_wins():
    text = ("## Backlog\n### P1\n- [ ] Mention P2 here\n  P0 is prose\n"
            "## Pending Work - Ordered\nP2 - Alternate:\n- [ ] Not counted twice\n")
    assert parser.parse_backlog_counts(text) == {"P0": 0, "P1": 1, "P2": 0}


@pytest.mark.parametrize("marker", ["-", "+", "*", "1."])
def test_list_markers_lazy_continuation_and_sibling_boundary(marker):
    text = f"## Current Sprint\n{marker} [ ] First\nlazy continuation\n- Scope: outside\n- [ ] Second\n"
    assert parser.parse_sprint_tasks(text) == [
        {"name": "First\nlazy continuation", "done": False}, {"name": "Second", "done": False}]


def test_history_is_explicit_not_inferred_from_age_or_completed_items():
    text = ("## Current Sprint - 2020-01-01\n- [x] Past\n- [ ] Still current\n"
            "Historical sprint context:\n- [ ] Old\nCurrent refresh:\n- [ ] Live again\n")
    assert parser.parse_sprint_tasks(text) == [
        {"name": "Past", "done": True}, {"name": "Still current", "done": False},
        {"name": "Live again", "done": False}]


def test_generated_state_keeps_snapshot_authority_and_correct_real_backlog():
    root = Path(__file__).resolve().parents[1]
    result = parser.generate_state(root / "PLAN.md", project_root=root)
    assert result["backlog_counts"] == {"P0": 0, "P1": 4, "P2": 6}
    assert result["state_surface_contract"]["authority_scope"] == "session_context_only"
    assert result["state_surface_contract"]["non_authoritative_for"] == [
        "gate_verdict", "classification_validation", "escalation_closure"]


def test_phase_examples_and_inline_mentions_do_not_override_real_status():
    text = ("```text\n[>] Phase A: Example\n```\n"
            "- [>] Phase E: Current\nExample says [x] Phase E: closed\n")
    assert parser.parse_current_phase(text) == {"id": "PhaseE", "name": "Current"}
    assert parser.parse_gate_status(text) == {"PhaseE": "in_progress"}


def test_unindented_fenced_block_after_blank_is_not_a_list_continuation():
    assert parser.parse_sprint_tasks("## Current Sprint\n- [ ] Work\n\n```text\nexample\n```\n") == [
        {"name": "Work", "done": False}]
