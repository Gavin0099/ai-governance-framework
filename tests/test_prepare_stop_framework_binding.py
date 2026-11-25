"""Regression tests for Issue #360: Prepare-to-Stop framework binding symmetry.

Verifies that in submodule consumers:
1. Prepare records the verified framework binding inside the R2-hashed candidate JSON
   without mutating the owner.json schema.
2. Native Stop re-verifies the active framework binding against the Prepare-recorded
   binding BEFORE begin_closeout, memory writes, receipt emission, or R2 RELEASED.
3. Mid-session drift (Sample 004 repro: Prepare on locked v1, Stop after checking out v2)
   fails closed with zero closeout side effects.
4. Even if Stop is internally three-way consistent at v2 (new consumer commit updating
   gitlink + checkout + framework.lock.json after Prepare on v1), Stop still fails closed
   because v2 != v1.
5. Submodule consumers reject prepared candidates that omit framework_binding.
6. Unprepared Stop turns (even during mid-upgrade mismatch), legitimate consumer upgrades
   committed before Prepare, and self-hosted framework closeouts continue to work.
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

from governance_tools import shared_closeout_ownership as own

FRAMEWORK = Path(__file__).resolve().parents[1]
SUBMODULE = "ai-governance-framework"


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
def framework_versions(tmp_path_factory):
    """Create a local git repo with two clean framework commits (v1 and v2)."""
    src = tmp_path_factory.mktemp("fw-issue360-src")
    _git(src, "init", "--quiet")
    for rel_dir in ("governance_tools", "runtime_hooks", "memory_pipeline", "governance", "schemas"):
        shutil.copytree(FRAMEWORK / rel_dir, src / rel_dir)
    for rel_file in ("AGENTS.md", "AGENTS.base.md", "PLAN.md", "contract.yaml"):
        if (FRAMEWORK / rel_file).is_file():
            shutil.copyfile(FRAMEWORK / rel_file, src / rel_file)
    (src / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    _git(src, "add", ".")
    _git(src, "commit", "-qm", "framework v1")
    v1 = _git(src, "rev-parse", "HEAD")

    (src / "governance" / "V2_MARKER.md").write_text("# v2\n", encoding="utf-8")
    _git(src, "add", "governance/V2_MARKER.md")
    _git(src, "commit", "-qm", "framework v2")
    v2 = _git(src, "rev-parse", "HEAD")
    return {"repo": src, "v1": v1, "v2": v2}


@pytest.fixture
def consumer_repo(tmp_path, framework_versions):
    """Create a committed submodule consumer pinned to framework v1."""
    root = (tmp_path / "consumer").resolve()
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(
        root, "-c", "protocol.file.allow=always",
        "submodule", "add", "--quiet", str(framework_versions["repo"]), SUBMODULE,
    )
    _git(root / SUBMODULE, "checkout", "--quiet", framework_versions["v1"])
    (root / "AGENTS.md").write_text("# consumer\n", encoding="utf-8")
    (root / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (root / "governance").mkdir()
    (root / "governance" / "framework.lock.json").write_text(
        json.dumps({"adopted_commit": framework_versions["v1"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "memory").mkdir()
    (root / "evidence.txt").write_text("ok\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "pin consumer to framework v1")
    return root


def _start_codex_session(root: Path, sid: str = "session-360") -> None:
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


def _prepare_candidate(root: Path, sid: str = "session-360") -> subprocess.CompletedProcess:
    fw = root / SUBMODULE
    payload = {
        "task_intent": "Verify framework binding symmetry",
        "work_summary": "Checked evidence.txt under locked framework.",
        "tools_used": ["pytest evidence.txt"],
        "artifacts_referenced": ["evidence.txt"],
        "open_risks": [],
        "checks_run": "pytest evidence.txt",
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


def _run_codex_stop(root: Path, sid: str = "session-360") -> subprocess.CompletedProcess:
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


def _assert_no_closeout_side_effects(root: Path, sid: str) -> None:
    assert not (root / "artifacts" / "runtime" / "closeouts" / f"{sid}.json").exists()
    assert not (root / "artifacts" / "runtime" / "closeout-completions" / f"{sid}.json").exists()
    receipts_dir = root / "artifacts" / "runtime" / "closeout-receipts"
    assert not receipts_dir.exists() or not list(receipts_dir.glob("*.json"))
    releases_dir = root / "artifacts" / "runtime" / "shared-closeout" / "releases"
    assert not releases_dir.exists() or not list(releases_dir.glob("*.json"))
    assert not list((root / "memory").glob("*.md"))


def test_sample004_repro_stop_rejects_checkout_drift_before_side_effects(
    consumer_repo, framework_versions
):
    _start_codex_session(consumer_repo, "session-s004")
    prep = _prepare_candidate(consumer_repo, "session-s004")
    assert prep.returncode == 0, prep.stdout + prep.stderr
    prep_report = json.loads(prep.stdout)
    cand_path = consumer_repo / prep_report["candidate_identity"]["relative_path"]
    cand_json = json.loads(cand_path.read_text(encoding="utf-8"))
    assert cand_json.get("framework_binding", {}).get("checkout_head") == framework_versions["v1"]

    # Simulate Sample 004: agent switches submodule checkout to v2 after Prepare succeeded on v1
    _git(consumer_repo / SUBMODULE, "checkout", "--quiet", framework_versions["v2"])

    stop = _run_codex_stop(consumer_repo, "session-s004")
    assert stop.returncode != 0
    _assert_no_closeout_side_effects(consumer_repo, "session-s004")
    owner_state = json.loads(
        (consumer_repo / own.AREA / "owner.json").read_text(encoding="utf-8")
    )
    assert owner_state["state"] == "OWNED"


def test_stop_rejects_when_both_stages_consistent_but_at_different_versions(
    consumer_repo, framework_versions
):
    _start_codex_session(consumer_repo, "session-v1-to-v2")
    prep = _prepare_candidate(consumer_repo, "session-v1-to-v2")
    assert prep.returncode == 0, prep.stdout + prep.stderr

    # Commit a full three-way consistent consumer upgrade to v2 AFTER Prepare ran on v1
    _git(consumer_repo / SUBMODULE, "checkout", "--quiet", framework_versions["v2"])
    (consumer_repo / "governance" / "framework.lock.json").write_text(
        json.dumps({"adopted_commit": framework_versions["v2"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    _git(consumer_repo, "add", SUBMODULE, "governance/framework.lock.json")
    _git(consumer_repo, "commit", "-qm", "post-prepare upgrade to v2")

    stop = _run_codex_stop(consumer_repo, "session-v1-to-v2")
    assert stop.returncode != 0
    _assert_no_closeout_side_effects(consumer_repo, "session-v1-to-v2")
    owner_state = json.loads(
        (consumer_repo / own.AREA / "owner.json").read_text(encoding="utf-8")
    )
    assert owner_state["state"] == "OWNED"


def test_stop_rejects_submodule_consumer_candidate_missing_framework_binding(consumer_repo):
    sid = "session-missing-binding"
    _start_codex_session(consumer_repo, sid)
    candidate = {
        "session_id": sid,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_intent": "Manual candidate without framework_binding",
        "work_summary": "Attempt closeout without framework_binding",
        "tools_used": ["pytest evidence.txt"],
        "artifacts_referenced": ["evidence.txt"],
        "open_risks": [],
    }
    data = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    rel = f"artifacts/runtime/closeout_candidates/{sid}/20261124T080000000000Z.json"
    text = (
        "TASK_INTENT: Manual candidate without framework_binding\n"
        "WORK_COMPLETED: Attempt closeout without framework_binding\n"
        "FILES_TOUCHED: evidence.txt\n"
        "CHECKS_RUN: pytest evidence.txt\n"
        "OPEN_RISKS: NONE\n"
        "NOT_DONE: NONE\n"
        "RECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n"
    ).encode("utf-8")
    ci = {"relative_path": rel, "sha256": hashlib.sha256(data).hexdigest()}
    with own.execution_exclusion(consumer_repo) as lease:
        rec = own.acquire_owner(lease, sid, ci, hashlib.sha256(text).hexdigest())
        p = consumer_repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        (consumer_repo / own.TEXT).write_bytes(text)
        own.confirm_prepared(lease, sid, rec["generation"])

    stop = _run_codex_stop(consumer_repo, sid)
    assert stop.returncode != 0
    _assert_no_closeout_side_effects(consumer_repo, sid)


def test_unprepared_mid_upgrade_stop_skips_cleanly_and_committed_upgrade_succeeds(
    consumer_repo, framework_versions
):
    sid = "session-upgrade"
    _start_codex_session(consumer_repo, sid)

    # Mid-upgrade turn: submodule moved to v2 while lock is still v1, no candidate prepared yet
    _git(consumer_repo / SUBMODULE, "checkout", "--quiet", framework_versions["v2"])
    mid_stop = _run_codex_stop(consumer_repo, sid)
    assert mid_stop.returncode == 0, mid_stop.stderr
    assert mid_stop.stdout == ""
    _assert_no_closeout_side_effects(consumer_repo, sid)

    # Complete legitimate upgrade commit (gitlink + lock aligned at v2), then Prepare + Stop
    (consumer_repo / "governance" / "framework.lock.json").write_text(
        json.dumps({"adopted_commit": framework_versions["v2"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    _git(consumer_repo, "add", SUBMODULE, "governance/framework.lock.json")
    _git(consumer_repo, "commit", "-qm", "upgrade consumer to framework v2")

    prep = _prepare_candidate(consumer_repo, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr
    final_stop = _run_codex_stop(consumer_repo, sid)
    assert final_stop.returncode == 0, final_stop.stderr
    owner_state = json.loads(
        (consumer_repo / own.AREA / "owner.json").read_text(encoding="utf-8")
    )
    assert owner_state["state"] == "RELEASED"



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


def test_deferred_handoff_rejects_missing_framework_binding_and_recovers_after_reprepare(
    consumer_repo,
):
    sid = "session-handoff-missing-binding"
    _start_codex_session(consumer_repo, sid)
    candidate = {
        "session_id": sid,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_intent": "Legacy pre-#360 candidate without framework_binding",
        "work_summary": "Prepared before framework_binding existed.",
        "tools_used": ["pytest evidence.txt"],
        "artifacts_referenced": ["evidence.txt"],
        "open_risks": [],
    }
    data = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    rel = f"artifacts/runtime/closeout_candidates/{sid}/20261124T080000000000Z.json"
    text = (
        "TASK_INTENT: Legacy pre-#360 candidate without framework_binding\n"
        "WORK_COMPLETED: Prepared before framework_binding existed.\n"
        "FILES_TOUCHED: evidence.txt\n"
        "CHECKS_RUN: pytest evidence.txt\n"
        "OPEN_RISKS: NONE\n"
        "NOT_DONE: NONE\n"
        "RECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n"
    ).encode("utf-8")
    ci = {"relative_path": rel, "sha256": hashlib.sha256(data).hexdigest()}
    with own.execution_exclusion(consumer_repo) as lease:
        rec = own.acquire_owner(lease, sid, ci, hashlib.sha256(text).hexdigest())
        p = consumer_repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        (consumer_repo / own.TEXT).write_bytes(text)
        own.confirm_prepared(lease, sid, rec["generation"])

    rejected = _publish_fixture_handoff(consumer_repo, sid)
    assert rejected.returncode != 0
    assert "FRAMEWORK_BINDING_MISSING" in rejected.stderr
    assert not (consumer_repo / "artifacts" / "runtime" / "closeout-requests" / sid / "request.json").exists()
    _assert_no_closeout_side_effects(consumer_repo, sid)

    # Legal recovery path: re-run prepare_closeout_candidate under aligned framework
    reprep = _prepare_candidate(consumer_repo, sid)
    assert reprep.returncode == 0, reprep.stdout + reprep.stderr
    recovered = _publish_fixture_handoff(consumer_repo, sid)
    assert recovered.returncode == 0, recovered.stderr
    assert json.loads(recovered.stdout)["status"] == "REQUESTED"


def test_deferred_handoff_rejects_post_prepare_three_way_version_switch(
    consumer_repo, framework_versions
):
    sid = "session-handoff-v1-to-v2"
    _start_codex_session(consumer_repo, sid)
    prep = _prepare_candidate(consumer_repo, sid)
    assert prep.returncode == 0, prep.stdout + prep.stderr

    # Commit a full three-way consistent consumer upgrade to v2 AFTER Prepare ran on v1
    _git(consumer_repo / SUBMODULE, "checkout", "--quiet", framework_versions["v2"])
    (consumer_repo / "governance" / "framework.lock.json").write_text(
        json.dumps({"adopted_commit": framework_versions["v2"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    _git(consumer_repo, "add", SUBMODULE, "governance/framework.lock.json")
    _git(consumer_repo, "commit", "-qm", "post-prepare upgrade to v2 for handoff")

    rejected = _publish_fixture_handoff(consumer_repo, sid)
    assert rejected.returncode != 0
    assert "FRAMEWORK_DRIFT" in rejected.stderr
    assert not (consumer_repo / "artifacts" / "runtime" / "closeout-requests" / sid / "request.json").exists()
    _assert_no_closeout_side_effects(consumer_repo, sid)
