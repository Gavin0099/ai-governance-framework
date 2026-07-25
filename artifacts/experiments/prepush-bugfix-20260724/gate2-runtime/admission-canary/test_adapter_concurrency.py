#!/usr/bin/env python3
"""Concurrency tests for the canary adapter's audit log.

A real model may issue tool calls in parallel. Before the serialising lock,
`next_seq()` was a read-modify-write race: two callers read n, both wrote n+1,
so two calls shared a sequence number and the log silently under-counted. The
verifier's ordered join assumed that could not happen.

These tests fire genuinely concurrent adapter invocations and require that the
audit log survives: no duplicate sequence numbers, none lost, every line valid
JSON, and one line per call. They do NOT need Docker -- execution is stubbed, so
what is under test is the logging/sequencing path itself.

Run: python test_adapter_concurrency.py     (exit 0 = all pass)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
results: list[tuple[str, str]] = []

CONCURRENCY = 12

# A worker that imports the real adapter but replaces only container execution,
# so the sequence/lock/log path exercised is exactly the production one.
WORKER = textwrap.dedent(
    """
    import os, sys
    sys.path.insert(0, os.environ["ADAPTER_DIR"])
    import canary_adapter as A
    A.execute = lambda verb, args: (0, "stub-output")
    sys.exit(A.main(["ls"]))
    """
)


def check(name: str, ok: bool, extra: str = "") -> None:
    results.append((name, "PASS" if ok else f"FAIL {extra}"))


def run_concurrent(tmp: str) -> list[subprocess.Popen]:
    worker = os.path.join(tmp, "worker.py")
    with open(worker, "w", encoding="utf-8") as fh:
        fh.write(WORKER)
    env = {
        **os.environ,
        "ADAPTER_DIR": HERE,
        "GATE2_ADAPTER_LOG": os.path.join(tmp, "adapter-log.jsonl"),
        "GATE2_POLICY": os.path.join(HERE, "policy_canary.json"),
    }
    procs = [subprocess.Popen([sys.executable, worker], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
             for _ in range(CONCURRENCY)]
    for p in procs:
        p.wait(timeout=120)
    return procs


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "adapter-log.jsonl")
        procs = run_concurrent(tmp)

        failed = [p for p in procs if p.returncode != 0]
        check("every concurrent call exited 0", not failed,
              str([p.stderr.read().decode()[:100] for p in failed][:2]))

        with open(log_path, encoding="utf-8") as fh:
            raw = [ln for ln in fh if ln.strip()]

        rows = []
        parse_ok = True
        for ln in raw:
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                parse_ok = False
        check("every log line is valid JSON (no interleaved writes)", parse_ok)
        check(f"one log line per call ({CONCURRENCY})", len(rows) == CONCURRENCY,
              f"got {len(rows)}")

        seqs = sorted(r.get("seq") for r in rows)
        check("no duplicate sequence numbers", len(set(seqs)) == len(seqs),
              f"{len(seqs) - len(set(seqs))} duplicate(s)")
        check("sequence numbers are contiguous 1..N",
              seqs == list(range(1, len(rows) + 1)), str(seqs[:5]))

        pids = {r.get("pid") for r in rows}
        check("calls really came from distinct processes", len(pids) == CONCURRENCY,
              f"{len(pids)} distinct pid(s)")

        # The lock is meant to be observable, not just present: under real
        # contention at least one caller must have waited.
        waited = [r for r in rows if (r.get("lock_wait_ms") or 0) > 0]
        check("contention was actually observed (lock_wait_ms > 0 somewhere)",
              len(waited) > 0, "no caller ever waited -- was the lock exercised?")

        # The seq counter must agree with the log after the storm.
        try:
            with open(log_path + ".seq", encoding="utf-8") as fh:
                final = int(fh.read().strip())
        except (OSError, ValueError):
            final = -1
        check("seq counter matches the number of logged calls",
              final == CONCURRENCY, f"counter={final}")

    for name, res in results:
        print(f"[{name}] {res}")
    failed_n = [n for n, r in results if not r.startswith("PASS")]
    print("---")
    print(f"{len(results)} checks: " + ("ALL PASSED" if not failed_n
                                        else f"{len(failed_n)} FAILED"))
    return 0 if not failed_n else 1


if __name__ == "__main__":
    sys.exit(main())
