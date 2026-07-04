"""
Phase 1.5 — session_id handoff end-to-end verification

Proves the complete chain:
  closeout artifact (session_id)
       ↓
  governance_tools.memory_record (build + render)
       ↓
  rendered memory entry (session_id preserved)
       ↓
  memory_authority_guard (no non_canonical_writer violation)

Test cases:
  A. session_id from closeout artifact is preserved in rendered entry
  B. canonical entry with receipt session_id passes guard (no non_canonical_writer)
  C. session_id with closeout artifact provenance binds an entry when commit is
     UNCOMMITTED (provenance fallback — guard does not flag unbound_memory)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.memory_record import (
    build_session_derived_record,
    render_session_derived_entry,
    append_session_derived_entry,
)
from governance_tools.memory_authority_guard import check_daily_memory

# ── constants ─────────────────────────────────────────────────────────────────

# Simulated session_id from a closeout receipt (schema_version 1.1)
RECEIPT_SESSION_ID = "585cfd62-322d-4bde-8f87-786a096ea010"

# Post-cutoff date — ensures guard applies canonical writer enforcement
POST_CUTOFF_FILENAME = "2026-06-02.md"

REAL_COMMIT = "94a120260fb0"    # real hash format → bound
UNCOMMITTED = "UNCOMMITTED"     # no real hash → relies on session_id for binding


def _write_closeout_artifact(project_root: Path, session_id: str = RECEIPT_SESSION_ID) -> None:
    closeouts = project_root / "artifacts" / "runtime" / "closeouts"
    closeouts.mkdir(parents=True, exist_ok=True)
    (closeouts / f"{session_id}.json").write_text(
        json.dumps({"session_id": session_id}) + "\n",
        encoding="utf-8",
    )


# ── A. session_id preserved in rendered entry ─────────────────────────────────

class TestSessionIdPreservedInRenderedEntry:
    """Receipt session_id must survive build → render unchanged."""

    def test_rendered_entry_contains_receipt_session_id(self):
        record = build_session_derived_record(
            what_changed="handoff verification",
            commit=REAL_COMMIT,
            session_id=RECEIPT_SESSION_ID,
            memory_binding="bound",
            test_evidence="unit test",
            next_step="none",
        )
        rendered = render_session_derived_entry(record)
        assert f"session_id: {RECEIPT_SESSION_ID}" in rendered, (
            f"Expected session_id: {RECEIPT_SESSION_ID!r} in rendered entry"
        )

    def test_rendered_entry_has_canonical_writer_fields(self):
        record = build_session_derived_record(
            what_changed="handoff verification",
            commit=REAL_COMMIT,
            session_id=RECEIPT_SESSION_ID,
            memory_binding="bound",
            test_evidence="unit test",
            next_step="none",
        )
        rendered = render_session_derived_entry(record)
        assert "memory_type: session-derived" in rendered
        assert "writer: governance_tools.memory_record" in rendered
        assert "record_format_version: 1.0" in rendered


# ── B. canonical entry with receipt session_id passes guard ───────────────────

class TestCanonicalEntryPassesGuard:
    """Entry produced by memory_record must not trigger non_canonical_writer."""

    def test_no_non_canonical_writer_violation(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        record = build_session_derived_record(
            what_changed="handoff verification",
            commit=REAL_COMMIT,
            session_id=RECEIPT_SESSION_ID,
            memory_binding="bound",
            test_evidence="unit test",
            next_step="none",
        )
        daily = mem / POST_CUTOFF_FILENAME
        daily.write_text(render_session_derived_entry(record), encoding="utf-8")

        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert ncw == [], (
            f"Canonical memory_record entry must not trigger non_canonical_writer: {ncw}"
        )

    def test_append_path_produces_canonical_entry(self, tmp_path):
        """append_session_derived_entry (the write path used by CLI) also passes guard."""
        record = build_session_derived_record(
            what_changed="handoff via append path",
            commit=REAL_COMMIT,
            session_id=RECEIPT_SESSION_ID,
            memory_binding="bound",
            test_evidence="unit test",
            next_step="none",
        )
        append_session_derived_entry(project_root=tmp_path, record=record)

        mem = tmp_path / "memory"
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert ncw == [], (
            f"append_session_derived_entry output must not trigger non_canonical_writer: {ncw}"
        )


# ── C. session_id as provenance-backed fallback binding ───────────────────────

class TestSessionIdAsUnboundFallback:
    """session_id with artifact provenance can bind an entry (no real commit required).

    When commit is UNCOMMITTED but session_id has a closeout artifact, guard
    must not report unbound_memory for this entry.
    """

    def test_uncommitted_commit_with_session_id_not_flagged_as_unbound(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_closeout_artifact(tmp_path)
        record = build_session_derived_record(
            what_changed="fallback binding test",
            commit=UNCOMMITTED,
            session_id=RECEIPT_SESSION_ID,
            memory_binding="unbound",   # memory_binding label; guard uses its own logic
            test_evidence="unit test",
            next_step="none",
        )
        daily = mem / POST_CUTOFF_FILENAME
        daily.write_text(render_session_derived_entry(record), encoding="utf-8")

        violations, _ = check_daily_memory(mem, tmp_path)
        unbound = [v for v in violations if v["code"] == "unbound_memory"]
        assert unbound == [], (
            f"Entry with session_id must not be flagged as unbound_memory even "
            f"when commit is UNCOMMITTED: {unbound}"
        )
