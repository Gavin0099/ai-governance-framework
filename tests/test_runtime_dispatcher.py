import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.dispatcher import dispatch_event


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
