from pathlib import Path

from memory_pipeline.memory_layout import MEMORY_FILE_ALIASES, resolve_memory_file


def test_current_memory_layout_accepts_02_workflow_for_tech_stack(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    workflow = memory_root / "02_workflow.md"
    workflow.write_text("# Workflow\n", encoding="utf-8")

    assert "02_workflow.md" in MEMORY_FILE_ALIASES["tech_stack"]
    assert resolve_memory_file(memory_root, "tech_stack") == workflow
