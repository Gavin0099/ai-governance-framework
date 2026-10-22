"""VS Code root-bound session identity and summary preparation (#225).

The VS Code bridge is exercised the way it really runs: installed as
<consumer>/.github/hooks/ai-governance-lifecycle.py and fed a SessionStart
payload on stdin.  Summary preparation goes through the formal
prepare_closeout_candidate entry in a committed submodule consumer, reusing the
fixtures of test_prepare_closeout_candidate.

Acceptance (issue #225):
  - the right VS Code session can prepare its summary
  - another session cannot
  - an envelope + summary copied to another worktree is rejected
  - a missing summary stays a failure
  - Codex protections hold (covered by the existing Codex suites)
  - a legacy v1.0 VS Code envelope is rejected and never migrated
  - provider/source relabelling is rejected
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from runtime_hooks.core import _canonical_closeout as core
from tests.test_prepare_closeout_candidate import (
    INPUT, SOURCES, SUBMODULE, environment, git, invoke, owner, runtime_bytes,
)

FRAMEWORK = Path(__file__).resolve().parents[1]
BRIDGE_SOURCE = "runtime_hooks/adapters/copilot/lifecycle.py"
INSTALLED_BRIDGE = Path(".github/hooks/ai-governance-lifecycle.py")
# lifecycle.resolve_framework_root() recognises a framework by these files.
VSCODE_SOURCES = [*SOURCES, BRIDGE_SOURCE, "governance_tools/session_end_hook.py"]
PROVIDER = "github-copilot-vscode"


def _envelope_path(root: Path, sid: str) -> Path:
    return root / "artifacts/runtime/sessions" / sid / "session-envelope.json"


def _start(root: Path, sid: str = "vscode-A", *, framework: Path, bridge: Path | None = None,
           **overrides) -> dict:
    payload = {"hook_event_name": "SessionStart", "session_id": sid, "cwd": str(root),
               "transcript_path": str(root / "transcript.jsonl"), **overrides}
    payload = {k: v for k, v in payload.items() if v is not None}
    result = subprocess.run(
        [sys.executable, "-B", str(bridge or root / INSTALLED_BRIDGE),
         "--event-type", "session_start", "--surface", "auto"],
        input=json.dumps(payload), cwd=root, capture_output=True, text=True,
        encoding="utf-8", timeout=60,
        env={**environment(), "AI_GOVERNANCE_FRAMEWORK_ROOT": str(framework)},
    )
    return json.loads(result.stdout)


# ── committed submodule consumer (formal prepare entry) ─────────────────────

@pytest.fixture(scope="module")
def framework_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("vscode-preparation-source")
    git(root, "init", "--quiet")
    for name in VSCODE_SOURCES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FRAMEWORK / name, root / name)
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "disposable preparation implementation")
    return root


def _make_consumer(root: Path, framework_source: Path) -> Path:
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
        str(framework_source), SUBMODULE)
    (root / "governance").mkdir()
    (root / "governance/framework.lock.json").write_text(
        json.dumps({"adopted_commit": git(root / SUBMODULE, "rev-parse", "HEAD")}), encoding="utf-8")
    (root / "evidence.txt").write_text("fixture evidence", encoding="utf-8")
    (root / INSTALLED_BRIDGE).parent.mkdir(parents=True)
    shutil.copyfile(root / SUBMODULE / BRIDGE_SOURCE, root / INSTALLED_BRIDGE)
    git(root, "add", ".")
    git(root, "commit", "-qm", "registered consumer with VS Code bridge")
    return root.resolve()


@pytest.fixture
def consumer(tmp_path, framework_source):
    return _make_consumer(tmp_path / "vscode consumer", framework_source)


def _start_in(consumer: Path, sid: str = "vscode-A", **overrides) -> dict:
    return _start(consumer, sid, framework=consumer / SUBMODULE, **overrides)


def test_vscode_start_creates_root_bound_identity(consumer):
    result = _start_in(consumer)
    assert result["ok"] is True, result
    assert (result["binding"], result["identity_status"]) == ("root_bound", "created")
    envelope = json.loads(_envelope_path(consumer, "vscode-A").read_bytes())
    assert envelope["schema_version"] == "1.1"
    assert envelope["provider"] == PROVIDER  # real identity, not relabelled as Codex
    assert envelope["repo_binding"] == {"consumer_root": str(consumer),
                                        "source": "vscode_session_start"}
    assert core.read_session_envelope("vscode-A", consumer) is not None
    assert not (consumer / "artifacts/runtime/sessions/vscode-A/.vscode-start.lock").exists()


def test_vscode_session_can_prepare_its_summary(consumer):
    assert _start_in(consumer)["binding"] == "root_bound"
    result = invoke(consumer, sid="vscode-A")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["state"] == owner(consumer)["state"] == "OWNED"
    candidate = json.loads((consumer / report["candidate_identity"]["relative_path"]).read_bytes())
    assert candidate["session_id"] == "vscode-A"
    assert candidate["work_summary"] == INPUT["work_summary"]


def test_repeated_start_preserves_identity(consumer):
    first = _start_in(consumer)
    before = _envelope_path(consumer, "vscode-A").read_bytes()
    again = _start_in(consumer, source="resume")
    assert (again["binding"], again["identity_status"]) == ("root_bound", "preserved")
    assert _envelope_path(consumer, "vscode-A").read_bytes() == before
    assert first["session_envelope_path"] == again["session_envelope_path"]


@pytest.mark.parametrize("other", ["vscode-B", "never-started"])
def test_other_session_cannot_prepare(consumer, other):
    assert _start_in(consumer)["binding"] == "root_bound"
    before = runtime_bytes(consumer)
    result = invoke(consumer, sid=other)
    assert result.returncode == 1, result.stdout
    assert "INVALID_OWNER" in result.stdout
    assert runtime_bytes(consumer) == before


def test_envelope_and_summary_copied_to_other_worktree_are_rejected(consumer, tmp_path):
    assert _start_in(consumer)["binding"] == "root_bound"
    assert invoke(consumer, sid="vscode-A").returncode == 0
    other = tmp_path / "other worktree"
    git(consumer, "worktree", "add", "--quiet", "--detach", str(other))
    git(other, "-c", "protocol.file.allow=always", "submodule", "update", "--init", "--quiet")
    shutil.copytree(consumer / "artifacts", other / "artifacts")
    assert core.read_session_envelope("vscode-A", other.resolve()) is None
    before = runtime_bytes(other)
    result = invoke(other.resolve(), sid="vscode-A", framework=other.resolve() / SUBMODULE)
    assert result.returncode == 1, result.stdout
    assert "INVALID_OWNER" in result.stdout
    assert runtime_bytes(other) == before


@pytest.mark.parametrize("inputs", [{}, {**INPUT, "work_summary": ""},
                                    {k: v for k, v in INPUT.items() if k != "work_summary"}])
def test_missing_summary_stays_a_failure(consumer, inputs):
    assert _start_in(consumer)["binding"] == "root_bound"
    before = runtime_bytes(consumer)
    result = invoke(consumer, sid="vscode-A", inputs=inputs)
    assert result.returncode == 1, result.stdout
    assert json.loads(result.stdout)["status"] == "REJECTED"
    assert not (consumer / "artifacts/runtime/shared-closeout/owner.json").exists()
    assert runtime_bytes(consumer) == before


def test_legacy_vscode_envelope_is_rejected_and_never_migrated(consumer):
    core.write_session_envelope("vscode-A", consumer, provider=PROVIDER)
    legacy = _envelope_path(consumer, "vscode-A").read_bytes()
    assert json.loads(legacy)["schema_version"] == "1.0"
    result = invoke(consumer, sid="vscode-A")
    assert result.returncode == 1 and "INVALID_OWNER" in result.stdout
    restart = _start_in(consumer)
    # Review on #226: a preserved v1.0 identity must not be reported as root-bound.
    assert (restart["binding"], restart["identity_status"], restart["binding_reason"]) == (
        "legacy_unbound", "preserved", "existing_legacy_envelope_preserved")
    assert _envelope_path(consumer, "vscode-A").read_bytes() == legacy  # no migration
    assert invoke(consumer, sid="vscode-A").returncode == 1


# ── bridge-only cases (plain repo; framework from this checkout) ────────────

@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "plain consumer"
    root.mkdir()
    git(root, "init", "--quiet")
    (root / INSTALLED_BRIDGE).parent.mkdir(parents=True)
    shutil.copyfile(FRAMEWORK / BRIDGE_SOURCE, root / INSTALLED_BRIDGE)
    return root.resolve()


def _runtime(root: Path) -> list[str]:
    base = root / "artifacts"
    return sorted(p.relative_to(root).as_posix() for p in base.rglob("*")) if base.exists() else []


def test_cwd_of_another_repo_is_rejected_without_writes(repo, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    git(elsewhere, "init", "--quiet")
    result = _start(repo, framework=FRAMEWORK, cwd=str(elsewhere.resolve()))
    assert result["ok"] is False and "do not match" in result["error"]
    assert _runtime(repo) == [] and _runtime(elsewhere) == []


def test_subdirectory_of_the_installed_repo_is_accepted_like_codex(repo):
    sub = repo / "src"
    sub.mkdir()
    result = _start(repo, framework=FRAMEWORK, cwd=str(sub))
    # git toplevel of src/ is the repo, so a subdirectory of the right repo is accepted
    # exactly as for Codex; what must never pass is a different root.
    assert result["ok"] is True and result["binding"] == "root_bound"
    assert core.read_session_envelope("vscode-A", repo)["repo_binding"]["consumer_root"] == str(repo)


def test_wrong_event_name_is_rejected_without_writes(repo):
    result = _start(repo, framework=FRAMEWORK, hook_event_name="Stop")
    assert result["ok"] is False and "SessionStart" in result["error"]
    assert _runtime(repo) == []


def test_resume_without_identity_is_not_invented(repo):
    result = _start(repo, framework=FRAMEWORK, source="resume")
    assert result["ok"] is False and "no start time invented" in result["error"]
    assert _runtime(repo) == []


def test_completion_without_envelope_is_not_recreated(repo):
    completion = repo / "artifacts/runtime/closeout-completions/vscode-A.json"
    completion.parent.mkdir(parents=True)
    completion.write_text("{}", encoding="utf-8")
    result = _start(repo, framework=FRAMEWORK)
    assert result["ok"] is False and "Completion marker" in result["error"]
    assert not _envelope_path(repo, "vscode-A").exists()


def test_corrupt_envelope_is_not_overwritten(repo):
    path = _envelope_path(repo, "vscode-A")
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")
    result = _start(repo, framework=FRAMEWORK)
    assert result["ok"] is False and "invalid" in result["error"]
    assert path.read_text(encoding="utf-8") == "not json"


@pytest.mark.parametrize("sid, reason", [
    ("vscode.session.1", "session_id_not_root_bound_format"),
    ("_vscode-1", "session_id_not_root_bound_format"),
])
def test_ids_outside_root_bound_format_keep_legacy_behaviour(repo, sid, reason):
    result = _start(repo, sid, framework=FRAMEWORK)
    assert result["ok"] is True
    assert (result["binding"], result["binding_reason"]) == ("legacy_unbound", reason)
    envelope = json.loads(_envelope_path(repo, sid).read_bytes())
    assert envelope["schema_version"] == "1.0" and "repo_binding" not in envelope


def test_missing_event_name_keeps_legacy_behaviour(repo):
    result = _start(repo, framework=FRAMEWORK, hook_event_name=None)
    assert result["ok"] is True
    assert (result["binding"], result["binding_reason"]) == ("legacy_unbound", "payload_has_no_event_name")
    assert json.loads(_envelope_path(repo, "vscode-A").read_bytes())["schema_version"] == "1.0"


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


def test_bridge_newer_than_framework_keeps_legacy_behaviour(repo, tmp_path):
    """Reader before writer: an older framework cannot read a VS Code v1.1
    envelope, so a newer bridge must not write one through it (nor fail)."""
    older = tmp_path / "older framework"
    (older / "runtime_hooks/core").mkdir(parents=True)
    (older / "runtime_hooks/core/_canonical_closeout.py").write_text(_OLDER_CORE, encoding="utf-8")
    (older / "governance_tools").mkdir()
    (older / "governance_tools/session_end_hook.py").write_text("", encoding="utf-8")
    result = _start(repo, framework=older)
    assert result["ok"] is True, result
    assert (result["binding"], result["binding_reason"]) == (
        "legacy_unbound", "framework_without_root_bound_support")
    assert json.loads(_envelope_path(repo, "vscode-A").read_bytes())["schema_version"] == "1.0"


def test_bridge_outside_installed_location_keeps_legacy_behaviour(repo):
    result = _start(repo, framework=FRAMEWORK, bridge=FRAMEWORK / BRIDGE_SOURCE)
    assert result["ok"] is True
    assert (result["binding"], result["binding_reason"]) == (
        "legacy_unbound", "bridge_not_in_installed_location")
    assert json.loads(_envelope_path(repo, "vscode-A").read_bytes())["schema_version"] == "1.0"


# ── provider/source relabelling (core) ──────────────────────────────────────

@pytest.mark.parametrize("provider, forged_source", [
    (PROVIDER, "codex_session_start"),
    ("codex", "vscode_session_start"),
])
def test_relabelled_binding_source_is_rejected(repo, provider, forged_source):
    core.write_session_envelope("session-a", repo, provider=provider, bound_consumer_root=repo)
    assert core.read_session_envelope("session-a", repo) is not None
    path = _envelope_path(repo, "session-a")
    payload = json.loads(path.read_bytes())
    payload["repo_binding"]["source"] = forged_source
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope("session-a", repo) is None


def test_vscode_provider_cannot_be_relabelled_as_codex(repo):
    core.write_session_envelope("session-a", repo, provider=PROVIDER, bound_consumer_root=repo)
    path = _envelope_path(repo, "session-a")
    payload = json.loads(path.read_bytes())
    payload["provider"] = "codex"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope("session-a", repo) is None


@pytest.mark.parametrize("provider", ["github-copilot", "claude", "unknown"])
def test_only_listed_providers_can_bind(repo, provider):
    with pytest.raises(ValueError, match="root-bound provider"):
        core.write_session_envelope("session-a", repo, provider=provider, bound_consumer_root=repo)
    with pytest.raises(ValueError, match="cannot establish"):
        core.establish_root_bound_session(
            session_id="session-a", cwd=str(repo), installed_root=repo, provider=provider,
            require_existing=False, lock_name=".x-start.lock")
    assert _runtime(repo) == []


# ── review on #226 ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("provider", [["codex"], {"codex": 1}, 7, None])
def test_non_string_provider_reads_as_unreadable_not_crash(repo, provider):
    core.write_session_envelope("session-a", repo, provider=PROVIDER, bound_consumer_root=repo)
    path = _envelope_path(repo, "session-a")
    payload = json.loads(path.read_bytes())
    payload["provider"] = provider
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope("session-a", repo) is None


def _start_raw(root: Path, payload: dict, framework: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", str(root / INSTALLED_BRIDGE),
         "--event-type", "session_start", "--surface", "auto"],
        input=json.dumps(payload), cwd=root, capture_output=True, text=True,
        encoding="utf-8", timeout=60,
        env={**environment(), "AI_GOVERNANCE_FRAMEWORK_ROOT": str(framework)},
    )
    return json.loads(result.stdout)


def test_documented_vscode_local_payload_reaches_root_binding(repo):
    """The installed hook config is Copilot-format (sessionStart), but VS Code
    Local "maps the configuration and then sends the payloads documented here"
    (code.visualstudio.com/docs/agents/reference/hooks-reference): snake_case
    common fields, SessionStart source "new".  This is that exact shape."""
    payload = {"timestamp": "2026-10-22T03:00:00.000Z", "cwd": str(repo),
               "session_id": "vscode-documented", "hook_event_name": "SessionStart",
               "transcript_path": str(repo / "t.jsonl"), "source": "new"}
    result = _start_raw(repo, payload, FRAMEWORK)
    assert (result["surface"], result["provider"]) == ("vscode", PROVIDER)
    assert (result["binding"], result["identity_status"]) == ("root_bound", "created")


def test_copilot_camelcase_payload_stays_on_the_copilot_surface(repo):
    """Copilot sessions send camelCase; that surface is not approved for binding."""
    payload = {"sessionId": "copilot-1", "hookEventName": "sessionStart", "cwd": str(repo)}
    result = _start_raw(repo, payload, FRAMEWORK)
    assert (result["surface"], result["provider"]) == ("copilot", "github-copilot")
    assert "binding" not in result
    assert json.loads(_envelope_path(repo, "copilot-1").read_bytes())["schema_version"] == "1.0"
