# Enumd Non-Equivalence Table

**Scope:** This document is the authoritative list of mappings that are
explicitly **forbidden** between Enumd concepts and ai-governance-framework
canonical states.

**Why this document exists:**
Enumd operates on synthesis pipeline quality.  The framework operates on
agent misuse risk.  These are orthogonal concerns.  Without this table, an
engineer or automated consumer could accidentally treat Enumd's domain-calibrated
verdicts as framework lifecycle decisions — silently introducing false equivalence
that corrupts the trust boundary.

**Version:** 1.0
**Last updated:** 2026-04

---

## Rule 1 — Enumd verdicts do NOT map to framework lifecycle states

| Enumd verdict | What it means in Enumd | Forbidden framework mapping | Why |
|---------------|------------------------|----------------------------|-----|
| `KEEP` | Node's overlap score is above the calibrated threshold; claim is kept in synthesis output | `ignore` (lifecycle action) | Enumd KEEP is corpus-calibrated overlap; framework `ignore` is a human-reviewed disposal decision |
| `DOWNGRADE` | Node is deprioritised in synthesis output due to low overlap or domain drift | `test_fix` | DOWNGRADE moves a claim down in synthesis ranking; `test_fix` repairs a broken test assertion |
| `REMOVE` | Node is excluded from synthesis output | `production_fix` or `escalate` | REMOVE removes a claim from the synthesis store; framework fixes address runtime correctness |
| `THIN_SYNTHESIS` | Claim store has too few supporting items to synthesise reliably | `thin_evidence` (no framework equivalent) | Enumd THIN_SYNTHESIS targets synthesis depth; the framework has no equivalent concept |
| `SKIPPED` | Node was not evaluated in this wave | `not_tested` | Enumd SKIPPED is a pipeline scheduling artefact; `not_tested` means no misuse test was run |

**Consequence:** No Enumd verdict may be used to set `current_state`,
`promote_eligible`, or any canonical lifecycle field.

---

## Rule 2 — Enumd pass/fail outcomes do NOT map to misuse observed/not observed

| Enumd outcome | What it means in Enumd | Forbidden framework mapping | Why |
|---------------|------------------------|----------------------------|-----|
| `outcomes.passed > 0, suppressed = 0` | All nodes cleared Enumd's overlap threshold | `not_observed_in_window` | Enumd "all pass" is synthesis quality clearance; it makes no claim about agent misuse |
| `outcomes.suppressed > 0` | Some nodes fell below the overlap threshold | `observed` (misuse signal) | Enumd suppression is a corpus-calibration artefact; it does not indicate agent misuse |
| `outcomes.flagged > 0` | Some nodes were flagged for human review in Enumd | `risk_observed` | Enumd flagging is synthesis-layer advisory; it does not represent a confirmed misuse observation |
| *(no advisories)* | Enumd ran and found no advisory signals | `not_observed_in_window` | Absence of Enumd advisories means synthesis pipeline was quiet; it does not mean misuse risk is absent |

**Consequence:** `misuse_evidence_status` is **always `"not_tested"`** for any
Enumd observation.  `not_observed_in_window` would claim absence of risk;
`not_tested` correctly represents that Enumd does not test agent misuse.

---

## Rule 3 — Enumd advisory signals do NOT map to framework advisory vocabulary

| Enumd signal | What it means in Enumd | Forbidden framework mapping | Why |
|--------------|------------------------|----------------------------|-----|
| `domain_misalignment_risk` | A node's overlap score is close to the calibrated threshold | Framework risk signal (e.g. `session_start` override) | Enumd advisory is synthesis-pipeline-local; framework risk signal feeds lifecycle overrides |
| `thin_synthesis` | A node has few supporting synthesis items | `thin_evidence` lifecycle event | Enumd thin synthesis targets claim store depth; the framework has no equivalent concept |
| `calibration_profile_changed` | The calibration profile changed versus a prior wave | Cross-wave instability signal | A calibration change means trend delta is **not interpretable as behavioral change**; it is a meta-signal about the analysis itself |

**Consequence:** Enumd advisory signals are stored in `advisory_signals[]`, not
in `observation.evidence_refs`.  They must not be counted, aggregated, or
weighted as evidence density.

---

## Rule 4 — Calibration thresholds do NOT generalise

| Enumd threshold | Value | Forbidden use |
|-----------------|-------|---------------|
| `LOW_OVERLAP_THRESHOLD` | 0.40 | Must not become a framework default threshold |
| `HANDOFF_THRESHOLD` | 0.30 | Must not be used outside the Enumd corpus context |
| `ANY_NODE_THRESHOLD` | 0.50 | Must not be interpreted as a misuse detection threshold |

These thresholds were calibrated on the Enumd Wave 1 corpus.  They have no
meaning outside that corpus.

**Consequence:** Calibration profile fields are preserved verbatim in
`enumd_provenance.calibration_profile` for trend-analysis disambiguation only.
They may never be used as decision inputs in promotion or closure logic.

---

## Rule 5 — Cross-wave suppression delta is NOT a behavioral signal when calibration changed

When comparing suppression counts between two Enumd waves:

```python
def suppression_changed_because_of_behavior(wave_a: dict, wave_b: dict) -> bool:
    """
    Returns True only if the suppression increase is attributable to
    behavioral change, not to a calibration profile change.
    """
    pa = wave_a["payload"]["policy_applied"]
    pb = wave_b["payload"]["policy_applied"]
    return (
        pa["policy_id"] == pb["policy_id"]
        and pa["calibration_profile"] == pb["calibration_profile"]
    )
```

If `suppression_changed_because_of_behavior()` returns **False**, the
suppression delta **must not** be interpreted as behavioral degradation.
Doing so would introduce a false conclusion into the framework's risk record.

**Consequence:** Any trend analysis code consuming Enumd observations **must**
call this check before attributing suppression change to agent behavior.
Until an explicit trend consumer is implemented, these observations are
classified as:

> **trend-aware provenance preserved — trend judgment not yet enabled**

---

## Rule 6 — Enumd observations may never participate in closure or promotion

Regardless of what an Enumd report contains, the following fields may never
be set based on Enumd input:

| Field | May Enumd set it? |
|-------|-------------------|
| `current_state` | **No** |
| `promote_eligible` | **No** |
| `phase3_entry_allowed` | **No** |
| `closure_verified` | **No** |
| `closure_review_approved` | **No** |

These fields are exclusively the domain of canonical aggregation
(`phase2_aggregation_consumer`) and the Phase 3 gate
(`phase3_promotion_gate`).  Any Enumd payload that contains these fields
is treated as a forbidden authority injection and the envelope is degraded.

---

## Permitted use of Enumd observations

| Use | Permitted? | Notes |
|-----|-----------|-------|
| Advisory evidence for human reviewer | Yes | Via `advisory_signals[]` |
| Provenance tracing | Yes | Via `enumd_provenance` and `evidence_refs` |
| Trend analysis (same calibration profile) | Future | Requires explicit trend consumer |
| Synthesis quality monitoring | Yes | External to framework decision logic |
| Misuse risk assessment | **No** | Enumd does not test agent misuse |
| Closure decision support | **No** | Closure requires human reviewer via canonical path |
| Promotion gate input | **No** | Gate reads only `aggregation_result` fields |

---

*This table is enforced programmatically by `enumd_adapter.py`.
Changes to this table require explicit review and corresponding adapter updates.*
