"""The VS Code Copilot agent learns its own session id from the governed SessionStart (ruling 2026-11-12).

VS Code gives the agent no session id, yet closeout preparation needs the platform's own
id. After the shared Copilot SessionStart has established or preserved a root-bound
github-copilot-vscode identity, the hook returns the documented top-level
additionalContext naming that id. The note only informs the agent: R2 still checks the
platform-created envelope, repository, transcript and ownership on its own, and verify
reports the VS Code Stop and Copilot CLI sessionEnd execution points separately.
"""
import json
import os
from pathlib import Path

import pytest

from governance_tools.hook_install_validator import VSCODE_MANAGED_STOP_ENTRY, copilot_closeout_wiring
from governance_tools.manage_agent_closeout import _PENDING_HOOK_NOTE, CopilotAdapter
from runtime_hooks.adapters.copilot.lifecycle import run_lifecycle_event
from runtime_hooks.core import _canonical_closeout as core
from tests.test_vscode_root_bound_session import (  # noqa: F401 - fixtures
    FRAMEWORK, _run_installed, envelope_path, installed_consumer, repo)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def copilot_home(tmp_path_factory, monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    home = tmp_path_factory.mktemp("copilot-home")
    monkeypatch.setenv("COPILOT_HOME", str(home))
    return home


def register(sid, client="vscode-agent-host"):
    state = Path(os.environ["COPILOT_HOME"]) / "session-state" / sid
    state.mkdir(parents=True, exist_ok=True)
    (state / "workspace.yaml").write_text(f"id: {sid}\nclient_name: {client}\n", encoding="utf-8")


def copilot_start(root, sid, **extra):
    return run_lifecycle_event({"sessionId": sid, "cwd": str(root), "hookEventName": "sessionStart", **extra},
                               event_type="session_start", surface="copilot")


# ── SessionStart tells the VS Code agent its id, and nothing else gets it ──────

def test_vscode_identity_start_returns_its_session_id_as_additional_context(repo):
    register("vs-a")
    result = copilot_start(repo, "vs-a")
    assert result["ok"] and result["provider"] == "github-copilot-vscode"
    context = result["additionalContext"]
    assert isinstance(context, str) and "vs-a" in context
    assert str(repo) in context
    assert "prepare_closeout_candidate.py" in context and "PREPARED / PENDING_HOOK" in context
    assert "manual_fallback" in context and "not proof of identity" in context
    assert ".current-session-id" in context  # named only as the place never to take an id from
    assert "hookSpecificOutput" not in result  # the documented top-level field only
    # The id named is the one the platform-created envelope holds.
    assert core.read_session_envelope("vs-a", repo)["session_id"] == "vs-a"


def test_snake_case_vscode_start_also_returns_the_id(repo):
    result = run_lifecycle_event({"session_id": "vs-snake", "cwd": str(repo), "hook_event_name": "SessionStart"},
                                 event_type="session_start", surface="vscode")
    assert result["session_envelope_binding"] == "root_bound"
    assert "vs-snake" in result["additionalContext"]


def test_resumed_vscode_identity_is_named_again(repo):
    register("vs-r")
    copilot_start(repo, "vs-r")
    before = envelope_path(repo, "vs-r").read_bytes()
    again = copilot_start(repo, "vs-r", source="resume")
    assert again["status"] == "session_envelope_preserved"
    assert "vs-r" in again["additionalContext"]
    assert envelope_path(repo, "vs-r").read_bytes() == before


def test_copilot_cli_identity_gets_no_session_id_context(repo):
    register("cli-a", "github/cli")
    result = copilot_start(repo, "cli-a")
    assert result["ok"] and result["provider"] == "github-copilot"
    assert result["session_envelope_binding"] == "root_bound"
    assert "additionalContext" not in result


def test_legacy_vscode_identity_gets_no_session_id_context(repo):
    register("vs-legacy")
    core.write_session_envelope("vs-legacy", repo, provider="github-copilot-vscode")  # 1.0
    result = copilot_start(repo, "vs-legacy")
    assert result["session_envelope_binding"] == "legacy"
    assert "additionalContext" not in result


@pytest.mark.parametrize("record", ["missing", "unknown_client", "other_session"])
def test_no_identity_means_no_context_and_no_envelope(repo, record):
    sid = "vs-bad"
    if record == "unknown_client":
        register(sid, "some-other-host")
    elif record == "other_session":
        state = Path(os.environ["COPILOT_HOME"]) / "session-state" / sid
        state.mkdir(parents=True)
        (state / "workspace.yaml").write_text("id: someone-else\nclient_name: vscode-agent-host\n", encoding="utf-8")
    with pytest.raises(ValueError):
        copilot_start(repo, sid)
    assert not envelope_path(repo, sid).exists()


def test_installed_entry_prints_top_level_additional_context(installed_consumer):
    """What the Copilot runtime reads: the installed command's stdout JSON."""
    register("vs-installed")
    result = _run_installed(installed_consumer, {"sessionId": "vs-installed", "hookEventName": "sessionStart",
                                                 "cwd": str(installed_consumer)})
    assert result["ok"] is True and result["provider"] == "github-copilot-vscode", result
    assert "vs-installed" in result["additionalContext"]


def test_installed_entry_failure_prints_no_context(installed_consumer):
    result = _run_installed(installed_consumer, {"sessionId": "vs-missing", "hookEventName": "sessionStart",
                                                 "cwd": str(installed_consumer)})
    assert result["ok"] is False and result["status"] == "bridge_error"
    assert "additionalContext" not in result


# ── verify reports each Copilot execution point on its own ─────────────────────

def test_verify_reports_vscode_stop_and_cli_session_end_separately(installed_consumer):
    wiring = copilot_closeout_wiring(installed_consumer)
    assert wiring == {"bridge_governed": True, "shared_registration_governed": True,
                      "vscode_stop": True, "cli_session_end": True}
    result = CopilotAdapter().verify(installed_consumer, FRAMEWORK)
    assert result["installed"] is True
    assert result["vscode_stop"] is True and result["cli_session_end"] is True
    assert result["location"].endswith("ai-governance-vscode.json")
    assert "VS Code Copilot Stop (agent_stop): installed" in result["note"]
    assert "closeout is left to it" in result["note"]
    assert "Copilot CLI sessionEnd (lifecycle bridge): installed" in result["note"]
    assert result["note"].endswith(_PENDING_HOOK_NOTE)


def test_verify_without_the_vscode_stop_keeps_the_cli_and_drops_the_pending_note(installed_consumer):
    config = installed_consumer / ".github/hooks/ai-governance-vscode.json"
    config.write_text(json.dumps({"version": 1, "hooks": {"Stop": [{"type": "command", "command": "echo hi"}]}}),
                      encoding="utf-8")
    result = CopilotAdapter().verify(installed_consumer, FRAMEWORK)
    assert result["vscode_stop"] is False and result["cli_session_end"] is True
    assert result["installed"] is True  # the CLI sessionEnd is still wired
    assert "VS Code Copilot Stop (agent_stop): not installed" in result["note"]
    assert _PENDING_HOOK_NOTE not in result["note"]


def test_verify_with_a_retired_vscode_session_end_is_not_a_stop_point(installed_consumer):
    config = installed_consumer / ".github/hooks/ai-governance-vscode.json"
    legacy = {"type": "command",
              "command": "python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"}
    config.write_text(json.dumps({"version": 1, "hooks": {"Stop": [VSCODE_MANAGED_STOP_ENTRY, legacy]}}),
                      encoding="utf-8")
    assert copilot_closeout_wiring(installed_consumer)["vscode_stop"] is False


def test_verify_without_the_shared_registration_reports_neither(installed_consumer):
    (installed_consumer / ".github/hooks/ai-governance-copilot.json").write_text(
        json.dumps({"version": 1, "hooks": {"sessionEnd": []}}), encoding="utf-8")
    wiring = copilot_closeout_wiring(installed_consumer)
    assert wiring["vscode_stop"] is False and wiring["cli_session_end"] is False
    result = CopilotAdapter().verify(installed_consumer, FRAMEWORK)
    assert result["installed"] is False
    assert _PENDING_HOOK_NOTE not in result["note"]


def test_verify_without_the_bridge_reports_neither(installed_consumer):
    (installed_consumer / ".github/hooks/ai-governance-lifecycle.py").unlink()
    assert copilot_closeout_wiring(installed_consumer) == {
        "bridge_governed": False, "shared_registration_governed": False,
        "vscode_stop": False, "cli_session_end": False}


def test_verify_agrees_with_the_hook_validator(installed_consumer):
    from governance_tools.hook_install_validator import validate_hook_install
    checks = validate_hook_install(installed_consumer, FRAMEWORK).checks
    wiring = copilot_closeout_wiring(installed_consumer)
    assert checks["copilot_session_end_hooks_governed"] is wiring["cli_session_end"] is True
    assert checks["copilot_vscode_hooks_governed"] is True and wiring["vscode_stop"] is True


# ── guidance: one source of the VS Code id, CLI and manual fallback kept apart ─

GUIDANCE = ["AGENTS.base.md", "baselines/repo-min/AGENTS.base.md",
            "governance/agent-contract-template.md", "governance/copilot-instructions-template.md"]


@pytest.mark.parametrize("rel", GUIDANCE)
def test_guidance_names_the_vscode_id_source_and_separates_the_cli(rel):
    text = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
    assert ("in VS Code Copilot, the id that the governed SessionStart hook adds to the conversation as "
            "`additionalContext`") in text
    assert "the Codex Stop hook and the VS Code Copilot Stop hook" in text
    assert "a Copilot CLI session is given no session id, so it does not prepare" in text
    assert "is rejected and its closeout" not in text and "is rejected: report" not in text
    assert "today only the Codex Stop hook" not in text
    assert "RELEASE_PROOF_INVALID" in text  # the refused manual fallback stays named
