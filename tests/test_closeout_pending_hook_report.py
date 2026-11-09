"""Issue #287: a PREPARED candidate with an installed session-end hook is
reported as pending, not as NOT PERSISTED, and the manual fallback is not
offered for it. Wording only; R2 evidence stays the sole confirmation."""
from pathlib import Path

from governance_tools.manage_agent_closeout import (
    _PENDING_HOOK_NOTE,
    ClaudeAdapter,
    CodexCLIAdapter,
)

ROOT = Path(__file__).resolve().parents[1]
GUIDANCE = [
    "AGENTS.base.md",
    "baselines/repo-min/AGENTS.base.md",
    "governance/agent-contract-template.md",
    "governance/copilot-instructions-template.md",
]


def _text(rel):
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def test_guidance_reports_pending_hook_and_skips_refused_fallback():
    for rel in GUIDANCE:
        text = _text(rel)
        assert "`PREPARED` / `PENDING_HOOK`" in text, rel
        # Only a hook that runs the closeout counts, and verify must say so.
        assert "says the closeout is left to it" in text, rel
        assert "a hook that only writes a checkpoint does not count" in text, rel
        assert "reports the governed session-end hook as installed" not in text, rel
        # verify defaults to the current directory, and preparation runs from
        # the framework checkout, so the consumer root must be explicit.
        assert "manage_agent_closeout --project-root <repo> verify --agent <agent>" in text, rel
        # Rule 5's manual attempt is reconciled, not silently skipped.
        assert "cannot release a `PREPARED` candidate, so that report is its outcome" in text, rel
        assert "not `NOT PERSISTED`" in text, rel
        assert "An installed hook is not proof that it will run or succeed" in text, rel
        assert "hook runs the closeout after" not in text, rel
        assert "RELEASE_PROOF_INVALID" in text, rel
        assert "do not attempt it" in text, rel
        assert "where none is usable, the agent attempts the manual closeout" not in text, rel
        assert "Where no usable governed hook exists, attempt the manual closeout" not in text, rel


def test_codex_verify_adds_pending_note_only_when_hook_installed(tmp_path):
    adapter = CodexCLIAdapter()
    framework = tmp_path / "framework"
    project = tmp_path / "consumer"
    project.mkdir()
    missing = adapter.verify(project, framework)
    assert missing["installed"] is False
    assert _PENDING_HOOK_NOTE not in missing["note"]

    adapter.install(project, framework)
    installed = adapter.verify(project, framework)
    assert installed["installed"] is True
    assert installed["note"].endswith(_PENDING_HOOK_NOTE)
    assert "native execution is not verified" in installed["note"]


def test_claude_verify_never_leaves_the_closeout_to_its_hook(tmp_path, monkeypatch):
    # Claude's SessionEnd hook only writes a resumable checkpoint; telling the
    # agent the closeout is pending on it would never resolve.
    # Isolate the user's global ~/.claude/settings.json.
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    adapter = ClaudeAdapter()
    framework = tmp_path / "framework"
    project = tmp_path / "consumer"
    project.mkdir()
    assert _PENDING_HOOK_NOTE not in adapter.verify(project, framework)["note"]
    adapter.install(project, framework)
    result = adapter.verify(project, framework)
    assert result["binding_state"] == "CORRECTLY_INSTALLED"
    assert _PENDING_HOOK_NOTE not in result["note"]
    assert "closeout is left to" not in result["note"]


def test_codex_note_carries_the_phrase_the_guidance_keys_on():
    assert "the closeout is left to this hook" in _PENDING_HOOK_NOTE


def test_codex_print_manual_says_fallback_is_not_for_prepared_candidates(tmp_path):
    text = CodexCLIAdapter().print_manual(tmp_path)
    assert "Not for a PREPARED (R2) candidate" in text
    assert "RELEASE_PROOF_INVALID" in text
