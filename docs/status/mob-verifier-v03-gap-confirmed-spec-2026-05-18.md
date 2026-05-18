# MOB Verifier v0.3 — gap_confirmed Workflow Spec

Date: 2026-05-18
Status: spec-frozen (implementation-ready)
Author: GavinWu
Scope: Hearth governance repo — `scripts/mob_verifier.py` + new YAML annotation layer

**Revision (same day):** Added anti-write-back constraint (Section 6.1), revised
implementation order to test-first (Section 10), conservative first annotation
guidance (Section 10, Step 3).

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

### 6.1 Anti-Write-Back Constraint (hard rule)

`gap_status.json` (Layer 3 output) is **read-only derived status**.

It MUST NOT:
- Write back to `gap_observed.ndjson` (Layer 1)
- Modify or annotate any Layer 1 record
- Inject fields into Layer 2 YAML
- Act as a trigger source for any downstream write

Rationale: if Layer 3 could modify Layer 1, the observation record would become
mutable after-the-fact. Governance lineage collapses — the "original observation"
is no longer recoverable.

Implementation enforcement: `gap_disposition_reader.py` opens ndjson files in
read-only mode. Any `write`, `open(…, 'w')`, or file mutation in the reader is a
build-time violation caught by test FM-05 (see Section 8).

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

### FM-05: Layer 3 write-back to Layer 1
**Risk:** gap_disposition_reader.py writes derived status back into gap_observed.ndjson,
making observation records mutable and erasing the original lineage.
**Guard:** Test verifies reader opens all input files read-only. Any file write operation
in reader = test failure. gap_status.json is the only permitted output artifact.

---

## 9. What v0.3 Does NOT Include

- `per-MOB convention_start` → v0.4
- `reconstruction_ambiguous` edge case testing → v0.4/v0.5
- MOB-03/04/07 automation → permanently deferred (semantic inference prohibited)
- batch scan dashboard → **permanently prohibited** (Gap Consumption Boundary)
- Automatic gap_confirmed via any heuristic → **prohibited**

---

## 10. Implementation Plan

**Order rationale:** Failure conditions are locked before happy path.
Layer 3 tests must exist before Layer 1 and Layer 2 are modified — prevents
accidental happy-path-only implementation.

### Step 1 — YAML schema + reader tests (Layer 3 failure conditions first)

Create `gap_disposition_reader.py` with tests covering:
- FM-01: reader has no YAML write path (verified by code inspection test)
- FM-02: `disposition=confirmed` with empty rationale → treated as `needs_more_evidence`
- FM-03: `consequence_eligible=true` with `disposition≠confirmed` → validation error
- FM-05: reader opens ndjson read-only; no write operations permitted (anti-write-back)
- Unmatched `observed_gap_id` (gap in ndjson, no YAML entry) → `disposition_pending=true`, `consequence_eligible=false`

No actual ndjson or YAML files required for these tests — use fixtures.

### Step 2 — mob_verifier.py: add observed_gap_id

Add `observed_gap_id` field to every `gap_observed` record.
Format: `{repo_id}::{date}::{mob_id}::{trigger_path}` (locked).

Regression: run against 2026-05-07 and 2026-05-04.
Verify: same gap_observed counts as v0.2; `observed_gap_id` stable across two runs
of same input (determinism check).

### Step 3 — First YAML annotation (conservative)

Write the first entry for MOB-05 gaps from 2026-05-07.

**Conservative constraint:** First annotation MUST be either:
- `disposition: needs_more_evidence` + `consequence_eligible: false`, OR
- `disposition: confirmed` + `consequence_eligible: false`

Do NOT set `consequence_eligible: true` in the first annotation.

Rationale: verify the review mechanism exists and the reader handles it correctly,
before opening any consequence eligibility path. v0.3 proves the annotation
workflow works; consequence authorization is a separate gate.

### Step 4 — Produce gap_status.json (Layer 3 output)

Run `gap_disposition_reader.py` against v0.3 ndjson + first YAML annotation.
Verify output contains correct `disposition_pending` for unannotated gaps and
correct derived status for annotated gaps.

**Implementation location:** Hearth governance repo (path to be confirmed per machine).
This spec lives in ai-governance-framework as the cross-repo design authority.

---

## Version History

| Version | Date | Change |
|---|---|---|
| v0.3-spec | 2026-05-18 | Initial spec: gap_confirmed workflow, YAML annotation, three-layer architecture |
| v0.3-spec-r2 | 2026-05-18 | Add anti-write-back constraint (FM-05, Section 6.1); revise implementation order to test-first (Step 1 = reader failure tests); add conservative first-annotation constraint (consequence_eligible=false initially) |
