"""Regression tests for governance_tools.runtime_identity.

Env fixtures are transcribed from the runtime-detection spike evidence
(spikes/runtime-detect/result-*.json, committed at a23325c0); these tests
formally supersede the spike's inline assertions per the budget entry
(docs/governance/agent-runtime-evaluation-budget-entry-2026-07-16.md).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from governance_tools.runtime_identity import (
    RUNTIME_IDENTITY_SCHEMA_VERSION,
    build_fingerprint,
    build_profile,
    classify_surface,
    detect_agent,
    main,
    normalize_model_id,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Spike fixture: Claude Code / Windows / desktop app (result-claude_code-claude-desktop.json)
CLAUDE_ENV = {
    "CLAUDECODE": "1",
    "CLAUDE_CODE_ENTRYPOINT": "claude-desktop",
    "CLAUDE_CODE_SESSION_ID": "e4333b54-c3fa-42bf-afd7-8fbe32e863cb",
    "CLAUDE_CODE_EXECPATH": r"C:\Users\u\AppData\Roaming\Claude\claude-code\2.1.209\claude.exe",
    "TERM": "xterm-256color",
}

# Spike fixture: Codex / Windows / Codex Desktop (result-codex-codex-desktop.json)
CODEX_ENV = {
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE": "Codex Desktop",
    "CODEX_SANDBOX_NETWORK_DISABLED": "1",
    "CODEX_SHELL": "powershell",
    "CODEX_THREAD_ID": "thread-123",
}

# Spike fixture: GitHub Copilot / VS Code (result-copilot-vscode.json)
COPILOT_ENV = {
    "COPILOT_AGENT": "1",
    "TERM_PROGRAM": "vscode",
}


def _fake_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    return home


def _fake_repo(tmp_path: Path, version: str = "1.2.0") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "README.md").write_text(
        f"# Repo\n\n**Version {version}** - test fixture\n", encoding="utf-8")
    return repo


class TestAgentDetection:
    def test_claude_code_verified_from_env_marker(self):
        field = detect_agent(CLAUDE_ENV)
        assert field["value"] == "claude_code"
        assert field["detection"] == "verified"
        assert field["signal_source"] == "env:CLAUDECODE"

    def test_codex_verified_from_observed_originator_marker(self):
        field = detect_agent(CODEX_ENV)
        assert field["value"] == "codex"
        assert field["detection"] == "verified"
        assert field["signal_source"] == "env:CODEX_INTERNAL_ORIGINATOR_OVERRIDE"

    def test_incidental_codex_configuration_vars_do_not_verify_agent(self):
        field = detect_agent({
            "CODEX_PERMISSION_PROFILE": "workspace-write",
            "CODEX_SANDBOX_NETWORK_DISABLED": "1",
            "CODEX_SHELL": "powershell",
        })
        assert field["value"] is None
        assert field["detection"] == "unknown"

    def test_copilot_verified_from_env_marker(self):
        field = detect_agent(COPILOT_ENV)
        assert field["value"] == "github_copilot"
        assert field["detection"] == "verified"

    def test_negative_no_markers_degrades_to_unknown_without_guessing(self):
        # Spike negative test: stripping markers must yield unknown, not a guess.
        field = detect_agent({"TERM_PROGRAM": "vscode", "PATH": "/usr/bin"})
        assert field["value"] is None
        assert field["detection"] == "unknown"


class TestModelNormalization:
    def test_claude_fable_5(self):
        identity = normalize_model_id("claude-fable-5")
        assert identity["provider"] == "anthropic"
        assert identity["family"] == "claude-fable"
        assert identity["version"] == "5"
        assert identity["raw_id"] == "claude-fable-5"

    def test_claude_opus_4_8(self):
        identity = normalize_model_id("claude-opus-4-8")
        assert identity["family"] == "claude-opus"
        assert identity["version"] == "4.8"

    def test_gpt_5_6_sol(self):
        identity = normalize_model_id("gpt-5.6-sol")
        assert identity["provider"] == "openai"
        assert identity["family"] == "gpt-5"
        assert identity["version"] == "5.6"
        assert identity["variant"] == "sol"

    def test_unrecognized_id_maps_to_unknown_family_never_guessed(self):
        identity = normalize_model_id("totally-new-model-x9")
        assert identity["family"] == "unknown"
        assert identity["provider"] == "unknown"
        assert identity["raw_id"] == "totally-new-model-x9"


class TestProfileClaudeCode:
    def test_model_verified_via_session_keyed_transcript(self, tmp_path):
        home = _fake_home(tmp_path)
        sid = CLAUDE_ENV["CLAUDE_CODE_SESSION_ID"]
        transcript_dir = home / ".claude" / "projects" / "some-project"
        transcript_dir.mkdir(parents=True)
        (transcript_dir / f"{sid}.jsonl").write_text(
            '{"model":"claude-fable-5","x":1}\n{"model":"claude-fable-5"}\n',
            encoding="utf-8")

        profile = build_profile(CLAUDE_ENV, home, _fake_repo(tmp_path))
        model = profile["model"]
        assert model["detection"] == "verified"
        assert model["binding_scope"] == "session"
        assert model["signal_source"] == "harness_transcript"
        assert model["value"]["family"] == "claude-fable"
        assert profile["detection_status"] == "full"

    def test_agent_version_verified_from_execpath(self, tmp_path):
        profile = build_profile(CLAUDE_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        assert profile["agent_version"]["value"] == "2.1.209"
        assert profile["agent_version"]["detection"] == "verified"

    def test_surface_desktop_app(self, tmp_path):
        profile = build_profile(CLAUDE_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        assert profile["surface"]["value"] == "claude-desktop"
        assert profile["surface"]["surface_class"] == "desktop_app"


class TestProfileCodex:
    def test_model_detected_config_default_never_session_bound(self, tmp_path):
        home = _fake_home(tmp_path)
        codex_dir = home / ".codex"
        codex_dir.mkdir()
        (codex_dir / "config.toml").write_text(
            'model = "gpt-5.6-sol"\n', encoding="utf-8")

        profile = build_profile(CODEX_ENV, home, _fake_repo(tmp_path))
        model = profile["model"]
        assert model["detection"] == "detected"
        assert model["binding_scope"] == "config_default"
        assert model["value"]["family"] == "gpt-5"
        # detected model => never detection_status full
        assert profile["detection_status"] == "partial"

    def test_session_id_from_codex_thread(self, tmp_path):
        profile = build_profile(CODEX_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        assert profile["session_id"]["value"] == "thread-123"
        assert profile["session_id"]["detection"] == "verified"


class TestProfileCopilot:
    def test_half_blind_surface_verified_model_unknown(self, tmp_path):
        profile = build_profile(COPILOT_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        assert profile["agent"]["value"] == "github_copilot"
        assert profile["surface"]["value"] == "vscode"
        assert profile["surface"]["surface_class"] == "ide"
        assert profile["model"]["detection"] == "unknown"
        assert profile["model"]["value"] is None


class TestConservativeDegradation:
    def test_empty_env_yields_legal_all_unknown_profile(self, tmp_path):
        profile = build_profile({}, _fake_home(tmp_path),
                                tmp_path / "norepo")
        assert profile["detection_status"] == "none"
        for name in ("agent", "agent_version", "model", "surface",
                     "session_id", "permission_mode", "tools",
                     "governance_version"):
            assert profile[name]["detection"] == "unknown"
            assert profile[name]["value"] is None
        assert profile["fingerprint"]["coarse_id"] == "unknown"
        assert profile["fingerprint"]["full_id"] == "unknown"

    def test_reported_tier_is_never_emitted(self, tmp_path):
        for env in ({}, CLAUDE_ENV, CODEX_ENV, COPILOT_ENV):
            profile = build_profile(env, _fake_home(tmp_path),
                                    _fake_repo(tmp_path))
            for name in ("agent", "agent_version", "model", "surface",
                         "session_id", "permission_mode", "tools",
                         "governance_version"):
                assert profile[name]["detection"] in (
                    "verified", "detected", "unknown")


class TestHookPayload:
    def test_permission_mode_and_tools_from_payload(self, tmp_path):
        payload = {"permission_mode": "workspace-write",
                   "tools": ["shell", "filesystem"]}
        profile = build_profile(CLAUDE_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path), hook_payload=payload)
        assert profile["permission_mode"]["value"] == "workspace-write"
        assert profile["permission_mode"]["detection"] == "verified"
        assert profile["tools"]["value"] == ["filesystem", "shell"]

    def test_absent_payload_keeps_fields_unknown(self, tmp_path):
        profile = build_profile(CLAUDE_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        assert profile["permission_mode"]["detection"] == "unknown"
        assert profile["tools"]["detection"] == "unknown"


class TestFingerprint:
    def _profile(self, tmp_path, env, version="1.2.0"):
        return build_profile(env, _fake_home(tmp_path),
                             _fake_repo(tmp_path, version))

    def test_coarse_id_stable_across_sessions_and_versions(self, tmp_path):
        env_a = dict(CLAUDE_ENV)
        env_b = dict(CLAUDE_ENV)
        env_b["CLAUDE_CODE_SESSION_ID"] = "ffffffff-0000-0000-0000-000000000000"
        env_b["CLAUDE_CODE_EXECPATH"] = env_b["CLAUDE_CODE_EXECPATH"].replace(
            "2.1.209", "2.2.0")
        fp_a = self._profile(tmp_path, env_a)["fingerprint"]
        fp_b = self._profile(tmp_path, env_b)["fingerprint"]
        # agent version bump: coarse id unchanged (samples keep accumulating),
        # full id changed (drift marker).
        assert fp_a["coarse_id"] == fp_b["coarse_id"]
        assert fp_a["full_id"] != fp_b["full_id"]

    def test_full_id_excludes_session_id(self, tmp_path):
        env_b = dict(CLAUDE_ENV)
        env_b["CLAUDE_CODE_SESSION_ID"] = "ffffffff-0000-0000-0000-000000000000"
        fp_a = self._profile(tmp_path, CLAUDE_ENV)["fingerprint"]
        fp_b = self._profile(tmp_path, env_b)["fingerprint"]
        assert fp_a["full_id"] == fp_b["full_id"]

    def test_coarse_id_changes_when_model_family_changes(self, tmp_path):
        env_a = dict(CLAUDE_ENV, ANTHROPIC_MODEL="claude-fable-5")
        env_b = dict(CLAUDE_ENV, ANTHROPIC_MODEL="claude-opus-4-8")
        fp_a = self._profile(tmp_path, env_a)["fingerprint"]
        fp_b = self._profile(tmp_path, env_b)["fingerprint"]
        assert fp_a["coarse_id"] != fp_b["coarse_id"]

    def test_fingerprint_schema_version_recorded(self, tmp_path):
        fp = self._profile(tmp_path, CLAUDE_ENV)["fingerprint"]
        assert fp["fingerprint_schema_version"] == "1.0"


class TestSchemaConformance:
    def test_profile_conforms_to_schema_shape(self, tmp_path):
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "runtime_identity.schema.json")
            .read_text(encoding="utf-8"))
        profile = build_profile(CLAUDE_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        properties = schema["properties"]
        assert set(profile) <= set(properties)
        for key in schema["required"]:
            assert key in profile, f"missing required field {key}"
        assert profile["schema_version"] in properties["schema_version"]["enum"]
        assert (profile["detection_status"]
                in properties["detection_status"]["enum"])
        tiers = schema["$defs"]["detection_tier"]["enum"]
        for name in ("agent", "agent_version", "model", "surface",
                     "session_id", "permission_mode", "tools",
                     "governance_version"):
            assert profile[name]["detection"] in tiers
        assert profile["generator"]["llm_calls"] == 0

    def test_no_username_or_absolute_path_leaks(self, tmp_path):
        # CLAUDE_CODE_EXECPATH contains a user path; only the version segment
        # may survive into the profile.
        profile = build_profile(CLAUDE_ENV, _fake_home(tmp_path),
                                _fake_repo(tmp_path))
        dump = json.dumps(profile)
        assert "AppData" not in dump
        assert "Users" not in dump
        assert str(tmp_path) not in dump


class TestCli:
    def test_detect_writes_profile_and_exits_zero(self, tmp_path, monkeypatch, capsys):
        repo = _fake_repo(tmp_path)
        monkeypatch.setattr("pathlib.Path.home", lambda: _fake_home(tmp_path))
        for key in list(CLAUDE_ENV) + ["CODEX_THREAD_ID", "COPILOT_AGENT",
                                       "ANTHROPIC_MODEL", "TERM_PROGRAM"]:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")

        exit_code = main(["detect", "--repo", str(repo)])
        assert exit_code == 0
        written = json.loads(
            (repo / ".governance" / "runtime-profile.json")
            .read_text(encoding="utf-8"))
        assert written["agent"]["value"] == "claude_code"
        assert written["schema_version"] == RUNTIME_IDENTITY_SCHEMA_VERSION
        assert "runtime identity" in capsys.readouterr().out

    def test_detect_in_unknown_env_still_exits_zero(self, tmp_path, monkeypatch):
        repo = _fake_repo(tmp_path)
        monkeypatch.setattr("pathlib.Path.home", lambda: _fake_home(tmp_path))
        identity_prefixes = ("CLAUDE_", "CODEX_", "COPILOT_", "GEMINI_",
                             "CURSOR_")
        identity_keys = {
            "CLAUDECODE", "ANTHROPIC_MODEL", "OPENAI_MODEL",
            "TERM_PROGRAM", "TERMINAL_EMULATOR", "GITHUB_ACTIONS",
            "WT_SESSION",
        }
        for key in list(os.environ):
            if key in identity_keys or key.startswith(identity_prefixes):
                monkeypatch.delenv(key, raising=False)
        exit_code = main(["detect", "--repo", str(repo)])
        assert exit_code == 0
        written = json.loads(
            (repo / ".governance" / "runtime-profile.json")
            .read_text(encoding="utf-8"))
        assert written["agent"]["detection"] == "unknown"

    def test_show_without_profile_exits_zero(self, tmp_path, capsys):
        repo = _fake_repo(tmp_path)
        assert main(["show", "--repo", str(repo)]) == 0
        assert "no runtime profile" in capsys.readouterr().out


class TestSurfaceClassification:
    @pytest.mark.parametrize("value,expected", [
        ("claude-desktop", "desktop_app"),
        ("cli", "cli"),
        ("vscode", "ide"),
        ("sdk-ts", "sdk"),
        ("github_actions", "ci"),
        (None, "unknown"),
        ("something-new", "unknown"),
    ])
    def test_classes(self, value, expected):
        assert classify_surface(value) == expected
