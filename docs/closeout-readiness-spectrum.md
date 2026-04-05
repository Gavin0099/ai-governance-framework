# Closeout Readiness Spectrum

> Version: 1.0
> Related: docs/closeout-repo-readiness.md, docs/session-closeout-schema.md

---

## Purpose

This document defines four readiness levels for session closeout governance.

It exists because "ready / not-ready" does not accurately describe the
progression from having a stop hook to having verified session closeout.

Readiness levels describe **what closeout governance capability a repo currently
supports**. They do not describe team quality, engineering maturity, or AI usage
quality.

---

## Hard rules

**Rule 1 — Level is determined by capability checklist, not a single condition.**

A repo is not Level 2 because it "has AGENTS.base.md". It is Level 2 when the
specific capability checklist for Level 2 is satisfied. Partial checklists
result in the lower level.

**Rule 2 — Level does not affect individual session verdict logic.**

Readiness level shapes adoption expectations. It does not flow into
`session_end_hook` classification, memory promotion decisions, or verdict
artifacts. A Level 0 repo can still produce a `valid` closeout if the AI writes
a correct one. A Level 3 repo can still produce a `closeout_missing` verdict.

---

## Level 0 — Hook Entry Only

The stop hook can call `session_end_hook`. Nothing else is guaranteed.

**Capability checklist:**
- [ ] `python -m governance_tools.session_end_hook --project-root <repo>` runs without Python error
- [ ] Stop hook configured (`.claude/settings.json`) or manual call path documented
- [ ] `artifacts/` directory is writable

**What this level supports:**
- Stop-time entry into the closeout pipeline
- Degraded verdicts (`closeout_missing`, `schema_invalid`) are recorded

**What this level does NOT support:**
- Canonical closeout artifact production
- Content validation
- Memory updates of any kind

**Typical state:** repo just connected to global stop hook; no closeout schema
has been communicated to the AI.

---

## Level 1 — Canonical Closeout Ready

The repo can produce a structurally valid closeout. The 7-field schema is
available to the AI and the artifact path is writable.

**Capability checklist (Level 0 +):**
- [ ] `docs/session-closeout-schema.md` (or equivalent) is accessible in the framework repo
- [ ] `AGENTS.base.md` contains the Session Closeout Obligation section
- [ ] `artifacts/session-closeout.txt` write path exists or can be created
- [ ] AI can reference the 7-field schema when writing closeout

**What this level supports:**
- `schema_valid` closeouts possible
- `session_end_hook` can classify `presence`, `schema_validity`
- Verdict artifacts are produced

**What this level does NOT support:**
- Content sufficiency check is not reliably guided
- No pre-validation before closeout is written
- Evidence cross-reference is not meaningful yet

**Expected verdict distribution:** `closeout_missing` or `schema_invalid` common
until AI has internalized the schema. First `schema_valid` closeouts appear.

---

## Level 2 — Content-Governed Closeout

The repo has pre-validation guidance aligned with runtime judgment. The AI
knows what makes content insufficient before `session_end_hook` classifies it.

**Capability checklist (Level 1 +):**
- [ ] `AGENTS.base.md` closeout obligation includes content rules:
  - must name specific files or tool commands (observable anchor)
  - vague phrases are listed and rejected
  - `NOT_DONE` and `OPEN_RISKS` must not be omitted under pressure
- [ ] Pre-validation checklist in agent instructions matches `session_end_hook` judgment criteria
- [ ] `failure_signals` and `per_layer_results` are observable in verdict artifacts

**What this level supports:**
- `content_sufficient` closeouts possible
- `working_state_update` memory tier becomes meaningful
- `failure_signals` help diagnose why closeouts fail
- Naïve faking (vague phrases, empty fields) is consistently caught

**What this level does NOT support:**
- Syntactic anchors that refer to non-existent files are not caught
- Tool names that appear in `CHECKS_RUN` without artifact evidence are not challenged

**Expected verdict distribution:** `content_insufficient` drops. `valid` and
`evidence_inconsistent` become the dominant non-trivial states.

---

## Level 3 — Cross-Referenced Closeout

The repo has filesystem and artifact cross-reference enabled. Claims in
`FILES_TOUCHED` and `CHECKS_RUN` are spot-checked against observable signals.

**Capability checklist (Level 2 +):**
- [ ] `FILES_TOUCHED` values are checked for filesystem existence at closeout time
- [ ] `CHECKS_RUN` tool names are mapped to expected artifact directories
  (e.g. `pytest` → `.pytest_cache`, `session_end_hook` → `artifacts/runtime/verdicts/`)
- [ ] `cross_reference_results` appear in verdict artifacts
- [ ] `working_state_update` vs `verified_state_update` distinction is active

**What this level supports:**
- `evidence_consistent` closeouts possible
- `verified_state_update` memory promotion has evidence prerequisite
- Syntactic gaming (real filenames that were never touched) raises cost
- `cross_reference_results` give reviewers specific inconsistency signals

**What this level does NOT support:**
- Proof of execution — cross-reference is an inconsistency signal, not verification
- Prevention of a determined adversarial agent constructing all required artifacts
- Semantic correctness of claimed code changes

**Expected verdict distribution:** `evidence_inconsistent` now catches repos
where AI claims files it didn't touch. `valid` + `verified_state_update`
becomes the achievable steady state for compliant sessions.

---

## Progression path

```
Level 0                    Level 1                   Level 2                  Level 3
Hook entry only      →   Schema available       →   Content governed    →   Cross-referenced
                          AGENTS.base.md             pre-validation           file + tool check
                          7-field schema             observable anchor        artifact signals
                          artifact path writable     failure_signals          working/verified split
```

**Typical progression time:** Each level can be reached in a single session if
the repo owner actively addresses the checklist. Most repos reach Level 2
within two to three sessions after adoption.

---

## Relationship to memory promotion

| Repo level | Likely memory tier | Notes |
|-----------|-------------------|-------|
| Level 0 | `no_update` | Schema usually missing, memory_mode=stateless |
| Level 1 | `no_update` or `working_state_update` | Schema valid but content often insufficient |
| Level 2 | `working_state_update` | Content sufficient, evidence unchecked |
| Level 3 | `working_state_update` or `verified_state_update` | Depends on individual session result |

**Important:** This table describes typical outcomes, not automatic mapping.
A Level 2 repo can still produce `verified_state_update` if the AI writes a
closeout that happens to pass all four layers. A Level 3 repo can still produce
`no_update` if the AI writes a missing or schema-invalid closeout.

Memory tier is always determined by the single-session classification result,
not by repo readiness level.

---

## How to check your repo's current level

```bash
# Step 1 — can session_end_hook run?
python -m governance_tools.session_end_hook --project-root <your-repo> --format human

# If this runs without error: Level 0 minimum

# Step 2 — check AGENTS.base.md has closeout obligation
grep -c "Session Closeout Obligation" <your-repo>/AGENTS.base.md <your-repo>/AGENTS.md 2>/dev/null

# If present: Level 1 candidate (check full L1 checklist)

# Step 3 — write a test closeout and check content classification
cat > <your-repo>/artifacts/session-closeout.txt << 'EOF'
TASK_INTENT: test content validation
WORK_COMPLETED: updated main.py to fix edge case handling
FILES_TOUCHED: NONE
CHECKS_RUN: NONE
OPEN_RISKS: NONE
NOT_DONE: NONE
RECOMMENDED_MEMORY_UPDATE: NO_UPDATE
EOF
python -m governance_tools.session_end_hook --project-root <your-repo> --format human

# If content_sufficiency=sufficient: Level 2 candidate
# If cross_reference_results present with tool checks: Level 3 candidate
```

---

## Non-goals

- Readiness level is not a score or grade
- Higher level does not mean the repo is "better governed"
- Level 3 does not prevent a sufficiently motivated agent from gaming the system
- This spectrum does not replace the verdict artifact as the authoritative record
- Readiness level is not stored in any runtime artifact or checked by `session_end_hook`
