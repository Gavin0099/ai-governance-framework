import os
import time
from pathlib import Path

from governance_tools.memory_freshness_guard import evaluate


DAY = 24 * 60 * 60


def _write_memory_file(memory_root: Path, name: str) -> Path:
    path = memory_root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("memory\n", encoding="utf-8")
    return path


def _write_required_memory(memory_root: Path) -> tuple[Path, Path]:
    active = _write_memory_file(memory_root, "01_active_task.md")
    knowledge = _write_memory_file(memory_root, "03_knowledge_base.md")
    return active, knowledge


def _check_by_name(result: dict, logical_name: str) -> dict:
    return next(item for item in result["checks"] if item["logical_name"] == logical_name)


def test_fresh_required_memory_files_pass(tmp_path: Path) -> None:
    _write_required_memory(tmp_path / "memory")

    result = evaluate(tmp_path, max_age_days=30)

    assert result["ok"] is True
    assert result["failures"] == []
    active = _check_by_name(result, "active_task")
    assert active["exists"] is True
    assert active["is_file"] is True
    assert active["stale"] is False
    assert active["reason"] is None


def test_missing_required_memory_file_blocks(tmp_path: Path) -> None:
    _write_memory_file(tmp_path / "memory", "03_knowledge_base.md")

    result = evaluate(tmp_path, max_age_days=30)

    assert result["ok"] is False
    active = _check_by_name(result, "active_task")
    assert active["exists"] is False
    assert active["is_file"] is False
    assert active["stale"] is True
    assert active["reason"] == "missing"
    assert active in result["failures"]


def test_stale_required_memory_file_blocks(tmp_path: Path) -> None:
    active, _knowledge = _write_required_memory(tmp_path / "memory")
    old = time.time() - (40 * DAY)
    os.utime(active, (old, old))

    result = evaluate(tmp_path, max_age_days=30)

    assert result["ok"] is False
    active_check = _check_by_name(result, "active_task")
    assert active_check["is_file"] is True
    assert active_check["stale"] is True
    assert active_check["reason"] == "stale"
    assert active_check in result["failures"]


def test_future_required_memory_mtime_blocks(tmp_path: Path) -> None:
    active, _knowledge = _write_required_memory(tmp_path / "memory")
    future = time.time() + (40 * DAY)
    os.utime(active, (future, future))

    result = evaluate(tmp_path, max_age_days=30)

    assert result["ok"] is False
    active_check = _check_by_name(result, "active_task")
    assert active_check["is_file"] is True
    assert active_check["future_mtime"] is True
    assert active_check["stale"] is True
    assert active_check["reason"] == "future_mtime"
    assert active_check in result["failures"]


def test_directory_at_required_memory_path_blocks(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    (memory_root / "01_active_task.md").mkdir(parents=True)
    _write_memory_file(memory_root, "03_knowledge_base.md")

    result = evaluate(tmp_path, max_age_days=30)

    assert result["ok"] is False
    active_check = _check_by_name(result, "active_task")
    assert active_check["exists"] is True
    assert active_check["is_file"] is False
    assert active_check["stale"] is True
    assert active_check["reason"] == "not_file"
    assert active_check in result["failures"]


def test_zero_max_age_keeps_fresh_file_boundary(tmp_path: Path) -> None:
    _write_required_memory(tmp_path / "memory")

    result = evaluate(tmp_path, max_age_days=0)

    assert result["ok"] is True
    active_check = _check_by_name(result, "active_task")
    assert active_check["reason"] is None
