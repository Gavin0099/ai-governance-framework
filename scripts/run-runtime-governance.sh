#!/usr/bin/env bash
# Shared runtime-governance enforcement entrypoint for local hooks and CI.

set -euo pipefail

MODE="enforce"
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --pytest-arg)
            PYTEST_ARGS+=("$2")
            shift 2
            ;;
        *)
            echo "Usage: bash scripts/run-runtime-governance.sh [--mode enforce|smoke|ci] [--pytest-arg ARG]"
            exit 1
            ;;
    esac
done

if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
    echo "[runtime-governance] python is required"
    exit 1
fi

PYTHON_CMD="python"
command -v python >/dev/null 2>&1 || PYTHON_CMD="python3"

run_smoke() {
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness claude_code --event-type session_start --output artifacts/runtime/smoke/claude_session_start.txt --json-output artifacts/runtime/smoke/claude_session_start.json
    "$PYTHON_CMD" governance_tools/change_control_summary.py --session-start-file artifacts/runtime/smoke/claude_session_start.json --output artifacts/runtime/smoke/claude_change_control_summary.txt
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness claude_code --event-type pre_task
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness claude_code --event-type post_task
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness codex --event-type session_start --output artifacts/runtime/smoke/codex_session_start.txt --json-output artifacts/runtime/smoke/codex_session_start.json
    "$PYTHON_CMD" governance_tools/change_control_summary.py --session-start-file artifacts/runtime/smoke/codex_session_start.json --output artifacts/runtime/smoke/codex_change_control_summary.txt
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness codex --event-type post_task
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness gemini --event-type session_start --output artifacts/runtime/smoke/gemini_session_start.txt --json-output artifacts/runtime/smoke/gemini_session_start.json
    "$PYTHON_CMD" governance_tools/change_control_summary.py --session-start-file artifacts/runtime/smoke/gemini_session_start.json --output artifacts/runtime/smoke/gemini_change_control_summary.txt
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --harness gemini --event-type post_task
    "$PYTHON_CMD" runtime_hooks/smoke_test.py --event-type session_start --output artifacts/runtime/smoke/shared_session_start.txt --json-output artifacts/runtime/smoke/shared_session_start.json
    "$PYTHON_CMD" governance_tools/change_control_summary.py --session-start-file artifacts/runtime/smoke/shared_session_start.json --output artifacts/runtime/smoke/shared_change_control_summary.txt
}

run_pytest_suite() {
    if ! "$PYTHON_CMD" -c "import pytest" >/dev/null 2>&1; then
        echo "[runtime-governance] pytest is required for mode=$MODE"
        echo "[runtime-governance] install it with: pip install pytest"
        exit 1
    fi

    "$PYTHON_CMD" -m pytest \
        tests/test_runtime_smoke_test.py \
        tests/test_runtime_dispatcher.py \
        tests/test_runtime_pre_task_check.py \
        tests/test_runtime_post_task_check.py \
        tests/test_runtime_session_end.py \
        tests/test_memory_curator.py \
        tests/test_rule_pack_loader.py \
        tests/test_state_generator.py \
        tests/test_test_result_ingestor.py \
        tests/test_architecture_drift_checker.py \
        --basetemp .pytest_tmp_runtime \
        "${PYTEST_ARGS[@]}"
}

case "$MODE" in
    smoke)
        echo "[runtime-governance] mode=smoke"
        run_smoke
        ;;
    ci)
        echo "[runtime-governance] mode=ci"
        run_smoke
        run_pytest_suite
        ;;
    enforce)
        echo "[runtime-governance] mode=enforce"
        run_smoke
        run_pytest_suite
        ;;
    *)
        echo "Unsupported mode: $MODE"
        exit 1
        ;;
esac

echo "[runtime-governance] complete"
