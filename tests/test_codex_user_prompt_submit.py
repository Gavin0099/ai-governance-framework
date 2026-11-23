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

from governance_tools import task_level_detector as classifier
from runtime_hooks.adapters.codex import user_prompt_submit as adapter


PROMPT = "I334_DISTINCTIVE_PROMPT_873af92: adjust the button spacing — 中文 🐢"
KNOWN_RECORD_NAME = hashlib.sha256(b"known-session").hexdigest()[:32] + ".jsonl"
ERROR_CODES = {
    "invalid_json", "wrong_event", "missing_prompt", "non_string_prompt",
    "invalid_prompt_encoding", "invalid_session_id", "invalid_turn_id",
    "identifier_redacted", "classifier_error", "upgrade_error",
    "invalid_level_return", "invalid_upgrade_load", "write_error", "bootstrap_error",
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


def identifier_digest(value):
    """The spec's hash oracle, independent of adapter validation/redaction."""
    if not isinstance(value, str):
        return None
    try:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    except UnicodeError:
        return None


def read_only_record(
    tmp_path, project, filename=KNOWN_RECORD_NAME, *, prompt=PROMPT,
    identifiers=("known-session", "turn-1"), raw_identifiers=("known-session", "turn-1"),
    levels=("L0", "L0"), loads=(), errors=(),
):
    """Check decoded fields and actual directory names, not just schema keys.

    Every free-text-capable field has an explicit expected value. Adding a
    field is not the confidentiality oracle: leaks through existing fields
    must fail these checks even when the set of keys is unchanged.
    """
    directory = project / "artifacts/runtime/level-floor"
    path = directory / filename
    assert path.resolve().is_relative_to(directory.resolve())
    expected = {project, project / "artifacts", project / "artifacts/runtime", directory, path}
    assert set(tmp_path.rglob("*")) == expected
    assert [entry.name for entry in directory.iterdir()] == [filename]
    assert filename == "invalid-session.jsonl" or re.fullmatch(r"[0-9a-f]{32}\.jsonl", filename)
    raw = path.read_bytes()
    assert PROMPT.encode("utf-8") not in raw
    assert b"I334_DISTINCTIVE_PROMPT_873af92" not in raw
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    # These fields were renamed/removed; their absence checks that migration,
    # while the explicit value checks below enforce confidentiality.
    assert "signals" not in record
    assert "error" not in record
    assert "elapsed_ms" not in record
    assert record["schema_version"] == "1.0"
    assert record["session_id"] == raw_identifiers[0]
    assert record["turn_id"] == raw_identifiers[1]
    assert record["session_id_sha256"] == identifier_digest(identifiers[0])
    assert record["turn_id_sha256"] == identifier_digest(identifiers[1])
    assert record["prompt_sha256"] == identifier_digest(prompt)
    assert record["prompt_len"] == (len(prompt) if prompt is not None else None)
    assert record["detector_level"] == levels[0]
    assert record["provisional_level"] == levels[1]
    assert record["provisional_level_basis"] == "text_heuristic_report_only"
    assert record["upgrade_additional_loads"] == list(loads)
    assert all(re.fullmatch(r"[a-z0-9_]{1,64}", item) for item in record["upgrade_additional_loads"])
    assert record["error_codes"] == list(errors)
    assert all(type(code) is str and code in ERROR_CODES for code in record["error_codes"])
    assert datetime.fromisoformat(record["recorded_at"]).utcoffset() == timedelta(0)
    assert record["framework_commit"] is None or re.fullmatch(
        r"[0-9a-f]{40}|[0-9a-f]{64}", record["framework_commit"],
    )
    assert isinstance(record["handler_elapsed_ms"], float)
    assert record["handler_elapsed_ms"] >= 0
    return record


@pytest.mark.parametrize("prompt, levels, loads", [
    (PROMPT, ("L0", "L0"), []),
    ("", ("L1", "L1"), []),
    ("Change the schema", ("L1", "L1"), []),
    ("A breaking change", ("L2", "L2"), []),
    ("Fix typo in the kdc label", ("L0", "L1"), ["domain_summary"]),
])
def test_valid_prompt_records_fixed_levels_and_upgrade_load_examples(
    tmp_path, project, submit, prompt, levels, loads,
):
    """Spec examples: loads are L0 resource requests, never detector reasons."""
    assert submit(event(prompt)).err == ""
    read_only_record(tmp_path, project, prompt=prompt, levels=levels, loads=loads)
    if prompt:
        path = project / "artifacts/runtime/level-floor" / KNOWN_RECORD_NAME
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

    monkeypatch.setattr(classifier, "detect_task_level", detect)
    monkeypatch.setattr(classifier, "apply_upgrade_triggers", upgrade)
    submit(event())
    assert calls == [("detect", PROMPT), ("upgrade", "L0", PROMPT, "medium")]
    read_only_record(tmp_path, project, levels=("L0", "L1"), loads=["domain_summary"])


def test_classifier_output_and_untrusted_metadata_cannot_leak_prompt(
    tmp_path, project, submit, monkeypatch,
):
    def detect(prompt):
        print(prompt)
        print(prompt, file=sys.stderr)
        return "L0"

    monkeypatch.setattr(classifier, "detect_task_level", detect)
    monkeypatch.setattr(classifier, "apply_upgrade_triggers", lambda *args, **kwargs: ("L0", [PROMPT]))
    assert submit({**event(), "turn_id": PROMPT}).err == ""
    read_only_record(
        tmp_path, project, identifiers=("known-session", PROMPT),
        raw_identifiers=("known-session", None),
        errors=["invalid_turn_id", "invalid_upgrade_load"],
    )


@pytest.mark.parametrize("prompt_fields", [{}, {"prompt": None}, {"prompt": 123},
                                             {"prompt": []}, {"prompt": {}}, {"prompt": False}])
def test_missing_or_non_string_prompt_is_unknown(tmp_path, project, submit, monkeypatch, prompt_fields):
    def unexpected_detector(*args, **kwargs):
        pytest.fail("non-string prompts must not reach the detector")

    monkeypatch.setattr(classifier, "detect_task_level", unexpected_detector)
    payload = event()
    payload.pop("prompt")
    payload.update(prompt_fields)
    assert submit(payload).err == ""
    read_only_record(
        tmp_path, project, prompt=None, levels=("UNKNOWN", "UNKNOWN"),
        errors=["non_string_prompt" if "prompt" in prompt_fields else "missing_prompt"],
    )


def test_non_utf8_prompt_records_only_length_and_fixed_error(tmp_path, project, submit, monkeypatch):
    def unexpected_detector(*args, **kwargs):
        pytest.fail("non-UTF-8 prompts must not reach the detector")

    monkeypatch.setattr(classifier, "detect_task_level", unexpected_detector)
    assert submit(event("\ud800")).err == ""
    read_only_record(
        tmp_path, project, prompt="\ud800", levels=("UNKNOWN", "UNKNOWN"),
        errors=["invalid_prompt_encoding"],
    )


@pytest.mark.parametrize("raw", ["", "not-json " + PROMPT, '{"prompt": "' + PROMPT])
def test_non_json_stdin_records_error_without_leaking_prompt(tmp_path, project, submit, raw):
    assert submit(raw=raw).err == ""
    read_only_record(
        tmp_path, project, "invalid-session.jsonl", prompt=None,
        identifiers=(None, None), raw_identifiers=(None, None), levels=("UNKNOWN", "UNKNOWN"),
        errors=["invalid_json", "wrong_event", "invalid_session_id", "invalid_turn_id", "missing_prompt"],
    )


@pytest.mark.parametrize("payload", [None, [], 42, PROMPT, {**event(), "hook_event_name": "Stop"},
                                     {key: value for key, value in event().items() if key != "hook_event_name"}])
def test_invalid_payload_or_event_records_error(tmp_path, project, submit, payload, monkeypatch):
    def unexpected_detector(*args, **kwargs):
        pytest.fail("invalid hook events must not reach the detector")

    monkeypatch.setattr(classifier, "detect_task_level", unexpected_detector)
    assert submit(payload).err == ""
    if isinstance(payload, dict):
        read_only_record(tmp_path, project, levels=("UNKNOWN", "UNKNOWN"), errors=["wrong_event"])
    else:
        read_only_record(
            tmp_path, project, "invalid-session.jsonl", prompt=None,
            identifiers=(None, None), raw_identifiers=(None, None), levels=("UNKNOWN", "UNKNOWN"),
            errors=["wrong_event", "invalid_session_id", "invalid_turn_id", "missing_prompt"],
        )


@pytest.mark.parametrize("function", ["detect_task_level", "apply_upgrade_triggers"])
@pytest.mark.parametrize("prompt, leaked_text", [
    (PROMPT, PROMPT), (PROMPT, PROMPT[:3]), (PROMPT, PROMPT[5:9]),
    (PROMPT, PROMPT[5:12]), (PROMPT, PROMPT.casefold()),
    ("SensitiveCanary", "ＳｅｎｓｉｔｉｖｅＣａｎａｒｙ"),
    ("ABCD\nEFGH\nIJKL", repr("ABCD\nEFGH\nIJKL")),
])
@pytest.mark.parametrize("exception_type", [RuntimeError, SystemExit])
def test_classifier_exception_redacts_prompt_and_fragments(
    tmp_path, project, submit, monkeypatch, function, prompt, leaked_text, exception_type,
):
    def fail(*args, **kwargs):
        raise exception_type("classification failed for " + leaked_text)

    monkeypatch.setattr(classifier, function, fail)
    if function == "apply_upgrade_triggers":
        monkeypatch.setattr(classifier, "detect_task_level", lambda prompt: "L0")
    assert submit(event(prompt)).err == ""
    record = read_only_record(
        tmp_path, project, prompt=prompt,
        levels=("UNKNOWN", "UNKNOWN") if function == "detect_task_level" else ("L0", "UNKNOWN"),
        errors=["classifier_error" if function == "detect_task_level" else "upgrade_error"],
    )
    assert leaked_text not in json.dumps(record)


def test_classifier_exception_discards_even_safe_messages(
    tmp_path, project, submit, monkeypatch,
):
    def fail(prompt):
        raise RuntimeError("classification\nfailed\tplease retry")

    monkeypatch.setattr(classifier, "detect_task_level", fail)
    assert submit(event()).err == ""
    read_only_record(tmp_path, project, levels=("UNKNOWN", "UNKNOWN"), errors=["classifier_error"])


@pytest.mark.parametrize("session_fields", [
    {"session_id": "../x"}, {"session_id": "a/b"}, {"session_id": "a\\b"},
    {"session_id": ""}, {"session_id": "x" * 129},
    {"session_id": "a b"}, {"session_id": "中文"}, {"session_id": "\ud800"},
    {"session_id": None}, {"session_id": 12}, {},
])
def test_invalid_session_id_stays_inside_level_floor(tmp_path, project, submit, session_fields):
    payload = event()
    payload.pop("session_id")
    payload.update(session_fields)
    assert submit(payload).err == ""
    session_id = session_fields.get("session_id")
    digest = identifier_digest(session_id)
    filename = digest[:32] + ".jsonl" if digest is not None else "invalid-session.jsonl"
    read_only_record(
        tmp_path, project, filename, identifiers=(session_id, "turn-1"),
        raw_identifiers=(None, "turn-1"), errors=["invalid_session_id"],
    )


@pytest.mark.parametrize("session_id", ["z", "A_9.valid-session", "x" * 128, "..", "a..b"])
def test_valid_session_id_boundaries(tmp_path, project, submit, session_id):
    assert submit(event(session_id=session_id)).err == ""
    read_only_record(
        tmp_path, project, identifier_digest(session_id)[:32] + ".jsonl",
        identifiers=(session_id, "turn-1"), raw_identifiers=(session_id, "turn-1"),
    )


@pytest.mark.parametrize("prompt, echo", [
    ("SensitiveCanary123", "SensitiveCanary123"),
    ("SensitiveCanary123", "sEnSiTiVeCaNaRy123"),
    ("SensitiveCanary123", "Canary"),
    ("SensitiveCanary123", "Can"),
    ("SensitiveCanary123", "S"),
    ("SensitiveCanary123", "xxCANARYyy"),
    ("SensitiveCanary123", "xxsEnSyy"),
    ("ＳＥＮＳＩＴＩＶＥＣＡＮＡＲＹ123", "sensitivecanary123"),
    ("Straße42", "STRASSE42"),
    ("ABCD\nEFGH\nIJKL", "xxEFGHyy"),
    ("Z", "Z"),
])
def test_prompt_identifiers_and_normalized_fragments_are_hashed_and_redacted(
    tmp_path, project, submit, monkeypatch, prompt, echo,
):
    monkeypatch.setattr(classifier, "detect_task_level", lambda prompt: "L0")
    assert submit({**event(prompt, session_id=echo), "turn_id": echo}).err == ""
    filename = identifier_digest(echo)[:32] + ".jsonl"
    record = read_only_record(
        tmp_path, project, filename, prompt=prompt, identifiers=(echo, echo),
        raw_identifiers=(None, None), errors=["identifier_redacted"],
    )
    assert record["session_id_sha256"] == record["turn_id_sha256"]
    assert filename != echo + ".jsonl"


@pytest.mark.parametrize("prompt, echo", [
    (PROMPT, PROMPT),
    ("ABCD\nEFGH\nIJKL", "ABCD\nEFGH\nIJKL"),
    ("ABCD\nEFGH\nIJKL", repr("ABCD\nEFGH\nIJKL")),
])
def test_non_ascii_multiline_and_escaped_identifiers_never_survive_in_decoded_fields(
    tmp_path, project, submit, monkeypatch, prompt, echo,
):
    monkeypatch.setattr(classifier, "detect_task_level", lambda prompt: "L0")
    assert submit({**event(prompt, session_id=echo), "turn_id": echo}).err == ""
    read_only_record(
        tmp_path, project, identifier_digest(echo)[:32] + ".jsonl", prompt=prompt,
        identifiers=(echo, echo), raw_identifiers=(None, None),
        errors=["invalid_session_id", "invalid_turn_id"],
    )


@pytest.mark.parametrize("session_id", ["NUL", "CON", "COM1", "NUL.note", "con", "com1.notes"])
def test_windows_device_identifiers_persist_only_as_digest_named_regular_files(
    tmp_path, project, submit, session_id,
):
    assert submit(event(session_id=session_id)).err == ""
    filename = identifier_digest(session_id)[:32] + ".jsonl"
    read_only_record(
        tmp_path, project, filename, identifiers=(session_id, "turn-1"),
        raw_identifiers=(session_id, "turn-1"),
    )
    directory = project / "artifacts/runtime/level-floor"
    assert (directory / filename).is_file()
    assert all(entry.name.split(".")[0].upper() not in {"NUL", "CON", "COM1"}
               for entry in directory.iterdir())


@pytest.mark.parametrize("turn_id", [None, 12, False, [], {}, "", "x" * 129, "a b", "\ud800"])
def test_invalid_turn_identifier_has_only_a_digest_or_null(
    tmp_path, project, submit, turn_id,
):
    assert submit({**event(), "turn_id": turn_id}).err == ""
    read_only_record(
        tmp_path, project, identifiers=("known-session", turn_id),
        raw_identifiers=("known-session", None), errors=["invalid_turn_id"],
    )


def test_json_decoder_prompt_bearing_diagnostics_are_fixed_codes(
    tmp_path, project, submit, monkeypatch,
):
    prompt = "ABCD\nEFGH\nIJKL"

    def fail(stream):
        raise json.JSONDecodeError("bad prompt: " + repr(prompt), prompt, 0)

    monkeypatch.setattr(adapter.json, "load", fail)
    assert submit(raw=prompt).err == ""
    read_only_record(
        tmp_path, project, "invalid-session.jsonl", prompt=None,
        identifiers=(None, None), raw_identifiers=(None, None), levels=("UNKNOWN", "UNKNOWN"),
        errors=["invalid_json", "wrong_event", "invalid_session_id", "invalid_turn_id", "missing_prompt"],
    )


@pytest.mark.parametrize("function", ["detect_task_level", "apply_upgrade_triggers"])
@pytest.mark.parametrize("value", [PROMPT, "l0", "UNKNOWN", "L3", None, 1, [], {}])
def test_invalid_level_returns_cannot_leak_through_either_existing_level_field(
    tmp_path, project, submit, monkeypatch, function, value,
):
    if function == "detect_task_level":
        monkeypatch.setattr(classifier, function, lambda prompt: value)

        def unexpected_upgrade(*args, **kwargs):
            pytest.fail("invalid detector levels must not reach upgrade")

        monkeypatch.setattr(classifier, "apply_upgrade_triggers", unexpected_upgrade)
        levels = ("UNKNOWN", "UNKNOWN")
    else:
        monkeypatch.setattr(classifier, "detect_task_level", lambda prompt: "L0")
        monkeypatch.setattr(classifier, function, lambda *args, **kwargs: (value, []))
        levels = ("L0", "UNKNOWN")
    assert submit(event()).err == ""
    read_only_record(tmp_path, project, levels=levels, errors=["invalid_level_return"])


@pytest.mark.parametrize("prompt, untrusted_load", [
    (PROMPT, PROMPT), (PROMPT, PROMPT[:4]), (PROMPT, PROMPT.casefold()),
    ("sensitivecanary", "sensitivecanary"),
    ("SensitiveCanary", "canary"), ("ＳＥＮＳＩＴＩＶＥ", "sensitive"),
    ("ABCD\nEFGH\nIJKL", repr("ABCD\nEFGH\nIJKL")),
    (PROMPT, "governance/ARCHITECTURE.md"), (PROMPT, "a" * 65),
    (PROMPT, "bad\nload"), (PROMPT, None), (PROMPT, 1), (PROMPT, {}),
])
def test_upgrade_loads_drop_prompt_echoes_and_invalid_resource_tokens(
    tmp_path, project, submit, monkeypatch, prompt, untrusted_load,
):
    monkeypatch.setattr(classifier, "detect_task_level", lambda prompt: "L0")
    monkeypatch.setattr(classifier, "apply_upgrade_triggers",
                        lambda *args, **kwargs: ("L1", ["domain_summary", untrusted_load]))
    assert submit(event(prompt)).err == ""
    read_only_record(
        tmp_path, project, prompt=prompt, levels=("L0", "L1"), loads=["domain_summary"],
        errors=["invalid_upgrade_load"],
    )


@pytest.mark.parametrize("loads", [PROMPT, None, {}, ("domain_summary",)])
def test_upgrade_loads_require_a_list(tmp_path, project, submit, monkeypatch, loads):
    monkeypatch.setattr(classifier, "apply_upgrade_triggers", lambda *args, **kwargs: ("L0", loads))
    assert submit(event()).err == ""
    read_only_record(tmp_path, project, errors=["invalid_upgrade_load"])


def test_upgrade_load_resource_name_boundaries(tmp_path, project, submit, monkeypatch):
    loads = ["domain_summary", "z", "z" * 64, "resource_42"]
    monkeypatch.setattr(classifier, "apply_upgrade_triggers", lambda *args, **kwargs: ("L0", loads))
    assert submit(event()).err == ""
    read_only_record(tmp_path, project, loads=loads)


def test_each_turn_appends_one_record_and_measures_handler_elapsed_ms(project, submit, monkeypatch):
    ticks = iter([10.0, 10.125, 20.0, 20.25])
    monkeypatch.setattr(adapter, "perf_counter", lambda: next(ticks))
    submit(event())
    submit({**event(), "turn_id": "turn-2"})
    path = project / "artifacts/runtime/level-floor" / KNOWN_RECORD_NAME
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [record["turn_id"] for record in records] == ["turn-1", "turn-2"]
    assert [record["handler_elapsed_ms"] for record in records] == [125.0, 250.0]


def test_handler_elapsed_ms_includes_serialization_and_open_but_excludes_final_write(
    tmp_path, project, submit, monkeypatch,
):
    ticks = [10.0]
    operations = []
    original_dumps = json.dumps
    original_open = Path.open

    def clock():
        operations.append("clock")
        return ticks[0]

    def serialize(value, *args, **kwargs):
        if isinstance(value, dict) and "handler_elapsed_ms" in value:
            operations.append("serialize")
            ticks[0] += 0.25
        return original_dumps(value, *args, **kwargs)

    class RecordStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            operations.append("open")
            ticks[0] += 0.125
            self.stream.__enter__()
            return self

        def write(self, text):
            operations.append("write")
            ticks[0] += 10.0
            return self.stream.write(text)

        def __exit__(self, *args):
            operations.append("close")
            ticks[0] += 10.0
            return self.stream.__exit__(*args)

    def open_record(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return RecordStream(stream) if path.suffix == ".jsonl" else stream

    monkeypatch.setattr(adapter, "perf_counter", clock)
    monkeypatch.setattr(adapter.json, "dumps", serialize)
    monkeypatch.setattr(Path, "open", open_record)
    assert submit(event()).err == ""
    assert operations == ["clock", "open", "serialize", "clock", "write", "close"]
    monkeypatch.setattr(Path, "open", original_open)
    assert read_only_record(tmp_path, project)["handler_elapsed_ms"] == 375.0


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
            (directory / KNOWN_RECORD_NAME).symlink_to(outside / "escaped.jsonl")
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
    read_only_record(tmp_path, project)


@pytest.mark.parametrize("failure", ["ImportError", "RuntimeError", "SystemExit"])
def test_cli_bootstrap_import_failure_exits_zero_without_stdout_and_records_fixed_error(
    tmp_path, project, failure,
):
    entry = Path(adapter.__file__).resolve()
    child = """
import builtins
import runpy
import sys

entry, project_root, failure = sys.argv[1:]
original_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == "governance_tools.task_level_detector":
        print("BOOTSTRAP_PROMPT_CANARY")
        print("BOOTSTRAP_PROMPT_CANARY", file=sys.stderr)
        error = {"ImportError": ImportError, "RuntimeError": RuntimeError, "SystemExit": SystemExit}[failure]
        raise error("BOOTSTRAP_PROMPT_CANARY")
    return original_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
sys.argv = [entry, "--project-root", project_root]
runpy.run_path(entry, run_name="__main__")
"""
    prompt = "BOOTSTRAP_PROMPT_CANARY"
    result = subprocess.run(
        [sys.executable, "-B", "-c", child, str(entry), str(project), failure],
        cwd=tmp_path, input=json.dumps(event(prompt)), text=True, encoding="utf-8",
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == "UserPromptSubmit: bootstrap failed\n"
    record = read_only_record(
        tmp_path, project, prompt=prompt, levels=("UNKNOWN", "UNKNOWN"), errors=["bootstrap_error"],
    )
    assert prompt not in json.dumps(record)


@pytest.mark.parametrize("exception_type", [RuntimeError, SystemExit])
def test_handler_setup_failure_is_guarded_and_writes_best_effort_record(
    tmp_path, project, submit, monkeypatch, exception_type,
):
    def fail():
        raise exception_type(PROMPT)

    monkeypatch.setattr(adapter, "_framework_commit", fail)
    assert submit(event()).err == "UserPromptSubmit: bootstrap failed\n"
    read_only_record(
        tmp_path, project, "invalid-session.jsonl", prompt=None,
        identifiers=(None, None), raw_identifiers=(None, None), levels=("UNKNOWN", "UNKNOWN"),
        errors=["bootstrap_error"],
    )


def test_record_initialization_failure_still_exits_zero_without_free_text(
    tmp_path, project, submit, monkeypatch,
):
    def fail():
        raise RuntimeError(PROMPT)

    monkeypatch.setattr(adapter, "_empty_record", fail)
    assert submit(event()).err == "UserPromptSubmit: bootstrap failed\n"
    assert set(tmp_path.rglob("*")) == {project}


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
