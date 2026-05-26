# Fleet Governance v1 Closing Statement — 2026-05-26

## Final State

- required_verified: 9/10
- scope-normalized ratio: 0.9
- baseline snapshot: governance_repo_matrix_snapshot_20260526_153232
- remaining required blocker: Kernel-Driver-Contract (domain authority coexistence problem)
- schema changes this session: none
- evidence contract changes: none

---

## Confirmed Capabilities (verified through actual execution)

**Signal detection (7 signals, stable)**
- hooks / fw / agents / dirty_ok / evidence / head_ok / ts_ok
- Consistent across 20 repos; matrix is repeatable

**evidence_tier differentiation (working)**
- `ev_tier` column visible per repo in all snapshots (tier_2 / tier_3 / ci_strict / unknown)
- hardware repos (tier_3) do not require test_result gate
- gate_blocked=True entries correctly rejected (governance gap at 3/10 closed)

**agents_calibration (working with documented boundary)**
- scaffold → repo_specific_minimal transition validated via `<!-- governance:key=... -->` markers
- Reliable for standard repos
- Domain contract repos (Kernel-Driver-Contract) have a documented semantic conflict — agents=scaffold is expected and documented, not a deficiency

**self-governance (verified with semantic caveat)**
- ai-governance-framework is repo_native_verified
- `_self_reference_note` in framework.lock.json preserves semantic boundary: verified = admissible evidence chain, not framework correctness

**Repeatable onboarding path (verified on 8 repos)**
- `hooks + framework.lock + fresh closeout + dirty_explained`
- No schema changes required; path is stable

---

## Needs Design Decision (cannot proceed without selection)

**Kernel-Driver-Contract 10/10**
- Blocker: agents_calibration checker reads AGENTS.md only; domain contract repos need alternate lookup path
- Preferred path: Option A (separate files: AGENTS.md domain authority + governance/fleet.AGENTS.md calibration + contract.yaml boundary declaration)
- Prerequisite: confirm checker support before any file edits
- If checker does not support alternate path: write framework capability plan first; do not pursue 10/10 until capability is confirmed
- See: docs/fleet/plan_10of10_kernel_driver_contract.md

---

## Confirmed Pending (one item, concrete)

**PS1 matrix script auto-append to trend.jsonl**
- Add one line per matrix run to scope_normalized_trend.jsonl
- Add dirty_true_count field to each entry
- This is the direct fix for Pattern 2 (tracking mechanisms dropped under acceleration)
- Once this is done, the "framework has no enforcement for its own tracking" observation is resolved
- If recording gaps still occur after automation, re-evaluate whether deeper enforcement is needed

---

## Observations With Explicit Disposition

| Observation | Disposition |
|---|---|
| cli ev_tier=unknown | Not a verified-path blocker; no action until a second ev_tier=unknown repo with different behavior appears |
| 4/10 / 5/10 checkpoint docs missing | Gap recorded in trend.jsonl; backfill deliberately withheld; acceptable |
| Four-state evidence model | Rejected — over-engineering at this fleet size; admissibility filter function is sufficient |
| Verified semantic disclaimer | Dismissed — ev_tier column already provides per-repo quality context; no extra label needed |
| v2 contract direction | Deferred — wait for trend data from several sessions; use data to decide, not analysis alone |

---

## Design Patterns Carried Forward to v2

Recorded in memory/00_long_term.md. Summary:

1. **Analysis outpaces absorption** — mechanical fixes drove 3/10→9/10, not architecture. Start from minimum viable change.
2. **Manual tracking is dropped under pressure** — the PS1 automation fix addresses the symptom; the underlying principle is that governance designed for others must be tested against your own behavior under load.
3. **Best discoveries come from collisions** — gate_blocked, agents dominance, domain authority conflict, dirty dependency were all unplanned. v2 should strengthen the framework's ability to surface surprises, not add more pre-emptive rules.
