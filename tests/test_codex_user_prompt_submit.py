"""I334-2a stage A: §4B / §4B-1 report-only adapter acceptance tests."""

import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from governance_tools.task_level_detector import apply_upgrade_triggers, detect_task_level
from runtime_hooks.adapters.codex import user_prompt_submit as adapter


PROMPT = "I334_DISTINCTIVE_PROMPT_873af92: adjust the button spacing — 中文 🐢"
FIELDS = {
    "schema_version", "recorded_at", "session_id", "turn_id", "prompt_sha256",
    "prompt_len", "detector_level", "provisional_level", "provisional_level_basis",
    "signals", "framework_commit", "elapsed_ms", "error",
}


def event(prompt=PROMPT, session_id="known-session"):
    return {
        "hook_event_name": "UserPromptSubmit", "session_id": session_id,
        "turn_id": "turn-1", "prompt": prompt,
    }


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "consumer's space path"
    root.mkdir()
    return root


@pytest.fixture
def submit(project, monkeypatch, capsys):
    def invoke(payload=None, *, raw=None):
        monkeypatch.setattr(sys, "argv", [
            "user_prompt_submit.py", "--project-root", str(project),
        ])
        monkeypatch.setattr(sys, "stdin", io.StringIO(
            json.dumps(payload) if raw is None else raw,
        ))
        assert adapter.main() == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert PROMPT not in captured.err
        assert "I334_DISTINCTIVE_PROMPT_873af92" not in captured.err
        return captured
    return invoke


def read_only_record(tmp_path, project, filename="known-session.jsonl"):
    """Assert the entire fixture tree, including absence of docs/payload-audit."""
    directory = project / "artifacts/runtime/level-floor"
    path = directory / filename
    assert path.resolve().is_relative_to(directory.resolve())
    expected = {project, project / "artifacts", project / "artifacts/runtime", directory, path}
    assert set(tmp_path.rglob("*")) == expected
    raw = path.read_bytes()
    assert PROMPT.encode("utf-8") not in raw
    assert b"I334_DISTINCTIVE_PROMPT_873af92" not in raw
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert set(record) == FIELDS
    assert isinstance(record["elapsed_ms"], float)
    assert record["elapsed_ms"] >= 0
    return record


@pytest.mark.parametrize("prompt", [
    PROMPT, "", "Change the schema", "A breaking change", "Fix typo in the kdc label",
])
def test_valid_prompt_records_provisional_level_and_metadata(tmp_path, project, submit, prompt):
    """Characterize delegation, without claiming classifier accuracy (§4B-1.1)."""
    assert submit(event(prompt)).err == ""
    record = read_only_record(tmp_path, project)
    detector = detect_task_level(prompt)
    provisional, signals = apply_upgrade_triggers(detector, prompt, risk_level="medium")
    assert record["schema_version"] == "1.0"
    assert record["session_id"] == "known-session"
    assert record["turn_id"] == "turn-1"
    assert record["prompt_sha256"] == hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    assert record["prompt_len"] == len(prompt)
    assert record["detector_level"] == detector
    assert record["provisional_level"] == provisional
    assert record["provisional_level_basis"] == "text_heuristic_report_only"
    assert record["signals"] == signals
    assert all(isinstance(signal, str) for signal in record["signals"])
    assert datetime.fromisoformat(record["recorded_at"]).utcoffset() == timedelta(0)
    assert record["framework_commit"] is None or re.fullmatch(
        r"[0-9a-f]{40}|[0-9a-f]{64}", record["framework_commit"],
    )
    assert record["error"] is None
    if prompt:
        path = project / "artifacts/runtime/level-floor/known-session.jsonl"
        assert prompt.encode("utf-8") not in path.read_bytes()


def test_classifier_receives_no_explicit_level_and_medium_risk(
    tmp_path, project, submit, monkeypatch,
):
    calls = []

    def detect(prompt):
        calls.append(("detect", prompt))
        return "L0"

    def upgrade(level, prompt, *, risk_level):
        calls.append(("upgrade", level, prompt, risk_level))
        return "L1", ["domain_summary"]

    monkeypatch.setattr(adapter, "detect_task_level", detect)
    monkeypatch.setattr(adapter, "apply_upgrade_triggers", upgrade)
    submit(event())
    assert calls == [("detect", PROMPT), ("upgrade", "L0", PROMPT, "medium")]
    record = read_only_record(tmp_path, project)
    assert record["detector_level"] == "L0"
    assert record["provisional_level"] == "L1"
    assert record["signals"] == ["domain_summary"]


def test_classifier_output_and_untrusted_metadata_cannot_leak_prompt(
    tmp_path, project, submit, monkeypatch,
):
    def detect(prompt):
        print(prompt)
        print(prompt, file=sys.stderr)
        return "L0"

    monkeypatch.setattr(adapter, "detect_task_level", detect)
    monkeypatch.setattr(adapter, "apply_upgrade_triggers", lambda *args, **kwargs: ("L0", [PROMPT]))
    assert submit({**event(), "turn_id": PROMPT}).err == ""
    record = read_only_record(tmp_path, project)
    assert record["turn_id"] == "<redacted>"
    assert record["signals"] == ["<redacted>"]
    assert record["error"] is None


@pytest.mark.parametrize("prompt_fields", [{}, {"prompt": None}, {"prompt": 123},
                                             {"prompt": []}, {"prompt": {}}, {"prompt": False}])
def test_missing_or_non_string_prompt_is_unknown(tmp_path, project, submit, monkeypatch, prompt_fields):
    def unexpected_detector(*args, **kwargs):
        pytest.fail("non-string prompts must not reach the detector")

    monkeypatch.setattr(adapter, "detect_task_level", unexpected_detector)
    payload = event()
    payload.pop("prompt")
    payload.update(prompt_fields)
    assert submit(payload).err == ""
    record = read_only_record(tmp_path, project)
    assert record["detector_level"] == "UNKNOWN"
    assert record["provisional_level"] == "UNKNOWN"
    assert record["prompt_sha256"] is None
    assert record["prompt_len"] is None
    assert record["signals"] == []


@pytest.mark.parametrize("raw", ["", "not-json " + PROMPT, '{"prompt": "' + PROMPT])
def test_non_json_stdin_records_error_without_leaking_prompt(tmp_path, project, submit, raw):
    assert submit(raw=raw).err == ""
    record = read_only_record(tmp_path, project, "invalid-session.jsonl")
    assert record["error"]
    assert record["provisional_level"] == "UNKNOWN"


@pytest.mark.parametrize("payload", [None, [], 42, PROMPT, {**event(), "hook_event_name": "Stop"},
                                     {key: value for key, value in event().items() if key != "hook_event_name"}])
def test_invalid_payload_or_event_records_error(tmp_path, project, submit, payload, monkeypatch):
    def unexpected_detector(*args, **kwargs):
        pytest.fail("invalid hook events must not reach the detector")

    monkeypatch.setattr(adapter, "detect_task_level", unexpected_detector)
    assert submit(payload).err == ""
    filename = "known-session.jsonl" if isinstance(payload, dict) else "invalid-session.jsonl"
    record = read_only_record(tmp_path, project, filename)
    assert record["error"]
    assert record["provisional_level"] == "UNKNOWN"


@pytest.mark.parametrize("function", ["detect_task_level", "apply_upgrade_triggers"])
@pytest.mark.parametrize("leaked_text", [PROMPT, PROMPT[:8], PROMPT[5:19]])
@pytest.mark.parametrize("exception_type", [RuntimeError, SystemExit])
def test_classifier_exception_redacts_prompt_and_fragments(
    tmp_path, project, submit, monkeypatch, function, leaked_text, exception_type,
):
    def fail(*args, **kwargs):
        raise exception_type("classification failed for " + leaked_text)

    monkeypatch.setattr(adapter, function, fail)
    assert submit(event()).err == ""
    record = read_only_record(tmp_path, project)
    assert record["provisional_level"] == "UNKNOWN"
    assert record["error"] == exception_type.__name__ + ": <redacted>"
    assert leaked_text not in json.dumps(record)


def test_classifier_exception_preserves_only_a_sanitized_safe_message(
    tmp_path, project, submit, monkeypatch,
):
    def fail(prompt):
        raise RuntimeError("classification\nfailed\tplease retry")

    monkeypatch.setattr(adapter, "detect_task_level", fail)
    assert submit(event()).err == ""
    record = read_only_record(tmp_path, project)
    assert record["error"] == "RuntimeError: classification failed please retry"


@pytest.mark.parametrize("session_fields", [
    {"session_id": "../x"}, {"session_id": "a/b"}, {"session_id": "a\\b"},
    {"session_id": ""}, {"session_id": "x" * 129}, {"session_id": ".."},
    {"session_id": "a..b"}, {"session_id": "a b"}, {"session_id": "中文"},
    {"session_id": None}, {"session_id": 12}, {},
])
def test_invalid_session_id_stays_inside_level_floor(tmp_path, project, submit, session_fields):
    payload = event()
    payload.pop("session_id")
    payload.update(session_fields)
    assert submit(payload).err == ""
    record = read_only_record(tmp_path, project, "invalid-session.jsonl")
    assert record["error"] == "invalid_session_id"
    assert record["session_id"] is None


@pytest.mark.parametrize("session_id", ["a", "A_9.valid-session", "x" * 128])
def test_valid_session_id_boundaries(tmp_path, project, submit, session_id):
    assert submit(event(session_id=session_id)).err == ""
    record = read_only_record(tmp_path, project, session_id + ".jsonl")
    assert record["session_id"] == session_id
    assert record["error"] is None


def test_each_turn_appends_one_record_and_measures_elapsed_ms(project, submit, monkeypatch):
    ticks = iter([10.0, 10.125, 20.0, 20.25])
    monkeypatch.setattr(adapter, "perf_counter", lambda: next(ticks))
    submit(event())
    submit({**event(), "turn_id": "turn-2"})
    path = project / "artifacts/runtime/level-floor/known-session.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [record["turn_id"] for record in records] == ["turn-1", "turn-2"]
    assert [record["elapsed_ms"] for record in records] == [125.0, 250.0]


def test_write_failure_is_zero_and_emits_one_short_sanitized_line(project, submit, monkeypatch):
    original_open = Path.open

    def fail_record_write(path, *args, **kwargs):
        if path.suffix == ".jsonl":
            raise OSError("cannot write " + PROMPT)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_record_write)
    captured = submit(event())
    assert captured.err == "UserPromptSubmit: record write failed\n"
    assert not list(project.rglob("*.jsonl"))
    assert not (project / "docs").exists()


@pytest.mark.parametrize("link_kind", ["directory", "record"])
def test_resolved_symlink_escape_never_writes_outside_level_floor(
    tmp_path, project, submit, link_kind,
):
    directory = project / "artifacts/runtime/level-floor"
    outside = tmp_path / "outside"
    outside.mkdir()
    directory.parent.mkdir(parents=True)
    try:
        if link_kind == "directory":
            directory.symlink_to(outside, target_is_directory=True)
        else:
            directory.mkdir()
            (directory / "known-session.jsonl").symlink_to(outside / "escaped.jsonl")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this host")
    before = set(tmp_path.rglob("*"))
    assert submit(event()).err == "UserPromptSubmit: record write failed\n"
    assert set(tmp_path.rglob("*")) == before
    assert not list(outside.iterdir())


@pytest.mark.parametrize("layout", ["detached", "loose", "packed", "worktree", "missing"])
def test_framework_commit_reads_git_files_best_effort(tmp_path, monkeypatch, layout):
    framework = tmp_path / "framework"
    framework.mkdir()
    monkeypatch.setattr(adapter, "FRAMEWORK_ROOT", framework)
    if layout == "missing":
        assert adapter._framework_commit() is None
        return
    sha = "a1" * 20
    git_dir = framework / ".git"
    if layout == "worktree":
        git_dir = tmp_path / "git-common/worktrees/fixture"
        git_dir.mkdir(parents=True)
        (framework / ".git").write_text("gitdir: ../git-common/worktrees/fixture\n", encoding="utf-8")
        (git_dir / "commondir").write_text("../..\n", encoding="utf-8")
        (tmp_path / "git-common/packed-refs").write_text(sha + " refs/heads/topic\n", encoding="utf-8")
    else:
        git_dir.mkdir()
    (git_dir / "HEAD").write_text(
        sha + "\n" if layout == "detached" else "ref: refs/heads/topic\n", encoding="utf-8",
    )
    if layout == "loose":
        ref = git_dir / "refs/heads/topic"
        ref.parent.mkdir(parents=True)
        ref.write_text(sha + "\n", encoding="utf-8")
    elif layout == "packed":
        (git_dir / "packed-refs").write_text("# pack-refs\n" + sha + " refs/heads/topic\n", encoding="utf-8")
    assert adapter._framework_commit() == sha


def test_cli_reads_stdin_with_empty_stdout_and_no_other_files(tmp_path, project):
    entry = Path(adapter.__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-B", str(entry), "--project-root", str(project)],
        cwd=tmp_path, input=json.dumps(event()), text=True, encoding="utf-8",
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert PROMPT not in result.stdout + result.stderr
    assert read_only_record(tmp_path, project)["error"] is None


@pytest.mark.parametrize("arguments", [[], ["--help"], ["--unexpected", PROMPT]])
def test_argument_errors_also_keep_stdout_empty_and_exit_zero(
    tmp_path, project, monkeypatch, capsys, arguments,
):
    monkeypatch.setattr(sys, "argv", ["user_prompt_submit.py", *arguments])
    assert adapter.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "UserPromptSubmit: invalid arguments\n"
    assert set(tmp_path.rglob("*")) == {project}
