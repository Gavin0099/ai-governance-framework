# Closeout Repo Readiness

> Version: 1.0

A repo is **closeout-ready** when it meets the following minimum conditions.
Meeting these conditions does not guarantee closeout quality — it only means
the infrastructure for session closeout is in place.

---

## Minimum conditions

### 1. AGENTS.base.md present and contains closeout obligation

The adopted repo must have `AGENTS.base.md` (or the obligation text included
in `AGENTS.md`) with the Session Closeout Obligation section.

Verify:
```bash
grep -l "Session Closeout Obligation" AGENTS.base.md AGENTS.md 2>/dev/null
```

If missing, re-adopt:
```bash
python governance_tools/adopt_governance.py --target <repo> --framework-root <ai-gov>
```

---

### 2. Artifact write path exists or can be created

`session_end_hook` writes to `artifacts/session-closeout.txt` and
`artifacts/runtime/`. The repo must not block writes to these paths.

Verify:
```bash
mkdir -p artifacts/runtime && echo "ok" > artifacts/.write-test && rm artifacts/.write-test
```

---

### 3. `session_end_hook` is executable from the framework repo

The stop hook calls `python -m governance_tools.session_end_hook`.
This requires:
- Python with framework dependencies installed
- The framework repo on the Python path (`cd` to framework root or use `-m`)

Verify:
```bash
# From framework repo root
python -m governance_tools.session_end_hook --project-root <your-repo> --format human
```

Expected output: `closeout_status=closeout_missing` (file not there yet) with exit code 1.
If you see a Python error, dependencies are not installed.

---

### 4. Schema document is accessible

`docs/session-closeout-schema.md` must be present in the framework repo so the
AI can reference it when writing the closeout.

Verify:
```bash
test -f docs/session-closeout-schema.md && echo "present"
```

---

### 5. Stop hook configured (for automatic closeout)

For automatic closeout on every session, `.claude/settings.json` must have a
`Stop` hook. See `docs/stop-hook-setup.md`.

Manual fallback: run `python -m governance_tools.session_end_hook --project-root .`
before ending a session.

---

## Readiness check command

Run all five conditions at once:

```bash
python -m governance_tools.session_end_hook --project-root <your-repo> --format human
```

| Output | Meaning |
|--------|---------|
| `closeout_status=closeout_missing` | Infrastructure ready; AI has not written closeout yet |
| `closeout_status=valid` + `promoted=True` | Fully ready and last session closed cleanly |
| Python `ModuleNotFoundError` | Dependencies not installed |
| `FileNotFoundError` on project-root | Path does not exist |

---

## What readiness does NOT guarantee

- That the AI will write a valid closeout (schema and content are the AI's obligation)
- That memory will update (promotion still requires `closeout_status=valid`)
- That evidence claims are true (evidence_consistency is best-effort only)
- That the repo is fully governance-compliant in all other dimensions

Readiness is a prerequisite for the closeout contract to function.
It is not a certification of governance quality.

---

## Memory promotion note

Memory is updated only when `closeout_status=valid` (all four layers pass).

This is intentionally conservative. There is a known trade-off:

- **Too strict**: valid closeouts that fail evidence_consistency due to
  filesystem layout differences will not update memory, even if the
  underlying work was real.
- **Too permissive**: accepting content_insufficient closeouts into memory
  allows AI self-report to bypass verification.

The current policy errs toward strict. If evidence_consistency false-positives
become a recurring problem (e.g. cross-drive paths, CI environments), the
appropriate fix is to adjust the evidence consistency checks — not to lower
the `valid` bar.

A two-tier memory promotion model (`memory_safe_update` for content_sufficient
but evidence_unchecked closeouts, `memory_high_confidence_update` for fully
valid closeouts) is a future option if the strict gate causes memory starvation.
