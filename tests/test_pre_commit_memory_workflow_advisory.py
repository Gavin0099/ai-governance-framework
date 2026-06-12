from __future__ import annotations

from pathlib import Path


HOOK = Path("scripts/hooks/pre-commit")


def test_pre_commit_exposes_memory_workflow_advisory() -> None:
    text = HOOK.read_text(encoding="utf-8")

    assert 'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"' in text
    assert '--repo "$TARGET_REPO_ROOT" --check --format json' in text
    assert "MEMORY_WORKFLOW_GUARD_RAN=" in text
    assert "memory workflow advisory: memory/** changes detected" in text
    assert "guard_status=not_run_in_pre_commit_advisory" in text
    assert "completion_claim_allowed=not_evaluated_without_guard" in text
    assert "run the command above before claiming memory completion" in text


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
    assert "completion_claim_allowed=not_evaluated_without_guard" in advisory_block
    assert "pre-commit advisory only; commit is not blocked" in advisory_block


def test_pre_commit_exposes_protected_baseline_refresh_advisory() -> None:
    text = HOOK.read_text(encoding="utf-8")

    assert "protected baseline refresh advisory" in text
    assert "overridable\\." in text
    assert "adopt_governance.py --target . --refresh" in text
    assert "pre-commit advisory only; commit is not blocked by this check" in text
