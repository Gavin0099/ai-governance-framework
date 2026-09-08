"""
Unit tests for governance_tools/memory_janitor.py
Coverage target: ≥ 70%

Test groups:
  A. check_hot_memory_status   — threshold boundary + missing file
  B. generate_warning_message  — all status codes
  C. analyze_archivable_content— regex heuristics + missing file
  D. execute_cleanup           — fail-closed containment / no-write guarantees
  E. manifest                  — _load_manifest / _save_manifest round-trip
"""

import json
import sys
import os
from pathlib import Path

import pytest

# Make governance_tools importable without installation
sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.memory_janitor import MemoryJanitor, UnsafeCleanupBlocked, main


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


def _current_like_active_task() -> str:
    """Build a 159-line, character-threshold CRITICAL active-task projection."""
    lines = [f"state line {i:03d} " + ("x" * 56) for i in range(1, 160)]
    lines[0] = "# Active Task"
    lines[83] = "## Next Steps"
    lines[84] = "- Preserve the retained next step while newer state follows."
    lines[94] = "## Open Risks"
    lines[95] = "- Current risk must not disappear during memory maintenance."
    lines[110] = "## Claim Ceiling"
    lines[111] = "- Cleanup is not Gate 3 validity evidence."
    lines[152] = "## Rev9 STOP"
    lines[158] = "- Latest committed Gate 3 authority remains binding."
    content = "\n".join(lines) + "\n"
    assert len(content.splitlines()) == 159
    assert 10_000 <= len(content) < 12_000
    return content


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

    def test_current_like_projection_is_critical_by_character_count(self, janitor):
        janitor.active_task_file.write_text(_current_like_active_task(), encoding="utf-8")
        line_count, char_count, status = janitor.check_hot_memory_status()
        assert line_count == 159
        assert 10_000 <= char_count < 12_000
        assert status == "CRITICAL"


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

    @pytest.mark.parametrize("status", ["CRITICAL", "EMERGENCY"])
    def test_high_pressure_guidance_requires_verified_cutover(self, janitor, status):
        msg = janitor.generate_warning_message(260, 12_500, status)
        assert "archive + replacement-state cutover" in msg
        for unsafe_guidance in ("--clean", "--execute", "execute_cleanup_now", "強制執行掃除"):
            assert unsafe_guidance not in msg

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
    def test_dry_run_reports_blocked_without_writes(self, janitor):
        original = _current_like_active_task().encode("utf-8")
        janitor.active_task_file.write_bytes(original)

        result = janitor.execute_cleanup(dry_run=True)

        assert result.startswith("[BLOCKED]")
        assert "verified archive" in result
        assert "replacement-state cutover" in result
        assert "截短" not in result
        assert janitor.active_task_file.read_bytes() == original
        assert not janitor.archive_dir.exists()

    def test_missing_file_returns_message_without_creating_archive(self, janitor):
        result = janitor.execute_cleanup(dry_run=False)
        assert "不存在" in result
        assert not janitor.archive_dir.exists()

    def test_real_cleanup_fails_closed_and_preserves_exact_bytes(self, janitor):
        original = _current_like_active_task().encode("utf-8")
        janitor.active_task_file.write_bytes(original)

        with pytest.raises(UnsafeCleanupBlocked, match="verified archive"):
            janitor.execute_cleanup(dry_run=False)

        assert janitor.active_task_file.read_bytes() == original
        assert not janitor.archive_dir.exists()

    def test_discard_region_sections_remain_after_refusal(self, janitor):
        original = _current_like_active_task()
        janitor.active_task_file.write_text(original, encoding="utf-8")

        with pytest.raises(UnsafeCleanupBlocked):
            janitor.execute_cleanup(dry_run=False)

        retained = janitor.active_task_file.read_text(encoding="utf-8")
        assert "## Open Risks" in retained
        assert "## Claim Ceiling" in retained
        assert "## Rev9 STOP" in retained
        assert "Latest committed Gate 3 authority" in retained

    def test_cleanup_without_next_steps_also_fails_closed(self, janitor):
        original = ("# Title\n" + "".join(f"line {i}\n" for i in range(1, 30))).encode("utf-8")
        janitor.active_task_file.write_bytes(original)

        with pytest.raises(UnsafeCleanupBlocked):
            janitor.execute_cleanup(dry_run=False)

        assert janitor.active_task_file.read_bytes() == original
        assert not janitor.archive_dir.exists()

    @pytest.mark.parametrize("legacy_flag", ["--execute", "--clean"])
    def test_cli_cleanup_flags_exit_nonzero_without_writes(
        self, mem_root, legacy_flag, monkeypatch, capsys
    ):
        active = mem_root / "01_active_task.md"
        original = _current_like_active_task().encode("utf-8")
        active.write_bytes(original)
        monkeypatch.setattr(
            sys,
            "argv",
            ["memory_janitor.py", "--memory-root", str(mem_root), legacy_flag],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "verified archive" in captured.err
        assert "replacement-state cutover" in captured.err
        assert active.read_bytes() == original
        assert not (mem_root / "archive").exists()

    @pytest.mark.parametrize(
        "mixed_flags",
        [
            ["--clean", "--check"],
            ["--execute", "--plan"],
            ["--clean", "--manifest"],
        ],
    )
    def test_cleanup_intent_cannot_bypass_refusal_with_other_actions(
        self, mem_root, mixed_flags, monkeypatch, capsys
    ):
        active = mem_root / "01_active_task.md"
        original = _current_like_active_task().encode("utf-8")
        active.write_bytes(original)
        monkeypatch.setattr(
            sys,
            "argv",
            ["memory_janitor.py", "--memory-root", str(mem_root), *mixed_flags],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "verified archive" in captured.err
        assert "replacement-state cutover" in captured.err
        assert active.read_bytes() == original
        assert not (mem_root / "archive").exists()


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
        assert "verified archive + replacement-state cutover" in report
        assert "--execute" not in report
        assert "--clean" not in report

    def test_critical_status_requires_verified_cutover(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_HARD_LIMIT)
        report = janitor.create_archive_plan()
        assert "CRITICAL" in report
        assert "archive + replacement-state cutover" in report
        assert "--execute" not in report
        assert "--clean" not in report

    def test_emergency_status_urges_stop_without_destructive_guidance(self, janitor):
        _write_lines(janitor.active_task_file, MemoryJanitor.HOT_MEMORY_CRITICAL)
        report = janitor.create_archive_plan()
        assert "EMERGENCY" in report
        assert "停止增加 active memory" in report
        assert "archive + replacement-state cutover" in report
        assert "--execute" not in report
        assert "--clean" not in report

    @pytest.mark.parametrize(
        ("line_count", "expected_recommendation"),
        [
            (MemoryJanitor.HOT_MEMORY_HARD_LIMIT, "verified_archive_and_replacement_state_cutover_required"),
            (MemoryJanitor.HOT_MEMORY_CRITICAL, "verified_archive_and_replacement_state_cutover_required"),
        ],
    )
    def test_json_plan_never_recommends_destructive_cleanup(
        self, mem_root, line_count, expected_recommendation, monkeypatch, capsys
    ):
        _write_lines(mem_root / "01_active_task.md", line_count)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "memory_janitor.py",
                "--memory-root",
                str(mem_root),
                "--plan",
                "--format",
                "json",
            ],
        )

        main()

        payload = json.loads(capsys.readouterr().out)
        assert payload["recommendation"] == expected_recommendation
        serialized = json.dumps(payload)
        for unsafe_guidance in ("--clean", "--execute", "execute_cleanup_now"):
            assert unsafe_guidance not in serialized

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
        janitor.archive_dir.mkdir(parents=True)
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
        janitor._save_manifest({"version": "1.0", "archives": []})
        raw = (janitor.archive_dir / "manifest.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)  # must not raise
        assert isinstance(parsed, dict)
