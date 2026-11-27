"""Regression tests for Issue #254: Prepare-to-Stop consumer gate_policy.yaml binding.

Verifies that in submodule consumers:
1. Prepare records the exact presence + SHA-256 digest of consumer
   ``governance/gate_policy.yaml`` in the R2-hashed candidate JSON
   (``gate_policy_binding``), without altering ``framework_binding`` or ``owner.json``.
2. Modifying ``governance/gate_policy.yaml`` between Prepare and Stop
   (e.g. ``fail_mode: strict`` -> ``fail_mode: audit``) fails closed BEFORE
   ``begin_closeout``, memory writes, receipt emission, or R2 ``RELEASED``.
3. Creating ``governance/gate_policy.yaml`` after Prepare (absent -> present) or
   deleting it after Prepare (present -> absent) also fails closed with zero side effects.
4. Submodule consumer ``OWNED`` candidates missing ``gate_policy_binding`` fail closed
   on both direct Stop and deferred handoff, and recover cleanly after re-Prepare.
5. Deferred handoff rejects post-Prepare ``gate_policy.yaml`` drift before writing
   any handoff request.
6. Symlinked ``governance/gate_policy.yaml`` is rejected fail-closed at Prepare and Stop.
7. Unchanged policy (strict or audit) and legitimate policy updates followed by
   re-Prepare succeed normally.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from governance_tools import prepare_closeout_candidate as preparation
from governance_tools import shared_closeout_ownership as own

FRAMEWORK = Path(__file__).resolve().parents[1]
SUBMODULE = "ai-governance-framework"
STRICT_POLICY = 'version: "1"\nfail_mode: strict\n'
AUDIT_POLICY = 'version: "1"\nfail_mode: audit\n'


def _env() -> dict[str, str]:
    return {
        **{k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")},
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git", "-C", str(root),
            "-c", "core.hooksPath=NUL",
            "-c", "user.name=Fixture",
            "-c", "user.email=fixture@example.invalid",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(),
    ).stdout.strip()


@pytest.fixture(scope="module")
def framework_src(tmp_path_factory):
    """Create a local clean framework git repo from the current checkout."""
    src = tmp_path_factory.mktemp("fw-issue254-src")
    _git(src, "init", "--quiet")
    for rel_dir in ("governance_tools", "runtime_hooks", "memory_pipeline", "governance", "schemas"):
        shutil.copytree(FRAMEWORK / rel_dir, src / rel_dir)
    for rel_file in ("AGENTS.md", "AGENTS.base.md", "PLAN.md", "contract.yaml"):
        if (FRAMEWORK / rel_file).is_file():
            shutil.copyfile(FRAMEWORK / rel_file, src / rel_file)
    (src / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    _git(src, "add", ".")
    _git(src, "commit", "-qm", "framework snapshot")
    v1 = _git(src, "rev-parse", "HEAD")
    return {"repo": src, "v1": v1}


def _make_consumer(tmp_path: Path, framework_src: dict, *, initial_policy: str | None) -> Path:
    root = (tmp_path / "consumer").resolve()
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(
        root, "-c", "protocol.file.allow=always",
        "submodule", "add", "--quiet", str(framework_src["repo"]), SUBMODULE,
    )
    (root / "AGENTS.md").write_text("# consumer\n", encoding="utf-8")
    (root / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (root / "governance").mkdir()
    (root / "governance" / "framework.lock.json").write_text(
        json.dumps({"adopted_commit": framework_src["v1"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    if initial_policy is not None:
        (root / "governance" / "gate_policy.yaml").write_text(
            initial_policy, encoding="utf-8", newline="\n"
        )
    (root / "memory").mkdir()
    (root / "evidence.txt").write_text("ok\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "init consumer")
    return root


def _start_codex_session(root: Path, sid: str) -> None:
    fw = root / SUBMODULE
    code = (
        "import sys; from pathlib import Path; "
        "from runtime_hooks.adapters.codex.session_start import run; "
        "run({'hook_event_name':'SessionStart','source':'startup',"
        "'session_id':sys.argv[2],'cwd':sys.argv[1]}, Path(sys.argv[1]))"
    )
    res = subprocess.run(
        [sys.executable, "-B", "-c", code, str(root), sid],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**_env(), "PYTHONPATH": str(fw)},
        timeout=30,
    )
    assert res.returncode == 0, res.stderr


def _prepare_candidate(root: Path, sid: str) -> subprocess.CompletedProcess:
    fw = root / SUBMODULE
    payload = {
        "task_intent": "Verify gate_policy binding symmetry",
        "work_summary": "Inspected evidence.txt under bound gate policy.",
        "tools_used": ["read"],
        "artifacts_referenced": ["evidence.txt"],
        "open_risks": [],
        "checks_run": "NONE",
        "not_done": "NONE",
        "recommended_memory_update": "NO_UPDATE",
    }
    return subprocess.run(
        [
            sys.executable, "-B",
            str(fw / "governance_tools" / "prepare_closeout_candidate.py"),
            "--consumer-root", str(root),
            "--framework-root", str(fw),
            "--session-id", sid,
        ],
        input=json.dumps(payload),
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(),
        timeout=30,
    )


def _run_codex_stop(root: Path, sid: str) -> subprocess.CompletedProcess:
    fw = root / SUBMODULE
    stdin_payload = json.dumps({
        "session_id": sid,
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    })
    return subprocess.run(
        [
            sys.executable, "-B",
            str(fw / "governance_tools" / "session_closeout_entry.py"),
            "--project-root", str(root),
            "--format", "json",
            "--agent-id", "codex",
            "--trigger-mode", "native_hook",
            "--no-ledger-write",
        ],
        input=stdin_payload,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env(),
        timeout=60,
    )


def _publish_fixture_handoff(root: Path, sid: str) -> subprocess.CompletedProcess:
    fw = root / SUBMODULE
    data = (json.dumps({"type": "session_meta", "payload": {"id": sid}}) + "\n").encode("utf-8")
    t_sha = hashlib.sha256(data).hexdigest()
    rel = f"artifacts/runtime/handoff-transcript-fixtures/{sid}/{t_sha}.jsonl"
    transcript = root / rel
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_bytes(data)
    t_ref = {
        "session_id": sid,
        "immutable_locator": rel,
        "sha256": t_sha,
        "retention_contract": "fixture-retained-transcript",
        "retention_version": "1.0",
        "readable_after_hook": True,
        "source_kind": "fixture",
    }
    manifest_bytes = json.dumps(
        {"consumer_root": str(root.resolve()), "transcript": t_ref},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    (transcript.parent / "manifest.json").write_bytes(manifest_bytes)
    code = (
        "import json, sys; from pathlib import Path; "
        "from governance_tools import closeout_handoff as h; "
        "root = Path(sys.argv[1]); sid = sys.argv[2]; ref = json.loads(sys.argv[3]); "
        "res = h.publish_request(root, sid, ref, h.FixtureTranscriptProvider(root)); "
        "print(json.dumps(res))"
    )
    return subprocess.run(
        [sys.executable, "-B", "-c", code, str(root), sid, json.dumps(t_ref)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**_env(), "PYTHONPATH": str(fw)},
        timeout=30,
    )


def _assert_no_closeout_side_effects(root: Path, sid: str) -> None:
    assert not (root / "artifacts" / "runtime" / "closeouts" / f"{sid}.json").exists()
    assert not (root / "artifacts" / "runtime" / "closeout-completions" / f"{sid}.json").exists()
    receipts_dir = root / "artifacts" / "runtime" / "closeout-receipts"
    assert not receipts_dir.exists() or not list(receipts_dir.glob("*.json"))
    releases_dir = root / "artifacts" / "runtime" / "shared-closeout" / "releases"
    assert not releases_dir.exists() or not list(releases_dir.glob("*.json"))
    assert not list((root / "memory").glob("*.md"))


def test_stop_rejects_strict_to_audit_policy_drift_before_side_effects(tmp_path, framework_src):
    """Primary #254 regression: changing strict -> audit after Prepare must fail closed."""
    consumer = _make_consumer(tmp_path, framework_src, initial_policy=STRICT_POLICY)
    sid = "session-254-strict-to-audit"
    _start_codex_session(consumer, sid)

    prep = _prepare_candidate(consumer, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr
    prep_report = json.loads(prep.stdout)
    cand = json.loads((consumer / prep_report["candidate_identity"]["relative_path"]).read_text(encoding="utf-8"))
    assert cand["gate_policy_binding"] == {
        "relative_path": "governance/gate_policy.yaml",
        "present": True,
        "sha256": hashlib.sha256(STRICT_POLICY.encode("utf-8")).hexdigest(),
    }

    # Mutate consumer gate_policy.yaml from strict to audit between Prepare and Stop
    (consumer / "governance" / "gate_policy.yaml").write_text(
        AUDIT_POLICY, encoding="utf-8", newline="\n"
    )

    stop = _run_codex_stop(consumer, sid)
    assert stop.returncode != 0
    assert "GATE_POLICY_BINDING_DRIFT" in (stop.stdout + stop.stderr)
    _assert_no_closeout_side_effects(consumer, sid)
    owner_state = json.loads((consumer / own.AREA / "owner.json").read_text(encoding="utf-8"))
    assert owner_state["state"] == "OWNED"


def test_stop_rejects_policy_created_after_prepare(tmp_path, framework_src):
    """Absent at Prepare -> created as audit before Stop must fail closed."""
    consumer = _make_consumer(tmp_path, framework_src, initial_policy=None)
    sid = "session-254-absent-to-audit"
    _start_codex_session(consumer, sid)

    prep = _prepare_candidate(consumer, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr
    prep_report = json.loads(prep.stdout)
    cand = json.loads((consumer / prep_report["candidate_identity"]["relative_path"]).read_text(encoding="utf-8"))
    assert cand["gate_policy_binding"] == {
        "relative_path": "governance/gate_policy.yaml",
        "present": False,
        "sha256": None,
    }

    (consumer / "governance" / "gate_policy.yaml").write_text(
        AUDIT_POLICY, encoding="utf-8", newline="\n"
    )

    stop = _run_codex_stop(consumer, sid)
    assert stop.returncode != 0
    assert "GATE_POLICY_BINDING_DRIFT" in (stop.stdout + stop.stderr)
    _assert_no_closeout_side_effects(consumer, sid)


def test_stop_rejects_policy_deleted_after_prepare(tmp_path, framework_src):
    """Present at Prepare -> deleted before Stop must fail closed."""
    consumer = _make_consumer(tmp_path, framework_src, initial_policy=STRICT_POLICY)
    sid = "session-254-present-to-absent"
    _start_codex_session(consumer, sid)

    prep = _prepare_candidate(consumer, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr

    (consumer / "governance" / "gate_policy.yaml").unlink()

    stop = _run_codex_stop(consumer, sid)
    assert stop.returncode != 0
    assert "GATE_POLICY_BINDING_DRIFT" in (stop.stdout + stop.stderr)
    _assert_no_closeout_side_effects(consumer, sid)


def test_deferred_handoff_rejects_post_prepare_policy_drift(tmp_path, framework_src):
    """Deferred handoff must also reject strict -> audit drift before writing request."""
    consumer = _make_consumer(tmp_path, framework_src, initial_policy=STRICT_POLICY)
    sid = "session-254-handoff-drift"
    _start_codex_session(consumer, sid)

    prep = _prepare_candidate(consumer, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr

    (consumer / "governance" / "gate_policy.yaml").write_text(
        AUDIT_POLICY, encoding="utf-8", newline="\n"
    )

    rejected = _publish_fixture_handoff(consumer, sid)
    assert rejected.returncode != 0
    assert "GATE_POLICY_DRIFT" in (rejected.stdout + rejected.stderr)
    assert not (consumer / "artifacts" / "runtime" / "closeout-requests" / sid / "request.json").exists()
    _assert_no_closeout_side_effects(consumer, sid)


def test_stop_and_handoff_reject_missing_gate_policy_binding_and_recover_on_reprepare(
    tmp_path, framework_src
):
    """Submodule consumer candidate with framework_binding but missing gate_policy_binding fails closed."""
    consumer = _make_consumer(tmp_path, framework_src, initial_policy=STRICT_POLICY)
    sid = "session-254-missing-policy-binding"
    _start_codex_session(consumer, sid)

    # First run Prepare to obtain a valid framework_binding, then craft a candidate omitting gate_policy_binding
    prep = _prepare_candidate(consumer, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr
    prep_report = json.loads(prep.stdout)
    orig = json.loads((consumer / prep_report["candidate_identity"]["relative_path"]).read_text(encoding="utf-8"))
    legacy_candidate = {k: v for k, v in orig.items() if k != "gate_policy_binding"}
    data = (json.dumps(legacy_candidate, indent=2) + "\n").encode("utf-8")
    rel = f"artifacts/runtime/closeout_candidates/{sid}/99999999T000000000000Z.json"
    text = (consumer / own.TEXT).read_bytes()
    ci = {"relative_path": rel, "sha256": hashlib.sha256(data).hexdigest()}
    with own.execution_exclusion(consumer) as lease:
        rec = own.acquire_owner(lease, sid, ci, hashlib.sha256(text).hexdigest())
        p = consumer / rel
        p.write_bytes(data)
        own.confirm_prepared(lease, sid, rec["generation"])

    stop = _run_codex_stop(consumer, sid)
    assert stop.returncode != 0
    assert "GATE_POLICY_BINDING_MISSING" in (stop.stdout + stop.stderr)
    _assert_no_closeout_side_effects(consumer, sid)

    rejected = _publish_fixture_handoff(consumer, sid)
    assert rejected.returncode != 0
    assert "GATE_POLICY_BINDING_MISSING" in (rejected.stdout + rejected.stderr)

    # Re-running Prepare restores gate_policy_binding and allows handoff/closeout
    # Remove synthetic 99999999 filename so newer timestamp ordering holds
    (consumer / rel).unlink()
    reprep = _prepare_candidate(consumer, sid)
    assert reprep.returncode == 0, reprep.stdout + reprep.stderr
    recovered = _publish_fixture_handoff(consumer, sid)
    assert recovered.returncode == 0, recovered.stderr
    assert json.loads(recovered.stdout)["status"] == "REQUESTED"


def test_unchanged_strict_policy_preserves_gate_blocked_and_reprepare_allows_legitimate_update(
    tmp_path, framework_src
):
    """Positive paths: unchanged strict stays gate_blocked=True; re-Prepare after audit update succeeds."""
    consumer = _make_consumer(tmp_path, framework_src, initial_policy=STRICT_POLICY)
    sid1 = "session-254-unchanged-strict"
    _start_codex_session(consumer, sid1)
    assert _prepare_candidate(consumer, sid1).returncode == 0
    stop1 = _run_codex_stop(consumer, sid1)
    assert stop1.returncode == 0, stop1.stderr
    receipts = sorted((consumer / "artifacts" / "runtime" / "closeout-receipts").glob("*.json"))
    assert len(receipts) == 1
    r1 = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert r1["hook_outcome"]["gate_blocked"] is True
    assert r1["hook_outcome"]["ok"] is False

    # Now legitimately update policy to audit, re-Prepare in a new session, and confirm Stop succeeds
    (consumer / "governance" / "gate_policy.yaml").write_text(AUDIT_POLICY, encoding="utf-8")
    sid2 = "session-254-legit-audit"
    _start_codex_session(consumer, sid2)
    assert _prepare_candidate(consumer, sid2).returncode == 0
    stop2 = _run_codex_stop(consumer, sid2)
    assert stop2.returncode == 0, stop2.stderr
    receipts2 = sorted((consumer / "artifacts" / "runtime" / "closeout-receipts").glob("*.json"))
    assert len(receipts2) == 2
    r2 = json.loads(receipts2[-1].read_text(encoding="utf-8"))
    assert r2["hook_outcome"]["gate_blocked"] is False
    assert r2["hook_outcome"]["ok"] is True


def test_gate_policy_binding_rejects_directory_as_policy_file(tmp_path):
    """A directory at governance/gate_policy.yaml must fail closed on all platforms."""
    consumer = (tmp_path / "consumer").resolve()
    (consumer / "governance" / "gate_policy.yaml").mkdir(parents=True)
    with pytest.raises(preparation.PreparationError, match="regular file"):
        preparation.gate_policy_binding_identity(consumer)


def test_gate_policy_binding_rejects_symlink_escape(tmp_path):
    """Symlinked gate_policy.yaml must fail closed."""
    outside = tmp_path / "outside.yaml"
    outside.write_text(AUDIT_POLICY, encoding="utf-8")
    consumer = (tmp_path / "consumer").resolve()
    (consumer / "governance").mkdir(parents=True)
    link = consumer / "governance" / "gate_policy.yaml"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation requires elevated privilege on this host: {exc}")

    with pytest.raises((own.OwnershipError, preparation.PreparationError)):
        preparation.gate_policy_binding_identity(consumer)
