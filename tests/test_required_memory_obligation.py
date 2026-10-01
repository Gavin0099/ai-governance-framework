import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


HOOK = Path(__file__).resolve().parents[1] / "governance_tools" / "required_memory_obligation.py"
SESSION = "01a0eb40-0000-7000-8000-000000000001"


def _repo(tmp_path, checker_state="blocked"):
    repo = tmp_path / "MEM-TRIGGER-001"
    (repo / "memory").mkdir(parents=True)
    (repo / ".codex").mkdir()
    (repo / "PLAN.md").write_text("# Test plan\n\n- [ ] Verify the required dependency.\n", encoding="utf-8")
    (repo / "memory" / "01_active_task.md").write_text(
        "# Active task\n\n- Sample task awaits execution.\n", encoding="utf-8"
    )
    checker = repo / "verify-prereq.ps1"
    event_line = (
        'GOVERNANCE_EVENT_V1 {"id":"MEM-TRIGGER-001",'
        '"type":"required_dependency_blocked",'
        '"dependency":"mem-trigger-required-tool","status":"blocked"}'
    )
    script = {
        "blocked": f"Write-Output '{event_line}'\nexit 42\n",
        "ready": "Write-Output 'Dependency ready'\nexit 0\n",
        "malformed": "Write-Output 'GOVERNANCE_EVENT_V1 {broken-json'\nexit 42\n",
    }[checker_state]
    checker.write_text(script, encoding="utf-8")
    (repo / ".codex" / "memory-obligation-contract.json").write_text(
        json.dumps({
            "event_id": "MEM-TRIGGER-001",
            "dependency": "mem-trigger-required-tool",
            "event_type": "required_dependency_blocked",
            "event_status": "blocked",
            "approved_producer": {
                "path": "verify-prereq.ps1",
                "sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
                "blocked_exit_code": 42,
            },
            "plan_risk_headings": ["Risk", "Risks", "Risk / blocker", "Risks / Blockers", "風險"],
        }),
        encoding="utf-8",
    )
    return repo


def _invoke(repo, phase, payload, trusted_sha=None):
    if trusted_sha is None:
        trusted_sha = hashlib.sha256((repo / "verify-prereq.ps1").read_bytes()).hexdigest()
    completed = subprocess.run(
        [sys.executable, "-B", str(HOOK), "--event", phase, "--repo-root", str(repo),
         "--contract", ".codex/memory-obligation-contract.json",
         "--approved-producer-path", "verify-prereq.ps1",
         "--approved-producer-sha256", trusted_sha],
        input=json.dumps(payload), text=True, capture_output=True, check=True,
    )
    return json.loads(completed.stdout)


def _blocked_tool_event():
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "session_id": SESSION,
        "turn_id": "turn-A",
        "tool_use_id": "exec-required-check",
        "tool_input": {"command": "Get-Content PLAN.md; & .\\verify-prereq.ps1; Write-Output EXIT_CODE=42"},
        "tool_response": (
            'GOVERNANCE_EVENT_V1 {"id":"MEM-TRIGGER-001",'
            '"type":"required_dependency_blocked",'
            '"dependency":"mem-trigger-required-tool","status":"blocked"}\n'
            "Required converter unavailable: mem-trigger-required-tool\nEXIT_CODE=42"
        ),
    }


def _stop_event(active=False, message="Sample task DONE"):
    return {
        "hook_event_name": "Stop",
        "session_id": SESSION,
        "turn_id": "turn-A",
        "stop_hook_active": active,
        "last_assistant_message": message,
    }


def test_a_recognized_blocker_requires_plan_risk_and_active_task(tmp_path):
    repo = _repo(tmp_path)
    feedback = _invoke(repo, "post-tool-use", _blocked_tool_event())
    state = list((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json"))
    assert len(state) == 1
    record = json.loads(state[0].read_text(encoding="utf-8"))
    obligation_id = record["id"]
    assert record["event_id"] == "MEM-TRIGGER-001"
    assert obligation_id in feedback["hookSpecificOutput"]["additionalContext"]
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"

    with (repo / "PLAN.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n## Risk / blocker\n- {obligation_id} mem-trigger-required-tool unavailable.\n")
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"

    with (repo / "memory" / "01_active_task.md").open("a", encoding="utf-8") as stream:
        stream.write(f"- {obligation_id} mem-trigger-required-tool blocked.\n")
    assert _invoke(repo, "stop", _stop_event()) == {}
    assert json.loads(state[0].read_text(encoding="utf-8"))["status"] == "resolved"

    (repo / "memory" / "01_active_task.md").write_text("# Active task\n", encoding="utf-8")
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"
    assert json.loads(state[0].read_text(encoding="utf-8"))["status"] == "pending"


def test_b_intentional_miss_blocks_completion_but_allows_honest_blocked_report(tmp_path):
    repo = _repo(tmp_path)
    _invoke(repo, "post-tool-use", _blocked_tool_event())
    record = json.loads(next((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json")).read_text(encoding="utf-8"))
    obligation_id = record["id"]
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"
    assert _invoke(repo, "stop", _stop_event(active=True, message="Still DONE"))["continue"] is False
    honest = f"BLOCKED: MEMORY_OBLIGATION_UNRESOLVED {obligation_id}"
    assert _invoke(repo, "stop", _stop_event(active=True, message=honest)) == {}


def test_no_declared_blocker_does_not_create_an_obligation(tmp_path):
    repo = _repo(tmp_path, checker_state="ready")
    event = _blocked_tool_event()
    event["tool_input"]["command"] = "rg missing-pattern"
    event["tool_response"] = "Required converter unavailable: mem-trigger-required-tool\nEXIT_CODE=1"
    assert _invoke(repo, "post-tool-use", event) == {}
    event["tool_input"]["command"] = "./verify-prereq.ps1"
    event["tool_response"] = "Dependency ready"
    assert _invoke(repo, "post-tool-use", event) == {}
    assert not (repo / "memory" / ".pending_memory_obligations").exists()
    observations = list((repo / "memory" / ".memory_obligation_observations" / SESSION).glob("*.json"))
    assert len(observations) == 1
    assert json.loads(observations[0].read_text(encoding="utf-8"))["status"] == "no_blocker"
    assert _invoke(repo, "stop", _stop_event()) == {}


def test_command_forms_with_same_event_reuse_one_obligation(tmp_path):
    repo = _repo(tmp_path)
    event = _blocked_tool_event()
    for index, command in enumerate((
        "& .\\verify-prereq.ps1",
        "powershell -NoProfile -File .\\verify-prereq.ps1",
        "./verify-prereq.ps1",
        "pwsh -File verify-prereq.ps1",
    )):
        event["tool_input"]["command"] = command
        event["tool_use_id"] = f"exec-check-{index}"
        feedback = _invoke(repo, "post-tool-use", event)
        assert "MEM-OBL-" in feedback["hookSpecificOutput"]["additionalContext"]
    records = list((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json"))
    assert len(records) == 1
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"


def test_absolute_checker_and_interpreter_forms_reuse_relative_obligation(tmp_path):
    repo = _repo(tmp_path / "parent with spaces")
    checker = repo / "verify-prereq.ps1"
    interpreter = shutil.which("pwsh")
    assert interpreter, "Focused checker tests require PowerShell"
    event = _blocked_tool_event()
    obligation_ids = set()
    for index, command in enumerate((
        "./verify-prereq.ps1",
        f'& "{checker}"',
        f'"{interpreter}" -NoProfile -File "{checker}"',
        f'& "{interpreter}" -File .\\verify-prereq.ps1',
        f'"{tmp_path / "unrelated.exe"}" --version; & "{checker}"',
    )):
        event["tool_input"]["command"] = command
        event["tool_use_id"] = f"absolute-check-{index}"
        feedback = _invoke(repo, "post-tool-use", event)
        assert "MEM-OBL-" in feedback["hookSpecificOutput"]["additionalContext"]
        records = list((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json"))
        assert len(records) == 1
        obligation_ids.add(json.loads(records[0].read_text(encoding="utf-8"))["id"])
    assert len(obligation_ids) == 1
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"


def test_unrelated_absolute_executable_is_ignored_without_state(tmp_path):
    repo = _repo(tmp_path)
    event = _blocked_tool_event()
    event["tool_input"]["command"] = f'"{tmp_path / "Program Files" / "Docker" / "docker.exe"}" --version'
    assert _invoke(repo, "post-tool-use", event) == {}
    assert not (repo / "memory" / ".memory_obligation_observations").exists()
    assert not (repo / "memory" / ".pending_memory_obligations").exists()
    assert _invoke(repo, "stop", _stop_event()) == {}


def test_similar_absolute_checker_paths_do_not_register(tmp_path):
    repo = _repo(tmp_path)
    other = tmp_path / "unapproved" / "verify-prereq.ps1"
    other.parent.mkdir()
    other.write_bytes((repo / "verify-prereq.ps1").read_bytes())
    event = _blocked_tool_event()
    for command in (
        f'& "{other}"',
        f'pwsh -File "{other}"',
        f'& "{repo / "verify-prereq.ps1.bak"}"',
    ):
        event["tool_input"]["command"] = command
        assert _invoke(repo, "post-tool-use", event) == {}
    assert not (repo / "memory" / ".memory_obligation_observations").exists()
    assert not (repo / "memory" / ".pending_memory_obligations").exists()
    assert _invoke(repo, "stop", _stop_event()) == {}


@pytest.mark.parametrize("error_type", [OSError, ValueError])
def test_invocation_path_resolution_failure_leaves_blocking_fallback(tmp_path, monkeypatch, error_type):
    from governance_tools import required_memory_obligation as bridge

    repo = _repo(tmp_path)
    event = _blocked_tool_event()
    contract = json.loads((repo / ".codex" / "memory-obligation-contract.json").read_text(encoding="utf-8"))

    def resolution_error(*args):
        raise error_type("invocation path resolution failed")

    monkeypatch.setattr(bridge, "_approved_invocation", resolution_error)
    with pytest.raises(error_type, match="invocation path resolution failed"):
        bridge._register(repo, contract, event)
    records = list((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["status"] == "registration_error"
    stop = _invoke(repo, "stop", _stop_event())
    assert stop["decision"] == "block"
    assert record["id"] in stop["reason"]


def test_unlisted_plan_heading_does_not_consume_obligation(tmp_path):
    repo = _repo(tmp_path)
    _invoke(repo, "post-tool-use", _blocked_tool_event())
    state = next((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json"))
    obligation_id = json.loads(state.read_text(encoding="utf-8"))["id"]
    with (repo / "PLAN.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n## Notes\n- {obligation_id} mem-trigger-required-tool unavailable.\n")
    with (repo / "memory" / "01_active_task.md").open("a", encoding="utf-8") as stream:
        stream.write(f"- {obligation_id} mem-trigger-required-tool blocked.\n")
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"


def test_malformed_structured_event_fails_registration_closed(tmp_path):
    repo = _repo(tmp_path, checker_state="malformed")
    event = _blocked_tool_event()
    response = _invoke(repo, "post-tool-use", event)
    assert response["decision"] == "block"
    assert "MEMORY_OBLIGATION_REGISTRATION_ERROR" in response["reason"]
    stop = _invoke(repo, "stop", _stop_event())
    assert stop["decision"] == "block"
    assert "MEMORY_OBLIGATION_REGISTRATION_ERROR" in stop["reason"]
    assert not list((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("MEM-OBL-*.json"))


def test_registered_obligation_state_loss_blocks_stop(tmp_path):
    repo = _repo(tmp_path)
    _invoke(repo, "post-tool-use", _blocked_tool_event())
    record = next((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("MEM-OBL-*.json"))
    obligation_id = record.stem
    record.unlink()
    stop = _invoke(repo, "stop", _stop_event())
    assert stop["decision"] == "block"
    assert f"MEMORY_OBLIGATION_STATE_LOST:{obligation_id}" in stop["reason"]


def test_observation_creation_failure_leaves_a_blocking_fallback(tmp_path):
    repo = _repo(tmp_path)
    observation_root = repo / "memory" / ".memory_obligation_observations"
    observation_root.write_text("occupied by a file", encoding="utf-8")
    response = _invoke(repo, "post-tool-use", _blocked_tool_event())
    assert response["decision"] == "block"
    fallback = list((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("MEM-OBL-*.json"))
    assert len(fallback) == 1
    assert json.loads(fallback[0].read_text(encoding="utf-8"))["status"] == "registration_error"
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"
    observation_root.unlink()
    stop = _invoke(repo, "stop", _stop_event())
    assert stop["decision"] == "block"
    assert "REGISTRATION-ERROR" in stop["reason"]


def test_partial_observation_write_blocks_stop(tmp_path):
    repo = _repo(tmp_path)
    _invoke(repo, "post-tool-use", _blocked_tool_event())
    receipt = next((repo / "memory" / ".memory_obligation_observations" / SESSION).glob("*.json"))
    receipt.write_text('{"status":', encoding="utf-8")
    stop = _invoke(repo, "stop", _stop_event())
    assert stop["decision"] == "block"
    assert "MEMORY_OBLIGATION_STATE_ERROR" in stop["reason"]


def test_resolved_observation_allows_next_turn(tmp_path):
    repo = _repo(tmp_path)
    _invoke(repo, "post-tool-use", _blocked_tool_event())
    state = next((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("MEM-OBL-*.json"))
    obligation_id = state.stem
    (repo / "PLAN.md").write_text(
        f"# Test plan\n\n## Risks\n- {obligation_id} mem-trigger-required-tool blocked.\n",
        encoding="utf-8",
    )
    (repo / "memory" / "01_active_task.md").write_text(
        f"# Active task\n- {obligation_id} mem-trigger-required-tool blocked.\n",
        encoding="utf-8",
    )
    assert _invoke(repo, "stop", _stop_event()) == {}
    later = _stop_event()
    later["turn_id"] = "turn-later"
    assert _invoke(repo, "stop", later) == {}
    receipt = next((repo / "memory" / ".memory_obligation_observations" / SESSION).glob("*.json"))
    observation = json.loads(receipt.read_text(encoding="utf-8"))
    assert observation["turn_id"] == "turn-A"
    assert observation["dependency"] == "mem-trigger-required-tool"
    assert json.loads(state.read_text(encoding="utf-8"))["status"] == "resolved"


def test_echoed_marker_without_checker_invocation_does_not_register(tmp_path):
    repo = _repo(tmp_path)
    event = _blocked_tool_event()
    event["tool_input"]["command"] = "Write-Output '<structured event marker>'"
    assert _invoke(repo, "post-tool-use", event) == {}
    assert not (repo / "memory" / ".pending_memory_obligations").exists()


@pytest.mark.parametrize("command", [
    "Write-Output 'ready'; # & .\\verify-prereq.ps1",
    "# & .\\verify-prereq.ps1\nWrite-Output 'ready'",
    "Write-Output 'ready'; <# & .\\verify-prereq.ps1 #>",
    "<# comment\n& .\\verify-prereq.ps1\n#>\nWrite-Output 'ready'",
])
def test_commented_checker_is_not_an_invocation(tmp_path, command):
    repo = _repo(tmp_path)
    actual = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=repo, capture_output=True, text=True, timeout=15,
    )
    assert actual.returncode == 0, actual.stderr
    assert actual.stdout.strip() == "ready"
    assert not actual.stderr
    event = _blocked_tool_event()
    event["tool_input"]["command"] = command
    event["tool_response"] = actual.stdout
    assert _invoke(repo, "post-tool-use", event) == {}
    assert not (repo / "memory" / ".memory_obligation_observations").exists()
    assert not (repo / "memory" / ".pending_memory_obligations").exists()
    assert _invoke(repo, "stop", _stop_event()) == {}


@pytest.mark.parametrize("command", [
    "# & .\\verify-prereq.ps1\n& .\\verify-prereq.ps1",
    "Write-Output 'literal #'; <# & .\\verify-prereq.ps1 #>\n& .\\verify-prereq.ps1",
])
def test_checker_after_comment_still_registers(tmp_path, command):
    repo = _repo(tmp_path)
    actual = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=repo, capture_output=True, text=True, timeout=15,
    )
    assert actual.returncode != 0, actual.stderr
    assert "GOVERNANCE_EVENT_V1 " in actual.stdout
    event = _blocked_tool_event()
    event["tool_input"]["command"] = command
    event["tool_response"] = actual.stdout
    feedback = _invoke(repo, "post-tool-use", event)
    assert "MEM-OBL-" in feedback["hookSpecificOutput"]["additionalContext"]
    assert _invoke(repo, "stop", _stop_event())["decision"] == "block"


def test_changed_approved_checker_fails_closed(tmp_path):
    repo = _repo(tmp_path)
    trusted_sha = hashlib.sha256((repo / "verify-prereq.ps1").read_bytes()).hexdigest()
    (repo / "verify-prereq.ps1").write_text("Write-Output 'changed'\n", encoding="utf-8")
    response = _invoke(repo, "post-tool-use", _blocked_tool_event(), trusted_sha=trusted_sha)
    assert response["decision"] == "block"
    assert "approved producer bytes do not match" in response["reason"]


def test_modified_contract_cannot_replace_trusted_producer_sha(tmp_path):
    repo = _repo(tmp_path)
    trusted_sha = hashlib.sha256((repo / "verify-prereq.ps1").read_bytes()).hexdigest()
    checker = repo / "verify-prereq.ps1"
    checker.write_text("Write-Output 'Dependency ready'\nexit 0\n", encoding="utf-8")
    contract_path = repo / ".codex" / "memory-obligation-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["approved_producer"]["sha256"] = hashlib.sha256(checker.read_bytes()).hexdigest()
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    response = _invoke(repo, "post-tool-use", _blocked_tool_event(), trusted_sha=trusted_sha)
    assert response["decision"] == "block"
    assert "differs from trusted hook definition" in response["reason"]


def test_malformed_hook_stdin_capture_preserves_raw_bytes_and_stage(tmp_path):
    repo = _repo(tmp_path)
    raw = b'{"hook_event_name":"PostToolUse","tool_response":{"output":"broken"}'
    env = dict(os.environ)
    env["MEM_TRIGGER_CAPTURE_ERRORS"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", str(HOOK), "--event", "post-tool-use",
         "--repo-root", str(repo), "--contract", ".codex/memory-obligation-contract.json",
         "--approved-producer-path", "verify-prereq.ps1",
         "--approved-producer-sha256", hashlib.sha256((repo / "verify-prereq.ps1").read_bytes()).hexdigest()],
        input=raw, capture_output=True, check=True, env=env,
    )
    response = json.loads(completed.stdout)
    assert response["decision"] == "block"
    folder = repo / "memory" / ".hook_payload_errors"
    captures = list(folder.glob("*.stdin.bin"))
    metadata = list(folder.glob("*.error.json"))
    assert len(captures) == len(metadata) == 1
    assert captures[0].read_bytes() == raw
    assert json.loads(metadata[0].read_text(encoding="utf-8"))["stage"] == "payload"


def test_malformed_registered_obligation_fails_closed(tmp_path):
    repo = _repo(tmp_path)
    _invoke(repo, "post-tool-use", _blocked_tool_event())
    record = next((repo / "memory" / ".pending_memory_obligations" / SESSION).glob("*.json"))
    record.write_text("{invalid json", encoding="utf-8")
    response = _invoke(repo, "stop", _stop_event())
    assert response["decision"] == "block"
    assert "MEMORY_OBLIGATION_STATE_ERROR" in response["reason"]
