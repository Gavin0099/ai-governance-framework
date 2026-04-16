# Enumd → ai-governance-framework Field Mapping

**Scope:** This document is the authoritative field correspondence table for
the Enumd integration seam.  It governs what the ingestor preserves, what it
routes, and what it deliberately does not translate.

**Version:** 1.0  
**Last updated:** 2026-04

---

## Routing Directives (decided before any field mapping)

| Rule | Basis | Effect |
|------|-------|--------|
| `semantic_boundary.represents_agent_behavior == false` | Enumd reports synthesise corpus artifacts, not agent runtime steps | Observation is excluded from `lifecycle_class`, `E1b`, and `session_count` statistics |
| `observation_class == "external_analysis_artifact"` | Enumd is an external analysis system, not a framework runtime session | Routed to `artifacts/external-observations/`, not `canonical-audit-log.jsonl` |
| `is_runtime_eligible()` filter must return `False` | Prevents lifecycle inflation | Any tool that reads canonical observations must apply this filter before aggregating |

```python
def is_runtime_eligible(obs: dict) -> bool:
    """True only for observations representing agent runtime behavior."""
    return obs.get("semantic_boundary", {}).get("represents_agent_behavior", True)
```

---

## Field Mapping Table

| Enumd field | Framework output field | Mapping type | Notes |
|-------------|------------------------|--------------|-------|
| `producer` | `payload.producer` | pass-through | Must equal `"enumd"` |
| `artifact_type` | `payload.artifact_type` | pass-through | — |
| `schema_version` | `payload.schema_version` | pass-through | Ingestor validates against `SUPPORTED_SCHEMA_VERSIONS` |
| `observation_class` | `observation_class` | promoted to envelope | Framework owns this field; value must be `external_analysis_artifact` |
| `observation_type` | `observation_type` | promoted to envelope | Enumd owns the value (`synthesis_governance_report`) |
| `run_id` | `run_id` | promoted to envelope | Used to name the output file |
| `domain` | `payload.domain` | pass-through | Enumd-specific, not framework taxonomy |
| `semantic_scope` | `payload.semantic_scope` | pass-through | Value `"enumd-specific"` is informational only |
| `instrumentation_version` | `payload.instrumentation_version` | pass-through | — |
| `semantic_boundary` | `semantic_boundary` | promoted to envelope | Preserved verbatim; `represents_agent_behavior` is a routing directive |
| `calibration_profile` | `calibration_profile` | promoted to envelope | Preserved verbatim; required for trend-analysis disambiguation |
| `calibration_profile.overlap_thresholds.low_overlap` | — | **not adopted** | Enumd corpus-calibrated (0.40); must not become framework default |
| `calibration_profile.overlap_thresholds.handoff` | — | **not adopted** | Enumd corpus-calibrated (0.30); not a framework threshold |
| `observed.*` | `payload.observed` | pass-through | Raw Enumd counts; no recomputation |
| `policy_applied.policy_id` | `payload.policy_applied.policy_id` | pass-through | Required for trend disambiguation |
| `policy_applied.calibration_profile` | `payload.policy_applied.calibration_profile` | pass-through | Required: distinguishes behavioral change from threshold change |
| `policy_applied.outcomes.*` | `payload.policy_applied.outcomes` | pass-through | Suppressed/flagged/passed counts; no reinterpretation |
| `advisories[].signal` | `payload.advisories[].signal` | pass-through | Enumd signal taxonomy; not framework advisory taxonomy |
| `advisories[].decision_distance` | `payload.advisories[].decision_distance` | pass-through | `"advisory_only"` means Enumd did not block; no framework equivalent action |
| `raw_artifacts.*` | `payload.raw_artifacts` | pass-through | Paths are Enumd-repo-relative |
| *(generated)* | `source` | added by ingestor | Always `"enumd"` |
| *(generated)* | `ingested_at` | added by ingestor | UTC ISO-8601 timestamp |
| *(generated)* | `source_path` | added by ingestor | Absolute path of the input file |

---

## Non-Equivalences (hard constraints)

These mappings are explicitly **forbidden** because they would introduce false
equivalence between Enumd's domain-calibrated semantics and the framework's
general-purpose lifecycle model.

| Enumd concept | Framework concept | Why NOT equivalent |
|---------------|-------------------|--------------------|
| `KEEP` (tiered enforcement) | `ignore` (lifecycle action) | Enumd KEEP is calibrated on overlap score against a domain corpus; framework `ignore` is a human-reviewed disposal decision |
| `DOWNGRADE` | `test_fix` | DOWNGRADE deprioritises a synthesised claim; `test_fix` repairs a broken test assertion |
| `REMOVE` | `production_fix` / `escalate` | REMOVE removes a claim from synthesis output; production fixes address runtime correctness |
| `LOW_OVERLAP_THRESHOLD = 0.40` | any framework threshold | 0.40 was calibrated on Enumd's Wave 1 corpus; it has no meaning outside that corpus |
| `domain_misalignment_risk` advisory | framework risk signal | Enumd advisory is synthesis-pipeline-local; framework risk signal feeds `session_start` overrides |
| `THIN_SYNTHESIS` verdict | `thin_evidence` lifecycle event | Enumd THIN_SYNTHESIS targets claim store depth; framework has no equivalent thin-evidence concept |

---

## Trend Analysis Disambiguation Protocol

When observing suppression rate changes across Enumd waves, analysis tooling
**must** check both fields before drawing conclusions:

```python
def suppression_changed_because_of_behavior(wave_a: dict, wave_b: dict) -> bool:
    """
    Returns True only if the increase in suppression is attributable to
    behavioral change, not to a calibration profile change.
    """
    pa = wave_a["payload"]["policy_applied"]
    pb = wave_b["payload"]["policy_applied"]
    # Same policy + same calibration → behavioral signal
    return (
        pa["policy_id"] == pb["policy_id"]
        and pa["calibration_profile"] == pb["calibration_profile"]
    )
```

If `calibration_profile` changed between waves, suppression delta is
**not interpretable as behavioral signal** without further analysis.

---

## Governance Primitives NOT Extracted

The following Enumd internals were evaluated and explicitly excluded from the
framework integration surface:

| Enumd internal | Reason not extracted |
|----------------|----------------------|
| `CROSS_DOMAIN_SLUG_PATTERNS` (claim-store.ts) | Domain slug list calibrated on Enumd corpus (lenovo, linux, saleae, …); not generalizable |
| `STRUCTURAL_ALLOWLIST` with Chinese markers (synthesis-enforcer.ts) | Enumd-specific synthesis artifact; no framework analogue |
| `SANITIZATION_PATTERNS` (20 regex in claim-store.ts) | Input sanitisation for Enumd claim ingestion; unrelated to framework audit surface |
| `THIN_CONTEXT_MARKERS` in Chinese (kal-checker.ts) | KAL-checker internals; Enumd-owned |
| `KalResult` (CONVERGED / THIN_SYNTHESIS / SKIPPED) | Synthesis verdict; no direct mapping to framework session lifecycle states |

---

*This mapping table is informational and auditable. Changes to the ingestor
must be reflected here. Changes to this table that affect routing directives
require explicit review.*
