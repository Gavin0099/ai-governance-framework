from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
REPO = Path.cwd().resolve()
MANIFEST = BASE / "capability-probe-02-invocation-journal-manifest.json"
COMMIT = "1" * 40
EXECUTION_PACKET_SHA256 = "2" * 64
READINESS_REVIEW_SHA256 = "3" * 64
BOOTSTRAP_SHA256 = "4" * 64


def load_module():
    path = BASE / "invocation_journal_bootstrap.py"
    spec = importlib.util.spec_from_file_location("c1_probe02_invocation_journal_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


JOURNAL = load_module()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def success_result() -> object:
    return JOURNAL.ChildResult(0, False, b"", b"")


def invoke(
    tmp_path: Path,
    launcher,
    *,
    publisher=JOURNAL._atomic_publish,
    child_output_root: Path | None = None,
):
    parent = tmp_path / "evidence"
    parent.mkdir(exist_ok=True)
    return JOURNAL.run_journaled_child(
        journal_root=parent / "journal",
        child_output_root=child_output_root or parent / "attempt",
        commit=COMMIT,
        execution_packet_sha256=EXECUTION_PACKET_SHA256,
        readiness_review_sha256=READINESS_REVIEW_SHA256,
        bootstrap_sha256=BOOTSTRAP_SHA256,
        child_argv=["python", "-I", "-"],
        child_payload=b"verified child bytes",
        cwd=tmp_path,
        environment={"NO_COLOR": "1"},
        timeout=1.0,
        launcher=launcher,
        publisher=publisher,
        clock=lambda: "2026-08-28T00:00:00Z",
    )


def test_authority_is_consumed_before_child_launch(tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def launcher(argv, payload, cwd, environment, timeout):
        root = tmp_path / "evidence" / "journal"
        start = json.loads((root / JOURNAL.START_NAME).read_bytes())
        observed.update(start)
        assert not (root / JOURNAL.OUTCOME_NAME).exists()
        return JOURNAL.ChildResult(7, False, b"child-out", b"child-err")

    outcome = invoke(tmp_path, launcher)
    assert observed["authority_consumed"] is True
    assert observed["execution_authorization_packet_sha256"] == EXECUTION_PACKET_SHA256
    assert observed["readiness_review_sha256"] == READINESS_REVIEW_SHA256
    assert observed["journal_bootstrap_sha256"] == BOOTSTRAP_SHA256
    assert observed["child_launch_attempted"] is False
    assert outcome["status"] == "INVOCATION_CHILD_NONZERO"
    assert outcome["child_launch_attempted"] is True


def test_child_nonzero_produces_bounded_outcome_without_raw_output(tmp_path: Path) -> None:
    outcome = invoke(
        tmp_path,
        lambda *args: JOURNAL.ChildResult(9, False, b"private stdout", b"private stderr"),
    )
    assert outcome["status"] == "INVOCATION_CHILD_NONZERO"
    assert outcome["child_result"]["stdout_bytes"] == len(b"private stdout")
    assert outcome["child_result"]["stderr_bytes"] == len(b"private stderr")
    payload = (tmp_path / "evidence" / "journal" / JOURNAL.OUTCOME_NAME).read_bytes()
    assert b"private stdout" not in payload
    assert b"private stderr" not in payload
    assert outcome["raw_stdout_retained"] is False
    assert outcome["raw_stderr_retained"] is False


def test_child_preclaim_failure_is_bounded_by_outer_outcome(tmp_path: Path) -> None:
    outcome = invoke(
        tmp_path,
        lambda *args: JOURNAL.ChildResult(2, False, b"", b"binding failed"),
    )
    assert outcome["status"] == "INVOCATION_CHILD_NONZERO"
    assert outcome["child_terminal"]["present"] is False
    assert JOURNAL.inspect_journal(tmp_path / "evidence" / "journal") == outcome["status"]


def test_child_terminal_publication_denial_is_bounded_by_outer_outcome(tmp_path: Path) -> None:
    output = tmp_path / "evidence" / "attempt"

    def launcher(*args):
        output.mkdir()
        return JOURNAL.ChildResult(1, False, b"", b"terminal publication denied")

    outcome = invoke(tmp_path, launcher, child_output_root=output)
    assert outcome["status"] == "INVOCATION_CHILD_NONZERO"
    assert output.is_dir()
    assert list(output.iterdir()) == []
    assert outcome["child_terminal"]["present"] is False
    assert (tmp_path / "evidence" / "journal" / JOURNAL.OUTCOME_NAME).is_file()


def test_child_launch_failure_produces_bounded_outcome(tmp_path: Path) -> None:
    def launcher(*args):
        raise PermissionError("synthetic launch denial")

    outcome = invoke(tmp_path, launcher)
    assert outcome["status"] == "INVOCATION_CHILD_LAUNCH_FAILED"
    assert outcome["exception_class"] == "PermissionError"
    assert outcome["child_result"] is None
    assert JOURNAL.inspect_journal(tmp_path / "evidence" / "journal") == outcome["status"]


def test_child_crash_produces_bounded_outcome(tmp_path: Path) -> None:
    def launcher(*args):
        raise KeyboardInterrupt()

    outcome = invoke(tmp_path, launcher)
    assert outcome["status"] == "INVOCATION_CHILD_CRASHED"
    assert outcome["exception_class"] == "KeyboardInterrupt"


def test_child_timeout_produces_bounded_outcome(tmp_path: Path) -> None:
    outcome = invoke(
        tmp_path,
        lambda *args: JOURNAL.ChildResult(None, True, b"partial", b"timeout"),
    )
    assert outcome["status"] == "INVOCATION_CHILD_TIMEOUT"
    assert outcome["child_result"]["timed_out"] is True


def test_zero_without_child_terminal_is_not_completion(tmp_path: Path) -> None:
    outcome = invoke(tmp_path, lambda *args: success_result())
    assert outcome["status"] == "INVOCATION_CHILD_ZERO_WITHOUT_TERMINAL"
    assert outcome["child_terminal"]["present"] is False


def test_child_terminal_is_projected_by_digest_not_raw_bytes(tmp_path: Path) -> None:
    output = tmp_path / "evidence" / "attempt"

    def launcher(*args):
        output.mkdir()
        payload = b'{"status":"CAPABILITY_PROBE_AMBIGUOUS"}\n'
        (output / "terminal.json").write_bytes(payload)
        return success_result()

    outcome = invoke(tmp_path, launcher, child_output_root=output)
    assert outcome["status"] == "INVOCATION_CHILD_COMPLETED"
    assert outcome["child_terminal"] == {
        "present": True,
        "bytes": 40,
        "sha256": sha256(b'{"status":"CAPABILITY_PROBE_AMBIGUOUS"}\n'),
        "status": "CAPABILITY_PROBE_AMBIGUOUS",
    }
    assert b'{"status":"CAPABILITY_PROBE_AMBIGUOUS"}' not in (
        tmp_path / "evidence" / "journal" / JOURNAL.OUTCOME_NAME
    ).read_bytes()


def test_outcome_publication_denial_leaves_durable_start(tmp_path: Path) -> None:
    def publisher(root: Path, name: str, payload: bytes):
        if name == JOURNAL.OUTCOME_NAME:
            raise PermissionError("synthetic outcome denial")
        return JOURNAL._atomic_publish(root, name, payload)

    with pytest.raises(JOURNAL.OutcomePublicationError, match="start receipt remains"):
        invoke(tmp_path, lambda *args: JOURNAL.ChildResult(5, False, b"", b""), publisher=publisher)
    root = tmp_path / "evidence" / "journal"
    assert (root / JOURNAL.START_NAME).is_file()
    assert not (root / JOURNAL.OUTCOME_NAME).exists()
    assert JOURNAL.inspect_journal(root) == "INVOCATION_STARTED_OUTCOME_INCOMPLETE"


def test_wrapper_crash_after_start_is_bounded_by_start_receipt(tmp_path: Path) -> None:
    root = tmp_path / "journal"
    JOURNAL._claim_journal(root)
    JOURNAL._atomic_publish(
        root,
        JOURNAL.START_NAME,
        JOURNAL._start_payload(
            COMMIT,
            "2026-08-28T00:00:00Z",
            EXECUTION_PACKET_SHA256,
            READINESS_REVIEW_SHA256,
            BOOTSTRAP_SHA256,
        ),
    )
    assert JOURNAL.inspect_journal(root) == "INVOCATION_STARTED_OUTCOME_INCOMPLETE"


def test_start_publication_failure_never_launches_child_or_consumes_authority(tmp_path: Path) -> None:
    launches = 0

    def launcher(*args):
        nonlocal launches
        launches += 1
        return success_result()

    def publisher(root: Path, name: str, payload: bytes):
        raise PermissionError("synthetic start denial")

    with pytest.raises(PermissionError):
        invoke(tmp_path, launcher, publisher=publisher)
    assert launches == 0
    assert not (tmp_path / "evidence" / "journal").exists()


def test_concurrent_invocation_has_one_owner_and_one_child_launch(tmp_path: Path) -> None:
    parent = tmp_path / "evidence"
    parent.mkdir()
    root = parent / "journal"
    launch_count = 0
    launch_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def launcher(*args):
        nonlocal launch_count
        with launch_lock:
            launch_count += 1
        return JOURNAL.ChildResult(6, False, b"", b"")

    def run():
        barrier.wait()
        try:
            return JOURNAL.run_journaled_child(
                journal_root=root,
                child_output_root=parent / "attempt",
                commit=COMMIT,
                execution_packet_sha256=EXECUTION_PACKET_SHA256,
                readiness_review_sha256=READINESS_REVIEW_SHA256,
                bootstrap_sha256=BOOTSTRAP_SHA256,
                child_argv=["child"],
                child_payload=b"bytes",
                cwd=tmp_path,
                environment={},
                timeout=1.0,
                launcher=launcher,
                clock=lambda: "2026-08-28T00:00:00Z",
            )["status"]
        except JOURNAL.JournalAlreadyClaimed:
            return "LOSER"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert results.count("INVOCATION_CHILD_NONZERO") == 1
    assert results.count("LOSER") == 1
    assert launch_count == 1
    assert sorted(item.name for item in root.iterdir()) == ["outcome.json", "start.json"]


def test_direct_file_execution_is_rejected_before_repo_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "argv", [str(BASE / "invocation_journal_bootstrap.py")])
    with pytest.raises(JOURNAL.JournalError, match="streamed"):
        JOURNAL.execute(
            repo_root=tmp_path,
            owner_authorized_freeze_commit="1" * 40,
            owner_authorized_execution_packet_sha256="2" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
        )


def test_manifest_authorities_are_all_false() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert all(value is False for value in manifest["execution_authority"].values())
    assert all(value is False for value in manifest["authoring_boundary"].values())


def test_policy_fixes_authority_consumption_boundary() -> None:
    policy = json.loads((BASE / "invocation-journal-policy.json").read_text(encoding="utf-8"))
    assert policy["authority_consumed_when"] == "START_RECEIPT_VISIBLE_AND_READBACK_EXACT"
    assert policy["authority_not_consumed_before_start"] is True
    assert policy["child_launch_before_start_forbidden"] is True
    assert policy["start_only_state"] == "INVOCATION_STARTED_OUTCOME_INCOMPLETE"
    assert policy["retry_allowed"] is False


def test_audit_binding_matches_reviewed_silent_failure() -> None:
    binding = json.loads((BASE / "probe02-silent-failure-audit-binding.json").read_text(encoding="utf-8"))
    assert binding["audited_commit"] == "2e42cc6abe0c3f6cdea89e660cc1271c5842fb33"
    assert binding["audit_session"] == "2026-08-28-69"
    assert binding["audit_terminal"] == "SILENT_FAILURE_PATH_REMAINS"
    assert binding["correction_required_before_readiness_authorization"] is True


def test_frozen_inventory_matches_files_and_git_blob_oids() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {"capability-probe-02-invocation-journal-manifest.json"}
    for entry in manifest["frozen_files"]:
        path = BASE / entry["path"]
        payload = path.read_bytes()
        expected.add(entry["path"])
        assert len(payload) == entry["bytes"]
        assert sha256(payload) == entry["sha256"]
        oid = subprocess.check_output(["git", "hash-object", str(path)], cwd=REPO, text=True).strip()
        assert oid == entry["git_blob_oid"]
    actual = {item.name for item in BASE.iterdir() if item.name != "__pycache__"}
    assert actual == expected
    bootstrap = (BASE / "invocation_journal_bootstrap.py").read_bytes()
    assert sha256(bootstrap) == manifest["frozen_executor_sha256"]


def test_source_binding_matches_reviewed_probe02_bootstrap() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    binding = manifest["source_bindings"][0]
    oid = subprocess.check_output(
        ["git", "rev-parse", f'{binding["commit"]}:{binding["path"]}'],
        cwd=REPO,
        text=True,
    ).strip()
    payload = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=REPO)
    assert oid == binding["git_blob_oid"]
    assert len(payload) == binding["bytes"]
    assert sha256(payload) == binding["sha256"]


def test_formal_roots_remain_absent() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw = manifest["derived_paths"]
    for key in ("journal_root", "attempt_output_root", "cli_staging_root", "private_root"):
        assert not (REPO / raw[key]).exists()


def test_no_hosted_auth_randomization_or_retry_surface() -> None:
    source = (BASE / "invocation_journal_bootstrap.py").read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    policy = json.loads((BASE / "invocation-journal-policy.json").read_text(encoding="utf-8"))
    assert "urlopen" not in source
    assert "requests." not in source
    assert "--auth-file" not in source
    assert "auth.json" not in source
    assert policy["hosted_requests"] == 0
    assert policy["auth_payloads"] == 0
    assert policy["retry_allowed"] is False
    assert manifest["journal_contract"]["retry_allowed"] is False
    assert manifest["authoring_boundary"]["randomization_created"] is False


def test_start_and_outcome_files_are_create_once(tmp_path: Path) -> None:
    root = tmp_path / "journal"
    root.mkdir()
    payload = JOURNAL._start_payload(
        COMMIT,
        "2026-08-28T00:00:00Z",
        EXECUTION_PACKET_SHA256,
        READINESS_REVIEW_SHA256,
        BOOTSTRAP_SHA256,
    )
    JOURNAL._atomic_publish(root, JOURNAL.START_NAME, payload)
    with pytest.raises(JOURNAL.JournalError, match="already exists"):
        JOURNAL._atomic_publish(root, JOURNAL.START_NAME, payload)
    assert sorted(item.name for item in root.iterdir()) == ["start.json"]
