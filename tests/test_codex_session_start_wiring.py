"""#288: F-7 reports the Codex SessionStart identity hook; it never installs it."""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.codex_session_start_wiring import (
    INSTALLED_CORRECTLY,
    INSTALLED_INCORRECTLY,
    NOT_APPLICABLE,
    NOT_INSTALLED,
    assess_codex_session_start,
    diagnostic_warnings,
    format_stage,
)
from governance_tools.external_governance_submodule_updater import UpdateResult
from governance_tools.f7_full_update import format_human, run_f7_full_update
from governance_tools.manage_agent_closeout import CodexCLIAdapter
from runtime_hooks.adapters.codex.session_start import SESSION_START_MATCHER, install

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "runtime_hooks/adapters/codex/session_start.py"


@pytest.fixture
def consumer(tmp_path: Path) -> Path:
    root = tmp_path / "consumer"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root.resolve()


def _hooks_file(consumer: Path) -> Path:
    return consumer / ".codex" / "hooks.json"


def _write_hooks(consumer: Path, hooks: dict) -> None:
    _hooks_file(consumer).parent.mkdir(parents=True, exist_ok=True)
    _hooks_file(consumer).write_text(json.dumps({"hooks": hooks}), encoding="utf-8")


def _identity_hook(entry: Path, project_root: Path) -> dict:
    return {"type": "command", "command": shlex.join(["python3", str(entry), "--project-root", str(project_root)])}


def _assess_unchanged(consumer: Path, framework: Path = ROOT) -> dict:
    before = _hooks_file(consumer).read_bytes() if _hooks_file(consumer).exists() else None
    report = assess_codex_session_start(consumer, framework)
    after = _hooks_file(consumer).read_bytes() if _hooks_file(consumer).exists() else None
    assert after == before, "the check must never write .codex/hooks.json"
    return report


def test_consumer_without_codex_is_not_checked(consumer: Path) -> None:
    report = _assess_unchanged(consumer)
    assert report["status"] == NOT_APPLICABLE
    assert report["stop_wiring"] == NOT_APPLICABLE
    assert report["report_only"] is True
    assert diagnostic_warnings(report) == []
    assert not _hooks_file(consumer).exists()


def test_stop_only_consumer_is_reported_with_a_working_repair(consumer: Path) -> None:
    CodexCLIAdapter().install(consumer, ROOT)
    report = _assess_unchanged(consumer)
    assert report["status"] == NOT_INSTALLED
    assert report["stop_wiring"] == "consistent"
    assert "--install" in report["repair"] and consumer.as_posix() in report["repair"]
    warnings = diagnostic_warnings(report)
    assert len(warnings) == 1 and "owner's approval" in warnings[0]

    # The suggested command is the existing installer and produces a correct binding.
    args = shlex.split(report["repair"])
    subprocess.run([sys.executable, *args[1:]], check=True, capture_output=True)
    fixed = _assess_unchanged(consumer)
    assert fixed["status"] == INSTALLED_CORRECTLY
    assert fixed["stop_wiring"] == "consistent"
    assert diagnostic_warnings(fixed) == []


def test_installer_output_is_recognised_as_correct(consumer: Path) -> None:
    CodexCLIAdapter().install(consumer, ROOT)
    install(consumer)
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_CORRECTLY, report["reasons"]
    assert report["repair"] is None and report["stop_repair"] is None
    rendered = "\n".join(format_stage(report))
    assert "codex_session_start=installed_correctly" in rendered
    assert "codex_session_start.stop_wiring=consistent" in rendered


def test_installer_output_with_an_apostrophe_in_the_path_is_correct(tmp_path: Path) -> None:
    # PowerShell writes an apostrophe as '' inside single quotes; POSIX
    # splitting would drop it and misreport the consumer root.
    root = tmp_path / "owner's consumer"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    root = root.resolve()
    CodexCLIAdapter().install(root, ROOT)
    install(root)
    hook = json.loads(_hooks_file(root).read_text(encoding="utf-8"))["hooks"]["SessionStart"][0]["hooks"][0]
    assert "commandWindows" in hook
    report = _assess_unchanged(root)
    assert report["status"] == INSTALLED_CORRECTLY, report["reasons"]


def test_malformed_existing_binding_is_not_reported_as_missing(consumer: Path) -> None:
    install(consumer)
    data = json.loads(_hooks_file(consumer).read_text(encoding="utf-8"))
    hook = data["hooks"]["SessionStart"][0]["hooks"][0]
    hook["command"] += " 'unterminated"
    del hook["commandWindows"]
    _hooks_file(consumer).write_text(json.dumps(data), encoding="utf-8")
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_INCORRECTLY
    assert any("cannot be decoded" in reason for reason in report["reasons"]), report["reasons"]
    assert "--install" not in report["repair"]
    # The installer recognises the same binding and refuses, so suggesting it would not help.
    with pytest.raises(ValueError, match="differs"):
        install(consumer)


def test_a_mention_of_the_entry_is_not_an_identity_hook(consumer: Path) -> None:
    mention = {"type": "command",
               "command": shlex.join(["echo", str(ENTRY), "--project-root", str(consumer)])}
    _write_hooks(consumer, {"SessionStart": [{"matcher": SESSION_START_MATCHER, "hooks": [mention]}]})
    CodexCLIAdapter().install(consumer, ROOT)
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_INCORRECTLY
    assert any("does not run the identity entry" in reason for reason in report["reasons"])
    assert any("installed incorrectly" in w for w in diagnostic_warnings(report))


@pytest.mark.parametrize("extra", [["--install"], ["--help"], []])
def test_other_modes_of_the_entry_are_not_identity_hooks(consumer: Path, extra: list[str]) -> None:
    # The repair command pasted into the hook keeps --install: it runs the
    # installer on every start and never establishes an identity.
    args = ["python3", str(ENTRY)] + (["--project-root", str(consumer)] if extra != [] else []) + extra
    hook = {"type": "command", "command": shlex.join(args)}
    _write_hooks(consumer, {"SessionStart": [{"matcher": SESSION_START_MATCHER, "hooks": [hook]}]})
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_INCORRECTLY
    assert any("must pass only --project-root" in reason for reason in report["reasons"]), report["reasons"]


def _windows(script: str) -> str:
    import base64
    return "powershell -NoProfile -EncodedCommand " + base64.b64encode(script.encode("utf-16-le")).decode("ascii")


@pytest.mark.parametrize("tail, ok", [("; exit $LASTEXITCODE", True), ("; exit 0", False), ("; Remove-Item x", False)])
def test_windows_tail_must_keep_the_exit_code(consumer: Path, tail: str, ok: bool) -> None:
    hook = _identity_hook(ENTRY, consumer)
    hook["commandWindows"] = _windows(f"& 'C:\\Python\\python.exe' '{ENTRY}' '--project-root' '{consumer}'{tail}")
    _write_hooks(consumer, {"SessionStart": [{"matcher": SESSION_START_MATCHER, "hooks": [hook]}]})
    report = _assess_unchanged(consumer)
    assert (report["status"] == INSTALLED_CORRECTLY) is ok, report["reasons"]


def test_non_command_hook_type_is_incorrect(consumer: Path) -> None:
    hook = {**_identity_hook(ENTRY, consumer), "type": "prompt"}
    _write_hooks(consumer, {"SessionStart": [{"matcher": SESSION_START_MATCHER, "hooks": [hook]}]})
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_INCORRECTLY
    assert any("hook type" in reason for reason in report["reasons"])


def test_versioned_interpreter_names_are_invocations(consumer: Path) -> None:
    hook = {"type": "command",
            "command": shlex.join(["/usr/bin/python3.11", "-B", str(ENTRY), "--project-root", str(consumer)])}
    _write_hooks(consumer, {"SessionStart": [{"matcher": SESSION_START_MATCHER, "hooks": [hook]}]})
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_CORRECTLY, report["reasons"]


def test_custom_session_start_hook_is_not_counted_and_kept(consumer: Path) -> None:
    custom = {"type": "command", "command": "echo custom start"}
    _write_hooks(consumer, {"SessionStart": [{"hooks": [custom]}]})
    report = _assess_unchanged(consumer)
    assert report["status"] == NOT_INSTALLED
    assert json.loads(_hooks_file(consumer).read_text(encoding="utf-8"))["hooks"]["SessionStart"][0]["hooks"] == [custom]


@pytest.mark.parametrize(
    "case, expected_reason",
    [
        ("other_framework", "not this framework checkout's entry"),
        ("other_root", "not this consumer"),
        ("duplicate", "expected one"),
        ("matcher", "SessionStart matcher"),
        ("misplaced", "registered under Stop"),
    ],
)
def test_incorrect_bindings_are_named(consumer: Path, tmp_path: Path, case: str, expected_reason: str) -> None:
    good = _identity_hook(ENTRY, consumer)
    groups = {
        "other_framework": {"SessionStart": [{"matcher": SESSION_START_MATCHER,
                            "hooks": [_identity_hook(tmp_path / "other-fw" / "runtime_hooks/adapters/codex/session_start.py", consumer)]}]},
        "other_root": {"SessionStart": [{"matcher": SESSION_START_MATCHER,
                       "hooks": [_identity_hook(ENTRY, tmp_path / "elsewhere")]}]},
        "duplicate": {"SessionStart": [{"matcher": SESSION_START_MATCHER, "hooks": [good, good]}]},
        "matcher": {"SessionStart": [{"matcher": "^startup$", "hooks": [good]}]},
        "misplaced": {"Stop": [{"hooks": [good]}]},
    }[case]
    _write_hooks(consumer, groups)
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_INCORRECTLY
    assert any(expected_reason in reason for reason in report["reasons"]), report["reasons"]
    assert "refuses to replace" in report["repair"]
    assert any("installed incorrectly" in w for w in diagnostic_warnings(report))


def test_stop_bound_to_another_checkout_is_inconsistent(consumer: Path, tmp_path: Path) -> None:
    other = tmp_path / "owner-checkout"
    other.mkdir()
    CodexCLIAdapter().install(consumer, other)
    install(consumer)
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_CORRECTLY
    assert report["stop_wiring"] == "inconsistent"
    assert "install --agent codex" in report["stop_repair"]
    assert any("same checkout" in w for w in diagnostic_warnings(report))


def test_session_end_publisher_is_not_answered_with_a_second_closeout(consumer: Path) -> None:
    install(consumer)
    data = json.loads(_hooks_file(consumer).read_text(encoding="utf-8"))
    publisher = (ROOT / "governance_tools/native_closeout_publisher.py").as_posix()
    data["hooks"]["SessionEnd"] = [{"hooks": [{"type": "command",
                                    "command": f'python -B "{publisher}" --consumer-root "{consumer.as_posix()}"'}]}]
    _hooks_file(consumer).write_text(json.dumps(data), encoding="utf-8")
    report = _assess_unchanged(consumer)
    assert report["stop_wiring"] == "not_found"
    assert "review that path" in report["stop_repair"]
    assert "install --agent codex" not in report["stop_repair"]


def test_unreadable_hooks_file_is_reported_not_repaired(consumer: Path) -> None:
    _hooks_file(consumer).parent.mkdir(parents=True)
    _hooks_file(consumer).write_text("{not json", encoding="utf-8")
    report = _assess_unchanged(consumer)
    assert report["status"] == INSTALLED_INCORRECTLY
    assert "by hand" in report["repair"]


def _fake_update(repo: Path):
    def fake(**_kwargs):
        return UpdateResult(
            ok=True, mode="dry_run", update_mode="dry_run", fast_forward=True, repo=str(repo),
            submodule_path="ai-governance-framework", before_head="a" * 40, target_head="a" * 40,
            after_head="a" * 40, staged_files=[], committed=False, commit_hash=None,
            message="dry run complete", errors=[],
            full_update_stage_report={"final_status": "already_current", "framework_pointer": "already_current"},
        )
    return fake


def _submodule_consumer(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitmodules").write_text(
        '[submodule "ai-governance-framework"]\n\tpath = ai-governance-framework\n'
        "\turl = https://github.com/Gavin0099/ai-governance-framework.git\n",
        encoding="utf-8",
    )
    (repo / "ai-governance-framework").mkdir()
    return repo


def test_f7_reports_the_gap_without_changing_status_or_files(monkeypatch, tmp_path: Path) -> None:
    import governance_tools.f7_full_update as f7

    repo = _submodule_consumer(tmp_path)
    monkeypatch.setattr(f7, "update_governance_submodule", _fake_update(repo))
    baseline = run_f7_full_update(repo_root=repo, framework_root=tmp_path / "unused", apply=False)
    assert baseline.stages["codex_session_start"]["status"] == NOT_APPLICABLE
    assert not any("codex SessionStart" in w for w in baseline.warnings)

    CodexCLIAdapter().install(repo, repo / "ai-governance-framework")
    hooks_before = _hooks_file(repo).read_bytes()
    result = run_f7_full_update(repo_root=repo, framework_root=tmp_path / "unused", apply=False)
    stage = result.stages["codex_session_start"]
    assert stage["status"] == NOT_INSTALLED and stage["report_only"] is True
    assert result.f7_final_status == baseline.f7_final_status
    assert result.ok == baseline.ok
    assert _hooks_file(repo).read_bytes() == hooks_before
    assert any(w.startswith("f7-diagnostic: codex SessionStart identity hook is not installed") for w in result.warnings)
    assert "codex_session_start=not_installed" in format_human(result)
