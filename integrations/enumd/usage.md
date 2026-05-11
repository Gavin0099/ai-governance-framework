# Enumd Integration — Usage Guide

This document answers three questions for anyone using the Enumd integration
seam in the ai-governance-framework.

---

## Q1 — How do I give the ingestor an artifact?

### Prerequisites

An Enumd `governance_report.json` must exist on disk.  The file must conform
to `integrations/enumd/schema.sample.json`.

### CLI (from framework repo root)

```powershell
# Standard ingest — writes output to artifacts/external-observations/
python integrations/enumd/ingestor.py path/to/governance_report.json

# Dry-run — validates and prints the canonical observation; nothing is written
python integrations/enumd/ingestor.py path/to/governance_report.json --dry-run

# Explicit repo-root (when running from a different working directory)
python integrations/enumd/ingestor.py path/to/governance_report.json \
    --repo-root e:/BackUp/Git_EE/ai-governance-framework
```

Exit codes:
- `0` — ingestion succeeded
- `1` — validation error; see stderr for details

### Python API

```python
from pathlib import Path
from integrations.enumd.ingestor import ingest

result = ingest(
    report_path=Path("path/to/governance_report.json"),
    repo_root=Path("e:/BackUp/Git_EE/ai-governance-framework"),
    dry_run=False,
)

if not result["ok"]:
    raise RuntimeError(result["errors"])

print(result["output_path"])    # artifacts/external-observations/enumd-wave-5.json
print(result["observation"])    # canonical observation dict
```

---

## Q2 — What does the ingestor output?

### Output location

```
artifacts/external-observations/enumd-{run_id}.json
```

Example: a report with `"run_id": "wave-5"` produces  
`artifacts/external-observations/enumd-wave-5.json`

### Output schema (envelope)

```json
{
  "observation_class": "external_analysis_artifact",
  "observation_type": "synthesis_governance_report",
  "source": "enumd",
  "run_id": "wave-5",
  "ingested_at": "2026-04-15T12:00:00+00:00",
  "source_path": "/abs/path/to/governance_report.json",
  "semantic_boundary": {
    "represents_agent_behavior": false,
    "derivation": "synthesis_pipeline"
  },
  "calibration_profile": { "name": "production_v1", "overlap_thresholds": { ... } },
  "payload": {
    "producer": "enumd",
    "artifact_type": "governance_report",
    "schema_version": "1.0",
    "run_type": "production_wave",
    "domain": "usb_windows_firmware",
    "observed": { ... },
    "policy_applied": { ... },
    "advisories": [ ... ],
    "raw_artifacts": { ... }
  }
}
```

The `payload` object contains the Enumd report verbatim (minus the two fields
promoted to the envelope: `semantic_boundary` and `calibration_profile`).

### Routing guarantee

`observation_class: "external_analysis_artifact"` and
`semantic_boundary.represents_agent_behavior: false` are preserved at the
envelope level so that any downstream analysis tool can apply the
`is_runtime_eligible()` filter correctly:

```python
def is_runtime_eligible(obs: dict) -> bool:
    return obs.get("semantic_boundary", {}).get("represents_agent_behavior", True)

# Enumd observations always return False — excluded from lifecycle aggregations
```

---

## Q3 — What is NOT guaranteed equivalent?

### Enumd decisions ≠ framework lifecycle actions

| Enumd outcome | Do NOT map to |
|---------------|---------------|
| `KEEP` | framework `ignore` |
| `DOWNGRADE` | framework `test_fix` |
| `REMOVE` | framework `production_fix` or `escalate` |

These are different decision models calibrated on different evidence
(Enumd: overlap scores on synthesis corpus; framework: test failure
classification and lifecycle history).

### Calibration thresholds are NOT framework defaults

```
low_overlap:  0.40  ← Enumd Wave 1 corpus only
handoff:      0.30  ← Enumd HANDOFF node type only
any_node:     0.50  ← Enumd any-node threshold only
```

Do not use these values anywhere else in the framework.

### Enumd advisories are NOT framework risk signals

An Enumd `domain_misalignment_risk` advisory reflects a synthesis pipeline
concern (claim overlap below a domain-calibrated threshold).  It does NOT
imply a framework governance risk signal that would influence `session_start`
overrides or `min_task_level`.

To emit a framework risk signal from Enumd observations, you would need to
author a separate producer that reads Enumd output and decides — with explicit
policy — when a synthesis concern crosses a threshold warranting a framework
signal.  That producer does not exist yet and is out of scope for this
integration seam.

### Wave run ≠ session observation

Enumd wave runs describe batch synthesis pipeline output over a corpus.  They
are not equivalent to framework session observations (which track individual
AI-agent runtime sessions).  They must not be aggregated into
`recent_lifecycle_class`, `session_count`, or `E1b` statistics.

---

## Validation errors reference

| Error | Cause | Fix |
|-------|-------|-----|
| `missing required field: 'semantic_boundary'` | Report predates v1.0 schema | Add `semantic_boundary` block to the report |
| `represents_agent_behavior must be false` | Field was set to `true` or omitted | Set `"represents_agent_behavior": false` in `semantic_boundary` |
| `unsupported schema_version` | Report uses a schema version not yet recognised | Check `SUPPORTED_SCHEMA_VERSIONS` in ingestor.py and update if schema is valid |
| `expected 'enumd', got '...'` | Wrong producer field | This adapter only accepts `"producer": "enumd"` artifacts |
| `missing required field: 'calibration_profile'` | Calibration metadata absent | Add `calibration_profile` with at least `name` and `overlap_thresholds` |

---

*For field-level semantics and non-equivalence rules, see
`integrations/enumd/mapping.md`.*  
*For the canonical sample artifact, see
`integrations/enumd/schema.sample.json`.*
*For runtime portability boundary and execution-mode scope, see
`integrations/enumd/execution-model-decision.md`.*
