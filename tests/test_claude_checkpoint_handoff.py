"""S1 P2: real hooks retain only this session's previously verified binding.

The owner-provided regression sequences are the behavior source. Formal release
uses the real claude_formal_closeout CLI in a synthetic registered submodule.
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import zipfile

import pytest

from tests.test_claude_closeout_admission import claude_rows, write_rows
from tests.test_claude_session_lifecycle import (
    FRAMEWORK, INPUT, LIFECYCLE, SID_A, SID_B, SUBMODULE, consumer as lifecycle_consumer,
    environment, git, hook, invoke, lc, owner,
)

SID_C = "cccccccc-0000-4000-8000-000000000003"
A_SUMMARY = "A verified progress from evidence.txt."
B_SUMMARY = "B independent progress from evidence.txt."


@pytest.fixture(scope="module")
def framework_source(tmp_path_factory):
    # The complete closeout CLI has more dependencies than the small lifecycle
    # fixture. Follow the existing registered-submodule tests' archive pattern,
    # overlaying the lifecycle under test before committing the synthetic copy.
    root = tmp_path_factory.mktemp("sf")
    archive = subprocess.run(
        ["git", "-C", str(FRAMEWORK), "archive", "--format=zip", "HEAD"],
        capture_output=True, check=True, env=environment(),
    ).stdout
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        bundle.extractall(root)
    shutil.copyfile(FRAMEWORK / LIFECYCLE, root / LIFECYCLE)
    git(root, "init", "--quiet")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic checkpoint handoff framework")
    return root


@pytest.fixture
def consumer(lifecycle_consumer):
    root = lifecycle_consumer
    (root / "AGENTS.md").write_text("# Synthetic governed consumer\n", encoding="utf-8")
    git(root, "add", "AGENTS.md")
    git(root, "commit", "-qm", "synthetic governance marker")
    return root


def _start(root, sid=SID_A, source="startup"):
    result = hook(root, "session_start", {
        "hook_event_name": "SessionStart", "session_id": sid,
        "cwd": str(root), "source": source,
    })
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def _checkpoint_path(root, sid=SID_A):
    return root / lc.CHECKPOINTS_DIR / f"{sid}.json"


def _end(root, sid=SID_A):
    result = hook(root, "session_end", {
        "hook_event_name": "SessionEnd", "session_id": sid,
        "cwd": str(root), "reason": "other",
    })
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""
    return json.loads(_checkpoint_path(root, sid).read_bytes())


def _legacy_end(root, tmp_path):
    """Run the actual 10bd1f09 hook, including its unsafe re-binding behavior."""
    source = subprocess.run([
        "git", "-C", str(FRAMEWORK), "show", f"10bd1f09:{LIFECYCLE}",
    ], capture_output=True, check=True, env=environment()).stdout
    script = tmp_path / "legacy" / LIFECYCLE
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_bytes(source)
    result = subprocess.run([
        sys.executable, "-B", "-S", str(script), "--event", "session_end",
        "--project-root", str(root),
    ], input=json.dumps({"hook_event_name": "SessionEnd", "session_id": SID_A,
                         "cwd": str(root), "reason": "other"}), cwd=root,
        env={**environment(), "PYTHONPATH": str(root / SUBMODULE)},
        capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""
    checkpoint = json.loads(_checkpoint_path(root).read_bytes())
    assert "candidate_rejected" not in checkpoint  # no version/self-trust marker
    return checkpoint


def _prepare(root, sid=SID_A, summary=A_SUMMARY):
    result = invoke(root, sid=sid, inputs={**INPUT, "work_summary": summary})
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["candidate_identity"]


def _release(root, tmp_path):
    transcript = write_rows(tmp_path / "a.jsonl", claude_rows(root, sid=SID_A))
    result = subprocess.run([
        sys.executable, "-B", "-S",
        str(root / SUBMODULE / "governance_tools/claude_formal_closeout.py"),
        "--project-root", str(root), "--session-id", SID_A,
        "--owner-request", "please close out this synthetic session",
        "--transcript-path", str(transcript), "--deadline-ms", "30000",
    ], cwd=root, env=environment(), capture_output=True, text=True,
        encoding="utf-8", timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "FINALIZED" and report["owner_state"] == "RELEASED"
    assert owner(root)["state"] == "RELEASED"


def _tamper(root, identity):
    path = root / identity["relative_path"]
    value = json.loads(path.read_bytes())
    value["work_summary"] = "TAMPERED progress"
    path.write_text(json.dumps(value), encoding="utf-8")


def _released_a(root, tmp_path):
    _start(root)
    identity = _prepare(root)
    assert _end(root)["candidate"] == identity
    _release(root, tmp_path)
    return identity


def _b_prepares(root):
    _start(root, SID_B)
    identity = _prepare(root, SID_B, B_SUMMARY)
    assert _end(root, SID_B)["candidate"] == identity
    return identity


def test_real_hooks_refuse_tamper_across_two_resumes(consumer):
    _start(consumer)
    identity = _prepare(consumer)
    assert _end(consumer)["candidate"] == identity
    _tamper(consumer, identity)
    refused = _start(consumer, source="resume")
    assert "state=checkpoint_mismatch" in refused and "TAMPERED" not in refused
    checkpoint = _end(consumer)
    assert checkpoint["candidate"] is None and checkpoint["candidate_rejected"]
    again = _start(consumer, source="resume")
    assert "state=exit_unconfirmed" in again and "(no verified summary)" in again
    assert "TAMPERED" not in again


@pytest.mark.parametrize("drop_release", [False, True])
def test_formal_closeout_then_late_exit_preserves_handoff(consumer, tmp_path, drop_release):
    identity = _released_a(consumer, tmp_path)
    released_owner = (consumer / lc.OWNER_RECORD).read_bytes()
    if drop_release:
        # A matching RELEASED owner is independently sufficient for read-back;
        # this does not attempt the next prepare, which needs the release proof.
        generation = owner(consumer)["generation"]
        (consumer / lc.OWNER_RECORD.parent / "releases" / f"{generation}.json").unlink()
    assert _end(consumer)["candidate"] == identity
    context = _start(consumer, SID_B)
    assert "state=checkpointed" in context and A_SUMMARY in context
    assert (consumer / lc.OWNER_RECORD).read_bytes() == released_owner


def test_a_late_exit_keeps_a_binding_after_b_prepares(consumer, tmp_path):
    a = _released_a(consumer, tmp_path)
    generation = owner(consumer)["generation"]
    release = json.loads((consumer / lc.OWNER_RECORD.parent / "releases" / f"{generation}.json").read_bytes())
    assert release["consumer_root"] == str(consumer) and release["session_id"] == SID_A
    assert release["state"] == "RELEASED" and release["candidate_identity"] == a
    b = _b_prepares(consumer)
    assert a != b
    owner_before = (consumer / lc.OWNER_RECORD).read_bytes()
    b_before = _checkpoint_path(consumer, SID_B).read_bytes()
    assert _end(consumer)["candidate"] == a
    assert _checkpoint_path(consumer, SID_B).read_bytes() == b_before
    assert (consumer / lc.OWNER_RECORD).read_bytes() == owner_before
    assert owner(consumer)["session_id"] == SID_B
    context = _start(consumer, SID_C)
    assert "state=checkpointed" in context and A_SUMMARY in context and B_SUMMARY not in context
    context_b = _start(consumer, SID_B, "resume")
    assert "state=checkpointed" in context_b and B_SUMMARY in context_b


def test_legacy_rebound_checkpoint_requires_r2_vouch_after_upgrade(consumer, tmp_path):
    _start(consumer)
    prepared = _prepare(consumer)
    assert _legacy_end(consumer, tmp_path)["candidate"] == prepared
    owner_before = (consumer / lc.OWNER_RECORD).read_bytes()
    _tamper(consumer, prepared)
    refused = _start(consumer, source="resume")
    assert "state=checkpoint_mismatch" in refused and "TAMPERED" not in refused
    rebound = _legacy_end(consumer, tmp_path)["candidate"]
    assert rebound["relative_path"] == prepared["relative_path"]
    assert rebound["sha256"] != prepared["sha256"]

    upgraded = _end(consumer)
    resumed = _start(consumer, source="resume")
    assert "(no verified summary)" in resumed and "TAMPERED" not in resumed
    assert upgraded["candidate"] is None and upgraded["candidate_rejected"]
    assert (consumer / lc.OWNER_RECORD).read_bytes() == owner_before


@pytest.mark.parametrize("fault", ["sha256", "consumer_root", "session_id"])
def test_release_record_must_vouch_for_carried_binding(consumer, tmp_path, fault):
    a = _released_a(consumer, tmp_path)
    generation = owner(consumer)["generation"]
    release_path = consumer / lc.OWNER_RECORD.parent / "releases" / f"{generation}.json"
    _b_prepares(consumer)
    owner_before = (consumer / lc.OWNER_RECORD).read_bytes()
    b_before = _checkpoint_path(consumer, SID_B).read_bytes()
    candidate_before = (consumer / a["relative_path"]).read_bytes()
    release = json.loads(release_path.read_bytes())
    if fault == "sha256":
        release["candidate_identity"]["sha256"] = "0" * 64
    elif fault == "consumer_root":
        release["consumer_root"] = str(consumer / "elsewhere")
    else:
        release["session_id"] = SID_B
    release_path.write_text(json.dumps(release), encoding="utf-8")

    checkpoint = _end(consumer)
    assert checkpoint["candidate"] is None and checkpoint["candidate_rejected"]
    context = _start(consumer, source="resume")
    assert "(no verified summary)" in context and A_SUMMARY not in context
    assert (consumer / a["relative_path"]).read_bytes() == candidate_before
    assert _checkpoint_path(consumer, SID_B).read_bytes() == b_before
    assert (consumer / lc.OWNER_RECORD).read_bytes() == owner_before


def test_carried_binding_is_refused_if_file_is_tampered_later(consumer, tmp_path):
    identity = _released_a(consumer, tmp_path)
    assert _end(consumer)["candidate"] == identity
    _tamper(consumer, identity)
    refused = _start(consumer, SID_B)
    assert "state=checkpoint_mismatch" in refused and "TAMPERED" not in refused
    assert _end(consumer)["candidate"] is None
    refused_again = _start(consumer, SID_C)
    assert "(no verified summary)" in refused_again and "TAMPERED" not in refused_again


@pytest.mark.parametrize("previous", ["missing", "foreign_session", "foreign_candidate"])
def test_late_exit_never_borrows_b_checkpoint(consumer, tmp_path, previous):
    _released_a(consumer, tmp_path)
    b = _b_prepares(consumer)
    a_path = _checkpoint_path(consumer)
    if previous == "missing":
        a_path.unlink()
    elif previous == "foreign_session":
        a_path.write_bytes(_checkpoint_path(consumer, SID_B).read_bytes())
    else:
        a_checkpoint = json.loads(a_path.read_bytes())
        a_checkpoint["candidate"] = b
        a_path.write_text(json.dumps(a_checkpoint), encoding="utf-8")
    b_before = _checkpoint_path(consumer, SID_B).read_bytes()
    assert _end(consumer)["candidate"] is None
    context = _start(consumer, source="resume")
    assert "(no verified summary)" in context and B_SUMMARY not in context
    assert _checkpoint_path(consumer, SID_B).read_bytes() == b_before


@pytest.mark.parametrize("record_name", ["owner", "release", "checkpoint"])
@pytest.mark.parametrize("damage", ["deep", "oversize"])
def test_corrupted_trust_json_still_writes_rejected_checkpoint(consumer, tmp_path, record_name, damage):
    if record_name == "owner":
        _start(consumer)
        identity = _prepare(consumer)
        assert _end(consumer)["candidate"] == identity
        path = consumer / lc.OWNER_RECORD
    else:
        identity = _released_a(consumer, tmp_path)
        path = _checkpoint_path(consumer)
        if record_name == "release":
            generation = owner(consumer)["generation"]
            path = consumer / lc.RELEASES_DIR / f"{generation}.json"
            _b_prepares(consumer)

    original = json.loads(path.read_bytes())
    if damage == "deep":
        # Construct valid JSON without asking the test's own encoder to recurse.
        raw = json.dumps(original)[:-1] + ', "extra":' + "[" * 5000 + "0" + "]" * 5000 + "}"
    else:
        # Still a valid, matching record if the reader ignores the size bound.
        raw = json.dumps({**original, "extra": "x" * (128 * 1024)})
    path.write_text(raw, encoding="utf-8")
    corrupted = path.read_bytes()
    candidate_before = (consumer / identity["relative_path"]).read_bytes()
    owner_before = (consumer / lc.OWNER_RECORD).read_bytes()
    b_before = _checkpoint_path(consumer, SID_B).read_bytes() if record_name == "release" else None

    checkpoint = _end(consumer)  # Real hook must return zero and replace the checkpoint.
    assert checkpoint["candidate"] is None and checkpoint["candidate_rejected"]
    context = _start(consumer, source="resume")
    assert "(no verified summary)" in context and A_SUMMARY not in context
    assert (consumer / identity["relative_path"]).read_bytes() == candidate_before
    assert (consumer / lc.OWNER_RECORD).read_bytes() == owner_before
    if record_name != "checkpoint":
        assert path.read_bytes() == corrupted
    if b_before is not None:
        assert _checkpoint_path(consumer, SID_B).read_bytes() == b_before
