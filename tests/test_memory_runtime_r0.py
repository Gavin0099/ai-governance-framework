from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from governance_tools import memory_record
from memory_pipeline import active_task_round_trip, memory_layout
from memory_pipeline.active_task_round_trip import round_trip_active_task


def _record() -> dict[str, str]:
    return memory_record.build_session_derived_record(
        what_changed="R0 fixture",
        commit="fixture-commit",
        session_id="session-r0-fixture",
        memory_binding="bound",
        test_evidence="NOT RUN: R0 fixture construction",
        next_step="Run the bounded round trip.",
        plan_reconciliation=memory_record.PLAN_RECONCILIATION_NOT_APPLICABLE,
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    memory_root = tmp_path / "memory"
    memory_root.mkdir(parents=True)
    return tmp_path, memory_root


def _resolved_observation(
    record: dict[str, str],
    summary: str,
    **overrides: Any,
) -> dict[str, Any]:
    rendered = memory_record.render_active_task_projection(record, summary=summary).encode("utf-8")
    observation: dict[str, Any] = {
        "resolution_state": "resolved",
        "query_class": "current_progress",
        "logical_name": "active_task",
        "requested_record_identity": record["record_identity"],
        "resolved_record_identity": record["record_identity"],
        "authorized_projection_sha256": hashlib.sha256(rendered).hexdigest(),
    }
    observation.update(overrides)
    return observation


def _non_resolved_observation(record: dict[str, str], state: str) -> dict[str, Any]:
    return {
        "resolution_state": state,
        "query_class": "current_progress",
        "logical_name": "active_task",
        "requested_record_identity": record["record_identity"],
    }


def _call(
    tmp_path: Path,
    *,
    record: dict[str, str] | None = None,
    summary: str = "Implement the bounded R0 slice.",
    observation: Any = None,
    m1b3_observation: Any = None,
) -> tuple[str, bytes]:
    project_root, memory_root = _roots(tmp_path)
    admitted_record = _record() if record is None else record
    admitted_observation = (
        _resolved_observation(admitted_record, summary)
        if observation is None
        else observation
    )
    return round_trip_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        record=admitted_record,
        summary=summary,
        authority_observation=admitted_observation,
        m1b3_observation=m1b3_observation,
    )


def test_exact_written_round_trip_returns_canonical_lf_context(tmp_path: Path) -> None:
    record = _record()
    summary = "Implement the bounded R0 slice."

    disposition, context = _call(tmp_path, record=record, summary=summary)

    expected = (
        f"- {summary} <!-- memory_record_projection:active-task-summary:"
        f"{record['record_identity']} -->\n"
    ).encode("utf-8")
    assert (disposition, context) == ("resolved", expected)
    assert (tmp_path / "memory" / "01_active_task.md").read_bytes() == expected


def test_exact_already_present_round_trip_does_not_duplicate(tmp_path: Path) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    observation = _resolved_observation(record, "Task")

    first = round_trip_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        record=record,
        summary="Task",
        authority_observation=observation,
    )
    second = round_trip_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        record=record,
        summary="Task",
        authority_observation=observation,
    )

    assert first == second
    assert (tmp_path / "memory" / "01_active_task.md").read_text(encoding="utf-8").count(
        record["record_identity"]
    ) == 1


@pytest.mark.parametrize(
    "line_boundary",
    ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"],
)
def test_writer_rejects_splitlines_boundaries_before_persisting(
    tmp_path: Path,
    line_boundary: str,
) -> None:
    record = _record()

    with pytest.raises(ValueError, match="exactly one line"):
        memory_record.append_projection_with_outcome(
            project_root=tmp_path,
            record=record,
            surface=memory_record.SURFACE_ACTIVE_TASK_SUMMARY,
            active_task_summary=f"Task{line_boundary}Something",
        )

    assert not (tmp_path / "memory").exists()


@pytest.mark.parametrize(
    "line_boundary",
    ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"],
)
def test_legacy_boundary_record_with_valid_replacement_fails_without_duplicate_append(
    tmp_path: Path,
    line_boundary: str,
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    persisted = (
        f"- Task{line_boundary}Something "
        f"<!-- memory_record_projection:active-task-summary:{record['record_identity']} -->\n"
    ).encode("utf-8")
    target.write_bytes(persisted)

    with pytest.raises(ValueError, match="contains a line boundary"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Replacement task",
            authority_observation=_resolved_observation(record, "Replacement task"),
        )

    assert target.read_bytes() == persisted
    assert target.read_bytes().count(record["record_identity"].encode("ascii")) == 1


@pytest.mark.parametrize(
    "line_boundary",
    ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"],
)
def test_independent_parser_rejects_persisted_summary_line_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    line_boundary: str,
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    target.write_bytes(
        (
            f"- Historical{line_boundary}task "
            f"<!-- memory_record_projection:active-task-summary:{record['record_identity']} -->\n"
        ).encode("utf-8")
    )
    monkeypatch.setattr(
        memory_record,
        "append_projection_with_outcome",
        lambda **kwargs: memory_record.MemoryWriteOutcome(
            path=target,
            status=memory_record.MEMORY_WRITE_STATUS_ALREADY_PRESENT,
            record_identity=record["record_identity"],
            writer=memory_record.WRITER_ID,
        ),
    )

    with pytest.raises(ValueError, match="contains a line boundary"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_exact_already_present_crlf_round_trip_renders_lf(tmp_path: Path) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    rendered = memory_record.render_active_task_projection(record, summary="Task")
    (memory_root / "01_active_task.md").write_bytes(rendered.replace("\n", "\r\n").encode("utf-8"))

    result = round_trip_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        record=record,
        summary="Task",
        authority_observation=_resolved_observation(record, "Task"),
    )

    assert result == ("resolved", rendered.encode("utf-8"))


def test_same_identity_different_summary_fails_closed(tmp_path: Path) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    (memory_root / "01_active_task.md").write_text(
        memory_record.render_active_task_projection(record, summary="Old task"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="payload does not match"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="New task",
            authority_observation=_resolved_observation(record, "New task"),
        )


def test_writer_resolver_path_mismatch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    monkeypatch.setattr(
        memory_layout,
        "resolve_memory_file",
        lambda root, logical_name: root / "other.md",
    )

    with pytest.raises(ValueError, match="does not match logical resolver"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )
    assert (memory_root / "01_active_task.md").exists()


@pytest.mark.parametrize("root_kind", ["missing", "file"])
def test_missing_or_non_directory_memory_root_fails_closed(
    tmp_path: Path, root_kind: str
) -> None:
    memory_root = tmp_path / "memory"
    if root_kind == "file":
        memory_root.write_text("not a directory", encoding="utf-8")
    record = _record()

    with pytest.raises(ValueError, match="memory_root must exist and be a directory"):
        round_trip_active_task(
            project_root=tmp_path,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_unknown_logical_name_fails_closed(tmp_path: Path) -> None:
    project_root, memory_root = _roots(tmp_path)
    record = _record()

    with pytest.raises(ValueError, match="active_task"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="unknown",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_missing_surface_is_not_an_empty_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    monkeypatch.setattr(
        memory_record,
        "append_projection_with_outcome",
        lambda **kwargs: memory_record.MemoryWriteOutcome(
            path=target,
            status=memory_record.MEMORY_WRITE_STATUS_WRITTEN,
            record_identity=record["record_identity"],
            writer=memory_record.WRITER_ID,
        ),
    )

    with pytest.raises(ValueError, match="surface is missing"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_root", "project"),
        ("memory_root", "memory"),
        ("logical_name", 1),
        ("record", []),
        ("summary", None),
        ("authority_observation", []),
        ("m1b3_observation", []),
    ],
)
def test_invalid_argument_types_fail_closed(
    tmp_path: Path, field: str, value: Any
) -> None:
    project_root, memory_root = _roots(tmp_path)
    record = _record()
    kwargs: dict[str, Any] = {
        "project_root": project_root,
        "memory_root": memory_root,
        "logical_name": "active_task",
        "record": record,
        "summary": "Task",
        "authority_observation": _resolved_observation(record, "Task"),
        "m1b3_observation": None,
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        round_trip_active_task(**kwargs)


@pytest.mark.parametrize("dependency", ["writer", "resolver", "read"])
def test_ordinary_dependency_exceptions_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dependency: str
) -> None:
    project_root, memory_root = _roots(tmp_path)
    record = _record()

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("ordinary failure")

    if dependency == "writer":
        monkeypatch.setattr(memory_record, "append_projection_with_outcome", fail)
    elif dependency == "resolver":
        monkeypatch.setattr(memory_layout, "resolve_memory_file", fail)
    else:
        target = memory_root / "01_active_task.md"
        real_read_bytes = Path.read_bytes

        def fail_target_read(path: Path) -> bytes:
            if path == target:
                raise RuntimeError("ordinary read failure")
            return real_read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", fail_target_read)

    with pytest.raises(ValueError):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_invalid_utf8_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    target.write_bytes(b"\xff\n")
    monkeypatch.setattr(
        memory_record,
        "append_projection_with_outcome",
        lambda **kwargs: memory_record.MemoryWriteOutcome(
            path=target,
            status=memory_record.MEMORY_WRITE_STATUS_ALREADY_PRESENT,
            record_identity=record["record_identity"],
            writer=memory_record.WRITER_ID,
        ),
    )

    with pytest.raises(ValueError, match="strict UTF-8"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


@pytest.mark.parametrize(
    "case",
    ["zero", "multiple", "malformed", "missing_terminator", "bare_cr", "mixed_cr"],
)
def test_target_zero_multiple_or_malformed_marker_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    valid = memory_record.render_active_task_projection(record, summary="Task").encode("utf-8")
    if case == "zero":
        target.write_bytes(b"# unrelated\n")
    elif case == "multiple":
        target.write_bytes(valid + valid)
    elif case == "malformed":
        target.write_bytes(valid + valid.rstrip(b"\n") + b" trailing-bytes\n")
    elif case == "missing_terminator":
        target.write_bytes(valid.rstrip(b"\n"))
    elif case == "bare_cr":
        target.write_bytes(valid.rstrip(b"\n") + b"\r")
    else:
        target.write_bytes(valid.rstrip(b"\n").replace(b"Task", b"Task\rvalue") + b"\n")
    monkeypatch.setattr(
        memory_record,
        "append_projection_with_outcome",
        lambda **kwargs: memory_record.MemoryWriteOutcome(
            path=target,
            status=memory_record.MEMORY_WRITE_STATUS_ALREADY_PRESENT,
            record_identity=record["record_identity"],
            writer=memory_record.WRITER_ID,
        ),
    )

    with pytest.raises(ValueError):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_well_formed_non_target_identities_are_ignored(tmp_path: Path) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    historical = (
        "- Historical task <!-- memory_record_projection:active-task-summary:"
        + ("0" * 64)
        + " -->\n"
    )
    (memory_root / "01_active_task.md").write_text(historical, encoding="utf-8")

    disposition, context = round_trip_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        record=record,
        summary="Task",
        authority_observation=_resolved_observation(record, "Task"),
    )

    assert disposition == "resolved"
    assert record["record_identity"].encode("ascii") in context
    assert ("0" * 64).encode("ascii") not in context


@pytest.mark.parametrize(
    "malformed_marker",
    [
        "memory_record_projection:active-task-summaryX:",
        "memory_record_projection:active-task-summary :",
    ],
)
def test_valid_target_with_malformed_projection_namespace_fails_closed(
    tmp_path: Path,
    malformed_marker: str,
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    malformed = (
        f"- Historical task <!-- {malformed_marker}"
        + ("0" * 64)
        + " -->\n"
    )
    (memory_root / "01_active_task.md").write_text(malformed, encoding="utf-8")

    with pytest.raises(ValueError, match="malformed active-task grammar"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_caller_record_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    record = _record()
    record["record_identity"] = "0" * 64

    with pytest.raises(ValueError, match="caller record identity"):
        _call(
            tmp_path,
            record=record,
            observation=_non_resolved_observation(record, "unassessable"),
        )


@pytest.mark.parametrize("mutation", ["identity", "status"])
def test_invalid_writer_outcome_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    target.write_text(
        memory_record.render_active_task_projection(record, summary="Task"),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        memory_record,
        "append_projection_with_outcome",
        lambda **kwargs: memory_record.MemoryWriteOutcome(
            path=target,
            status=(
                "unexpected"
                if mutation == "status"
                else memory_record.MEMORY_WRITE_STATUS_WRITTEN
            ),
            record_identity=("0" * 64) if mutation == "identity" else record["record_identity"],
            writer=memory_record.WRITER_ID,
        ),
    )

    with pytest.raises(ValueError):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


def test_unhashable_writer_status_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    target.write_text(
        memory_record.render_active_task_projection(record, summary="Task"),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        memory_record,
        "append_projection_with_outcome",
        lambda **kwargs: memory_record.MemoryWriteOutcome(
            path=target,
            status=[],
            record_identity=record["record_identity"],
            writer=memory_record.WRITER_ID,
        ),
    )

    with pytest.raises(ValueError, match="unsupported status"):
        round_trip_active_task(
            project_root=project_root,
            memory_root=memory_root,
            logical_name="active_task",
            record=record,
            summary="Task",
            authority_observation=_resolved_observation(record, "Task"),
        )


@pytest.mark.parametrize(
    "state", ["reviewer_required", "disputed", "insufficient_authority", "unassessable"]
)
def test_m1_non_resolved_states_are_preserved_without_rendering(
    tmp_path: Path, state: str
) -> None:
    record = _record()

    result = _call(
        tmp_path,
        record=record,
        summary="Task",
        observation=_non_resolved_observation(record, state),
    )

    assert result == (state, b"")


@pytest.mark.parametrize(
    "field,value",
    [
        ("query_class", "event_history"),
        ("logical_name", "review_log"),
        ("requested_record_identity", "0" * 64),
    ],
)
def test_m1_observation_subject_mismatch_fails_closed(
    tmp_path: Path, field: str, value: str
) -> None:
    record = _record()
    observation = _resolved_observation(record, "Task", **{field: value})

    with pytest.raises(ValueError, match="mismatch"):
        _call(tmp_path, record=record, summary="Task", observation=observation)


def test_unhashable_authority_resolution_state_fails_closed(tmp_path: Path) -> None:
    record = _record()
    observation = _resolved_observation(record, "Task")
    observation["resolution_state"] = []

    with pytest.raises(ValueError, match="invalid resolution state"):
        _call(tmp_path, record=record, summary="Task", observation=observation)


def test_authority_digest_mismatch_for_changed_summary_fails_closed(tmp_path: Path) -> None:
    record = _record()
    observation = _resolved_observation(record, "Old task")

    with pytest.raises(ValueError, match="digest mismatch"):
        _call(tmp_path, record=record, summary="New task", observation=observation)


def test_authority_identity_mismatch_with_same_content_fails_closed(tmp_path: Path) -> None:
    record = _record()
    observation = _resolved_observation(
        record,
        "Task",
        resolved_record_identity="0" * 64,
    )

    with pytest.raises(ValueError, match="resolved authority identity"):
        _call(tmp_path, record=record, summary="Task", observation=observation)


@pytest.mark.parametrize("digest", [None, "A" * 64, "abc"])
def test_malformed_authority_projection_digest_fails_closed(
    tmp_path: Path, digest: Any
) -> None:
    record = _record()
    observation = _resolved_observation(
        record,
        "Task",
        authorized_projection_sha256=digest,
    )

    with pytest.raises(ValueError, match="digest is malformed"):
        _call(tmp_path, record=record, summary="Task", observation=observation)


def test_legacy_observation_without_digest_is_non_resolving_history(tmp_path: Path) -> None:
    record = _record()
    legacy_resolved = _resolved_observation(record, "Task")
    legacy_resolved.pop("authorized_projection_sha256")

    with pytest.raises(ValueError, match="digest is malformed"):
        _call(tmp_path, record=record, summary="Task", observation=legacy_resolved)

    other_root = tmp_path / "non-resolved"
    assert _call(
        other_root,
        record=record,
        summary="Task",
        observation=_non_resolved_observation(record, "reviewer_required"),
    ) == ("reviewer_required", b"")


def test_multiple_current_authority_observations_fail_closed(tmp_path: Path) -> None:
    record = _record()

    with pytest.raises(ValueError, match="exactly one mapping"):
        _call(
            tmp_path,
            record=record,
            summary="Task",
            observation=[_resolved_observation(record, "Task")],
        )


def test_m1b3_detector_is_not_called(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from governance_tools import memory_reconciliation

    def forbidden_call(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("M1b-3 detector must not be called")

    monkeypatch.setattr(
        memory_reconciliation,
        "detect_missing_logical_memory_surface",
        forbidden_call,
    )

    assert _call(tmp_path, m1b3_observation={"findings": []})[0] == "resolved"


@pytest.mark.parametrize("mismatch", [None, "logical_name", "resolved_path"])
def test_m1b3_finding_requires_logical_name_and_path_match(
    tmp_path: Path, mismatch: str | None
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    finding = {
        "code": "missing_logical_memory_surface",
        "logical_name": "active_task",
        "resolved_path": str(memory_root / "01_active_task.md"),
    }
    if mismatch == "logical_name":
        finding["logical_name"] = "review_log"
    elif mismatch == "resolved_path":
        finding["resolved_path"] = str(memory_root / "other.md")

    kwargs = {
        "project_root": project_root,
        "memory_root": memory_root,
        "logical_name": "active_task",
        "record": record,
        "summary": "Task",
        "authority_observation": _resolved_observation(record, "Task"),
        "m1b3_observation": {"findings": [finding]},
    }
    if mismatch is None:
        assert round_trip_active_task(**kwargs)[0] == "resolved"
    else:
        with pytest.raises(ValueError, match="M1b-3 finding"):
            round_trip_active_task(**kwargs)


def test_clean_m1b3_report_is_advisory_only(tmp_path: Path) -> None:
    assert _call(
        tmp_path,
        m1b3_observation={
            "detector": "missing_logical_memory_surface",
            "findings": [],
            "mode": "report_only",
        },
    )[0] == "resolved"


def test_surrounding_summary_whitespace_uses_public_renderer_normalization(
    tmp_path: Path,
) -> None:
    record = _record()
    summary = "  Task with normalized edges.  "

    disposition, context = _call(tmp_path, record=record, summary=summary)

    assert disposition == "resolved"
    assert context.startswith(b"- Task with normalized edges. ")
    assert b"  Task" not in context


@pytest.mark.parametrize(
    "token", ["<!--", "-->", "memory_record_projection:"]
)
def test_reserved_projection_tokens_fail_at_writer_boundary(
    tmp_path: Path, token: str
) -> None:
    record = _record()
    with pytest.raises(ValueError, match="reserved projection syntax"):
        _call(
            tmp_path,
            record=record,
            summary=f"Task {token}",
            observation=_non_resolved_observation(record, "unassessable"),
        )


def test_no_silent_drop_injection_or_duplicate_render(tmp_path: Path) -> None:
    record = _record()
    disposition, context = _call(tmp_path, record=record, summary="Task")

    assert disposition == "resolved"
    assert context.count(b"memory_record_projection:active-task-summary:") == 1
    assert context.count(record["record_identity"].encode("ascii")) == 1
    assert context.endswith(b"\n")


def test_single_snapshot_dependency_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    target = memory_root / "01_active_task.md"
    target.write_text(
        memory_record.render_active_task_projection(record, summary="Task"),
        encoding="utf-8",
    )
    observation = _resolved_observation(record, "Task")
    counts = {
        "identity": 0,
        "render": 0,
        "writer": 0,
        "resolver": 0,
        "exists": 0,
        "read": 0,
    }
    real_identity = memory_record.build_record_identity
    real_render = memory_record.render_active_task_projection
    real_exists = Path.exists
    real_read_bytes = Path.read_bytes

    def counted_identity(value: dict[str, str]) -> str:
        counts["identity"] += 1
        return real_identity(value)

    def counted_render(value: dict[str, str], *, summary: str) -> str:
        counts["render"] += 1
        return real_render(value, summary=summary)

    def counted_writer(**kwargs: Any) -> memory_record.MemoryWriteOutcome:
        counts["writer"] += 1
        return memory_record.MemoryWriteOutcome(
            path=target,
            status=memory_record.MEMORY_WRITE_STATUS_ALREADY_PRESENT,
            record_identity=record["record_identity"],
            writer=memory_record.WRITER_ID,
        )

    def counted_resolver(root: Path, logical_name: str) -> Path:
        counts["resolver"] += 1
        return target

    def counted_exists(path: Path) -> bool:
        if path == target:
            counts["exists"] += 1
        return real_exists(path)

    def counted_read(path: Path) -> bytes:
        if path == target:
            counts["read"] += 1
        return real_read_bytes(path)

    monkeypatch.setattr(memory_record, "build_record_identity", counted_identity)
    monkeypatch.setattr(memory_record, "render_active_task_projection", counted_render)
    monkeypatch.setattr(memory_record, "append_projection_with_outcome", counted_writer)
    monkeypatch.setattr(memory_layout, "resolve_memory_file", counted_resolver)
    monkeypatch.setattr(Path, "exists", counted_exists)
    monkeypatch.setattr(Path, "read_bytes", counted_read)

    result = round_trip_active_task(
        project_root=project_root,
        memory_root=memory_root,
        logical_name="active_task",
        record=record,
        summary="Task",
        authority_observation=observation,
    )

    assert result[0] == "resolved"
    assert counts == {
        "identity": 1,
        "render": 1,
        "writer": 1,
        "resolver": 1,
        "exists": 1,
        "read": 1,
    }


def test_unchanged_input_and_snapshot_preserve_exact_round_trip_bytes(tmp_path: Path) -> None:
    record = _record()
    project_root, memory_root = _roots(tmp_path)
    observation = _resolved_observation(record, "Task")
    kwargs = {
        "project_root": project_root,
        "memory_root": memory_root,
        "logical_name": "active_task",
        "record": record,
        "summary": "Task",
        "authority_observation": observation,
    }

    first = round_trip_active_task(**kwargs)
    second = round_trip_active_task(**kwargs)

    assert first == second
