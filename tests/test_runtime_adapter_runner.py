import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.adapters.claude_code.normalize_event import normalize_event as normalize_claude
from runtime_hooks.adapters.shared_adapter_runner import run_adapter_event


@pytest.fixture
def local_runtime_root():
    path = Path("tests") / "_tmp_adapter_runner"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_run_adapter_event_pre_task(local_runtime_root, monkeypatch):
    plan = local_runtime_root / "PLAN.md"
    plan.write_text("> **Owner**: Tester\n> **Freshness**: Sprint (7d)\n", encoding="utf-8")

    import runtime_hooks.adapters.shared_adapter_runner as runner

    class FreshnessStub:
        status = "FRESH"
        days_since_update = 0
        threshold_days = 7

    monkeypatch.setattr(runner, "run_pre_task_check", lambda **kwargs: {"ok": True, "warnings": [], "errors": [], "runtime_contract": {"rules": ["common"]}})

    payload = {
        "cwd": str(local_runtime_root),
        "prompt": "Add runtime hooks",
        "active_rules": "common",
    }
    envelope = run_adapter_event(normalize_claude, "pre_task", payload)
    assert envelope["normalized_event"]["event_type"] == "pre_task"
    assert envelope["result"]["ok"] is True


def test_run_adapter_event_session_start(local_runtime_root):
    plan = local_runtime_root / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor service boundary\n",
        encoding="utf-8",
    )
    before_file = local_runtime_root / "application" / "before.cs"
    after_file = local_runtime_root / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    payload = {
        "cwd": str(local_runtime_root),
        "plan": str(plan),
        "prompt": "Refactor service boundary",
        "active_rules": "common",
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "impact_before": [str(before_file)],
        "impact_after": [str(after_file)],
    }
    envelope = run_adapter_event(normalize_claude, "session_start", payload)
    assert envelope["normalized_event"]["event_type"] == "session_start"
    assert envelope["result"]["suggested_agent"] == "advanced-agent"


def test_run_adapter_event_post_task_creates_snapshot(local_runtime_root):
    response_file = local_runtime_root / "response.txt"
    response_file.write_text(
        "[Governance Contract]\n"
        "LANG = C++\nLEVEL = L2\nSCOPE = feature\nPLAN = PLAN.md\n"
        "LOADED = SYSTEM_PROMPT, HUMAN-OVERSIGHT\n"
        "CONTEXT = repo -> runtime-governance; NOT: platform rewrite\n"
        "PRESSURE = SAFE (20/200)\nRULES = common,python\nRISK = medium\n"
        "OVERSIGHT = review-required\nMEMORY_MODE = candidate\n",
        encoding="utf-8",
    )
    payload = {
        "workspace": str(local_runtime_root),
        "task": "Review output",
        "rules": ["common", "python"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "output_file": str(response_file),
        "snapshot": True,
    }
    from runtime_hooks.adapters.codex.normalize_event import normalize_event as normalize_codex

    envelope = run_adapter_event(normalize_codex, "post_task", payload)
    assert envelope["result"]["ok"] is True
    assert envelope["result"]["snapshot"] is not None
    assert Path(envelope["result"]["snapshot"]["snapshot_path"]).exists()
