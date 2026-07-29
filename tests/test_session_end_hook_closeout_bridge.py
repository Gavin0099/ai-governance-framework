import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.session_end_hook import run_session_end_hook
from runtime_hooks.core._canonical_closeout import write_candidate, write_session_envelope


_FIXTURE_ROOT = Path(__file__).parent / "_tmp_p1b_session_end_hook_closeout_bridge"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_bound_candidate(
    repo: Path,
    session_id: str,
    *,
    task_intent: str,
    work_summary: str,
    artifacts_referenced: list[str],
    tools_used: list[str] | None = None,
) -> None:
    write_candidate(
        session_id,
        repo,
        {
            "task_intent": task_intent,
            "work_summary": work_summary,
            "tools_used": tools_used or ["inspect"],
            "artifacts_referenced": artifacts_referenced,
            "open_risks": [],
        },
    )


def test_session_end_hook_writes_non_missing_canonical_closeout_when_closeout_present() -> None:
    repo = _reset_fixture("bridge_valid_closeout")
    session_id = "bridge-valid-closeout"
    write_session_envelope(session_id, repo, provider="test")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    touched = repo / "src" / "main.cpp"
    touched.parent.mkdir(parents=True, exist_ok=True)
    touched.write_text("int main(){return 0;}\n", encoding="utf-8")

    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: canonical closeout bridge validation",
                "WORK_COMPLETED: updated src/main.cpp and validated closeout bridge",
                "FILES_TOUCHED: src/main.cpp",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: one week observation window",
                "RECOMMENDED_MEMORY_UPDATE: keep closeout generation enabled",
                "TASK_ID: bridge-test",
                "RUN_ID: run-001",
                "COMMIT_HASH: abc1234",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _write_bound_candidate(
        repo,
        session_id,
        task_intent="canonical closeout bridge validation",
        work_summary="updated src/main.cpp and validated closeout bridge",
        artifacts_referenced=["src/main.cpp"],
    )
    result = run_session_end_hook(repo)
    assert result["closeout_status"] == "valid"

    canonical_path = repo / "artifacts" / "runtime" / "closeouts" / f"{result['session_id']}.json"
    assert canonical_path.exists()
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    assert canonical["closeout_status"] == "valid"
    assert canonical["task_intent"] == "canonical closeout bridge validation"


def test_session_end_hook_accepts_closeout_metadata_lines_when_closeout_present() -> None:
    repo = _reset_fixture("bridge_metadata_lines")
    session_id = "bridge-metadata-lines"
    write_session_envelope(session_id, repo, provider="test")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    touched = repo / "src" / "main.cpp"
    touched.parent.mkdir(parents=True, exist_ok=True)
    touched.write_text("int main(){return 0;}\n", encoding="utf-8")

    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: metadata bridge validation",
                "WORK_COMPLETED: validated extra run metadata lines in src/main.cpp",
                "FILES_TOUCHED: src/main.cpp",
                "CHECKS_RUN: session_end_hook; npm",
                "OPEN_RISKS: NONE",
                "NOT_DONE: NONE",
                "RECOMMENDED_MEMORY_UPDATE: NO_UPDATE",
                "TASK_ID: metadata-test",
                "RUN_ID: run-002",
                "COMMIT_HASH: def5678",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _write_bound_candidate(
        repo,
        session_id,
        task_intent="metadata bridge validation",
        work_summary="validated extra run metadata lines in src/main.cpp",
        artifacts_referenced=["src/main.cpp"],
        tools_used=["session_end_hook", "npm"],
    )
    result = run_session_end_hook(repo, hook_session_id=session_id)
    assert result["closeout_status"] == "valid"
    assert result["per_layer_results"]["missing_fields"] == []


def test_session_end_hook_no_ledger_write_skips_tracked_ledgers() -> None:
    repo = _reset_fixture("bridge_no_ledger_write")
    write_session_envelope("bridge-no-ledger", repo, provider="test")

    result = run_session_end_hook(
        repo,
        hook_session_id="bridge-no-ledger",
        ledger_write_allowed=False,
    )

    assert result["ledger_write_status"] == {
        "ledger_write_allowed": False,
        "session_index": "skipped_no_write_mode",
        "claim_enforcement_receipt": "skipped_no_write_mode",
    }
    assert not (repo / "artifacts" / "session-index.ndjson").exists()
    assert not (repo / "artifacts" / "claim-enforcement" / "claim-enforcement-receipts.ndjson").exists()


def test_fresh_legacy_closeout_without_bound_candidate_fails_closed() -> None:
    repo = _reset_fixture("bridge_legacy_without_candidate")
    session_id = "bridge-legacy-without-candidate"
    write_session_envelope(session_id, repo, provider="test")
    (repo / "legacy.txt").write_text("legacy content\n", encoding="utf-8")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: legacy closeout without identity",
                "WORK_COMPLETED: updated legacy.txt",
                "FILES_TOUCHED: legacy.txt",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: NONE",
                "RECOMMENDED_MEMORY_UPDATE: preserve old content",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_session_end_hook(
        repo,
        hook_session_id=session_id,
        ledger_write_allowed=False,
    )

    assert result["closeout_status"] == "stale_or_mismatched"
    assert result["session_binding"]["status"] == "session_candidate_missing"
    assert result["decision"] == "DO_NOT_PROMOTE"
    assert result["promoted"] is False
    canonical = json.loads(
        (
            repo
            / "artifacts"
            / "runtime"
            / "closeouts"
            / f"{session_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert canonical["closeout_status"] == "missing"
    daily_memory = Path(result["daily_memory_path"]).read_text(encoding="utf-8")
    assert "legacy closeout without identity" not in daily_memory


def test_stale_closeout_is_not_promoted_for_new_session() -> None:
    repo = _reset_fixture("bridge_stale_closeout")
    session_id = "bridge-stale-closeout"
    envelope = write_session_envelope(session_id, repo, provider="test")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: stale prior task",
                "WORK_COMPLETED: updated stale.txt",
                "FILES_TOUCHED: stale.txt",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: NONE",
                "RECOMMENDED_MEMORY_UPDATE: stale prior memory",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    started_at = datetime.fromisoformat(envelope["started_at"])
    stale_time = (started_at - timedelta(seconds=5)).timestamp()
    os.utime(closeout, (stale_time, stale_time))

    result = run_session_end_hook(
        repo,
        hook_session_id=session_id,
        ledger_write_allowed=False,
    )

    assert result["closeout_status"] == "stale_or_mismatched"
    assert result["session_binding"]["status"] == "session_candidate_missing"
    assert result["promoted"] is False
    assert result["decision"] == "DO_NOT_PROMOTE"
    assert result["daily_memory_write_status"] == "written"
    assert "stale prior task" not in Path(result["daily_memory_path"]).read_text(
        encoding="utf-8"
    )


def test_fresh_but_different_closeout_is_not_bound_to_session_candidate() -> None:
    repo = _reset_fixture("bridge_content_mismatch")
    session_id = "bridge-content-mismatch"
    write_session_envelope(session_id, repo, provider="test")
    touched = repo / "fresh.txt"
    touched.write_text("fresh candidate\n", encoding="utf-8")
    (repo / "stale.txt").write_text("stale copied closeout\n", encoding="utf-8")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: stale copied task",
                "WORK_COMPLETED: updated stale.txt",
                "FILES_TOUCHED: stale.txt",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: NONE",
                "RECOMMENDED_MEMORY_UPDATE: stale prior memory",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_bound_candidate(
        repo,
        session_id,
        task_intent="fresh candidate task",
        work_summary="updated fresh.txt",
        artifacts_referenced=["fresh.txt"],
    )

    result = run_session_end_hook(
        repo,
        hook_session_id=session_id,
        ledger_write_allowed=False,
    )

    assert result["closeout_status"] == "stale_or_mismatched"
    assert result["closeout_pre_binding_status"] == "session_candidate_content_mismatch"
    assert result["decision"] == "DO_NOT_PROMOTE"
    assert result["promoted"] is False


def test_consumed_closeout_cannot_be_reused(monkeypatch) -> None:
    repo = _reset_fixture("bridge_consumed_once")
    session_id = "bridge-consumed-once"
    write_session_envelope(session_id, repo, provider="test")
    touched = repo / "consumed.txt"
    touched.write_text("consumed once\n", encoding="utf-8")
    closeout = repo / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(
        "\n".join(
            [
                "TASK_INTENT: consume once validation",
                "WORK_COMPLETED: updated consumed.txt",
                "FILES_TOUCHED: consumed.txt",
                "CHECKS_RUN: NONE",
                "OPEN_RISKS: NONE",
                "NOT_DONE: NONE",
                "RECOMMENDED_MEMORY_UPDATE: preserve once",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _write_bound_candidate(
        repo,
        session_id,
        task_intent="consume once validation",
        work_summary="updated consumed.txt",
        artifacts_referenced=["consumed.txt"],
    )
    first = run_session_end_hook(repo, hook_session_id=session_id)

    import governance_tools.session_end_hook as hook_module

    def _unexpected_side_effect(*args, **kwargs):
        raise AssertionError("already-consumed hook must return before side effects")

    monkeypatch.setattr(hook_module, "_append_canonical_audit_log", _unexpected_side_effect)
    monkeypatch.setattr(hook_module, "write_candidate_and_advisory", _unexpected_side_effect)
    monkeypatch.setattr(hook_module, "_ingest_transcript_for_closeout", _unexpected_side_effect)
    second = run_session_end_hook(repo, hook_session_id=session_id)

    assert first["session_binding"]["status"] == "valid"
    assert second["session_binding"]["status"] == "already_consumed"
    assert second["closeout_status"] == "stale_or_mismatched"
    assert second["decision"] == "ALREADY_CONSUMED"
    assert second["daily_memory_write_attempted"] is False
    assert second["promoted"] is False
