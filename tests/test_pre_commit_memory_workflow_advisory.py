from __future__ import annotations

from pathlib import Path


HOOK = Path("scripts/hooks/pre-commit")


def test_pre_commit_exposes_memory_workflow_advisory() -> None:
    text = HOOK.read_text(encoding="utf-8")

    assert 'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"' in text
    assert '--repo "$TARGET_REPO_ROOT" --check --format json' in text
    assert "memory workflow advisory: memory/** changes detected" in text


def test_pre_commit_memory_workflow_is_not_selective_blocking() -> None:
    text = HOOK.read_text(encoding="utf-8")
    block_start = text.index("# Advisory-only memory workflow dispatch.")
    block_end = text.index("# ── 跳過條件", block_start)
    advisory_block = text[block_start:block_end]

    invocation_lines = [
        line for line in advisory_block.splitlines()
        if "MEMORY_WORKFLOW_RESULT=" in line
    ]
    assert invocation_lines
    assert all("--fail-on-blocker" not in line for line in invocation_lines)
    assert "pre-commit advisory only; commit is not blocked" in advisory_block
