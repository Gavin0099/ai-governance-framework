from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from governance_tools.memory_emergency_event import append_emergency_event_with_outcome
from governance_tools.memory_janitor import MemoryJanitor
from governance_tools.memory_record import (
    MEMORY_WRITE_STATUS_WRITTEN,
    SURFACE_ACTIVE_TASK_SUMMARY,
    SURFACE_REVIEW_LOG,
    append_projection_with_outcome,
    append_active_task_supersession_relation_with_outcome,
    build_record_identity,
    build_session_derived_record,
)


def _fixture(root: Path, *, active_chars: int = 12_000, evidence: bytes = b"durable evidence\n"):
    memory = root / "memory"
    memory.mkdir(parents=True)
    active = memory / "01_active_task.md"
    active.write_text("x" * active_chars, encoding="utf-8")
    evidence_path = root / "artifacts" / "evidence" / "event.md"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_bytes(evidence)
    record = build_session_derived_record(
        what_changed="P40 L2 transaction returned rc=3 at attach; update success is not established",
        commit="UNCOMMITTED",
        session_id="emergency-test-session",
        memory_binding="unbound",
        test_evidence="NOT CLAIMED: test fixture only",
        next_step="Do not repeat the write without renewed authorization",
        plan_reconciliation="not_applicable",
    )
    return active, evidence_path, record


def _append(root: Path, record: dict[str, str], evidence: Path, *, authorization: str = "owner instruction test"):
    return append_emergency_event_with_outcome(
        project_root=root,
        record=record,
        authorization_ref=authorization,
        not_done="L2 update success not established; no further firmware write authorized",
        evidence_path="artifacts/evidence/event.md",
    )


def test_emergency_event_appends_daily_only_and_preserves_active(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    active_before = active.read_bytes()
    outcome = _append(tmp_path, record, evidence)

    assert outcome.status == MEMORY_WRITE_STATUS_WRITTEN
    assert outcome.path.parent == tmp_path / "memory"
    assert outcome.path.name != "01_active_task.md"
    text = outcome.path.read_text(encoding="utf-8")
    evidence_sha256 = hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert "memory_type: session-derived" in text
    assert "emergency_event_marker: EMERGENCY_EVENT" in text
    assert "emergency_event_authorization_ref: owner instruction test" in text
    assert f"emergency_active_task_sha256: {hashlib.sha256(active_before).hexdigest()}" in text
    assert f"emergency_evidence_sha256: {evidence_sha256}" in text
    assert "emergency_not_done: L2 update success not established" in text
    assert f"record_identity: {outcome.record_identity}" in text
    assert active.read_bytes() == active_before
    assert MemoryJanitor(tmp_path / "memory").check_hot_memory_status()[2] == "EMERGENCY"


def test_emergency_event_binds_record_identity_to_evidence_hash(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    outcome = _append(tmp_path, record, evidence)
    text = outcome.path.read_text(encoding="utf-8")
    evidence_reference = (
        "NOT CLAIMED: emergency event capture only; "
        f"evidence=artifacts/evidence/event.md; sha256={hashlib.sha256(evidence.read_bytes()).hexdigest()}"
    )
    expected = build_record_identity({**record, "test_evidence": evidence_reference})
    assert outcome.record_identity == expected
    assert f"record_identity: {expected}" in text
    assert "emergency_event_identity: " in text


def test_emergency_event_allows_only_one_entry_per_active_digest(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    _append(tmp_path, record, evidence)
    with pytest.raises(ValueError, match="already exists for this active source"):
        _append(tmp_path, record, evidence)
    text = next(tmp_path.glob("memory/2026-??-??.md")).read_text(encoding="utf-8")
    assert text.count("emergency_event_marker: EMERGENCY_EVENT") == 1
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_rejects_non_emergency_pressure_without_writes(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path, active_chars=100)
    with pytest.raises(ValueError, match="only available at measured EMERGENCY"):
        _append(tmp_path, record, evidence)
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 100


@pytest.mark.parametrize("surface", [SURFACE_REVIEW_LOG, SURFACE_ACTIVE_TASK_SUMMARY])
def test_ordinary_projection_writer_refuses_during_emergency(tmp_path: Path, surface: str) -> None:
    active, _evidence, record = _fixture(tmp_path)
    with pytest.raises(ValueError, match="EMERGENCY pressure blocks ordinary memory writes"):
        append_projection_with_outcome(
            project_root=tmp_path,
            record=record,
            surface=surface,
            active_task_summary="must not update active state",
        )
    assert not (tmp_path / "memory" / "04_review_log.md").exists()
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_active_task_supersession_writer_refuses_during_emergency(tmp_path: Path) -> None:
    active, _evidence, _record = _fixture(tmp_path)
    with pytest.raises(ValueError, match="EMERGENCY pressure blocks ordinary memory writes"):
        append_active_task_supersession_relation_with_outcome(
            project_root=tmp_path,
            predecessor_record_identity="a" * 64,
            predecessor_projection_sha256="b" * 64,
            successor_record_identity="c" * 64,
            successor_projection_sha256="d" * 64,
        )
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_rejects_missing_authorization_reference(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    with pytest.raises(ValueError, match="authorization_ref must be non-empty"):
        _append(tmp_path, record, evidence, authorization="  ")
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_rejects_evidence_outside_repository_evidence_root(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("not an approved evidence path", encoding="utf-8")
    with pytest.raises(ValueError, match="under artifacts/evidence"):
        append_emergency_event_with_outcome(
            project_root=tmp_path,
            record=record,
            authorization_ref="owner instruction test",
            not_done="no active-state rewrite",
            evidence_path="outside.md",
        )
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_rejects_evidence_symlink(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    alias = tmp_path / "artifacts" / "evidence" / "alias.md"
    alias.symlink_to(evidence)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        append_emergency_event_with_outcome(
            project_root=tmp_path,
            record=record,
            authorization_ref="owner instruction test",
            not_done="no active-state rewrite",
            evidence_path="artifacts/evidence/alias.md",
        )
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_rejects_oversized_evidence(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path, evidence=b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds the 10 MiB limit"):
        _append(tmp_path, record, evidence)
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_rejects_oversized_entry(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    record["what_changed"] = "x" * 5_000
    with pytest.raises(ValueError, match="exceeds the 4 KiB limit"):
        _append(tmp_path, record, evidence)
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_cannot_claim_plan_update(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    record["plan_reconciliation"] = "updated"
    with pytest.raises(ValueError, match="must not claim a PLAN update"):
        _append(tmp_path, record, evidence)
    assert not list(tmp_path.glob("memory/2026-??-??.md"))
    assert active.read_text(encoding="utf-8") == "x" * 12_000


def test_emergency_event_preserves_existing_daily_bytes_as_prefix(tmp_path: Path) -> None:
    active, evidence, record = _fixture(tmp_path)
    today = datetime.now().astimezone().date().isoformat()
    daily = tmp_path / "memory" / f"{today}.md"
    original = f"# {today}\n\nprior canonical event\n".encode("utf-8")
    daily.write_bytes(original)
    outcome = _append(tmp_path, record, evidence)
    final = outcome.path.read_bytes()
    assert final.startswith(original + b"\n")
    assert active.read_text(encoding="utf-8") == "x" * 12_000
