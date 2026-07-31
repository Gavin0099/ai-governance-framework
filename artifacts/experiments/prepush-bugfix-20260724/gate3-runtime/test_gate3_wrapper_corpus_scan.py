"""Tests for the rollout corpus scanner.

The scanner reads private material, so most of what matters here is what it
refuses to emit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate3_codex_live_canary as live  # noqa: E402
import gate3_wrapper_corpus_scan as scan  # noqa: E402

WORKSPACE = "C:/workspace"
SECRET_COMMAND = "Get-Content C:/Users/private/.codex/auth.json"


def _record(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _corpus(root: Path, cli_version: str, inputs: list[str]) -> Path:
    path = root / f"rollout-{cli_version}.jsonl"
    lines = [
        _record(
            {
                "payload": {"cli_version": cli_version, "id": "session"},
                "type": "session_meta",
            }
        )
    ]
    lines += [
        _record(
            {
                "payload": {
                    "input": source,
                    "name": "exec",
                    "type": "custom_tool_call",
                },
                "type": "response_item",
            }
        )
        for source in inputs
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _accepted() -> str:
    return (
        'const r = await tools.shell_command({command:"git rev-parse HEAD",'
        f'workdir:{json.dumps(WORKSPACE)}}}); text(r)\n'
    )


def _rejected_with_secret() -> str:
    return (
        "const r = await tools.shell_command({command:"
        + json.dumps(SECRET_COMMAND)
        + ",timeout_ms:120000,workdir:"
        + json.dumps(WORKSPACE)
        + "}); text(r)\n"
    )


def test_scan_counts_acceptance_per_cli_version(tmp_path: Path) -> None:
    _corpus(tmp_path, "1.0.0", [_accepted(), _rejected_with_secret()])
    _corpus(tmp_path, "2.0.0", [_rejected_with_secret()])
    report = scan.scan(tmp_path, min_signature_count=1)
    assert report["exec_tool_calls"] == 3
    assert report["exec_tool_calls_accepted"] == 1
    assert report["by_cli_version"] == {
        "1.0.0": {"accepted": 1, "total": 2},
        "2.0.0": {"accepted": 0, "total": 1},
    }
    assert report["sessions_with_exec_calls"] == 2


def test_thin_signatures_are_folded_into_a_count_only_bucket(
    tmp_path: Path,
) -> None:
    """A signature seen once could identify the session that produced it."""
    common = [_rejected_with_secret()] * 6
    rare = (
        'const r = await tools.shell_command({command:"git status",'
        "login:false,workdir:" + json.dumps(WORKSPACE) + "}); text(r)\n"
    )
    _corpus(tmp_path, "1.0.0", common + [rare])
    report = scan.scan(tmp_path, min_signature_count=5)
    assert report["distinct_rejected_signatures"] == 2
    assert len(report["rejected_signatures"]) == 1
    assert report["rejected_signatures"][0]["count"] == 6
    assert report["below_threshold"] == {
        "distinct_signatures": 1,
        "total_count": 1,
    }
    encoded = json.dumps(report, sort_keys=True)
    assert "login" not in encoded


def test_aggregate_only_drops_every_breakdown(tmp_path: Path) -> None:
    _corpus(tmp_path, "1.0.0", [_accepted(), _rejected_with_secret()])
    report = scan.scan(tmp_path, aggregate_only=True)
    assert report["aggregate_only"] is True
    for field in ("by_cli_version", "rejected_signatures", "below_threshold"):
        assert field not in report
    assert report["exec_tool_calls"] == 2
    assert report["exec_tool_calls_accepted"] == 1
    assert report["cosmetic_rejections"] == 1
    assert report["privilege_affecting_rejections"] == 0


def test_default_threshold_is_not_one() -> None:
    """The safe shape has to be the default, not an opt-in."""
    assert scan.DEFAULT_MIN_SIGNATURE_COUNT > 1


def test_scan_never_emits_tool_input_content(tmp_path: Path) -> None:
    _corpus(tmp_path, "1.0.0", [_rejected_with_secret()])
    encoded = json.dumps(scan.scan(tmp_path), sort_keys=True).encode("utf-8")
    assert b"auth.json" not in encoded
    assert b"Get-Content" not in encoded
    assert b"Users" not in encoded
    assert b"rollout-1.0.0" not in encoded
    assert live._privacy_violations(encoded) == []


def test_privilege_affecting_fields_are_separated(tmp_path: Path) -> None:
    cosmetic = _rejected_with_secret()
    privileged = (
        'const r = await tools.shell_command({command:"git status",'
        "sandbox_permissions:[],workdir:"
        + json.dumps(WORKSPACE)
        + "}); text(r)\n"
    )
    _corpus(tmp_path, "1.0.0", [cosmetic, privileged])
    report = scan.scan(tmp_path, min_signature_count=1)
    assert report["privilege_affecting_rejections"] == 1
    by_privilege = {
        entry["privilege_affecting"]: entry["field_semantics"]
        for entry in report["rejected_signatures"]
    }
    assert by_privilege[False] == ["core", "execution_bound"]
    assert by_privilege[True] == ["core", "privilege"]


def test_every_allowlisted_field_has_a_declared_semantic() -> None:
    assert set(scan.FIELD_SEMANTICS) == set(live.SAFE_TOOL_INPUT_FIELD_NAMES)
    assert scan.PRIVILEGE_AFFECTING <= set(scan.FIELD_SEMANTICS.values())


def test_unparsable_lines_and_non_exec_calls_are_ignored(
    tmp_path: Path,
) -> None:
    path = _corpus(tmp_path, "1.0.0", [_accepted()])
    path.write_text(
        path.read_text(encoding="utf-8")
        + "not json\n"
        + _record(
            {
                "payload": {
                    "input": _rejected_with_secret(),
                    "name": "something_else",
                    "type": "custom_tool_call",
                },
                "type": "response_item",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = scan.scan(tmp_path)
    assert report["exec_tool_calls"] == 1
    assert report["distinct_rejected_signatures"] == 0


def test_main_refuses_a_missing_sessions_root(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        scan.main(["--sessions-root", str(tmp_path / "absent")])
