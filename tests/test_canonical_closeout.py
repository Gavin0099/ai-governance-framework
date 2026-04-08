"""
Tests for runtime_hooks/core/_canonical_closeout.py

Coverage:
- build_canonical_closeout(): all 5 closeout_status paths
- _validate_candidate_schema(): field presence + type checks
- _run_semantic_validation(): content_insufficient + inconsistent + valid
- pick_latest_candidate(): empty dir, single file, multiple files
- write_candidate(): append-only, deterministic output
- write_canonical_closeout(): creates dir, writes file
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout import (
    build_canonical_closeout,
    pick_latest_candidate,
    write_candidate,
    write_canonical_closeout,
    _validate_candidate_schema,
)

CLOSED_AT = "2026-04-08T00:00:00+00:00"
SESSION_ID = "test-session-001"

_VALID_CANDIDATE = {
    "task_intent": "add feature X",
    "work_summary": "implemented X in src/x.py, added tests",
    "tools_used": ["read", "edit"],
    "artifacts_referenced": ["src/x.py"],
    "open_risks": [],
}


# ---------------------------------------------------------------------------
# build_canonical_closeout — status paths
# ---------------------------------------------------------------------------

class TestBuildCanonicalCloseout:

    def _build(self, candidate, artifacts=None, signals=None):
        return build_canonical_closeout(
            session_id=SESSION_ID,
            closed_at=CLOSED_AT,
            candidate_payload=candidate,
            existing_artifacts=frozenset(artifacts or []),
            runtime_signals=signals or {},
        )

    def test_no_candidate_gives_missing(self):
        result = self._build(None)
        assert result["closeout_status"] == "missing"
        assert result["session_id"] == SESSION_ID
        assert result["closed_at"] == CLOSED_AT
        assert result["task_intent"] is None
        assert result["work_summary"] is None
        assert result["evidence_summary"]["tools_used"] == []
        assert result["open_risks"] == []

    def test_schema_invalid_gives_schema_invalid(self):
        result = self._build({"task_intent": "only one field"})
        assert result["closeout_status"] == "schema_invalid"

    def test_non_dict_candidate_gives_schema_invalid(self):
        result = self._build("not a dict")
        assert result["closeout_status"] == "schema_invalid"

    def test_wrong_type_field_gives_schema_invalid(self):
        bad = {**_VALID_CANDIDATE, "tools_used": "not-a-list"}
        result = self._build(bad)
        assert result["closeout_status"] == "schema_invalid"

    def test_empty_work_summary_gives_content_insufficient(self):
        candidate = {**_VALID_CANDIDATE, "work_summary": "  "}
        result = self._build(candidate, artifacts=["src/x.py"])
        assert result["closeout_status"] == "content_insufficient"

    def test_no_evidence_gives_content_insufficient(self):
        candidate = {
            **_VALID_CANDIDATE,
            "tools_used": [],
            "artifacts_referenced": [],
        }
        result = self._build(candidate)
        assert result["closeout_status"] == "content_insufficient"

    def test_artifact_not_found_gives_inconsistent(self):
        # artifacts_referenced lists "src/x.py" but it's not in existing_artifacts
        result = self._build(_VALID_CANDIDATE, artifacts=[])
        assert result["closeout_status"] == "inconsistent"

    def test_verifiable_tool_without_runtime_signal_gives_inconsistent(self):
        candidate = {**_VALID_CANDIDATE, "tools_used": ["pytest"], "artifacts_referenced": []}
        # runtime_signals has no tools_executed
        result = self._build(candidate, artifacts=[], signals={})
        assert result["closeout_status"] == "inconsistent"

    def test_verifiable_tool_with_runtime_signal_gives_valid(self):
        candidate = {**_VALID_CANDIDATE, "tools_used": ["pytest"], "artifacts_referenced": []}
        result = self._build(
            candidate,
            artifacts=[],
            signals={"tools_executed": ["pytest"]},
        )
        assert result["closeout_status"] == "valid"

    def test_valid_candidate_gives_valid(self):
        result = self._build(_VALID_CANDIDATE, artifacts=["src/x.py"])
        assert result["closeout_status"] == "valid"
        assert result["task_intent"] == "add feature X"
        assert result["work_summary"] == "implemented X in src/x.py, added tests"
        assert result["evidence_summary"]["tools_used"] == ["read", "edit"]
        assert result["evidence_summary"]["artifacts_referenced"] == ["src/x.py"]

    def test_canonical_is_deterministic(self):
        """Same inputs → same output (pure function)."""
        a = self._build(_VALID_CANDIDATE, artifacts=["src/x.py"])
        b = self._build(_VALID_CANDIDATE, artifacts=["src/x.py"])
        assert a == b

    def test_session_id_and_closed_at_always_present(self):
        for candidate in [None, _VALID_CANDIDATE]:
            result = self._build(candidate, artifacts=["src/x.py"])
            assert result["session_id"] == SESSION_ID
            assert result["closed_at"] == CLOSED_AT


# ---------------------------------------------------------------------------
# pick_latest_candidate
# ---------------------------------------------------------------------------

class TestPickLatestCandidate:

    def test_no_dir_returns_none(self, tmp_path):
        assert pick_latest_candidate(SESSION_ID, tmp_path) is None

    def test_empty_dir_returns_none(self, tmp_path):
        (tmp_path / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID).mkdir(
            parents=True
        )
        assert pick_latest_candidate(SESSION_ID, tmp_path) is None

    def test_single_file_returned(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        d.mkdir(parents=True)
        payload = {"task_intent": "single"}
        (d / "20260408T000000000000Z.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        result = pick_latest_candidate(SESSION_ID, tmp_path)
        assert result["task_intent"] == "single"

    def test_latest_file_selected_by_lexicographic_order(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        d.mkdir(parents=True)
        (d / "20260408T100000000000Z.json").write_text(
            json.dumps({"task_intent": "first"}), encoding="utf-8"
        )
        (d / "20260408T120000000000Z.json").write_text(
            json.dumps({"task_intent": "latest"}), encoding="utf-8"
        )
        result = pick_latest_candidate(SESSION_ID, tmp_path)
        assert result["task_intent"] == "latest"

    def test_unreadable_file_returns_none(self, tmp_path):
        d = tmp_path / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        d.mkdir(parents=True)
        (d / "20260408T000000000000Z.json").write_text("NOT JSON {{{", encoding="utf-8")
        assert pick_latest_candidate(SESSION_ID, tmp_path) is None


# ---------------------------------------------------------------------------
# write_candidate (append-only)
# ---------------------------------------------------------------------------

class TestWriteCandidate:

    def test_creates_timestamped_file(self, tmp_path):
        path = write_candidate(SESSION_ID, tmp_path, _VALID_CANDIDATE, timestamp="20260408T000000000000Z")
        assert path.exists()
        assert path.name == "20260408T000000000000Z.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["task_intent"] == _VALID_CANDIDATE["task_intent"]

    def test_two_writes_produce_two_files(self, tmp_path):
        write_candidate(SESSION_ID, tmp_path, _VALID_CANDIDATE, timestamp="20260408T100000000000Z")
        write_candidate(SESSION_ID, tmp_path, _VALID_CANDIDATE, timestamp="20260408T120000000000Z")
        d = tmp_path / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        assert len(list(d.glob("*.json"))) == 2


# ---------------------------------------------------------------------------
# write_canonical_closeout
# ---------------------------------------------------------------------------

class TestWriteCanonicalCloseout:

    def test_writes_to_closeouts_dir(self, tmp_path):
        canonical = build_canonical_closeout(
            session_id=SESSION_ID,
            closed_at=CLOSED_AT,
            candidate_payload=_VALID_CANDIDATE,
            existing_artifacts=frozenset(["src/x.py"]),
            runtime_signals={},
        )
        path = write_canonical_closeout(canonical, tmp_path)
        assert path.exists()
        assert path.parent.name == "closeouts"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["session_id"] == SESSION_ID
        assert loaded["closeout_status"] == "valid"

    def test_creates_directory_if_missing(self, tmp_path):
        canonical = build_canonical_closeout(
            session_id="new-session",
            closed_at=CLOSED_AT,
            candidate_payload=None,
            existing_artifacts=frozenset(),
            runtime_signals={},
        )
        path = write_canonical_closeout(canonical, tmp_path)
        assert path.parent.is_dir()


# ---------------------------------------------------------------------------
# schema validation edge cases
# ---------------------------------------------------------------------------

class TestValidateCandidateSchema:

    def test_all_fields_present_and_correct(self):
        ok, _ = _validate_candidate_schema(_VALID_CANDIDATE)
        assert ok is True

    def test_missing_field_fails(self):
        for field in _VALID_CANDIDATE:
            partial = {k: v for k, v in _VALID_CANDIDATE.items() if k != field}
            ok, reason = _validate_candidate_schema(partial)
            assert ok is False
            assert field in reason

    def test_list_with_non_string_element_fails(self):
        bad = {**_VALID_CANDIDATE, "tools_used": ["pytest", 42]}
        ok, _ = _validate_candidate_schema(bad)
        assert ok is False
