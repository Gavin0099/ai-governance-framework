#!/usr/bin/env python3
"""
E1b Phase 2 — Distribution Analysis Script.

Reads one or more canonical-audit-log.jsonl files, computes per-repo
entropy / signal_ratio / degenerate metrics, and evaluates whether the
accumulated observation pool satisfies the Phase 2 readiness gate.

Purpose
-------
Make Phase 2 "observably waiting" rather than "passively waiting".
Running this script after real sessions accumulate answers:

  - Is the log growing into a usable distribution?
  - Are there low-entropy / degenerate repos dominating the pool?
  - Does the pool have enough repo diversity to build a valid baseline?

Phase 2 readiness gate (all four conditions must pass before Phase 3):
  --min-sessions N          total session entries across all repos
  --min-repos   M           distinct contributing repos
  --min-nondegenerate R     fraction of repos that are NOT degenerate
  --max-dominance R         max fraction any one repo can occupy

Usage
-----
    # Default: read this repo's own log
    python scripts/analyze_e1b_distribution.py

    # Read multiple repo logs (merged view)
    python scripts/analyze_e1b_distribution.py --log-path a.jsonl b.jsonl c.jsonl

    # Override gate thresholds
    python scripts/analyze_e1b_distribution.py --min-sessions 40 --min-repos 5

    # Machine-readable output
    python scripts/analyze_e1b_distribution.py --json

E1b Phase roadmap
-----------------
  Phase 1 (done):     passive observation — entropy + degenerate guard; advisory_only=True
  Phase 2 (this):     distribution understanding — accumulate + analyze real sessions
  Phase 3 (blocked):  trigger design — only after Phase 2 gate passes
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

_E1B_MIN_VALID_ENTROPY: float = 0.3

# Default Phase 2 readiness gate thresholds.
# These can be overridden via CLI flags.
# The rationale for each:
#   min_sessions=20  — below 20 the entropy estimate is unreliable
#   min_repos=3      — single-repo pool cannot reveal repo-level variance
#   min_nondegenerate=0.7 — conservative pre-empirical governance threshold;
#     NOT derived from observed data. A policy choice to prevent heavily-degenerate
#     pools from anchoring a spurious baseline.
#     Revise downward only after empirical distribution has been established.
#   max_dominance=0.6 — no single repo should supply more than 60% of samples
#   min_unique_pattern=0.4 — at least 40% of sessions must have distinct signatures
#     (guards against pseudo-diversity: 3 repos all running identical lifecycle pattern)
_PHASE2_MIN_SESSIONS: int = 20
_PHASE2_MIN_REPOS: int = 3
_PHASE2_MIN_NONDEGENERATE_RATIO: float = 0.7
_PHASE2_MAX_REPO_DOMINANCE: float = 0.6
_PHASE2_MIN_UNIQUE_PATTERN_RATIO: float = 0.4

_DEFAULT_LOG_PATH = (
    Path("artifacts") / "runtime" / "canonical-audit-log.jsonl"
)


# ── Session fingerprint ──────────────────────────────────────────────────────

def _session_fingerprint(entry: dict) -> tuple:
    """
    Compact signature for a single audit-log entry.

    Used to estimate session-level diversity across the pool.
    Two entries with the same fingerprint represent statistically the same
    kind of session — repeated observations of an identical lifecycle pattern.

    Components
    ----------
    artifact_state  — absent / ok / stale / malformed
    signals         — sorted tuple of emitted signal codes
    gate_blocked    — whether the gate was blocked this session

    Not included: repo_name, timestamp, policy_provenance.
    We want to measure lifecycle diversity, not repo identity.

    Limitation (design boundary)
    ----------------------------
    This fingerprint is sufficient as a GATE GUARD against pseudo-diversity.
    It is NOT a session type classifier.

    Two sessions may share the same fingerprint yet have operationally different
    meanings — e.g. (absent, [], False) can represent::
      - transient artifact absence
      - long-running static absent lifecycle
      - post-create deletion tail-state

    If Phase 3 requires pattern-level analysis (transition sequences, lifecycle
    length, state trajectory), this fingerprint must be upgraded before use.
    Do not treat unique_pattern_ratio as proof of lifecycle diversity.
    """
    artifact_state = entry.get("artifact_state", "unknown")
    signals = tuple(sorted(entry.get("signals") or []))
    gate_blocked = bool(entry.get("gate_blocked"))
    return (artifact_state, signals, gate_blocked)


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_entries(log_paths: list[Path]) -> list[dict]:
    """Load and merge JSONL entries from one or more log files."""
    entries: list[dict] = []
    for path in log_paths:
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            continue
    return entries


# ── Per-repo statistics ───────────────────────────────────────────────────────

def compute_repo_stats(entries: list[dict]) -> dict[str, dict]:
    """
    Compute per-repo statistics from raw audit log entries.

    Metrics
    -------
    session_count      number of entries for this repo
    distinct_states    number of unique artifact_state values seen
    entropy            distinct_states / session_count  (0..1)
    is_degenerate      entropy < _E1B_MIN_VALID_ENTROPY
    signal_ratio       fraction of entries that recorded at least one signal
    state_breakdown    count per artifact_state value
    gate_blocked_count entries where gate_blocked=True
    first_seen         earliest timestamp in this repo's entries
    last_seen          latest timestamp
    skip_type          'structural' | 'temporary' | None (from policy_provenance)
    lifecycle_capable  True when skip_test_result_check is not set / False when skip=false
    """
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        repo = e.get("repo_name") or "unknown"
        by_repo[repo].append(e)

    stats: dict[str, dict] = {}
    for repo, repo_entries in by_repo.items():
        try:
            repo_entries.sort(key=lambda e: e.get("timestamp", ""))
        except Exception:  # noqa: BLE001
            pass

        n = len(repo_entries)
        states = [e.get("artifact_state", "unknown") for e in repo_entries]
        distinct = len(set(states))
        entropy = round(distinct / n, 4) if n > 0 else 0.0
        is_degenerate = entropy < _E1B_MIN_VALID_ENTROPY

        signals_count = sum(1 for e in repo_entries if e.get("signals"))
        signal_ratio = round(signals_count / n, 4) if n > 0 else 0.0

        state_breakdown: dict[str, int] = defaultdict(int)
        for s in states:
            state_breakdown[s] += 1

        gate_blocked_count = sum(
            1 for e in repo_entries if e.get("gate_blocked")
        )

        timestamps = [
            e.get("timestamp", "") for e in repo_entries if e.get("timestamp")
        ]

        # skip_type: take the most recent non-null value from policy_provenance.
        skip_type: str | None = None
        for e in reversed(repo_entries):
            prov = e.get("policy_provenance") or {}
            st = prov.get("skip_type")
            if st is not None:
                skip_type = st
                break
        # lifecycle_capable: repo is in entropy analysis pool when skip_type is
        # not set (repo-local policy was never skip=true) or when there is no
        # skip declaration at all in the log.
        # Repos with any skip declaration (structural OR temporary) are NOT in
        # the entropy baseline pool.
        has_any_skip = any(
            (e.get("policy_provenance") or {}).get("skip_type") is not None
            for e in repo_entries
        )
        # If no skip_type in any entry, infer from state distribution:
        # purely absent + no signals suggests silent skip.
        # We conservatively keep it in the lifecycle pool if we can't tell.
        lifecycle_capable = not has_any_skip

        stats[repo] = {
            "session_count": n,
            "distinct_states": distinct,
            "entropy": entropy,
            "is_degenerate": is_degenerate,
            "signal_ratio": signal_ratio,
            "state_breakdown": dict(state_breakdown),
            "gate_blocked_count": gate_blocked_count,
            "first_seen": timestamps[0] if timestamps else "unknown",
            "last_seen": timestamps[-1] if timestamps else "unknown",
            "skip_type": skip_type,
            "lifecycle_capable": lifecycle_capable,
        }
    return stats


# ── Fleet coverage layer ──────────────────────────────────────────────────────

# Stale threshold for temporary_skip repos: if adoption debt is older than
# this many days without being resolved, it is flagged as stale.
_TEMPORARY_SKIP_STALE_DAYS: int = 90

# Fleet representativeness threshold: if lifecycle_capable_ratio falls below
# this value, the entropy baseline may not represent fleet reality even when
# Phase 2 gate passes.
_LIFECYCLE_CAPABLE_MIN_RATIO: float = 0.3


def compute_fleet_coverage(repo_stats: dict[str, dict]) -> dict:
    """
    Layer 1: Fleet Coverage summary.

    Reports the structural composition of the fleet without conflating
    governance classification with entropy quality.

    Categories
    ----------
    lifecycle_capable : skip not declared — eligible for entropy analysis
    structural_skip   : skip declared as permanent (non-Python stack, doc repo)
    temporary_skip    : skip declared as provisional (adoption debt)
    unclassified_skip : skip=true but skip_type not declared in log

    Additional signals (hardening layer)
    ------------------------------------
    lifecycle_capable_ratio  : lifecycle_capable_count / total_repos
    baseline_representative  : True when ratio >= _LIFECYCLE_CAPABLE_MIN_RATIO
    structural_skip_inconsistencies : structural repos with observed lifecycle
        activity (signal_ratio > 0 or non-absent state) — policy may be
        dishonest; soft advisory, not a gate blocker
    temporary_skip_aging     : per-repo adoption-debt age; flags stale entries
        (age_days > _TEMPORARY_SKIP_STALE_DAYS without becoming lifecycle-capable)
    """
    total = len(repo_stats)
    lifecycle_capable = [r for r, s in repo_stats.items() if s["lifecycle_capable"]]
    structural_skip = [
        r for r, s in repo_stats.items()
        if not s["lifecycle_capable"] and s["skip_type"] == "structural"
    ]
    temporary_skip = [
        r for r, s in repo_stats.items()
        if not s["lifecycle_capable"] and s["skip_type"] == "temporary"
    ]
    unclassified_skip = [
        r for r, s in repo_stats.items()
        if not s["lifecycle_capable"] and s["skip_type"] is None
    ]

    lifecycle_capable_ratio = round(
        len(lifecycle_capable) / total if total > 0 else 0.0, 4
    )
    baseline_representative = lifecycle_capable_ratio >= _LIFECYCLE_CAPABLE_MIN_RATIO

    # structural_skip consistency check:
    # A structural skip repo should never show lifecycle activity.
    # observation data contradicting the skip_type declaration is a signal
    # that the label may have been used to escape governance pressure.
    structural_skip_inconsistencies: list[dict] = []
    for r in structural_skip:
        s = repo_stats[r]
        has_non_absent = any(state != "absent" for state in s["state_breakdown"])
        if s["signal_ratio"] > 0 or has_non_absent:
            structural_skip_inconsistencies.append({
                "repo": r,
                "signal_ratio": s["signal_ratio"],
                "states": s["state_breakdown"],
                "advisory": (
                    "structural_skip declared but lifecycle activity observed; "
                    "verify skip_type is correct"
                ),
            })

    # temporary_skip aging: track how long adoption debt has been outstanding.
    # temporary skip is a provisional state — it should eventually become
    # lifecycle_capable. Stale entries indicate unresolved adoption gaps.
    today = datetime.date.today()
    temporary_skip_aging: list[dict] = []
    for r in temporary_skip:
        s = repo_stats[r]
        first = s.get("first_seen", "unknown")
        age_days: int | None = None
        try:
            if first and first != "unknown":
                first_d = datetime.date.fromisoformat(first[:10])
                age_days = (today - first_d).days
        except (ValueError, TypeError):
            pass
        stale = age_days is not None and age_days > _TEMPORARY_SKIP_STALE_DAYS
        temporary_skip_aging.append({
            "repo": r,
            "first_seen": first,
            "age_days": age_days,
            "stale": stale,
        })

    return {
        "total_repos": total,
        "lifecycle_capable": lifecycle_capable,
        "structural_skip": structural_skip,
        "temporary_skip": temporary_skip,
        "unclassified_skip": unclassified_skip,
        "lifecycle_capable_count": len(lifecycle_capable),
        "structural_skip_count": len(structural_skip),
        "temporary_skip_count": len(temporary_skip),
        "unclassified_skip_count": len(unclassified_skip),
        "lifecycle_capable_ratio": lifecycle_capable_ratio,
        "baseline_representative": baseline_representative,
        "structural_skip_inconsistencies": structural_skip_inconsistencies,
        "temporary_skip_aging": temporary_skip_aging,
    }


# ── Phase 2 readiness gate ────────────────────────────────────────────────────

def evaluate_phase2_gate(
    entries: list[dict],
    repo_stats: dict[str, dict],
    min_sessions: int,
    min_repos: int,
    min_nondegenerate_ratio: float,
    max_dominance: float,
    min_unique_pattern_ratio: float,
) -> dict:
    """
    Evaluate whether the accumulated observation pool satisfies Phase 2 gate.

    IMPORTANT: this gate operates ONLY on lifecycle-capable repos (skip=false).
    Structural/temporary skip repos are excluded from entropy baseline analysis.
    Fleet composition is reported separately in compute_fleet_coverage().

    Phase 3 (trigger design) must not start until this gate is READY.
    """
    # Filter to lifecycle-capable repos only (skip repos excluded from entropy pool).
    lc_stats = {r: s for r, s in repo_stats.items() if s["lifecycle_capable"]}
    lc_entries = [
        e for e in entries
        if (e.get("repo_name") or "unknown") in lc_stats
    ]
    total_sessions = sum(s["session_count"] for s in lc_stats.values())
    repo_count = len(lc_stats)
    degenerate_repos = sum(
        1 for s in lc_stats.values() if s["is_degenerate"]
    )
    nondegenerate_repos = repo_count - degenerate_repos
    nondegenerate_ratio = (
        round(nondegenerate_repos / repo_count, 4) if repo_count > 0 else 0.0
    )
    max_sessions_any = max(
        (s["session_count"] for s in lc_stats.values()), default=0
    )
    max_dominance_actual = (
        round(max_sessions_any / total_sessions, 4) if total_sessions > 0 else 0.0
    )

    # Unique session pattern ratio: distinct fingerprints / total sessions.
    # Guards against pseudo-diversity — 3 repos all running the same lifecycle
    # pattern look like repos=3, but the pool has pattern_ratio near 0.
    fingerprints = [_session_fingerprint(e) for e in lc_entries]
    unique_patterns = len(set(fingerprints))
    unique_pattern_ratio = (
        round(unique_patterns / total_sessions, 4) if total_sessions > 0 else 0.0
    )

    # Degenerate rate interpretation — advisory, not a gate blocker.
    # degenerate_rate near 0 is NOT automatically good:
    #   it may mean broken-pipeline / skip-abuse patterns are never observed.
    degenerate_rate = (
        round(degenerate_repos / repo_count, 4) if repo_count > 0 else 0.0
    )
    if degenerate_rate < 0.05:
        degen_interp = (
            "low (<0.05) — coverage review required: confirm this reflects "
            "genuine stability, not missing broken-pipeline / skip-abuse "
            "observations; absence of degenerate sessions is not inherently bad"
        )
    elif degenerate_rate <= 0.30:
        degen_interp = "expected mixed (0.05–0.30) — normal range"
    else:
        degen_interp = (
            "high (>0.30) — possible systemic instability "
            "or persistently unhealthy lifecycle patterns"
        )

    checks: dict[str, dict] = {
        "min_sessions": {
            "label": "total sessions ≥ N",
            "required": min_sessions,
            "actual": total_sessions,
            "pass": total_sessions >= min_sessions,
        },
        "min_repos": {
            "label": "distinct repos ≥ M",
            "required": min_repos,
            "actual": repo_count,
            "pass": repo_count >= min_repos,
        },
        "min_nondegenerate_ratio": {
            "label": "non-degenerate repos ≥ ratio",
            "required": min_nondegenerate_ratio,
            "actual": nondegenerate_ratio,
            "pass": nondegenerate_ratio >= min_nondegenerate_ratio,
        },
        "max_repo_dominance": {
            "label": "dominant repo fraction ≤ limit",
            "required": max_dominance,
            "actual": max_dominance_actual,
            "pass": max_dominance_actual <= max_dominance,
        },
        "unique_pattern_ratio": {
            "label": "unique session patterns ≥ ratio",
            "required": min_unique_pattern_ratio,
            "actual": unique_pattern_ratio,
            "pass": unique_pattern_ratio >= min_unique_pattern_ratio,
        },
    }

    all_pass = all(c["pass"] for c in checks.values())
    return {
        "verdict": "READY" if all_pass else "NOT_READY",
        "total_sessions": total_sessions,
        "repo_count": repo_count,
        "degenerate_repos": degenerate_repos,
        "nondegenerate_ratio": nondegenerate_ratio,
        "max_repo_dominance": max_dominance_actual,
        "unique_patterns": unique_patterns,
        "unique_pattern_ratio": unique_pattern_ratio,
        "degenerate_rate": degenerate_rate,
        "degenerate_rate_interpretation": degen_interp,
        "checks": checks,
    }


# ── Percentile helper ─────────────────────────────────────────────────────────

def _percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = min(int(len(sorted_v) * pct / 100), len(sorted_v) - 1)
    return round(sorted_v[idx], 4)


# ── Human-readable output ─────────────────────────────────────────────────────

def _print_human(
    stats: dict[str, dict],
    fleet: dict,
    gate: dict,
    log_paths: list[Path],
) -> None:
    sep = "─" * 72

    print(sep)
    print("  E1b Phase 2 — Distribution Analysis")
    print(sep)
    print(f"  log source(s) : {', '.join(str(p) for p in log_paths)}")
    print(
        f"  total entries : {sum(s['session_count'] for s in stats.values())}"
    )
    print(f"  distinct repos: {len(stats)}")
    print()

    # ── Layer 1: Fleet Coverage ───────────────────────────────────────────────
    lc_ratio = fleet["lifecycle_capable_ratio"]
    lc_ratio_advisory = (
        f"  [ADVISORY] ratio={lc_ratio:.2f} < {_LIFECYCLE_CAPABLE_MIN_RATIO:.2f}: "
        f"baseline may not represent fleet"
        if not fleet["baseline_representative"] else ""
    )
    print("  ┌── Layer 1: Fleet Coverage ─────────────────────────────────────┐")
    print(f"  │  total repos              : {fleet['total_repos']}")
    print(
        f"  │  lifecycle_capable        : {fleet['lifecycle_capable_count']}  "
        f"{fleet['lifecycle_capable']}"
    )
    print(
        f"  │  lifecycle_capable_ratio  : {lc_ratio:.4f}  "
        + ("[OK]" if fleet["baseline_representative"] else
           f"[LOW] < {_LIFECYCLE_CAPABLE_MIN_RATIO}: baseline not representative of fleet")
    )
    if fleet["structural_skip"]:
        print(
            f"  │  structural_skip          : {fleet['structural_skip_count']}  "
            f"{fleet['structural_skip']}"
        )
    else:
        print(f"  │  structural_skip          : 0")
    if fleet["temporary_skip"]:
        print(
            f"  │  temporary_skip           : {fleet['temporary_skip_count']}  "
            f"{fleet['temporary_skip']}"
        )
    else:
        print(f"  │  temporary_skip           : 0")
    if fleet["unclassified_skip"]:
        print(
            f"  │  unclassified_skip        : {fleet['unclassified_skip_count']}  "
            f"{fleet['unclassified_skip']}  <- add skip_type to gate_policy.yaml"
        )
    # structural_skip consistency advisory
    if fleet["structural_skip_inconsistencies"]:
        print("  │")
        print("  │  [ADVISORY] structural_skip inconsistencies detected:")
        for item in fleet["structural_skip_inconsistencies"]:
            states_str = "  ".join(
                f"{k}:{v}" for k, v in sorted(item["states"].items())
            )
            print(
                f"  │    {item['repo']}: signal_ratio={item['signal_ratio']:.4f}  "
                f"states={states_str}"
            )
            print(f"  │      -> {item['advisory']}")
    # temporary_skip aging table
    if fleet["temporary_skip_aging"]:
        print("  │")
        print("  │  temporary_skip aging (adoption debt tracker):")
        for item in fleet["temporary_skip_aging"]:
            age_str = f"{item['age_days']}d" if item["age_days"] is not None else "unknown"
            stale_tag = "  [STALE >90d]" if item["stale"] else ""
            print(
                f"  │    {item['repo']:<30} first_seen={item['first_seen'][:10]}  "
                f"age={age_str}{stale_tag}"
            )
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    # ── Layer 2: Entropy Quality (lifecycle-capable repos only) ───────────────
    lc_stats = {r: s for r, s in stats.items() if s["lifecycle_capable"]}
    excluded = len(stats) - len(lc_stats)
    excluded_note = (
        f" ({excluded} repo{'s' if excluded != 1 else ''} with "
        f"structural/temporary skip excluded)"
        if excluded > 0 else ""
    )
    print(
        f"  ┌── Layer 2: Entropy Quality (lifecycle-capable repos only){excluded_note}"
    )
    print("  │")

    if not lc_stats:
        print("  │  (no lifecycle-capable repos in pool)")
        print("  └────────────────────────────────────────────────────────────────┘")
    else:
        # Per-repo table (lifecycle-capable only)
        col_w = max((len(r) for r in lc_stats), default=4) + 2
        col_w = max(col_w, 20)
        hdr = (
            f"  │  {'repo':<{col_w}} {'sessions':>8} {'entropy':>8} "
            f"{'sig_ratio':>9} {'degenerate':>11}  states"
        )
        print(hdr)
        print(
            f"  │  {'─'*col_w} {'─'*8} {'─'*8} {'─'*9} {'─'*11}  {'─'*20}"
        )
        for repo, s in sorted(
            lc_stats.items(), key=lambda kv: kv[1]["session_count"], reverse=True
        ):
            degen_mark = "YES(!!)" if s["is_degenerate"] else "no"
            state_str = "  ".join(
                f"{k}:{v}" for k, v in sorted(s["state_breakdown"].items())
            )
            print(
                f"  │  {repo:<{col_w}} {s['session_count']:>8} {s['entropy']:>8.4f} "
                f"{s['signal_ratio']:>9.4f} {degen_mark:>11}  {state_str}"
            )

        entropies = [s["entropy"] for s in lc_stats.values()]
        signal_ratios = [s["signal_ratio"] for s in lc_stats.values()]
        degenerate_count = sum(1 for s in lc_stats.values() if s["is_degenerate"])
        degenerate_pct = int(degenerate_count / len(lc_stats) * 100)
        print("  │")
        print("  │  Distribution (lifecycle-capable repos):")
        print(
            f"  │    entropy   — median={_percentile(entropies, 50):.4f}  "
            f"p90={_percentile(entropies, 90):.4f}  "
            f"p95={_percentile(entropies, 95):.4f}"
        )
        print(
            f"  │    sig_ratio — median={_percentile(signal_ratios, 50):.4f}  "
            f"p90={_percentile(signal_ratios, 90):.4f}  "
            f"p95={_percentile(signal_ratios, 95):.4f}"
        )
        print(
            f"  │    degenerate repos: {degenerate_count}/{len(lc_stats)} ({degenerate_pct}%)"
        )
        print(
            f"  │    unique patterns : {gate['unique_patterns']}/{gate['total_sessions']} "
            f"(ratio={gate['unique_pattern_ratio']:.4f})"
        )
        degen_interp = gate.get("degenerate_rate_interpretation", "")
        if degen_interp:
            print(
                f"  │    degenerate_rate : {gate['degenerate_rate']:.4f}  [{degen_interp}]"
            )
        print("  │")

        # Phase 2 readiness gate
        verdict = gate["verdict"]
        verdict_label = "READY" if verdict == "READY" else "NOT_READY"
        verdict_marker = "[OK]" if verdict == "READY" else "[NO]"
        print(f"  │  Phase 2 Readiness Gate — {verdict_marker} {verdict_label}")
        for check in gate["checks"].values():
            mark = "  │    [OK]" if check["pass"] else "  │    [NO]"
            print(
                f"{mark}  {check['label']:<36} "
                f"required={check['required']}  "
                f"actual={check['actual']}"
            )
        # baseline representativeness advisory (post-gate)
        if not fleet["baseline_representative"]:
            print("  │")
            lc_r = fleet["lifecycle_capable_ratio"]
            lc_n = fleet["lifecycle_capable_count"]
            tot = fleet["total_repos"]
            print(
                f"  │  [ADVISORY] lifecycle_capable_ratio={lc_r:.4f} "
                f"< {_LIFECYCLE_CAPABLE_MIN_RATIO:.2f}:"
            )
            print(
                f"  │    only {lc_n}/{tot} repos are lifecycle-capable;"
            )
            print(
                "  │    a READY verdict here reflects quality of a narrow subset,"
            )
            print(
                "  │    not fleet-wide lifecycle health. "
                "E1b != adoption completeness."
            )
        print("  └────────────────────────────────────────────────────────────────┘")
    print(sep)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="E1b Phase 2: Distribution Analysis + Readiness Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/analyze_e1b_distribution.py\n"
            "  python scripts/analyze_e1b_distribution.py --json\n"
            "  python scripts/analyze_e1b_distribution.py \\\n"
            "    --log-path ../repo-a/artifacts/runtime/canonical-audit-log.jsonl \\\n"
            "               ../repo-b/artifacts/runtime/canonical-audit-log.jsonl\n"
        ),
    )
    parser.add_argument(
        "--log-path",
        nargs="+",
        metavar="PATH",
        help=(
            f"Path(s) to canonical-audit-log.jsonl "
            f"(default: {_DEFAULT_LOG_PATH})"
        ),
    )
    parser.add_argument(
        "--min-sessions",
        type=int,
        default=_PHASE2_MIN_SESSIONS,
        metavar="N",
        help=f"Min total sessions for Phase 2 gate (default: {_PHASE2_MIN_SESSIONS})",
    )
    parser.add_argument(
        "--min-repos",
        type=int,
        default=_PHASE2_MIN_REPOS,
        metavar="M",
        help=f"Min distinct repos for Phase 2 gate (default: {_PHASE2_MIN_REPOS})",
    )
    parser.add_argument(
        "--min-nondegenerate",
        type=float,
        default=_PHASE2_MIN_NONDEGENERATE_RATIO,
        metavar="R",
        help=(
            f"Min non-degenerate repo fraction (default: "
            f"{_PHASE2_MIN_NONDEGENERATE_RATIO})"
        ),
    )
    parser.add_argument(
        "--max-dominance",
        type=float,
        default=_PHASE2_MAX_REPO_DOMINANCE,
        metavar="R",
        help=(
            f"Max fraction any one repo can hold (default: "
            f"{_PHASE2_MAX_REPO_DOMINANCE})"
        ),
    )
    parser.add_argument(
        "--min-unique-pattern",
        type=float,
        default=_PHASE2_MIN_UNIQUE_PATTERN_RATIO,
        metavar="R",
        help=(
            f"Min unique session pattern ratio — guards pseudo-diversity "
            f"(default: {_PHASE2_MIN_UNIQUE_PATTERN_RATIO})"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit machine-readable JSON output",
    )
    args = parser.parse_args()

    log_paths = (
        [Path(p) for p in args.log_path]
        if args.log_path
        else [_DEFAULT_LOG_PATH]
    )

    entries = _load_entries(log_paths)

    if not entries:
        if args.emit_json:
            print(json.dumps({"repos": {}, "phase2_gate": {
                "verdict": "NOT_READY",
                "total_sessions": 0,
                "repo_count": 0,
                "note": "no entries found",
            }}, indent=2))
        else:
            print("No entries found. Log is empty or all paths missing.")
            print(f"  searched: {', '.join(str(p) for p in log_paths)}")
        return 0

    repo_stats = compute_repo_stats(entries)
    fleet = compute_fleet_coverage(repo_stats)
    gate = evaluate_phase2_gate(
        entries,
        repo_stats,
        min_sessions=args.min_sessions,
        min_repos=args.min_repos,
        min_nondegenerate_ratio=args.min_nondegenerate,
        max_dominance=args.max_dominance,
        min_unique_pattern_ratio=args.min_unique_pattern,
    )

    if args.emit_json:
        print(json.dumps(
            {"repos": repo_stats, "fleet_coverage": fleet, "phase2_gate": gate},
            indent=2,
        ))
        return 0

    _print_human(repo_stats, fleet, gate, log_paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
