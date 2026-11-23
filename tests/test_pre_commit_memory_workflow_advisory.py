from __future__ import annotations

from pathlib import Path


HOOK = Path("scripts/hooks/pre-commit")


def test_pre_commit_exposes_memory_workflow_advisory() -> None:
    text = HOOK.read_text(encoding="utf-8")
    runner_start = text.index("run_python_advisory() {")
    runner_end = text.index("# Advisory-only memory workflow dispatch.", runner_start)
    runner = text[runner_start:runner_end]

    assert 'MEMORY_WORKFLOW_TOOL="$FRAMEWORK_ROOT/governance_tools/memory_workflow.py"' in text
    assert '--repo "$TARGET_REPO_ROOT" --check --run-guard --format json' in text
    assert 'FRAMEWORK_PYTHON_ROOT="$FRAMEWORK_ROOT"' in text
    # The command-scoped assignment preserves the caller's PYTHONPATH; the
    # installed-hook test checks unset, empty and inherited environments.
    assert (
        'PYTHONPATH="$FRAMEWORK_PYTHON_ROOT${PYTHONPATH:+:$PYTHONPATH}" '
        '"${PYTHON_CMD[@]}" -c'
    ) in runner
    assert "MEMORY_WORKFLOW_GUARD_RAN=" in text
    assert "MEMORY_WORKFLOW_WARNINGS=" in text
    assert "memory workflow advisory: memory/** changes detected" in text
    assert "memory workflow advisory: report-only warnings detected" in text
    assert "warning_codes=$MEMORY_WORKFLOW_WARNINGS" in text
    assert "guard_status=not_run_in_pre_commit_advisory" in text
    assert "completion_claim_allowed=not_evaluated_without_guard" in text
    assert "run the command above before claiming memory completion" in text


def test_pre_commit_memory_workflow_is_not_selective_blocking() -> None:
    text = HOOK.read_text(encoding="utf-8")
    block_start = text.index("# Advisory-only memory workflow dispatch.")
    block_end = text.index("# ── 跳過條件", block_start)
    advisory_block = text[block_start:block_end]

    # Inspect complete shell commands, including backslash continuations.
    invocation_lines = [
        line for line in advisory_block.replace("\\\n", "").splitlines()
        if "MEMORY_WORKFLOW_RESULT=" in line
    ]
    assert invocation_lines
    assert all('run_python_advisory "memory workflow"' in line for line in invocation_lines)
    assert all('"$MEMORY_WORKFLOW_TOOL"' in line for line in invocation_lines)
    assert all("--run-guard" in line for line in invocation_lines)
    assert all("--fail-on-blocker" not in line for line in invocation_lines)
    assert all("|| true" in line for line in invocation_lines)
    assert "completion_claim_allowed=not_evaluated_without_guard" in advisory_block
    assert "warning_codes=$MEMORY_WORKFLOW_WARNINGS" in advisory_block
    assert "pre-commit advisory only; commit is not blocked" in advisory_block


def test_pre_commit_exposes_protected_baseline_refresh_advisory() -> None:
    text = HOOK.read_text(encoding="utf-8")

    assert "protected baseline refresh advisory" in text
    assert "overridable\\." in text
    assert "adopt_governance.py --target . --refresh" in text
    assert "pre-commit advisory only; commit is not blocked by this check" in text
