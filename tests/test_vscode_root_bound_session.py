"""VS Code root-bound session identity: own provider identity, worktree binding, no Codex disguise."""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from runtime_hooks.adapters.codex.session_start import run as codex_start
from runtime_hooks.adapters.copilot.lifecycle import run_lifecycle_event
from runtime_hooks.core import _canonical_closeout as core

SID = "vscode-session-a"


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "core.hooksPath=NUL", *args],
        check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "consumer vscode"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    git(root, "commit", "--allow-empty", "-qm", "fixture")
    return root.resolve()


def vscode_start(root, sid=SID, surface="vscode"):
    payload = {"session_id": sid, "cwd": str(root), "hook_event_name": "SessionStart"}
    return run_lifecycle_event(payload, event_type="session_start", surface=surface)


def envelope_path(root, sid=SID):
    return root / "artifacts/runtime/sessions" / sid / "session-envelope.json"


def write_summary(root, sid=SID):
    (root / "evidence.txt").write_text("fixture evidence", encoding="utf-8")
    candidate = dict(task_intent="Inspect VS Code binding", work_summary="Inspected evidence.txt",
                     tools_used=["inspect"], artifacts_referenced=["evidence.txt"], open_risks=[])
    core.write_candidate(sid, root, candidate)
    text = root / "artifacts/session-closeout.txt"
    text.write_text("TASK_INTENT: Inspect VS Code binding\nWORK_COMPLETED: Inspected evidence.txt\n"
                    "FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n"
                    "NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n", encoding="utf-8")
    envelope = core.read_session_envelope(sid, root)
    later = datetime.fromisoformat(envelope["started_at"]).timestamp() + 1
    os.utime(text, (later, later))
    return candidate


def test_vscode_start_is_bound_with_real_vscode_identity(repo):
    result = vscode_start(repo)
    assert result["ok"] and result["status"] == "session_envelope_written"
    assert result["session_envelope_binding"] == "root_bound"
    payload = json.loads(envelope_path(repo).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.1"
    assert payload["provider"] == "github-copilot-vscode"
    assert payload["repo_binding"] == {"consumer_root": str(repo), "source": "vscode_session_start"}
    assert core.read_session_envelope(SID, repo) is not None


def test_repeated_vscode_start_preserves_identity_bytes(repo):
    vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    again = vscode_start(repo)
    assert again["ok"] and again["status"] == "session_envelope_preserved"
    assert envelope_path(repo).read_bytes() == before


def test_existing_legacy_vscode_envelope_is_never_migrated(repo):
    core.write_session_envelope(SID, repo, provider="github-copilot-vscode")
    before = envelope_path(repo).read_bytes()
    result = vscode_start(repo)
    assert result["ok"] and result["session_envelope_binding"] == "legacy"
    assert envelope_path(repo).read_bytes() == before


def test_copilot_cli_surface_stays_legacy(repo):
    result = vscode_start(repo, sid="cli-session", surface="copilot")
    assert result["ok"] and result["session_envelope_binding"] == "legacy"
    assert json.loads(envelope_path(repo, "cli-session").read_text())["schema_version"] == "1.0"


def test_unbindable_session_id_fails_closed_without_legacy_fallback(repo):
    result = vscode_start_safe(repo, "dotted.session")
    assert result is None
    assert not (repo / "artifacts/runtime/sessions/dotted.session").exists()


def vscode_start_safe(root, sid):
    try:
        vscode_start(root, sid)
    except ValueError:
        return None
    return "started"


def test_subdirectory_workspace_fails_closed(repo):
    sub = repo / "sub"
    sub.mkdir()
    with pytest.raises(ValueError, match="do not match"):
        vscode_start(sub)
    assert not (repo / "artifacts").exists() and not (sub / "artifacts").exists()


@pytest.mark.parametrize("provider,source", [
    ("codex", "vscode_session_start"),
    ("github-copilot-vscode", "codex_session_start"),
    ("github-copilot", "vscode_session_start"),
    ("github-copilot", "codex_session_start"),
])
def test_reader_rejects_provider_source_mismatch(repo, provider, source):
    vscode_start(repo)
    path = envelope_path(repo)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provider"] = provider
    payload["repo_binding"]["source"] = source
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope(SID, repo) is None


def test_vscode_provider_cannot_be_written_as_codex_and_vice_versa(repo):
    for provider in ("claude", "github-copilot", "unknown"):
        with pytest.raises(ValueError, match="Codex or VS Code"):
            core.write_session_envelope("x-" + provider, repo, provider=provider, bound_consumer_root=repo)
    codex_start(dict(hook_event_name="SessionStart", source="startup", session_id="codex-a", cwd=str(repo)), repo)
    payload = json.loads(envelope_path(repo, "codex-a").read_text())
    assert payload["provider"] == "codex"
    assert payload["repo_binding"]["source"] == "codex_session_start"


def test_vscode_start_cannot_adopt_a_codex_session_identity(repo):
    codex_start(dict(hook_event_name="SessionStart", source="startup", session_id="codex-a", cwd=str(repo)), repo)
    before = envelope_path(repo, "codex-a").read_bytes()
    pointer = repo / "artifacts/runtime/.current-session-id"
    pointer_before = pointer.read_bytes() if pointer.exists() else None
    with pytest.raises(ValueError, match="another provider"):
        vscode_start(repo, sid="codex-a")
    assert envelope_path(repo, "codex-a").read_bytes() == before
    assert (pointer.read_bytes() if pointer.exists() else None) == pointer_before


def test_codex_start_cannot_adopt_a_vscode_session_identity(repo):
    vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    with pytest.raises(ValueError, match="another provider"):
        codex_start(dict(hook_event_name="SessionStart", source="startup", session_id=SID, cwd=str(repo)), repo)
    assert envelope_path(repo).read_bytes() == before


def test_codex_hook_reports_non_git_cwd_as_system_message(tmp_path, monkeypatch, capsys):
    import io
    from runtime_hooks.adapters.codex import session_start as codex_hook
    elsewhere = tmp_path / "not a repo"
    elsewhere.mkdir()
    payload = dict(hook_event_name="SessionStart", source="startup", session_id="codex-a", cwd=str(elsewhere))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr("sys.argv", ["session_start.py", "--project-root", str(elsewhere)])
    assert codex_hook.main() == 1
    assert "Governance SessionStart failed" in json.loads(capsys.readouterr().out)["systemMessage"]


def test_vscode_start_works_in_non_ascii_project_path_without_utf8_mode(tmp_path):
    root = tmp_path / "專案 consumer"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    git(root, "commit", "--allow-empty", "-qm", "fixture")
    code = (
        "import json, sys\n"
        "from runtime_hooks.adapters.copilot.lifecycle import run_lifecycle_event\n"
        "root = sys.argv[1]\n"
        "r = run_lifecycle_event({'session_id': 'cjk-a', 'cwd': root, 'hook_event_name': 'SessionStart'},"
        " event_type='session_start', surface='vscode')\n"
        "print(json.dumps({'ok': r['ok'], 'binding': r['session_envelope_binding']}))\n"
    )
    env = {**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run([sys.executable, "-c", code, str(root)], env=env, cwd=Path(__file__).parents[1],
                          capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {"ok": True, "binding": "root_bound"}


def test_git_toplevel_decodes_utf8_regardless_of_console_codepage(repo, monkeypatch):
    from runtime_hooks.core import _bound_session_start as bound
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout=str(repo) + "\n", stderr="")

    monkeypatch.setattr(bound.subprocess, "run", fake_run)
    assert bound.git_toplevel(str(repo)) == repo
    assert seen.get("encoding") == "utf-8"


def test_codex_and_vscode_identities_are_not_interchangeable(repo):
    vscode_start(repo)
    path = envelope_path(repo)
    payload = json.loads(path.read_text())
    payload["provider"] = "codex"  # relabel without changing the source
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope(SID, repo) is None


def test_vscode_session_closeout_saves_summary_for_own_session(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    candidate = write_summary(repo)
    result = run_session_end_hook(repo, hook_session_id=SID, ledger_write_allowed=False)
    assert result["session_binding"]["status"] == "valid"
    assert result["closeout_status"] == "valid"
    canonical = json.loads((repo / f"artifacts/runtime/closeouts/{SID}.json").read_text())
    assert canonical["task_intent"] == candidate["task_intent"]
    assert canonical["work_summary"] == candidate["work_summary"]
    assert envelope_path(repo).read_bytes() == before


def test_missing_summary_keeps_failure_state(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    vscode_start(repo)
    result = run_session_end_hook(repo, hook_session_id=SID, ledger_write_allowed=False)
    assert result["closeout_status"] == "closeout_missing" and result["decision"] == "DO_NOT_PROMOTE"
    assert result["session_binding"]["status"] == "session_candidate_missing"
    recorded = json.loads((repo / f"artifacts/runtime/closeouts/{SID}.json").read_text())
    assert recorded["closeout_status"] == "missing" and recorded["work_summary"] is None


def test_other_session_summary_is_rejected(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    vscode_start(repo, "vscode-session-a")
    vscode_start(repo, "vscode-session-b")
    write_summary(repo, "vscode-session-a")
    result = run_session_end_hook(repo, hook_session_id="vscode-session-b", ledger_write_allowed=False)
    assert result["closeout_status"] != "valid"
    assert result["session_binding"]["status"] != "valid"
    recorded = json.loads((repo / "artifacts/runtime/closeouts/vscode-session-b.json").read_text())
    assert recorded["closeout_status"] == "missing" and recorded["work_summary"] is None
    assert not (repo / "artifacts/runtime/closeouts/vscode-session-a.json").exists()


def test_copied_vscode_identity_is_rejected_in_other_worktree(repo, tmp_path):
    vscode_start(repo)
    other = tmp_path / "other-worktree"
    git(repo, "worktree", "add", "--detach", str(other))
    copied = envelope_path(other)
    copied.parent.mkdir(parents=True)
    copied.write_bytes(envelope_path(repo).read_bytes())
    assert core.read_session_envelope(SID, other) is None
    before = copied.read_bytes()
    result = vscode_start_result(other)
    assert result["ok"] is False
    assert copied.read_bytes() == before
    assert not (other / "artifacts/runtime/.current-session-id").exists()


def vscode_start_result(root):
    try:
        return vscode_start(root)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


# ── installed bridge: independent anchor, older framework, formal install entry ──

FRAMEWORK = Path(__file__).resolve().parents[1]
BRIDGE_SOURCE = FRAMEWORK / "runtime_hooks/adapters/copilot/lifecycle.py"
INSTALLED_BRIDGE = Path(".github/hooks/ai-governance-lifecycle.py")
LOCAL_HARNESS_PAYLOAD = {"hook_event_name": "SessionStart", "source": "new",
                         "timestamp": "2026-10-22T03:00:00.000Z"}


def _clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("GIT_") and k != "AI_GOVERNANCE_FRAMEWORK_ROOT"}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


def _install_bridge(root):
    (root / INSTALLED_BRIDGE).parent.mkdir(parents=True, exist_ok=True)
    (root / INSTALLED_BRIDGE).write_bytes(BRIDGE_SOURCE.read_bytes())


def _run_bridge(bridge, payload, *, cwd, framework=FRAMEWORK):
    done = subprocess.run([sys.executable, "-B", str(bridge), "--event-type", "session_start",
                           "--surface", "auto"], input=json.dumps(payload), cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", timeout=120,
                          env=_clean_env(AI_GOVERNANCE_FRAMEWORK_ROOT=str(framework)))
    return json.loads(done.stdout)


def _runtime(root):
    base = root / "artifacts"
    return sorted(p.relative_to(root).as_posix() for p in base.rglob("*")) if base.exists() else []


def test_installed_bridge_binds_its_own_root(repo):
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(repo)}, cwd=repo)
    assert result["ok"] is True, result
    assert result["session_envelope_binding"] == "root_bound"
    assert core.read_session_envelope(SID, repo)["repo_binding"]["consumer_root"] == str(repo)


def test_installed_bridge_rejects_payload_cwd_of_another_repo(repo, tmp_path):
    """The installed copy, not the payload, decides which root may be bound."""
    other = tmp_path / "other repo"
    subprocess.run(["git", "init", "--quiet", str(other)], check=True)
    other = other.resolve()
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(other)}, cwd=repo)
    assert result["ok"] is False and "do not match" in result["error"]
    assert _runtime(repo) == [] and _runtime(other) == []


_OLDER_CORE = '''
import json
from datetime import datetime, timezone


def write_session_envelope(session_id, project_root, *, provider="unknown", **_):
    path = project_root / "artifacts/runtime/sessions" / session_id / "session-envelope.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "1.0", "session_id": session_id, "provider": provider,
               "started_at": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {**payload, "artifact_path": str(path)}
'''


def test_bridge_newer_than_framework_keeps_legacy_envelope(repo, tmp_path):
    """Reader before writer: an older framework cannot read a VS Code v1.1
    envelope, so the bridge keeps that framework's legacy path instead of
    failing with no envelope."""
    older = tmp_path / "older framework"
    (older / "runtime_hooks/core").mkdir(parents=True)
    (older / "runtime_hooks/core/_canonical_closeout.py").write_text(_OLDER_CORE, encoding="utf-8")
    (older / "governance_tools").mkdir()
    (older / "governance_tools/session_end_hook.py").write_text("", encoding="utf-8")
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(repo)},
                         cwd=repo, framework=older)
    assert result["ok"] is True, result
    assert result["session_envelope_binding"] == "legacy"
    assert result["session_envelope_binding_reason"] == "framework_without_root_bound_support"
    assert json.loads(envelope_path(repo).read_bytes())["schema_version"] == "1.0"


@pytest.fixture
def installed_consumer(tmp_path):
    """A consumer set up by the real installer CLI, as a user would run it."""
    root = tmp_path / "installed consumer"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    done = subprocess.run(
        [sys.executable, "-m", "governance_tools.hook_installer", "--repo", str(root),
         "--framework-root", str(FRAMEWORK), "--repository-id", "example/installed-consumer"],
        cwd=FRAMEWORK, capture_output=True, text=True, encoding="utf-8", timeout=120,
        env=_clean_env(),
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return root.resolve()


def _installed_session_start_command(root):
    config = json.loads((root / ".github/hooks/ai-governance-copilot.json").read_text(encoding="utf-8"))
    (entry,) = config["hooks"]["sessionStart"]
    return entry["command"]


def _run_installed(root, payload):
    """Run the configured command verbatim; the framework is found only through
    what the installer configured (no AI_GOVERNANCE_FRAMEWORK_ROOT)."""
    env = _clean_env()
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    done = subprocess.run(_installed_session_start_command(root), shell=True, cwd=root,
                          input=json.dumps(payload), capture_output=True, text=True,
                          encoding="utf-8", timeout=120, env=env)
    return json.loads(done.stdout)


def test_installer_wires_session_start_through_the_bridge(installed_consumer):
    assert _installed_session_start_command(installed_consumer) == (
        "python .github/hooks/ai-governance-lifecycle.py --event-type session_start --surface auto")
    assert (installed_consumer / INSTALLED_BRIDGE).is_file()


def test_installed_entry_local_harness_payload_is_root_bound(installed_consumer):
    """VS Code Local maps the Copilot-format config and sends its own snake_case
    payload (code.visualstudio.com/docs/agents/reference/hooks-reference)."""
    from governance_tools import shared_closeout_ownership as ownership

    result = _run_installed(installed_consumer, {**LOCAL_HARNESS_PAYLOAD, "session_id": "vscode-local",
                                                 "cwd": str(installed_consumer)})
    assert result["ok"] is True, result
    assert (result["surface"], result["session_envelope_binding"]) == ("vscode", "root_bound")
    assert Path(result["framework_root"]).resolve() == FRAMEWORK.resolve()
    ownership._identity(installed_consumer, "vscode-local")  # prepare's identity preflight


def test_installed_entry_copilot_harness_payload_is_not_root_bound(installed_consumer):
    """VS Code's Copilot harness sends the camelCase Copilot payload: copilot
    surface, unbound, cannot prepare a summary.  Binding it is not approved."""
    from governance_tools import shared_closeout_ownership as ownership

    result = _run_installed(installed_consumer, {"sessionId": "copilot-harness",
                                                 "hookEventName": "sessionStart",
                                                 "cwd": str(installed_consumer)})
    assert result["ok"] is True, result
    assert (result["surface"], result["provider"]) == ("copilot", "github-copilot")
    assert result["session_envelope_binding"] == "legacy"
    with pytest.raises(ownership.OwnershipError, match="INVALID_OWNER"):
        ownership._identity(installed_consumer, "copilot-harness")


# ── same SessionStart payload rules as Codex (review on main@fea3e918) ──────

@pytest.mark.parametrize("event", ["Stop", "UserPromptSubmit", "", None])
def test_only_a_session_start_event_establishes_identity(repo, event):
    payload = {"session_id": SID, "cwd": str(repo), "hook_event_name": event}
    payload = {k: v for k, v in payload.items() if v is not None}
    with pytest.raises(ValueError, match="SessionStart"):
        run_lifecycle_event(payload, event_type="session_start", surface="vscode")
    assert _runtime(repo) == []


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_resume_or_compact_never_invents_an_identity(repo, source):
    payload = {"session_id": SID, "cwd": str(repo), "hook_event_name": "SessionStart",
               "source": source}
    with pytest.raises(ValueError, match="no start time invented"):
        run_lifecycle_event(payload, event_type="session_start", surface="vscode")
    assert _runtime(repo) == []


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_resume_or_compact_preserves_an_existing_identity(repo, source):
    first = vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    again = run_lifecycle_event({"session_id": SID, "cwd": str(repo), "hook_event_name": "SessionStart",
                                 "source": source}, event_type="session_start", surface="vscode")
    assert again["status"] == "session_envelope_preserved"
    assert envelope_path(repo).read_bytes() == before
    assert again["session_envelope_path"] == first["session_envelope_path"]


# ── the legacy fallback covers only a missing framework API (second review) ──

def _older_framework(tmp_path):
    older = tmp_path / "older framework"
    (older / "runtime_hooks/core").mkdir(parents=True)
    (older / "runtime_hooks/core/_canonical_closeout.py").write_text(_OLDER_CORE, encoding="utf-8")
    (older / "governance_tools").mkdir()
    (older / "governance_tools/session_end_hook.py").write_text("", encoding="utf-8")
    return older


def test_older_framework_does_not_downgrade_a_foreign_project(repo, tmp_path):
    other = tmp_path / "other repo"
    subprocess.run(["git", "init", "--quiet", str(other)], check=True)
    other = other.resolve()
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(other)},
                         cwd=repo, framework=_older_framework(tmp_path))
    assert result["ok"] is False and "do not match" in result["error"]
    assert _runtime(repo) == [] and _runtime(other) == []


@pytest.mark.parametrize("event", ["Stop", None])
def test_older_framework_does_not_downgrade_a_wrong_event(repo, tmp_path, event):
    _install_bridge(repo)
    payload = {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(repo), "hook_event_name": event}
    payload = {k: v for k, v in payload.items() if v is not None}
    result = _run_bridge(repo / INSTALLED_BRIDGE, payload, cwd=repo, framework=_older_framework(tmp_path))
    assert result["ok"] is False and "SessionStart" in result["error"]
    assert _runtime(repo) == []


def test_installed_bridge_subdirectory_cwd_fails_closed(repo):
    """Same as for payload-derived roots (#227): the cwd must be the root itself."""
    sub = repo / "src"
    sub.mkdir()
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(sub)}, cwd=repo)
    assert result["ok"] is False and "do not match" in result["error"]
    assert _runtime(repo) == []


# ── legacy fallback keeps the identity rules; only a missing module downgrades ──

def _legacy_envelope(root, provider="github-copilot-vscode", sid=SID):
    path = envelope_path(root, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "1.0", "session_id": sid, "provider": provider,
                                "started_at": "2026-10-01T00:00:00+00:00"}), encoding="utf-8")
    return path.read_bytes()


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_older_framework_resume_without_identity_is_refused(repo, tmp_path, source):
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "source": source, "session_id": SID, "cwd": str(repo)},
                         cwd=repo, framework=_older_framework(tmp_path))
    assert result["ok"] is False and "no start time invented" in result["error"]
    assert _runtime(repo) == []


@pytest.mark.parametrize("source", ["new", "resume"])
def test_older_framework_preserves_an_existing_identity(repo, tmp_path, source):
    before = _legacy_envelope(repo)
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "source": source, "session_id": SID, "cwd": str(repo)},
                         cwd=repo, framework=_older_framework(tmp_path))
    assert result["ok"] is True, result
    assert result["status"] == "session_envelope_preserved"
    assert result["session_envelope_binding_reason"] == "framework_without_root_bound_support"
    assert envelope_path(repo).read_bytes() == before  # not rewritten with a new start time


def test_older_framework_does_not_adopt_another_providers_identity(repo, tmp_path):
    before = _legacy_envelope(repo, provider="codex")
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(repo)},
                         cwd=repo, framework=_older_framework(tmp_path))
    assert result["ok"] is False and "another provider" in result["error"]
    assert envelope_path(repo).read_bytes() == before


@pytest.mark.parametrize("module_source, expected", [
    ("import governance_nonexistent_dependency_xyz\n", "governance_nonexistent_dependency_xyz"),
    ("VALUE = 1\n", "establish_bound_session"),
])
def test_broken_root_bound_module_is_an_error_not_a_downgrade(repo, tmp_path, module_source, expected):
    """Only an absent _bound_session_start means "framework too old"."""
    framework = _older_framework(tmp_path)
    (framework / "runtime_hooks/core/_bound_session_start.py").write_text(module_source, encoding="utf-8")
    _install_bridge(repo)
    result = _run_bridge(repo / INSTALLED_BRIDGE,
                         {**LOCAL_HARNESS_PAYLOAD, "session_id": SID, "cwd": str(repo)},
                         cwd=repo, framework=framework)
    assert result["ok"] is False and expected in result["error"]
    assert _runtime(repo) == []
