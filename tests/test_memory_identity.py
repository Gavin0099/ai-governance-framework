from __future__ import annotations

import hashlib

import pytest

from governance_tools.memory_identity import (
    CANONICAL_MEMORY_WRITER,
    IdentityRelation,
    RecordAttemptKind,
    RelationStatus,
    TargetExistence,
    build_event_identity,
    build_record_identity,
    classify_record_attempt,
    summarize_relations,
)


EVENT_VECTORS = (
    (
        "99dc75d4-1093-43c3-b3df-3b8f1029ecf2",
        "ff63b1f998f10dbfbe28867f45126c3de29c57089d40ab17f7932c46012da6b9",
    ),
    (
        "ec30bdae-8298-4c00-bb5b-80602c9221c2",
        "01dde2227a3249049c1d78d201fa8680e99f5ecc9b82bd07cfd0836616c59aea",
    ),
    (
        "fc67ba60-04e4-4b95-8f87-1a1dcf09fa86",
        "284386c7dcad43129fddba1d3cbc278be3d7ab2a82429a0a9a8a37af85729e75",
    ),
    (
        "094062cd-6003-4355-b586-99439ca17c1a",
        "0f95a9c638b73dcf13aab797f30eab525381718a94ef91d311a43b22aee91792",
    ),
    (
        "af8d2092-5ed5-4b0f-addf-a1705b44e080",
        "7cc96163f88afab77f7469d7ffa9215145aa6ba1baeeb9ccb52a4a29746d9050",
    ),
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record_identity(*, event_identity: str, what_changed: str) -> str:
    return build_record_identity(
        event_identity=event_identity,
        record_format_version="1",
        memory_type="session-derived",
        writer=CANONICAL_MEMORY_WRITER,
        what_changed=what_changed,
        commit_hash="0123456789abcdef0123456789abcdef01234567",
        test_evidence="synthetic tests passed",
        next_step="review the synthetic relation",
        plan_reconciliation="not-required",
    )


def _relation(
    label: str,
    *,
    target: TargetExistence,
    status: RelationStatus,
) -> IdentityRelation:
    return IdentityRelation(
        legacy_record_identity_v1=_digest(f"legacy:{label}"),
        event_identity=_digest(f"event:{label}"),
        record_identity_v2=(
            _digest(f"record:{label}")
            if target is TargetExistence.RECORD_TARGET_PRESENT
            else None
        ),
        session_id=f"synthetic-session-{label}",
        target_existence=target,
        current_status=status,
    )


@pytest.mark.parametrize(("session_id", "expected"), EVENT_VECTORS)
def test_memory_event_v1_vectors(session_id: str, expected: str) -> None:
    assert build_event_identity(session_id=session_id) == expected


def test_event_identity_is_domain_separated_and_rejects_multiline_input() -> None:
    session_id = "synthetic-session"

    canonical = build_event_identity(session_id=session_id)
    changed_domain = build_event_identity(
        session_id=session_id,
        event_kind="synthetic-closeout",
    )

    assert canonical != changed_domain
    with pytest.raises(ValueError, match="exactly one line"):
        build_event_identity(session_id="synthetic\nsession")


def test_memory_record_v2_changes_with_event_and_content() -> None:
    first_event = build_event_identity(session_id="synthetic-session-one")
    second_event = build_event_identity(session_id="synthetic-session-two")

    first_record = _record_identity(
        event_identity=first_event,
        what_changed="synthetic result one",
    )
    same_record = _record_identity(
        event_identity=first_event,
        what_changed="synthetic result one",
    )
    changed_content = _record_identity(
        event_identity=first_event,
        what_changed="synthetic result two",
    )
    changed_event = _record_identity(
        event_identity=second_event,
        what_changed="synthetic result one",
    )

    assert first_record == same_record
    assert first_record != changed_content
    assert first_record != changed_event


def test_same_session_retry_remains_idempotent() -> None:
    event_identity = build_event_identity(session_id="synthetic-retry-session")
    record_identity = _record_identity(
        event_identity=event_identity,
        what_changed="synthetic stable result",
    )

    assert (
        classify_record_attempt(
            previous_record_identity=record_identity,
            candidate_record_identity=record_identity,
        )
        is RecordAttemptKind.RETRY
    )
    with pytest.raises(ValueError, match="must not declare supersession"):
        classify_record_attempt(
            previous_record_identity=record_identity,
            candidate_record_identity=record_identity,
            supersedes_record_identity=record_identity,
        )


def test_same_session_changed_content_requires_exact_supersession() -> None:
    event_identity = build_event_identity(session_id="synthetic-correction-session")
    previous = _record_identity(
        event_identity=event_identity,
        what_changed="synthetic original result",
    )
    corrected = _record_identity(
        event_identity=event_identity,
        what_changed="synthetic corrected result",
    )

    with pytest.raises(ValueError, match="requires supersedes_record_identity"):
        classify_record_attempt(
            previous_record_identity=previous,
            candidate_record_identity=corrected,
        )
    with pytest.raises(ValueError, match="must name the current record"):
        classify_record_attempt(
            previous_record_identity=previous,
            candidate_record_identity=corrected,
            supersedes_record_identity=_digest("wrong-record"),
        )
    assert (
        classify_record_attempt(
            previous_record_identity=previous,
            candidate_record_identity=corrected,
            supersedes_record_identity=previous,
        )
        is RecordAttemptKind.CORRECTION
    )


def test_cross_session_equivalent_content_has_distinct_identities() -> None:
    first_event = build_event_identity(session_id="synthetic-cross-session-one")
    second_event = build_event_identity(session_id="synthetic-cross-session-two")

    assert first_event != second_event
    assert _record_identity(
        event_identity=first_event,
        what_changed="synthetic equivalent content",
    ) != _record_identity(
        event_identity=second_event,
        what_changed="synthetic equivalent content",
    )


def test_synthetic_dc4_relation_expands_one_legacy_identity_to_two_targets() -> None:
    legacy_identity = _digest("synthetic-dc4-legacy")
    relations = []
    for suffix in ("one", "two"):
        event_identity = build_event_identity(
            session_id=f"synthetic-dc4-session-{suffix}"
        )
        relations.append(
            IdentityRelation(
                legacy_record_identity_v1=legacy_identity,
                event_identity=event_identity,
                record_identity_v2=_record_identity(
                    event_identity=event_identity,
                    what_changed=f"synthetic dc4 content {suffix}",
                ),
                session_id=f"synthetic-dc4-session-{suffix}",
                target_existence=TargetExistence.RECORD_TARGET_PRESENT,
                current_status=RelationStatus.PENDING_SOURCE_PRESERVATION,
            )
        )

    summary = summarize_relations(relations)

    assert summary.total == 2
    assert summary.record_target_present == 2
    assert summary.pending_source_preservation == 2


def test_synthetic_f99_relation_preserves_materialized_and_event_only_versions() -> None:
    legacy_identity = _digest("synthetic-f99-legacy")
    materialized_event = _digest("synthetic-f99-materialized-event")
    relations = (
        IdentityRelation(
            legacy_record_identity_v1=legacy_identity,
            event_identity=materialized_event,
            record_identity_v2=_digest("synthetic-f99-materialized-record"),
            session_id="synthetic-f99-materialized-session",
            target_existence=TargetExistence.RECORD_TARGET_PRESENT,
            current_status=RelationStatus.MATERIALIZED,
        ),
        IdentityRelation(
            legacy_record_identity_v1=legacy_identity,
            event_identity=_digest("synthetic-f99-unmaterialized-event"),
            record_identity_v2=None,
            session_id="synthetic-f99-unmaterialized-session",
            target_existence=TargetExistence.EVENT_ONLY,
            current_status=RelationStatus.RECORD_VERSION_UNMATERIALIZED,
        ),
    )

    summary = summarize_relations(relations)

    assert summary.record_target_present == 1
    assert summary.event_only == 1
    assert summary.materialized == 1
    assert summary.record_version_unmaterialized == 1


def test_synthetic_dangling_relation_is_event_only() -> None:
    summary = summarize_relations(
        (
            _relation(
                "dangling",
                target=TargetExistence.EVENT_ONLY,
                status=RelationStatus.RECORD_DANGLING,
            ),
        )
    )

    assert summary.total == 1
    assert summary.event_only == 1
    assert summary.record_dangling == 1


def test_owner_decision_partition_satisfies_both_relation_dimensions() -> None:
    relations = [
        _relation(
            f"materialized-{index}",
            target=TargetExistence.RECORD_TARGET_PRESENT,
            status=RelationStatus.MATERIALIZED,
        )
        for index in range(60)
    ]
    relations.extend(
        _relation(
            f"pending-{index}",
            target=TargetExistence.RECORD_TARGET_PRESENT,
            status=RelationStatus.PENDING_SOURCE_PRESERVATION,
        )
        for index in range(11)
    )
    relations.append(
        _relation(
            "unmaterialized",
            target=TargetExistence.EVENT_ONLY,
            status=RelationStatus.RECORD_VERSION_UNMATERIALIZED,
        )
    )
    relations.extend(
        _relation(
            f"dangling-{index}",
            target=TargetExistence.EVENT_ONLY,
            status=RelationStatus.RECORD_DANGLING,
        )
        for index in range(4)
    )

    summary = summarize_relations(relations)

    assert summary.total == 76
    assert summary.record_target_present == 71
    assert summary.event_only == 5
    assert summary.materialized == 60
    assert summary.pending_source_preservation == 11
    assert summary.record_version_unmaterialized == 1
    assert summary.record_dangling == 4
    assert (
        summary.materialized + summary.pending_source_preservation
        == summary.record_target_present
    )
    assert (
        summary.record_version_unmaterialized + summary.record_dangling
        == summary.event_only
    )


@pytest.mark.parametrize(
    ("target", "status"),
    (
        (TargetExistence.EVENT_ONLY, RelationStatus.MATERIALIZED),
        (
            TargetExistence.RECORD_TARGET_PRESENT,
            RelationStatus.RECORD_DANGLING,
        ),
    ),
)
def test_relation_validator_rejects_cross_dimension_mismatch(
    target: TargetExistence,
    status: RelationStatus,
) -> None:
    with pytest.raises(ValueError, match="requires"):
        summarize_relations((_relation("invalid", target=target, status=status),))


def test_relation_validator_rejects_duplicate_relation() -> None:
    relation = _relation(
        "duplicate",
        target=TargetExistence.RECORD_TARGET_PRESENT,
        status=RelationStatus.MATERIALIZED,
    )

    with pytest.raises(ValueError, match="duplicate"):
        summarize_relations((relation, relation))
