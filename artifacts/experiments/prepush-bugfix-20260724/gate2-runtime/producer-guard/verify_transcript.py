#!/usr/bin/env python3
"""Independent auditor for a Gate 2 channel run.

Reads only artifacts -- the model transcript and the adapter log -- and answers
the question a reviewer actually has: *is this evidence complete, and does it
join up?* It never consults the guard, the adapter or the container, so it can
be run by someone who does not trust either.

    python verify_transcript.py --transcript t.jsonl --adapter-log a.jsonl

Every check is printed with PASS/FAIL. Exit 0 only if all pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

PRE = "pre_tool_use"
TERMINALS = ("post_tool_use", "post_tool_use_failure")


def load(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{i}: not valid JSON ({exc})")
    return rows


class Checks:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []
        self.notes: list[str] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append((name, ok, detail))

    def note(self, text: str) -> None:
        """Observation, not a pass/fail assertion. Reported, never counted."""
        self.notes.append(text)

    def report(self) -> int:
        for name, ok, detail in self.rows:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        for text in self.notes:
            print(f"[NOTE] {text}")
        bad = [n for n, ok, _ in self.rows if not ok]
        print("---")
        print(f"{len(self.rows)} checks, {len(bad)} failed" if bad else f"{len(self.rows)} checks, ALL PASSED")
        return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--adapter-log", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args()

    events = load(args.transcript)
    adapter = load(args.adapter_log)
    c = Checks()

    pres = [e for e in events if e.get("event") == PRE]
    terms = [e for e in events if e.get("event") in TERMINALS]
    executed = [a for a in adapter if a.get("decision") == "executed"]
    rejected = [a for a in adapter if a.get("decision") == "rejected"]
    allowed = [e for e in pres if e.get("decision") == "allow"]
    denied = [e for e in pres if e.get("decision") == "deny"]

    c.add("transcript is non-empty", bool(events), f"{len(events)} events")
    c.add("every pre event carries a tool_use_id",
          all(isinstance(e.get("tool_use_id"), str) and e["tool_use_id"] for e in pres))
    c.add("every terminal event carries a tool_use_id",
          all(isinstance(e.get("tool_use_id"), str) and e["tool_use_id"] for e in terms))
    c.add("pre-event tool_use_ids are unique",
          len({e.get("tool_use_id") for e in pres}) == len(pres),
          f"{len(pres)} pre events")

    by_id: dict[str, list[dict]] = {}
    for e in terms:
        by_id.setdefault(e.get("tool_use_id"), []).append(e)

    missing = [e["tool_use_id"] for e in allowed if len(by_id.get(e.get("tool_use_id"), [])) != 1]
    c.add("every ALLOWED call has exactly one terminal event under the same tool_use_id",
          not missing, f"{len(allowed)} allowed; broken: {missing}")

    leaked = [e["tool_use_id"] for e in denied if by_id.get(e.get("tool_use_id"))]
    c.add("no DENIED call has a terminal event", not leaked, f"{len(denied)} denied; leaked: {leaked}")

    pre_ids = {e.get("tool_use_id") for e in pres}
    orphans = [t.get("tool_use_id") for t in terms if t.get("tool_use_id") not in pre_ids]
    c.add("no terminal event without a matching pre event", not orphans, f"orphans: {orphans}")

    c.add("allowed-call count equals adapter executed-line count",
          len(allowed) == len(executed), f"transcript {len(allowed)} vs adapter {len(executed)}")

    c.add("the adapter rejected nothing (nothing reached it that the guard should have stopped)",
          not rejected, f"{len(rejected)} rejected line(s)")

    # --- serialisation is enforced, so it is checked rather than assumed ------
    # The adapter holds an exclusive lock across sequence allocation, execution
    # and logging. Before that lock, concurrent calls raced: a call could vanish
    # from the log while the remaining lines still looked perfectly consistent
    # (contiguous, no duplicates), so "the log looks fine" was never evidence
    # that the log was complete.
    seqs = [a.get("seq") for a in executed]
    c.add("adapter sequence numbers are unique",
          len(set(seqs)) == len(seqs), f"{len(seqs) - len(set(seqs))} duplicate(s)")
    c.add("adapter sequence numbers are contiguous from 1",
          sorted(seqs) == list(range(1, len(seqs) + 1)), str(sorted(seqs)[:6]))

    # --- counted join, order-independent -------------------------------------
    # Matching by multiset rather than by position means a harness that issues
    # tool calls in parallel cannot silently pass verification on the strength
    # of an accidental ordering. Byte-identical concurrent calls stay
    # individually correlated through tool_use_id on the transcript side; on the
    # adapter side they are indistinguishable by construction, so the honest
    # guarantee is that every call is accounted for, not that a specific pair
    # can be told apart.
    def fingerprints(rows):
        return Counter((r.get("verb"), r.get("args_sha256")) for r in rows)

    want, got = fingerprints(allowed), fingerprints(executed)
    only_transcript = want - got
    extra = got - want
    detail = []
    if only_transcript:
        detail.append("in transcript but not adapter: "
                      + ", ".join(f"{v}/{str(h)[:8]}x{n}"
                                  for (v, h), n in only_transcript.items()))
    if extra:
        detail.append("in adapter but not transcript: "
                      + ", ".join(f"{v}/{str(h)[:8]}x{n}" for (v, h), n in extra.items()))
    c.add("verb+argument-digest multiset matches between transcript and adapter log "
          "(order-independent)", not detail, "; ".join(detail))

    # Contention is informational, but recording it is how we learn whether the
    # real harness issues parallel tool calls at all.
    contended = [a for a in executed if (a.get("lock_wait_ms") or 0) > 0]
    c.note(f"adapter calls that waited on the serialisation lock: {len(contended)}"
           f" of {len(executed)}"
           + (" (the harness issued overlapping tool calls)" if contended else ""))

    # The shared observable: the adapter's normalised stdout digest must be the
    # digest the post hook recorded for the same call.
    # Order-independent: for each allowed call, its terminal event's stdout
    # digest must appear among the adapter lines that share its verb and
    # argument digest. Positional pairing would have been an ordering assumption
    # again, which is exactly what parallel tool calls break.
    adapter_obs: dict[tuple, Counter] = {}
    for a in executed:
        adapter_obs.setdefault((a.get("verb"), a.get("args_sha256")),
                               Counter())[a.get("stdout_sha256")] += 1
    obs_bad = []
    for e in allowed:
        term = by_id.get(e.get("tool_use_id"), [None])[0]
        if term is None or term.get("event") == "post_tool_use_failure":
            continue  # failure payloads carry `error`, not stdout, by design
        key = (e.get("verb"), e.get("args_sha256"))
        pool = adapter_obs.get(key)
        want_digest = term.get("stdout_sha256")
        if not pool or pool.get(want_digest, 0) <= 0:
            obs_bad.append(f"{e.get('tool_use_id')} {e.get('verb')}: "
                           f"{str(want_digest)[:8]} not among the adapter's "
                           f"stdout digests for that call")
        else:
            pool[want_digest] -= 1
    c.add("shared observable (normalised stdout digest) agrees on both sides "
          "(order-independent)", not obs_bad, "; ".join(obs_bad))

    # Duplicate identical commands must still be individually resolvable.
    digests: dict[str, list[dict]] = {}
    for e in allowed:
        digests.setdefault(e.get("command_sha256"), []).append(e)
    dupes = {d: v for d, v in digests.items() if len(v) > 1}
    dupe_ok = all(len({e["tool_use_id"] for e in v}) == len(v) for v in dupes.values())
    c.add("repeated identical commands are still individually correlated",
          dupe_ok, f"{len(dupes)} command digest(s) repeated"
          + (" -- none in this run, so this check is vacuous" if not dupes else ""))

    failures = [t for t in terms if t.get("event") == "post_tool_use_failure"]
    c.add("failed calls are correlated by the same tool_use_id as their request",
          all(t.get("tool_use_id") in pre_ids for t in failures),
          f"{len(failures)} failure event(s)"
          + (" -- none in this run, so this check is vacuous" if not failures else ""))

    policies = {(e.get("policy_id"), e.get("policy_sha256")) for e in pres}
    c.add("one policy was in force for the whole run", len(policies) == 1, str(sorted(map(str, policies))))
    apolicies = {(a.get("policy_id"), a.get("policy_sha256")) for a in adapter}
    c.add("the adapter enforced the same policy the guard did",
          policies == apolicies, f"guard {sorted(map(str, policies))} vs adapter {sorted(map(str, apolicies))}")

    rc = c.report()
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(
                {
                    "transcript": args.transcript,
                    "adapter_log": args.adapter_log,
                    "events": len(events),
                    "pre": len(pres),
                    "allowed": len(allowed),
                    "denied": len(denied),
                    "terminal": len(terms),
                    "adapter_executed": len(executed),
                    "adapter_rejected": len(rejected),
                    "checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in c.rows],
                    "verdict": "PASS" if rc == 0 else "FAIL",
                },
                fh,
                indent=2,
                sort_keys=True,
            )
            fh.write("\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
