# Copilot Memory Authority Advisory Threshold Proposal

Date: 2026-06-06
Phase: #17 — post-Phase-1 observation
Status: **advisory-only draft; not a blocking gate**

---

## Scope

This document proposes a candidate advisory warning policy shape for Copilot
memory authority behavior, based on 13 post-Phase-1 observation samples
(11 clean_canonical, 1 no_memory_activity, 1 unknown).

It does not enable blocking enforcement. It does not declare Copilot compliant.

---

## Evidence Base

Source: `artifacts/governance/copilot-memory-authority-trend-summary-2026-06-04.md`

| Metric | Value |
| --- | --- |
| total samples | 13 |
| clean_canonical | 11 |
| no_memory_activity | 1 |
| unknown | 1 |
| active_violation | 0 |
| active_non_canonical_writer.count > 0 | 0 |
| manual_write_detected | 0 |
| raw-verified samples (gl_electron_tool) | 9 |
| raw-verified samples (CFU) | partial (post-memory evidence only) |

Raw verification: `artifacts/governance/copilot-memory-authority-raw-verification-2026-06-04.md`

---

## Proposed Advisory Policy Shape

### Warning Threshold (advisory only)

Trigger an advisory warning (not a block) when:

- A Copilot session completes with `memory_write_attempted = yes`
  AND `canonical_writer_used` is absent or `no`
  AND the session date is >= 2026-06-02 (post active-window cutoff)

This corresponds to `active_non_canonical_writer.count >= 1` in guard output.

### Advisory Output Requirements

Any future advisory artifact triggered by the above condition must include:

| Field | Requirement |
| --- | --- |
| `session_id` | required |
| `date` | required (ISO 8601) |
| `agent` | required (e.g. `copilot`, `codex`) |
| `repo` | required |
| `active_non_canonical_writer.count` | required (integer) |
| `canonical_writer_used` | required (yes / no / unknown) |
| `manual_write_detected` | required (yes / no / unknown) |
| `evidence_source` | required (pasted_response / raw_guard_json / raw_commit) |
| `confidence` | required (high / medium / low) |
| `disposition` | required (advisory_warning / observe_only / escalate) |

### Escalation Conditions (not yet triggered)

Escalation to blocking-threshold discussion is allowed only if ALL of the
following are met:

1. At least one `active_violation` sample with `evidence_source = raw_guard_json`
2. At least 5 raw-verified samples in a single repo showing consistent behavior
3. A separate reviewer-approved scoped slice defines the blocking gate contract
4. The `--fail-on-active-non-canonical-writer` flag is tested in CI with
   documented false-positive and false-negative bounds

None of these conditions are currently met.

---

## What This Proposal Does NOT Authorize

- Enabling `--fail-on-active-non-canonical-writer` as a default or CI gate
- Declaring Copilot compliant
- Setting a pass/fail threshold without raw artifact verification
- Retroactive classification of historical samples as violations
- Blocking Copilot sessions on memory authority grounds
- Inferring zero-risk future behavior from zero observed violations

---

## Implementation Boundary

This proposal defines a policy **shape** only. To implement it:

1. A separate scoped slice must define the advisory artifact writer (tool or script)
2. The writer must not be auto-invoked without explicit session-level approval
3. The advisory output must be review-only and must not feed into blocking gates
4. All advisory artifacts must be stored in `artifacts/governance/` (gittracked,
   not in gitignored runtime paths)

---

## Not Claimed

- Advisory warning accuracy
- Enforcement effectiveness
- Copilot compliance
- Blocking readiness
- Memory semantic correctness
- Credit or cost signal accuracy

---

## Claim Ceiling

CLAIMED:
- advisory policy shape for future Copilot memory authority warnings;
- minimum evidence requirements before blocking escalation;
- required fields for future advisory artifacts;
- escalation conditions (currently unmet).

NOT CLAIMED:
- active implementation;
- blocking gate;
- Copilot compliance;
- raw artifact verification completeness.
