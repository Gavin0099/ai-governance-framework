#!/usr/bin/env python3
"""Guard, policy and adapter must describe the same channel.

The review's standing worry about the first design was that the contract lived
in two places and could drift. It now lives in one, but the adapter still owns
the execution table -- so this asserts the two halves line up exactly: no verb
admitted with no way to run it, and no runnable verb that was never admitted.

Runs offline: no container, no docker. Run: python test_canary_conformance.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "producer-guard"))

import canary_adapter as A  # noqa: E402
import gate2_producer_guard as G  # noqa: E402
from gate2_policy import load_policy  # noqa: E402

results: list[tuple[str, str]] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    results.append((name, "PASS" if ok else f"FAIL {extra}"))


def main() -> int:
    policy = load_policy(os.path.join(HERE, "policy_canary.json"))
    adapter = os.path.join(HERE, "canary_adapter.sh")

    check("every admitted verb has an execution mapping",
          set(policy.verbs) <= set(A.EXEC), str(set(policy.verbs) - set(A.EXEC)))
    check("every executable verb is admitted by the policy",
          set(A.EXEC) <= set(policy.verbs), str(set(A.EXEC) - set(policy.verbs)))
    for verb, (arity, _) in A.EXEC.items():
        want = len(policy.verbs.get(verb, ()))
        check(f"arity agrees for {verb!r}", arity == want, f"adapter {arity} vs policy {want}")

    # The guard admits exactly what the policy admits, through the real command
    # surface -- a whole-command check, not just policy.check().
    for verb, (arity, _) in A.EXEC.items():
        args = ["src/calc.py", "aGk="][:arity] if verb in ("read", "write") else ["aGk="][:arity]
        allow, reason, _ = G.evaluate(policy, adapter, "Bash", {"command": " ".join([adapter, verb, *args])})
        check(f"guard admits the sanctioned form of {verb!r}", allow, reason)

    check("the producer channel has no verb that runs an arbitrary command",
          not ({"sh", "bash", "exec", "eval", "run", "shell"} & set(A.EXEC)))
    check("the producer channel has no verb that takes anything out of the sandbox",
          not ({"cp", "copy", "export", "fetch", "push"} & set(A.EXEC)))

    for name, res in results:
        print(f"[{name}] {res}")
    failed = [n for n, r in results if not r.startswith("PASS")]
    print("---")
    print(f"{len(results)} checks: " + ("ALL PASSED" if not failed else f"{len(failed)} FAILED"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
