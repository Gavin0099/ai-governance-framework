import json
import os
import shutil
import subprocess
import sys
from datetime import date as _date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.dispatcher import dispatch_event
from runtime_hooks.dispatcher import format_human_envelope


@pytest.fixture
def local_dispatch_root():
    path = Path("tests") / "_tmp_dispatcher"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_dispatch_pre_task_event(local_dispatch_root, monkeypatch):
    import runtime_hooks.dispatcher as dispatcher

    monkeypatch.setattr(
        dispatcher,
        "run_pre_task_check",
        lambda **kwargs: {"ok": True, "warnings": [], "errors": [], "runtime_contract": {"rules": ["common"]}},
    )
    event = {
        "event_type": "pre_task",
        "project_root": str(local_dispatch_root),
        "rules": ["common"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
    }
    envelope = dispatch_event(event)
    assert envelope["event_type"] == "pre_task"
    assert envelope["result"]["ok"] is True


def test_dispatch_session_start_event(local_dispatch_root, monkeypatch):
    import runtime_hooks.dispatcher as dispatcher

    monkeypatch.setattr(
        dispatcher,
        "build_session_start_context",
        lambda **kwargs: {
            "ok": True,
            "runtime_contract": {"rules": ["common"], "risk": "medium", "oversight": "review-required", "memory_mode": "candidate"},
            "suggested_rules_preview": ["common", "refactor"],
            "suggested_skills": ["code-style", "governance-runtime"],
            "suggested_agent": "advanced-agent",
            "pre_task_check": {"warnings": [], "errors": []},
        },
    )
    plan = local_dispatch_root / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor service boundary\n",
        encoding="utf-8",
    )
    before_file = local_dispatch_root / "application" / "before.cs"
    after_file = local_dispatch_root / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )
    event = {
        "event_type": "session_start",
        "project_root": str(local_dispatch_root),
        "plan_path": str(plan),
        "task": "Refactor service boundary",
        "rules": ["common"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "impact_before_files": [str(before_file)],
        "impact_after_files": [str(after_file)],
    }
    envelope = dispatch_event(event)
    assert envelope["event_type"] == "session_start"
    assert envelope["result"]["ok"] is True
    assert envelope["result"]["suggested_rules_preview"] == ["common", "refactor"]


def test_dispatch_session_start_event_can_use_explicit_contract():
    event = {
        "event_type": "session_start",
        "project_root": ".",
        "plan_path": "PLAN.md",
        "task": "Inspect firmware contract path",
        "rules": ["common"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "contract": str(Path("examples/usb-hub-contract/contract.yaml").resolve()),
    }
    envelope = dispatch_event(event)
    assert envelope["result"]["ok"] is True
    assert envelope["result"]["contract_resolution"]["source"] == "explicit"
    assert envelope["result"]["domain_contract"]["name"] == "usb-hub-firmware-contract"


def test_dispatch_post_task_event(local_dispatch_root):
    response = local_dispatch_root / "response.txt"
    response.write_text(
        "[Governance Contract]\n"
        "LANG = C++\nLEVEL = L2\nSCOPE = feature\nPLAN = PLAN.md\n"
        "LOADED = SYSTEM_PROMPT, HUMAN-OVERSIGHT\n"
        "CONTEXT = repo -> runtime-governance; NOT: platform rewrite\n"
        "PRESSURE = SAFE (20/200)\nRULES = common,python\nRISK = medium\n"
        "OVERSIGHT = review-required\nMEMORY_MODE = candidate\n",
        encoding="utf-8",
    )
    event = {
        "event_type": "post_task",
        "project_root": str(local_dispatch_root),
        "task": "Capture final output",
        "rules": ["common", "python"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "response_file": str(response),
        "create_snapshot": True,
        "snapshot_summary": "Candidate memory from dispatcher",
    }
    envelope = dispatch_event(event)
    assert envelope["event_type"] == "post_task"
    assert envelope["result"]["ok"] is True
    assert envelope["result"]["snapshot"] is not None


def test_dispatcher_human_output_surfaces_contract_context():
    envelope = dispatch_event(
        {
            "event_type": "session_start",
            "project_root": ".",
            "plan_path": "PLAN.md",
            "task": "Inspect firmware contract path",
            "rules": ["common"],
            "risk": "medium",
            "oversight": "review-required",
            "memory_mode": "candidate",
            "contract": str(Path("examples/usb-hub-contract/contract.yaml").resolve()),
        }
    )
    output = format_human_envelope(envelope)
    assert "event_type=session_start" in output
    assert "contract_source=explicit" in output
    assert "domain_contract=usb-hub-firmware-contract" in output


def test_dispatcher_cli_can_apply_contract_override():
    result = subprocess.run(
        [
            sys.executable,
            "runtime_hooks/dispatcher.py",
            "--file",
            "runtime_hooks/examples/shared/session_start.shared.json",
            "--contract",
            str(Path("examples/usb-hub-contract/contract.yaml").resolve()),
            "--format",
            "human",
        ],
        cwd=Path(__file__).parent.parent,
        text=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        check=True,
    )
    assert "contract_source=explicit" in result.stdout
    assert "domain_contract=usb-hub-firmware-contract" in result.stdout


def test_dispatcher_cli_can_infer_project_root_and_plan_from_contract(tmp_path):
    contract_file = tmp_path / "contract.yaml"
    plan_path = tmp_path / "PLAN.md"
    governance_dir = tmp_path / ".governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    (governance_dir / "version_manifest.yaml").write_text(
        'schema_version: "1.0"\nlast_updated: "2026-05-03"\ngovernance_version: "0.4.0"\n'
        'contract_schema_version: "1.2.0"\nruntime_entrypoint_version: "1.1.0"\n'
        'hook_wiring_version: "1.0.0"\nartifact_layout_version: "1.0.0"\nmemory_layout_version: "1.0.0"\n',
        encoding="utf-8",
    )
    contract_file.write_text("name: local-contract\n", encoding="utf-8")
    plan_path.write_text(
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Validate dispatcher overrides\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "runtime_hooks/dispatcher.py",
            "--file",
            "runtime_hooks/examples/shared/session_start.shared.json",
            "--contract",
            str(contract_file.resolve()),
            "--format",
            "json",
        ],
        cwd=Path(__file__).parent.parent,
        text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True, stdin=subprocess.DEVNULL,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["result"]["project_root"] == str(tmp_path.resolve())
    assert payload["result"]["contract_resolution"]["source"] == "explicit"


def test_dispatcher_cli_can_apply_post_task_response_and_checks_overrides(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "runtime_hooks/dispatcher.py",
            "--file",
            "runtime_hooks/examples/shared/post_task.shared.json",
            "--project-root",
            str(tmp_path.resolve()),
            "--contract",
            str(Path("examples/usb-hub-contract/contract.yaml").resolve()),
            "--response-file",
            str(Path("examples/usb-hub-contract/fixtures/post_task_response.txt").resolve()),
            "--checks-file",
            str(Path("examples/usb-hub-contract/fixtures/interrupt_regression.checks.json").resolve()),
            "--format",
            "json",
        ],
        cwd=Path(__file__).parent.parent,
        text=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["result"]["contract_resolution"]["source"] == "explicit"
    assert any("interrupt_safety_validator" in warning for warning in payload["result"]["warnings"])
    assert payload["result"]["domain_validator_results"][0]["name"] == "interrupt_safety_validator"
    assert "HUB-ISR-001" in payload["result"]["domain_validator_results"][0]["warnings"][0]


def test_native_example_files_exist():
    example_paths = [
        Path("runtime_hooks/examples/claude_code/pre_task.native.json"),
        Path("runtime_hooks/examples/claude_code/post_task.native.json"),
        Path("runtime_hooks/examples/codex/pre_task.native.json"),
        Path("runtime_hooks/examples/codex/post_task.native.json"),
        Path("runtime_hooks/examples/gemini/pre_task.native.json"),
        Path("runtime_hooks/examples/gemini/post_task.native.json"),
        Path("runtime_hooks/examples/shared/pre_task.shared.json"),
        Path("runtime_hooks/examples/shared/post_task.shared.json"),
        Path("runtime_hooks/examples/shared/session_start.shared.json"),
        Path("runtime_hooks/examples/shared/ai_response.txt"),
    ]
    for path in example_paths:
        assert path.exists(), f"missing example payload: {path}"
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
