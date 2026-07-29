from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_live_canary as live


WORKSPACE = "C:/workspace"
SESSION_ID = "019facd0-11a5-7673-8914-ca863bff0588"
CURRENT_DATE = "2026-07-29"


def _line(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )


def _context_contract() -> dict[str, object]:
    return {
        "current_date": CURRENT_DATE,
        "meta": live.CONTEXT_META_EXPECTED,
        "provider": live.DEFAULT_PROVIDER,
        "public_context_tokens": live.PUBLIC_CONTEXT_TOKENS,
        "turn": live.CONTEXT_TURN_EXPECTED,
    }


def _shell_input(command: str, workdir: str = WORKSPACE) -> str:
    return (
        "const r = await tools.shell_command({command:"
        + json.dumps(command)
        + ",workdir:"
        + json.dumps(workdir)
        + "}); text(r)\n"
    )


def _patch_input(target: str) -> str:
    patch = (
        "*** Begin Patch\n"
        f"*** Update File: {target}\n"
        "@@\n"
        "-    return a - b\n"
        "+    return a + b\n"
        "*** End Patch"
    )
    return (
        "const patch = "
        + json.dumps(patch)
        + ";\ntext(await tools.apply_patch(patch));\n"
    )


def _machine_context(workspace: str) -> str:
    return (
        "<environment_context>"
        f"<cwd>{workspace}</cwd>"
        "<shell>powershell</shell>"
        f"<current_date>{CURRENT_DATE}</current_date>"
        f"<timezone>{live.DEFAULT_TIMEZONE}</timezone>"
        "<filesystem><workspace_roots>"
        f"<root>{workspace}</root>"
        "</workspace_roots><permission_profile type=\"disabled\">"
        "<file_system type=\"unrestricted\" />"
        "</permission_profile></filesystem>"
        "</environment_context>"
    )


def _rollout(
    *,
    session_id: str = SESSION_ID,
    model: str = live.DEFAULT_MODEL,
    comp_hash: str = live.DEFAULT_COMP_HASH,
    cli_version: str = live.DEFAULT_CLI_VERSION,
    effort: str = live.DEFAULT_REASONING,
    prompt: str = "frozen prompt",
    event_prompt: str | None = None,
    provider: str = live.DEFAULT_PROVIDER,
    meta_cwd: str = WORKSPACE,
    turn_cwd: str = WORKSPACE,
    workspace_roots: list[str] | None = None,
    machine_cwd: str = WORKSPACE,
    developer_text: str = "frozen developer instructions",
    tool_input: str | None = None,
) -> bytes:
    if workspace_roots is None:
        workspace_roots = [WORKSPACE]
    if tool_input is None:
        tool_input = _shell_input("git rev-parse HEAD")
    event_prompt = prompt if event_prompt is None else event_prompt
    return b"".join(
        [
            _line(
                {
                    "payload": {
                        "base_instructions": {"text": "frozen base instructions"},
                        "cli_version": cli_version,
                        "cwd": meta_cwd,
                        "history_mode": "legacy",
                        "id": session_id,
                        "model_provider": provider,
                        "originator": "Codex Desktop",
                        "session_id": session_id,
                        "source": "exec",
                        "thread_source": "user",
                    },
                    "timestamp": "2026-07-29T08:00:00Z",
                    "type": "session_meta",
                }
            ),
            _line(
                {
                    "payload": {
                        "approval_policy": "never",
                        "approvals_reviewer": "user",
                        "collaboration_mode": {
                            "mode": "default",
                            "settings": {
                                "developer_instructions": None,
                                "model": model,
                                "reasoning_effort": effort,
                            },
                        },
                        "comp_hash": comp_hash,
                        "current_date": CURRENT_DATE,
                        "cwd": turn_cwd,
                        "effort": effort,
                        "model": model,
                        "multi_agent_version": "v1",
                        "permission_profile": {"type": "disabled"},
                        "personality": "pragmatic",
                        "realtime_active": False,
                        "sandbox_policy": {"type": "danger-full-access"},
                        "summary": "auto",
                        "timezone": live.DEFAULT_TIMEZONE,
                        "turn_id": "turn-1",
                        "workspace_roots": workspace_roots,
                    },
                    "timestamp": "2026-07-29T08:00:01Z",
                    "type": "turn_context",
                }
            ),
            _line(
                {
                    "payload": {
                        "content": [
                            {"text": developer_text, "type": "input_text"}
                        ],
                        "role": "developer",
                        "type": "message",
                    },
                    "timestamp": "2026-07-29T08:00:01Z",
                    "type": "response_item",
                }
            ),
            _line(
                {
                    "payload": {
                        "full": True,
                        "state": {"cwd": turn_cwd, "model": model},
                    },
                    "timestamp": "2026-07-29T08:00:01Z",
                    "type": "world_state",
                }
            ),
            _line(
                {
                    "payload": {
                        "content": [
                            {
                                "text": _machine_context(machine_cwd),
                                "type": "input_text",
                            }
                        ],
                        "role": "user",
                        "type": "message",
                    },
                    "timestamp": "2026-07-29T08:00:01Z",
                    "type": "response_item",
                }
            ),
            _line(
                {
                    "payload": {
                        "content": [{"text": prompt, "type": "input_text"}],
                        "role": "user",
                        "type": "message",
                    },
                    "timestamp": "2026-07-29T08:00:02Z",
                    "type": "response_item",
                }
            ),
            _line(
                {
                    "payload": {
                        "message": event_prompt,
                        "type": "user_message",
                    },
                    "timestamp": "2026-07-29T08:00:02Z",
                    "type": "event_msg",
                }
            ),
            _line(
                {
                    "payload": {
                        "call_id": "call-1",
                        "input": tool_input,
                        "name": "exec",
                        "type": "custom_tool_call",
                    },
                    "timestamp": "2026-07-29T08:00:03Z",
                    "type": "response_item",
                }
            ),
        ]
    )


def _parse(tmp_path: Path, raw: bytes, prompt: bytes = b"frozen prompt"):
    path = tmp_path / "rollout.jsonl"
    path.write_bytes(raw)
    return live.parse_rollout(
        path,
        expected_prompt=prompt,
        expected_model=live.DEFAULT_MODEL,
        expected_comp_hash=live.DEFAULT_COMP_HASH,
        expected_cli_version=live.DEFAULT_CLI_VERSION,
        expected_reasoning=live.DEFAULT_REASONING,
        expected_workspace=Path(WORKSPACE),
        expected_context_contract=_context_contract(),
    )


def test_parse_rollout_accepts_exact_route(tmp_path: Path) -> None:
    result = _parse(tmp_path, _rollout())
    assert result["session_id"] == SESSION_ID
    assert result["model"] == live.DEFAULT_MODEL
    assert result["comp_hash"] == live.DEFAULT_COMP_HASH
    assert result["cli_version"] == live.DEFAULT_CLI_VERSION
    assert result["prompt_sha256"] == live._sha256_bytes(b"frozen prompt")
    assert result["machine_context_count"] == 1
    assert result["tool_inventory"][0]["kind"] == "shell_command"


def test_prepare_rejects_non_frozen_route(tmp_path: Path) -> None:
    with pytest.raises(live.CanaryError, match="frozen Codex route"):
        live.prepare(
            tmp_path,
            tmp_path / "staging",
            run_id="test",
            model="different",
            comp_hash=live.DEFAULT_COMP_HASH,
            cli_version=live.DEFAULT_CLI_VERSION,
            reasoning=live.DEFAULT_REASONING,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("model", "gpt-5.6-terra", "model mismatch"),
        ("comp_hash", "2999", "component hash mismatch"),
        ("cli_version", "0.145.0", "CLI build mismatch"),
        ("effort", "medium", "reasoning mismatch"),
        ("provider", "other", "model provider"),
    ],
)
def test_parse_rollout_rejects_model_build_identity_mismatch(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    with pytest.raises(live.CanaryError, match=message):
        _parse(tmp_path, _rollout(**{field: value}))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"meta_cwd": "C:/wrong"}, "session_meta cwd"),
        ({"turn_cwd": "C:/wrong"}, "turn_context cwd"),
        ({"workspace_roots": ["C:/wrong"]}, "workspace roots"),
        ({"machine_cwd": "C:/wrong"}, "machine context"),
    ],
)
def test_parse_rollout_rejects_context_path_mismatch(
    tmp_path: Path,
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(live.CanaryError, match=message):
        _parse(tmp_path, _rollout(**kwargs))


def test_parse_rollout_rejects_prompt_byte_mismatch(tmp_path: Path) -> None:
    with pytest.raises(live.CanaryError, match="one exact task prompt"):
        _parse(tmp_path, _rollout(prompt="changed prompt"))


def test_parse_rollout_rejects_duplicate_event_prompt_mismatch(
    tmp_path: Path,
) -> None:
    with pytest.raises(live.CanaryError, match="event user message"):
        _parse(tmp_path, _rollout(event_prompt="changed duplicate"))


def test_context_fingerprint_changes_with_developer_instructions(
    tmp_path: Path,
) -> None:
    first = _parse(tmp_path, _rollout())
    second_path = tmp_path / "second"
    second_path.mkdir()
    second = _parse(
        second_path,
        _rollout(developer_text="different developer instructions"),
    )
    assert (
        first["context_identity_sha256"]
        != second["context_identity_sha256"]
    )


def test_parse_rollout_rejects_command_chaining(tmp_path: Path) -> None:
    tool_input = _shell_input("git add calc.py; git commit -m chained")
    with pytest.raises(live.CanaryError, match="simple-command contract"):
        _parse(tmp_path, _rollout(tool_input=tool_input))


@pytest.mark.parametrize(
    "command",
    [
        r"Get-Content ..\secret.txt",
        r"git -C .. status",
        r"python -B ..\outside.py",
        r"Get-Content $env:USERPROFILE\secret.txt",
        r"git push origin main",
        r"git config --global user.name attacker",
        r"git clean -fdx",
    ],
)
def test_parse_rollout_rejects_semantic_command_escape(
    tmp_path: Path,
    command: str,
) -> None:
    with pytest.raises(
        live.CanaryError,
        match="simple-command contract|per-command grammar",
    ):
        _parse(tmp_path, _rollout(tool_input=_shell_input(command)))


@pytest.mark.parametrize(
    "command",
    [
        "git rev-parse HEAD",
        "git rev-parse HEAD^",
        "git rev-list --parents -n 1 HEAD",
        "git status --porcelain=v1 --untracked-files=all",
        "git diff --check",
        "git diff -- calc.py",
        "git diff -- calc.py test_calc.py",
        "git add calc.py",
        'git commit -m "Fix add implementation"',
        "python -B test_calc.py",
        "Get-ChildItem -Force",
        "Get-Content calc.py",
        "Get-Content test_calc.py",
        "rg --files",
    ],
)
def test_parse_rollout_accepts_frozen_command_grammar(
    tmp_path: Path,
    command: str,
) -> None:
    result = _parse(
        tmp_path,
        _rollout(tool_input=_shell_input(command)),
    )
    assert result["tool_inventory"][0]["command"] == command
    assert result["tool_inventory"][0]["rule"]


def test_parse_rollout_accepts_workspace_local_directory_read(
    tmp_path: Path,
) -> None:
    result = _parse(
        tmp_path,
        _rollout(tool_input=_shell_input("Get-ChildItem -Force")),
    )
    assert result["tool_inventory"][0]["command"] == "Get-ChildItem -Force"


def test_parse_rollout_rejects_outside_workdir(tmp_path: Path) -> None:
    tool_input = _shell_input("git status --short", "C:/outside")
    with pytest.raises(live.CanaryError, match="workdir differs"):
        _parse(tmp_path, _rollout(tool_input=tool_input))


def test_parse_rollout_accepts_scoped_apply_patch(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        _rollout(tool_input=_patch_input("C:/workspace/calc.py")),
    )
    assert result["tool_inventory"][0]["kind"] == "apply_patch"


def test_parse_rollout_rejects_outside_apply_patch(tmp_path: Path) -> None:
    with pytest.raises(live.CanaryError, match="target escapes"):
        _parse(
            tmp_path,
            _rollout(tool_input=_patch_input("C:/outside/calc.py")),
        )


def test_public_workspace_patch_scope_is_exact() -> None:
    assert live._patch_target_is_allowed(
        r"WORKSPACE_A\calc.py",
        "WORKSPACE_A",
    )
    assert not live._patch_target_is_allowed(
        r"WORKSPACE_A\subdir\calc.py",
        "WORKSPACE_A",
    )


def test_parse_rollout_rejects_tool_search(tmp_path: Path) -> None:
    raw = _rollout() + _line(
        {
            "payload": {
                "call_id": "call-search",
                "name": "tool_search",
                "type": "tool_search_call",
            },
            "timestamp": "2026-07-29T08:00:04Z",
            "type": "response_item",
        }
    )
    with pytest.raises(live.CanaryError, match="tool search"):
        _parse(tmp_path, raw)


def test_sanitizer_is_deterministic_and_removes_host_identity(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(
        _line(
            {
                "path": "C:/Users/alice/.codex/skills/test/SKILL.md",
                "repo": "D:/private/repo",
                "owner": (
                    "DESKTOP-SECRET/alice "
                    "(S-1-5-21-111111111-222222222-333333333-1001)"
                ),
            }
        )
    )
    first = live.sanitize_jsonl(
        source,
        workspace="D:/private/repo",
        context_token="WORKSPACE_A",
    )
    second = live.sanitize_jsonl(
        source,
        workspace="D:/private/repo",
        context_token="WORKSPACE_A",
    )
    assert first == second
    assert b"WORKSPACE_A" in first
    assert b"<LOCAL_USER_PATH>" in first
    assert b"<LOCAL_HOST>" in first
    assert b"<WINDOWS_SID>" in first
    assert live._privacy_violations(first) == []


def test_sanitizer_redacts_mapping_keys_and_all_absolute_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(
        _line(
            {
                r"C:\tmp\gate3-run\a\calc.py": {
                    "repository_url": (
                        r"D:\repo\.live-canary-staging\run\inputs"
                        r"\baseline.bundle"
                    ),
                    "shell": (
                        r"C:\WINDOWS\System32\WindowsPowerShell\v1.0"
                        r"\powershell.exe"
                    ),
                }
            }
        )
    )
    sanitized = live.sanitize_jsonl(
        source,
        workspace=r"C:\tmp\gate3-run\a",
        context_token="WORKSPACE_A",
    )
    payload = json.loads(sanitized)
    assert list(payload) == [r"WORKSPACE_A\calc.py"]
    assert payload[r"WORKSPACE_A\calc.py"] == {
        "repository_url": "<LOCAL_ABSOLUTE_PATH>",
        "shell": "<LOCAL_ABSOLUTE_PATH>",
    }
    assert live._privacy_violations(sanitized) == []


@pytest.mark.parametrize(
    "private_path",
    [
        "C:\\",
        r"C:\private\file.txt",
        r"\\server\share\secret.txt",
        r"\\?\UNC\server\share\secret.txt",
        "\\\\?\\C:\\",
        r"\\?\C:\private\file.txt",
    ],
)
def test_sanitizer_redacts_every_windows_absolute_path_form(
    tmp_path: Path,
    private_path: str,
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(_line({"private_path": private_path}))
    sanitized = live.sanitize_jsonl(
        source,
        workspace=r"D:\unrelated\workspace",
        context_token="WORKSPACE_A",
    )
    assert json.loads(sanitized) == {
        "private_path": "<LOCAL_ABSOLUTE_PATH>"
    }
    assert live._privacy_violations(sanitized) == []


def test_sanitizer_rejects_mapping_key_collision(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_bytes(
        _line(
            {
                r"C:\workspace": "source",
                "WORKSPACE_A": "already-public",
            }
        )
    )
    with pytest.raises(live.CanaryError, match="mapping-key collision"):
        live.sanitize_jsonl(
            source,
            workspace=r"C:\workspace",
            context_token="WORKSPACE_A",
        )


def test_sanitized_rollout_remains_strictly_parseable(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    public = tmp_path / "public.jsonl"
    source.write_bytes(_rollout())
    public.write_bytes(
        live.sanitize_jsonl(
            source,
            workspace=WORKSPACE,
            context_token=live.PUBLIC_CONTEXT_TOKENS["A"],
        )
    )
    result = live.parse_rollout(
        public,
        expected_prompt=b"frozen prompt",
        expected_model=live.DEFAULT_MODEL,
        expected_comp_hash=live.DEFAULT_COMP_HASH,
        expected_cli_version=live.DEFAULT_CLI_VERSION,
        expected_reasoning=live.DEFAULT_REASONING,
        expected_workspace=live.PUBLIC_CONTEXT_TOKENS["A"],
        expected_context_contract=_context_contract(),
    )
    assert result["session_id"] == SESSION_ID


def test_workspace_redaction_covers_javascript_escaped_windows_path() -> None:
    workspace = r"C:\private\repo"
    source = (
        r'const r = await tools.shell_command({command:"git status",'
        r'workdir:"C:\\private\\repo"}); text(r)'
    )
    sanitized = live._replace_workspace_text(
        source,
        workspace,
        "WORKSPACE_A",
    )
    assert sanitized.endswith('workdir:"WORKSPACE_A"}); text(r)')
    assert "private" not in sanitized


def test_public_privacy_scan_rejects_raw_host_identifier(
    tmp_path: Path,
) -> None:
    (tmp_path / "raw.txt").write_text(
        "DESKTOP-SECRET S-1-5-21-111-222-333-1001",
        encoding="utf-8",
    )
    with pytest.raises(live.CanaryError, match="private host identifiers"):
        live.verify_public_privacy(tmp_path)


@pytest.mark.parametrize(
    "private_path",
    [
        "C:\\",
        r"C:\private\file.txt",
        r"\\server\share\secret.txt",
        r"\\?\UNC\server\share\secret.txt",
        "\\\\?\\C:\\",
        r"\\?\C:\private\file.txt",
    ],
)
def test_public_privacy_scan_rejects_any_windows_absolute_path(
    tmp_path: Path,
    private_path: str,
) -> None:
    (tmp_path / "raw.txt").write_text(
        private_path,
        encoding="utf-8",
    )
    with pytest.raises(live.CanaryError, match="windows_absolute_path"):
        live.verify_public_privacy(tmp_path)


def test_public_privacy_scan_does_not_treat_json_escapes_as_unc() -> None:
    payload = _line(
        {
            "input": (
                "*** Begin Patch\n"
                "*** Update File: WORKSPACE_A\\calc.py\n"
                "@@\n"
            )
        }
    )
    assert live._privacy_violations(payload) == []


def _exec_events(
    session_id: str = SESSION_ID,
    *,
    failed: bool = False,
) -> bytes:
    return b"".join(
        [
            _line({"thread_id": session_id, "type": "thread.started"}),
            _line({"type": "turn.started"}),
            _line(
                {
                    "error": {"message": "failed"},
                    "type": "turn.failed",
                }
                if failed
                else {
                    "type": "turn.completed",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }
            ),
        ]
    )


def test_parse_exec_events_binds_public_thread_to_saved_rollout(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_bytes(_exec_events())
    result = live.parse_exec_events(path, expected_session_id=SESSION_ID)
    assert result["thread_id"] == SESSION_ID
    assert result["turn_completed"] is True


def test_parse_exec_events_rejects_session_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_bytes(_exec_events("different"))
    with pytest.raises(live.CanaryError, match="thread id differs"):
        live.parse_exec_events(path, expected_session_id=SESSION_ID)


def test_parse_exec_events_rejects_failed_turn(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_bytes(_exec_events(failed=True))
    with pytest.raises(live.CanaryError, match="failed turn"):
        live.parse_exec_events(path, expected_session_id=SESSION_ID)


def test_git_safe_directories_are_process_local(tmp_path: Path) -> None:
    prior = os.environ.get("GIT_CONFIG_COUNT")
    with live._git_safe_directories([tmp_path]):
        assert int(os.environ["GIT_CONFIG_COUNT"]) == int(prior or "0") + 1
        index = int(prior or "0")
        assert os.environ[f"GIT_CONFIG_KEY_{index}"] == "safe.directory"
        assert (
            os.environ[f"GIT_CONFIG_VALUE_{index}"]
            == tmp_path.resolve().as_posix()
        )
    assert os.environ.get("GIT_CONFIG_COUNT") == prior
