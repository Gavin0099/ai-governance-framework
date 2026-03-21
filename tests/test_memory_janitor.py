"""
Unit tests for governance_tools/memory_janitor.py
Coverage target: ≥ 70%

Test groups:
  A. check_hot_memory_status   — threshold boundary + missing file
  B. generate_warning_message  — all status codes
  C. analyze_archivable_content— regex heuristics + missing file
  D. execute_cleanup           — dry-run / real run / idempotency / edge cases
  E. manifest                  — _load_manifest / _save_manifest round-trip
"""

import json
import sys
import os
from pathlib import Path

import pytest

# Make governance_tools importable without installation
sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.memory_janitor import MemoryJanitor


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mem_root(tmp_path):
    """建立暫存 memory/ 目錄，01_active_task.md 尚不存在。"""
    root = tmp_path / "memory"
    root.mkdir()
    return root


@pytest.fixture
def janitor(mem_root):
    return MemoryJanitor(mem_root)


def _write_lines(path: Path, n: int, extra: str = "") -> None:
    """在 path 寫入 n 行內容（最後附加 extra 區塊）。"""
    lines = [f"line {i}\n" for i in range(1, n + 1)]
    path.write_text("".join(lines) + extra, encoding="utf-8")


# ── A. check_hot_memory_status ────────────────────────────────────────────

class TestCheckHotMemoryStatus:
    def test_missing_file_returns_safe(self, janitor):
        count, _, status = janitor.check_hot_memory_status()
        assert count == 0
        assert status == "SAFE"

    def test_empty_file_returns_safe(self, janitor):
        janitor.active_task_file.write_text("", encoding="utf-8")
        count, _, status = janitor.check_hot_memory_status()
        assert count == 0
        assert status == "SAFE"

    def test_below_soft_limit_is_safe(self, janitor):
        _write_lines(janitor.active_task_file, 100)
        _, _, status = janitor.check_hot_memory_status()
        assert status == "SAFE"

    def test_at_soft_limit_is_warning(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_SOFT_LIMIT)
        count, _, status = janitor.check_hot_memory_status()
        assert status == "WARNING"
        assert count == MemoryJanitor.HOT_MEMORY_SOFT_LIMIT

    def test_at_hard_limit_is_critical(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_HARD_LIMIT)
        _, _, status = janitor.check_hot_memory_status()
        assert status == "CRITICAL"

    def test_between_hard_and_critical_is_critical(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_HARD_LIMIT + 10)
        _, _, status = janitor.check_hot_memory_status()
        assert status == "CRITICAL"

    def test_at_emergency_limit_is_emergency(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_CRITICAL)
        _, _, status = janitor.check_hot_memory_status()
        assert status == "EMERGENCY"

    def test_above_emergency_is_emergency(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_CRITICAL + 50)
        _, _, status = janitor.check_hot_memory_status()
        assert status == "EMERGENCY"

    def test_just_below_soft_limit_is_safe(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_SOFT_LIMIT - 1)
        _, _, status = janitor.check_hot_memory_status()
        assert status == "SAFE"


# ── B. generate_warning_message ───────────────────────────────────────────

class TestGenerateWarningMessage:
    def test_safe_returns_empty(self, janitor):
        assert janitor.generate_warning_message(50, 50, "SAFE") == ""

    def test_warning_message_contains_line_count(self, janitor):
        msg = janitor.generate_warning_message(185, 185, "WARNING")
        assert "185" in msg
        assert msg  # non-empty

    def test_critical_message_contains_line_count(self, janitor):
        msg = janitor.generate_warning_message(210, 210, "CRITICAL")
        assert "210" in msg

    def test_emergency_message_contains_line_count(self, janitor):
        msg = janitor.generate_warning_message(260, 260, "EMERGENCY")
        assert "260" in msg

    def test_unknown_status_returns_empty(self, janitor):
        assert janitor.generate_warning_message(50, 50, "UNKNOWN") == ""


# ── C. analyze_archivable_content ─────────────────────────────────────────

class TestAnalyzeArchivableContent:
    def test_missing_file_returns_empty_dicts(self, janitor):
        result = janitor.analyze_archivable_content()
        assert result["completed_tasks"] == []
        assert result["obsolete_decisions"] == []
        assert result["archived_references"] == []

    def test_detects_strikethrough_obsolete(self, janitor):
        janitor.active_task_file.write_text(
            "Some content\n~~deprecated thing~~\nMore content\n",
            encoding="utf-8",
        )
        result = janitor.analyze_archivable_content()
        assert any("deprecated thing" in d for d in result["obsolete_decisions"])

    def test_detects_superseded_decisions(self, janitor):
        janitor.active_task_file.write_text(
            "Decision A (Superseded by ADR-0002)\n",
            encoding="utf-8",
        )
        result = janitor.analyze_archivable_content()
        assert any("Superseded" in d for d in result["obsolete_decisions"])

    def test_detects_adr_references(self, janitor):
        janitor.active_task_file.write_text(
            "See ADR-0001 and ADR-0042 for details.\n",
            encoding="utf-8",
        )
        result = janitor.analyze_archivable_content()
        assert "ADR-0001" in result["archived_references"]
        assert "ADR-0042" in result["archived_references"]

    def test_adr_references_deduplicated(self, janitor):
        janitor.active_task_file.write_text(
            "ADR-0001 mentioned twice. Also ADR-0001 again.\n",
            encoding="utf-8",
        )
        result = janitor.analyze_archivable_content()
        assert result["archived_references"].count("ADR-0001") == 1

    def test_no_special_content_returns_empty_lists(self, janitor):
        janitor.active_task_file.write_text(
            "# Normal content\n\nJust regular text.\n",
            encoding="utf-8",
        )
        result = janitor.analyze_archivable_content()
        assert result["archived_references"] == []
        assert result["obsolete_decisions"] == []


# ── D. execute_cleanup ────────────────────────────────────────────────────

class TestExecuteCleanup:
    def test_dry_run_does_not_modify_files(self, janitor):
        original = "line 1\nline 2\nline 3\n"
        janitor.active_task_file.write_text(original, encoding="utf-8")
        janitor.execute_cleanup(dry_run=True)
        assert janitor.active_task_file.read_text(encoding="utf-8") == original

    def test_dry_run_no_archive_created(self, janitor):
        _write_lines(janitor.active_task_file, 50)
        janitor.execute_cleanup(dry_run=True)
        archives = list(janitor.archive_dir.glob("active_task_*.md"))
        assert len(archives) == 0

    def test_missing_file_returns_message(self, janitor):
        result = janitor.execute_cleanup(dry_run=False)
        assert "不存在" in result

    def test_real_run_creates_archive(self, janitor):
        _write_lines(janitor.active_task_file, 50)
        janitor.execute_cleanup(dry_run=False)
        archives = list(janitor.archive_dir.glob("active_task_*.md"))
        assert len(archives) == 1

    def test_archive_contains_full_original_content(self, janitor):
        content = "".join(f"line {i}\n" for i in range(1, 51))
        janitor.active_task_file.write_text(content, encoding="utf-8")
        janitor.execute_cleanup(dry_run=False)
        archive = list(janitor.archive_dir.glob("active_task_*.md"))[0]
        assert archive.read_text(encoding="utf-8") == content

    def test_original_file_truncated_after_cleanup(self, janitor):
        _write_lines(janitor.active_task_file, 50)
        original_lines = 50
        janitor.execute_cleanup(dry_run=False)
        new_lines = len(janitor.active_task_file.read_text(encoding="utf-8").splitlines())
        assert new_lines < original_lines

    def test_pointer_block_inserted_in_original(self, janitor):
        _write_lines(janitor.active_task_file, 30)
        janitor.execute_cleanup(dry_run=False)
        content = janitor.active_task_file.read_text(encoding="utf-8")
        assert "ARCHIVED" in content
        assert "archive/" in content

    def test_manifest_written_after_real_run(self, janitor):
        _write_lines(janitor.active_task_file, 30)
        janitor.execute_cleanup(dry_run=False)
        manifest_path = janitor.archive_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(manifest["archives"]) == 1

    def test_manifest_appends_on_second_run(self, janitor):
        _write_lines(janitor.active_task_file, 30)
        janitor.execute_cleanup(dry_run=False)
        _write_lines(janitor.active_task_file, 30)
        janitor.execute_cleanup(dry_run=False)
        manifest = json.loads(
            (janitor.archive_dir / "manifest.json").read_text(encoding="utf-8")
        )
        assert len(manifest["archives"]) == 2

    def test_manifest_entry_has_required_fields(self, janitor):
        _write_lines(janitor.active_task_file, 30)
        janitor.execute_cleanup(dry_run=False)
        manifest = json.loads(
            (janitor.archive_dir / "manifest.json").read_text(encoding="utf-8")
        )
        entry = manifest["archives"][0]
        for field in ("timestamp", "datetime", "archive_file", "original_lines", "new_lines", "reason"):
            assert field in entry, f"manifest entry missing field: {field}"

    def test_next_steps_preserved_after_cleanup(self, janitor):
        content = (
            "# Title\n"
            + "".join(f"line {i}\n" for i in range(1, 20))
            + "\n## Next Steps\n\n- Do something important\n- Continue the work\n"
        )
        janitor.active_task_file.write_text(content, encoding="utf-8")
        janitor.execute_cleanup(dry_run=False)
        result = janitor.active_task_file.read_text(encoding="utf-8")
        assert "Do something important" in result

    def test_no_duplicate_next_steps(self, janitor):
        content = (
            "# Title\n"
            + "".join(f"line {i}\n" for i in range(1, 20))
            + "\n## Next Steps\n\n- Action item\n"
        )
        janitor.active_task_file.write_text(content, encoding="utf-8")
        janitor.execute_cleanup(dry_run=False)
        result = janitor.active_task_file.read_text(encoding="utf-8")
        assert result.count("## Next Steps") == 1

    def test_cleanup_without_next_steps_section(self, janitor):
        content = "# Title\n" + "".join(f"line {i}\n" for i in range(1, 30))
        janitor.active_task_file.write_text(content, encoding="utf-8")
        result = janitor.execute_cleanup(dry_run=False)
        assert "✅" in result


# ── E. create_archive_plan ───────────────────────────────────────────────

class TestCreateArchivePlan:
    def test_returns_string(self, janitor):
        report = janitor.create_archive_plan()
        assert isinstance(report, str)

    def test_contains_status_line(self, janitor):
        _write_lines(janitor.active_task_file, 50)
        report = janitor.create_archive_plan()
        assert "SAFE" in report

    def test_safe_status_recommends_no_action(self, janitor):
        _write_lines(janitor.active_task_file, 50)
        report = janitor.create_archive_plan()
        assert "良好" in report or "無需掃除" in report

    def test_warning_status_in_report(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_SOFT_LIMIT)
        report = janitor.create_archive_plan()
        assert "WARNING" in report
        assert "建議" in report

    def test_critical_status_suggests_execute(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_HARD_LIMIT)
        report = janitor.create_archive_plan()
        assert "CRITICAL" in report
        assert "--execute" in report

    def test_emergency_status_urges_stop(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_CRITICAL)
        report = janitor.create_archive_plan()
        assert "EMERGENCY" in report
        assert "立即" in report

    def test_report_includes_adr_references(self, janitor):
        janitor.active_task_file.write_text(
            "See ADR-0001 for context.\n" * 5,
            encoding="utf-8",
        )
        report = janitor.create_archive_plan()
        assert "ADR-0001" in report

    def test_report_includes_obsolete_decisions(self, janitor):
        janitor.active_task_file.write_text(
            "~~old decision~~\n" * 5,
            encoding="utf-8",
        )
        report = janitor.create_archive_plan()
        assert "old decision" in report

    def test_missing_file_produces_safe_report(self, janitor):
        report = janitor.create_archive_plan()
        assert "SAFE" in report


# ── F. manifest round-trip ────────────────────────────────────────────────

class TestManifest:
    def test_load_manifest_missing_returns_empty(self, janitor):
        manifest = janitor._load_manifest()
        assert manifest["version"] == "1.0"
        assert manifest["archives"] == []

    def test_load_manifest_corrupted_returns_empty(self, janitor):
        (janitor.archive_dir / "manifest.json").write_text("NOT JSON", encoding="utf-8")
        manifest = janitor._load_manifest()
        assert manifest["archives"] == []

    def test_save_and_load_roundtrip(self, janitor):
        data = {"version": "1.0", "archives": [{"timestamp": "20260305_120000", "reason": "test"}]}
        janitor._save_manifest(data)
        loaded = janitor._load_manifest()
        assert loaded == data

    def test_save_creates_manifest_file(self, janitor):
        janitor._save_manifest({"version": "1.0", "archives": []})
        assert (janitor.archive_dir / "manifest.json").exists()

    def test_manifest_is_valid_json(self, janitor):
        _write_lines(janitor.active_task_file, 10)
        janitor.execute_cleanup(dry_run=False)
        raw = (janitor.archive_dir / "manifest.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)  # must not raise
        assert isinstance(parsed, dict)
