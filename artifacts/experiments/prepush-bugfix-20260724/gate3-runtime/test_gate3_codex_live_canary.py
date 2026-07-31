from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

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


def _parse(
    tmp_path: Path,
    raw: bytes,
    prompt: bytes = b"frozen prompt",
    *,
    rollout_diagnostic: dict[str, object] | None = None,
    parse_phase: str | None = None,
):
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
        rollout_diagnostic=rollout_diagnostic,
        parse_phase=parse_phase,
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


def _rollout_with_world_state_payloads(payloads: list[object]) -> bytes:
    records = [
        json.loads(line)
        for line in _rollout().splitlines()
        if line.strip()
    ]
    index = next(
        i for i, record in enumerate(records) if record["type"] == "world_state"
    )
    template = records.pop(index)
    for offset, payload in enumerate(payloads):
        record = dict(template)
        record["payload"] = payload
        records.insert(index + offset, record)
    return b"".join(_line(record) for record in records)


@pytest.mark.parametrize(
    ("payloads", "expected_census", "error", "parse_phase"),
    [
        (
            [],
            {
                "full_true_count": 0,
                "object_payload_count": 0,
                "raw_count": 0,
                "state_object_count": 0,
            },
            "rollout has no world_state baseline",
            "source",
        ),
        (
            [{"full": True, "state": {"cwd": WORKSPACE}}],
            {
                "full_true_count": 1,
                "object_payload_count": 1,
                "raw_count": 1,
                "state_object_count": 1,
            },
            None,
            "source",
        ),
        (
            [
                {"full": True, "state": {"cwd": WORKSPACE}},
                {"full": False, "state": {}},
            ],
            {
                "full_true_count": 1,
                "object_payload_count": 2,
                "raw_count": 2,
                "state_object_count": 2,
            },
            None,
            "public",
        ),
        (
            ["non-object"],
            {
                "full_true_count": 0,
                "object_payload_count": 0,
                "raw_count": 1,
                "state_object_count": 0,
            },
            "every world_state payload must be an object",
            "public",
        ),
        (
            [{"full": False, "state": {"cwd": WORKSPACE}}],
            {
                "full_true_count": 0,
                "object_payload_count": 1,
                "raw_count": 1,
                "state_object_count": 1,
            },
            "rollout must contain exactly one full world_state baseline",
            "source",
        ),
        (
            [
                {"full": True, "state": {"cwd": WORKSPACE}},
                {"full": True, "state": {"model": live.DEFAULT_MODEL}},
            ],
            {
                "full_true_count": 2,
                "object_payload_count": 2,
                "raw_count": 2,
                "state_object_count": 2,
            },
            "rollout must contain exactly one full world_state baseline",
            "public",
        ),
        (
            [{"full": True, "state": "non-object"}],
            {
                "full_true_count": 1,
                "object_payload_count": 1,
                "raw_count": 1,
                "state_object_count": 0,
            },
            "every world_state must have a boolean full flag and object state",
            "source",
        ),
        (
            [
                {"full": False, "state": {"model": live.DEFAULT_MODEL}},
                {"full": True, "state": {"cwd": WORKSPACE}},
            ],
            {
                "full_true_count": 1,
                "object_payload_count": 2,
                "raw_count": 2,
                "state_object_count": 2,
            },
            "world_state full baseline must precede every delta",
            "public",
        ),
    ],
    ids=[
        "zero",
        "one-full",
        "one-full-one-delta",
        "non-object-payload",
        "no-full",
        "multiple-full",
        "non-object-state",
        "delta-before-full",
    ],
)
def test_world_state_census_and_parser_enforce_full_delta_contract(
    tmp_path: Path,
    payloads: list[object],
    expected_census: dict[str, int],
    error: str | None,
    parse_phase: str,
) -> None:
    diagnostic = live._empty_rollout_diagnostics()["A"]
    raw = _rollout_with_world_state_payloads(payloads)
    if error is None:
        _parse(
            tmp_path,
            raw,
            rollout_diagnostic=diagnostic,
            parse_phase=parse_phase,
        )
        expected_status = "PASS"
    else:
        with pytest.raises(
            live.CanaryError,
            match=error,
        ):
            _parse(
                tmp_path,
                raw,
                rollout_diagnostic=diagnostic,
                parse_phase=parse_phase,
            )
        expected_status = "FAIL"
    assert diagnostic == {
        "parse_phases": {
            "public": (
                expected_status if parse_phase == "public" else "NOT_RUN"
            ),
            "source": (
                expected_status if parse_phase == "source" else "NOT_RUN"
            ),
        },
        "public_census": (
            expected_census if parse_phase == "public" else None
        ),
        "source_census": (
            expected_census if parse_phase == "source" else None
        ),
    }


def test_world_state_delta_order_is_bound_into_context_identity(
    tmp_path: Path,
) -> None:
    baseline = {"full": True, "state": {"cwd": WORKSPACE}}
    first_delta = {"full": False, "state": {"model": live.DEFAULT_MODEL}}
    second_delta = {"full": False, "state": {"summary": "auto"}}
    original = _parse(
        tmp_path,
        _rollout_with_world_state_payloads(
            [baseline, first_delta, second_delta]
        ),
    )
    reordered = _parse(
        tmp_path,
        _rollout_with_world_state_payloads(
            [baseline, second_delta, first_delta]
        ),
    )
    assert (
        original["context_identity_sha256"]
        != reordered["context_identity_sha256"]
    )


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
        r"\\.\PhysicalDrive0",
        r"\\?\Volume{01234567-89ab-cdef-0123-456789abcdef}\secret.txt",
        r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1\secret.txt",
        r"\Device\HarddiskVolume1\secret.txt",
        r"\??\C:\private\file.txt",
        r"\Global??\C:\private\file.txt",
        r"\DosDevices\C:\private\file.txt",
        r"//./PhysicalDrive0",
        r"//?/Volume{01234567-89ab-cdef-0123-456789abcdef}/secret.txt",
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
        r"\\.\PhysicalDrive0",
        r"\\?\Volume{01234567-89ab-cdef-0123-456789abcdef}\secret.txt",
        r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1\secret.txt",
        r"\Device\HarddiskVolume1\secret.txt",
        r"\??\C:\private\file.txt",
        r"\Global??\C:\private\file.txt",
        r"\DosDevices\C:\private\file.txt",
        r"//./PhysicalDrive0",
        r"//?/Volume{01234567-89ab-cdef-0123-456789abcdef}/secret.txt",
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


def _identity_bundle(
    tmp_path: Path,
    producer_identity: dict[str, str],
) -> tuple[Path, str, str]:
    repo = tmp_path / "source"
    repo.mkdir()
    live._git(repo, "init", "-q")
    live._git(repo, "config", "core.autocrlf", "false")
    live._git(
        repo,
        "config",
        "user.name",
        live.BASELINE_GIT_IDENTITY["name"],
    )
    live._git(
        repo,
        "config",
        "user.email",
        live.BASELINE_GIT_IDENTITY["email"],
    )
    (repo / "calc.py").write_bytes(b"return 1\n")
    live._git(repo, "add", "calc.py")
    live._git(repo, "commit", "-q", "-m", "baseline", env=live.COMMIT_ENV)
    baseline = live._git(repo, "rev-parse", "HEAD").decode().strip()
    live._git(repo, "config", "user.name", producer_identity["name"])
    live._git(repo, "config", "user.email", producer_identity["email"])
    (repo / "calc.py").write_bytes(b"return 2\n")
    live._git(repo, "add", "calc.py")
    live._git(repo, "commit", "-q", "-m", "output", env=live.COMMIT_ENV)
    output = live._git(repo, "rev-parse", "HEAD").decode().strip()
    bundle = tmp_path / "repo.bundle"
    live._git(repo, "bundle", "create", str(bundle), "--all")
    return bundle, baseline, output


def test_bundle_commit_identity_accepts_frozen_synthetic_metadata(
    tmp_path: Path,
) -> None:
    bundle, baseline, output = _identity_bundle(
        tmp_path,
        live.PRODUCER_GIT_IDENTITY,
    )
    result = live._verify_bundle_commit_identities(
        bundle,
        baseline_commit=baseline,
        output_commit=output,
        producer_identity=live.PRODUCER_GIT_IDENTITY,
    )
    assert result == {
        "baseline": live._expanded_git_identity(
            live.BASELINE_GIT_IDENTITY
        ),
        "output": live._expanded_git_identity(
            live.PRODUCER_GIT_IDENTITY
        ),
    }


def test_bundle_commit_identity_rejects_inherited_operator_metadata(
    tmp_path: Path,
) -> None:
    private_identity = {
        "email": "operator-private@example.invalid",
        "name": "Operator Private",
    }
    bundle, baseline, output = _identity_bundle(tmp_path, private_identity)
    with pytest.raises(
        live.CanaryError,
        match="outside frozen synthetic allowlist",
    ) as caught:
        live._verify_bundle_commit_identities(
            bundle,
            baseline_commit=baseline,
            output_commit=output,
            producer_identity=live.PRODUCER_GIT_IDENTITY,
        )
    assert private_identity["name"] not in str(caught.value)
    assert private_identity["email"] not in str(caught.value)


def test_bundle_commit_identity_rejects_private_merge_parent(
    tmp_path: Path,
) -> None:
    bundle, baseline, _ = _identity_bundle(
        tmp_path,
        live.PRODUCER_GIT_IDENTITY,
    )
    repo = tmp_path / "source"
    live._git(repo, "branch", "valid-output")
    live._git(repo, "checkout", "-q", "-b", "private-side", baseline)
    live._git(repo, "config", "user.name", "Private Side")
    live._git(repo, "config", "user.email", "private-side@example.invalid")
    (repo / "side.txt").write_bytes(b"private side\n")
    live._git(repo, "add", "side.txt")
    live._git(
        repo,
        "commit",
        "-q",
        "-m",
        "private side",
        env=live.COMMIT_ENV,
    )
    live._git(repo, "checkout", "-q", "valid-output")
    live._git(
        repo,
        "config",
        "user.name",
        live.PRODUCER_GIT_IDENTITY["name"],
    )
    live._git(
        repo,
        "config",
        "user.email",
        live.PRODUCER_GIT_IDENTITY["email"],
    )
    live._git(
        repo,
        "merge",
        "--no-ff",
        "-q",
        "-m",
        "merge output",
        "private-side",
        env=live.COMMIT_ENV,
    )
    output = live._git(repo, "rev-parse", "HEAD").decode().strip()
    bundle.unlink()
    live._git(repo, "bundle", "create", str(bundle), "--all")
    with pytest.raises(live.CanaryError, match="commit graph"):
        live._verify_bundle_commit_identities(
            bundle,
            baseline_commit=baseline,
            output_commit=output,
            producer_identity=live.PRODUCER_GIT_IDENTITY,
        )


def test_bundle_commit_identity_rejects_extra_private_ref(
    tmp_path: Path,
) -> None:
    bundle, baseline, output = _identity_bundle(
        tmp_path,
        live.PRODUCER_GIT_IDENTITY,
    )
    repo = tmp_path / "source"
    live._git(repo, "checkout", "-q", "-b", "private-ref", baseline)
    live._git(repo, "config", "user.name", "Private Ref")
    live._git(repo, "config", "user.email", "private-ref@example.invalid")
    (repo / "private.txt").write_bytes(b"private ref\n")
    live._git(repo, "add", "private.txt")
    live._git(
        repo,
        "commit",
        "-q",
        "-m",
        "private ref",
        env=live.COMMIT_ENV,
    )
    live._git(repo, "checkout", "-q", "-")
    bundle.unlink()
    live._git(repo, "bundle", "create", str(bundle), "--all")
    with pytest.raises(live.CanaryError, match="commit graph"):
        live._verify_bundle_commit_identities(
            bundle,
            baseline_commit=baseline,
            output_commit=output,
            producer_identity=live.PRODUCER_GIT_IDENTITY,
        )


def test_launcher_sets_and_verifies_repo_local_synthetic_identity() -> None:
    source = live.DEFAULT_SESSION_LAUNCHER.read_text(encoding="utf-8")
    assert "config --local user.name $syntheticGitName" in source
    assert "config --local user.email $syntheticGitEmail" in source
    assert "config --global" not in source
    assert live.PRODUCER_GIT_IDENTITY["name"] in source
    assert live.PRODUCER_GIT_IDENTITY["email"] in source
    assert "[string]$CodexHome" in source
    assert "$env:CODEX_HOME = $CodexHome" in source


@pytest.mark.parametrize(
    ("payload", "violation"),
    [
        (b"Authorization: Bearer abcdefghijklmnop", "credential_bearer"),
        (b"sk-examplecredentialvalue", "credential_openai_secret"),
        (b'{"access_token":"example"}', "credential_token_field"),
        (b'{"refresh_token":"example"}', "credential_token_field"),
        (b'{"id_token":"example"}', "credential_token_field"),
    ],
)
def test_public_privacy_scan_rejects_credential_markers(
    payload: bytes,
    violation: str,
) -> None:
    assert violation in live._privacy_violations(payload)


def _credential_plan(path: Path, pair_runner: Path, launcher: Path) -> Path:
    path.write_bytes(
        live._json_bytes(
            {
                "frozen_route": {
                    "launcher_implementation_sha256": live._sha256_file(
                        launcher
                    ),
                    "pair_runner_implementation_sha256": live._sha256_file(
                        pair_runner
                    ),
                },
                "schema": live.ROUTE_PLAN_SCHEMA,
            }
        )
    )
    return path


def _valid_credential_receipt(
    route_plan: Path,
    pair_runner: Path,
    launcher: Path,
) -> dict[str, object]:
    return {
        "auth_files_removed": True,
        "auth_route": "chatgpt",
        "credential_seed_compare": "PASS",
        "implementation": {
            "launcher_sha256": live._sha256_file(launcher),
            "pair_runner_sha256": live._sha256_file(pair_runner),
        },
        "login_status": {"A": "PASS", "B": "PASS"},
        "route_plan_sha256": live._sha256_file(route_plan),
        "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
        "secret_material_retained": False,
        "session_exit_codes": {"A": 0, "B": 0},
        "session_invocations": 2,
    }


def test_credential_receipt_accepts_only_exact_safe_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receipt.json"
    route_plan = _credential_plan(
        tmp_path / "route-plan.json",
        live.DEFAULT_PAIR_RUNNER,
        live.DEFAULT_SESSION_LAUNCHER,
    )
    receipt = _valid_credential_receipt(
        route_plan,
        live.DEFAULT_PAIR_RUNNER,
        live.DEFAULT_SESSION_LAUNCHER,
    )
    path.write_bytes(live._json_bytes(receipt))
    assert (
        live._validate_credential_runner_receipt(path, route_plan) == receipt
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("auth_files_removed", False),
        ("auth_route", "api_key"),
        ("credential_seed_compare", "FAIL"),
        ("secret_material_retained", True),
        ("session_invocations", 1),
        ("session_invocations", 3),
        (
            "implementation",
            {
                "launcher_sha256": "0" * 64,
                "pair_runner_sha256": "0" * 64,
            },
        ),
        ("route_plan_sha256", "0" * 64),
        ("credential_digest", "not-allowed"),
        ("credential_source_path", "not-allowed"),
    ],
)
def test_credential_receipt_rejects_failure_or_extra_fields(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    path = tmp_path / "receipt.json"
    route_plan = _credential_plan(
        tmp_path / "route-plan.json",
        live.DEFAULT_PAIR_RUNNER,
        live.DEFAULT_SESSION_LAUNCHER,
    )
    receipt = _valid_credential_receipt(
        route_plan,
        live.DEFAULT_PAIR_RUNNER,
        live.DEFAULT_SESSION_LAUNCHER,
    )
    receipt[field] = value
    path.write_bytes(live._json_bytes(receipt))
    with pytest.raises(live.CanaryError, match="receipt is invalid"):
        live._validate_credential_runner_receipt(path, route_plan)


def test_hand_authored_exact_receipt_cannot_bypass_orchestrator(
    tmp_path: Path,
) -> None:
    route_plan = _credential_plan(
        tmp_path / "route-plan.json",
        live.DEFAULT_PAIR_RUNNER,
        live.DEFAULT_SESSION_LAUNCHER,
    )
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(
        live._json_bytes(
            _valid_credential_receipt(
                route_plan,
                live.DEFAULT_PAIR_RUNNER,
                live.DEFAULT_SESSION_LAUNCHER,
            )
        )
    )
    assert not hasattr(live, "_build_orchestrated")
    assert not hasattr(live, "_ORCHESTRATION_CAPABILITY")
    with pytest.raises(SystemExit):
        live._parser().parse_args(["build"])


def _write_fake_codex(path: Path) -> None:
    path.write_text(
        "\r\n".join(
            [
                "@echo off",
                'if not exist "%CODEX_HOME%\\auth.json" exit /b 11',
                'if "%1"=="login" (',
                '  echo login>>"%FAKE_CODEX_LOG%"',
                '  if /i "%CODEX_HOME%"=="%FAIL_CODEX_HOME%" exit /b 12',
                "  echo Logged in using ChatGPT",
                "  exit /b 0",
                ")",
                'if "%1"=="exec" goto exec_call',
                "exit /b 13",
                ":exec_call",
                'echo exec>>"%FAKE_CODEX_LOG%"',
                'if exist "%FAIL_A_MARKER%" goto fail_exec',
                (
                    'if exist "%FAIL_B_MARKER%" '
                    'if exist "%FAIL_B_ARMED%" goto fail_exec'
                ),
                'if exist "%FAIL_B_MARKER%" type nul > "%FAIL_B_ARMED%"',
                "echo fake session output",
                "exit /b 0",
                ":fail_exec",
                'if exist "%FAIL_A_MARKER%" del "%FAIL_A_MARKER%"',
                "exit /b 14",
                "",
            ]
        ),
        encoding="utf-8",
        newline="",
    )


def _run_fake_pair(
    tmp_path: Path,
    *,
    fail_b_login: bool,
    fail_exec: str | None = None,
    tamper: str | None = None,
    outside_temp: bool = False,
):
    root = Path(tempfile.mkdtemp(prefix="gate3-credential-test-"))
    fake = root / "fake-codex.cmd"
    _write_fake_codex(fake)
    credential = root / "private-auth.json"
    credential.write_text('{"fake":"credential"}\n', encoding="utf-8")
    runtime = root / "runtime"
    runtime.mkdir()
    pair_runner = runtime / live.DEFAULT_PAIR_RUNNER.name
    launcher = runtime / live.DEFAULT_SESSION_LAUNCHER.name
    pair_source = live.DEFAULT_PAIR_RUNNER.read_text(encoding="utf-8")
    production_binding = (
        "$credentialSource = Join-Path "
        "([Environment]::GetFolderPath('UserProfile')) "
        "'.codex\\auth.json'"
    )
    assert production_binding in pair_source
    pair_runner.write_text(
        pair_source.replace(
            production_binding,
            "$credentialSource = " + repr(str(credential)),
            1,
        ),
        encoding="utf-8",
        newline="\n",
    )
    launcher.write_bytes(live.DEFAULT_SESSION_LAUNCHER.read_bytes())
    route_plan = _credential_plan(
        root / "route-plan.json", pair_runner, launcher
    )
    if tamper == "runner":
        pair_runner.write_text(
            pair_runner.read_text(encoding="utf-8") + "\n# tampered\n",
            encoding="utf-8",
            newline="\n",
        )
    elif tamper == "launcher":
        launcher.write_text(
            launcher.read_text(encoding="utf-8") + "\n# tampered\n",
            encoding="utf-8",
            newline="\n",
        )
    log = root / "calls.txt"
    private = root / "private"
    private.mkdir()
    receipt = private / "credential-runner-receipt.json"
    homes = {"A": root / "home-a", "B": root / "home-b"}
    repos = {"A": root / "repo-a", "B": root / "repo-b"}
    prompts = {"A": root / "prompt-a.txt", "B": root / "prompt-b.txt"}
    for treatment in ("A", "B"):
        homes[treatment].mkdir()
        repos[treatment].mkdir()
        live._git(repos[treatment], "init", "-q")
        prompts[treatment].write_text(
            f"fake prompt {treatment}\n", encoding="utf-8"
        )
    env = os.environ.copy()
    env["FAKE_CODEX_LOG"] = str(log)
    env["FAIL_CODEX_HOME"] = str(homes["B"]) if fail_b_login else ""
    fail_a_marker = root / "fail-a.marker"
    fail_b_marker = root / "fail-b.marker"
    fail_b_armed = root / "fail-b.armed"
    if fail_exec == "A":
        fail_a_marker.write_text("fail\n", encoding="utf-8")
    elif fail_exec == "B":
        fail_b_marker.write_text("fail\n", encoding="utf-8")
    env["FAIL_A_MARKER"] = str(fail_a_marker)
    env["FAIL_B_MARKER"] = str(fail_b_marker)
    env["FAIL_B_ARMED"] = str(fail_b_armed)
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(pair_runner),
        "-CodexCommand",
        str(fake),
        "-RoutePlanPath",
        str(route_plan),
        "-ArmAWorkspace",
        str(tmp_path if outside_temp else repos["A"]),
        "-ArmBWorkspace",
        str(repos["B"]),
        "-ArmAPromptPath",
        str(prompts["A"]),
        "-ArmBPromptPath",
        str(prompts["B"]),
        "-ArmACodexHome",
        str(homes["A"]),
        "-ArmBCodexHome",
        str(homes["B"]),
        "-ArmAStdoutPath",
        str(private / "a.stdout"),
        "-ArmBStdoutPath",
        str(private / "b.stdout"),
        "-ArmAStderrPath",
        str(private / "a.stderr"),
        "-ArmBStderrPath",
        str(private / "b.stderr"),
        "-ArmAExitCodePath",
        str(private / "a.exit"),
        "-ArmBExitCodePath",
        str(private / "b.exit"),
        "-PrivateReceiptPath",
        str(receipt),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        env=env,
        text=True,
        timeout=60,
    )
    return (
        result,
        credential,
        log,
        receipt,
        homes,
        route_plan,
        pair_runner,
        launcher,
        root,
    )


def test_pair_runner_preflights_then_invokes_exactly_two_fake_sessions(
    tmp_path: Path,
) -> None:
    result_data = _run_fake_pair(tmp_path, fail_b_login=False)
    (
        result,
        credential,
        log,
        receipt_path,
        homes,
        route_plan,
        pair_runner,
        launcher,
        root,
    ) = result_data
    try:
        assert result.returncode == 0, result.stderr
        assert log.read_text(encoding="utf-8").splitlines() == [
            "login",
            "login",
            "exec",
            "exec",
        ]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt == _valid_credential_receipt(
            route_plan, pair_runner, launcher
        )
        assert (
            credential.read_text(encoding="utf-8")
            == '{"fake":"credential"}\n'
        )
        assert not (homes["A"] / "auth.json").exists()
        assert not (homes["B"] / "auth.json").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pair_runner_failed_preflight_starts_zero_fake_sessions_and_cleans(
    tmp_path: Path,
) -> None:
    result, _, log, receipt_path, homes, _, _, _, root = _run_fake_pair(
        tmp_path, fail_b_login=True
    )
    try:
        assert result.returncode == 2
        assert log.read_text(encoding="utf-8").splitlines() == [
            "login",
            "login",
        ]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["session_invocations"] == 0
        assert receipt["login_status"] == {"A": "PASS", "B": "FAIL"}
        assert not (homes["A"] / "auth.json").exists()
        assert not (homes["B"] / "auth.json").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize(
    ("failed_treatment", "expected_exits"),
    [
        ("A", {"A": 14, "B": 0}),
        ("B", {"A": 0, "B": 14}),
    ],
)
def test_pair_runner_arm_failure_still_invokes_each_session_once_and_cleans(
    tmp_path: Path,
    failed_treatment: str,
    expected_exits: dict[str, int],
) -> None:
    result, _, log, receipt_path, homes, _, _, _, root = _run_fake_pair(
        tmp_path,
        fail_b_login=False,
        fail_exec=failed_treatment,
    )
    try:
        assert result.returncode == 1
        assert log.read_text(encoding="utf-8").splitlines() == [
            "login",
            "login",
            "exec",
            "exec",
        ]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["session_invocations"] == 2
        assert receipt["session_exit_codes"] == expected_exits
        assert not (homes["A"] / "auth.json").exists()
        assert not (homes["B"] / "auth.json").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pair_runner_binds_production_auth_and_user_temp() -> None:
    source = live.DEFAULT_PAIR_RUNNER.read_text(encoding="utf-8")
    assert "[string]$CredentialSource" not in source
    assert (
        "$credentialSource = Join-Path "
        "([Environment]::GetFolderPath('UserProfile')) "
        "'.codex\\auth.json'"
    ) in source
    assert "[System.IO.Path]::GetTempPath()" in source
    assert "pair_runner_implementation_sha256" in source
    assert "launcher_implementation_sha256" in source
    launcher = live.DEFAULT_SESSION_LAUNCHER.read_text(encoding="utf-8")
    assert "[string]$ExpectedLauncherSha256" in launcher
    assert "$observedLauncherSha256 -ne $ExpectedLauncherSha256" in launcher


@pytest.mark.parametrize("tamper", ["runner", "launcher"])
def test_pair_runner_rejects_unpinned_implementation_before_login(
    tmp_path: Path,
    tamper: str,
) -> None:
    result, _, log, receipt, _, _, _, _, root = _run_fake_pair(
        tmp_path,
        fail_b_login=False,
        tamper=tamper,
    )
    try:
        assert result.returncode != 0
        assert not log.exists()
        assert not receipt.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pair_runner_rejects_non_temp_private_runtime_before_login(
    tmp_path: Path,
) -> None:
    result, _, log, receipt, _, _, _, _, root = _run_fake_pair(
        tmp_path,
        fail_b_login=False,
        outside_temp=True,
    )
    try:
        assert result.returncode != 0
        assert not log.exists()
        assert not receipt.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _set_orchestrator_builder(
    monkeypatch: pytest.MonkeyPatch,
    builder: object,
) -> None:
    closure = dict(
        zip(
            live.orchestrate.__code__.co_freevars,
            live.orchestrate.__closure__ or (),
            strict=True,
        )
    )
    monkeypatch.setattr(closure["builder"], "cell_contents", builder)


def test_private_cleanup_removes_readonly_git_objects(tmp_path: Path) -> None:
    private_root = tmp_path / "private"
    git_object = private_root / "repo-a" / ".git" / "objects" / "object"
    git_object.parent.mkdir(parents=True)
    git_object.write_bytes(b"synthetic git object")
    git_object.chmod(stat.S_IREAD)
    live._remove_private_tree(private_root)
    assert not private_root.exists()


@pytest.mark.parametrize(
    "failure_phase",
    ["preflight", "arm_a", "arm_b", "build"],
)
def test_orchestrator_cleans_every_private_asset_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_phase: str,
) -> None:
    private_root = tmp_path / "private-runtime"
    output = tmp_path / "published"
    monkeypatch.setattr(
        live.tempfile,
        "mkdtemp",
        lambda **_: str(private_root.mkdir() or private_root),
    )
    monkeypatch.setattr(live.shutil, "which", lambda _: "npm.cmd")

    def fake_prepare(
        _repo: Path,
        staging: Path,
        **_: object,
    ) -> dict[str, object]:
        (staging / "inputs").mkdir(parents=True)
        for name in (
            "baseline.bundle",
            "producer-prompt-a.txt",
            "producer-prompt-b.txt",
        ):
            (staging / "inputs" / name).write_text(
                "synthetic\n", encoding="utf-8"
            )
        (staging / "route-plan.json").write_text(
            "{}\n", encoding="utf-8"
        )
        return {}

    def fake_private_process(command: list[str], *, label: str) -> None:
        if label == "temporary Codex CLI installation":
            codex = (
                private_root
                / "cli"
                / "node_modules"
                / ".bin"
                / "codex.cmd"
            )
            codex.parent.mkdir(parents=True)
            codex.write_text("@echo off\n", encoding="utf-8")
        elif "repository" in label:
            Path(command[-1]).mkdir(parents=True)

    process_count = 0
    observed_pair_states: list[dict[str, object]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        nonlocal process_count
        process_count += 1
        if "--version" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=f"codex-cli {live.DEFAULT_CLI_VERSION}",
                stderr="",
            )
        raw = private_root / "raw"
        (raw / "private-rollout.jsonl").write_text(
            "private\n", encoding="utf-8"
        )
        pair_states = {
            "preflight": {
                "session_invocations": 0,
                "session_exit_codes": {"A": None, "B": None},
            },
            "arm_a": {
                "session_invocations": 2,
                "session_exit_codes": {"A": 14, "B": 0},
            },
            "arm_b": {
                "session_invocations": 2,
                "session_exit_codes": {"A": 0, "B": 14},
            },
            "build": {
                "session_invocations": 2,
                "session_exit_codes": {"A": 0, "B": 0},
            },
        }
        observed_pair_states.append(pair_states[failure_phase])
        state = pair_states[failure_phase]
        receipt_path = Path(
            command[command.index("-PrivateReceiptPath") + 1]
        )
        receipt_path.write_text(
            json.dumps(
                {
                    "login_status": (
                        {"A": "FAIL", "B": "FAIL"}
                        if failure_phase == "preflight"
                        else {"A": "PASS", "B": "PASS"}
                    ),
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": state["session_exit_codes"],
                    "session_invocations": state["session_invocations"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode={
                "preflight": 2,
                "arm_a": 1,
                "arm_b": 1,
                "build": 0,
            }[failure_phase],
            stdout=b"",
            stderr=b"",
        )

    def fake_build(
        _repo: Path,
        _staging: Path,
        built: Path,
        **kwargs: object,
    ) -> dict[str, object]:
        if failure_phase == "build":
            diagnostics = kwargs["rollout_diagnostics"]
            assert isinstance(diagnostics, dict)
            diagnostics["A"]["parse_phases"]["source"] = "FAIL"
            diagnostics["A"]["source_census"] = {
                "full_true_count": 0,
                "object_payload_count": 0,
                "raw_count": 0,
                "state_object_count": 0,
            }
            raise live.CanaryError("synthetic build failure")
        built.mkdir()
        (built / "canary-summary.json").write_text(
            "{}\n", encoding="utf-8"
        )
        return {"status": "PASS"}

    monkeypatch.setattr(live, "prepare", fake_prepare)
    monkeypatch.setattr(live, "_run_private_process", fake_private_process)
    monkeypatch.setattr(live.subprocess, "run", fake_run)
    _set_orchestrator_builder(monkeypatch, fake_build)
    monkeypatch.setattr(
        live,
        "_single_rollout",
        lambda home: home / "sessions" / "rollout.jsonl",
    )
    monkeypatch.setattr(
        live,
        "verify",
        lambda *_: {"status": "PASS"},
    )
    with pytest.raises(live.CanaryError):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert process_count == 2
    assert observed_pair_states == [
        {
            "preflight": {
                "session_invocations": 0,
                "session_exit_codes": {"A": None, "B": None},
            },
            "arm_a": {
                "session_invocations": 2,
                "session_exit_codes": {"A": 14, "B": 0},
            },
            "arm_b": {
                "session_invocations": 2,
                "session_exit_codes": {"A": 0, "B": 14},
            },
            "build": {
                "session_invocations": 2,
                "session_exit_codes": {"A": 0, "B": 0},
            },
        }[failure_phase]
    ]
    assert not private_root.exists()
    assert not output.exists()
    assert list(tmp_path.glob(".published.candidate-*")) == []
    failure_root = output.with_name(f"{output.name}.failure")
    receipt_path = failure_root / "failure-receipt.json"
    assert receipt_path.is_file()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == live.FAILURE_RECEIPT_SCHEMA
    assert receipt["scoreable"] is False
    assert receipt["success_packet_admitted"] is False
    assert receipt["success_packet_publication_attempted"] is False
    assert receipt["cleanup"] == {"residue_classes": [], "status": "PASS"}
    assert receipt["execution"]["session_invocations"] == {
        "preflight": 0,
        "arm_a": 2,
        "arm_b": 2,
        "build": 2,
    }[failure_phase]
    assert receipt["execution"]["session_exit_codes"] == {
        "preflight": {"A": None, "B": None},
        "arm_a": {"A": 14, "B": 0},
        "arm_b": {"A": 0, "B": 14},
        "build": {"A": 0, "B": 0},
    }[failure_phase]
    assert receipt["failure_stage"] == {
        "preflight": "pair_execution",
        "arm_a": "pair_execution",
        "arm_b": "pair_execution",
        "build": "packet_build",
    }[failure_phase]
    if failure_phase == "build":
        assert receipt["rollout_diagnostics"]["A"] == {
            "parse_phases": {
                "public": "NOT_RUN",
                "source": "FAIL",
            },
            "public_census": None,
            "source_census": {
                "full_true_count": 0,
                "object_payload_count": 0,
                "raw_count": 0,
                "state_object_count": 0,
            },
        }
        assert set(receipt["rollout_diagnostics"]) == {"A", "B"}
    else:
        assert "rollout_diagnostics" not in receipt
    assert live._privacy_violations(receipt_path.read_bytes()) == []
    assert list(tmp_path.glob(".published.failure-candidate-*")) == []


def test_orchestrator_publishes_only_after_verified_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root = tmp_path / "private-runtime"
    output = tmp_path / "published"
    monkeypatch.setattr(
        live.tempfile,
        "mkdtemp",
        lambda **_: str(private_root.mkdir() or private_root),
    )
    monkeypatch.setattr(live.shutil, "which", lambda _: "npm.cmd")

    def fake_prepare(
        _repo: Path,
        staging: Path,
        **_: object,
    ) -> dict[str, object]:
        (staging / "inputs").mkdir(parents=True)
        for name in (
            "baseline.bundle",
            "producer-prompt-a.txt",
            "producer-prompt-b.txt",
        ):
            (staging / "inputs" / name).write_text(
                "synthetic\n", encoding="utf-8"
            )
        (staging / "route-plan.json").write_text(
            "{}\n", encoding="utf-8"
        )
        return {}

    def fake_private_process(command: list[str], *, label: str) -> None:
        if label == "temporary Codex CLI installation":
            codex = (
                private_root
                / "cli"
                / "node_modules"
                / ".bin"
                / "codex.cmd"
            )
            codex.parent.mkdir(parents=True)
            codex.write_text("@echo off\n", encoding="utf-8")
        elif "repository" in label:
            Path(command[-1]).mkdir(parents=True)

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        if "--version" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=f"codex-cli {live.DEFAULT_CLI_VERSION}",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def fake_build(
        _repo: Path,
        _staging: Path,
        built: Path,
        **_: object,
    ) -> dict[str, object]:
        built.mkdir()
        (built / "canary-summary.json").write_text(
            "{}\n", encoding="utf-8"
        )
        return {"status": "PASS"}

    monkeypatch.setattr(live, "prepare", fake_prepare)
    monkeypatch.setattr(live, "_run_private_process", fake_private_process)
    monkeypatch.setattr(live.subprocess, "run", fake_run)
    _set_orchestrator_builder(monkeypatch, fake_build)
    monkeypatch.setattr(
        live,
        "_single_rollout",
        lambda home: home / "sessions" / "rollout.jsonl",
    )
    monkeypatch.setattr(
        live,
        "verify",
        lambda *_: {"status": "PASS"},
    )
    result = live.orchestrate(tmp_path, output, run_id="synthetic")
    assert result == {"status": "PASS"}
    assert output.is_dir()
    assert not private_root.exists()
    assert list(tmp_path.glob(".published.candidate-*")) == []
    assert not output.with_name(f"{output.name}.failure").exists()


def _mock_successful_orchestrator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_post_publish_verify: bool = False,
) -> tuple[Path, Path]:
    private_root = tmp_path / "private-runtime-edge"
    output = tmp_path / "published-edge"
    monkeypatch.setattr(
        live.tempfile,
        "mkdtemp",
        lambda **_: str(private_root.mkdir() or private_root),
    )
    monkeypatch.setattr(live.shutil, "which", lambda _: "npm.cmd")
    monkeypatch.setattr(live.secrets, "token_hex", lambda _: "fixed")

    def fake_prepare(
        _repo: Path,
        staging: Path,
        **_: object,
    ) -> dict[str, object]:
        (staging / "inputs").mkdir(parents=True)
        for name in (
            "baseline.bundle",
            "producer-prompt-a.txt",
            "producer-prompt-b.txt",
        ):
            (staging / "inputs" / name).write_text(
                "synthetic\n", encoding="utf-8"
            )
        (staging / "route-plan.json").write_text(
            "{}\n", encoding="utf-8"
        )
        return {}

    def fake_private_process(command: list[str], *, label: str) -> None:
        if label == "temporary Codex CLI installation":
            codex = (
                private_root
                / "cli"
                / "node_modules"
                / ".bin"
                / "codex.cmd"
            )
            codex.parent.mkdir(parents=True)
            codex.write_text("@echo off\n", encoding="utf-8")
        elif "repository" in label:
            Path(command[-1]).mkdir(parents=True)

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        if "--version" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=f"codex-cli {live.DEFAULT_CLI_VERSION}",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def fake_build(
        _repo: Path,
        _staging: Path,
        built: Path,
        **_: object,
    ) -> dict[str, object]:
        built.mkdir()
        (built / "canary-summary.json").write_text(
            "{}\n", encoding="utf-8"
        )
        return {"status": "PASS"}

    def fake_verify(_repo: Path, root: Path) -> dict[str, object]:
        if fail_post_publish_verify and root == output:
            raise live.CanaryError("synthetic post-publish verify failure")
        return {"status": "PASS"}

    monkeypatch.setattr(live, "prepare", fake_prepare)
    monkeypatch.setattr(live, "_run_private_process", fake_private_process)
    monkeypatch.setattr(live.subprocess, "run", fake_run)
    _set_orchestrator_builder(monkeypatch, fake_build)
    monkeypatch.setattr(
        live,
        "_single_rollout",
        lambda home: home / "sessions" / "rollout.jsonl",
    )
    monkeypatch.setattr(live, "verify", fake_verify)
    return private_root, output


def test_orchestrator_collision_cleans_private_root_without_deleting_foreign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path, monkeypatch
    )
    collision = tmp_path / ".published-edge.candidate-fixed"
    collision.mkdir()
    with pytest.raises(live.CanaryError, match="candidate path"):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert not private_root.exists()
    assert collision.is_dir()
    assert not output.exists()


def test_orchestrator_atomic_candidate_race_preserves_foreign_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path, monkeypatch
    )
    candidate = tmp_path / ".published-edge.candidate-fixed"
    real_mkdir = os.mkdir

    def racing_mkdir(path: object, mode: int = 0o777) -> None:
        if Path(path) == candidate:
            real_mkdir(path, mode)
            (candidate / "foreign.marker").write_text(
                "foreign\n", encoding="utf-8"
            )
            raise FileExistsError("synthetic candidate race")
        real_mkdir(path, mode)

    monkeypatch.setattr(live.os, "mkdir", racing_mkdir)
    with pytest.raises(FileExistsError, match="candidate race"):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert not private_root.exists()
    assert (candidate / "foreign.marker").read_text(
        encoding="utf-8"
    ) == "foreign\n"
    assert not output.exists()


def test_orchestrator_replace_failure_cleans_candidate_and_private_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path, monkeypatch
    )
    real_replace = live.os.replace
    replace_calls = 0

    def fail_first_replace(source: object, destination: object) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            raise OSError("synthetic replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(live.os, "replace", fail_first_replace)
    with pytest.raises(OSError, match="synthetic replace failure"):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert not private_root.exists()
    assert not output.exists()
    assert not (tmp_path / ".published-edge.candidate-fixed").exists()
    receipt = json.loads(
        (
            output.with_name(f"{output.name}.failure")
            / "failure-receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert replace_calls == 2
    assert receipt["failure_stage"] == "success_publication"
    assert receipt["success_packet_admitted"] is False
    assert receipt["success_packet_publication_attempted"] is True
    assert receipt["success_packet_present"] is False


def test_orchestrator_post_publish_verify_failure_removes_new_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path,
        monkeypatch,
        fail_post_publish_verify=True,
    )
    with pytest.raises(live.CanaryError, match="post-publish"):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert not private_root.exists()
    assert not output.exists()
    assert not (tmp_path / ".published-edge.candidate-fixed").exists()
    failure_receipt = json.loads(
        (
            output.with_name(f"{output.name}.failure")
            / "failure-receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert failure_receipt["success_packet_admitted"] is False
    assert failure_receipt["success_packet_publication_attempted"] is True
    assert failure_receipt["success_packet_present"] is False


@pytest.mark.parametrize(
    ("invocations", "exit_codes"),
    [
        (0, {"A": None, "B": None}),
        (1, {"A": 7, "B": None}),
        (2, {"A": 0, "B": 9}),
    ],
)
def test_failure_execution_summary_preserves_exact_session_count(
    tmp_path: Path,
    invocations: int,
    exit_codes: dict[str, int | None],
) -> None:
    receipt = tmp_path / "credential-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "login_status": {"A": "PASS", "B": "PASS"},
                "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                "session_exit_codes": exit_codes,
                "session_invocations": invocations,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = live._failure_execution_summary(receipt, pair_started=True)
    assert summary == {
        "credential_preflight": "PASS",
        "login_status": {"A": "PASS", "B": "PASS"},
        "runner_receipt_status": "VALID",
        "session_exit_codes": exit_codes,
        "session_invocations": invocations,
    }


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        (b'{"schema":', "INVALID"),
        (
            json.dumps(
                {
                    "access_token": "sk-synthetic-secret-material",
                    "login_status": {"A": "PASS", "B": "PASS"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": None, "B": None},
                    "session_invocations": 0,
                }
            ).encode("utf-8"),
            "PRIVACY_REJECTED",
        ),
        (
            json.dumps(
                {
                    "login_status": {"A": "PASS", "B": "PASS"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": 7, "B": 9},
                    "session_invocations": 0,
                }
            ).encode("utf-8"),
            "INVALID",
        ),
        (
            json.dumps(
                {
                    "login_status": {"A": "PASS", "B": "PASS"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": None, "B": 7},
                    "session_invocations": 1,
                }
            ).encode("utf-8"),
            "INVALID",
        ),
        (
            json.dumps(
                {
                    "login_status": {"A": "PASS", "B": "PASS"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": 0, "B": None},
                    "session_invocations": 2,
                }
            ).encode("utf-8"),
            "INVALID",
        ),
        (
            json.dumps(
                {
                    "login_status": {"A": "FAIL", "B": "FAIL"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": 7, "B": None},
                    "session_invocations": 1,
                }
            ).encode("utf-8"),
            "INVALID",
        ),
        (
            json.dumps(
                {
                    "login_status": {"A": "PASS", "B": "FAIL"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": 0, "B": 9},
                    "session_invocations": 2,
                }
            ).encode("utf-8"),
            "INVALID",
        ),
    ],
)
def test_failure_execution_summary_rejects_untrusted_receipts_without_throwing(
    tmp_path: Path,
    payload: bytes,
    expected_status: str,
) -> None:
    receipt = tmp_path / "credential-receipt.json"
    receipt.write_bytes(payload)
    summary = live._failure_execution_summary(receipt, pair_started=True)
    assert summary["runner_receipt_status"] == expected_status
    assert summary["session_invocations"] is None


def test_orchestrator_cleanup_failure_publishes_only_negative_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path,
        monkeypatch,
    )
    real_remove = live._remove_private_tree

    def leave_private_residue(path: Path) -> None:
        if path == private_root:
            return
        real_remove(path)

    monkeypatch.setattr(live, "_remove_private_tree", leave_private_residue)
    with pytest.raises(
        live.CanaryError,
        match="failed runtime artifact cleanup verification",
    ):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert not output.exists()
    receipt_path = (
        output.with_name(f"{output.name}.failure") / "failure-receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["failure_stage"] == "private_cleanup"
    assert receipt["cleanup"] == {
        "residue_classes": ["private_runtime"],
        "status": "FAIL",
    }
    assert receipt["scoreable"] is False
    assert receipt["success_packet_admitted"] is False
    assert receipt["success_packet_present"] is False
    assert receipt["success_packet_publication_attempted"] is False
    assert live._privacy_violations(receipt_path.read_bytes()) == []


def test_truncated_runner_receipt_cannot_skip_cleanup_or_negative_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path,
        monkeypatch,
    )

    def truncated_pair(command: list[str], **_: object) -> SimpleNamespace:
        if "--version" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=f"codex-cli {live.DEFAULT_CLI_VERSION}",
                stderr="",
            )
        receipt_path = Path(
            command[command.index("-PrivateReceiptPath") + 1]
        )
        receipt_path.write_bytes(b'{"schema":')
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(live.subprocess, "run", truncated_pair)
    with pytest.raises(live.CanaryError, match="authorized A/B pair failed"):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    assert not private_root.exists()
    receipt_path = (
        output.with_name(f"{output.name}.failure") / "failure-receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["failure_stage"] == "pair_execution"
    assert receipt["execution"]["runner_receipt_status"] == "INVALID"
    assert receipt["execution"]["session_invocations"] is None
    assert receipt["cleanup"] == {"residue_classes": [], "status": "PASS"}


def test_pair_failure_stage_survives_cleanup_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root, output = _mock_successful_orchestrator(
        tmp_path,
        monkeypatch,
    )

    def failed_pair(command: list[str], **_: object) -> SimpleNamespace:
        if "--version" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=f"codex-cli {live.DEFAULT_CLI_VERSION}",
                stderr="",
            )
        receipt_path = Path(
            command[command.index("-PrivateReceiptPath") + 1]
        )
        receipt_path.write_text(
            json.dumps(
                {
                    "login_status": {"A": "PASS", "B": "PASS"},
                    "schema": live.CREDENTIAL_RECEIPT_SCHEMA,
                    "session_exit_codes": {"A": 14, "B": 0},
                    "session_invocations": 2,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"")

    real_remove = live._remove_private_tree

    def leave_private_residue(path: Path) -> None:
        if path == private_root:
            return
        real_remove(path)

    monkeypatch.setattr(live.subprocess, "run", failed_pair)
    monkeypatch.setattr(live, "_remove_private_tree", leave_private_residue)
    with pytest.raises(
        live.CanaryError,
        match="failed runtime artifact cleanup verification",
    ):
        live.orchestrate(tmp_path, output, run_id="synthetic")
    receipt_path = (
        output.with_name(f"{output.name}.failure") / "failure-receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["failure_stage"] == "pair_execution"
    assert receipt["execution"]["session_exit_codes"] == {"A": 14, "B": 0}
    assert receipt["cleanup"] == {
        "residue_classes": ["private_runtime"],
        "status": "FAIL",
    }


def test_failure_receipt_is_complete_before_atomic_publication_and_redacts_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "published"
    observed_candidates: list[dict[str, object]] = []
    real_rename = live.os.rename

    def observing_rename(source: object, destination: object) -> None:
        candidate_receipt = Path(source) / "failure-receipt.json"
        observed_candidates.append(
            json.loads(candidate_receipt.read_text(encoding="utf-8"))
        )
        real_rename(source, destination)

    monkeypatch.setattr(live.os, "rename", observing_rename)
    receipt_path = live._publish_failure_receipt(
        output,
        run_id="eyJhbGciOiJIUzI1NiJ9.secret.signature",
        failure_stage="packet_build",
        execution={
            "credential_preflight": "PASS",
            "login_status": {"A": "PASS", "B": "PASS"},
            "runner_receipt_status": "VALID",
            "session_exit_codes": {"A": 0, "B": 3},
            "session_invocations": 2,
        },
        cleanup_status="PASS",
        residue_classes=[],
        success_packet_publication_attempted=False,
        success_packet_present=False,
        rollout_diagnostics={
            "A": {
                "parse_phases": {
                    "source": "FAIL",
                    "public": "NOT_RUN",
                },
                "source_census": {
                    "full_true_count": 0,
                    "object_payload_count": 0,
                    "raw_count": 1,
                    "state_object_count": 0,
                },
                "private_path": "C:/Users/private/rollout.jsonl",
            },
            "B": {
                "parse_phases": {
                    "source": "PASS",
                    "public": "FAIL",
                },
                "source_census": {
                    "full_true_count": 1,
                    "object_payload_count": 1,
                    "raw_count": 1,
                    "state_object_count": 1,
                },
                "public_census": {
                    "full_true_count": 2,
                    "object_payload_count": 2,
                    "raw_count": 2,
                    "state_object_count": 2,
                },
                "private_blob_marker": "private",
            },
        },
    )
    published = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert observed_candidates == [published]
    assert published["run_id"] == "REDACTED"
    assert published["rollout_diagnostics"] == {
        "A": {
            "parse_phases": {
                "public": "NOT_RUN",
                "source": "FAIL",
            },
            "public_census": None,
            "source_census": {
                "full_true_count": 0,
                "object_payload_count": 0,
                "raw_count": 1,
                "state_object_count": 0,
            },
        },
        "B": {
            "parse_phases": {
                "public": "FAIL",
                "source": "PASS",
            },
            "public_census": {
                "full_true_count": 2,
                "object_payload_count": 2,
                "raw_count": 2,
                "state_object_count": 2,
            },
            "source_census": {
                "full_true_count": 1,
                "object_payload_count": 1,
                "raw_count": 1,
                "state_object_count": 1,
            },
        },
    }
    assert "private_path" not in receipt_path.read_text(encoding="utf-8")
    assert "private_blob_marker" not in receipt_path.read_text(encoding="utf-8")
    assert live._privacy_violations(receipt_path.read_bytes()) == []


def test_orchestrator_rejects_non_public_run_id_before_private_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root_created = False

    def forbidden_mkdtemp(**_: object) -> str:
        nonlocal private_root_created
        private_root_created = True
        raise AssertionError("private work must not start")

    monkeypatch.setattr(live.tempfile, "mkdtemp", forbidden_mkdtemp)
    with pytest.raises(live.CanaryError, match="privacy-safe"):
        live.orchestrate(
            tmp_path,
            tmp_path / "published",
            run_id="eyJhbGciOiJIUzI1NiJ9.secret.signature",
        )
    assert private_root_created is False
