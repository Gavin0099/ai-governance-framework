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

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append((name, ok, detail))

    def report(self) -> int:
        for name, ok, detail in self.rows:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
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

    # Ordered join. The channel is serial, so the k-th allowed call in the
    # transcript must be the k-th line in the adapter log.
    join_bad = []
    for k, (e, a) in enumerate(zip(allowed, executed)):
        if e.get("verb") != a.get("verb") or e.get("args_sha256") != a.get("args_sha256"):
            join_bad.append(f"#{k}: transcript {e.get('verb')}/{str(e.get('args_sha256'))[:8]}"
                            f" vs adapter {a.get('verb')}/{str(a.get('args_sha256'))[:8]}")
    c.add("ordered verb+argument-digest join between transcript and adapter log",
          not join_bad, "; ".join(join_bad))

    # The shared observable: the adapter's normalised stdout digest must be the
    # digest the post hook recorded for the same call.
    obs_bad = []
    for k, (e, a) in enumerate(zip(allowed, executed)):
        term = by_id.get(e.get("tool_use_id"), [None])[0]
        if term is None:
            continue
        if term.get("event") == "post_tool_use_failure":
            continue  # failure payloads carry `error`, not stdout, by design
        if term.get("stdout_sha256") != a.get("stdout_sha256"):
            obs_bad.append(f"#{k} {e.get('verb')}: {str(term.get('stdout_sha256'))[:8]}"
                           f" != {str(a.get('stdout_sha256'))[:8]}")
    c.add("shared observable (normalised stdout digest) agrees on both sides",
          not obs_bad, "; ".join(obs_bad))

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
