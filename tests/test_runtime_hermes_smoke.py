from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from runtime_hooks.examples.hermes.stub_runner import (
    execute_stub_tool,
    make_stub_tool_call,
    parse_tool_call,
)
from runtime_hooks.smoke_test import DEFAULT_EXAMPLES, NORMALIZERS, run_smoke


REPO_ROOT = Path(__file__).resolve().parents[1]
HERMES_EXAMPLES = REPO_ROOT / "runtime_hooks" / "examples" / "hermes"


def _write_minimal_project(root: Path) -> None:
    (root / "PLAN.md").write_text(
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: runtime-smoke\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase 1 : Hermes smoke registration\n",
        encoding="utf-8",
    )


def test_hermes_registered_in_standard_smoke() -> None:
    # Visibility: hermes is a first-class smoke harness with all three events.
    assert "hermes" in NORMALIZERS
    for event_type in ("session_start", "pre_task", "post_task"):
        assert ("hermes", event_type) in DEFAULT_EXAMPLES


def test_hermes_pre_task_smoke_ok(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)
    envelope = run_smoke("hermes", "pre_task", project_root=tmp_path)
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["metadata"]["harness"] == "hermes"


def test_hermes_post_task_smoke_ok(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)
    # post_task ok requires a contract-compliant response (must embed a
    # [Governance Contract] block); produce one via the stub's own writer.
    response_file = tmp_path / "response.txt"
    tool_call = parse_tool_call(make_stub_tool_call("post_task smoke"))
    execute_stub_tool(tool_call, response_file, task="post_task smoke")
    envelope = run_smoke("hermes", "post_task", project_root=tmp_path, response_file=response_file)
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["response_file"] == str(response_file)
    assert envelope["result"]["adapter_contract"]["compliant"] is True


def test_hermes_cron_artifact_post_task_smoke_ok(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)
    response_source = HERMES_EXAMPLES / "cron_output.5bf23ff.md"
    response_file = tmp_path / "hermes-cron-output.md"
    response_file.write_text(response_source.read_text(encoding="utf-8"), encoding="utf-8")

    envelope = run_smoke("hermes", "post_task", project_root=tmp_path, response_file=response_file)

    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["response_file"] == str(response_file)
    assert envelope["result"]["adapter_contract"]["compliant"] is True
    assert "source_type = cron_output_file" in response_file.read_text(encoding="utf-8")
