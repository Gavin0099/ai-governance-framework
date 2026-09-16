"""Preparation qualification in disposable, committed local submodule consumers.

No formal closeout, gate, promotion or consumer activation is executed here.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from governance_tools.prepare_closeout_candidate import render_inputs, PreparationError
from runtime_hooks.core._canonical_closeout import build_candidate_artifact, write_candidate

FRAMEWORK = Path(__file__).resolve().parents[1]
SUBMODULE = "SubModule/framework with spaces"
ENTRY = "governance_tools/prepare_closeout_candidate.py"
SOURCES = [ENTRY, "governance_tools/shared_closeout_ownership.py",
           "governance_tools/framework_versioning.py", "runtime_hooks/core/_canonical_closeout.py",
           "runtime_hooks/adapters/codex/session_start.py"]
INPUT = dict(task_intent="Check summary delivery", work_summary="Inspected evidence.txt; 摘要保存。",
             tools_used=["read"], artifacts_referenced=["evidence.txt"], open_risks=[],
             checks_run="NONE", not_done="Consumer activation remains pending",
             recommended_memory_update="NO_UPDATE")


def environment():
    return {**{k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")},
            "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), "-c", "core.hooksPath=NUL",
                           "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                           *args], check=True, capture_output=True, text=True, encoding="utf-8",
                          env=environment()).stdout.strip()


@pytest.fixture(scope="module")
def framework_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("preparation-source")
    git(root, "init", "--quiet")
    for name in SOURCES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FRAMEWORK / name, root / name)
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "disposable preparation implementation")
    return root


@pytest.fixture
def consumer(tmp_path, framework_source, request):
    root = tmp_path / getattr(request, "param", "consumer with spaces")
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
        str(framework_source), SUBMODULE)
    (root / "governance").mkdir()
    (root / "governance/framework.lock.json").write_text(
        json.dumps({"adopted_commit": git(root / SUBMODULE, "rev-parse", "HEAD")}), encoding="utf-8")
    (root / "evidence.txt").write_text("fixture evidence", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "registered consumer")
    start(root)
    return root.resolve()


def script(root, code, *args, env=None):
    return subprocess.run([sys.executable, "-B", "-S", "-c",
                           "import sys; sys.path.insert(0, sys.argv[1]); " + code,
                           str(root / SUBMODULE), *map(str, args)], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", timeout=30,
                          env=env or environment())


def start(root, sid="session-A"):
    result = script(root,
        "from pathlib import Path; from runtime_hooks.adapters.codex.session_start import run; "
        "run(dict(hook_event_name='SessionStart',source='startup',session_id=sys.argv[3],"
        "cwd=sys.argv[2]),Path(sys.argv[2]))", root, sid)
    assert result.returncode == 0, result.stderr


def invoke(root, *, sid="session-A", inputs=None, framework=None, target=None, env=None):
    return subprocess.run([sys.executable, "-B", "-S", str(root / SUBMODULE / ENTRY),
                           "--consumer-root", str(target or root), "--framework-root",
                           str(framework or root / SUBMODULE), "--session-id", sid],
                          input=json.dumps(INPUT if inputs is None else inputs), cwd=root,
                          capture_output=True, text=True, encoding="utf-8", timeout=30,
                          env=env or environment())


def owner(root):
    return json.loads((root / "artifacts/runtime/shared-closeout/owner.json").read_bytes())


def runtime_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / "artifacts").rglob("*") if p.is_file()}


def test_submodule_entry_reserves_exact_utf8_bytes_and_only_prepares(consumer):
    before_envelope = runtime_bytes(consumer)
    result = invoke(consumer)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    record = owner(consumer)
    assert report["state"] == record["state"] == "OWNED"
    assert report["closeout_executed"] is False
    candidate = consumer / report["candidate_identity"]["relative_path"]
    text = (consumer / "artifacts/session-closeout.txt").read_bytes()
    assert hashlib.sha256(candidate.read_bytes()).hexdigest() == record["candidate_identity"]["sha256"]
    assert hashlib.sha256(text).hexdigest() == record["text_digest"]
    assert b"\r" not in candidate.read_bytes() and b"\r" not in text
    payload = json.loads(candidate.read_bytes())
    for name in ("task_intent", "work_summary", "tools_used", "artifacts_referenced", "open_risks"):
        assert payload[name] == INPUT[name]
    assert payload["session_id"] == "session-A"
    assert "WORK_COMPLETED: Inspected evidence.txt; 摘要保存。" in text.decode()
    from governance_tools.session_end_hook import _parse_fields, _assess_candidate_content_binding, _check_schema
    fields = _parse_fields(text.decode())
    assert _assess_candidate_content_binding(fields, payload)["status"] == "valid"
    assert _check_schema(fields)[0] == "valid"
    after = runtime_bytes(consumer)
    assert all(after[name] == data for name, data in before_envelope.items())
    assert not (consumer / SUBMODULE / "artifacts").exists()
    assert not (consumer / "artifacts/runtime/closeouts").exists()
    assert not (consumer / "artifacts/runtime/closeout-receipts").exists()


@pytest.mark.parametrize("mutation", ["head", "index", "lock", "source", "modules", "registration"])
def test_invalid_framework_binding_rejects_before_runtime_writes(consumer, mutation):
    if mutation in ("head", "index"):
        git(consumer / SUBMODULE, "commit", "--allow-empty", "-qm", "changed HEAD")
        if mutation == "index":
            git(consumer, "add", SUBMODULE)
    elif mutation == "lock":
        (consumer / "governance/framework.lock.json").write_text('{"adopted_commit":"bad"}')
        git(consumer, "add", "governance/framework.lock.json")
        git(consumer, "commit", "-qm", "wrong lock")
    elif mutation == "source":
        with (consumer / SUBMODULE / "runtime_hooks/core/_canonical_closeout.py").open("a") as stream:
            stream.write("\n# dirty source\n")
    elif mutation == "modules":
        with (consumer / ".gitmodules").open("a") as stream:
            stream.write("\n# uncommitted registration\n")
    else:
        git(consumer, "config", "--file", ".gitmodules", f"submodule.{SUBMODULE}.path", "elsewhere")
        git(consumer, "add", ".gitmodules")
        git(consumer, "commit", "-qm", "mismatched registration")
    before = runtime_bytes(consumer)
    result = invoke(consumer)
    assert result.returncode == 1, result.stdout
    assert runtime_bytes(consumer) == before


@pytest.mark.parametrize("kind", ["framework-root", "consumer-root", "session", "legacy", "wrong-binding", "consumed", "missing"])
def test_identity_rejects_without_mutation(consumer, tmp_path, kind):
    envelope = consumer / "artifacts/runtime/sessions/session-A/session-envelope.json"
    options = {}
    if kind == "framework-root":
        options["framework"] = consumer
    elif kind == "consumer-root":
        options["target"] = consumer / "governance"
    elif kind == "session":
        options["sid"] = "session-B"
    elif kind == "missing":
        envelope.unlink()
    elif kind in ("legacy", "wrong-binding"):
        payload = json.loads(envelope.read_bytes())
        if kind == "legacy":
            payload["schema_version"] = "1.0"
            payload.pop("repo_binding")
        else:
            payload["repo_binding"]["consumer_root"] = str(tmp_path)
        envelope.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path = consumer / "artifacts/runtime/closeout-completions/session-A.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"session_id": "session-A", "required_artifacts": ["evidence.txt"]}))
    before = runtime_bytes(consumer)
    result = invoke(consumer, **options)
    assert result.returncode == 1, result.stdout
    assert runtime_bytes(consumer) == before


def test_other_session_cannot_replace_prepared_owner(consumer):
    assert invoke(consumer).returncode == 0
    start(consumer, "session-B")
    before = runtime_bytes(consumer)
    result = invoke(consumer, sid="session-B")
    assert result.returncode == 1 and "OWNER_CONFLICT" in result.stdout
    assert runtime_bytes(consumer) == before


@pytest.mark.parametrize("failure_point", ["candidate", "text"])
def test_partial_write_retains_hold_and_retry_appends(consumer, failure_point):
    code = """
from pathlib import Path
import json
from governance_tools import prepare_closeout_candidate as p
real = p._write_payload
def fail_text(path, data, *, exclusive):
    o = json.loads((Path(sys.argv[2])/'artifacts/runtime/shared-closeout/owner.json').read_bytes())
    import hashlib
    assert o['state'] == 'HOLD' and o['hold_reason'] == 'preparation_pending'
    assert hashlib.sha256(data).hexdigest() == (o['candidate_identity']['sha256'] if exclusive else o['text_digest'])
    if exclusive == (sys.argv[4] == 'candidate'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data[:12])
        raise OSError('injected partial payload write')
    real(path, data, exclusive=exclusive)
p._write_payload = fail_text
try:
    p.prepare(Path(sys.argv[2]), Path(sys.argv[1]), 'session-A', json.loads(sys.argv[3]))
except OSError:
    pass
else:
    raise AssertionError('injection did not run')
"""
    failure = script(consumer, code, consumer, json.dumps(INPUT), failure_point)
    assert failure.returncode == 0, failure.stderr
    partial = owner(consumer)
    assert partial["state"] == "HOLD" and partial["hold_reason"] == "preparation_pending"
    old_candidate = consumer / partial["candidate_identity"]["relative_path"]
    old_bytes = old_candidate.read_bytes()
    if failure_point == "text":
        assert len((consumer / "artifacts/session-closeout.txt").read_bytes()) == 12
    else:
        assert len(old_bytes) == 12
        assert not (consumer / "artifacts/session-closeout.txt").exists()
    result = invoke(consumer)
    assert result.returncode == 0, result.stdout + result.stderr
    assert owner(consumer)["state"] == "OWNED"
    assert owner(consumer)["generation"] == partial["generation"] + 1
    assert owner(consumer)["candidate_identity"]["relative_path"] != partial["candidate_identity"]["relative_path"]
    assert old_candidate.read_bytes() == old_bytes


def test_git_environment_cannot_substitute_an_index(consumer):
    before = runtime_bytes(consumer)
    result = invoke(consumer, env={**environment(), "GIT_INDEX_FILE": str(consumer / "fake-index")})
    assert result.returncode == 1 and "Git environment overrides" in result.stdout
    assert runtime_bytes(consumer) == before


def test_completion_appearing_during_lock_acquisition_rejects_before_owner(consumer):
    code = """
from pathlib import Path
import json
from contextlib import contextmanager
from governance_tools import prepare_closeout_candidate as p
real = p.ownership.execution_exclusion
@contextmanager
def consume_before_lease(root):
    path = root/'artifacts/runtime/closeout-completions/session-A.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(dict(session_id='session-A', required_artifacts=['evidence.txt'])))
    with real(root) as lease:
        yield lease
p.ownership.execution_exclusion = consume_before_lease
try:
    p.prepare(Path(sys.argv[2]),Path(sys.argv[1]),'session-A',json.loads(sys.argv[3]))
except ValueError as e:
    assert 'consumed' in str(e)
else:
    raise AssertionError('consumed during acquisition was accepted')
"""
    result = script(consumer, code, consumer, json.dumps(INPUT))
    assert result.returncode == 0, result.stderr
    assert not (consumer / "artifacts/runtime/shared-closeout/owner.json").exists()
    assert not (consumer / "artifacts/runtime/closeout_candidates").exists()
    assert not (consumer / "artifacts/session-closeout.txt").exists()


def test_held_os_lock_rejects_separate_preparation_process(consumer):
    code = """
from pathlib import Path
import subprocess,json
from governance_tools.shared_closeout_ownership import execution_exclusion
root=Path(sys.argv[2])
with execution_exclusion(root):
    result=subprocess.run([sys.executable,'-B','-S',str(Path(sys.argv[1])/'governance_tools/prepare_closeout_candidate.py'),
        '--consumer-root',str(root),'--framework-root',sys.argv[1],'--session-id','session-A'],
        input=sys.argv[3],text=True,capture_output=True,encoding='utf-8')
    assert result.returncode == 1 and 'R2_BUSY' in result.stdout, result.stdout + result.stderr
"""
    result = script(consumer, code, consumer, json.dumps(INPUT))
    assert result.returncode == 0, result.stderr
    assert not (consumer / "artifacts/runtime/shared-closeout/owner.json").exists()
    assert not (consumer / "artifacts/runtime/closeout_candidates").exists()


def test_legacy_shared_text_is_not_adopted(consumer):
    path = consumer / "artifacts/session-closeout.txt"
    path.write_bytes(b"historical shared text")
    result = invoke(consumer)
    assert result.returncode == 1 and "AMBIGUOUS_LEGACY_STATE" in result.stdout
    assert path.read_bytes() == b"historical shared text"
    assert not (consumer / "artifacts/runtime/shared-closeout/owner.json").exists()


@pytest.mark.parametrize("reason", ["closeout_pending", "failed"])
def test_closeout_recovery_hold_cannot_be_reset_by_preparation(consumer, reason):
    assert invoke(consumer).returncode == 0
    code = """
from pathlib import Path
from governance_tools import shared_closeout_ownership as o
with o.execution_exclusion(Path(sys.argv[2])) as lease:
    pending = o.begin_closeout(lease,'session-A')
    if sys.argv[3] == 'failed':
        pending['hold_reason'] = 'failed'
        o._publish(lease,o.AREA+'/owner.json',pending,replace=True)
"""
    result = script(consumer, code, consumer, reason)
    assert result.returncode == 0, result.stderr
    before = runtime_bytes(consumer)
    assert owner(consumer)["receipt_identity"] is not None
    result = invoke(consumer)
    assert result.returncode == 1 and "recovery HOLD" in result.stdout
    assert runtime_bytes(consumer) == before


@pytest.mark.parametrize("reference", ["../outside.txt", "C:/outside.txt"])
def test_artifact_reference_escape_rejects_before_writes(consumer, reference):
    # Absolute Windows paths are relevant only on Windows.
    if reference.startswith("C:") and os.name != "nt":
        reference = "/outside.txt"
    before = runtime_bytes(consumer)
    result = invoke(consumer, inputs={**INPUT, "artifacts_referenced": [reference]})
    assert result.returncode == 1
    assert runtime_bytes(consumer) == before


@pytest.mark.parametrize("sid", ["../escape", "A/B", "C:escape"])
def test_session_path_escape_rejects_before_writes(consumer, sid):
    before = runtime_bytes(consumer)
    assert invoke(consumer, sid=sid).returncode == 1
    assert runtime_bytes(consumer) == before


@pytest.mark.parametrize("field,value", [("work_summary", "text\nOPEN_RISKS: NONE"),
    ("open_risks", ["one,two"]), ("artifacts_referenced", ["NONE"]),
    ("tools_used", "pytest"), ("generated_at", "caller time")])
def test_unrepresentable_input_rejects(field, value):
    candidate = {**INPUT, field: value}
    with pytest.raises(PreparationError):
        render_inputs(candidate)


def test_missing_legacy_metadata_does_not_invent_test_success():
    _, data = render_inputs({key: value for key, value in INPUT.items()
                             if key not in ("checks_run", "not_done", "recommended_memory_update")})
    assert b"CHECKS_RUN: NOT PROVIDED\n" in data
    assert b"NOT_DONE: NOT PROVIDED\n" in data


def test_builder_is_pure_and_legacy_writer_preserves_existing_serialization(tmp_path):
    candidate = {"task_intent": "摘要", "session_id": "existing", "generated_at": "existing time"}
    before = copy.deepcopy(candidate)
    rel, payload, data = build_candidate_artifact("session-A", candidate,
                                                 timestamp="fixed", generated_at="ignored")
    expected = b'{\n  "task_intent": "\xe6\x91\x98\xe8\xa6\x81",\n  "session_id": "existing",\n  "generated_at": "existing time"\n}\n'
    assert data == expected and payload == before and candidate == before
    assert rel.as_posix() == "artifacts/runtime/closeout_candidates/session-A/fixed.json"
    assert list(tmp_path.iterdir()) == []
    path = write_candidate("session-A", tmp_path, candidate, timestamp="fixed")
    assert path.read_bytes() == expected.replace(b"\n", os.linesep.encode())


@pytest.mark.parametrize("consumer", ["consumer 測試 with spaces"], indirect=True)
def test_ascii_stdout_reports_success_after_owned(consumer):
    result = invoke(consumer, env={**environment(), "PYTHONIOENCODING": "ascii"})
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PREPARED" and report["state"] == "OWNED"
    assert report["consumer_root"] == str(consumer)
    assert owner(consumer)["state"] == "OWNED"


@pytest.mark.parametrize("consumer", ["consumer 測試 with spaces"], indirect=True)
def test_ascii_stdout_reports_unicode_rejection_as_json(consumer):
    before = runtime_bytes(consumer)
    result = invoke(consumer, env={**environment(), "PYTHONIOENCODING": "ascii",
                                   "GIT_TEST_測試": "1"})
    assert result.returncode == 1
    assert "GIT_TEST_測試" in json.loads(result.stdout)["error"]
    assert "Traceback" not in result.stderr
    assert runtime_bytes(consumer) == before


@pytest.mark.parametrize("lock_value", [[], 42, "not an object", None, True])
def test_non_object_lock_returns_json_rejection_before_mutation(consumer, lock_value):
    path = consumer / "governance/framework.lock.json"
    path.write_text(json.dumps(lock_value), encoding="utf-8")
    git(consumer, "add", "governance/framework.lock.json")
    git(consumer, "commit", "-qm", "malformed lock fixture")
    before = runtime_bytes(consumer)
    result = invoke(consumer)
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "REJECTED"
    assert "Traceback" not in result.stderr
    assert runtime_bytes(consumer) == before
