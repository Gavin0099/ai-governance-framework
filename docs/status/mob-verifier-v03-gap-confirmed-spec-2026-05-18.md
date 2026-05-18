# MOB Verifier v0.3 — gap_confirmed Workflow Spec

Date: 2026-05-18
Status: spec-frozen (pre-implementation)
Author: GavinWu
Scope: Hearth governance repo — `scripts/mob_verifier.py` + new YAML annotation layer

---

## 1. Problem Statement

v0.2 verifier produces only `gap_observed`. There is no path from observation to confirmed
governance consequence. Every gap is permanently "observed but unresolved."

`gap_confirmed` is NOT a stronger verifier conclusion.
It is a **human-reviewed state transition** — a separate governance act, not a measurement upgrade.

This distinction is the core boundary this spec protects.

---

## 2. Three-Layer Architecture

```
Layer 1 — Observation (verifier output)
  mob_verifier.py → observation.ndjson
  status values: gap_observed | obligation_observed | pre_convention | reconstruction_ambiguous

Layer 2 — Review Disposition (human annotation)
  reviewer → artifacts/review/mob-gap-disposition.yaml
  status values: confirmed | rejected | needs_more_evidence

Layer 3 — Consequence Eligibility (derived, by separate consumer)
  gap_disposition_reader.py → reads Layer 1 + Layer 2
  status: governance_consequence_eligible: true | false
```

**Invariants:**
- Layer 1 is produced by machine; Layer 2 is authored by human; Layer 3 is derived by machine from 1+2.
- No layer may write into another layer's artifact.
- `mob_verifier.py` does NOT read or write YAML — prevents self-authorization loop.
- YAML does NOT embed raw observation data — it references by `observed_gap_id`.

---

## 3. YAML Annotation Schema

File: `artifacts/review/mob-gap-disposition.yaml`

```yaml
schema_version: "1.0"
entries:
  - mob_id: MOB-05
    observed_gap_id: "hearth::2026-05-07::MOB-05::pkg/supabase"
    source_artifact: "artifacts/observations/2026-05-07.ndjson"
    reviewer: GavinWu
    reviewed_at: "2026-05-18T00:00:00Z"
    disposition: confirmed          # confirmed | rejected | needs_more_evidence
    rationale: >
      Submodule bump at pkg/supabase on 2026-05-07 has no corresponding
      memory/02_project_facts.md update. Verified in git log. Genuine lineage gap.
    consequence_eligible: true

  - mob_id: MOB-01
    observed_gap_id: "hearth::2026-05-07::MOB-01::apps/web/db/migrations"
    source_artifact: "artifacts/observations/2026-05-07.ndjson"
    reviewer: GavinWu
    reviewed_at: "2026-05-18T00:00:00Z"
    disposition: needs_more_evidence
    rationale: >
      Migration added but unclear if same-working-day boundary applies —
      commit was authored 23:47 local time. Reconstruction_ambiguous candidate.
    consequence_eligible: false
```

### Field Contracts

| Field | Type | Required | Notes |
|---|---|---|---|
| `mob_id` | string | yes | Must match verifier's known MOB set |
| `observed_gap_id` | string | yes | Stable ID from observation record; format: `repo::date::mob_id::path` |
| `source_artifact` | string | yes | Path to ndjson observation file |
| `reviewer` | string | yes | Human identity; not machine-generated |
| `reviewed_at` | ISO 8601 string | yes | Review timestamp, not observation timestamp |
| `disposition` | enum | yes | `confirmed` \| `rejected` \| `needs_more_evidence` |
| `rationale` | string | yes | Must be human-authored; minimum 1 sentence |
| `consequence_eligible` | bool | yes | True only if disposition=confirmed |

### Derived Constraint

```
consequence_eligible: true
  REQUIRES disposition == "confirmed"
  PROHIBITED if disposition == "rejected" or "needs_more_evidence"
```

This constraint is enforced by the consumer (Layer 3), not by the YAML schema itself.

---

## 4. observed_gap_id Format

`{repo_id}::{date}::{mob_id}::{trigger_path}`

Example: `hearth::2026-05-07::MOB-05::pkg/supabase`

This ID must be:
- Stable across runs (deterministic given same input)
- Unique within a date
- Referenced verbatim by YAML — no fuzzy matching

`mob_verifier.py` v0.3 must emit this field in observation records.

---

## 5. mob_verifier.py Changes (Layer 1 only)

Only one addition to the verifier:

**Add `observed_gap_id` to every gap_observed record.**

No other changes. The verifier does NOT:
- Read YAML
- Write YAML
- Produce `gap_confirmed` status
- Produce `consequence_eligible` field

```python
# observation record shape (v0.3)
{
  "record_type": "gap_observed",
  "mob_id": "MOB-05",
  "observed_gap_id": "hearth::2026-05-07::MOB-05::pkg/supabase",
  "date": "2026-05-07",
  "trigger_path": "pkg/supabase",
  "trigger_commit": "abc1234",
  "obligation_artifact": "memory/02_project_facts.md",
  "pre_convention": false,
  "reconstruction_ambiguous": false
}
```

---

## 6. gap_disposition_reader.py (new — Layer 3)

New consumer tool. Reads observation ndjson + YAML, derives consequence eligibility.

```
Input:  observation ndjson (Layer 1) + mob-gap-disposition.yaml (Layer 2)
Output: gap_status_report.json (Layer 3)
```

Output record shape:
```json
{
  "observed_gap_id": "hearth::2026-05-07::MOB-05::pkg/supabase",
  "mob_id": "MOB-05",
  "observation_status": "gap_observed",
  "disposition": "confirmed",
  "consequence_eligible": true,
  "reviewer": "GavinWu",
  "reviewed_at": "2026-05-18T00:00:00Z",
  "derived_at": "2026-05-18T10:00:00Z"
}
```

If no YAML entry exists for an `observed_gap_id`:
```json
{
  "observed_gap_id": "hearth::2026-05-07::MOB-01::apps/web/db/migrations",
  "mob_id": "MOB-01",
  "observation_status": "gap_observed",
  "disposition": null,
  "consequence_eligible": false,
  "disposition_pending": true
}
```

**`disposition_pending: true` prevents unreviewed gaps from entering consequence eligibility.**

---

## 7. Claim Ceiling (unchanged from v0.2)

| Claim | Allowed |
|---|---|
| `gap_observed` records exist for date X | ✓ |
| `gap_confirmed` for specific gap (with YAML evidence) | ✓ |
| `consequence_eligible` for specific confirmed gap | ✓ |
| Historical gap pattern established | ✗ |
| Temporal integrity verified | ✗ |
| Contributor performance signal | ✗ (Gap Consumption Boundary) |

---

## 8. Failure Modes to Guard

### FM-01: Self-authorization loop
**Risk:** mob_verifier.py reads YAML and upgrades its own output.
**Guard:** mob_verifier.py has no YAML dependency. Verified by import audit.

### FM-02: disposition=confirmed without rationale
**Risk:** YAML entry with `disposition: confirmed` but empty rationale launders a machine observation as human-confirmed.
**Guard:** Reader validates `rationale` is non-empty for `disposition=confirmed`. If empty → treat as `needs_more_evidence`.

### FM-03: consequence_eligible=true with disposition≠confirmed
**Risk:** Schema allows the inconsistency.
**Guard:** Reader enforces: `consequence_eligible: true` AND `disposition != "confirmed"` → validation error, reject entry.

### FM-04: observed_gap_id drift
**Risk:** Verifier changes ID generation logic → YAML references become stale.
**Guard:** ID format is locked in v0.3 schema. Any format change requires schema_version bump + YAML migration.

---

## 9. What v0.3 Does NOT Include

- `per-MOB convention_start` → v0.4
- `reconstruction_ambiguous` edge case testing → v0.4/v0.5
- MOB-03/04/07 automation → permanently deferred (semantic inference prohibited)
- batch scan dashboard → **permanently prohibited** (Gap Consumption Boundary)
- Automatic gap_confirmed via any heuristic → **prohibited**

---

## 10. Implementation Plan

1. **mob_verifier.py v0.3**: Add `observed_gap_id` field to gap_observed records
2. **YAML schema**: Create `artifacts/review/mob-gap-disposition.yaml` with schema_version header
3. **gap_disposition_reader.py**: New consumer; validates YAML + ndjson; derives consequence eligibility
4. **Regression test**: Run v0.3 against 2026-05-07 and 2026-05-04; verify same gap_observed counts as v0.2; verify `observed_gap_id` stable across runs
5. **First YAML annotation**: Manually annotate MOB-05 gaps from 2026-05-07 as first confirmed entries

**Implementation location:** Hearth governance repo (path to be confirmed per machine).
This spec lives in ai-governance-framework as the cross-repo design authority.

---

## Version History

| Version | Date | Change |
|---|---|---|
| v0.3-spec | 2026-05-18 | Initial spec: gap_confirmed workflow, YAML annotation, three-layer architecture |
