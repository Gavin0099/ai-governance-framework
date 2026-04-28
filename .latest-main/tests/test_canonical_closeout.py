"""
Tests for runtime_hooks/core/_canonical_closeout.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout import (
    _validate_candidate_schema,
    build_canonical_closeout,
    pick_latest_candidate,
    write_candidate,
    write_canonical_closeout,
)

CLOSED_AT = "2026-04-08T00:00:00+00:00"
SESSION_ID = "test-session-001"
_FIXTURE_ROOT = Path(__file__).parent / "_tmp_canonical_closeout"

_VALID_CANDIDATE = {
    "task_intent": "add feature X",
    "work_summary": "implemented X in src/x.py, added tests",
    "tools_used": ["read", "edit"],
    "artifacts_referenced": ["src/x.py"],
    "open_risks": [],
}


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


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

    def test_schema_invalid_gives_schema_invalid(self):
        assert self._build({"task_intent": "only one field"})["closeout_status"] == "schema_invalid"

    def test_non_dict_candidate_gives_schema_invalid(self):
        assert self._build("not a dict")["closeout_status"] == "schema_invalid"

    def test_wrong_type_field_gives_schema_invalid(self):
        bad = {**_VALID_CANDIDATE, "tools_used": "not-a-list"}
        assert self._build(bad)["closeout_status"] == "schema_invalid"

    def test_empty_work_summary_gives_content_insufficient(self):
        candidate = {**_VALID_CANDIDATE, "work_summary": "  "}
        assert self._build(candidate, artifacts=["src/x.py"])["closeout_status"] == "content_insufficient"

    def test_no_evidence_gives_content_insufficient(self):
        candidate = {**_VALID_CANDIDATE, "tools_used": [], "artifacts_referenced": []}
        assert self._build(candidate)["closeout_status"] == "content_insufficient"

    def test_artifact_not_found_gives_inconsistent(self):
        assert self._build(_VALID_CANDIDATE, artifacts=[])["closeout_status"] == "inconsistent"

    def test_verifiable_tool_without_runtime_signal_gives_inconsistent(self):
        candidate = {**_VALID_CANDIDATE, "tools_used": ["pytest"], "artifacts_referenced": []}
        assert self._build(candidate, artifacts=[], signals={})["closeout_status"] == "inconsistent"

    def test_verifiable_tool_with_runtime_signal_gives_valid(self):
        candidate = {**_VALID_CANDIDATE, "tools_used": ["pytest"], "artifacts_referenced": []}
        assert self._build(candidate, artifacts=[], signals={"tools_executed": ["pytest"]})["closeout_status"] == "valid"

    def test_valid_candidate_gives_valid(self):
        result = self._build(_VALID_CANDIDATE, artifacts=["src/x.py"])
        assert result["closeout_status"] == "valid"
        assert result["task_intent"] == "add feature X"

    def test_canonical_is_deterministic(self):
        assert self._build(_VALID_CANDIDATE, artifacts=["src/x.py"]) == self._build(_VALID_CANDIDATE, artifacts=["src/x.py"])

    def test_session_id_and_closed_at_always_present(self):
        for candidate in [None, _VALID_CANDIDATE]:
            result = self._build(candidate, artifacts=["src/x.py"])
            assert result["session_id"] == SESSION_ID
            assert result["closed_at"] == CLOSED_AT


class TestPickLatestCandidate:
    def test_no_dir_returns_none(self):
        assert pick_latest_candidate(SESSION_ID, _reset_fixture("pick_latest_no_dir")) is None

    def test_empty_dir_returns_none(self):
        repo = _reset_fixture("pick_latest_empty_dir")
        (repo / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID).mkdir(parents=True)
        assert pick_latest_candidate(SESSION_ID, repo) is None

    def test_single_file_returned(self):
        repo = _reset_fixture("pick_latest_single")
        d = repo / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        d.mkdir(parents=True)
        (d / "20260408T000000000000Z.json").write_text(json.dumps({"task_intent": "single"}), encoding="utf-8")
        assert pick_latest_candidate(SESSION_ID, repo)["task_intent"] == "single"

    def test_latest_file_selected_by_lexicographic_order(self):
        repo = _reset_fixture("pick_latest_lexicographic")
        d = repo / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        d.mkdir(parents=True)
        (d / "20260408T100000000000Z.json").write_text(json.dumps({"task_intent": "first"}), encoding="utf-8")
        (d / "20260408T120000000000Z.json").write_text(json.dumps({"task_intent": "latest"}), encoding="utf-8")
        assert pick_latest_candidate(SESSION_ID, repo)["task_intent"] == "latest"

    def test_unreadable_file_returns_none(self):
        repo = _reset_fixture("pick_latest_unreadable")
        d = repo / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        d.mkdir(parents=True)
        (d / "20260408T000000000000Z.json").write_text("NOT JSON {{{", encoding="utf-8")
        assert pick_latest_candidate(SESSION_ID, repo) is None


class TestWriteCandidate:
    def test_creates_timestamped_file(self):
        repo = _reset_fixture("write_candidate_timestamped")
        path = write_candidate(SESSION_ID, repo, _VALID_CANDIDATE, timestamp="20260408T000000000000Z")
        assert path.exists()
        assert path.name == "20260408T000000000000Z.json"

    def test_two_writes_produce_two_files(self):
        repo = _reset_fixture("write_candidate_append")
        write_candidate(SESSION_ID, repo, _VALID_CANDIDATE, timestamp="20260408T100000000000Z")
        write_candidate(SESSION_ID, repo, _VALID_CANDIDATE, timestamp="20260408T120000000000Z")
        d = repo / "artifacts" / "runtime" / "closeout_candidates" / SESSION_ID
        assert len(list(d.glob("*.json"))) == 2


class TestWriteCanonicalCloseout:
    def test_writes_to_closeouts_dir(self):
        repo = _reset_fixture("write_canonical_closeouts_dir")
        canonical = build_canonical_closeout(
            session_id=SESSION_ID,
            closed_at=CLOSED_AT,
            candidate_payload=_VALID_CANDIDATE,
            existing_artifacts=frozenset(["src/x.py"]),
            runtime_signals={},
        )
        path = write_canonical_closeout(canonical, repo)
        assert path.exists()
        assert path.parent.name == "closeouts"

    def test_creates_directory_if_missing(self):
        repo = _reset_fixture("write_canonical_creates_dir")
        canonical = build_canonical_closeout(
            session_id="new-session",
            closed_at=CLOSED_AT,
            candidate_payload=None,
            existing_artifacts=frozenset(),
            runtime_signals={},
        )
        assert write_canonical_closeout(canonical, repo).parent.is_dir()


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
        ok, _ = _validate_candidate_schema({**_VALID_CANDIDATE, "tools_used": ["pytest", 42]})
        assert ok is False
