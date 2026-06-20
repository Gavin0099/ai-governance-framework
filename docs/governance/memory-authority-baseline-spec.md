# Memory Authority Baseline-Banking Spec v0.2

Status: reviewer-facing design spec. Advisory / read-layer only — no enforcement.

Derived from:
- `governance_tools/memory_authority_guard.py` (violation source)
- `artifacts/governance/checkpoint-memory-baseline-2026-06-19.json` (baseline format precedent)
- `governance_tools/checkpoint_memory_baseline_compare.py` (compare-model precedent)
- `docs/governance/checkpoint-memory-audit-spec.md` (sibling spec house style)

> **v0.2 change**: per-record identity was proven non-viable against real guard
> output (48% of records collide on the available fields — see §2). The model is
> now **count-bucket banking** (per-key counts, not per-record ids).

This spec defines a **baseline-banking read layer above** `memory_authority_guard`.
Its purpose is to turn the guard's standing "322 total warnings" into
"new-since-baseline + active", so the advisory surface stops drowning in frozen
historical debt (warning fatigue). It does **not** change the guard, enforcement,
or memory content.

## 0. Boundary (what this is / is not)

- It is a **separate read/report layer**: it loads a frozen baseline, reruns the
  guard, and reports deltas. The guard keeps emitting its full findings unchanged.
- It is **advisory / not_enforcement**: `blocking=false`, never a gate input.
- It does **not** delete, edit, or "clean up" historical debt in `memory/`.

## 1. Frozen baseline snapshot format (count-bucket)

```jsonc
{
  "schema_version": "0.2",
  "model": "count_bucket",  // per-key counts, NOT per-record ids (see §2)
  "baseline_id": "memory-authority-baseline-YYYY-MM-DD",
  "created_at": "<iso>",
  "source_command": "python -m governance_tools.memory_authority_guard --format json",
  "source_head": "<commit>",
  "claim_class": "advisory",
  "blocking": false,
  "not_enforcement": true,
  "baseline_purpose": "Freeze current memory-authority warning debt so reviews see new drift, not 322 total.",
  "baseline_interpretation_source": "docs/governance/<memory-debt-disposition>.md",
  "safety_invariant": "active_non_canonical_writer is NEVER part of this baseline; asserted at write time (SI-2).",
  "summary": {
    "total": 322,
    "by_code": { "unbound_memory": 229, "non_canonical_writer": 86, "structural_memory_auto_write": 6, "missing_canonical_memory": 1 },
    "by_disposition": { "baseline_debt": "<count>", "structural_candidate": "<count>" }  // illustrative; counts filled by cut2
  },
  "buckets": [
    { "identity_key": "<hash>", "code": "unbound_memory", "disposition": "baseline_debt",
      "count": 14, "reason": "no_anchor",
      "display": "2026-05-05.md · entry='- memory_type: session-derived' · no_anchor" }
  ]
}
```

The baseline stores, per `identity_key`, the **count** of matching violations at
snapshot time. It does not store per-record ids.

## 2. Identity key = count-bucket key (per-record identity is not viable)

Per-record identity was tested against real guard output and **fails**:

```
322 violations  →  189 unique (code,file,entry,section,date,reason) tuples
23 keys collide, covering 156 records (~48%)
worst: 22 non_canonical_writer in 2026-05-05.md share ONE key
```

Cause: the guard's `entry` field is only the entry **header line** (e.g.
`- memory_type: session-derived`), which repeats for every entry of that type in
a daily file. A stable per-record id is impossible without the guard emitting a
richer locator (line number / full-entry hash) — and that is a guard change,
**out of scope**.

**Resolution — bank counts per bucket key:**

```
identity_key = hash(normalized(<per-class fields>))
baseline:   identity_key -> count
```

Pinned per-class fields (from real guard JSON; resolves former §6 open #1):

| code | identity fields | notes |
|---|---|---|
| `unbound_memory` | code, file, entry, reason | `entry` may be null; `reason` carries the `read_error:` subtype |
| `non_canonical_writer` | code, file, entry, reason | `entry` = header line (drives the collisions above) |
| `structural_memory_auto_write` | code, file, section, reason | `section` heading = stable |
| `missing_canonical_memory` | code, date, reason | `date` = stable natural key |

- `normalized(...)` lowercases/strips and selects the present fields for that class.
- `display` is human-readable only, never used for matching.
- **Tradeoff (record):** count-banking reports "N added in this bucket" but
  **cannot name the exact individual entry**. Acceptable for an advisory
  warning-fatigue layer; per-entry pinpointing would require a guard change.

## 3. Disposition rules — baselineable vs always-fresh

The dividing line is **"is this an active enforcement/blocker signal?"** If yes,
it is unconditionally always-fresh (never suppressed, even if it existed at
snapshot time). Otherwise it is baselineable: the snapshot count is debt; counts
above the snapshot are new drift.

| class | kind | in baseline? |
|---|---|---|
| `unbound_memory` | baselineable | snapshot count → `baseline_debt`; excess → drift |
| `non_canonical_writer` | baselineable | snapshot count → `baseline_debt`; excess → drift |
| `structural_memory_auto_write` | baselineable | snapshot count → `structural_candidate`; excess → drift |
| `missing_canonical_memory` | baselineable | snapshot count → `baseline_debt`; excess → drift |
| `read_error` (**`unbound_memory` reason subtype**, not a code) | baselineable | snapshot count → `baseline_debt`; excess → drift |
| **`active_non_canonical_writer`** | **always-fresh** | **never — full count, even if pre-existing** |
| any future blocker-class signal | always-fresh | never |

> `read_error` is identified by `code=unbound_memory` **plus a `reason` starting
> with `read_error:`** — there is no top-level `read_error` code. Because `reason`
> is part of the bucket key, read_error entries bucket separately and follow the
> same baselineable (snapshot=debt / excess=drift) rule automatically.

## 4. Hard invariants (prevent banking an active signal)

```
SI-1  always-fresh classes are computed OUTSIDE baseline subtraction — they never
      pass through suppression, so a blocker can never be hidden by a baseline.
SI-2  writing a baseline is REFUSED if active_non_canonical_writer > 0 at snapshot
      time (cannot freeze an active blocker into historical debt).
SI-3  per baselineable key, only the snapshot count is debt; any count above the
      snapshot count is new-since-baseline.
```

SI-1 holds **by construction**: `active_non_canonical_writer` is a separate
top-level guard field (`{count, violations, mode: report_only}`), structurally
outside the `violations` list the baseline operates on.

## 5. Report shape (count-delta; answers all five questions)

```
total_historical_debt   = baseline.summary.total
current_total           = rerun guard total
suppressed_by_baseline  = Σ min(current_count[key], baseline_count[key])   over baselineable keys
new_since_baseline      = Σ max(0, current_count[key] - baseline_count[key]) over baselineable keys
active_fresh_findings   = always-fresh classes (top-level active_non_canonical_writer
                          + future blockers), full count (never suppressed; SI-1)
```

Human one-liner (so reviewers read "new + active", not "322"):

```
[memory-authority-baseline] new=<N> | active=<M> | suppressed=<K> | current_total=<T> | baseline=<B>
```

## 6. Open questions for cut2 (NOT resolved here)

1. **Debt-shrink hint**: the `max(0, …)` formula already tolerates shrinkage
   (resolved debt → `new=0`, `suppressed=current`). The report should additionally
   *flag* when `current_total < baseline.total` so the baseline can be re-frozen
   smaller rather than staying permanently oversized.
2. **Interpretation-source doc**: whether to add
   `docs/governance/memory-debt-disposition.md` (mirroring
   `commit-memory-binding-contract.md`) to carry per-bucket disposition reasons.

## Claim ceiling

```yaml
claim_ceiling:
  - reviewer-facing design spec only
  - advisory / read-layer above the guard; not enforcement
  - no guard behavior change; guard still emits full findings
  - no blocker, no gate input, no enforcement change
  - no historical cleanup of memory/ debt
  - no baseline artifact generated by this spec
not_claimed:
  - that warning debt is reduced (only re-framed as new-vs-baseline)
  - that active_non_canonical_writer can ever be baseline-suppressed (SI-1/SI-2 forbid it)
  - that individual new entries can be pinpointed (count-banking reports per-bucket added count only)
```
