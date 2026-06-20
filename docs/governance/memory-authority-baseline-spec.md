# Memory Authority Baseline-Banking Spec v0.1

Status: reviewer-facing design spec. Advisory / read-layer only — no enforcement.

Derived from:
- `governance_tools/memory_authority_guard.py` (violation source)
- `artifacts/governance/checkpoint-memory-baseline-2026-06-19.json` (baseline format precedent)
- `governance_tools/checkpoint_memory_baseline_compare.py` (compare-model precedent)
- `docs/governance/checkpoint-memory-audit-spec.md` (sibling spec house style)

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

## 1. Frozen baseline snapshot format (mirrors checkpoint-memory baseline)

```jsonc
{
  "schema_version": "0.1",
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
    "by_disposition": { "baseline_debt": "<count>", "structural_candidate": "<count>" }  // illustrative shape; counts filled by cut2
  },
  "dispositions": [
    { "code": "unbound_memory", "disposition": "baseline_debt", "reason": "...",
      "subjects": [ { "identity_key": "<hash>", "display": "memory/2026-04-10.md#entry-2" } ] }
  ]
}
```

## 2. Identity key (stable across edits)

Guard violations do **not** share a uniform `subject` field — they carry
`file` / `entry` / `section` / `date` / `reason`. A naive `(code, subject)` key
collapses multiple entries in one file and re-flips on edits. Therefore:

```
identity_key = hash(normalized(code, file, entry | section | date | reason))
```

- `normalized(...)` lowercases/strips and selects the available locating fields
  for that violation class (e.g. `unbound_memory` → file + entry; `read_error`
  → file + reason).
- A human-readable `subject` / `display` string is carried **only for display**,
  never used as the matching key.
- Open: the exact per-class field selection is pinned in cut2 against the real
  guard output (see §6).

## 3. Disposition rules — baselineable vs always-fresh

The dividing line is **"is this an active enforcement/blocker signal?"** If yes,
it is unconditionally always-fresh (never suppressed, even if it existed at
snapshot time). If it is an observation/warning, it is baselineable: existing
instances become `baseline_debt`; instances appearing after the baseline are
reported as new drift.

| class | kind | in baseline? |
|---|---|---|
| historical `unbound_memory` | baselineable | existing → `baseline_debt`; new → drift |
| historical `non_canonical_writer` | baselineable | existing → `baseline_debt`; new → drift |
| `structural_memory_auto_write` | baselineable | existing → `structural_candidate`; new → drift |
| `missing_canonical_memory` | baselineable | existing → `baseline_debt`; new → drift |
| **`read_error` / malformed** | baselineable | **existing → `baseline_debt`; new → drift** |
| **`active_non_canonical_writer`** | **always-fresh** | **never — full count, even if pre-existing** |
| current-diff active non-canonical writer | always-fresh | never |
| any future blocker-class signal | always-fresh | never |

> Correction vs draft: `read_error` is **not** unconditionally always-fresh. Only
> active enforcement classes are. A `read_error` already present at snapshot time
> is legitimate baseline debt; only a `read_error` that appears *after* the
> baseline is new drift.

## 4. Hard invariants (prevent banking an active signal)

```
SI-1  always-fresh classes are computed OUTSIDE baseline subtraction — they never
      pass through suppression, so a blocker can never be hidden by a baseline.
SI-2  writing a baseline is REFUSED if active_non_canonical_writer > 0 at snapshot
      time (cannot freeze an active blocker into historical debt).
SI-3  the baseline absorbs only subjects that (a) exist at snapshot time and
      (b) belong to a baselineable class; any new subject is new-since-baseline.
```

## 5. Report shape (answers all five questions)

```
total_historical_debt   = baseline.summary.total
current_total           = rerun guard total
suppressed_by_baseline  = current ∩ baseline, disposition ∈ baselineable
new_since_baseline      = baselineable-class subjects in current not in baseline
active_fresh_findings   = always-fresh classes, full count (never suppressed; SI-1)
```

Human one-liner (so reviewers read "new + active", not "322"):

```
[memory-authority-baseline] new=<N> | active=<M> | suppressed=<K> | current_total=<T> | baseline=<B>
```

## 6. Open questions for cut2 (NOT resolved here)

1. **Per-class identity field selection**: pin `normalized(...)` field sets per
   violation class against real guard JSON so historical debt matches stably and
   file edits do not spuriously flip entries to "new".
2. **Debt-shrink detection**: if `current_total < suppressed_by_baseline` (debt
   was resolved), the report should flag "baseline can be re-frozen smaller" so
   the baseline does not stay permanently oversized.
3. **Interpretation-source doc**: whether to add
   `docs/governance/memory-debt-disposition.md` (mirroring
   `commit-memory-binding-contract.md`) to carry disposition reasons.

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
  - that the per-class identity-key field selection is finalized (cut2)
```
