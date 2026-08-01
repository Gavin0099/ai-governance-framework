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


def test_scan_counts_acceptance_per_cli_class(tmp_path: Path) -> None:
    _corpus(tmp_path, "1.0.0", [_accepted(), _rejected_with_secret()])
    _corpus(tmp_path, "not-a-version", [_rejected_with_secret()])
    report = scan.scan(tmp_path, min_signature_count=1)
    assert report["exec_tool_calls"] == 3
    assert report["exec_tool_calls_accepted"] == 1
    assert report["by_cli_class"] == {
        "other_valid_semver": {"accepted": 1, "total": 2},
        "unknown_or_invalid": {"accepted": 0, "total": 1},
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


def test_rejections_are_reported_by_class(tmp_path: Path) -> None:
    """Scope violations must be countable separately from shape variance."""
    _corpus(
        tmp_path,
        "1.0.0",
        [
            _rejected_with_secret(),
            "const r = await tools.update_plan({plan:[]}); text(r)\n",
            "text('nothing')\n",
        ],
    )
    report = scan.scan(tmp_path, min_signature_count=1)
    assert report["rejections_by_class"] == {
        "single_frozen_call": 1,
        "multiple_calls": 0,
        "out_of_route_tool": 1,
        "no_tool_call": 1,
    }
    assert "update_plan" not in json.dumps(report, sort_keys=True)


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


# --- publication boundary -------------------------------------------------
#
# Keeping full reports out of version control used to be a convention: a
# .gitignore rule matching one filename pattern, plus whoever ran the command.
# These cover what the tool now refuses on its own.


def _sessions(tmp_path: Path) -> Path:
    root = tmp_path / "sessions"
    root.mkdir()
    _corpus(root, "1.0.0", [_accepted(), _rejected_with_secret()])
    return root


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    return repo


@pytest.fixture
def outside_version_control(monkeypatch: pytest.MonkeyPatch):
    """Make "not under a work tree" true regardless of where tmp_path lives.

    pytest's basetemp is wherever the runner puts it, and in a managed
    workspace that can be inside a checkout. A test for the success path must
    not silently become a test of the refusal path because of that. The
    predicate itself is covered separately against an explicit fixture.
    """
    real = scan._enclosing_git_root

    def only_declared_repos(path: Path) -> Path | None:
        found = real(path)
        if found is None:
            return None
        # Honour repositories the test created itself; ignore any checkout the
        # runner happens to have placed tmp_path inside.
        return found if (found / ".git").is_dir() and found.name == "repo" else None

    monkeypatch.setattr(scan, "_enclosing_git_root", only_declared_repos)
    return None


def test_full_report_is_refused_inside_a_git_work_tree(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(SystemExit) as failure:
        scan.main(
            [
                "--sessions-root",
                str(_sessions(tmp_path)),
                "--out",
                str(repo / "evidence" / "report.json"),
            ]
        )
    assert "git repository" in str(failure.value)
    assert not (repo / "evidence").exists()


@pytest.mark.parametrize(
    "name",
    ["report.json", "wrapper-corpus-scan.json", "notes.txt", ".hidden.json"],
)
def test_renaming_the_output_does_not_bypass_the_boundary(
    tmp_path: Path,
    name: str,
) -> None:
    """The old .gitignore rule matched one filename pattern. This does not."""
    repo = _repo(tmp_path)
    with pytest.raises(SystemExit) as failure:
        scan.main(
            [
                "--sessions-root",
                str(_sessions(tmp_path)),
                "--out",
                str(repo / name),
            ]
        )
    assert "git repository" in str(failure.value)


def test_boundary_holds_for_a_nested_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    with pytest.raises(SystemExit):
        scan.main(
            [
                "--sessions-root",
                str(_sessions(tmp_path)),
                "--out",
                str(nested / "report.json"),
            ]
        )


def test_full_report_is_never_written_to_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as failure:
        scan.main(["--sessions-root", str(_sessions(tmp_path))])
    assert "--out" in str(failure.value)
    assert capsys.readouterr().out == ""


def test_enclosing_git_root_finds_the_nearest_work_tree(
    tmp_path: Path,
) -> None:
    """The boundary predicate itself, on an explicit fixture."""
    repo = _repo(tmp_path)
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    assert scan._enclosing_git_root(nested) == repo
    assert scan._enclosing_git_root(repo) == repo
    inner = repo / "inner"
    (inner / ".git").mkdir(parents=True)
    assert scan._enclosing_git_root(inner) == inner


def test_full_report_writes_outside_version_control(
    tmp_path: Path,
    outside_version_control: None,
) -> None:
    out = tmp_path / "private" / "report.json"
    assert scan.main(
        [
            "--sessions-root",
            str(_sessions(tmp_path)),
            "--out",
            str(out),
        ]
    ) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["exec_tool_calls"] == 2
    assert not list(out.parent.glob("*.partial"))


def test_aggregate_only_may_still_go_to_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    outside_version_control: None,
) -> None:
    """The reviewable shape stays usable; only the full report is confined."""
    assert scan.main(
        ["--sessions-root", str(_sessions(tmp_path)), "--aggregate-only"]
    ) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["aggregate_only"] is True
    assert "by_cli_class" not in printed


def test_a_refused_write_leaves_no_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outside_version_control: None,
) -> None:
    out = tmp_path / "private" / "report.json"

    def explode(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk went away")

    monkeypatch.setattr(scan.os, "replace", explode)
    with pytest.raises(OSError):
        scan.main(
            [
                "--sessions-root",
                str(_sessions(tmp_path)),
                "--out",
                str(out),
            ]
        )
    assert not out.exists()
    assert not list(out.parent.glob("*.partial"))


# --- cli version normalization --------------------------------------------


def test_pinned_and_other_versions_are_classified_not_echoed(
    tmp_path: Path,
) -> None:
    _corpus(tmp_path, live.DEFAULT_CLI_VERSION, [_accepted()])
    _corpus(tmp_path, "0.145.0-alpha.18", [_rejected_with_secret()])
    report = scan.scan(tmp_path, min_signature_count=1)
    assert report["by_cli_class"] == {
        "other_valid_semver": {"accepted": 0, "total": 1},
        "pinned": {"accepted": 1, "total": 1},
    }
    encoded = json.dumps(report, sort_keys=True)
    # No value read out of the corpus survives. The pinned version does appear,
    # as the report's own `pinned_cli_version` label, but that is a constant
    # published in this repository, not something the corpus told us.
    assert "0.145.0-alpha.18" not in encoded
    assert encoded.count(live.DEFAULT_CLI_VERSION) == 1
    assert report["pinned_cli_version"] == live.DEFAULT_CLI_VERSION


@pytest.mark.parametrize(
    "value",
    [
        "C:/Users/daish/builds/codex-custom",
        "internal-build-daish-laptop",
        "0.146.0 (built by daish)",
        "",
        "x" * (scan.MAX_CLI_VERSION_LENGTH + 1),
        None,
        12345,
        {"version": "0.146.0"},
    ],
)
def test_hostile_cli_version_metadata_never_reaches_the_report(
    tmp_path: Path,
    value: object,
) -> None:
    """The field is free text; it must be classified, never carried through."""
    assert scan._cli_version_class(value) == "unknown_or_invalid"
    path = tmp_path / "rollout.jsonl"
    path.write_text(
        _record({"payload": {"cli_version": value}, "type": "session_meta"})
        + "\n"
        + _record(
            {
                "payload": {
                    "input": _rejected_with_secret(),
                    "name": "exec",
                    "type": "custom_tool_call",
                },
                "type": "response_item",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = scan.scan(tmp_path, min_signature_count=1)
    assert report["by_cli_class"] == {
        "unknown_or_invalid": {"accepted": 0, "total": 1}
    }
    encoded = json.dumps(report, sort_keys=True)
    if isinstance(value, str) and value:
        assert value not in encoded
    assert "daish" not in encoded
    assert live._privacy_violations(encoded.encode("utf-8")) == []


@pytest.mark.parametrize(
    "value", ["1.4６.0", "1.46.٠", "０.1.0", "1.4२.0"],
)
def test_non_ascii_digits_do_not_pass_as_a_valid_semver(value: str) -> None:
    """Same defect class as the contract's numeric literal.

    \\d spans Unicode, so these would classify as valid semver. Hostile or
    unexpected metadata must fall to unknown_or_invalid instead.
    """
    assert scan.SEMVER_RE.fullmatch(value) is None
    assert scan._cli_version_class(value) == "unknown_or_invalid"


def test_every_emitted_cli_class_is_a_declared_class(tmp_path: Path) -> None:
    _corpus(tmp_path, live.DEFAULT_CLI_VERSION, [_accepted()])
    _corpus(tmp_path, "not-a-version", [_rejected_with_secret()])
    report = scan.scan(tmp_path, min_signature_count=1)
    assert set(report["by_cli_class"]) <= set(scan.CLI_VERSION_CLASSES)
    for entry in report["rejected_signatures"]:
        assert set(entry["cli_classes"]) <= set(scan.CLI_VERSION_CLASSES)
