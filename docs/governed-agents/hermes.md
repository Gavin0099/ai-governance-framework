# Governed Agent Profile: Hermes Instance

**Governance mode:** Mode B — Contract-governed agent  
**Subject:** A deployed instance of the NousResearch Hermes agent  
**Source:** https://github.com/nousresearch/hermes-agent  
**Last reviewed:** 2026-04

---

## Overview

Hermes is a public OSS agent runtime (~91k GitHub stars, 449+ contributors,
daily commit cadence).  Its internal execution model — trajectory compression,
`acp_adapter/`, skill dispatch, cron scheduling — evolves independently of
this framework.  The framework cannot verify internal execution.

This asymmetry is permanent, not temporary.

**Governance relationship:**  
The framework provides *requirements* (via `contract.yaml` and
`AGENTS.base.md`).  A Hermes instance that wishes to be governed emits
*attestations* (minimum `session_closeout.json`) at session end.  The
framework treats attestations as evidence, not proof.

---

## Two Governance Modes — Quick Reference

| Mode A (Enumd) | Mode B (Hermes instance) |
|----------------|--------------------------|
| Evidence unit: governance report artifact | Evidence unit: session attestation |
| Framework adapter: `integrations/enumd/ingestor.py` | Framework side: reads `contract.yaml` / `AGENTS.base.md` |
| Framework can verify schema + calibration metadata | Framework can only verify attestation schema |
| Output: `artifacts/external-observations/` | Output: `artifacts/runtime/canonical-audit-log.jsonl` (attestation entry) |
| `represents_agent_behavior: false` | `represents_agent_behavior: true` |

---

## Attestation Schema — Minimum `session_closeout.json`

A governed Hermes instance emits one `session_closeout.json` per session via
`on_session_end()`.

### Required fields

```json
{
  "schema_version": "1.0",
  "producer": "hermes-instance",
  "session_id": "<unique session id>",
  "ended_at": "2026-04-15T12:00:00+00:00",
  "contract_ref": {
    "repo": "<governed repo url or local path>",
    "contract_file": "contract.yaml",
    "schema_version": "<contract.yaml schema_version value>"
  },
  "attestation": {
    "contract_read": true,
    "agents_base_read": true,
    "task_level_observed": "L1",
    "summary_produced": true,
    "closeout_attempted": true
  },
  "observation_class": "runtime_session",
  "semantic_boundary": {
    "represents_agent_behavior": true,
    "derivation": "session_end_hook"
  }
}
```

### Optional enrichment fields

```json
{
  "task_summary": "<one-line summary of what the session accomplished>",
  "risk_signals_observed": [],
  "open_items": [],
  "evidence_artifacts": [
    "artifacts/runtime/canonical-audit-log.jsonl"
  ]
}
```

### Field notes

| Field | Requirement | Notes |
|-------|-------------|-------|
| `schema_version` | Required | Bump when attestation schema changes |
| `producer` | Required | Must be `"hermes-instance"` (or a unique instance identifier) |
| `session_id` | Required | Unique per session; operator-chosen format |
| `ended_at` | Required | UTC ISO-8601 |
| `contract_ref.repo` | Required | Identifies which governed repo's contract was read |
| `contract_ref.contract_file` | Required | Must be `"contract.yaml"` for this framework |
| `attestation.contract_read` | Required | Boolean — was `contract.yaml` read before task execution? |
| `attestation.task_level_observed` | Required | L0/L1/L2 as understood by this session |
| `semantic_boundary.represents_agent_behavior` | Required | Must be `true` for Mode B sessions (enables lifecycle routing) |

---

## How a Hermes Operator Configures Attestation

### Step 1 — Read framework contract at session start

In Hermes `on_session_start()` or equivalent initialisation hook:

```python
import json
from pathlib import Path

def on_session_start(session_ctx):
    contract_path = Path(session_ctx.repo_root) / "contract.yaml"
    session_ctx.contract_read = contract_path.exists()
    session_ctx.agents_base_read = (
        Path(session_ctx.repo_root) / "AGENTS.base.md"
    ).exists()
```

### Step 2 — Emit attestation at session end

In Hermes `on_session_end()`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

def on_session_end(session_ctx):
    closeout = {
        "schema_version": "1.0",
        "producer": "hermes-instance",
        "session_id": session_ctx.session_id,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": {
            "repo": str(session_ctx.repo_root),
            "contract_file": "contract.yaml",
            "schema_version": session_ctx.contract_schema_version,
        },
        "attestation": {
            "contract_read": session_ctx.contract_read,
            "agents_base_read": session_ctx.agents_base_read,
            "task_level_observed": session_ctx.task_level or "L0",
            "summary_produced": session_ctx.summary_produced,
            "closeout_attempted": True,
        },
        "observation_class": "runtime_session",
        "semantic_boundary": {
            "represents_agent_behavior": True,
            "derivation": "session_end_hook",
        },
    }

    out_path = Path(session_ctx.repo_root) / "artifacts" / "runtime" / "session_closeout.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(closeout, indent=2), encoding="utf-8")
```

### Step 3 — Append to canonical audit log (optional but recommended)

For lifecycle tracking, the operator can append the attestation to
`artifacts/runtime/canonical-audit-log.jsonl` using the framework's
`session_end_hook.py`.  The framework's `analyze_e1b_distribution.py` and
`lifecycle_class` computation will then include this session in statistics.

---

## Attestation vs Internal Evidence — Boundary

| What counts as attestation | What is internal Hermes evidence |
|----------------------------|----------------------------------|
| `session_closeout.json` emitted via `on_session_end()` | `hermes_state.py` internal state |
| `contract_read: true` in attestation | Trajectory compression output |
| `task_level_observed` in attestation | `acp_adapter/` message routing |
| `summary_produced: true` | Skill dispatch logs |

The framework only observes attestation-level signals.  Internal Hermes
evidence (trajectory, state, dispatch logs) is not accessible to the
framework and is not a substitute for attestation.

**A Hermes session that does not emit `session_closeout.json` is ungoverned
from the framework's perspective**, regardless of what happened internally.

---

## What the Framework Can and Cannot Verify

### Can verify
- Attestation JSON is schema-valid
- `semantic_boundary.represents_agent_behavior == true` (enables lifecycle routing)
- `contract_ref.contract_file == "contract.yaml"` (correct contract)
- `attestation.contract_read == true`
- Session appears in `canonical-audit-log.jsonl`

### Cannot verify
- Whether `contract.yaml` was actually read and understood
- Whether `task_level_observed` accurately reflects the session's actual scope
- Whether Hermes internal behaviour was consistent with framework governance requirements
- Trajectory fidelity or skill execution correctness

This verification asymmetry means Mode B governance is **attestation-trust**,
not **execution-verification**.  Operators who require stronger verification
should use Mode A (artifact-governed) patterns where feasible.

---

## Relationship to `session_end_hook.py`

The framework's existing `runtime_hooks/session_end_hook.py` handles the
canonical closeout sequence for native framework sessions.  A Hermes instance
may:

- Call `session_end_hook.py` directly (if running in the same process)
- Produce a `session_closeout.json` that is compatible with the hook's expected
  input schema, then have an operator merge it after the fact

The minimum-attestation path described here (Option 3) does not require
calling `session_end_hook.py` directly.  The attestation file is sufficient
for governance tracking.

---

## Open Questions (not resolved in this document)

1. **Multi-session aggregation** — When a Hermes instance runs many governed
   sessions, should the operator maintain a per-session log or a rolling
   attestation log?  Not yet decided.

2. **Schema drift tolerance** — Hermes has a fast commit cadence.  If
   `on_session_end()` signatures change upstream, attestation templates may
   need updates.  No automated drift detection exists yet for Mode B governed
   agents.

3. **Minimum contract compliance check** — The framework does not yet define
   a machine-checkable test for "contract was read and understood" beyond the
   boolean attestation field.  This is a known verification gap.

---

*For the counterpart Mode A integration (Enumd), see
`integrations/enumd/`.*  
*For framework session governance hooks, see
`runtime_hooks/session_end_hook.py`.*
