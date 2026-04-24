import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.daily_memory_guard import evaluate_daily_memory_warning, format_human


_FIXTURE_ROOT = Path(__file__).parent / "_tmp_daily_memory_guard"


def _reset_fixture(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _today_str() -> str:
    return datetime.now().astimezone().date().isoformat()


def _write_summary(
    repo: Path,
    *,
    session_id: str,
    memory_mode: str,
    daily_memory_path: str | None,
    daily_memory_record: dict | None = None,
) -> None:
    summaries_dir = repo / "artifacts" / "runtime" / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "closed_at": "2026-04-24T00:00:00+08:00",
        "memory_mode": memory_mode,
        "decision": "AUTO_PROMOTE",
        "daily_memory_path": daily_memory_path,
        "daily_memory_record": daily_memory_record,
    }
    (summaries_dir / f"{session_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_daily_memory_guard_warns_when_non_stateless_today_memory_missing():
    repo = _reset_fixture("warn_missing")
    _write_summary(
        repo,
        session_id="s-warn",
        memory_mode="candidate",
        daily_memory_path=None,
        daily_memory_record={
            "what_changed": "important session",
            "commit": "abc123",
            "test_evidence": "pytest passed",
            "next_step": "follow up",
        },
    )

    result = evaluate_daily_memory_warning(repo)

    assert result["warn"] is True
    assert result["warning"] == "daily_memory_missing_warning"
    assert result["warning_code"] == "daily_memory_missing_warning"
    assert result["scope"] == "latest_session"
    assert result["push_allowed"] is True
    assert result["machine_reason"] == "governance_relevant_session_missing_daily_memory_path"
    assert result["latest_session_id"] == "s-warn"
    assert _today_str() in result["today_memory_path"]
    human = format_human(result)
    assert "daily_memory_missing_warning" in human
    assert "push allowed" in human
    assert "latest non-stateless governance-relevant session has no daily_memory_path" in human


def test_daily_memory_guard_skips_stateless_session():
    repo = _reset_fixture("skip_stateless")
    _write_summary(repo, session_id="s-stateless", memory_mode="stateless", daily_memory_path=None)

    result = evaluate_daily_memory_warning(repo)

    assert result["warn"] is False
    assert result["reason"] == "stateless_session"


def test_daily_memory_guard_still_warns_even_if_today_memory_exists_for_other_session():
    repo = _reset_fixture("today_exists_other_session")
    memory_dir = repo / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / f"{_today_str()}.md").write_text(f"# {_today_str()}\n", encoding="utf-8")
    _write_summary(
        repo,
        session_id="s-ok",
        memory_mode="candidate",
        daily_memory_path=None,
        daily_memory_record={
            "what_changed": "important later session",
            "commit": "def456",
            "test_evidence": "dotnet test passed",
            "next_step": "ship it",
        },
    )

    result = evaluate_daily_memory_warning(repo)

    assert result["warn"] is True
    assert result["reason"] == "session_level_daily_memory_missing"


def test_daily_memory_guard_uses_today_file_only_as_legacy_fallback():
    repo = _reset_fixture("legacy_fallback")
    memory_dir = repo / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / f"{_today_str()}.md").write_text(f"# {_today_str()}\n", encoding="utf-8")
    _write_summary(
        repo,
        session_id="s-legacy",
        memory_mode="candidate",
        daily_memory_path=None,
        daily_memory_record={},
    )

    result = evaluate_daily_memory_warning(repo)

    assert result["warn"] is False
    assert result["reason"] == "legacy_today_daily_memory_present"
