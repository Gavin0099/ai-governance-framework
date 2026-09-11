import json
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from runtime_hooks import smoke_test


FRAMEWORK = Path(__file__).resolve().parents[1]


def make_project(root, age=0):
    root.mkdir()
    (root / "PLAN.md").write_text(
        f"> **最後更新**: {(date.today() - timedelta(days=age)).isoformat()}\n"
        "> **Owner**: fixture\n> **Freshness**: Sprint (7d)\n"
        "[>] Phase 1 : Runtime fixture\n", encoding="utf-8",
    )
    shutil.copyfile(FRAMEWORK / "contract.yaml", root / "contract.yaml")
    (root / ".governance").mkdir()
    shutil.copyfile(FRAMEWORK / ".governance/version_manifest.yaml",
                    root / ".governance/version_manifest.yaml")
    return root


@pytest.mark.parametrize("harness,event", [(None, "session_start"),
                                         ("claude_code", "pre_task"),
                                         ("codex", "session_start")])
def test_default_smoke_isolates_stale_development_plan(tmp_path, monkeypatch, harness, event):
    development = make_project(tmp_path / "framework", age=22)
    shutil.copytree(FRAMEWORK / "runtime_hooks/examples", development / "runtime_hooks/examples")
    before = (development / "PLAN.md").read_bytes()
    monkeypatch.chdir(development)
    result = (smoke_test.run_shared_smoke(event) if harness is None
              else smoke_test.run_smoke(harness, event))["result"]
    check = result.get("pre_task_check", result)
    assert result["ok"] is True
    assert check["freshness"]["status"] == "FRESH"
    target = Path(check["plan_path"]).parent
    assert target != development
    assert target.name.startswith("ai-governance-self-smoke-")
    assert not target.exists()  # Context and runtime writes cleaned up.
    assert (development / "PLAN.md").read_bytes() == before


def test_explicit_project_still_rejects_stale_plan(tmp_path):
    project = make_project(tmp_path / "real-project", age=22)
    result = smoke_test.run_shared_smoke("session_start", project_root=project)["result"]
    assert result["ok"] is False
    assert result["pre_task_check"]["errors"] == ["PLAN.md freshness is CRITICAL"]
    assert result["project_root"] == str(project)


def test_environment_contract_preserves_existing_target_and_failure(tmp_path, monkeypatch):
    project = make_project(tmp_path / "env-project", age=22)
    shutil.copytree(FRAMEWORK / "runtime_hooks/examples", project / "runtime_hooks/examples")
    monkeypatch.chdir(project)
    monkeypatch.setenv("AI_GOVERNANCE_CONTRACT", str(project / "contract.yaml"))
    result = smoke_test.run_shared_smoke("session_start")["result"]
    assert result["ok"] is False
    assert result["contract_resolution"]["source"] == "env"
    assert Path(result["contract_resolution"]["path"]) == project / "contract.yaml"
    assert result["pre_task_check"]["errors"] == ["PLAN.md freshness is CRITICAL"]


@pytest.mark.parametrize("harness,event", [(None, "session_start"), ("claude_code", "pre_task")])
@pytest.mark.parametrize("age", [0, 22])
def test_environment_contract_targets_consumer_from_framework_cwd(tmp_path, monkeypatch, harness, event, age):
    development = make_project(tmp_path / "framework", age=22 if age == 0 else 0)
    consumer = make_project(tmp_path / "consumer with spaces", age=age)
    shutil.copytree(FRAMEWORK / "runtime_hooks/examples", development / "runtime_hooks/examples")
    monkeypatch.chdir(development)
    monkeypatch.setenv("AI_GOVERNANCE_CONTRACT", os.path.relpath(consumer / "contract.yaml", development))
    monkeypatch.setenv("AI_GOVERNANCE_NO_LEDGER_WRITE", "1")
    before = {p: p.read_bytes() for p in (development / "PLAN.md", consumer / "PLAN.md")}
    result = (smoke_test.run_shared_smoke(event) if harness is None
              else smoke_test.run_smoke(harness, event))["result"]
    check = result.get("pre_task_check", result)
    assert Path(check["plan_path"]) == consumer / "PLAN.md"
    assert Path(check["project_root"]) == consumer
    assert result["contract_resolution"]["source"] == "env"
    assert Path(result["contract_resolution"]["path"]) == consumer / "contract.yaml"
    assert result["ok"] is (age == 0)
    assert check["freshness"]["status"] == ("FRESH" if age == 0 else "CRITICAL")
    if age:
        assert "PLAN.md freshness is CRITICAL" in check["errors"]
    assert all(p.read_bytes() == original for p, original in before.items())


@pytest.mark.parametrize("option", ["--project-root", "--plan-path", "--contract"])
def test_explicit_cli_target_wins_over_environment(tmp_path, option):
    consumer = make_project(tmp_path / "env-consumer", age=22)
    explicit = make_project(tmp_path / "explicit-consumer")
    target = {"--project-root": explicit, "--plan-path": explicit / "PLAN.md",
              "--contract": explicit / "contract.yaml"}[option]
    completed = subprocess.run(
        [sys.executable, str(FRAMEWORK / "runtime_hooks/smoke_test.py"),
         "--event-type", "session_start", option, str(target), "--format", "json"],
        cwd=FRAMEWORK, env={**os.environ, "AI_GOVERNANCE_CONTRACT": str(consumer / "contract.yaml"),
                            "AI_GOVERNANCE_NO_LEDGER_WRITE": "1", "PYTHONIOENCODING": "utf-8",
                            "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)["result"]
    assert Path(result["pre_task_check"]["plan_path"]) == explicit / "PLAN.md"
    resolution = result["contract_resolution"]
    assert resolution["source"] == ("explicit" if option == "--contract" else "env")
    assert Path(resolution["path"]) == (explicit if option == "--contract" else consumer) / "contract.yaml"


@pytest.mark.parametrize("harness,event", [(None, "session_start"), ("claude_code", "pre_task")])
@pytest.mark.parametrize("layout", ["nested", "nested_with_plan", "no_plan"])
def test_nested_environment_contract_preserves_layout_contract(tmp_path, monkeypatch, harness, event, layout):
    consumer = make_project(tmp_path / "consumer", age=22 if layout == "nested_with_plan" else 0)
    config = make_project(consumer / "config")
    if layout != "nested_with_plan":
        (config / "PLAN.md").unlink()
    if layout == "no_plan":
        (consumer / "PLAN.md").unlink()
    shutil.copytree(FRAMEWORK / "runtime_hooks/examples", consumer / "runtime_hooks/examples")
    monkeypatch.chdir(consumer)
    monkeypatch.setenv("AI_GOVERNANCE_CONTRACT", str(config / "contract.yaml"))
    monkeypatch.setenv("AI_GOVERNANCE_NO_LEDGER_WRITE", "1")
    result = (smoke_test.run_shared_smoke(event) if harness is None
              else smoke_test.run_smoke(harness, event))["result"]
    check = result.get("pre_task_check", result)
    expected_root = config if layout == "nested_with_plan" else consumer
    assert Path(check["project_root"]).resolve() == expected_root
    assert Path(check["plan_path"]).resolve() == expected_root / "PLAN.md"
    assert result["contract_resolution"]["source"] == "env"
    assert Path(result["contract_resolution"]["path"]) == config / "contract.yaml"
    assert result["ok"] is (layout != "no_plan")
    assert check["freshness"]["status"] == ("ERROR" if layout == "no_plan" else "FRESH")


def test_required_contract_failure_still_exits_nonzero(tmp_path):
    project = make_project(tmp_path / "real-project")
    contract = project / "required.yaml"
    completed = subprocess.run(
        [sys.executable, str(FRAMEWORK / "runtime_hooks/smoke_test.py"),
         "--event-type", "session_start", "--project-root", str(project),
         "--contract", str(contract), "--format", "json"],
        cwd=FRAMEWORK, env={**os.environ, "AI_GOVERNANCE_NO_LEDGER_WRITE": "1",
                            "PYTHONDONTWRITEBYTECODE": "1"},
        text=True, capture_output=True,
    )
    assert completed.returncode != 0
    assert "contract" in (completed.stdout + completed.stderr).lower()


def test_advisory_and_actual_blocker_are_not_swallowed(tmp_path):
    project = make_project(tmp_path / "real-project", age=8)
    payload = json.loads((FRAMEWORK / "runtime_hooks/examples/shared/session_start.shared.json").read_text())
    payload.update(project_root=str(project), plan_path=str(project / "PLAN.md"),
                   risk="high", oversight="auto")
    payload_file = tmp_path / "event.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")
    result = smoke_test.run_shared_smoke("session_start", payload_file=payload_file)["result"]
    check = result["pre_task_check"]
    assert result["ok"] is False
    assert "PLAN.md is STALE" in check["warnings"]
    assert "High-risk tasks require oversight != auto" in check["errors"]


def test_default_fixture_does_not_swallow_actual_runtime_failure(monkeypatch):
    original = smoke_test.NORMALIZERS["claude_code"]

    def unauthorized(payload, event_type):
        normalized = original(payload, event_type=event_type)
        normalized.update(risk="high", oversight="auto")
        return normalized

    monkeypatch.setitem(smoke_test.NORMALIZERS, "claude_code", unauthorized)
    result = smoke_test.run_smoke("claude_code", "pre_task")["result"]
    assert result["ok"] is False
    assert "High-risk tasks require oversight != auto" in result["errors"]
