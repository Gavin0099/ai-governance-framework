from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "docs" / "memory-runtime-r0-exact-round-trip-spec.md"
AUTHORITY = REPO_ROOT / "governance" / "AUTHORITY.md"
PLAN = REPO_ROOT / "PLAN.md"
MEMORY_RECORD = REPO_ROOT / "governance_tools" / "memory_record.py"
MEMORY_LAYOUT = REPO_ROOT / "memory_pipeline" / "memory_layout.py"


def _json_block(marker: str) -> Any:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(marker)}:begin -->\s*```json\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(marker)}:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_r0_spec_is_non_authoritative_and_unregistered() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert not text.startswith("---")
    assert "NON-AUTHORITATIVE TECHNICAL\nSPECIFICATION" in text
    assert "is not registered in\n`governance/AUTHORITY.md`" in text
    assert "does not activate a\n  governance authority" in PLAN.read_text(encoding="utf-8")

    authority = AUTHORITY.read_text(encoding="utf-8")
    assert "MEMORY_RUNTIME_R0_EXACT_ROUND_TRIP" not in authority
    assert "memory-runtime-r0-exact-round-trip-spec.md" not in authority


def test_r0_contract_reuses_current_public_dependencies_without_broadening_identity() -> None:
    contract = _json_block("memory-runtime-r0-contract")
    assert contract == {
        "contract_version": "memory-runtime-r0-exact-round-trip.v0.1",
        "logical_name": "active_task",
        "writer": "governance_tools.memory_record.append_projection_with_outcome",
        "writer_surface": "SURFACE_ACTIVE_TASK_SUMMARY",
        "identity_source": "governance_tools.memory_record.build_record_identity",
        "expected_line_source": "governance_tools.memory_record.render_active_task_projection",
        "resolver": "memory_pipeline.memory_layout.resolve_memory_file",
        "rendering": "verbatim_retrieved_projection_line",
        "non_target_candidate_policy": "ignore_if_structurally_valid",
        "allowed_write_statuses": ["written", "already_present"],
        "resolution_states": [
            "resolved",
            "reviewer_required",
            "disputed",
            "insufficient_authority",
            "unassessable",
        ],
        "m1_observation_binding": {
            "query_class": "current_progress",
            "logical_name": "active_task",
            "requested_record_identity": "must_equal_caller_authorized_record_identity",
            "resolved_record_identity": "must_equal_writer_outcome_identity_when_resolved",
        },
        "failure_mode": "fail_closed",
        "mrcsp_composition": "caller_admitted_observation_only_no_detector_call",
        "implementation_authorized": False,
    }

    writer = MEMORY_RECORD.read_text(encoding="utf-8")
    layout = MEMORY_LAYOUT.read_text(encoding="utf-8")
    for public_name in (
        "def append_projection_with_outcome(",
        "def build_record_identity(",
        "def render_active_task_projection(",
        'SURFACE_ACTIVE_TASK_SUMMARY = "active-task-summary"',
        'MEMORY_WRITE_STATUS_WRITTEN = "written"',
        'MEMORY_WRITE_STATUS_ALREADY_PRESENT = "already_present"',
    ):
        assert public_name in writer
    assert "def resolve_memory_file(" in layout

    text = CONTRACT.read_text(encoding="utf-8")
    assert "defines the stable\n  identity used by canonical same-day deduplication" in text
    assert re.search(r"must\s+not\s+copy `_RECORD_IDENTITY_FIELDS`", text)
    assert "It must not call or copy private summary-normalization helpers" in text


def test_r0_contract_freezes_identity_content_path_and_set_invariants() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for required in (
        "caller-authorized canonical record identity",
        "canonical writer outcome identity",
        "persisted projection marker identity",
        "retrieved projection marker identity",
        "context-rendering provenance identity",
        "same-identity line with different summary bytes",
        "If the writer outcome path and resolver path do\nnot match",
        "set(context-rendered record identities) = set(E identities)",
        "count(context-rendered records) = |E|",
    ):
        assert required in text


def test_r0_spec_allows_well_formed_historical_non_target_identities() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "another identity is a permitted\nhistorical non-target record" in text
    assert "ignored for target selection" in text
    assert "Its presence\nis not corruption" in text
    assert "exactly one candidate for the\nexpected identity" in text
    assert "well_formed_non_target_identities_are_ignored" in text


def test_r0_contract_preserves_m1_states_and_keeps_m1b3_caller_admitted() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for state in (
        "reviewer_required",
        "disputed",
        "insufficient_authority",
        "unassessable",
    ):
        assert state in text
    assert re.search(r"states must be returned unchanged\s+with zero rendered records", text)
    assert "`query_class` is exactly `current_progress`" in text
    assert "whose `logical_name` is exactly\n`active_task`" in text
    assert "`requested_record_identity` equals the\ncaller-authorized canonical record identity" in text
    assert re.search(
        r"`resolved_record_identity` equal to the canonical writer outcome\s+identity",
        text,
    )
    assert "Missing or mismatched binding fields fail closed with `ValueError`" in text
    assert "must not call the M1b-3 detector" in text
    assert "A clean M1b-3 report is advisory only" in text
    assert "`logical_name` and\n  `resolved_path` exactly match" in text


def test_r0_evidence_inventory_is_bounded_and_complete() -> None:
    cases = _json_block("memory-runtime-r0-evidence-cases")
    assert cases == [
        "exact_written_round_trip",
        "exact_already_present_round_trip_without_duplicate",
        "same_identity_different_summary_fails_closed",
        "writer_resolver_path_mismatch_fails_closed",
        "missing_or_non_directory_root_fails_closed",
        "unknown_logical_name_fails_closed",
        "missing_surface_is_not_empty_result",
        "invalid_argument_types_fail_closed",
        "ordinary_dependency_exceptions_fail_closed",
        "invalid_utf8_fails_closed",
        "target_zero_multiple_or_malformed_marker_fails_closed",
        "well_formed_non_target_identities_are_ignored",
        "caller_record_identity_mismatch_fails_closed",
        "writer_outcome_identity_mismatch_fails_closed",
        "unexpected_writer_status_fails_closed",
        "m1_non_resolved_states_preserved_without_rendering",
        "m1_observation_subject_mismatch_fails_closed",
        "m1b3_detector_is_not_called",
        "m1b3_finding_requires_logical_name_and_path_match",
        "clean_m1b3_report_is_advisory_only",
        "surrounding_summary_whitespace_uses_public_renderer_normalization",
        "reserved_projection_tokens_fail_at_writer_boundary",
        "no_silent_drop_injection_or_duplicate_render",
        "single_snapshot_dependency_counts",
        "unchanged_input_and_snapshot_produce_byte_identical_json",
    ]
    assert len(cases) == len(set(cases)) == 25


def test_r0_plan_entry_is_candidate_and_requires_separate_implementation_authority() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    assert (
        "Current refresh - 2026-09-02 "
        "(Memory Runtime R0 technical specification candidate):"
    ) in plan
    assert "- [>] Define one bounded exact round-trip specification" in plan
    assert "Runtime implementation requires a separate owner\n  authorization" in plan
    assert "Implementation-readiness acceptance requires technical review approving the" in plan
    assert "exact candidate HEAD with no unresolved P0/P1" in plan
    assert "Specification activation" not in plan

    contract = CONTRACT.read_text(encoding="utf-8")
    for non_claim in (
        "no implementation in this specification tranche",
        "no writer redesign",
        "no atomic-write, crash-safety",
        "no MRCSP detector integration",
        "no semantic retrieval",
        "no update, supersession",
        "no schema, hook, CI, gate, blocker, enforcement, or Gate 3 change",
        "no Memory Runtime R1",
    ):
        assert non_claim in contract
