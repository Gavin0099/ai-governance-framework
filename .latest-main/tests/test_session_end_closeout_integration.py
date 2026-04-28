"""
Integration tests for session_end closeout + session index.
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core._canonical_closeout import write_candidate
from runtime_hooks.core.session_end import run_session_end

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_session_end_closeout"

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


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run(repo_root: Path, session_id="s-001", **kwargs):
    return run_session_end(
        project_root=repo_root,
        session_id=session_id,
        runtime_contract=_BASE_CONTRACT,
        **kwargs,
    )


class TestCanonicalCloseoutReturnValue:
    def test_canonical_closeout_present_in_return(self):
        result = _run(_reset_fixture("canonical_return_present"))
        assert "canonical_closeout" in result
        assert result["canonical_closeout"]["session_id"] == "s-001"

    def test_no_candidate_gives_missing_status(self):
        assert _run(_reset_fixture("missing_status"))["canonical_closeout"]["closeout_status"] == "missing"

    def test_valid_candidate_gives_valid_status(self):
        repo = _reset_fixture("valid_status")
        write_candidate("s-001", repo, _VALID_CANDIDATE)
        assert _run(repo)["canonical_closeout"]["closeout_status"] == "valid"

    def test_schema_invalid_candidate_gives_schema_invalid(self):
        repo = _reset_fixture("schema_invalid_status")
        write_candidate("s-001", repo, {"task_intent": "only one field"})
        assert _run(repo)["canonical_closeout"]["closeout_status"] == "schema_invalid"

    def test_empty_work_summary_gives_content_insufficient(self):
        repo = _reset_fixture("content_insufficient_status")
        write_candidate("s-001", repo, {**_VALID_CANDIDATE, "work_summary": "   "})
        assert _run(repo)["canonical_closeout"]["closeout_status"] == "content_insufficient"

    def test_artifact_not_found_gives_inconsistent(self):
        repo = _reset_fixture("inconsistent_status")
        write_candidate("s-001", repo, {**_VALID_CANDIDATE, "artifacts_referenced": ["src/missing.py"]})
        assert _run(repo)["canonical_closeout"]["closeout_status"] == "inconsistent"

    def test_artifact_found_on_disk_gives_valid(self):
        repo = _reset_fixture("artifact_found_valid")
        (repo / "src").mkdir()
        (repo / "src" / "x.py").write_text("# x", encoding="utf-8")
        write_candidate("s-001", repo, {**_VALID_CANDIDATE, "artifacts_referenced": ["src/x.py"]})
        assert _run(repo)["canonical_closeout"]["closeout_status"] == "valid"


class TestCanonicalCloseoutArtifactOnDisk:
    def test_artifact_path_returned(self):
        result = _run(_reset_fixture("artifact_path_returned"))
        assert result["canonical_closeout_artifact"] is not None
        assert Path(result["canonical_closeout_artifact"]).exists()

    def test_artifact_content_matches_return_value(self):
        repo = _reset_fixture("artifact_matches_return")
        result = _run(repo)
        on_disk = json.loads(Path(result["canonical_closeout_artifact"]).read_text(encoding="utf-8"))
        assert on_disk["closeout_status"] == result["canonical_closeout"]["closeout_status"]

    def test_artifact_in_closeouts_directory(self):
        result = _run(_reset_fixture("artifact_in_closeouts_dir"))
        assert Path(result["canonical_closeout_artifact"]).parent.name == "closeouts"

    def test_artifact_named_by_session_id(self):
        result = _run(_reset_fixture("artifact_named_by_session"), session_id="my-session-42")
        assert Path(result["canonical_closeout_artifact"]).stem == "my-session-42"

    def test_separate_sessions_write_separate_files(self):
        repo = _reset_fixture("separate_sessions")
        _run(repo, session_id="alpha")
        _run(repo, session_id="beta")
        files = {p.stem for p in (repo / "artifacts" / "runtime" / "closeouts").glob("*.json")}
        assert files == {"alpha", "beta"}


class TestSessionIndex:
    def test_index_created_after_session_end(self):
        repo = _reset_fixture("index_created")
        _run(repo)
        assert (repo / "artifacts" / "session-index.ndjson").exists()

    def test_index_entry_has_required_fields(self):
        repo = _reset_fixture("index_required_fields")
        _run(repo, session_id="idx-001")
        lines = [json.loads(l) for l in (repo / "artifacts" / "session-index.ndjson").read_text(encoding="utf-8").splitlines() if l.strip()]
        entry = next(e for e in lines if e["session_id"] == "idx-001")
        assert {"session_id", "closed_at", "closeout_status", "task_intent", "has_open_risks"}.issubset(entry.keys())

    def test_index_status_matches_canonical(self):
        repo = _reset_fixture("index_status_matches")
        write_candidate("s-002", repo, _VALID_CANDIDATE)
        _run(repo, session_id="s-002")
        lines = [json.loads(l) for l in (repo / "artifacts" / "session-index.ndjson").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert next(e for e in lines if e["session_id"] == "s-002")["closeout_status"] == "valid"

    def test_multiple_sessions_append_multiple_lines(self):
        repo = _reset_fixture("index_append_multiple")
        _run(repo, session_id="a")
        _run(repo, session_id="b")
        _run(repo, session_id="c")
        lines = [l for l in (repo / "artifacts" / "session-index.ndjson").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3

    def test_index_is_valid_ndjson(self):
        repo = _reset_fixture("index_valid_ndjson")
        _run(repo, session_id="ndjson-check")
        for line in (repo / "artifacts" / "session-index.ndjson").read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)

    def test_has_open_risks_true_when_risks_present(self):
        repo = _reset_fixture("index_open_risks_true")
        write_candidate("risky-session", repo, {**_VALID_CANDIDATE, "open_risks": ["might break prod"]})
        _run(repo, session_id="risky-session")
        lines = [json.loads(l) for l in (repo / "artifacts" / "session-index.ndjson").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert next(e for e in lines if e["session_id"] == "risky-session")["has_open_risks"] is True

    def test_has_open_risks_false_when_no_risks(self):
        repo = _reset_fixture("index_open_risks_false")
        _run(repo, session_id="safe-session")
        lines = [json.loads(l) for l in (repo / "artifacts" / "session-index.ndjson").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert next(e for e in lines if e["session_id"] == "safe-session")["has_open_risks"] is False
