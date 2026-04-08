# Closeout Schema — Candidate and Canonical

> Authority: `runtime_hooks/core/_canonical_closeout.py`
> Status: Stable (v1)
> Date: 2026-04-08

---

## Overview

Every session produces exactly one **canonical closeout artifact**.
The canonical artifact is always written by the system — never directly by AI.

AI may produce a **candidate closeout** via `/wrap-up` (the *candidate closeout
drafting surface*). `/wrap-up` is a quality-of-input tool, not a producer of
canonical output. The candidate is untrusted input; it is validated and normalized
into the canonical artifact by `build_canonical_closeout()` at session end.
Removing `/wrap-up` entirely must not prevent canonical closeout production —
the system falls back to `closeout_status = "missing"`, but a canonical artifact
is still written.

```
AI writes:    closeout_candidates/{session_id}/{timestamp}.json  ← candidate (untrusted)
System writes: closeouts/{session_id}.json                        ← canonical (authoritative)
```

---

## Trust Boundary

| Writer | Artifact | Trust level |
|--------|----------|-------------|
| AI (`/wrap-up`) | candidate | Untrusted — validated before use |
| `session_end_hook` | canonical | System — authoritative |
| `_append_session_index` | `session-index.ndjson` | Cache only — not source of truth |

**Invariants that must never be violated:**
- AI must not write directly to `artifacts/runtime/closeouts/`.
- `session-index.ndjson` must never be read as a source of truth by session_start, audit, or any downstream consumer. It is a scan cache only.
- `build_canonical_closeout()` is the single canonicalization function. No other code path may produce canonical closeout dicts.

---

## Candidate Schema (AI-written, untrusted)

Path: `artifacts/runtime/closeout_candidates/{session_id}/{YYYYmmddTHHMMSSffffffZ}.json`

```json
{
  "task_intent":         "string — one-sentence description of what the session aimed to do",
  "work_summary":        "string — concrete description of what was done; must name specific files/functions/tools",
  "tools_used":          ["string"] — tools invoked during the session,
  "artifacts_referenced": ["string"] — relative paths from project_root of files created or modified,
  "open_risks":          ["string"] — unresolved issues or concerns worth surfacing
}
```

**Absent fields**: `session_id`, `closed_at`, `closeout_status` — these are added by the system.
**Append-only**: `/wrap-up` called twice produces two files; `pick_latest_candidate()` selects the
lexicographically latest (= most recently authored, not most complete).

---

## Canonical Schema (system-written, authoritative)

Path: `artifacts/runtime/closeouts/{session_id}.json`

```json
{
  "session_id":       "string",
  "closed_at":        "ISO-8601 datetime with timezone",
  "closeout_status":  "valid | missing | schema_invalid | content_insufficient | inconsistent",
  "task_intent":      "string | null",
  "work_summary":     "string | null",
  "evidence_summary": {
    "tools_used":          ["string"],
    "artifacts_referenced": ["string"]
  },
  "open_risks": ["string"]
}
```

`task_intent`, `work_summary`, `evidence_summary.*`, and `open_risks` are populated from the
candidate only when `closeout_status` is `"valid"`, `"content_insufficient"`, or
`"inconsistent"`. They default to `null` / `[]` for `"missing"` and `"schema_invalid"`.

---

## `closeout_status` — Five Values

Evaluation is **first-match** in the order below. When a condition is met,
evaluation stops; no lower-precedence condition is checked.

| # | Condition | closeout_status | Fields populated? |
|---|-----------|-----------------|-------------------|
| 1 | No candidate file exists | `missing` | No (all null/empty) |
| 2 | Candidate unreadable, not a dict, missing required fields, or wrong field types | `schema_invalid` | No |
| 3 | Schema valid; `work_summary` empty or both `tools_used` and `artifacts_referenced` empty | `content_insufficient` | Partial |
| 4 | Schema valid; referenced artifact not found on disk; or verifiable tool claimed without runtime signal | `inconsistent` | Yes (candidate content preserved) |
| 5 | All checks pass | `valid` | Yes |

A candidate can only have one `closeout_status`. Because evaluation is first-match,
there is no ambiguity when multiple conditions could theoretically apply.

---

## `build_canonical_closeout()` Guarantee

This function has two hard guarantees:

1. **Never raises.** Any input — including `None`, malformed dicts, or garbage strings —
   produces a return value instead of an exception.

2. **Always returns a well-formed canonical dict.** The return value always conforms to
   the canonical schema above (all required keys present, correct types). The worst
   case is `closeout_status = "missing"` or `"schema_invalid"` with null/empty fields.

These guarantees are load-bearing: `run_session_end()` calls `build_canonical_closeout()`
before the try/except artifact-emission block, so the canonical dict is always available
even if the disk write subsequently fails.

Callers must not wrap calls in try/except to suppress the return value — the canonical
dict is always usable regardless of input quality.

---

## Signal Strength

Not all signals are equal. Downstream consumers (session_start, audit) must understand
what each check can and cannot prove:

### `existing_artifacts` — Weak existence signal

`_existing_artifacts` contains paths from `artifacts_referenced` that exist on disk at
session close time.

**What this proves:** the file path exists in the project at the moment of session end.

**What this does NOT prove:**
- The file was created or modified during this session.
- The AI's `work_summary` description of the file is accurate.
- Any tool actually operated on the file.
- The content matches what the candidate claims.

> Artifact existence is a consistency hint, not provenance.
> It tells you the path is present; it tells you nothing about who created it or whether it matches the candidate's claims.

### `tools_executed` — Verifiable tool signal

`runtime_signals["tools_executed"]` is populated from `event_log` entries with a `"tool"` field.

**What this proves:** a tool invocation was recorded in event_log during the session.

**What this does NOT prove:**
- The invocation succeeded.
- The result is relevant to the current candidate.
- The tool ran in the context described by `work_summary`.

### Verifiable tools taxonomy (frozen)

Tools in `_VERIFIABLE_TOOLS` trigger the runtime signal check:

```python
_VERIFIABLE_TOOLS = frozenset({"pytest", "build", "lint", "test", "make"})
```

Matching is **case-insensitive**. Normalization is **not** performed:
`"python -m pytest"` does **not** match `"pytest"`. Callers that want fuzzy
matching must normalize tool names before passing `event_log`.

**Design tradeoff — low recall, high stability:**
This taxonomy is intentionally strict. It will miss tool invocations with variant
spellings (e.g. `pytest -q`, `python -m pytest`). This is a deliberate choice:
fuzzy matching would make the taxonomy drift-prone and unpredictable across environments.
Low recall is the accepted cost of keeping the signal stable and auditable.

To extend this taxonomy, update `_canonical_closeout._VERIFIABLE_TOOLS` and this
document together. They must remain in sync.

---

## Session Index Cache

Path: `artifacts/session-index.ndjson`

Each line is a NDJSON entry:
```json
{
  "session_id":       "string",
  "closed_at":        "ISO-8601 datetime",
  "closeout_status":  "string",
  "task_intent":      "string | null",
  "has_open_risks":   true | false
}
```

**This file is NOT a source of truth.** It exists for fast scanning without
reading individual closeout files. It is append-only and write-failure is
non-fatal. Any discrepancy between this index and the canonical closeout
artifact must be resolved in favor of the canonical artifact.

---

## Downstream Consumer Rules

**Universal rule**: Any new consumer must read from `artifacts/runtime/closeouts/`
(canonical) only. Consuming candidate files directly or treating `session-index.ndjson`
as authoritative are both prohibited. Violations split the semantics of
`closeout_status` across layers and break auditability.

### session_start (Slice 5)

- Read from `artifacts/runtime/closeouts/` only (canonical).
- Do NOT read from `session-index.ndjson`.
- Apply injection rules by `closeout_status`:

| closeout_status | Inject |
|-----------------|--------|
| `valid` | `task_intent` + `work_summary` + `open_risks` |
| `content_insufficient` | Diagnostic warning only (no summary) |
| `missing` / `schema_invalid` / `inconsistent` | Minimal status warning only |

### closeout_audit (Slice 6)

- Read from `artifacts/runtime/closeouts/` only.
- May use `session-index.ndjson` as a read-ahead cache, but must not use it as authoritative.
- Must not derive new `closeout_status` values or extend the taxonomy.
- Output: aggregation, counts, trends, reviewer summaries only.

---

## Related Files

| File | Role |
|------|------|
| `runtime_hooks/core/_canonical_closeout.py` | Canonicalization logic (authoritative implementation) |
| `runtime_hooks/core/_canonical_closeout_context.py` | session_start context loader (Slice 5) |
| `runtime_hooks/core/session_end.py` | Orchestration: collects inputs, calls `build_canonical_closeout()` |
| `runtime_hooks/core/session_start.py` | Injects `closeout_context` into session start payload |
| `governance_tools/closeout_audit.py` | Aggregate health audit across canonical closeouts (Slice 6) |
| `governance_tools/expansion_boundary_checker.py` | `closeout_context` admission record |
| `tests/test_canonical_closeout.py` | Unit tests for `_canonical_closeout` module |
| `tests/test_canonical_closeout_context.py` | Unit tests for `_canonical_closeout_context` module |
| `tests/test_closeout_audit.py` | Unit tests for `closeout_audit` tool |
| `tests/test_session_end_closeout_integration.py` | Integration tests for the full pipeline |
| `docs/session-workflow-enhancement-plan.md` | Design rationale and implementation plan |
