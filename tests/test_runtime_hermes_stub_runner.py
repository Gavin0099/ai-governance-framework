from __future__ import annotations

from datetime import date as _date
from pathlib import Path

import pytest

from runtime_hooks.adapters.hermes.normalize_event import normalize_event
from runtime_hooks.adapters.shared_adapter_runner import run_adapter_event
from runtime_hooks.examples.hermes.stub_runner import (
    make_stub_tool_call,
    parse_tool_call,
    run_stub_task,
)


def _write_minimal_project(root: Path) -> None:
    (root / "PLAN.md").write_text(
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: runtime-smoke\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase 1 : Hermes stub runner smoke\n",
        encoding="utf-8",
    )


def test_stub_tool_call_parser_accepts_deterministic_tool_call() -> None:
    parsed = parse_tool_call(make_stub_tool_call("demo task"))

    assert parsed["name"] == "write_governed_response"
    assert "demo task" in parsed["arguments"]["summary"]


def test_stub_tool_call_parser_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError, match="unsupported stub tool"):
        parse_tool_call('<tool_call>{"name":"edit_file","arguments":{}}</tool_call>')


def test_hermes_stub_runner_produces_response_file_and_passes_adapter_pipeline(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)

    result = run_stub_task(project_root=tmp_path, output_dir=tmp_path / "out", task="stub smoke")

    response_file = Path(result["tool_result"]["response_file"])
    assert response_file.exists()
    assert "[Governance Contract]" in response_file.read_text(encoding="utf-8")
    assert result["pre_task"]["result"]["ok"] is True
    assert result["post_task"]["result"]["ok"] is True
    assert result["post_task"]["normalized_event"]["metadata"]["harness"] == "hermes"
    assert result["post_task"]["normalized_event"]["response_file"] == str(response_file)
    assert result["post_task"]["result"]["adapter_contract"]["compliant"] is True
    assert result["claim_class"] == "accepted-input-stub-smoke"
    assert "verified external Hermes runtime integration" in result["not_claimed"]


def test_hermes_post_task_without_response_file_is_rejected(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)
    payload = {
        "workspace": str(tmp_path),
        "task": "no artifact",
        "rules": ["common"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "event_name": "post_task",
        "run_id": "hermes-neg-01",
    }

    envelope = run_adapter_event(normalize_event, event_type="post_task", payload=payload)

    assert envelope["result"]["ok"] is False
    assert envelope["result"]["adapter_contract"]["required"] is True
    assert envelope["result"]["adapter_contract"]["compliant"] is False
