#!/usr/bin/env python3
"""Read a live producer run's artifacts and answer the five open questions.

`verify_transcript.py` asks whether the evidence joins up. This asks what the
real harness *did* -- the things the producer-guard README lists as documented
but never observed, because only an emulator had driven the channel.

    python answer_questions.py --transcript t.jsonl --adapter-log a.jsonl

Artifacts only: it never consults the guard, the adapter or the container.

EVERY ANSWER IS EITHER ANSWERED OR UNANSWERED, and the difference is load-
bearing. A run that never produced a denial says nothing about whether deny
works; a run whose calls cannot be individually attributed says nothing about
which post event a failure arrives on. Both of those previously printed a
confident wrong answer, which is worse than printing nothing.

IDENTITY, AND ITS LIMIT. The transcript is keyed by `tool_use_id`; the adapter
log is not, and cannot be -- the adapter is executed by the producer's shell and
never learns the id of the tool call that invoked it. So the only honest join is
verb + argument digest + the shared normalised stdout digest. Two calls that
agree on all three are indistinguishable by construction, exactly as
`verify_transcript.py` concedes. Where that ambiguity touches an answer, the
answer is UNANSWERED -- never a guess from list order, which is what an earlier
version did and which a reordered-call counter-example proved could invert the
conclusion.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from evidence_io import atomic_write_json

PRE = "pre_tool_use"
TERMINALS = ("post_tool_use", "post_tool_use_failure")

ANSWERED = "ANSWERED"
UNANSWERED = "UNANSWERED"


def load(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"{path}:{i}: not valid JSON ({exc})")
    return rows


# --------------------------------------------------------------------------- #
#  analysis (pure: takes rows, returns a verdict dict -- so tests can assert)   #
# --------------------------------------------------------------------------- #

def _q1(events: list[dict]) -> dict:
    per_event = {}
    for name in (PRE,) + TERMINALS:
        rows = [e for e in events if e.get("event") == name]
        withid = [e for e in rows if isinstance(e.get("tool_use_id"), str) and e["tool_use_id"]]
        per_event[name] = {
            "count": len(rows),
            "with_id": len(withid),
            "example": withid[0]["tool_use_id"] if withid else None,
        }
    observed = [n for n, v in per_event.items() if v["count"]]
    missing = [n for n, v in per_event.items() if v["count"] and v["with_id"] != v["count"]]
    unobserved = [n for n, v in per_event.items() if not v["count"]]

    if missing:
        return {"status": ANSWERED, "answer": f"NO -- {', '.join(missing)} carried events with no tool_use_id",
                "per_event": per_event}
    if len(observed) < 3:
        return {"status": UNANSWERED,
                "answer": f"every observed event carried a tool_use_id, but {', '.join(unobserved)} "
                          f"never occurred in this run, so all three events are not confirmed",
                "per_event": per_event}
    return {"status": ANSWERED, "answer": "YES -- all three event kinds occurred and every one carried a "
                                          "non-empty tool_use_id", "per_event": per_event}


def _q2(pres: list[dict], terms: list[dict], adapter: list[dict], probe_token: str) -> dict:
    denied = [e for e in pres if e.get("decision") == "deny"]
    # The operator's liveness probe is a denial the operator asked for. It
    # proves the deny path executes; it does NOT prove a producer trying to
    # leave the channel gets stopped, because no producer tried.
    probes = [e for e in denied if probe_token and probe_token in str(e.get("command") or "")]
    natural = [e for e in denied if e not in probes]
    term_ids = {e.get("tool_use_id") for e in terms}
    adapter_fp = Counter((a.get("verb"), a.get("args_sha256")) for a in adapter)
    rejected = [a for a in adapter if a.get("decision") == "rejected"]

    leaked = [e for e in denied if e.get("tool_use_id") in term_ids]
    reached = [e for e in denied
               if e.get("verb") and adapter_fp.get((e.get("verb"), e.get("args_sha256")))]

    if not denied:
        # The decisive point: no denial observed is NOT evidence that deny works.
        return {"status": UNANSWERED,
                "answer": "no denied call was observed, so this run says nothing about whether an "
                          "exit-0 deny JSON is honoured",
                "denied": 0, "probe_denials": 0, "producer_denials": 0,
                "leaked": 0, "reached": 0, "adapter_rejected": len(rejected), "denials": []}

    ok = not leaked and not reached and not rejected
    answer = ("HONOURED -- every denied call produced no terminal event, no adapter line "
              "and no adapter-side rejection"
              if ok else "LEAKED -- a denied call reached the tool")
    if ok and not natural:
        answer += (" -- but every denial was the operator's liveness probe; the producer never "
                   "attempted to leave the channel, so containment under a real escape attempt "
                   "is untested")
    return {"status": ANSWERED, "answer": answer,
            "denied": len(denied), "probe_denials": len(probes), "producer_denials": len(natural),
            "leaked": len(leaked), "reached": len(reached), "adapter_rejected": len(rejected),
            "denials": [{"command": e.get("command"), "reason": e.get("reason"),
                         "origin": "operator probe" if e in probes else "producer"} for e in denied]}


def _q3(pres: list[dict], terms: list[dict], adapter: list[dict]) -> dict:
    """Which post event does a non-zero Bash exit arrive on?

    Two independent routes, neither of which may use list order:

    A. CERTAIN ATTRIBUTION. A terminal event that carries a stdout digest can be
       matched to adapter lines sharing its verb, argument digest AND that exact
       stdout digest. If every such line agrees on the exit code, this call's
       exit code is known. If they disagree -- or the terminal event carries no
       stdout at all, which is how a failure payload looks -- the call is
       unattributable and contributes nothing.

    B. POPULATION MATCH. Independent of identity: if there are non-zero exits and
       no failure events exist at all, non-zero exits must arrive as PostToolUse.
       If the failure-event count equals the non-zero-exit count and the ordinary
       count equals the zero-exit count, they arrive as PostToolUseFailure.
       Anything else is inconclusive.

       Route B is only sound while every allowed call has exactly one terminal
       event. If a call is missing its terminal event, "no failure events exist"
       stops meaning "the failure arrived as PostToolUse" and starts meaning
       "the failure may have arrived as nothing at all", so the route is
       withdrawn rather than trusted.
    """
    allowed = [e for e in pres if e.get("decision") == "allow"]
    executed = [a for a in adapter if a.get("decision") == "executed"]
    by_id: dict = {}
    for t in terms:
        by_id.setdefault(t.get("tool_use_id"), []).append(t)

    n_nonzero = len([a for a in executed if a.get("exit") not in (0, None)])
    n_zero = len([a for a in executed if a.get("exit") == 0])
    fail_events = [t for t in terms if t.get("event") == "post_tool_use_failure"]
    ok_events = [t for t in terms if t.get("event") == "post_tool_use"]

    certain, unattributable = [], []
    for e in allowed:
        tlist = by_id.get(e.get("tool_use_id")) or []
        if len(tlist) != 1:
            unattributable.append((e.get("verb"), "no single terminal event"))
            continue
        t = tlist[0]
        digest = t.get("stdout_sha256")
        if not digest:
            unattributable.append((e.get("verb"), f"{t.get('event')} carries no stdout digest"))
            continue
        cands = [a for a in executed
                 if a.get("verb") == e.get("verb")
                 and a.get("args_sha256") == e.get("args_sha256")
                 and a.get("stdout_sha256") == digest]
        exits = {a.get("exit") for a in cands}
        if not cands:
            unattributable.append((
                e.get("verb"),
                "no adapter line matches its verb, arguments and shared stdout observable; "
                "the cross-side join is broken",
            ))
        elif len(exits) == 1:
            certain.append({"verb": e.get("verb"), "exit": exits.pop(), "event": t.get("event")})
        else:
            unattributable.append((e.get("verb"),
                                   "several adapter lines share its verb, arguments and stdout "
                                   f"but disagree on exit ({sorted(map(str, exits))})"))

    coverage_ok = bool(allowed) and all(len(by_id.get(e.get("tool_use_id")) or []) == 1
                                        for e in allowed)

    certain_nonzero = [c for c in certain if c["exit"] not in (0, None)]
    routes = []
    answer, status = None, UNANSWERED

    if certain_nonzero:
        kinds = sorted({c["event"] for c in certain_nonzero})
        routes.append(f"certain attribution: {len(certain_nonzero)} non-zero-exit call(s) -> "
                      f"{', '.join(kinds)}")
        if len(kinds) == 1:
            status, answer = ANSWERED, f"non-zero exits arrived as {kinds[0]}"
        else:
            status, answer = ANSWERED, f"non-zero exits arrived as BOTH {' and '.join(kinds)}"
        # Attributing one failing call does not license a general rule while
        # other failing calls remain unattributed.
        remainder = n_nonzero - len(certain_nonzero)
        if remainder > 0:
            answer += (f" -- but only {len(certain_nonzero)} of {n_nonzero} non-zero-exit call(s) "
                       f"could be attributed; the other {remainder} is not settled by this run")

    if n_nonzero == 0:
        routes.append("population: no non-zero exit occurred at all")
    elif not coverage_ok:
        routes.append("population: WITHDRAWN -- not every allowed call has exactly one terminal "
                      "event, so counting events cannot stand in for identity")
    elif not fail_events:
        routes.append(f"population: {n_nonzero} non-zero exit(s) and zero failure events")
        if status == UNANSWERED:
            status, answer = ANSWERED, "non-zero exits arrived as post_tool_use"
    elif len(fail_events) == n_nonzero and len(ok_events) == n_zero:
        routes.append(f"population: failure events ({len(fail_events)}) == non-zero exits "
                      f"({n_nonzero}) and ordinary events ({len(ok_events)}) == zero exits ({n_zero})")
        if status == UNANSWERED:
            status, answer = ANSWERED, "non-zero exits arrived as post_tool_use_failure"
    else:
        routes.append(f"population: inconclusive -- {len(fail_events)} failure event(s) vs "
                      f"{n_nonzero} non-zero exit(s); {len(ok_events)} ordinary vs {n_zero} zero")

    if status == UNANSWERED and answer is None:
        answer = ("no non-zero exit could be attributed to a terminal event, and the counts do not "
                  "settle it either" if n_nonzero else
                  "the run never produced a failing call")

    return {"status": status, "answer": answer, "routes": routes,
            "certain": certain, "unattributable": unattributable,
            "nonzero_exits": n_nonzero, "zero_exits": n_zero,
            "failure_events": len(fail_events), "ordinary_events": len(ok_events)}


def _q4(terms: list[dict]) -> dict:
    if not terms:
        return {"status": UNANSWERED, "answer": "no terminal event was recorded",
                "sources": {}, "keysets": [], "usable_observable": "0/0"}
    srcs = Counter(t.get("observable_source") for t in terms)
    keysets = Counter(tuple(t.get("response_keys") or []) for t in terms)
    usable = [t for t in terms if t.get("stdout_sha256")]
    top = keysets.most_common(1)[0][0]
    serializable_keysets = [
        {"keys": list(keys), "count": count}
        for keys, count in sorted(keysets.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {"status": ANSWERED,
            "answer": (f"tool_response is a dict with keys {list(top)}" if top
                       else "tool_response was not a dict on any event"),
            "sources": dict(srcs), "keysets": serializable_keysets,
            "usable_observable": f"{len(usable)}/{len(terms)}"}


def _q5(adapter: list[dict]) -> dict:
    executed = [a for a in adapter if a.get("decision") == "executed"]
    contended = [a for a in executed if (a.get("lock_wait_ms") or 0) > 0]
    if not executed:
        return {"status": UNANSWERED, "answer": "no adapter call executed", "contended": 0, "executed": 0}
    if contended:
        return {"status": ANSWERED, "answer": "YES -- overlapping tool calls were observed",
                "contended": len(contended), "executed": len(executed),
                "waits_ms": sorted((a.get("lock_wait_ms") or 0) for a in contended),
                "pids": len({a.get("pid") for a in executed})}
    # Absence of contention is not evidence of serialisation.
    return {"status": UNANSWERED,
            "answer": "no contention observed -- consistent with a harness that serialises tool "
                      "calls AND with one that simply never overlapped in this run",
            "contended": 0, "executed": len(executed)}


PROBE_TOKEN = "gate2-liveness-probe"


def analyse(events: list[dict], adapter: list[dict], probe_token: str = PROBE_TOKEN) -> dict:
    pres = [e for e in events if e.get("event") == PRE]
    terms = [e for e in events if e.get("event") in TERMINALS]
    return {
        "totals": {
            "events": len(events), "pre": len(pres),
            "allow": len([e for e in pres if e.get("decision") == "allow"]),
            "deny": len([e for e in pres if e.get("decision") == "deny"]),
            "terminal": len(terms), "adapter_lines": len(adapter),
            "adapter_executed": len([a for a in adapter if a.get("decision") == "executed"]),
        },
        "q1": _q1(events),
        "q2": _q2(pres, terms, adapter, probe_token),
        "q3": _q3(pres, terms, adapter),
        "q4": _q4(terms),
        "q5": _q5(adapter),
    }


# --------------------------------------------------------------------------- #
#  rendering                                                                    #
# --------------------------------------------------------------------------- #

QUESTIONS = {
    "q1": "does the harness supply tool_use_id on all three events?",
    "q2": "did the exit-0 deny JSON actually block the call?",
    "q3": "which post event does a non-zero Bash exit arrive on?",
    "q4": "what is the real shape of tool_response?",
    "q5": "does the harness issue parallel tool calls?",
}


def render(r: dict) -> None:
    t = r["totals"]
    print(f"transcript: {t['events']} events ({t['pre']} pre = {t['allow']} allow + {t['deny']} deny, "
          f"{t['terminal']} terminal)")
    print(f"adapter log: {t['adapter_lines']} lines ({t['adapter_executed']} executed)")

    for key, question in QUESTIONS.items():
        a = r[key]
        print(f"\n=== {key.upper()}. {question}")
        print(f"  [{a['status']}] {a['answer']}")

        if key == "q1":
            for name, v in a["per_event"].items():
                state = ("not observed in this run" if not v["count"]
                         else f"{v['with_id']}/{v['count']} carry a tool_use_id")
                print(f"    {name:<24} {v['count']:>3} event(s) -- {state}"
                      + (f"  e.g. {v['example']}" if v["example"] else ""))
        elif key == "q2":
            print(f"    denied {a['denied']} ({a['producer_denials']} producer-initiated, "
                  f"{a['probe_denials']} operator probe); leaked {a['leaked']}; "
                  f"reached the adapter {a['reached']}; adapter-side rejections {a['adapter_rejected']}")
            for d in a["denials"]:
                print(f"    - [{d['origin']}] {str(d['command'])[:76]}")
                print(f"        reason: {d['reason']}")
        elif key == "q3":
            for route in a["routes"]:
                print(f"    {route}")
            for c in a["certain"]:
                if c["exit"] not in (0, None):
                    print(f"    - {c['verb']:<8} exit={c['exit']} -> {c['event']}   (attributed by "
                          f"shared stdout digest)")
            for verb, why in a["unattributable"]:
                print(f"    - {verb:<8} UNATTRIBUTABLE: {why}")
        elif key == "q4":
            for src, n in a["sources"].items():
                print(f"    observable_source: {src!r} x{n}")
            for item in a["keysets"]:
                keys, n = item["keys"], item["count"]
                print(f"    response_keys: {list(keys) if keys else '<not a dict>'} x{n}")
            print(f"    terminal events carrying a usable shared observable: {a['usable_observable']}")
        elif key == "q5":
            print(f"    adapter calls that waited on the serialisation lock: "
                  f"{a['contended']} of {a['executed']}")
            if a.get("waits_ms"):
                print(f"    waits (ms): {a['waits_ms']}; distinct adapter pids: {a['pids']}")

    unanswered = [k for k in QUESTIONS if r[k]["status"] == UNANSWERED]
    print("\n---")
    print(f"{len(QUESTIONS) - len(unanswered)} answered, {len(unanswered)} unanswered"
          + (f" ({', '.join(u.upper() for u in unanswered)})" if unanswered else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--adapter-log", required=True)
    ap.add_argument("--json-out")
    ap.add_argument("--probe-token", default=PROBE_TOKEN,
                    help="marks operator-issued liveness-probe denials so they are not counted "
                         "as the producer being contained")
    args = ap.parse_args()

    result = analyse(load(args.transcript), load(args.adapter_log), args.probe_token)
    render(result)
    if args.json_out:
        atomic_write_json(args.json_out, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
