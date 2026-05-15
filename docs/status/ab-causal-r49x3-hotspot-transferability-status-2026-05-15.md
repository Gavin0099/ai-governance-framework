# AB Causal R49.x-3 Hotspot Transferability Status (2026-05-15)

As-of: 2026-05-15
Mode: observation-only
Decision: `hotspot_transferability_topology_collected`
causal_finding_level: `observation_only`

## Boundary
- Objective: characterize hotspot transferability topology, not prove reviewer dependency.
- Hotspot overlap is observational and non-gating.

## Summary
- total_runs: 18
- total_cells: 6
- transferability_assessable: True
- hotspot_unique_count: 3
- hotspot_overlap_rate: 0.6667

## Hotspot Cells
| scenario::substituted_owner | hotspot_id | run_count | drift_observed_count | event_log_absent_count |
|---|---|---:|---:|---:|
| SCN-RUNTIME::product | hs_scope_boundary_pressure | 3 | 3 | 3 |
| SCN-AUDIT::runtime | hs_authority_boundary_pressure | 3 | 3 | 3 |
| SCN-RUNTIME::audit | hs_evidence_lineage_strictness | 3 | 3 | 3 |
| SCN-PRODUCT::audit | hs_evidence_lineage_strictness | 3 | 3 | 3 |
| SCN-AUDIT::product | hs_scope_boundary_pressure | 3 | 3 | 3 |
| SCN-PRODUCT::runtime | hs_authority_boundary_pressure | 3 | 3 | 3 |

## Interpretation
- Transferability topology is measurable under harness mode.
- This run does not support reviewer-dependency claims (observation-only boundary).
- Next step: R49.x-4 remains blocked until metric interpretability prerequisites are explicitly met.
