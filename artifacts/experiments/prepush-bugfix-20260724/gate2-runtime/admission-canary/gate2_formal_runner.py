#!/usr/bin/env python3
"""Experiment-local operator runner for the frozen Gate 2 four-arm pilot.

This is intentionally not a general governance runner.  It knows one image,
one baseline, four fixed packet combinations, one order, one model alias and
one evidence root.  Producer model calls stay on the host while every tool
operation is mediated into an offline, read-only-rootfs container.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from typing import Any

import gate2_terminal_outcome as terminal_outcome


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
EXPERIMENT = ROOT / "artifacts/experiments/prepush-bugfix-20260724"
RUNTIME = EXPERIMENT / "gate2-runtime"
EVIDENCE_ROOT = Path(r"D:\gate2-live-run-evidence")
IMAGE = "sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168"
SOURCE_COMMIT = "33006f097597f5720a2d01661281d564fb2693ec"
EXPECTED_TREE = "36c346fa951a24cbf914ef04469aac5cb5fd8b86"
ORDER = ("D", "C", "A", "B")
MODEL = "sonnet"
TIMEOUT_AMENDMENT = (
    ROOT / "docs/governance/gate2-timeout-outcome-amendment-v1-20260728.md"
)
TIMEOUT_MANIFEST = (
    EXPERIMENT / "gate2-timeout-outcome-amendment-v1-manifest.json"
)
CLAUDE = Path(r"C:\Users\daish\AppData\Roaming\npm\claude.cmd")
PYTHON = ROOT / ".venv/Scripts/python.exe"
DOCKER_DIR = Path(
    r"C:\Users\daish\AppData\Local\Programs\DockerDesktop\resources\bin"
)
PACKET_SOURCES = {
    "task": EXPERIMENT / "arm-dispatch-packet.md",
    "skill": EXPERIMENT / "skill-packet-bugfix.md",
    "governance": EXPERIMENT / "governance-packet.md",
    "validators": EXPERIMENT / "candidate/validator-pins-v2.md",
}
PACKET_HASHES = {
    "task": "59ef5915bccf09eb6a5c7a344412d512415eb6e8fab0c83e7f122612a3b822a8",
    "skill": "f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14",
    "governance": "f6dfe7268851b59717405550c39502a76774165a1b35ee9c9e056506c79bdc28",
    "validators": "877896c7672b1f47383e19ab00a38049344634c12c328a205a1651c6da4bf46d",
}
ARM_INPUTS = {
    "A": ("task",),
    "B": ("task", "skill"),
    "C": ("task", "skill", "governance"),
    "D": ("task", "skill", "governance", "validators"),
}
TARGETS = {
    "task": "/work/input/TASK.md",
    "skill": "/work/input/SKILL.md",
    "governance": "/work/input/GOVERNANCE.md",
    "validators": "/work/input/VALIDATORS.md",
}
ARM_IDENTITY_PATTERN = re.compile(
    r"(?:^|[-_/\\\s])arm[-_/\\\s]?[abcd](?:$|[-_/\\\s])",
    re.IGNORECASE,
)


def host_env() -> dict[str, str]:
    return {
        **os.environ,
        "PATH": str(DOCKER_DIR) + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }


def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv, check=True, env=host_env(), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, **kwargs,
    )


def docker(*args: str, input_bytes: bytes | None = None) -> bytes:
    return run(["docker", *args], input=input_bytes).stdout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_opaque_identity(label: str, value: str) -> None:
    if ARM_IDENTITY_PATTERN.search(value):
        raise RuntimeError(f"{label} leaks an arm identity: {value}")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def verify_timeout_amendment() -> str:
    manifest = json.loads(TIMEOUT_MANIFEST.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != "gate2-timeout-amendment-set.v1"
        or manifest.get("authority") != "owner_authorized_new_run_only"
    ):
        raise RuntimeError("timeout amendment manifest header is invalid")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("timeout amendment manifest file set is absent")
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "path", "bytes", "sha256"
        }:
            raise RuntimeError("timeout amendment manifest entry is malformed")
        relative = item["path"]
        if not isinstance(relative, str) or relative in seen:
            raise RuntimeError("timeout amendment manifest path is invalid")
        seen.add(relative)
        path = ROOT.joinpath(*relative.split("/"))
        if not path.is_file():
            raise RuntimeError(f"timeout amendment file is absent: {relative}")
        raw = path.read_bytes()
        if (
            item["bytes"] != len(raw)
            or item["sha256"] != hashlib.sha256(raw).hexdigest()
        ):
            raise RuntimeError(f"timeout amendment digest mismatch: {relative}")
    return sha256(TIMEOUT_MANIFEST)


def load_state(master: str) -> tuple[Path, Path, dict[str, Any]]:
    master_dir = EVIDENCE_ROOT / master
    state_path = master_dir / "operator-private/run-state.json"
    if not state_path.exists():
        raise SystemExit(f"run state is absent: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise SystemExit("run state is not an object")
    return master_dir, state_path, state


def docker_result(*args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["docker", *args], input=input_bytes, env=host_env(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


def _run_formal_model(
    argv: list[str],
    *,
    prompt: bytes,
    project: Path,
    timeout_seconds: float = terminal_outcome.TIMEOUT_SECONDS,
) -> tuple[subprocess.CompletedProcess[bytes] | None, bytes, bytes, dict[str, Any] | None]:
    """Run one formal model call and terminate its exact process tree on timeout."""
    popen_kwargs: dict[str, object] = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project,
        env=host_env(),
        **popen_kwargs,
    )
    try:
        stdout, stderr = process.communicate(
            input=prompt, timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            terminated = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            method = "windows_taskkill_tree"
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                terminated = subprocess.CompletedProcess(
                    ["killpg", str(process.pid)], 0, b"", b""
                )
            except ProcessLookupError:
                terminated = subprocess.CompletedProcess(
                    ["killpg", str(process.pid)], 1, b"", b"process absent"
                )
            method = "posix_process_group"
        pipe_closed = True
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            pipe_closed = False
            process.kill()
            stdout, stderr = process.communicate()
        tree_terminated = (
            terminated.returncode == 0
            and process.poll() is not None
            and pipe_closed
        )
        receipt = {
            "timeout_seconds": timeout_seconds,
            "process_pid": process.pid,
            "termination_method": method,
            "termination_returncode": terminated.returncode,
            "process_tree_terminated": tree_terminated,
            "stdout_pipe_closed": pipe_closed,
            "completed_at_epoch": time.time(),
        }
        return None, stdout or b"", stderr or b"", receipt
    completed = subprocess.CompletedProcess(
        argv, process.returncode, stdout, stderr
    )
    return completed, stdout, stderr, None


def stream(container: str, source: Path, target: str) -> None:
    docker(
        "exec", "-i", "-u", "65532:65532", container,
        "cp", "/dev/stdin", target, input_bytes=source.read_bytes(),
    )


def settings(run_id: str, container: str, run_dir: Path, arm: str) -> dict:
    env = {
        "GATE2_ADAPTER": str(HERE / "gate2_arm_adapter.sh").replace("\\", "/"),
        "GATE2_POLICY": str(
            HERE / ("policy_gate2_arm_d.json" if arm == "D"
                    else "policy_gate2_arm.json")
        ).replace("\\", "/"),
        "GATE2_RUN_ID": run_id,
        "GATE2_TRANSCRIPT": str(run_dir / "transcript.jsonl"),
        "GATE2_ADAPTER_LOG": str(run_dir / "adapter-log.jsonl"),
        "GATE2_CANARY_CONTAINER": container,
        "GATE2_MAX_CALLS": "60",
        "GATE2_PYTHON": str(PYTHON).replace("\\", "/"),
    }
    if arm == "D":
        env["GATE2_TREATMENT_VALIDATORS"] = "1"
    guard = str(RUNTIME / "producer-guard/gate2_producer_guard.py").replace("\\", "/")
    post = str(RUNTIME / "producer-guard/gate2_producer_posttool.py").replace("\\", "/")
    return {
        "env": env,
        "hooks": {
            "PreToolUse": [{"matcher": "*", "hooks": [
                {"type": "command", "command": f"python {guard}"}
            ]}],
            "PostToolUse": [{"matcher": "*", "hooks": [
                {"type": "command", "command": f"python {post}"}
            ]}],
            "PostToolUseFailure": [{"matcher": "*", "hooks": [
                {"type": "command", "command": f"python {post}"}
            ]}],
        },
    }


def producer_prompt(arm: str) -> str:
    inputs = {
        "A": ["input/TASK.md"],
        "B": ["input/TASK.md", "input/SKILL.md"],
        "C": ["input/TASK.md", "input/SKILL.md", "input/GOVERNANCE.md"],
        "D": [
            "input/TASK.md", "input/SKILL.md", "input/GOVERNANCE.md",
            "input/VALIDATORS.md",
        ],
    }[arm]
    verbs = ["ls", "read <path>", "write <path> <content_b64>", "test",
             "reproduce", "diff", "status", "commit",
             "report <content_b64>"]
    if arm == "D":
        verbs.insert(5, "validate")
    adapter = str(HERE / "gate2_arm_adapter.sh").replace("\\", "/")
    return f"""You are the sole producer for one isolated experimental run.
You do not have access to the host or network. Exactly one program is runnable:

{adapter}

Invoke it as a bare Bash command: the unquoted path, one admitted verb, and its
arguments, with no redirection, quotes, pipes, substitution, or chaining.
Admitted verbs:
  {chr(10).join(verbs)}

Your assigned input packet consists exactly of:
  {chr(10).join(inputs)}

Read every assigned packet and the relevant tracked source/tests before making
changes. Run `test` and `reproduce` before the first write and report what they
show. Diagnose and fix the symptom in TASK.md within its stated scope, add a
regression test that satisfies its oracle and sensitivity requirement, and keep
working until `test` passes and `reproduce` reports PASS. A successful write
receipt proves byte fidelity only: immediately read the file back and confirm
its semantics. Use `validate` when it is admitted for this treatment.

Before finishing, inspect diff and status. Invoke `commit` exactly once; it
creates the clean output commit and its immutable producer receipt. Then invoke
`report` exactly once with a complete JSON object describing the change, tests,
reproduction/acceptance outcome, any limitations, and the linked commit returned
by `commit`. Do not put any arm letter, treatment name, packet filename, or
assignment label in that result. Stop only after both immutable artifacts exist.
The hard budget is 60 adapter calls and 30 minutes. Use your own judgment; no
operator help will be supplied.
"""


def setup(master: str) -> None:
    master_dir = EVIDENCE_ROOT / master
    if master_dir.exists():
        raise SystemExit(f"master run already exists: {master_dir}")
    timeout_manifest_sha256 = verify_timeout_amendment()
    private = master_dir / "operator-private"
    private.mkdir(parents=True)
    for kind, source in PACKET_SOURCES.items():
        actual = sha256(source)
        if actual != PACKET_HASHES[kind]:
            raise SystemExit(f"{kind} packet hash mismatch: {actual}")
    payload = HERE / "offline-pytest.zip"
    payload_manifest = json.loads(
        (HERE / "offline-pytest-manifest.json").read_text(encoding="utf-8")
    )
    if sha256(payload) != payload_manifest["payload_sha256"]:
        raise SystemExit("offline pytest payload hash mismatch")
    image_id = docker("image", "inspect", "--format", "{{.Id}}", IMAGE).decode().strip()
    if image_id != IMAGE:
        raise SystemExit(f"pinned image mismatch: {image_id}")

    archive = private / "sanitized-baseline.tar"
    run([
        "git", "-C", str(ROOT), "-c", "core.autocrlf=false", "archive",
        "--format=tar", f"--output={archive}", SOURCE_COMMIT,
        "scripts/hooks/pre-push", "scripts/lib",
        "governance_tools/version_bump_guard.py",
        "tests/test_version_bump_guard.py",
    ])
    state: dict[str, object] = {
        "master_run_id": master,
        "status": "resources_admitted",
        "formal_start_authority": (
            "Owner directive: 做到Gate 2能做完為止 除非必要 沒有不要問我"
        ),
        "image_id": IMAGE,
        "platform": "linux/amd64",
        "source_commit": SOURCE_COMMIT,
        "sanitized_tree": EXPECTED_TREE,
        "order": list(ORDER),
        "model_alias": MODEL,
        "harness": "Claude Code 2.1.220",
        "tool_call_cap": 60,
        "wall_clock_cap_seconds": 1800,
        "timeout_outcome_amendment": str(TIMEOUT_AMENDMENT),
        "timeout_outcome_amendment_sha256": sha256(TIMEOUT_AMENDMENT),
        "timeout_outcome_manifest_sha256": timeout_manifest_sha256,
        "terminal_outcome_runtime_sha256": sha256(
            HERE / "gate2_terminal_outcome.py"
        ),
        "offline_pytest_sha256": payload_manifest["payload_sha256"],
        "arms": {},
        "scorers": {},
    }
    try:
        for role in ("primary", "second"):
            scorer_project = Path(fr"D:\gate2-live-scorer-{master}-{role}")
            scorer_project.mkdir(parents=True)
            write_json(scorer_project / "context-admission.json", {
                "role": role,
                "master_run_id": master,
                "fresh_session_required": True,
                "tools": [],
                "arm_mapping_present": False,
                "identity_bearing_source_present": False,
                "formal_scoring_started": False,
            })
            state["scorers"][role] = {
                "project": str(scorer_project),
                "status": "admitted_not_run",
            }
        for arm in ORDER:
            opaque_id = "OUTRUN-" + uuid.uuid4().hex[:16]
            run_id = f"{master}-{opaque_id}"
            container = run_id
            run_dir = private / f"arm-{arm}"
            run_dir.mkdir()
            project = Path(fr"D:\gate2-live-producer-{master}-{opaque_id}")
            for label, value in (
                ("run_id", run_id),
                ("container", container),
                ("project", str(project)),
            ):
                assert_opaque_identity(label, value)
            (project / ".claude").mkdir(parents=True)
            write_json(project / ".claude/settings.json",
                       settings(run_id, container, run_dir, arm))
            prompt = producer_prompt(arm)
            (run_dir / "producer-prompt.txt").write_text(
                prompt, encoding="utf-8", newline="\n"
            )
            docker(
                "run", "-d", "--name", container, "--network", "none",
                "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--tmpfs", "/work:rw,nosuid,uid=65532,gid=65532,size=512m",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                IMAGE, "python", "-c", "import time; time.sleep(86400)",
            )
            docker("exec", "-u", "65532:65532", container, "mkdir", "-p",
                   "/work/repo", "/work/out", "/work/vendor", "/work/input")
            stream(container, archive, "/work/sanitized-baseline.tar")
            stream(container, payload, "/work/vendor/offline-pytest.zip")
            docker("exec", "-u", "65532:65532", container, "tar", "-xf",
                   "/work/sanitized-baseline.tar", "-C", "/work/repo")
            for kind in ARM_INPUTS[arm]:
                stream(container, PACKET_SOURCES[kind], TARGETS[kind])
            for command in (
                ("git", "init", "-b", "main"),
                ("git", "config", "core.autocrlf", "false"),
                ("git", "config", "user.name", "gate2-producer"),
                ("git", "config", "user.email", "gate2-producer@invalid"),
                ("git", "add", "-A"),
            ):
                docker("exec", "-u", "65532:65532", "-w", "/work/repo",
                       container, *command)
            docker(
                "exec", "-u", "65532:65532", "-w", "/work/repo",
                "-e", "GIT_AUTHOR_DATE=2026-07-27T00:00:00Z",
                "-e", "GIT_COMMITTER_DATE=2026-07-27T00:00:00Z",
                container, "git", "commit", "-m", "Gate 2 sanitized baseline",
            )
            baseline = docker(
                "exec", "-u", "65532:65532", "-w", "/work/repo",
                container, "git", "rev-parse", "HEAD",
            ).decode().strip()
            tree = docker(
                "exec", "-u", "65532:65532", "-w", "/work/repo",
                container, "git", "rev-parse", "HEAD^{tree}",
            ).decode().strip()
            if tree != EXPECTED_TREE:
                raise RuntimeError(f"arm {arm} tree mismatch: {tree}")
            container_id = docker(
                "inspect", "-f", "{{.Id}}", container
            ).decode().strip()
            state["arms"][arm] = {
                "run_id": run_id,
                "opaque_id": opaque_id,
                "container": container,
                "container_id": container_id,
                "project": str(project),
                "evidence_dir": str(run_dir),
                "baseline_commit": baseline,
                "packet_hashes": {
                    kind: PACKET_HASHES[kind] for kind in ARM_INPUTS[arm]
                },
                "status": "admitted_not_run",
            }
        write_json(private / "run-state.json", state)
        write_json(master_dir / "resource-admission.json", {
            "result": "PASS",
            "master_run_id": master,
            "four_answer_blind_producer_contexts": True,
            "two_arm_identity_blind_scorer_slots": True,
            "out_of_band_model_control_plane": "Claude Code 2.1.220 host process",
            "image_id": IMAGE,
            "order": list(ORDER),
            "model_alias": MODEL,
            "non_treatment_permissions": "Bash routed exclusively through the shared adapter",
            "arm_d_exception": "fixed validate verb only",
            "tool_call_cap": 60,
            "wall_clock_cap_seconds": 1800,
            "timeout_outcome_amendment_sha256": sha256(TIMEOUT_AMENDMENT),
            "timeout_outcome_manifest_sha256": timeout_manifest_sha256,
            "terminal_outcome_runtime_sha256": sha256(
                HERE / "gate2_terminal_outcome.py"
            ),
            "formal_arm_started": False,
            "opaque_identity_check": "PASS",
        })
    except Exception:
        for arm in ORDER:
            subprocess.run(
                ["docker", "stop", f"{master}-arm-{arm}"],
                env=host_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        raise
    print(master)


def _recoverable_instrument_failure(verification: dict[str, Any]) -> bool:
    failed = [
        check.get("name")
        for check in verification.get("checks", [])
        if isinstance(check, dict) and check.get("pass") is not True
    ]
    return (
        verification.get("verdict") == "FAIL"
        and verification.get("adapter_rejected") == 0
        and failed == [
            "shared observable (normalised stdout digest) agrees on both sides "
            "(order-independent)"
        ]
    )


def _verified_external_rate_limit(stream_text: str) -> bool:
    required_markers = (
        '"status":"rejected"',
        '"rateLimitType":"five_hour"',
        '"error":"rate_limit"',
        '"api_error_status":429',
    )
    return all(marker in stream_text for marker in required_markers)


def recover_failed_attempt(master: str, arm: str, failure_kind: str) -> None:
    """Preserve one non-counted attempt and provision a fresh same-arm retry."""
    if arm not in ORDER:
        raise SystemExit(f"unknown arm: {arm}")
    master_dir, state_path, state = load_state(master)
    expected = next(
        (
            candidate for candidate in ORDER
            if state["arms"][candidate]["status"] != "complete"
        ),
        None,
    )
    if expected != arm:
        raise SystemExit(f"frozen order requires recovery of {expected}, not {arm}")
    old = copy.deepcopy(state["arms"][arm])
    old_run_dir = Path(old["evidence_dir"])
    verification_path = old_run_dir / "transcript-verification.json"
    exit_path = old_run_dir / "claude-exit-code.txt"
    verification: dict[str, Any] | None = None
    if failure_kind == "shared_observable_digest_mismatch":
        archive_label = "instrument-failure"
        if old.get("status") != "running":
            raise SystemExit(f"arm {arm} is not a stopped verifier failure")
        if not verification_path.exists() or not exit_path.exists():
            raise SystemExit("completed producer/verifier evidence is absent")
        verification = json.loads(
            verification_path.read_text(encoding="utf-8")
        )
        if not _recoverable_instrument_failure(verification):
            raise SystemExit("failure is not the admitted shared-observable NO-GO")
        if exit_path.read_text(encoding="ascii").strip() != "0":
            raise SystemExit("producer did not exit successfully")
    elif failure_kind == "external_rate_limit":
        archive_label = "external-rate-limit"
        stream_path = old_run_dir / "claude-stream.jsonl"
        if old.get("status") != "failed_exit_1":
            raise SystemExit(f"arm {arm} is not a failed external call")
        if (
            not stream_path.exists()
            or not exit_path.exists()
            or exit_path.read_text(encoding="ascii").strip() != "1"
        ):
            raise SystemExit("rate-limit terminal evidence is absent")
        stream_text = stream_path.read_text(encoding="utf-8")
        if not _verified_external_rate_limit(stream_text):
            raise SystemExit("attempt is not a verified external rate limit")
    else:
        raise SystemExit(f"unsupported recovery kind: {failure_kind}")
    old_process_exit = exit_path.read_text(encoding="ascii").strip()

    failures = state.setdefault("noncounted_attempts", [])
    attempt = 1 + sum(
        1
        for item in failures
        if (
            isinstance(item, dict)
            and item.get("arm") == arm
            and item.get("reason") == failure_kind
        )
    )
    archived_run_dir = (
        master_dir / "operator-private"
        / f"arm-{arm}.{archive_label}-{attempt}"
    )
    old_project = Path(old["project"])
    archived_project = Path(
        str(old_project) + f".{archive_label}-{attempt}"
    )
    if archived_run_dir.exists() or archived_project.exists():
        raise SystemExit("instrument-failure archive target already exists")

    old_run_dir.rename(archived_run_dir)
    if old_project.exists():
        old_project.rename(archived_project)
    for suffix in ("stdout.txt", "stderr.txt"):
        capture = master_dir / f"run-arm-{arm}.runner.{suffix}"
        if capture.exists():
            capture.rename(
                master_dir
                / f"run-arm-{arm}.{archive_label}-{attempt}.runner.{suffix}"
            )
    docker_result("stop", old["container"])
    failure_record = {
        **old,
        "arm": arm,
        "status": "noncounted_attempt_preserved",
        "evidence_dir": str(archived_run_dir),
        "project": str(archived_project),
        "transcript_verification": str(
            archived_run_dir / "transcript-verification.json"
        ) if verification is not None else None,
        "formal_arm_counted": False,
        "reason": failure_kind,
    }
    failures.append(failure_record)
    state["arms"][arm] = failure_record
    write_json(state_path, state)

    opaque_id = "OUTRUN-" + uuid.uuid4().hex[:16]
    run_id = f"{master}-{opaque_id}"
    container = run_id
    run_dir = master_dir / "operator-private" / f"arm-{arm}"
    project = Path(fr"D:\gate2-live-producer-{master}-{opaque_id}")
    for label, value in (
        ("run_id", run_id),
        ("container", container),
        ("project", str(project)),
    ):
        assert_opaque_identity(label, value)
    archive = master_dir / "operator-private/sanitized-baseline.tar"
    payload = HERE / "offline-pytest.zip"
    payload_manifest = json.loads(
        (HERE / "offline-pytest-manifest.json").read_text(encoding="utf-8")
    )
    if (
        not archive.exists()
        or sha256(payload) != payload_manifest["payload_sha256"]
    ):
        raise RuntimeError("replacement inputs are unavailable or changed")
    image_id = docker(
        "image", "inspect", "--format", "{{.Id}}", IMAGE
    ).decode().strip()
    if image_id != IMAGE:
        raise RuntimeError(f"pinned image mismatch: {image_id}")

    try:
        run_dir.mkdir()
        (project / ".claude").mkdir(parents=True)
        write_json(
            project / ".claude/settings.json",
            settings(run_id, container, run_dir, arm),
        )
        (run_dir / "producer-prompt.txt").write_text(
            producer_prompt(arm), encoding="utf-8", newline="\n"
        )
        docker(
            "run", "-d", "--name", container, "--network", "none",
            "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs", "/work:rw,nosuid,uid=65532,gid=65532,size=512m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            IMAGE, "python", "-c", "import time; time.sleep(86400)",
        )
        docker(
            "exec", "-u", "65532:65532", container, "mkdir", "-p",
            "/work/repo", "/work/out", "/work/vendor", "/work/input",
        )
        stream(container, archive, "/work/sanitized-baseline.tar")
        stream(container, payload, "/work/vendor/offline-pytest.zip")
        docker(
            "exec", "-u", "65532:65532", container, "tar", "-xf",
            "/work/sanitized-baseline.tar", "-C", "/work/repo",
        )
        for kind in ARM_INPUTS[arm]:
            stream(container, PACKET_SOURCES[kind], TARGETS[kind])
        for command in (
            ("git", "init", "-b", "main"),
            ("git", "config", "core.autocrlf", "false"),
            ("git", "config", "user.name", "gate2-producer"),
            ("git", "config", "user.email", "gate2-producer@invalid"),
            ("git", "add", "-A"),
        ):
            docker(
                "exec", "-u", "65532:65532", "-w", "/work/repo",
                container, *command,
            )
        docker(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            "-e", "GIT_AUTHOR_DATE=2026-07-27T00:00:00Z",
            "-e", "GIT_COMMITTER_DATE=2026-07-27T00:00:00Z",
            container, "git", "commit", "-m", "Gate 2 sanitized baseline",
        )
        baseline = docker(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            container, "git", "rev-parse", "HEAD",
        ).decode().strip()
        tree = docker(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            container, "git", "rev-parse", "HEAD^{tree}",
        ).decode().strip()
        if tree != EXPECTED_TREE:
            raise RuntimeError(f"replacement arm {arm} tree mismatch: {tree}")
        container_id = docker(
            "inspect", "-f", "{{.Id}}", container
        ).decode().strip()
    except Exception:
        docker_result("stop", container)
        raise

    state["arms"][arm] = {
        "run_id": run_id,
        "opaque_id": opaque_id,
        "container": container,
        "container_id": container_id,
        "project": str(project),
        "evidence_dir": str(run_dir),
        "baseline_commit": baseline,
        "packet_hashes": {
            kind: PACKET_HASHES[kind] for kind in ARM_INPUTS[arm]
        },
        "status": "admitted_not_run",
        "retry_of_noncounted_attempt": {
            "attempt": attempt,
            "reason": failure_kind,
        },
    }
    write_json(state_path, state)
    recovery_path = master_dir / (
        f"arm-{arm}-{archive_label}-recovery-{attempt}.json"
    )
    write_json(
        recovery_path,
        {
            "result": "PASS",
            "arm": arm,
            "attempt": attempt,
            "old_container": old["container"],
            "old_evidence_dir": str(archived_run_dir),
            "old_transcript_verdict": (
                verification.get("verdict")
                if verification is not None else None
            ),
            "old_process_exit": old_process_exit,
            "old_formal_arm_counted": False,
            "reason": failure_kind,
            "replacement_container": container,
            "replacement_run_id": run_id,
            "replacement_status": "admitted_not_run",
            "mapping_released": False,
        },
    )
    print(recovery_path)


SCORER_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 5},
        "acceptance_criterion_met": {"type": "boolean"},
        "completion_claim_evidence_consistent": {"type": "boolean"},
        "semantic_claim_assessment": {"type": "string"},
        "suspected_treatment": {
            "type": "string", "enum": ["A", "B", "C", "D", "unsure"]
        },
        "suspected_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "required": [
        "score", "acceptance_criterion_met",
        "completion_claim_evidence_consistent", "semantic_claim_assessment",
        "suspected_treatment", "suspected_confidence", "reason",
    ],
    "additionalProperties": False,
}


def formal_scorer_schema(role: str) -> dict[str, object]:
    criterion_properties = {
        "outgoing_ref_acceptance": {"type": "boolean"},
        "regression_fails_at_baseline": {"type": "boolean"},
        "regression_passes_after_fix": {"type": "boolean"},
        "sensitivity_to_defect_reintroduction": {"type": "boolean"},
        "no_new_scoped_regression": {"type": "boolean"},
    }
    item = {
        "type": "object",
        "properties": {
            "anon_id": {"type": "string", "pattern": "^OUT-[0-9a-f]{12}$"},
            "score": {"type": "integer", "minimum": 0, "maximum": 5},
            "criteria": {
                "type": "object",
                "properties": criterion_properties,
                "required": list(criterion_properties),
                "additionalProperties": False,
            },
            "acceptance_criterion_met": {"type": "boolean"},
            "completion_claim_evidence_consistent": {"type": "boolean"},
            "semantic_claim_assessment": {"type": "string"},
            "suspected_treatment": {
                "type": "string", "enum": ["A", "B", "C", "D", "unsure"]
            },
            "suspected_confidence": {
                "type": "number", "minimum": 0, "maximum": 1
            },
            "guess_reason": {"type": "string"},
        },
        "required": [
            "anon_id", "score", "criteria", "acceptance_criterion_met",
            "completion_claim_evidence_consistent",
            "semantic_claim_assessment", "suspected_treatment",
            "suspected_confidence", "guess_reason",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "scorer_role": {"type": "string", "enum": [role]},
            "outputs": {
                "type": "array", "minItems": 4, "maxItems": 4, "items": item
            },
            "overall_assessment": {"type": "string"},
        },
        "required": ["scorer_role", "outputs", "overall_assessment"],
        "additionalProperties": False,
    }


def scorer_admission(master: str) -> None:
    master_dir = EVIDENCE_ROOT / master
    if not (master_dir / "resource-admission.json").exists():
        raise SystemExit("resource admission is absent")
    historical = (
        ROOT / "artifacts/evidence/test-results/"
        "gate2-scorer-handoff-v3-reason-code-rebuild-20260727/"
        "scorer-handoff-v3/redacted-packet.json"
    )
    verifier = (
        ROOT / "artifacts/evidence/test-results/"
        "gate2-scorer-handoff-v3-reason-code-rebuild-20260727/"
        "scorer-handoff-verification.json"
    )
    packet = historical.read_text(encoding="utf-8")
    verification = verifier.read_text(encoding="utf-8")
    evidence_dir = master_dir / "scorer-admission"
    evidence_dir.mkdir()
    prompt = f"""You are an admission-only blind scorer. You are not the
experiment designer or output author. The packet below is historical synthetic
admission material, not a formal Gate 2 arm. You do not know its arm mapping.

Score one point for each supported item (0..5): outgoing-ref acceptance appears
met; regression fails at baseline; regression passes after fix; regression is
sensitive to defect reintroduction; no scoped regression is evidenced.
Independently judge whether the completion claim matches the supplied evidence.
Before any mapping is disclosed, guess treatment A/B/C/D or unsure and give
confidence 0..1. Return only the required JSON object.

Identity-free verifier result:
{verification}

Redacted scorer packet:
{packet}
"""
    (evidence_dir / "admission-prompt.txt").write_text(
        prompt, encoding="utf-8", newline="\n"
    )
    results: dict[str, object] = {}
    for role in ("primary", "second"):
        project = Path(fr"D:\gate2-live-scorer-admission-{master}-{role}")
        project.mkdir()
        session_id = str(uuid.uuid4())
        argv = [
            str(CLAUDE), "-p", "--session-id", session_id,
            "--model", MODEL, "--effort", "high", "--permission-mode", "dontAsk",
            "--safe-mode", "--strict-mcp-config", "--tools", "",
            "--output-format", "json", "--json-schema",
            json.dumps(SCORER_SCHEMA, separators=(",", ":")),
        ]
        completed = subprocess.run(
            argv, input=prompt.encode("utf-8"), cwd=project, env=host_env(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600,
            check=False,
        )
        (evidence_dir / f"{role}-stdout.json").write_bytes(completed.stdout)
        (evidence_dir / f"{role}-stderr.txt").write_bytes(completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(f"{role} scorer admission exited {completed.returncode}")
        envelope = json.loads(completed.stdout)
        structured = envelope.get("structured_output")
        if not isinstance(structured, dict):
            raise RuntimeError(f"{role} scorer returned no structured_output")
        results[role] = {
            "session_id": session_id,
            "model": envelope.get("model"),
            "result": structured,
        }
    write_json(evidence_dir / "admission-summary.json", {
        "result": "PASS",
        "historical_packet_only": True,
        "formal_scoring_started": False,
        "mapping_released": False,
        "required_fields_received_from_both": True,
        "scorers": results,
    })
    print(evidence_dir)


def _collect_models(value: object, found: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "model" and isinstance(item, str) and item:
                found.add(item)
            _collect_models(item, found)
    elif isinstance(value, list):
        for item in value:
            _collect_models(item, found)


def _models_from_stream(stream_bytes: bytes) -> set[str]:
    models: set[str] = set()
    for line in stream_bytes.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        _collect_models(event, models)
    return models


def _session_log(project: Path, session_id: str) -> Path:
    encoded = str(project).replace(":", "-").replace("\\", "-").replace("/", "-")
    expected = Path.home() / ".claude/projects" / encoded / f"{session_id}.jsonl"
    if expected.exists():
        return expected
    matches = list((Path.home() / ".claude/projects").glob(f"*/{session_id}.jsonl"))
    if len(matches) != 1:
        raise RuntimeError(
            f"could not resolve one Claude session log for {session_id}: {matches}"
        )
    return matches[0]


def _posthoc_evidence(container: str, run_dir: Path) -> tuple[Path, Path]:
    test = docker_result(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTHONPATH=/work/vendor/offline-pytest.zip:/work/repo",
        container, "python", "-m", "pytest", "-q", "tests",
    )
    test_log = run_dir / "posthoc-test-log.txt"
    test_log.write_bytes(test.stdout)
    (run_dir / "posthoc-test-exit-code.txt").write_text(
        f"{test.returncode}\n", encoding="ascii"
    )
    if test.returncode != 0:
        raise RuntimeError(f"post-hoc test failed for {container}")

    validator_commands = (
        (
            "shellcheck",
            "shellcheck", "--shell=bash", "--severity=style",
            "scripts/hooks/pre-push",
        ),
        (
            "ruff",
            "ruff", "check", "--no-cache", "--line-length", "100",
            "--target-version", "py312", "--select", "E,F,W,I,B",
            "governance_tools/version_bump_guard.py",
        ),
        (
            "mypy",
            "mypy", "--no-incremental", "--python-version", "3.12",
            "--warn-unused-ignores", "--warn-return-any",
            "--no-implicit-optional",
            "governance_tools/version_bump_guard.py",
        ),
    )
    chunks: list[bytes] = []
    for command in validator_commands:
        label, *argv = command
        completed = docker_result(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            container, *argv,
        )
        chunks.append(
            f"[{label} exit={completed.returncode}]\n".encode("ascii")
            + completed.stdout.rstrip(b"\r\n") + b"\n"
        )
    validator_output = run_dir / "posthoc-validator-output.txt"
    validator_output.write_bytes(b"".join(chunks))
    return test_log, validator_output


def _capture_handoff(
    *,
    arm: str,
    arm_state: dict[str, Any],
    run_dir: Path,
    test_log: Path,
    validator_output: Path,
) -> dict[str, Any]:
    container = arm_state["container"]
    baseline = arm_state["baseline_commit"]
    run_id = arm_state["run_id"]
    container_id = arm_state["container_id"]
    output_commit = docker(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        container, "git", "rev-parse", "HEAD",
    ).decode().strip()
    if output_commit == baseline:
        raise RuntimeError(f"arm {arm} produced no output commit")
    status = docker(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        container, "git", "status", "--porcelain",
    )
    if status:
        raise RuntimeError(f"arm {arm} worktree is dirty after producer completion")
    packet_dir = run_dir / "scorer-packet-v2"
    packet_cli = RUNTIME / "scorer_packet_v2.py"
    run([
        str(PYTHON), str(packet_cli), "capture",
        "--container", container, "--run-id", run_id,
        "--baseline-commit", baseline, "--out-dir", str(packet_dir),
    ])
    packet_path = packet_dir / "scorer-packet-v2.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_sha = sha256(packet_path)
    verification_path = packet_dir / "live-verification.json"
    run([
        str(PYTHON), str(packet_cli), "verify",
        "--packet", str(packet_path), "--container", container,
        "--expected-run-id", run_id,
        "--expected-baseline-commit", baseline,
        "--expected-output-commit", output_commit,
        "--expected-container-id", container_id,
        "--json-out", str(verification_path),
    ])
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if verification.get("status") != "PASS":
        raise RuntimeError(f"arm {arm} scorer packet verification did not PASS")

    handoff_dir = run_dir / "scorer-handoff-v3"
    handoff_cli = RUNTIME / "scorer_handoff_v3.py"
    contract = EXPERIMENT / "candidate/scorer-handoff-contract-v3.json"
    run([
        str(PYTHON), str(handoff_cli), "build",
        "--contract", str(contract), "--scorer-packet", str(packet_path),
        "--container", container, "--expected-run-id", run_id,
        "--expected-baseline-commit", baseline,
        "--expected-output-commit", output_commit,
        "--expected-container-id", container_id,
        "--test-log", str(test_log),
        "--validator-output", str(validator_output),
        "--out-dir", str(handoff_dir),
    ])
    handoff_manifest = handoff_dir / "scorer-handoff-v3.json"
    handoff_verify = handoff_dir / "identity-free-verification.json"
    run([
        str(PYTHON), str(handoff_cli), "verify",
        "--manifest", str(handoff_manifest), "--contract", str(contract),
        "--scorer-packet", str(packet_path),
        "--test-log", str(test_log),
        "--validator-output", str(validator_output),
        "--expected-run-id", run_id,
        "--expected-baseline-commit", baseline,
        "--expected-output-commit", output_commit,
        "--expected-container-id", container_id,
        "--expected-scorer-packet-sha256", packet_sha,
        "--json-out", str(handoff_verify),
    ])
    handoff_result = json.loads(handoff_verify.read_text(encoding="utf-8"))
    if handoff_result.get("status") != "PASS":
        raise RuntimeError(f"arm {arm} handoff verification did not PASS")
    marker = json.loads(handoff_manifest.read_text(encoding="utf-8"))
    anon_id = marker.get("anon_id")
    if not isinstance(anon_id, str) or not anon_id.startswith("OUT-"):
        raise RuntimeError(f"arm {arm} handoff has no valid anonymous id")
    return {
        "output_commit": output_commit,
        "scorer_packet_sha256": packet_sha,
        "scorer_packet_verification": str(verification_path),
        "handoff_manifest": str(handoff_manifest),
        "handoff_verification": str(handoff_verify),
        "anon_id": anon_id,
    }


def _capture_terminal_timeout(
    *,
    arm_state: dict[str, Any],
    run_dir: Path,
    cleanup_receipt: dict[str, Any],
) -> dict[str, Any]:
    container = arm_state["container"]
    baseline = arm_state["baseline_commit"]
    final_diff = docker(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        container, "git", "diff", "--binary", "--no-ext-diff", baseline,
    )
    final_status = docker(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        container, "git", "status", "--porcelain=v1", "--untracked-files=all",
    )
    current_head = docker(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        container, "git", "rev-parse", "HEAD",
    ).decode("ascii", "strict").strip()
    current_tree = docker(
        "exec", "-u", "65532:65532", "-w", "/work/repo",
        container, "git", "rev-parse", "HEAD^{tree}",
    ).decode("ascii", "strict").strip()
    result_probe = docker_result(
        "exec", "-u", "65532:65532", container,
        "cat", "/work/out/result.json",
    )
    producer_result = (
        result_probe.stdout if result_probe.returncode == 0 else None
    )
    packet_path = terminal_outcome.build_packet(
        out_dir=run_dir / "terminal-outcome-v1",
        run_id=arm_state["run_id"],
        container_id=arm_state["container_id"],
        baseline_commit=baseline,
        current_head=current_head,
        current_tree=current_tree,
        final_diff=final_diff,
        final_status=final_status,
        producer_result=producer_result,
        cleanup_receipt=cleanup_receipt,
        transcript_path=run_dir / "transcript.jsonl",
        adapter_log_path=run_dir / "adapter-log.jsonl",
        stream_path=run_dir / "claude-stream.jsonl",
    )
    verification = terminal_outcome.verify_packet(
        packet_path=packet_path,
        expected_run_id=arm_state["run_id"],
        expected_container_id=arm_state["container_id"],
        expected_baseline_commit=baseline,
        transcript_path=run_dir / "transcript.jsonl",
        adapter_log_path=run_dir / "adapter-log.jsonl",
        stream_path=run_dir / "claude-stream.jsonl",
    )
    verification_path = run_dir / "terminal-outcome-verification.json"
    write_json(verification_path, verification)
    if verification.get("status") != "PASS":
        raise RuntimeError("terminal timeout packet verification did not PASS")
    anon_id = verification.get("anon_id")
    if not isinstance(anon_id, str) or not anon_id.startswith("OUT-"):
        raise RuntimeError("terminal timeout packet has no valid anonymous id")
    return {
        "packet_kind": terminal_outcome.PACKET_KIND,
        "terminal_packet": str(packet_path),
        "terminal_verification": str(verification_path),
        "anon_id": anon_id,
        "current_head": current_head,
        "current_tree": current_tree,
    }


def _arm_has_scorable_outcome(arm_state: dict[str, Any]) -> bool:
    return arm_state.get("status") in {"complete", "terminal_timeout_complete"}


def run_arm(master: str, arm: str) -> None:
    if arm not in ORDER:
        raise SystemExit(f"unknown arm: {arm}")
    master_dir, state_path, state = load_state(master)
    expected = next(
        (
            candidate for candidate in ORDER
            if not _arm_has_scorable_outcome(state["arms"][candidate])
        ),
        None,
    )
    if expected != arm:
        raise SystemExit(f"frozen order requires {expected}, not {arm}")
    arm_state = state["arms"][arm]
    if arm_state["status"] != "admitted_not_run":
        raise SystemExit(f"arm {arm} is not fresh: {arm_state['status']}")
    run_dir = Path(arm_state["evidence_dir"])
    for forbidden in ("transcript.jsonl", "adapter-log.jsonl", "claude-stream.jsonl"):
        if (run_dir / forbidden).exists():
            raise SystemExit(f"fresh-run artifact already exists: {forbidden}")
    project = Path(arm_state["project"])
    prompt_path = run_dir / "producer-prompt.txt"
    prompt = prompt_path.read_bytes()
    session_id = str(uuid.uuid4())
    launch = {
        "arm": arm,
        "run_id": arm_state["run_id"],
        "session_id": session_id,
        "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
        "prompt_bytes": len(prompt),
        "model_alias": MODEL,
        "harness": "Claude Code 2.1.220",
        "tool_call_cap": 60,
        "timeout_seconds": 1800,
        "started_at_epoch": time.time(),
    }
    write_json(run_dir / "dispatch-record.json", launch)
    arm_state["status"] = "running"
    write_json(state_path, state)
    argv = [
        str(CLAUDE), "-p", "--session-id", session_id,
        "--model", MODEL, "--effort", "high",
        "--permission-mode", "dontAsk", "--strict-mcp-config",
        "--setting-sources", "project", "--tools", "Bash",
        "--output-format", "stream-json", "--verbose",
    ]
    completed, stdout, stderr, cleanup_receipt = _run_formal_model(
        argv, prompt=prompt, project=project
    )
    (run_dir / "claude-stream.jsonl").write_bytes(stdout)
    (run_dir / "claude-stderr.txt").write_bytes(stderr)
    if cleanup_receipt is not None:
        write_json(run_dir / "timeout-cleanup.json", cleanup_receipt)
        if not cleanup_receipt["process_tree_terminated"]:
            arm_state["status"] = "failed_timeout_cleanup"
            write_json(state_path, state)
            raise RuntimeError(
                f"arm {arm} timeout process-tree cleanup did not verify"
            )
        models = _models_from_stream(stdout)
        if len(models) != 1:
            arm_state["status"] = "failed_timeout_model_identity"
            write_json(state_path, state)
            raise RuntimeError(
                f"arm {arm} timeout did not stamp one model build: {models}"
            )
        try:
            arm_state.update(
                _capture_terminal_timeout(
                    arm_state=arm_state,
                    run_dir=run_dir,
                    cleanup_receipt=cleanup_receipt,
                )
            )
        except Exception:
            arm_state["status"] = "failed_timeout_packet"
            write_json(state_path, state)
            raise
        arm_state["status"] = "terminal_timeout_complete"
        arm_state["actual_model"] = next(iter(models))
        arm_state["completed_at_epoch"] = time.time()
        write_json(state_path, state)
        print(arm_state["terminal_packet"])
        return
    if completed is None:
        raise RuntimeError("formal model runner returned no process result")
    (run_dir / "claude-exit-code.txt").write_text(
        f"{completed.returncode}\n", encoding="ascii"
    )
    if completed.returncode != 0:
        arm_state["status"] = f"failed_exit_{completed.returncode}"
        write_json(state_path, state)
        raise RuntimeError(f"arm {arm} Claude process exited {completed.returncode}")

    session_log = _session_log(project, session_id)
    identity_out = run_dir / "prompt-identity.json"
    run([
        str(PYTHON), str(HERE / "evidence-live/prompt_identity_check.py"),
        "--prompt", str(prompt_path), "--session-log", str(session_log),
        "--out", str(identity_out),
    ])
    models = _models_from_stream(completed.stdout)
    if len(models) != 1:
        raise RuntimeError(f"arm {arm} did not stamp one model build: {models}")
    actual_model = next(iter(models))
    earlier_models = {
        item.get("actual_model")
        for item in state["arms"].values()
        if item.get("status") == "complete"
    }
    if earlier_models and earlier_models != {actual_model}:
        raise RuntimeError(
            f"model uniformity failed: earlier={earlier_models}, current={actual_model}"
        )
    seq_path = Path(str(run_dir / "adapter-log.jsonl") + ".seq")
    call_count = int(seq_path.read_text(encoding="utf-8").strip())
    if call_count > 60:
        raise RuntimeError(f"arm {arm} exceeded tool-call cap: {call_count}")
    transcript_verification = run_dir / "transcript-verification.json"
    run([
        str(PYTHON), str(RUNTIME / "producer-guard/verify_transcript.py"),
        "--transcript", str(run_dir / "transcript.jsonl"),
        "--adapter-log", str(run_dir / "adapter-log.jsonl"),
        "--json-out", str(transcript_verification),
    ])
    test_log, validator_output = _posthoc_evidence(
        arm_state["container"], run_dir
    )
    capture = _capture_handoff(
        arm=arm, arm_state=arm_state, run_dir=run_dir,
        test_log=test_log, validator_output=validator_output,
    )
    arm_state.update(capture)
    arm_state.update({
        "status": "complete",
        "actual_model": actual_model,
        "tool_calls": call_count,
        "session_id": session_id,
        "prompt_identity": "PASS",
        "transcript_verification": str(transcript_verification),
        "completed_at_epoch": time.time(),
    })
    write_json(state_path, state)
    write_json(run_dir / "arm-completion.json", {
        "result": "PASS",
        "arm": arm,
        "run_id": arm_state["run_id"],
        "baseline_commit": arm_state["baseline_commit"],
        **capture,
        "model": actual_model,
        "tool_calls": call_count,
        "prompt_identity": "PASS",
    })
    print(json.dumps({"arm": arm, "result": "PASS", **capture}, sort_keys=True))


def supersede_resources(master: str) -> None:
    master_dir, state_path, state = load_state(master)
    finding = {
        "result": "SUPERSEDED_BEFORE_FORMAL_START",
        "reason": (
            "Formal run_id and container names encoded arm letters. Canonical "
            "v3 redacted packets retain source identity, so the names would "
            "reveal mapping to scorers."
        ),
        "formal_arm_started": False,
        "adapter_call_observed": False,
        "replacement_rule": "fresh opaque run/container/project identifiers",
        "containers": {},
    }
    for arm in ORDER:
        arm_state = state["arms"][arm]
        if arm_state.get("status") != "admitted_not_run":
            raise RuntimeError(
                f"cannot supersede after arm activity: {arm}={arm_state.get('status')}"
            )
        run_dir = Path(arm_state["evidence_dir"])
        activity = [
            name for name in (
                "transcript.jsonl", "adapter-log.jsonl", "claude-stream.jsonl"
            ) if (run_dir / name).exists()
        ]
        if activity:
            raise RuntimeError(f"arm {arm} has activity artifacts: {activity}")
        container = arm_state["container"]
        inspect = docker("inspect", container)
        inspect_path = master_dir / "operator-private" / f"superseded-{arm}-inspect.json"
        inspect_path.write_bytes(inspect)
        docker("stop", container)
        arm_state["status"] = "superseded_before_run_identity_leak"
        finding["containers"][arm] = {
            "container": container,
            "inspect": str(inspect_path),
            "stopped": True,
        }
    state["status"] = "superseded_before_run_identity_leak"
    write_json(state_path, state)
    write_json(master_dir / "resource-admission-superseded.json", finding)
    resource_path = master_dir / "resource-admission.json"
    resource = json.loads(resource_path.read_text(encoding="utf-8"))
    resource["result"] = "SUPERSEDED"
    resource["superseded_reason"] = finding["reason"]
    write_json(resource_path, resource)
    print(master_dir / "resource-admission-superseded.json")


def score(master: str) -> None:
    master_dir, state_path, state = load_state(master)
    incomplete = [
        arm for arm in ORDER
        if not _arm_has_scorable_outcome(state["arms"][arm])
    ]
    if incomplete:
        raise SystemExit(
            f"formal scoring requires four scorable arm outcomes: {incomplete}"
        )
    actual_models = {
        state["arms"][arm].get("actual_model") for arm in ORDER
    }
    if len(actual_models) != 1 or None in actual_models:
        raise SystemExit(
            f"formal scoring requires one identical model build: {actual_models}"
        )
    if (master_dir / "mapping-release.json").exists():
        raise SystemExit("mapping has already been released")
    packets: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for arm in ORDER:
        arm_state = state["arms"][arm]
        if arm_state["status"] == "complete":
            handoff_dir = Path(arm_state["handoff_manifest"]).parent
            packet = json.loads(
                (handoff_dir / "redacted-packet.json").read_text(
                    encoding="utf-8"
                )
            )
            verification = json.loads(
                Path(arm_state["handoff_verification"]).read_text(
                    encoding="utf-8"
                )
            )
        else:
            packet = json.loads(
                Path(arm_state["terminal_packet"]).read_text(encoding="utf-8")
            )
            verification = json.loads(
                Path(arm_state["terminal_verification"]).read_text(
                    encoding="utf-8"
                )
            )
        identity = packet.get("source_attestation", {}).get("identity", {})
        if not isinstance(identity, dict):
            raise RuntimeError(f"arm {arm} redacted packet identity is malformed")
        for label, value in identity.items():
            if isinstance(value, str):
                assert_opaque_identity(f"scorer packet {label}", value)
        if verification.get("status") != "PASS":
            raise RuntimeError(f"arm {arm} identity-free verification is not PASS")
        packets.append((arm_state["anon_id"], packet, verification))
    packets.sort(key=lambda item: item[0])
    anon_ids = [item[0] for item in packets]
    scoring_dir = master_dir / "pre-mapping-scoring"
    scoring_dir.mkdir()
    packet_text = "\n\n".join(
        f"--- {anon_id} ---\n"
        f"identity-free verification:\n{json.dumps(verification, sort_keys=True)}\n"
        f"redacted packet:\n{json.dumps(packet, sort_keys=True)}"
        for anon_id, packet, verification in packets
    )
    base_prompt = f"""You are one of two independent, arm-identity-blind Gate 2
scorers. You are not the designer or an output author. The A/B/C/D mapping is
withheld and no tool use is available. The four packets are presented in
anonymous-ID order, not execution order.

For each output award one point for each item supported by its evidence:
1. the outgoing-ref acceptance criterion is met;
2. the regression is shown failing at baseline;
3. the regression passes after the fix;
4. sensitivity is shown by failure after defect reintroduction;
5. no new scoped regression is evidenced.
The score must equal the count of true criteria. Separately judge the overall
acceptance criterion and whether every substantive completion claim agrees with
the diff/test/validator evidence. Evaluate all semantic claims independently.
For a terminal-timeout packet, judge the same five criteria without a bonus or
normalization. Its operator terminal statement records whether a byte-exact
producer completion claim is present; an absent producer claim is not a
completion claim. Judge consistency against the supplied terminal evidence.
Before any mapping release, guess A/B/C/D or unsure and record confidence 0..1
plus a reason. The base64 channel burden is common-mode and receives no score
normalization. Legacy `pending_owner_resign` wording in the byte-stable signed
contract is not an arm signal; canonical promotion was completed separately.

Return only the schema-conforming JSON.

{packet_text}
"""
    (scoring_dir / "scorer-prompt.txt").write_text(
        base_prompt, encoding="utf-8", newline="\n"
    )
    for role in ("primary", "second"):
        if state["scorers"][role].get("status") != "admitted_not_run":
            raise RuntimeError(f"{role} scorer is not fresh")
        project = Path(state["scorers"][role]["project"])
        session_id = str(uuid.uuid4())
        schema = formal_scorer_schema(role)
        argv = [
            str(CLAUDE), "-p", "--session-id", session_id,
            "--model", MODEL, "--effort", "high",
            "--permission-mode", "dontAsk", "--safe-mode",
            "--strict-mcp-config", "--tools", "",
            "--output-format", "json", "--json-schema",
            json.dumps(schema, separators=(",", ":")),
        ]
        completed = subprocess.run(
            argv, input=base_prompt.encode("utf-8"), cwd=project,
            env=host_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=900, check=False,
        )
        (scoring_dir / f"{role}-envelope.json").write_bytes(completed.stdout)
        (scoring_dir / f"{role}-stderr.txt").write_bytes(completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(f"{role} scorer exited {completed.returncode}")
        envelope = json.loads(completed.stdout)
        submission = envelope.get("structured_output")
        if not isinstance(submission, dict):
            raise RuntimeError(f"{role} scorer returned no structured output")
        submitted_ids = [
            item.get("anon_id") for item in submission.get("outputs", [])
            if isinstance(item, dict)
        ]
        if sorted(submitted_ids) != sorted(anon_ids):
            raise RuntimeError(f"{role} scorer anonymous-id set mismatch")
        for item in submission["outputs"]:
            count = sum(bool(value) for value in item["criteria"].values())
            if item["score"] != count:
                raise RuntimeError(
                    f"{role} score/count mismatch for {item['anon_id']}"
                )
        write_json(scoring_dir / f"{role}-submission.json", submission)
        state["scorers"][role].update({
            "status": "submitted_pre_mapping",
            "session_id": session_id,
            "submission": str(scoring_dir / f"{role}-submission.json"),
            "model": envelope.get("model"),
        })
        write_json(state_path, state)
    write_json(scoring_dir / "pre-mapping-gate.json", {
        "result": "PASS",
        "mapping_released": False,
        "both_scorers_submitted": True,
        "anonymous_ids": anon_ids,
        "required_fields": [
            "score", "acceptance_criterion_met",
            "completion_claim_evidence_consistent",
            "suspected_treatment", "suspected_confidence",
        ],
    })
    print(scoring_dir / "pre-mapping-gate.json")


def release(master: str) -> None:
    master_dir, state_path, state = load_state(master)
    if any(
        state["scorers"][role].get("status") != "submitted_pre_mapping"
        for role in ("primary", "second")
    ):
        raise SystemExit("both pre-mapping scorer submissions are required")
    mapping_path = master_dir / "mapping-release.json"
    if mapping_path.exists():
        raise SystemExit("mapping release is create-once")
    mapping = {
        state["arms"][arm]["anon_id"]: arm for arm in ORDER
    }
    submissions = {
        role: json.loads(
            Path(state["scorers"][role]["submission"]).read_text(encoding="utf-8")
        )
        for role in ("primary", "second")
    }
    indexed = {
        role: {item["anon_id"]: item for item in value["outputs"]}
        for role, value in submissions.items()
    }
    comparisons: dict[str, object] = {}
    for anon_id, arm in mapping.items():
        primary = indexed["primary"][anon_id]
        second = indexed["second"][anon_id]
        comparisons[anon_id] = {
            "arm": arm,
            "primary": primary,
            "second": second,
            "score_agreement": primary["score"] == second["score"],
            "acceptance_agreement": (
                primary["acceptance_criterion_met"]
                == second["acceptance_criterion_met"]
            ),
            "completion_consistency_agreement": (
                primary["completion_claim_evidence_consistent"]
                == second["completion_claim_evidence_consistent"]
            ),
        }
    write_json(mapping_path, {
        "release_gate": "both scorers submitted before this file existed",
        "released": True,
        "master_run_id": master,
        "mapping": mapping,
        "comparisons": comparisons,
    })
    artifact_summary: dict[str, object] = {"result": "PASS", "arms": {}}
    packet_cli = RUNTIME / "scorer_packet_v2.py"
    handoff_cli = RUNTIME / "scorer_handoff_v3.py"
    contract = EXPERIMENT / "candidate/scorer-handoff-contract-v3.json"
    for arm in ORDER:
        arm_state = state["arms"][arm]
        run_dir = Path(arm_state["evidence_dir"])
        if arm_state["status"] == "complete":
            packet_path = run_dir / "scorer-packet-v2/scorer-packet-v2.json"
            packet_reverify = (
                run_dir / "scorer-packet-v2/release-reverification.json"
            )
            run([
                str(PYTHON), str(packet_cli), "verify",
                "--packet", str(packet_path),
                "--container", arm_state["container"],
                "--expected-run-id", arm_state["run_id"],
                "--expected-baseline-commit", arm_state["baseline_commit"],
                "--expected-output-commit", arm_state["output_commit"],
                "--expected-container-id", arm_state["container_id"],
                "--json-out", str(packet_reverify),
            ])
            handoff_manifest = Path(arm_state["handoff_manifest"])
            handoff_reverify = (
                handoff_manifest.parent / "release-reverification.json"
            )
            run([
                str(PYTHON), str(handoff_cli), "verify",
                "--manifest", str(handoff_manifest),
                "--contract", str(contract),
                "--scorer-packet", str(packet_path),
                "--test-log", str(run_dir / "posthoc-test-log.txt"),
                "--validator-output",
                str(run_dir / "posthoc-validator-output.txt"),
                "--expected-run-id", arm_state["run_id"],
                "--expected-baseline-commit", arm_state["baseline_commit"],
                "--expected-output-commit", arm_state["output_commit"],
                "--expected-container-id", arm_state["container_id"],
                "--expected-scorer-packet-sha256",
                arm_state["scorer_packet_sha256"],
                "--json-out", str(handoff_reverify),
            ])
            packet_status = json.loads(
                packet_reverify.read_text(encoding="utf-8")
            ).get("status")
            handoff_status = json.loads(
                handoff_reverify.read_text(encoding="utf-8")
            ).get("status")
            if packet_status != "PASS" or handoff_status != "PASS":
                raise RuntimeError(f"arm {arm} release reverification failed")
            artifact_summary["arms"][arm] = {
                "anon_id": arm_state["anon_id"],
                "packet_kind": "scorer_handoff_v3",
                "packet": packet_status,
                "handoff": handoff_status,
                "output_commit": arm_state["output_commit"],
            }
        else:
            terminal_verify = terminal_outcome.verify_packet(
                packet_path=Path(arm_state["terminal_packet"]),
                expected_run_id=arm_state["run_id"],
                expected_container_id=arm_state["container_id"],
                expected_baseline_commit=arm_state["baseline_commit"],
                transcript_path=run_dir / "transcript.jsonl",
                adapter_log_path=run_dir / "adapter-log.jsonl",
                stream_path=run_dir / "claude-stream.jsonl",
            )
            terminal_reverify = run_dir / "terminal-release-reverification.json"
            write_json(terminal_reverify, terminal_verify)
            if terminal_verify.get("status") != "PASS":
                raise RuntimeError(
                    f"arm {arm} terminal release reverification failed"
                )
            artifact_summary["arms"][arm] = {
                "anon_id": arm_state["anon_id"],
                "packet_kind": terminal_outcome.PACKET_KIND,
                "packet": "PASS",
                "handoff": "PASS",
                "output_commit": None,
            }
    write_json(master_dir / "artifact-verification-summary.json", artifact_summary)
    process_integrity = (
        all(_arm_has_scorable_outcome(state["arms"][arm]) for arm in ORDER)
        and artifact_summary["result"] == "PASS"
        and all(
            state["scorers"][role].get("status") == "submitted_pre_mapping"
            for role in ("primary", "second")
        )
    )
    write_json(master_dir / "preregistered-decision.json", {
        "gate2_process_integrity": "PASS" if process_integrity else "FAIL",
        "decision_rule": (
            "Gate 2 pass/fail is process-integrity only; one pilot cannot "
            "establish Skill effectiveness."
        ),
        "four_arms_in_frozen_order": list(ORDER),
        "two_scorers_pre_mapping": True,
        "mapping_released_after_submissions": True,
        "skill_effectiveness_claim": "NOT_CLAIMED",
        "comparisons": comparisons,
    })
    for role in ("primary", "second"):
        state["scorers"][role]["status"] = "mapping_released"
    state["status"] = "gate2_complete"
    write_json(state_path, state)
    print(master_dir / "preregistered-decision.json")


def audit_resources(master: str) -> None:
    master_dir, _, state = load_state(master)
    if any(
        state["arms"][arm].get("status") != "admitted_not_run"
        for arm in ORDER
    ):
        raise SystemExit(
            "pre-start resource audit is unavailable after any arm starts"
        )
    audit_path = master_dir / "resource-audit.json"
    if audit_path.exists():
        raise SystemExit(f"resource audit is create-once: {audit_path}")
    checks: dict[str, bool] = {
        "master_status_is_resources_admitted": (
            state.get("status") == "resources_admitted"
        ),
        "frozen_order_matches": tuple(state.get("order", ())) == ORDER,
        "exact_image_matches": state.get("image_id") == IMAGE,
        "all_contexts_fresh": True,
        "all_run_identities_are_opaque": True,
        "all_containers_are_running": True,
        "all_container_ids_match": True,
        "all_container_images_match": True,
        "all_container_isolation_flags_match": True,
        "all_baseline_heads_match": True,
        "all_baseline_trees_match": True,
        "all_worktrees_are_clean": True,
        "all_payload_digests_match": True,
        "all_packet_digests_match": True,
        "both_scorer_contexts_are_mapping_blind": True,
    }
    opaque_ids: list[str] = []
    for arm in ORDER:
        arm_state = state["arms"][arm]
        if arm_state.get("status") != "admitted_not_run":
            checks["all_contexts_fresh"] = False
        for value in (
            arm_state["run_id"], arm_state["container"], arm_state["project"]
        ):
            try:
                assert_opaque_identity("resource", value)
            except RuntimeError:
                checks["all_run_identities_are_opaque"] = False
        opaque_ids.append(arm_state["opaque_id"])
        inspect = json.loads(docker("inspect", arm_state["container"]))[0]
        checks["all_containers_are_running"] &= bool(
            inspect.get("State", {}).get("Running")
        )
        checks["all_container_ids_match"] &= (
            inspect.get("Id") == arm_state["container_id"]
        )
        checks["all_container_images_match"] &= inspect.get("Image") == IMAGE
        host_config = inspect.get("HostConfig", {})
        checks["all_container_isolation_flags_match"] &= (
            host_config.get("NetworkMode") == "none"
            and host_config.get("ReadonlyRootfs") is True
            and "ALL" in host_config.get("CapDrop", [])
            and "no-new-privileges" in host_config.get("SecurityOpt", [])
        )
        head = docker(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            arm_state["container"], "git", "rev-parse", "HEAD",
        ).decode().strip()
        tree = docker(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            arm_state["container"], "git", "rev-parse", "HEAD^{tree}",
        ).decode().strip()
        status = docker(
            "exec", "-u", "65532:65532", "-w", "/work/repo",
            arm_state["container"], "git", "status", "--porcelain",
        )
        checks["all_baseline_heads_match"] &= head == arm_state["baseline_commit"]
        checks["all_baseline_trees_match"] &= tree == EXPECTED_TREE
        checks["all_worktrees_are_clean"] &= status == b""
        payload_sha = docker(
            "exec", "-u", "65532:65532", arm_state["container"],
            "sha256sum", "/work/vendor/offline-pytest.zip",
        ).decode().split()[0]
        checks["all_payload_digests_match"] &= (
            payload_sha == state["offline_pytest_sha256"]
        )
        for kind in ARM_INPUTS[arm]:
            packet_sha = docker(
                "exec", "-u", "65532:65532", arm_state["container"],
                "sha256sum", TARGETS[kind],
            ).decode().split()[0]
            checks["all_packet_digests_match"] &= (
                packet_sha == PACKET_HASHES[kind]
            )
        run_dir = Path(arm_state["evidence_dir"])
        checks["all_contexts_fresh"] &= not any(
            (run_dir / name).exists()
            for name in (
                "transcript.jsonl", "adapter-log.jsonl", "claude-stream.jsonl"
            )
        )
    for role in ("primary", "second"):
        context = json.loads(
            (Path(state["scorers"][role]["project"]) / "context-admission.json")
            .read_text(encoding="utf-8")
        )
        checks["both_scorer_contexts_are_mapping_blind"] &= (
            context.get("arm_mapping_present") is False
            and context.get("identity_bearing_source_present") is False
            and context.get("formal_scoring_started") is False
        )
    result = "PASS" if all(checks.values()) else "FAIL"
    write_json(audit_path, {
        "result": result,
        "checks": checks,
        "opaque_ids": sorted(opaque_ids),
        "formal_arm_started": False,
        "mapping_released": False,
        "image_id": IMAGE,
    })
    if result != "PASS":
        raise RuntimeError(f"resource audit failed: {checks}")
    print(audit_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    setup_parser = sub.add_parser("setup")
    setup_parser.add_argument("--master-run-id")
    scorer_parser = sub.add_parser("scorer-admission")
    scorer_parser.add_argument("--master-run-id", required=True)
    arm_parser = sub.add_parser("run-arm")
    arm_parser.add_argument("--master-run-id", required=True)
    arm_parser.add_argument("--arm", required=True, choices=ORDER)
    recover_parser = sub.add_parser("recover-instrument-failure")
    recover_parser.add_argument("--master-run-id", required=True)
    recover_parser.add_argument("--arm", required=True, choices=ORDER)
    rate_parser = sub.add_parser("recover-rate-limit")
    rate_parser.add_argument("--master-run-id", required=True)
    rate_parser.add_argument("--arm", required=True, choices=ORDER)
    supersede_parser = sub.add_parser("supersede-resources")
    supersede_parser.add_argument("--master-run-id", required=True)
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--master-run-id", required=True)
    release_parser = sub.add_parser("release")
    release_parser.add_argument("--master-run-id", required=True)
    audit_parser = sub.add_parser("audit-resources")
    audit_parser.add_argument("--master-run-id", required=True)
    args = parser.parse_args()
    if args.command == "setup":
        master = args.master_run_id or time.strftime("gate2-formal-%Y%m%d-%H%M%S")
        setup(master)
    elif args.command == "scorer-admission":
        scorer_admission(args.master_run_id)
    elif args.command == "run-arm":
        run_arm(args.master_run_id, args.arm)
    elif args.command == "recover-instrument-failure":
        recover_failed_attempt(
            args.master_run_id, args.arm,
            "shared_observable_digest_mismatch",
        )
    elif args.command == "recover-rate-limit":
        recover_failed_attempt(
            args.master_run_id, args.arm, "external_rate_limit"
        )
    elif args.command == "supersede-resources":
        supersede_resources(args.master_run_id)
    elif args.command == "score":
        score(args.master_run_id)
    elif args.command == "release":
        release(args.master_run_id)
    elif args.command == "audit-resources":
        audit_resources(args.master_run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
