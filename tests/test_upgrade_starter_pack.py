import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.upgrade_starter_pack import format_human_result, upgrade_repo


def _make_local_tmp(name: str) -> Path:
    path = Path("tests") / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_upgrade_starter_pack_seeds_missing_files():
    repo = _make_local_tmp("_tmp_upgrade_starter_pack_seed")
    try:
        result = upgrade_repo(repo, framework_root=Path("."), dry_run=False, refresh_managed=False)

        assert result["ok"] is True
        assert (repo / "SYSTEM_PROMPT.md").exists()
        assert (repo / "CLAUDE.md").exists()
        assert (repo / "GEMINI.md").exists()
        assert (repo / ".github" / "copilot-instructions.md").exists()
        assert (repo / "memory" / "01_active_task.md").exists()
        assert (repo / "memory_janitor.py").exists()
        assert (repo / "PLAN.md").exists()
        statuses = {item["target"]: item["status"] for item in result["files"]}
        assert statuses["SYSTEM_PROMPT.md"] == "seeded"
        assert statuses["PLAN.md"] == "seeded"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_upgrade_starter_pack_does_not_overwrite_existing_plan():
    repo = _make_local_tmp("_tmp_upgrade_starter_pack_plan")
    try:
        (repo / "PLAN.md").write_text("# custom plan\n", encoding="utf-8")

        result = upgrade_repo(repo, framework_root=Path("."), dry_run=False, refresh_managed=False)

        assert (repo / "PLAN.md").read_text(encoding="utf-8") == "# custom plan\n"
        statuses = {item["target"]: item["status"] for item in result["files"]}
        assert statuses["PLAN.md"] == "skipped_existing_plan"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_upgrade_starter_pack_can_refresh_managed_files():
    repo = _make_local_tmp("_tmp_upgrade_starter_pack_refresh")
    try:
        (repo / "SYSTEM_PROMPT.md").write_text("old prompt\n", encoding="utf-8")
        (repo / "CLAUDE.md").write_text("old claude\n", encoding="utf-8")

        result = upgrade_repo(repo, framework_root=Path("."), dry_run=False, refresh_managed=True)

        system_prompt = (repo / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
        claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Governance Agent" in system_prompt
        assert "Claude Code" in claude
        statuses = {item["target"]: item["status"] for item in result["files"]}
        assert statuses["SYSTEM_PROMPT.md"] == "refreshed"
        assert statuses["CLAUDE.md"] == "refreshed"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_upgrade_starter_pack_human_output_surfaces_plan_boundary():
    repo = _make_local_tmp("_tmp_upgrade_starter_pack_human")
    try:
        (repo / "PLAN.md").write_text("# existing plan\n", encoding="utf-8")
        result = upgrade_repo(repo, framework_root=Path("."), dry_run=True, refresh_managed=True)
        output = format_human_result(result)

        assert "[upgrade_starter_pack]" in output
        assert "refresh_managed=True" in output
        assert "file[PLAN.md]=skipped_existing_plan" in output
    finally:
        shutil.rmtree(repo, ignore_errors=True)
