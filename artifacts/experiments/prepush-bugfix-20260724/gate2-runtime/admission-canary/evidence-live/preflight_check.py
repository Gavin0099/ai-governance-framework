#!/usr/bin/env python3
"""Is the channel live in this session? GO / NO-GO from artifacts alone.

Run this once the producer has made its first two or three calls, and stop the
session immediately on NO-GO.

    python preflight_check.py --transcript t.jsonl --adapter-log a.jsonl \
        --deny-evidence transcript.probe-phase-1.jsonl

WHY THIS IS NO LONGER A PROBE. The first two designs asked the producer to run a
command whose only purpose was to be observed -- first one meant to be refused,
then a bare `status` with no context. Both failed the same way: the producer
oriented itself with `ls` or `Read`, met a run of bare refusals, and declined to
run an unexplained script in what looked like a hostile or broken environment.
That is correct behaviour on its part; the design was asking an aligned agent to
blind-run something it had just been prevented from inspecting.

So nothing artificial is asked any more. The producer is given the real task,
whose first natural step is `read TASK.md`, and this checks the artifacts that
call leaves behind. The cost is that the container may already have been read
from -- which is why the operator captures `baseline-before.json` first, and why
a NO-GO means re-seed rather than merely restart.

The deny path is evidenced from an earlier session's transcript via
`--deny-evidence`, so no producer is ever asked to trigger a refusal.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

from answer_questions import load

PRE = "pre_tool_use"
TERMINALS = ("post_tool_use", "post_tool_use_failure")
NATURAL_OBSERVABLE_VERBS = {"read", "ls", "test", "diff", "status"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--adapter-log", required=True)
    ap.add_argument("--deny-evidence",
                    help="a transcript from an earlier session in which the deny path was "
                         "exercised, so this session need not be asked to trigger one")
    args = ap.parse_args()

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    if not os.path.exists(args.transcript):
        check("the transcript file exists", False,
              f"{args.transcript} is absent -- the guard never ran, so the session has no hooks "
              f"(wrong working directory, or not Claude Code)")
        events = []
    else:
        events = load(args.transcript)
        check("the transcript file exists", True, args.transcript)

    adapter = load(args.adapter_log) if os.path.exists(args.adapter_log) else []

    check("the guard recorded at least one decision", bool(events), f"{len(events)} event(s)")

    pres = [e for e in events if e.get("event") == PRE]
    terms = [e for e in events if e.get("event") in TERMINALS]
    term_ids = {t.get("tool_use_id") for t in terms}
    allowed = [e for e in pres if e.get("decision") == "allow"]
    executed = [a for a in adapter if a.get("decision") == "executed"]

    # --- the deny path, possibly evidenced elsewhere --------------------------
    if args.deny_evidence:
        deny_events = load(args.deny_evidence)
        source = args.deny_evidence
        deny_terms = {t.get("tool_use_id") for t in deny_events if t.get("event") in TERMINALS}
    else:
        deny_events, source, deny_terms = events, args.transcript, term_ids
    denied_any = [e for e in deny_events
                  if e.get("event") == PRE and e.get("decision") == "deny"]

    check("the deny path was exercised", bool(denied_any),
          f"{len(denied_any)} denied call(s) in {source}")
    check("every denied call was refused for a stated reason",
          bool(denied_any) and all(e.get("reason") for e in denied_any),
          "; ".join(sorted({str(e.get("reason")) for e in denied_any}))[:160])
    check("no denied call produced a terminal event (they really did not run)",
          all(e.get("tool_use_id") not in deny_terms for e in denied_any))

    # --- the allow path, which must be THIS session ---------------------------
    check("at least one call was ALLOWED in this session", bool(allowed),
          f"{len(allowed)} allowed call(s): {sorted({str(e.get('verb')) for e in allowed})}")
    check("every allowed call produced exactly one terminal event",
          bool(allowed) and all(
              len([t for t in terms if t.get("tool_use_id") == e.get("tool_use_id")]) == 1
              for e in allowed),
          f"{len(terms)} terminal event(s) for {len(allowed)} allowed call(s)")
    check("the post hooks are firing (a terminal event exists at all)", bool(terms),
          f"{len(terms)} terminal event(s)")

    # --- the adapter side, which is what proves env reached the tool ----------
    check("the adapter log is at the configured path (env reached the tool process)",
          bool(executed), f"{args.adapter_log}: {len(executed)} executed line(s)")
    check("every adapter call recorded an exit code",
          bool(executed) and all(a.get("exit") is not None for a in executed),
          "; ".join(f"{a.get('verb')}:{a.get('exit')}" for a in executed[:6]))
    check("nothing reached the adapter that the guard should have stopped",
          not [a for a in adapter if a.get("decision") == "rejected"])
    check("allowed calls and adapter executions agree in number",
          len(allowed) == len(executed), f"transcript {len(allowed)} vs adapter {len(executed)}")

    # A count-only preflight passed live-canary-20260726-152447 even though the
    # byte-level join had been broken since the first call. Exercise the same
    # order-independent shared observable as the final verifier while the run is
    # still cheap to discard. The task's required first call is `read TASK.md`,
    # so at least one naturally multi-line-capable call must be present.
    by_id: dict[str, list[dict]] = {}
    for term in terms:
        by_id.setdefault(term.get("tool_use_id"), []).append(term)
    observable_calls = []
    for event in allowed:
        tlist = by_id.get(event.get("tool_use_id"), [])
        if (event.get("verb") in NATURAL_OBSERVABLE_VERBS
                and len(tlist) == 1
                and tlist[0].get("event") == "post_tool_use"
                and tlist[0].get("stdout_sha256")):
            observable_calls.append((event, tlist[0]))

    adapter_obs: dict[tuple, Counter] = {}
    for row in executed:
        key = (row.get("verb"), row.get("args_sha256"))
        adapter_obs.setdefault(key, Counter())[row.get("stdout_sha256")] += 1
    observable_bad = []
    for event, term in observable_calls:
        key = (event.get("verb"), event.get("args_sha256"))
        digest = term.get("stdout_sha256")
        pool = adapter_obs.get(key)
        if not pool or pool.get(digest, 0) <= 0:
            observable_bad.append(
                f"{event.get('tool_use_id')} {event.get('verb')}: "
                f"{str(digest)[:8]} not in adapter log"
            )
        else:
            pool[digest] -= 1
    observable_detail = (
        "; ".join(observable_bad)
        if observable_bad
        else f"{len(observable_calls)} read/ls/test/diff/status call(s) joined"
        if observable_calls
        else "no completed read/ls/test/diff/status call carries a stdout digest yet"
    )
    check("a natural output-bearing call has the same shared observable on both sides",
          bool(observable_calls) and not observable_bad, observable_detail)

    gpol = {(e.get("policy_id"), e.get("policy_sha256")) for e in pres}
    apol = {(a.get("policy_id"), a.get("policy_sha256")) for a in adapter}
    check("guard and adapter loaded the same policy", bool(gpol) and gpol == apol,
          f"guard {sorted(map(str, gpol))} vs adapter {sorted(map(str, apol))}")

    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    bad = [n for n, ok, _ in checks if not ok]
    print("---")
    if bad:
        print(f"NO-GO -- {len(bad)} of {len(checks)} checks failed. Stop the session now.")
        print("Move the partial transcript aside, re-seed the container, fix the cause, start again.")
        return 1
    print(f"GO -- all {len(checks)} checks passed. The channel is live in this session: "
          f"hooks loaded, both post directions wired, env reached the tool process, one policy "
          f"in force. Let it run to completion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
