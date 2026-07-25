#!/usr/bin/env python3
"""Mutation tests for the transcript verifier.

A verifier that passes everything is worse than no verifier, because it converts
an unexamined run into a green tick. So: build one consistent pair of artifacts,
confirm it passes, then break it in each way the evidence could plausibly be
wrong or tampered with and confirm the SPECIFIC check that should catch it does.

Run: python test_verify_transcript.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFIER = os.path.join(HERE, "verify_transcript.py")
POLICY = ("p-1", "deadbeef")
results: list[tuple[str, str]] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    results.append((name, "PASS" if ok else f"FAIL {extra}"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixture() -> tuple[list[dict], list[dict]]:
    """Two allowed calls (one of them repeated verbatim) and one denied call."""
    events: list[dict] = []
    adapter: list[dict] = []
    seq = 0
    for i, (tid, verb, args, out) in enumerate([
        ("toolu_a", "ls", [], "TASK.md\nsrc/calc.py"),
        ("toolu_b", "read", ["src/calc.py"], "def add(a, b):"),
        ("toolu_c", "read", ["src/calc.py"], "def add(a, b):"),  # byte-identical repeat
    ]):
        cmd = "adapter " + verb + " " + " ".join(args)
        args_sha = sha("\x00".join(args))
        events.append({"event": "pre_tool_use", "tool_use_id": tid, "decision": "allow",
                       "verb": verb, "args_sha256": args_sha, "command_sha256": sha(cmd),
                       "policy_id": POLICY[0], "policy_sha256": POLICY[1]})
        events.append({"event": "post_tool_use", "tool_use_id": tid,
                       "stdout_sha256": sha(out), "command_sha256": sha(cmd)})
        seq += 1
        adapter.append({"seq": seq, "decision": "executed", "verb": verb, "args_sha256": args_sha,
                        "exit": 0, "stdout_sha256": sha(out),
                        "policy_id": POLICY[0], "policy_sha256": POLICY[1]})
    events.append({"event": "pre_tool_use", "tool_use_id": "toolu_d", "decision": "deny",
                   "verb": None, "args_sha256": sha(""), "command_sha256": sha("docker exec x id"),
                   "policy_id": POLICY[0], "policy_sha256": POLICY[1]})
    return events, adapter


def run(events: list[dict], adapter: list[dict]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as d:
        t = os.path.join(d, "t.jsonl")
        a = os.path.join(d, "a.jsonl")
        for path, rows in ((t, events), (a, adapter)):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                for r in rows:
                    fh.write(json.dumps(r, sort_keys=True) + "\n")
        cp = subprocess.run([sys.executable, VERIFIER, "--transcript", t, "--adapter-log", a],
                            capture_output=True, text=True, timeout=60)
        return cp.returncode, cp.stdout


def failed_checks(stdout: str) -> list[str]:
    return [line[7:].split(" -- ")[0] for line in stdout.splitlines() if line.startswith("[FAIL]")]


def mutation(name: str, expect_fragment: str, mutate) -> None:
    e, a = fixture()
    mutate(e, a)
    rc, out = run(e, a)
    bad = failed_checks(out)
    hit = any(expect_fragment in b for b in bad)
    check(f"caught: {name}", rc != 0 and hit, f"exit={rc} failed={bad}")


def main() -> int:
    rc, out = run(*fixture())
    check("a consistent evidence pair passes", rc == 0, out[-400:])

    mutation("a terminal event is missing", "exactly one terminal event",
             lambda e, a: e.remove(next(x for x in e if x["event"] == "post_tool_use")))
    mutation("a terminal event is duplicated", "exactly one terminal event",
             lambda e, a: e.append(copy.deepcopy(next(x for x in e if x["event"] == "post_tool_use"))))
    mutation("a result appears with no request", "no terminal event without a matching pre",
             lambda e, a: e.append({"event": "post_tool_use", "tool_use_id": "toolu_ghost",
                                    "stdout_sha256": sha("x")}))
    mutation("a denied call produced a result", "no DENIED call has a terminal event",
             lambda e, a: e.append({"event": "post_tool_use", "tool_use_id": "toolu_d",
                                    "stdout_sha256": sha("x")}))
    mutation("the recorded output digest was altered", "shared observable",
             lambda e, a: e[1].update(stdout_sha256=sha("something else")))
    mutation("the adapter ran something the transcript does not show", "allowed-call count",
             lambda e, a: a.append({**a[-1], "seq": 99}))
    # Reordering the adapter log is deliberately NOT a failure any more: each
    # line carries its own seq, and the joins are order-independent so that a
    # harness issuing parallel tool calls cannot pass or fail on accidental
    # ordering. What must still be caught are the real symptoms of the
    # concurrency race the serialising lock now prevents.
    mutation("two adapter calls share a sequence number (the race signature)",
             "sequence numbers are unique",
             lambda e, a: a[-1].update(seq=a[0]["seq"]))
    mutation("an adapter line went missing, leaving a sequence gap",
             "contiguous from 1",
             lambda e, a: a.pop(1) if len(a) > 2 else None)
    mutation("something reached the adapter that the guard should have stopped",
             "adapter rejected nothing",
             lambda e, a: a.append({"seq": 99, "decision": "rejected", "verb": "sh",
                                    "args_sha256": sha(""), "policy_id": POLICY[0],
                                    "policy_sha256": POLICY[1]}))
    mutation("the policy changed mid-run", "one policy was in force",
             lambda e, a: e[0].update(policy_sha256="0000"))
    mutation("the adapter enforced a different policy", "adapter enforced the same policy",
             lambda e, a: [x.update(policy_sha256="1111") for x in a])
    mutation("a pre event lost its correlation id", "every pre event carries a tool_use_id",
             lambda e, a: e[0].update(tool_use_id=""))
    mutation("two calls were given the same correlation id", "tool_use_ids are unique",
             lambda e, a: e[4].update(tool_use_id="toolu_a"))

    for name, res in results:
        print(f"[{name}] {res}")
    failed = [n for n, r in results if not r.startswith("PASS")]
    print("---")
    print(f"{len(results)} checks: " + ("ALL PASSED" if not failed else f"{len(failed)} FAILED"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
