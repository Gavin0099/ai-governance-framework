"""Copilot agents learn their own session id from the governed SessionStart.

Closeout preparation needs the platform's own id. The shared SessionStart hands off
its root-bound id. CLI also requires current provider verification and governed
sessionEnd wiring. The note only informs the
agent: R2 still checks the envelope, repository, transcript and ownership on its own.
Verify reports the VS Code Stop and Copilot CLI sessionEnd execution points separately.
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from governance_tools import hook_install_validator
from governance_tools.hook_install_validator import (
    VSCODE_MANAGED_STOP_ENTRY, copilot_closeout_wiring, validate_hook_install,
)
from governance_tools.manage_agent_closeout import _PENDING_HOOK_NOTE, CopilotAdapter
from runtime_hooks.adapters.copilot import lifecycle
from runtime_hooks.adapters.copilot.lifecycle import _session_id_context, main, run_lifecycle_event
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


def register(sid, client="vscode-agent-host", *, record_id=None):
    state = Path(os.environ["COPILOT_HOME"]) / "session-state" / sid
    state.mkdir(parents=True, exist_ok=True)
    record = state / "workspace.yaml"
    record.write_text(f"id: {record_id or sid}\nclient_name: {client}\n", encoding="utf-8")
    return record


def copilot_start(root, sid, **extra):
    return run_lifecycle_event({"sessionId": sid, "cwd": str(root), "hookEventName": "sessionStart", **extra},
                               event_type="session_start", surface="copilot")


# ── SessionStart tells root-bound Copilot agents their own id ─────────────────

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


@pytest.mark.parametrize("surface", ["vscode", "copilot"])
def test_vscode_session_start_context_is_byte_identical_to_the_pre_s2_output(repo, surface):
    """Characterization baseline: the complete pre-S2 SessionStart note, verbatim."""
    register("vs-baseline")
    payload = ({"session_id": "vs-baseline", "hook_event_name": "SessionStart"}
               if surface == "vscode" else {"sessionId": "vs-baseline", "hookEventName": "sessionStart"})
    result = run_lifecycle_event({**payload, "cwd": str(repo)}, event_type="session_start", surface=surface)
    expected = (
        "AI Governance: the platform session id of this VS Code Copilot session is "
        f"vs-baseline. The SessionStart hook bound it to {repo}. "
        "Use it as <session-id> for prepare_closeout_candidate.py, and only at an "
        "owner-authorized closeout (AGENTS.base.md, Session Closeout Obligation); never take "
        "an id from artifacts/runtime/.current-session-id. After PREPARED, the VS Code Stop "
        "hook runs the formal closeout after your turn: report PREPARED / PENDING_HOOK, and do "
        "not run manual_fallback. Only R2 evidence (valid closeout, RELEASED ownership) "
        "confirms success. This note is not proof of identity."
    )
    assert result["additionalContext"].encode("utf-8") == expected.encode("utf-8")


@pytest.mark.parametrize("with_record", [True, False])
def test_resumed_vscode_identity_is_named_again(repo, with_record):
    workspace = register("vs-r")
    first = copilot_start(repo, "vs-r")
    before = envelope_path(repo, "vs-r").read_bytes()
    if not with_record:
        workspace.unlink()
    again = copilot_start(repo, "vs-r", source="resume")
    assert again["status"] == "session_envelope_preserved"
    assert again["additionalContext"].encode("utf-8") == first["additionalContext"].encode("utf-8")
    assert envelope_path(repo, "vs-r").read_bytes() == before


def test_copilot_cli_identity_gets_its_id_and_session_end_instructions(installed_consumer):
    repo = installed_consumer
    register("cli-a", "github/cli")
    result = copilot_start(repo, "cli-a")
    assert result["ok"] and result["provider"] == "github-copilot"
    assert result["session_envelope_binding"] == "root_bound"
    context = result["additionalContext"]
    assert "this Copilot CLI session is cli-a." in context
    assert str(repo) in context and "prepare_closeout_candidate.py" in context
    assert "only at an owner-authorized closeout" in context
    assert "never take an id from artifacts/runtime/.current-session-id" in context
    assert "After PREPARED, the CLI sessionEnd hook runs the formal closeout" in context
    assert "when the session ends (not after the turn)" in context
    assert "report PREPARED / PENDING_HOOK" in context and "do not run manual_fallback" in context
    assert "Only R2 evidence (valid closeout, RELEASED ownership) confirms success" in context
    assert "persistent folder trust" in context
    assert "--trust-folder cannot be combined with --resume" in context
    assert "This note is not proof of identity." in context
    assert "VS Code Stop" not in context and "hookSpecificOutput" not in result
    assert core.read_session_envelope("cli-a", repo)["session_id"] == "cli-a"


@pytest.mark.parametrize("entries,ready", [
    ({}, False),
    ([42], True),
    ([{"type": "command"}], True),
    ([{"type": "http"}], True),
    ([{"command": "echo done"}], True),
    ([{"type": "http", "url": "https://example.invalid/hook"}], True),
], ids=["non-array", "non-object", "missing-command", "missing-url", "command-default", "http"])
def test_cli_checks_whole_file_before_handing_off(installed_consumer, entries, ready):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["hooks"]["preToolUse"] = entries
    config.write_text(json.dumps(payload), encoding="utf-8")
    register("cli-shape", "github/cli")
    assert ("additionalContext" in copilot_start(repo, "cli-shape")) is ready
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["cli_session_end"] is ready
    assert verification["vscode_stop"] is False
    assert validate_hook_install(repo, FRAMEWORK).checks["copilot_session_end_hooks_governed"] is False


@pytest.mark.parametrize("suffix,escaped", [
    ("\U0001f9ea", True),
    ("\U0001f9ea", False),
    ("\u00a1", False),
], ids=["ascii-stdin", "utf8-stdin", "utf8-also-valid-cp950"])
def test_installed_cli_bridge_uses_utf8_under_cp950(installed_consumer, suffix, escaped):
    repo = installed_consumer.rename(installed_consumer.with_name(f"consumer {suffix}"))
    register("cli-utf8", "github/cli")
    payload = {"sessionId": "cli-utf8", "cwd": str(repo), "hookEventName": "sessionStart"}
    result = subprocess.run(
        [sys.executable, ".github/hooks/ai-governance-lifecycle.py",
         "--event-type", "session_start", "--surface", "auto"],
        cwd=repo, input=json.dumps(payload, ensure_ascii=escaped).encode("utf-8"),
        capture_output=True, timeout=120, env={**os.environ, "PYTHONIOENCODING": "cp950:strict"},
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert str(repo) in json.loads(result.stdout.decode("utf-8"))["additionalContext"]
    assert repo.name.encode("utf-8") in result.stdout


@pytest.mark.parametrize("client,provider", [
    ("github/cli", "github-copilot"),
    ("vscode-agent-host", "github-copilot-vscode"),
], ids=["cli", "vscode"])
@pytest.mark.parametrize("text_stdin", [False, True], ids=["byte-backed-stdin", "stringio-stdin"])
def test_bridge_hands_off_id_with_stringio_stdout(installed_consumer, monkeypatch, client, provider, text_stdin):
    repo = installed_consumer.rename(installed_consumer.with_name("consumer \u6e2c"))
    sid = "stringio-start"
    register(sid, client)
    payload = json.dumps({"sessionId": sid, "cwd": str(repo), "hookEventName": "sessionStart"}, ensure_ascii=False)
    if text_stdin:
        stdin = io.StringIO(payload)
    else:
        stdin = io.TextIOWrapper(io.BytesIO(payload.encode("utf-8")), encoding="ascii")
    with stdin, io.StringIO() as stdout, monkeypatch.context() as patch:
        patch.setattr(sys, "stdin", stdin)
        patch.setattr(sys, "stdout", stdout)
        assert main(["--event-type", "session_start", "--surface", "auto"]) == 0
        output = stdout.getvalue()
    result = json.loads(output)
    assert result["provider"] == provider
    assert sid in result["additionalContext"] and str(repo) in result["additionalContext"]
    assert repo.name in output


def test_vscode_bridge_keeps_legacy_stdout_encoding(installed_consumer):
    repo = installed_consumer.rename(installed_consumer.with_name("consumer \u6e2c"))
    register("vs-ascii")
    payload = {"session_id": "vs-ascii", "cwd": str(repo), "hook_event_name": "SessionStart"}
    result = subprocess.run(
        [sys.executable, ".github/hooks/ai-governance-lifecycle.py",
         "--event-type", "session_start", "--surface", "auto"],
        cwd=repo, input=json.dumps(payload).encode("ascii"), capture_output=True, timeout=120,
        env={**os.environ, "PYTHONIOENCODING": "ascii:backslashreplace"},
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    document = json.loads(result.stdout)
    assert str(repo) in document["additionalContext"]
    expected = json.dumps(document, ensure_ascii=False).encode("ascii", "backslashreplace")
    assert result.stdout == expected + os.linesep.encode("ascii")


@pytest.mark.parametrize("failure", ["provider-home", "framework-location"])
def test_vscode_bridge_keeps_legacy_output_when_decode_probe_fails(repo, monkeypatch, failure):
    repo = repo.rename(repo.with_name("consumer \u7652"))
    sid = "vs-probe-failure"
    payload = {"session_id": sid, "hook_event_name": "SessionStart", "cwd": str(repo)}
    start = run_lifecycle_event(payload, event_type="session_start", surface="auto")
    assert start["ok"]
    raw = json.dumps({**payload, "source": "resume"}, ensure_ascii=False).encode("cp950")

    def invoke(stdin):
        with stdin, io.StringIO() as stdout, monkeypatch.context() as patch:
            patch.setattr(sys, "stdin", stdin)
            patch.setattr(sys, "stdout", stdout)
            code = main(["--event-type", "session_start", "--surface", "auto"])
            return code, stdout.getvalue().encode("cp950")

    if failure == "provider-home":
        monkeypatch.delenv("COPILOT_HOME")

        def no_home():
            raise RuntimeError("home directory unavailable")

        monkeypatch.setattr(Path, "home", no_home)

    # 53299f7e passes the original text stream directly to json.loads.
    with io.TextIOWrapper(io.BytesIO(raw), encoding="cp950") as stream:
        expected = invoke(io.StringIO(stream.read()))
    assert expected[0] == 0 and sid in json.loads(expected[1].decode("cp950"))["additionalContext"]

    if failure == "framework-location":
        resolve = lifecycle.resolve_framework_root
        monkeypatch.setattr(lifecycle, "__package__", "")  # Direct script entry.

        def resolve_consumer_only(root):
            if root != repo:
                raise RuntimeError("pre-decode framework location unavailable")
            return resolve(root)

        monkeypatch.setattr(lifecycle, "resolve_framework_root", resolve_consumer_only)

    assert invoke(io.TextIOWrapper(io.BytesIO(raw), encoding="cp950")) == expected


@pytest.mark.parametrize("suffix,input_encoding,camel_case,client", [
    pytest.param("\u53f0", "cp950", False, "vscode-agent-host", id="cp950"),
    pytest.param("\u7652", "cp950", False, "vscode-agent-host", id="cp950-also-valid-utf8"),
    pytest.param("\u53f0", "utf-8", False, "vscode-agent-host", id="utf8"),
    pytest.param("\u7652", "cp950", True, "vscode-agent-host", id="camel-case-agent-host"),
    pytest.param("\u7652", "cp950", True, None, id="camel-case-missing-record"),
    pytest.param("\u7652", "cp950", True, "unrecognized", id="camel-case-unknown-client"),
])
def test_vscode_bridge_accepts_cp950_and_utf8_stdin(installed_consumer, suffix, input_encoding, camel_case, client):
    repo = installed_consumer.rename(installed_consumer.with_name(f"consumer {suffix}"))
    sid = "vs-cp950"
    workspace = register(sid)
    payload = {"sessionId": sid, "hookEventName": "sessionStart"} if camel_case else {
        "session_id": sid, "hook_event_name": "SessionStart",
    }
    payload["cwd"] = str(repo)
    if client != "vscode-agent-host":
        assert copilot_start(repo, sid)["provider"] == "github-copilot-vscode"
        payload["source"] = "resume"
        if client is None:
            workspace.unlink()
        else:
            register(sid, client)
    result = subprocess.run(
        [sys.executable, ".github/hooks/ai-governance-lifecycle.py",
         "--event-type", "session_start", "--surface", "auto"],
        cwd=repo, input=json.dumps(payload, ensure_ascii=False).encode(input_encoding),
        capture_output=True, timeout=120, env={**os.environ, "PYTHONIOENCODING": "cp950:strict"},
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    document = json.loads(result.stdout.decode("cp950"))
    assert document["provider"] == "github-copilot-vscode"
    assert sid in document["additionalContext"] and str(repo) in document["additionalContext"]
    assert result.stdout == json.dumps(document, ensure_ascii=False).encode("cp950") + os.linesep.encode("ascii")


@pytest.mark.parametrize("change", ["copilot-home", "disabled"])
def test_cli_refuses_misdirected_or_disabled_closeout(installed_consumer, change):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    if change == "copilot-home":
        payload["hooks"]["sessionEnd"][0]["env"] = {"COPILOT_HOME": str(repo / "wrong-home")}
    else:
        payload["disableAllHooks"] = True
    config.write_text(json.dumps(payload), encoding="utf-8")
    register("cli-not-ready", "github/cli")
    assert "additionalContext" not in copilot_start(repo, "cli-not-ready")
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["cli_session_end"] is False
    assert verification["vscode_stop"] is True


@pytest.mark.parametrize("surface", ["readiness", "f7"])
def test_vscode_only_session_end_command_preserves_legacy_install_result(installed_consumer, surface):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    entry = payload["hooks"]["sessionEnd"][0]
    entry["windows"] = "Write-Output done"
    # Also exercise the platform-specific key on POSIX test hosts.
    os_key = {"darwin": "osx", "linux": "linux"}.get(sys.platform)
    if os_key:
        entry[os_key] = "echo done"
    config.write_text(json.dumps(payload), encoding="utf-8")
    if surface == "readiness":
        from governance_tools.external_repo_readiness import assess_external_repo, governance_health

        assert governance_health(assess_external_repo(repo, framework_root=FRAMEWORK))["copilot_hooks"] == "SAFE"
    else:
        from governance_tools.f7_full_update import _copilot_hook_post_install_errors

        assert _copilot_hook_post_install_errors(repo, FRAMEWORK) == []


@pytest.mark.parametrize("override,ready", [
    ({"env": {"PYTHONIOENCODING": "utf-16"}}, False),
    ({"timeoutSec": "30"}, False),
    ({"windows": "Write-Output done"}, True),
], ids=["encoding", "string-timeout", "vscode-only-command"])
def test_cli_bounded_readiness_regressions(installed_consumer, monkeypatch, override, ready):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["hooks"]["sessionEnd"][0].update(override)
    config.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(hook_install_validator, "sys", SimpleNamespace(platform="win32"))
    register("cli-bounded", "github/cli")
    assert ("additionalContext" in copilot_start(repo, "cli-bounded")) is ready
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["cli_session_end"] is ready
    assert verification["vscode_stop"] is True
    assert validate_hook_install(repo, FRAMEWORK).checks["copilot_session_end_hooks_governed"] is True


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_installer_registration_matches_cli_template_on_both_platforms(installed_consumer, monkeypatch, platform):
    monkeypatch.setattr(hook_install_validator, "sys", SimpleNamespace(platform=platform))
    register("cli-template", "github/cli")
    assert "cli-template" in copilot_start(installed_consumer, "cli-template")["additionalContext"]
    assert CopilotAdapter().verify(installed_consumer, FRAMEWORK)["cli_session_end"] is True


@pytest.mark.parametrize("override,cli_ready", [
    ({"env": {"Path": "somewhere"}}, False),
    ({"timeoutSec": "30"}, False),
    ({"windows": "Write-Output done"}, True),
], ids=["path", "string-timeout", "vscode-only-command"])
def test_cli_start_uses_template_without_changing_vscode(installed_consumer, monkeypatch, override, cli_ready):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["hooks"]["sessionStart"][0].update(override)
    config.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(hook_install_validator, "sys", SimpleNamespace(platform="win32"))
    register("cli-bounded-start", "github/cli")
    assert ("additionalContext" in copilot_start(repo, "cli-bounded-start")) is cli_ready
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["cli_session_end"] is True
    assert verification["vscode_stop"] is True
    assert validate_hook_install(repo, FRAMEWORK).checks["copilot_session_end_hooks_governed"] is True


@pytest.mark.parametrize("registration,ready", [
    ("installer", True),
    ("shell_override_elsewhere", False),
    ("os_override_elsewhere", True),
    ("shell_override_governed", True),
    ("os_override_governed", True),
    ("inactive_override_elsewhere", True),
    ("wrong_cwd", False),
    ("default_cwd_explicit", False),
    ("timeout_alias", False),
    ("absolute_root_cwd", False),
    ("other_script_with_same_name", False),
])
def test_effective_session_end_controls_cli_handoff_and_verify(installed_consumer, registration, ready):
    repo = installed_consumer
    config = repo / ".github" / "hooks" / "ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    entry = payload["hooks"]["sessionEnd"][0]
    shell_key = "powershell" if sys.platform == "win32" else "bash"
    os_key = {"win32": "windows", "darwin": "osx"}.get(sys.platform, "linux")
    unrelated = "Write-Output done" if sys.platform == "win32" else "echo done"
    if registration == "shell_override_elsewhere":
        entry[shell_key] = unrelated
    elif registration == "os_override_elsewhere":
        entry[os_key] = unrelated
    elif registration == "shell_override_governed":
        entry[shell_key], entry["command"] = entry["command"], unrelated
    elif registration == "os_override_governed":
        entry[os_key] = entry["command"]
    elif registration == "inactive_override_elsewhere":
        entry["bash" if sys.platform == "win32" else "powershell"] = unrelated
    elif registration == "wrong_cwd":
        (repo / "subdir").mkdir()
        entry["cwd"] = "subdir"
    elif registration == "timeout_alias":
        entry["timeout"] = entry["timeoutSec"]
    elif registration == "default_cwd_explicit":
        entry["cwd"] = "."
    elif registration == "absolute_root_cwd":
        entry["cwd"] = str(repo)
    elif registration == "other_script_with_same_name":
        entry[shell_key] = entry["command"].replace(".github/hooks/", "other/")
    if registration != "installer":
        config.write_text(json.dumps(payload), encoding="utf-8")
    register("cli-effective", "github/cli")
    result = copilot_start(repo, "cli-effective")
    assert result["session_envelope_binding"] == "root_bound"
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert ("additionalContext" in result) is ready
    assert verification["cli_session_end"] is ready
    assert verification["vscode_stop"] is (registration != "shell_override_governed")
    assert verification["installed"] is True


@pytest.mark.parametrize("overrides,ready", [
    ({}, True),
    ({"env": {}}, False),
    ({"env": {"PATHEXT": ".COM"}}, False),
    ({"env": {"REVIEW_LABEL": "team"}}, False),
    ({"env": None}, False),
], ids=["installer", "empty-env", "pathext", "review-label", "null-env"])
def test_cli_session_end_environment_controls_handoff_and_verify(installed_consumer, overrides, ready):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["hooks"]["sessionEnd"][0].update(overrides)
    config.write_text(json.dumps(payload), encoding="utf-8")
    register("cli-env", "github/cli")
    assert ("additionalContext" in copilot_start(repo, "cli-env")) is ready
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["cli_session_end"] is ready
    assert verification["vscode_stop"] is True
    assert validate_hook_install(repo, FRAMEWORK).checks["copilot_session_end_hooks_governed"] is True


def test_session_start_review_label_withholds_cli_id_only(installed_consumer):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["hooks"]["sessionStart"][0]["env"] = {"REVIEW_LABEL": "team"}
    config.write_text(json.dumps(payload), encoding="utf-8")
    register("cli-start-env", "github/cli")
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["vscode_stop"] is True
    assert verification["cli_session_end"] is True
    assert "additionalContext" not in copilot_start(repo, "cli-start-env")
    assert validate_hook_install(repo, FRAMEWORK).checks["copilot_session_end_hooks_governed"] is True


@pytest.mark.parametrize("event,start_ready,end_ready", [
    ("errorOccurred", True, True), ("futureEvent", True, True),
    ("SessionStart", False, True), ("SessionEnd", True, False),
])
def test_cli_registration_keeps_other_events_independent(installed_consumer, event, start_ready, end_ready):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    canonical = event[0].lower() + event[1:]
    payload["hooks"][event] = payload["hooks"].get(canonical, [{"type": "command", "command": "echo done"}])
    config.write_text(json.dumps(payload), encoding="utf-8")
    register("cli-extra-event", "github/cli")
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["vscode_stop"] is False
    assert verification["cli_session_end"] is end_ready
    assert ("additionalContext" in copilot_start(repo, "cli-extra-event")) is (start_ready and end_ready)
    assert validate_hook_install(repo, FRAMEWORK).checks["copilot_session_end_hooks_governed"] is False


def test_cli_handoff_does_not_read_vscode_config(installed_consumer, monkeypatch):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-vscode.json"
    read_text = Path.read_text
    reads = 0

    def vanishes_on_second_read(path, *args, **kwargs):
        nonlocal reads
        if path == config:
            reads += 1
            if reads == 2:
                raise FileNotFoundError(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", vanishes_on_second_read)
    register("cli-vscode-race", "github/cli")
    assert "cli-vscode-race" in copilot_start(repo, "cli-vscode-race")["additionalContext"]
    assert reads == 0
    assert copilot_closeout_wiring(repo)["vscode_stop"] is True
    assert reads == 1


@pytest.mark.parametrize("filename", ["ai-governance-copilot.json", "ai-governance-lifecycle.py"])
def test_cli_handoff_fails_closed_on_unreadable_wiring(installed_consumer, monkeypatch, filename):
    repo = installed_consumer
    target = repo / ".github/hooks" / filename
    read_text = Path.read_text

    def permission_denied(path, *args, **kwargs):
        if path == target:
            raise PermissionError(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", permission_denied)
    register("cli-unreadable", "github/cli")
    assert "additionalContext" not in copilot_start(repo, "cli-unreadable")
    assert CopilotAdapter().verify(repo, FRAMEWORK)["cli_session_end"] is False


def test_vscode_wiring_unreadable_does_not_change_cli_readiness(installed_consumer, monkeypatch):
    config = installed_consumer / ".github/hooks/ai-governance-vscode.json"
    read_text = Path.read_text

    def file_disappeared(path, *args, **kwargs):
        if path == config:
            raise FileNotFoundError(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", file_disappeared)
    result = CopilotAdapter().verify(installed_consumer, FRAMEWORK)
    assert result["vscode_stop"] is False and result["cli_session_end"] is True


@pytest.mark.parametrize("record", ["matching", "unknown_client", "missing", "other_session"])
def test_resumed_cli_identity_requires_current_start_verification(installed_consumer, record):
    repo = installed_consumer
    workspace = register("cli-resume", "github/cli")
    first = copilot_start(repo, "cli-resume")
    assert "cli-resume" in first["additionalContext"]
    before = envelope_path(repo, "cli-resume").read_bytes()
    if record == "unknown_client":
        register("cli-resume", "some-other-host")
    elif record == "missing":
        workspace.unlink()
    elif record == "other_session":
        register("cli-resume", "github/cli", record_id="someone-else")
    again = _run_installed(repo, {"sessionId": "cli-resume", "hookEventName": "sessionStart",
                                  "cwd": str(repo), "source": "resume"})
    assert again["status"] == "session_envelope_preserved"
    if record == "matching":
        assert again["additionalContext"] == first["additionalContext"]
    else:
        assert "additionalContext" not in again
    assert envelope_path(repo, "cli-resume").read_bytes() == before


def test_resumed_cli_identity_is_not_handed_to_a_different_verified_provider(installed_consumer):
    repo = installed_consumer
    register("cli-mismatch", "github/cli")
    assert "additionalContext" in copilot_start(repo, "cli-mismatch")
    before = envelope_path(repo, "cli-mismatch").read_bytes()
    register("cli-mismatch", "vscode-agent-host")
    result = _run_installed(repo, {"sessionId": "cli-mismatch", "hookEventName": "sessionStart",
                                  "cwd": str(repo), "source": "resume"})
    assert result["ok"] is False and result["status"] == "bridge_error"
    assert "additionalContext" not in result
    assert envelope_path(repo, "cli-mismatch").read_bytes() == before


@pytest.mark.parametrize("client,provider", [
    ("vscode-agent-host", "github-copilot-vscode"), ("github/cli", "github-copilot"),
])
def test_legacy_copilot_identity_gets_no_session_id_context(repo, client, provider):
    register("legacy", client)
    core.write_session_envelope("legacy", repo, provider=provider)  # 1.0
    result = copilot_start(repo, "legacy")
    assert result["session_envelope_binding"] == "legacy"
    assert "additionalContext" not in result


@pytest.mark.parametrize("provider,binding", [
    ("unknown", "root_bound"), ("codex", "root_bound"), (None, "root_bound"),
    ("github-copilot", "legacy"), ("github-copilot-vscode", "legacy"),
])
def test_other_providers_and_unbound_identities_receive_no_context(provider, binding):
    assert _session_id_context(
        {"provider": provider, "session_envelope_binding": binding}, verified_provider=provider,
    ) == {}


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


def test_installed_cli_entry_prints_its_id_and_session_end_context(installed_consumer):
    register("cli-installed", "github/cli")
    result = _run_installed(installed_consumer, {"sessionId": "cli-installed", "hookEventName": "sessionStart",
                                                 "cwd": str(installed_consumer)})
    assert result["ok"] is True and result["provider"] == "github-copilot", result
    assert result["session_envelope_binding"] == "root_bound"
    assert "cli-installed" in result["additionalContext"]
    assert "CLI sessionEnd hook" in result["additionalContext"]
    assert "when the session ends (not after the turn)" in result["additionalContext"]


@pytest.mark.parametrize("wiring", ["missing", "wrong_event"])
def test_installed_cli_without_governed_session_end_has_no_context(installed_consumer, wiring):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    data = json.loads(config.read_text(encoding="utf-8"))
    if wiring == "missing":
        del data["hooks"]["sessionEnd"]
    else:
        data["hooks"]["sessionEnd"] = data["hooks"]["sessionStart"]
    config.write_text(json.dumps(data), encoding="utf-8")
    register("cli-start-only", "github/cli")
    result = _run_installed(repo, {"sessionId": "cli-start-only", "hookEventName": "sessionStart",
                                  "cwd": str(repo)})
    assert result["ok"] is True and result["provider"] == "github-copilot", result
    assert result["session_envelope_binding"] == "root_bound"
    assert "additionalContext" not in result
    verification = CopilotAdapter().verify(repo, FRAMEWORK)
    assert verification["cli_session_end"] is False
    assert verification["vscode_stop"] is False and verification["installed"] is False
    assert "VS Code Copilot Stop (agent_stop): not installed" in verification["note"]
    assert "Copilot CLI sessionEnd (lifecycle bridge): not installed" in verification["note"]


@pytest.mark.parametrize("client", [None, "some-other-host"])
def test_installed_entry_failure_prints_no_context(installed_consumer, client):
    if client is not None:
        register("vs-missing", client)
    result = _run_installed(installed_consumer, {"sessionId": "vs-missing", "hookEventName": "sessionStart",
                                                 "cwd": str(installed_consumer)})
    assert result["ok"] is False and result["status"] == "bridge_error"
    assert "additionalContext" not in result


# ── verify reports each Copilot execution point on its own ─────────────────────

# Frozen VS Code verdicts from 10bd1f09's copilot_closeout_wiring, with the
# official bridge and Stop config. These expectations also work in shallow clones.
@pytest.mark.parametrize("event,override,ready", [
    (None, {}, True),
    ("sessionEnd", None, False),
    ("sessionStart", {"powershell": "Write-Output done"}, True),
    ("sessionEnd", {"powershell": "Write-Output done"}, True),
    ("sessionStart", {"windows": "Write-Output done"}, True),
    ("sessionEnd", {"env": {"PATHEXT": ".COM"}}, True),
    ("sessionStart", {"env": {"REVIEW_LABEL": "team"}}, True),
    ("sessionEnd", {"timeoutSec": "30"}, True),
    (None, {"disableAllHooks": True}, True),
    ("errorOccurred", [{"type": "command", "command": "echo done"}], False),
    ("preToolUse", [{"type": "command"}], False),
    ("preToolUse", {}, False),
], ids=["installer", "missing-end", "powershell-start", "powershell-end", "windows-start",
        "env-end", "env-start", "string-timeout", "disabled", "extra-event", "bad-item", "bad-array"])
def test_vscode_verify_matches_10bd1f09(installed_consumer, monkeypatch, event, override, ready):
    monkeypatch.setattr(hook_install_validator, "sys", SimpleNamespace(platform="win32"))
    config = installed_consumer / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    if event is None:
        payload.update(override)
    elif override is None:
        del payload["hooks"][event]
    elif event in payload["hooks"]:
        payload["hooks"][event][0].update(override)
    else:
        payload["hooks"][event] = override
    config.write_text(json.dumps(payload), encoding="utf-8")
    assert CopilotAdapter().verify(installed_consumer, FRAMEWORK)["vscode_stop"] is ready
    assert copilot_closeout_wiring(installed_consumer)["shared_registration_governed"] is ready


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


def test_verify_without_the_vscode_stop_reports_cli_closeout_at_session_end(installed_consumer):
    config = installed_consumer / ".github/hooks/ai-governance-vscode.json"
    config.write_text(json.dumps({"version": 1, "hooks": {"Stop": [{"type": "command", "command": "echo hi"}]}}),
                      encoding="utf-8")
    result = CopilotAdapter().verify(installed_consumer, FRAMEWORK)
    assert result["vscode_stop"] is False and result["cli_session_end"] is True
    assert result["installed"] is True  # the CLI sessionEnd is still wired
    assert "VS Code Copilot Stop (agent_stop): not installed" in result["note"]
    assert "a prepared CLI session's closeout is left to this hook at sessionEnd" in result["note"]
    assert "when the CLI session ends (not after the turn)" in result["note"]
    assert _PENDING_HOOK_NOTE not in result["note"]
    register("cli-only", "github/cli")
    assert "cli-only" in copilot_start(installed_consumer, "cli-only")["additionalContext"]


def test_verify_without_shared_session_start_still_recognizes_cli_session_end(installed_consumer):
    repo = installed_consumer
    config = repo / ".github/hooks/ai-governance-copilot.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    del payload["hooks"]["sessionStart"]
    config.write_text(json.dumps(payload), encoding="utf-8")
    result = CopilotAdapter().verify(repo, FRAMEWORK)
    assert result["vscode_stop"] is False
    assert result["cli_session_end"] is True and result["installed"] is True
    register("cli-end-only", "github/cli")
    assert "additionalContext" not in copilot_start(repo, "cli-end-only")


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
    checks = validate_hook_install(installed_consumer, FRAMEWORK).checks
    wiring = copilot_closeout_wiring(installed_consumer)
    assert checks["copilot_session_end_hooks_governed"] is wiring["cli_session_end"] is True
    assert checks["copilot_vscode_hooks_governed"] is True and wiring["vscode_stop"] is True


# ── guidance: the hook gives both clients their id; execution points differ ────

GUIDANCE = ["AGENTS.base.md", "baselines/repo-min/AGENTS.base.md",
            "governance/agent-contract-template.md", "governance/copilot-instructions-template.md"]


@pytest.mark.parametrize("rel", GUIDANCE)
def test_guidance_names_both_copilot_id_sources_and_their_closeout_events(rel):
    text = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
    assert ("in VS Code Copilot or Copilot CLI, the id that the governed SessionStart hook adds to the conversation as "
            "`additionalContext`") in text
    assert "the Codex Stop hook and the VS Code Copilot Stop hook" in text
    assert "and the Copilot CLI sessionEnd hook" in text
    assert ("A Copilot CLI session receives its id from the SessionStart hook only when the current start "
            "verifies its CLI identity and the governed sessionEnd hook is installed") in text
    assert "its sessionEnd hook closes out a prepared session when the session ends (not after the turn)" in text
    assert "Without that id, report the closeout as not persisted" in text
    assert "loads repository hooks only with persistent folder trust" in text
    assert "`--trust-folder` cannot be combined with `--resume`" in text
    assert "never take an id from `artifacts/runtime/.current-session-id`" in text
    assert "given no session id" not in text and "does not prepare" not in text
    assert "is rejected and its closeout" not in text and "is rejected: report" not in text
    assert "today only the Codex Stop hook" not in text
    assert "RELEASE_PROOF_INVALID" in text  # the refused manual fallback stays named
