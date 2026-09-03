from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from governance_tools import memory_record
from memory_pipeline import active_task_supersession
from memory_pipeline.active_task_round_trip import round_trip_active_task
from memory_pipeline.active_task_supersession import (
    CURRENT_STATE_BASE,
    CURRENT_STATE_SUPERSEDED,
    select_current_active_task,
    supersede_active_task,
)


def _record(version: str) -> dict[str, str]:
    return memory_record.build_session_derived_record(
        what_changed=f"R1 fixture {version}",
        commit=f"fixture-{version}",
        session_id=f"session-r1-{version}",
        memory_binding="bound",
        test_evidence=f"NOT RUN: R1 {version} fixture construction",
        next_step=f"Exercise R1 {version}.",
        plan_reconciliation=memory_record.PLAN_RECONCILIATION_NOT_APPLICABLE,
    )


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    project_root = tmp_path.resolve()
    memory_root = project_root / "memory"
    memory_root.mkdir(parents=True)
    (project_root / ".git").mkdir()
    return project_root, memory_root, memory_root / "01_active_task.md"


def _projection(record: dict[str, str], summary: str) -> bytes:
    return memory_record.render_active_task_projection(record, summary=summary).encode("utf-8")


def _digest(record: dict[str, str], summary: str) -> str:
    return hashlib.sha256(_projection(record, summary)).hexdigest()


def _resolved_authority(
    predecessor: dict[str, str],
    predecessor_summary: str,
    successor: dict[str, str],
    successor_summary: str,
    **overrides: Any,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "decision": "supersede",
        "logical_name": "active_task",
        "query_class": "current_progress",
        "predecessor_record_identity": predecessor["record_identity"],
        "predecessor_projection_sha256": _digest(predecessor, predecessor_summary),
        "successor_record_identity": successor["record_identity"],
        "successor_projection_sha256": _digest(successor, successor_summary),
        "resolution_state": "resolved",
        "projection_status": "current",
        "review_status": "reviewed",
        "reviewer_authority_state": "authority_qualified",
        "anchor_state": "covers_latest_qualified_evidence",
        "state_transition_coverage": "covers_latest_substantive_transition",
        "later_change_state": "none_unreconciled",
        "coverage_boundary_state": "determinable_without_semantic_guessing",
        "authority_source": "current_human_instruction",
        "source_anchor": "owner authorization for the exact v1 to v2 transition",
    }
    observation.update(overrides)
    return observation


def _base_authority(
    predecessor: dict[str, str],
    predecessor_summary: str,
    **overrides: Any,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "resolution_state": "resolved",
        "query_class": "current_progress",
        "logical_name": "active_task",
        "requested_record_identity": predecessor["record_identity"],
        "resolved_record_identity": predecessor["record_identity"],
        "authorized_projection_sha256": _digest(predecessor, predecessor_summary),
    }
    observation.update(overrides)
    return observation


def _write_projection(
    project_root: Path,
    record: dict[str, str],
    summary: str,
) -> None:
    memory_record.append_projection_with_outcome(
        project_root=project_root,
        record=record,
        surface=memory_record.SURFACE_ACTIVE_TASK_SUMMARY,
        active_task_summary=summary,
    )


def _call(
    project_root: Path,
    memory_root: Path,
    predecessor: dict[str, str],
    predecessor_summary: str,
    successor: dict[str, str],
    successor_summary: str,
    authority: dict[str, Any],
) -> tuple[str, bytes]:
    return supersede_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        predecessor_record=predecessor,
        predecessor_summary=predecessor_summary,
        successor_record=successor,
        successor_summary=successor_summary,
        authority_observation=authority,
    )


def test_v1_only_is_base_current(tmp_path: Path) -> None:
    project_root, memory_root, _ = _roots(tmp_path)
    predecessor = _record("v1")
    summary = "Implement R1 specification."
    _write_projection(project_root, predecessor, summary)

    disposition, context = select_current_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        predecessor_record=predecessor,
        predecessor_summary=summary,
        authority_observation=_base_authority(predecessor, summary),
    )

    assert disposition == CURRENT_STATE_BASE
    assert context == _projection(predecessor, summary)


@pytest.mark.parametrize(
    "resolution_state",
    ["reviewer_required", "disputed", "insufficient_authority", "unassessable"],
)
def test_v1_only_preserves_non_resolved_authority_with_zero_context(
    tmp_path: Path,
    resolution_state: str,
) -> None:
    project_root, memory_root, _ = _roots(tmp_path)
    predecessor = _record("v1")
    summary = "Implement R1 specification."
    _write_projection(project_root, predecessor, summary)
    authority = _base_authority(
        predecessor,
        summary,
        resolution_state=resolution_state,
    )

    disposition, context = select_current_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        predecessor_record=predecessor,
        predecessor_summary=summary,
        authority_observation=authority,
    )

    assert disposition == resolution_state
    assert context == b""


def test_v1_only_requires_content_bound_authority(tmp_path: Path) -> None:
    project_root, memory_root, _ = _roots(tmp_path)
    predecessor = _record("v1")
    summary = "Implement R1 specification."
    _write_projection(project_root, predecessor, summary)

    with pytest.raises(ValueError, match="base authority_observation"):
        select_current_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            predecessor_record=predecessor,
            predecessor_summary=summary,
        )

    with pytest.raises(ValueError, match="projection digest mismatch"):
        select_current_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            predecessor_record=predecessor,
            predecessor_summary=summary,
            authority_observation=_base_authority(
                predecessor,
                summary,
                authorized_projection_sha256="0" * 64,
            ),
        )


def test_valid_supersession_keeps_v1_and_returns_only_v2(tmp_path: Path) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is ready for review."
    _write_projection(project_root, predecessor, v1_summary)
    authority = _resolved_authority(
        predecessor, v1_summary, successor, v2_summary
    )

    disposition, context = _call(
        project_root,
        memory_root,
        predecessor,
        v1_summary,
        successor,
        v2_summary,
        authority,
    )

    persisted = surface.read_bytes()
    assert disposition == CURRENT_STATE_SUPERSEDED
    assert context == _projection(successor, v2_summary)
    assert _projection(predecessor, v1_summary).rstrip(b"\n") in persisted
    assert _projection(successor, v2_summary).rstrip(b"\n") in persisted
    assert persisted.count(b"memory_runtime_supersession:") == 1


def test_complete_retry_is_zero_write_and_byte_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)
    first = _call(
        project_root, memory_root, predecessor, v1_summary, successor, v2_summary, authority
    )
    before = surface.read_bytes()

    def unexpected_writer(**_: object) -> object:
        raise AssertionError("a complete retry must not invoke a writer")

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_writer)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        unexpected_writer,
    )
    second = _call(
        project_root, memory_root, predecessor, v1_summary, successor, v2_summary, authority
    )

    assert first == second == (CURRENT_STATE_SUPERSEDED, _projection(successor, v2_summary))
    assert surface.read_bytes() == before


def test_partial_retrieval_has_no_current_and_never_repairs(tmp_path: Path) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    _write_projection(project_root, successor, v2_summary)
    before = surface.read_bytes()
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)

    with pytest.raises(ValueError, match="no unique current record"):
        select_current_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            predecessor_record=predecessor,
            predecessor_summary=v1_summary,
            successor_record=successor,
            successor_summary=v2_summary,
            authority_observation=authority,
        )
    assert surface.read_bytes() == before


def test_relation_failure_leaves_partial_and_fresh_authority_recovers_relation_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)
    real_relation_writer = memory_record.append_active_task_supersession_relation_with_outcome

    def fail_relation(**_: object) -> object:
        raise RuntimeError("simulated relation failure")

    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        fail_relation,
    )
    with pytest.raises(ValueError, match="relation write failed"):
        _call(
            project_root,
            memory_root,
            predecessor,
            v1_summary,
            successor,
            v2_summary,
            authority,
        )
    partial = surface.read_bytes()
    assert _projection(successor, v2_summary).rstrip(b"\n") in partial
    assert b"memory_runtime_supersession:" not in partial

    calls = {"projection": 0, "relation": 0}

    def unexpected_projection(**_: object) -> object:
        calls["projection"] += 1
        raise AssertionError("partial recovery must not rewrite the successor")

    def counted_relation(**kwargs: object) -> object:
        calls["relation"] += 1
        return real_relation_writer(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_projection)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        counted_relation,
    )
    disposition, context = _call(
        project_root, memory_root, predecessor, v1_summary, successor, v2_summary, authority
    )

    assert (disposition, context) == (
        CURRENT_STATE_SUPERSEDED,
        _projection(successor, v2_summary),
    )
    assert calls == {"projection": 0, "relation": 1}


@pytest.mark.parametrize("state", sorted(active_task_supersession.NON_RESOLVED_STATES))
def test_partial_state_preserves_non_resolved_disposition_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    _write_projection(project_root, successor, v2_summary)
    before = surface.read_bytes()
    authority = _resolved_authority(
        predecessor,
        v1_summary,
        successor,
        v2_summary,
        resolution_state=state,
    )

    def unexpected_writer(**_: object) -> object:
        raise AssertionError("non-resolved authority must not invoke a writer")

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_writer)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        unexpected_writer,
    )
    assert _call(
        project_root, memory_root, predecessor, v1_summary, successor, v2_summary, authority
    ) == (state, b"")
    assert surface.read_bytes() == before


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"successor_record_identity": "0" * 64}, "successor_record_identity mismatch"),
        ({"successor_projection_sha256": "f" * 64}, "successor_projection_sha256 mismatch"),
        ({"resolution_state": []}, "resolution_state is invalid"),
        ({"source_anchor": "bad\nanchor"}, "source anchor is invalid"),
    ],
)
def test_invalid_authority_fails_before_writers_and_preserves_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Any],
    message: str,
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    before = surface.read_bytes()
    authority = _resolved_authority(
        predecessor, v1_summary, successor, v2_summary, **overrides
    )

    def unexpected_writer(**_: object) -> object:
        raise AssertionError("invalid authority must fail before writer invocation")

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_writer)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        unexpected_writer,
    )
    with pytest.raises(ValueError, match=message):
        _call(
            project_root,
            memory_root,
            predecessor,
            v1_summary,
            successor,
            v2_summary,
            authority,
        )
    assert surface.read_bytes() == before


def test_unhashable_writer_status_fails_closed_as_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    before = surface.read_bytes()
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)

    def invalid_outcome(**_: object) -> object:
        return SimpleNamespace(
            path=surface,
            status=[],
            record_identity=successor["record_identity"],
        )

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", invalid_outcome)
    with pytest.raises(ValueError, match="unsupported status"):
        _call(
            project_root,
            memory_root,
            predecessor,
            v1_summary,
            successor,
            v2_summary,
            authority,
        )
    assert surface.read_bytes() == before


@pytest.mark.parametrize(
    "identity_field",
    [
        "record_format_version",
        "memory_type",
        "writer",
        "commit_hash",
        "test_evidence",
        "next_step",
    ],
)
def test_writer_normalization_identity_drift_fails_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity_field: str,
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    before = surface.read_bytes()
    successor[identity_field] = f"  {successor[identity_field]}  "
    successor["record_identity"] = memory_record.build_record_identity(successor)
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)

    def unexpected_writer(**_: object) -> object:
        raise AssertionError("normalization drift must fail before writer invocation")

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_writer)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        unexpected_writer,
    )
    with pytest.raises(ValueError, match="identity does not match canonical identity"):
        _call(
            project_root,
            memory_root,
            predecessor,
            v1_summary,
            successor,
            v2_summary,
            authority,
        )
    assert surface.read_bytes() == before


def test_writer_normalization_with_canonical_identity_completes(tmp_path: Path) -> None:
    project_root, memory_root, _ = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 is current."
    _write_projection(project_root, predecessor, v1_summary)
    successor["test_evidence"] = f"  {successor['test_evidence']}  "
    successor["record_identity"] = memory_record.prepare_projection_record(successor)[
        "record_identity"
    ]
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)

    assert _call(
        project_root,
        memory_root,
        predecessor,
        v1_summary,
        successor,
        v2_summary,
        authority,
    ) == (CURRENT_STATE_SUPERSEDED, _projection(successor, v2_summary))


def test_r0_raw_identity_normalization_drift_fails_before_persisting(
    tmp_path: Path,
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    record = _record("r0")
    summary = "R0 remains current."
    record["next_step"] = f"  {record['next_step']}  "
    record["record_identity"] = memory_record.build_record_identity(record)
    authority = _base_authority(record, summary)

    with pytest.raises(ValueError, match="identity does not match canonical identity"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary=summary,
            authority_observation=authority,
        )

    assert not surface.exists()


def test_conflicting_prewrite_relation_fails_before_writers_and_preserves_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor, other = _record("v1"), _record("v2"), _record("other")
    v1_summary, v2_summary, other_summary = "Implement R1.", "R1 current.", "Other."
    for record, summary in (
        (predecessor, v1_summary),
        (successor, v2_summary),
        (other, other_summary),
    ):
        _write_projection(project_root, record, summary)
    conflict = memory_record.render_active_task_supersession_relation(
        predecessor_record_identity=predecessor["record_identity"],
        predecessor_projection_sha256=_digest(predecessor, v1_summary),
        successor_record_identity=other["record_identity"],
        successor_projection_sha256=_digest(other, other_summary),
    ).encode("ascii")
    with surface.open("ab") as fh:
        fh.write(b"\n" + conflict)
    before = surface.read_bytes()
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)

    def unexpected_writer(**_: object) -> object:
        raise AssertionError("conflicting prewrite state must not invoke a writer")

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_writer)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        unexpected_writer,
    )
    with pytest.raises(ValueError, match="duplicate or conflicting"):
        _call(
            project_root,
            memory_root,
            predecessor,
            v1_summary,
            successor,
            v2_summary,
            authority,
        )
    assert surface.read_bytes() == before


def test_malformed_relation_and_missing_endpoint_fail_closed(tmp_path: Path) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    v1_summary, v2_summary = "Implement R1.", "R1 current."
    _write_projection(project_root, predecessor, v1_summary)
    with surface.open("ab") as fh:
        fh.write(b"\n<!-- memory_runtime_supersession:active-task-summaryX:bad -->\n")
    authority = _resolved_authority(predecessor, v1_summary, successor, v2_summary)

    with pytest.raises(ValueError, match="relation is malformed"):
        _call(
            project_root,
            memory_root,
            predecessor,
            v1_summary,
            successor,
            v2_summary,
            authority,
        )


def test_projection_line_that_also_claims_relation_namespace_fails_closed(
    tmp_path: Path,
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor = _record("v1")
    persisted_summary = "Inspect memory_runtime_supersession: history."
    requested_summary = "Inspect supersession history."
    surface.write_bytes(
        (
            f"- {persisted_summary} "
            "<!-- memory_record_projection:active-task-summary:"
            f"{predecessor['record_identity']} -->\n"
        ).encode("utf-8")
    )

    with pytest.raises(ValueError, match="multiple namespaces"):
        select_current_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            predecessor_record=predecessor,
            predecessor_summary=requested_summary,
            authority_observation=_base_authority(predecessor, requested_summary),
        )


def test_successor_relation_namespace_fails_before_writers_and_preserves_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor = _record("v1")
    successor = _record("v2")
    predecessor_summary = "Implement R1 specification."
    successor_summary = "Inspect memory_runtime_supersession: history."
    _write_projection(project_root, predecessor, predecessor_summary)
    before = surface.read_bytes()
    authority = _resolved_authority(
        predecessor,
        predecessor_summary,
        successor,
        "Safe successor summary.",
    )
    unsafe_projection = (
        f"- {successor_summary} "
        "<!-- memory_record_projection:active-task-summary:"
        f"{successor['record_identity']} -->\n"
    ).encode("utf-8")
    authority["successor_projection_sha256"] = hashlib.sha256(
        unsafe_projection
    ).hexdigest()

    def unexpected_writer(**_: object) -> object:
        raise AssertionError("reserved successor syntax must fail before writer invocation")

    monkeypatch.setattr(memory_record, "append_projection_with_outcome", unexpected_writer)
    monkeypatch.setattr(
        memory_record,
        "append_active_task_supersession_relation_with_outcome",
        unexpected_writer,
    )

    with pytest.raises(ValueError, match="reserved structured syntax"):
        _call(
            project_root,
            memory_root,
            predecessor,
            predecessor_summary,
            successor,
            successor_summary,
            authority,
        )

    assert surface.read_bytes() == before


def test_canonical_projection_writer_rejects_supersession_namespace_before_write(
    tmp_path: Path,
) -> None:
    project_root, _, surface = _roots(tmp_path)

    with pytest.raises(ValueError, match="reserved supersession syntax"):
        memory_record.append_projection_with_outcome(
            project_root=project_root,
            record=_record("v2"),
            surface=memory_record.SURFACE_ACTIVE_TASK_SUMMARY,
            active_task_summary="Inspect memory_runtime_supersession: history.",
        )

    assert not surface.exists()


def test_relation_writer_rejects_dual_namespace_before_mutation(tmp_path: Path) -> None:
    project_root, _, surface = _roots(tmp_path)
    predecessor = _record("v1")
    successor = _record("v2")
    predecessor_summary = "Implement R1 specification."
    successor_summary = "R1 implementation is ready for review."
    _write_projection(project_root, predecessor, predecessor_summary)
    _write_projection(project_root, successor, successor_summary)
    with surface.open("ab") as fh:
        fh.write(
            (
                "- Historical memory_runtime_supersession: note "
                "<!-- memory_record_projection:active-task-summary:"
                f"{'0' * 64} -->\n"
            ).encode("utf-8")
        )
    before = surface.read_bytes()

    with pytest.raises(ValueError, match="multiple namespaces"):
        memory_record.append_active_task_supersession_relation_with_outcome(
            project_root=project_root,
            predecessor_record_identity=predecessor["record_identity"],
            predecessor_projection_sha256=_digest(predecessor, predecessor_summary),
            successor_record_identity=successor["record_identity"],
            successor_projection_sha256=_digest(successor, successor_summary),
        )

    assert surface.read_bytes() == before


def test_same_identity_with_changed_summary_fails_before_mutation(tmp_path: Path) -> None:
    project_root, memory_root, surface = _roots(tmp_path)
    predecessor = _record("v1")
    successor = dict(predecessor)
    _write_projection(project_root, predecessor, "Old summary.")
    before = surface.read_bytes()
    authority = _resolved_authority(
        predecessor, "Old summary.", successor, "Changed summary."
    )

    with pytest.raises(ValueError, match="identities must be distinct"):
        _call(
            project_root,
            memory_root,
            predecessor,
            "Old summary.",
            successor,
            "Changed summary.",
            authority,
        )
    assert surface.read_bytes() == before


def test_unrelated_historical_lineage_does_not_change_target_selection(tmp_path: Path) -> None:
    project_root, memory_root, _ = _roots(tmp_path)
    old_v1, old_v2 = _record("old-v1"), _record("old-v2")
    predecessor, successor = _record("v1"), _record("v2")
    _write_projection(project_root, old_v1, "Old one.")
    _write_projection(project_root, old_v2, "Old two.")
    memory_record.append_active_task_supersession_relation_with_outcome(
        project_root=project_root,
        predecessor_record_identity=old_v1["record_identity"],
        predecessor_projection_sha256=_digest(old_v1, "Old one."),
        successor_record_identity=old_v2["record_identity"],
        successor_projection_sha256=_digest(old_v2, "Old two."),
    )
    _write_projection(project_root, predecessor, "Current v1.")
    authority = _resolved_authority(
        predecessor, "Current v1.", successor, "Current v2."
    )

    assert _call(
        project_root,
        memory_root,
        predecessor,
        "Current v1.",
        successor,
        "Current v2.",
        authority,
    ) == (CURRENT_STATE_SUPERSEDED, _projection(successor, "Current v2."))


@pytest.mark.parametrize("root_kind", ["relative", "wrong_memory", "not_repo"])
def test_invalid_roots_fail_before_writer(tmp_path: Path, root_kind: str) -> None:
    project_root, memory_root, _ = _roots(tmp_path)
    predecessor, successor = _record("v1"), _record("v2")
    authority = _resolved_authority(predecessor, "v1", successor, "v2")
    if root_kind == "relative":
        passed_project, passed_memory = Path("."), Path("memory")
    elif root_kind == "wrong_memory":
        wrong = project_root / "other"
        wrong.mkdir()
        passed_project, passed_memory = project_root, wrong
    else:
        (project_root / ".git").rmdir()
        passed_project, passed_memory = project_root, memory_root

    with pytest.raises(ValueError):
        _call(
            passed_project,
            passed_memory,
            predecessor,
            "v1",
            successor,
            "v2",
            authority,
        )


def test_relation_renderer_has_exact_lf_grammar_and_rejects_bad_fields() -> None:
    rendered = memory_record.render_active_task_supersession_relation(
        predecessor_record_identity="1" * 64,
        predecessor_projection_sha256="2" * 64,
        successor_record_identity="3" * 64,
        successor_projection_sha256="4" * 64,
    )
    assert rendered == (
        "<!-- memory_runtime_supersession:active-task-summary:"
        f"{'1' * 64}:{'2' * 64}:{'3' * 64}:{'4' * 64} -->\n"
    )
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        memory_record.render_active_task_supersession_relation(
            predecessor_record_identity="A" * 64,
            predecessor_projection_sha256="2" * 64,
            successor_record_identity="3" * 64,
            successor_projection_sha256="4" * 64,
        )
    with pytest.raises(ValueError, match="endpoints must be distinct"):
        memory_record.render_active_task_supersession_relation(
            predecessor_record_identity="1" * 64,
            predecessor_projection_sha256="2" * 64,
            successor_record_identity="1" * 64,
            successor_projection_sha256="4" * 64,
        )
