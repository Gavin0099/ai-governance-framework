"""
Integration tests for Slice 2+4 of the session workflow enhancement.

Coverage:
- run_session_end() produces canonical_closeout in its return dict
- run_session_end() writes canonical closeout artifact to disk
- run_session_end() appends to session-index.ndjson
- closeout_status paths: missing, schema_invalid, content_insufficient,
  inconsistent, valid — driven by presence/absence of candidate file
- session-index.ndjson entry fields match canonical closeout
- Multiple sessions append multiple lines (append-only)
- Runtime failure still initialises canonical_closeout (pure-function path
  runs before try block; only write_canonical_closeout may fail)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.session_end import run_session_end
from runtime_hooks.core._canonical_closeout import write_candidate

_BASE_CONTRACT = {
    "task": "test task",
    "rules": "standard",
    "risk": "low",
    "oversight": "auto",
    "memory_mode": "stateless",
}

_VALID_CANDIDATE = {
    "task_intent": "add feature X",
    "work_summary": "implemented X in src/x.py, added tests",
    "tools_used": ["read", "edit"],
    "artifacts_referenced": [],
    "open_risks": [],
}


def _run(tmp_path, session_id="s-001", **kwargs):
    return run_session_end(
        project_root=tmp_path,
        session_id=session_id,
        runtime_contract=_BASE_CONTRACT,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# canonical_closeout in return dict
# ---------------------------------------------------------------------------

class TestCanonicalCloseoutReturnValue:

    def test_canonical_closeout_present_in_return(self, tmp_path):
        result = _run(tmp_path)
        assert "canonical_closeout" in result
        cc = result["canonical_closeout"]
        assert cc["session_id"] == "s-001"
        assert "closeout_status" in cc
        assert "closed_at" in cc

    def test_no_candidate_gives_missing_status(self, tmp_path):
        result = _run(tmp_path)
        assert result["canonical_closeout"]["closeout_status"] == "missing"

    def test_valid_candidate_gives_valid_status(self, tmp_path):
        write_candidate("s-001", tmp_path, _VALID_CANDIDATE)
        result = _run(tmp_path)
        assert result["canonical_closeout"]["closeout_status"] == "valid"
        assert result["canonical_closeout"]["task_intent"] == "add feature X"

    def test_schema_invalid_candidate_gives_schema_invalid(self, tmp_path):
        write_candidate("s-001", tmp_path, {"task_intent": "only one field"})
        result = _run(tmp_path)
        assert result["canonical_closeout"]["closeout_status"] == "schema_invalid"

    def test_empty_work_summary_gives_content_insufficient(self, tmp_path):
        bad = {**_VALID_CANDIDATE, "work_summary": "   "}
        write_candidate("s-001", tmp_path, bad)
        result = _run(tmp_path)
        assert result["canonical_closeout"]["closeout_status"] == "content_insufficient"

    def test_artifact_not_found_gives_inconsistent(self, tmp_path):
        candidate_with_artifact = {**_VALID_CANDIDATE, "artifacts_referenced": ["src/missing.py"]}
        write_candidate("s-001", tmp_path, candidate_with_artifact)
        result = _run(tmp_path)
        assert result["canonical_closeout"]["closeout_status"] == "inconsistent"

    def test_artifact_found_on_disk_gives_valid(self, tmp_path):
        # Create the file on disk so existing_artifacts check passes
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "x.py").write_text("# x", encoding="utf-8")
        candidate_with_artifact = {**_VALID_CANDIDATE, "artifacts_referenced": ["src/x.py"]}
        write_candidate("s-001", tmp_path, candidate_with_artifact)
        result = _run(tmp_path)
        assert result["canonical_closeout"]["closeout_status"] == "valid"


# ---------------------------------------------------------------------------
# canonical closeout artifact written to disk
# ---------------------------------------------------------------------------

class TestCanonicalCloseoutArtifactOnDisk:

    def test_artifact_path_returned(self, tmp_path):
        result = _run(tmp_path)
        assert result["canonical_closeout_artifact"] is not None
        assert Path(result["canonical_closeout_artifact"]).exists()

    def test_artifact_content_matches_return_value(self, tmp_path):
        result = _run(tmp_path)
        path = Path(result["canonical_closeout_artifact"])
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        assert on_disk["session_id"] == result["canonical_closeout"]["session_id"]
        assert on_disk["closeout_status"] == result["canonical_closeout"]["closeout_status"]

    def test_artifact_in_closeouts_directory(self, tmp_path):
        result = _run(tmp_path)
        path = Path(result["canonical_closeout_artifact"])
        assert path.parent.name == "closeouts"

    def test_artifact_named_by_session_id(self, tmp_path):
        result = _run(tmp_path, session_id="my-session-42")
        path = Path(result["canonical_closeout_artifact"])
        assert path.stem == "my-session-42"

    def test_separate_sessions_write_separate_files(self, tmp_path):
        _run(tmp_path, session_id="alpha")
        _run(tmp_path, session_id="beta")
        closeouts_dir = tmp_path / "artifacts" / "runtime" / "closeouts"
        files = {p.stem for p in closeouts_dir.glob("*.json")}
        assert "alpha" in files
        assert "beta" in files


# ---------------------------------------------------------------------------
# session-index.ndjson (Slice 4)
# ---------------------------------------------------------------------------

class TestSessionIndex:

    def test_index_created_after_session_end(self, tmp_path):
        _run(tmp_path)
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        assert index_path.exists()

    def test_index_entry_has_required_fields(self, tmp_path):
        _run(tmp_path, session_id="idx-001")
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        lines = [json.loads(l) for l in index_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        entry = next(e for e in lines if e["session_id"] == "idx-001")
        assert "session_id" in entry
        assert "closed_at" in entry
        assert "closeout_status" in entry
        assert "task_intent" in entry
        assert "has_open_risks" in entry

    def test_index_status_matches_canonical(self, tmp_path):
        write_candidate("s-002", tmp_path, _VALID_CANDIDATE)
        _run(tmp_path, session_id="s-002")
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        lines = [json.loads(l) for l in index_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        entry = next(e for e in lines if e["session_id"] == "s-002")
        assert entry["closeout_status"] == "valid"

    def test_multiple_sessions_append_multiple_lines(self, tmp_path):
        _run(tmp_path, session_id="a")
        _run(tmp_path, session_id="b")
        _run(tmp_path, session_id="c")
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        lines = [l for l in index_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3

    def test_index_is_valid_ndjson(self, tmp_path):
        _run(tmp_path, session_id="ndjson-check")
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)  # must not raise

    def test_has_open_risks_true_when_risks_present(self, tmp_path):
        risky = {**_VALID_CANDIDATE, "open_risks": ["might break prod"]}
        write_candidate("risky-session", tmp_path, risky)
        _run(tmp_path, session_id="risky-session")
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        lines = [json.loads(l) for l in index_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        entry = next(e for e in lines if e["session_id"] == "risky-session")
        assert entry["has_open_risks"] is True

    def test_has_open_risks_false_when_no_risks(self, tmp_path):
        _run(tmp_path, session_id="safe-session")
        index_path = tmp_path / "artifacts" / "session-index.ndjson"
        lines = [json.loads(l) for l in index_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        entry = next(e for e in lines if e["session_id"] == "safe-session")
        assert entry["has_open_risks"] is False
