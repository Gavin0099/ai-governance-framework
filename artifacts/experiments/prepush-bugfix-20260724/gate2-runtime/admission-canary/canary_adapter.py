#!/usr/bin/env python3
"""Managed tool adapter for the gate2-admission-canary dry run.

The only sanctioned path from a producer session into the canary workspace. It
differs from the read-only rehearsal adapter in two ways that matter:

1. It admits the operations a producer actually needs -- read, write, test,
   diff, status, report -- so "the guard is safe but the producer cannot do the
   job" is testable rather than assumed.
2. Admissibility is not reimplemented here. It loads the same policy JSON the
   PreToolUse guard loads (see ../producer-guard/gate2_policy.py), so the two
   cannot drift. This file owns only EXECUTION: which argv runs in the
   container for an already-admitted verb.

It never passes a shell string into the container: every call is an explicit
argv. File content travels as base64 in an argument and is decoded on this side,
then streamed to `cp /dev/stdin <path>` inside the container -- so no content
ever passes through a shell.

Every call is logged to adapter-log.jsonl with a monotonic seq, the verb, an
argument digest (never the argument payload), the exit code and the digest of
the exact stdout bytes this adapter prints. That digest uses the SAME
normalisation as the PostToolUse hook -- `s.rstrip("\\r\\n")` -- so the adapter
log and the model transcript share one observable and can be joined.
"""
from __future__ import annotations

import base64
import binascii
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "producer-guard"))
from gate2_policy import PolicyError, load_policy  # noqa: E402

CONTAINER = os.environ.get("GATE2_CANARY_CONTAINER", "gate2-admission-canary")
POLICY_PATH = os.environ.get("GATE2_POLICY", os.path.join(HERE, "policy_canary.json"))
LOG = os.environ.get("GATE2_ADAPTER_LOG", os.path.join(HERE, "adapter-log.jsonl"))
SEQ = LOG + ".seq"
LOCK = LOG + ".lock"

REPO = "/work/repo"
OUT = "/work/out"
TEST_ARGV = ["python", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(text: str) -> str:
    """Shared observable definition -- must match gate2_producer_posttool.py."""
    return text.rstrip("\r\n")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@contextlib.contextmanager
def serialised():
    """Hold an exclusive lock across sequence allocation, execution and logging.

    A real model may issue tool calls concurrently. Without this, `next_seq()`
    was a read-modify-write race (two callers read n, both write n+1, so seq
    values collide and a line is effectively lost), and because the log line is
    written *after* execution, log order did not have to match execution order.
    The verifier's ordered join quietly assumed neither could happen.

    Holding the lock for the whole call turns that assumption into an enforced
    property: calls queue instead of interleaving, so seq is unique and
    contiguous and log order *is* execution order. The wait is also evidence --
    a non-zero `lock_wait_ms` means another call really was in flight, which is
    how we detect that the harness issues parallel tool calls at all.
    """
    start = time.monotonic()
    fh = open(LOCK, "a+b")
    try:
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        waited_ms = int((time.monotonic() - start) * 1000)
        yield waited_ms
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def next_seq() -> int:
    """Allocate the next sequence number. MUST be called while `serialised()`."""
    try:
        with open(SEQ, encoding="utf-8") as fh:
            n = int(fh.read().strip() or "0")
    except (OSError, ValueError):
        n = 0
    n += 1
    with open(SEQ, "w", encoding="utf-8") as fh:
        fh.write(str(n))
        fh.flush()
        os.fsync(fh.fileno())
    return n


def log(record: dict) -> None:
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def summarise(verb: str, args: list[str]) -> list[str]:
    """Arguments for the log: paths in full, payloads as digests only."""
    out = []
    for index, arg in enumerate(args):
        is_payload = (verb == "write" and index == 1) or verb == "report"
        out.append(
            f"<b64 len={len(arg)} sha256={sha(arg)[:16]}>"
            if is_payload or len(arg) > 96
            else arg
        )
    return out


def docker(argv: list[str], stdin: bytes | None = None) -> tuple[int, str]:
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    base = ["docker", "exec", "-u", "65532:65532", "-e", "HOME=/work", "-w", REPO]
    if stdin is not None:
        base.append("-i")
    cp = subprocess.run(
        base + [CONTAINER] + argv,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return cp.returncode, cp.stdout.decode("utf-8", "replace")


def write_file(
    target: str,
    content_b64: str,
    *,
    receipt_target: str,
    overwrite: bool = True,
) -> tuple[int, str]:
    """Stream decoded content into the container, then have the container attest
    the resulting digest and byte count.

    `content_matches_request` proves that the sandbox stored the exact decoded
    bytes submitted to the adapter. It cannot prove those submitted bytes match
    the producer's unstated semantic intent; the producer must still read back
    source writes. Result artifacts are create-once so a later mistaken report
    cannot silently replace the scorer's evidence.
    """
    try:
        blob = base64.b64decode(content_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        return 2, f"adapter: content is not valid base64 ({exc})"

    if not overwrite:
        exists_rc, exists_out = docker(["test", "-e", target])
        if exists_rc == 0:
            return 3, json.dumps({
                "error": "target already exists; report artifacts are immutable",
                "target": receipt_target,
                "written": False,
            }, sort_keys=True)
        if exists_rc != 1:
            return exists_rc, exists_out

    rc, out = docker(["cp", "/dev/stdin", target], stdin=blob)
    if rc != 0:
        return rc, out

    sha_rc, sha_out = docker(["sha256sum", target])
    if sha_rc != 0:
        return sha_rc, sha_out
    size_rc, size_out = docker(["wc", "-c", target])
    if size_rc != 0:
        return size_rc, size_out

    stored_sha256 = sha_out.split()[0] if sha_out.split() else ""
    try:
        stored_bytes = int(size_out.split()[0])
    except (IndexError, ValueError):
        return 3, f"adapter: could not parse stored byte count ({size_out!r})"

    expected_sha256 = sha_bytes(blob)
    verified = stored_sha256 == expected_sha256 and stored_bytes == len(blob)
    receipt = {
        "bytes": stored_bytes,
        "content_matches_request": verified,
        "sha256": stored_sha256,
        "target": receipt_target,
        "written": True,
    }
    return (0 if verified else 3), json.dumps(receipt, sort_keys=True)


# verb -> (arity, handler). A conformance test asserts this table and the policy
# describe the same verbs with the same arity, so a verb can never be admitted
# with no way to run it, or runnable without being admitted.
EXEC = {
    "ls": (0, lambda a: docker(["git", "ls-files"])),
    "read": (1, lambda a: docker(["cat", f"{REPO}/{a[0]}"])),
    "write": (2, lambda a: write_file(
        f"{REPO}/{a[0]}", a[1], receipt_target=f"repo:{a[0]}",
    )),
    "test": (0, lambda a: docker(TEST_ARGV)),
    "diff": (0, lambda a: docker(["git", "diff"])),
    "status": (0, lambda a: docker(["git", "status", "--porcelain"])),
    "report": (1, lambda a: write_file(
        f"{OUT}/result.json", a[0], receipt_target="out:result.json",
        overwrite=False,
    )),
}


def execute(verb: str, args: list[str]) -> tuple[int, str]:
    entry = EXEC.get(verb)
    if entry is None:
        # Unreachable if the conformance test holds; loud rather than silent.
        return 2, f"adapter: verb {verb!r} is admitted by policy but has no execution mapping"
    return entry[1](args)


def main(argv: list[str]) -> int:
    verb = argv[0] if argv else ""
    args = argv[1:]

    try:
        policy = load_policy(POLICY_PATH)
    except PolicyError as exc:
        print(f"adapter: policy unusable ({exc})", file=sys.stderr)
        return 2

    ok, reason = policy.check(verb, args) if verb else (False, "missing verb")

    # One critical section: allocate the sequence number, run the call, and
    # write its log line. Concurrent adapter invocations queue here rather than
    # interleaving, so seq stays unique and contiguous and log order is
    # execution order -- properties the verifier previously had to assume.
    with serialised() as lock_wait_ms:
        seq = next_seq()
        base = {
            "ts": now(),
            "seq": seq,
            "pid": os.getpid(),
            "lock_wait_ms": lock_wait_ms,
            "verb": verb or None,
            "args_summary": summarise(verb, args),
            "args_sha256": sha("\x00".join(args)),
            "arg_count": len(args),
            "container": CONTAINER,
            "policy_id": policy.policy_id,
            "policy_sha256": policy.sha256,
        }

        if not ok:
            # Defence in depth: the guard should already have refused this, so a
            # rejected line in this log means something reached the adapter that
            # the guard did not stop.
            log({**base, "decision": "rejected", "reason": reason, "exit": None,
                 "stdout_bytes": None, "stdout_sha256": None})
            print(f"adapter: rejected request ({reason})", file=sys.stderr)
            return 2

        rc, raw = execute(verb, args)
        out = normalise(raw).encode("utf-8")
        result_receipt = None
        if verb in ("write", "report"):
            try:
                parsed = json.loads(normalise(raw))
            except (json.JSONDecodeError, TypeError):
                pass
            else:
                if isinstance(parsed, dict):
                    result_receipt = parsed
        log({**base, "decision": "executed", "reason": None, "exit": rc,
             "stdout_bytes": len(out), "stdout_sha256": sha_bytes(out),
             "result_receipt": result_receipt})
    # Write the same bytes we just measured. Text-mode stdout translates LF to
    # CRLF when Python writes to a pipe on Windows; hashing before that
    # translation made every multi-line live result impossible to join with the
    # post-hook observation.
    sys.stdout.buffer.write(out + b"\n")
    sys.stdout.buffer.flush()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
