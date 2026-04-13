# E1a Tech Spec — Canonical Usage Auditability

> Status: draft — pending implementation approval  
> Prereqs locked: E6 / E7 / E8a / E8b

---

## Problem

E7 answers: "Did this session leave a canonical interpretation footprint?"  
E8b answers: "Does the multi-session history show a trend of adoption gaps?"

Neither produces a unified reviewer-facing signal that synthesises both dimensions
into a single answer:

> "In this session, was canonical interpretation usage observed — and does the
> historical context change the picture?"

A reviewer reading session output currently has to cross-reference two separate
advisory blocks (`canonical_path_audit` from E7, `canonical_audit_trend` from E8b)
and perform the synthesis manually.  There is no single field that names the
combined state.

---

## Target Outcome

Add a new `canonical_usage_audit` result key to `run_session_end_hook` that:

- synthesises the already-computed E7 single-session footprint and E8b multi-session
  trend into a single `usage_status` + `usage_note`
- is always `advisory_only=True` and NEVER influences `gate.blocked`
- requires no new I/O, no new config, and no new dependencies — all inputs are
  already available in the result pipeline

---

## Scope

### In scope

1. New pure function `_build_canonical_usage_audit(canonical_path_audit, canonical_audit_trend) -> dict`  
   — deterministic synthesis from two already-computed dicts; no side effects

2. New result key `canonical_usage_audit` in `run_session_end_hook` (added after
   `_compute_canonical_audit_trend`, reads from both E7 and E8b outputs)

3. New display block in `format_human_result` — shows `usage_status` + `[ADVISORY]`
   line when status is not `observed`

4. `tests/test_e1a_canonical_usage_audit.py` — 5 focused tests (see Evidence plan)

---

## Non-Goals

- NOT `gate.blocked` influence — `usage_status` must never feed any blocking path
- NOT E1b (enforcement) — E1a is observability only
- NOT ingestor invocation tracking — we observe footprint presence, not call sites
- NOT new I/O — `_build_canonical_usage_audit` is a pure dict-in / dict-out function
- NOT new `gate_policy.yaml` config — derivation is deterministic from E7+E8b; no
  threshold or window parameters needed
- NOT merging or replacing `canonical_path_audit` or `canonical_audit_trend` —
  both remain as independent keys; `canonical_usage_audit` is additive

---

## Affected Surfaces

| Surface | Change |
|---------|--------|
| `governance_tools/session_end_hook.py` | new `_build_canonical_usage_audit()` + wire-in + `format_human_result` display |
| `governance_tools/gate_policy.py` | **none** |
| `governance/gate_policy.yaml` | **none** |
| `tests/test_e1a_canonical_usage_audit.py` | **new** — 5 tests |

Public API: `run_session_end_hook` result gains one additive key.  No existing keys
are renamed or modified.  All callers that do not read `canonical_usage_audit` are
unaffected.

---

## `canonical_usage_audit` Schema

```python
{
    # Sourced from E7 (canonical_path_audit)
    "artifact_present":       bool,
    "canonical_key_present":  bool,   # == failure_disposition_key_present
                                      # Means: artifact contains the canonical
                                      # ingestor marker key.  Does NOT assert
                                      # that the ingestor was called; only that
                                      # the artifact looks like ingestor output.

    # Sourced from E8b (canonical_audit_trend)
    "trend_adoption_risk":  bool,
    "trend_signal_ratio":   float,        # rounded 4 decimals

    # Synthesis
    "usage_status":  str,    # "observed" | "missing"
                             # | "observed_with_trend_risk" | "trend_risk_context"
    "usage_note":    str,    # human-readable advisory sentence

    # Hard contract
    "advisory_only": True,   # literal True — never changes
    "basis":         str,    # "E7+E8b synthesis" — derivation traceability
}
```

---

## `usage_status` Logic

Two independent binary inputs produce a four-state output:

```
                         │ E7: footprint present  │ E7: footprint missing
                         │ (signals = [])         │ (signals ≠ [])
─────────────────────────┼────────────────────────┼────────────────────────
 trend adoption_risk=F   │   "observed"           │   "missing"
 trend adoption_risk=T   │   "observed_with_trend_risk" │   "trend_risk_context"
```

This is a **naming system, not a decision system**.  `_build_canonical_usage_audit`
does not produce new authority — it names a combination of two pre-existing signals
so reviewers do not have to cross-reference them manually.

**`observed`** (footprint present, no trend concern)  
→ usage_note: "canonical interpretation footprint present; no trend concern"

**`missing`** (footprint absent this session, trend not yet alarmed)  
→ usage_note: "canonical footprint absent this session; no sustained trend pattern yet"  
→ sources the E7 `audit_note` text as supplementary context

**`observed_with_trend_risk`** (this session OK, but trend shows repeated gaps nearby)  
→ usage_note: "canonical footprint present this session; trend signals repeated adoption gap in recent history (advisory)"

Naming rationale: `observed_with_trend_risk` is unambiguous — session state and
trend context are both named in the status string.  `weak` was avoided because
it implies a directionality reviewers would interpret inconsistently.

**`trend_risk_context`** (this session absent AND multi-session pattern agrees)  
→ usage_note: "canonical footprint absent this session and trend signals repeated adoption gap; reviewer context warranted (advisory only — no gate effect)"

All four states are advisory only.  `trend_risk_context` is the strongest advisory
because two independent dimensions agree on a gap, but it is NOT a block and carries
no gate effect.  The `(advisory only — no gate effect)` phrase in `usage_note` makes
this explicit in every rendered output.

---

## `format_human_result` Display

Summary line always present when key exists:

```
canonical_usage_audit: usage_status=observed artifact=True canonical_key=True trend_risk=False
```

`[ADVISORY]` line shown for any status other than `observed`:

```
canonical_usage_audit: usage_status=missing artifact=False canonical_key=False trend_risk=False
  [ADVISORY] canonical usage: canonical footprint absent this session; no sustained trend pattern yet
```

```
canonical_usage_audit: usage_status=observed_with_trend_risk artifact=True canonical_key=True trend_risk=True
  [ADVISORY] canonical usage: canonical footprint present this session; trend signals repeated adoption gap in recent history (advisory)
```

```
canonical_usage_audit: usage_status=trend_risk_context artifact=False canonical_key=False trend_risk=True
  [ADVISORY] canonical usage: canonical footprint absent this session and trend signals repeated adoption gap; reviewer context warranted (advisory only — no gate effect)
```

The `[ADVISORY]` line must use the same prefix style as E7 and E8b to maintain
consistent reviewer-scanning ergonomics.

---

## Boundary and API Considerations

### advisory_only is a hard invariant

`advisory_only=True` is literal in the source.  Any code path that reads
`canonical_usage_audit["usage_status"]` to influence `gate.blocked` is a spec
violation.

### No backfeed into E7 or E8b

`_build_canonical_usage_audit` consumes E7 and E8b results.  It does not mutate
them and does not write to any log.  E7 `canonical_path_audit` and E8b
`canonical_audit_trend` remain independent result keys.

### No new config authority

`gate_policy.yaml` is not touched.  Consuming repos cannot (and should not) tune
the synthesis logic — the 2×2 matrix is deterministic and non-configurable by
design.  If a consuming repo needs to tune thresholds, they do so via the E8b
`canonical_audit_trend` section.

### E1a is an interpretation layer, not a signal producer

`canonical_usage_audit` is a **derived interpretation layer** over E7 and E8b signals.
It does not introduce new authority, new signal sources, or new policy parameters.
Reviewers should treat it as a convenience name for a combination of pre-existing
signals, not as an independent judgment.

### basis field as derivation anchor

`basis: "E7+E8b synthesis"` is stored explicitly so that future reviewers and
tooling can identify that the field is derived, not independently authoritative.

---

## Failure Paths and Risk Points

| Scenario | Behaviour |
|----------|-----------|
| `canonical_path_audit` key absent from result | `_build_canonical_usage_audit` defaults to `artifact_present=False`, `ingestor_footprint_present=False` → `usage_status="missing"` or `"trend_risk_context"` |
| `canonical_audit_trend` key absent | defaults to `trend_adoption_risk=False`, `trend_signal_ratio=0.0` → more conservative output |
| `canonical_audit_trend.entries_read == 0` (empty history) | `adoption_risk=False` by E8b contract → `usage_status` depends only on E7 dimension |
| Any exception in `_build_canonical_usage_audit` | result falls back to `usage_status="observed"` with `advisory_only=True` AND `internal_error=True` + `usage_note` indicating the audit was unavailable — never blocks, but does not silently claim success |

The function must be callable with incomplete inputs and degrade to a safe advisory
output without raising.

**Fallback does not silently claim success.**  The `internal_error=True` key records
that the audit result is a safe default, not a genuine observation.  This prevents
implementation bugs from masking as `observed` status.

---

## Evidence Plan

Five tests in `tests/test_e1a_canonical_usage_audit.py`:

1. **`test_usage_status_observed`**  
   E7: signals=[], trend adoption_risk=False → `usage_status == "observed"`, `advisory_only=True`

2. **`test_usage_status_missing`**  
   E7: signals=["test_result_artifact_absent"], trend adoption_risk=False → `usage_status == "missing"`

3. **`test_usage_status_observed_with_trend_risk`**  
   E7: signals=[], trend adoption_risk=True → `usage_status == "observed_with_trend_risk"`

4. **`test_usage_status_trend_risk_context`**  
   E7: signals=["test_result_artifact_absent"], trend adoption_risk=True → `usage_status == "trend_risk_context"`

5. **`test_run_session_end_hook_includes_canonical_usage_audit`**  
   Full hook call: result includes `canonical_usage_audit` with `advisory_only=True`;
   `usage_status` does not affect `gate.blocked`; `format_human_result` renders
   an `[ADVISORY]` line when `usage_status != "observed"`

---

## Implementation Tranche

Single tranche.  No prerequisite changes needed — all dependencies are already in
the result pipeline from E7 and E8b.

Estimated diff:
- `session_end_hook.py`: ~60 lines added (function + wire-in + display block)
- `test_e1a_canonical_usage_audit.py`: ~120 lines (5 tests)

No changes to `gate_policy.py`, `gate_policy.yaml`, any other governance tool,
or any public contract.

**Implementation sequence**:
1. Add `_build_canonical_usage_audit(canonical_path_audit, canonical_audit_trend) -> dict`  
   after `_compute_canonical_audit_trend` in `session_end_hook.py`
2. Wire call in `run_session_end_hook` after `canonical_audit_trend =` line:  
   `canonical_usage_audit = _build_canonical_usage_audit(canonical_path_audit, canonical_audit_trend)`
3. Add `"canonical_usage_audit": canonical_usage_audit` to result dict
4. Add display block in `format_human_result` after `canonical_audit_trend` block
5. Write 5 tests
6. Run tests + regression (E7 / E8a / E8b / E5 suites)
7. Update PLAN.md + state_generator + commit + push

---

## PLAN.md Target Line (post-implementation)

```
- [x] E1a：canonical usage auditability — _build_canonical_usage_audit() pure synthesis
      of E7 + E8b into usage_status (observed / missing / observed_with_trend_risk /
      trend_risk_context); canonical_key_present replaces ingestor_footprint_present
      (naming accuracy); advisory_only=True hard-coded; NEVER gate.blocked;
      internal_error fallback does not silently claim observed; basis="E7+E8b synthesis"
      derivation anchor; format_human_result renders [ADVISORY] for all non-observed
      states; no new I/O, no new config, no gate_policy.yaml changes; 5/5 tests
```
