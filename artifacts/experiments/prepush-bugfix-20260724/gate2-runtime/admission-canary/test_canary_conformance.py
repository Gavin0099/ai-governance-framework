#!/usr/bin/env python3
"""Guard, policy and adapter must describe the same channel.

The review's standing worry about the first design was that the contract lived
in two places and could drift. It now lives in one, but the adapter still owns
the execution table -- so this asserts the two halves line up exactly: no verb
admitted with no way to run it, and no runnable verb that was never admitted.

Runs offline: no container, no docker. Run: python test_canary_conformance.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

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

    # Regression for live-canary-20260726-152447. This must cross a real process
    # stdout pipe: comparing the adapter and post-hook normalisers in-process
    # cannot see Windows text-mode LF -> CRLF translation.
    with tempfile.TemporaryDirectory() as tmp:
        adapter_log = os.path.join(tmp, "adapter-log.jsonl")
        worker = (
            "import sys\n"
            f"sys.path.insert(0, {HERE!r})\n"
            "import canary_adapter as A\n"
            "A.execute = lambda verb, args: (0, 'alpha\\nbeta\\n')\n"
            "raise SystemExit(A.main(['ls']))\n"
        )
        env = {
            **os.environ,
            "GATE2_ADAPTER_LOG": adapter_log,
            "GATE2_POLICY": os.path.join(HERE, "policy_canary.json"),
            "GATE2_CANARY_CONTAINER": "emission-regression-no-container",
        }
        cp = subprocess.run(
            [sys.executable, "-c", worker],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        check("adapter emission subprocess exits zero", cp.returncode == 0,
              cp.stderr.decode("utf-8", "replace"))
        check("adapter emits byte-exact LF through a subprocess pipe",
              cp.stdout == b"alpha\nbeta\n", repr(cp.stdout))
        try:
            with open(adapter_log, encoding="utf-8") as fh:
                recorded = json.loads(fh.read())
        except (OSError, json.JSONDecodeError) as exc:
            recorded = {}
            check("adapter emission subprocess writes one readable log line", False, str(exc))
        else:
            check("adapter emission subprocess writes one readable log line", True)
        observed = cp.stdout.rstrip(b"\r\n")
        check("logged stdout digest describes the bytes received across the pipe",
              recorded.get("stdout_sha256") == hashlib.sha256(observed).hexdigest(),
              f"log={recorded.get('stdout_sha256')} observed={hashlib.sha256(observed).hexdigest()}")
        check("logged stdout length describes the bytes received across the pipe",
              recorded.get("stdout_bytes") == len(observed),
              f"log={recorded.get('stdout_bytes')} observed={len(observed)}")

    for name, res in results:
        print(f"[{name}] {res}")
    failed = [n for n, r in results if not r.startswith("PASS")]
    print("---")
    print(f"{len(results)} checks: " + ("ALL PASSED" if not failed else f"{len(failed)} FAILED"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
