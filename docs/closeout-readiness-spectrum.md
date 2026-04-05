# Closeout Readiness Spectrum

> Version: 1.1
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

## Two independent dimensions

Readiness output carries two separate values. They must not be merged.

**`repo_readiness_level` (0-3)** — Structural capability checklist.
What governance infrastructure is in place. Determined by files, config, and
code — not by session history. A repo that just had `upgrade_closeout` applied
can be structural Level 3 immediately.

**`closeout_activation_state`** — Whether the closeout loop has been observed
in practice.

| Value | Meaning |
|-------|---------|
| `observed` | At least one verdict artifact exists — the loop has been run before |
| `pending` | Structural prerequisites met but no verdict artifacts yet |
| `unknown` | Structural level too low to activate meaningfully |

**`activation_recency`** — How recently the loop was last observed (only set
when `activation_state=observed`).

| Value | Meaning |
|-------|---------|
| `recent` | Most recent verdict artifact is within 30 days (by file mtime) |
| `stale` | Verdict artifacts exist but most recent is older than 30 days |

**What `recent` actually checks:** The mtime of the most recent verdict artifact
file. It does NOT check whether that session produced a `valid` or
`content_sufficient` closeout. A repo can be `observed/recent` while the last
10 sessions all ended in `closeout_missing`.

`recent` is an operational heuristic, not a guarantee of current health. It
answers "was the hook invoked recently?" — not "is the governance working?".

**Precise semantic definitions:**

`activation_state` indicates whether the repository has ever produced a
closeout artifact that entered the governance runtime. It does not imply
ongoing compliance or guarantee system trustworthiness.

`observed` = observed at least once. `observed` ≠ trustworthy.

`pending` = structural prerequisites met, but no observed run yet.
`pending` does not mean partially validated or nearly reliable. It means
no closeout run has been recorded. A pending repo has full structural
capability but zero activation history.

`unknown` = structural level too low to assess activation meaningfully.
`unknown` is not a negative verdict — it is a gap in information. Do not
treat it as equivalent to `pending`.

`activation_recency` refines `observed`: `stale` means the loop ran
historically but may not reflect current behavior. `stale` is the most
diagnostically valuable state — it should trigger a reviewer question,
not just be read as "imperfect observed".

Activation reduces the risk of completely unverified operation. It does not
eliminate errors or adversarial behavior.

**Why separate from structural level?** A repo can be structural Level 3 with
`activation=pending` (full capability in place, no session run yet). Treating
"no prior verdicts" as a structural deficiency would conflate:
- structural capability (what infrastructure is in place)
- activation history (whether that infrastructure has been exercised)

`prior_verdict_artifacts_exist` is an activation signal, not a structural one.
It does not affect `repo_readiness_level`.

---

## Reviewer action mapping

These are expected reviewer actions per activation state. This table converts
the three-dimension model into workflow input — not decision input.

| State combination | Expected reviewer action |
|-------------------|--------------------------|
| `pending` (any level) | Before treating the repo as activated, require at least one recorded closeout session that produces a verdict artifact (`closeout_status` present in `artifacts/runtime/verdicts/`). The minimum bar is a **recorded run** — not necessarily `valid`. A `closeout_missing` verdict counts: it proves the hook fired. Meeting this bar only proves the hook fired — it does not imply any quality or completeness of the closeout. Do not treat activation as an unlock condition. |
| `observed/recent` | Inspect individual session verdict artifacts. Do not assume health. `observed/recent` means the hook was invoked recently — not that recent sessions passed. Activation does not reflect the quality distribution of closeout runs; quality must be assessed at the session verdict level. |
| `observed/stale` | Distinguish three causes before acting: **(1) wiring failed** — stop hook broke, artifact path changed, or CI workflow disconnected; **(2) usage interrupted** — hook works but sessions haven't happened recently; **(3) adoption stopped** — team stopped using the repo at the decision level. **Triage order:** rule out wiring first (cheapest to verify: check hook config and artifact path), then check recent session activity, and only then consider adoption-level stop. Reversing this order typically misdiagnoses the cause. |
| `unknown` | Check artifact write path and structural prerequisites. `unknown` is a gap in information, not a negative verdict. |

**Note:** These are reviewer workflow actions, not enforcement. The verdict artifact
for each individual session is the authoritative record, not the activation state.
Activation state is an existence check, not a quality grade.

---

## Known future gap: activation quality

The current model answers three questions:
1. Does the repo have structural capability? (`level`)
2. Has closeout ever been observed? (`activation_state`)
3. Was it observed recently? (`activation_recency`)

It does not answer a fourth question:
4. What quality did recent closeouts achieve?

A repo that is `observed/recent` could have had every recent session end in
`closeout_missing`. The current model cannot distinguish that from a repo
where every recent session produced `valid + verified_state_update`.

This gap is intentional for now. Adding a `recent_closeout_quality` or
`recent_closeout_health` dimension would provide that signal, but adds
runtime cost and complexity. The right trigger for that addition is when
reviewers consistently report that `observed/recent` is misleading them
about repo health — not before.

Until then: always read individual verdict artifacts alongside the activation
state. Activation state is an existence check, not a quality grade.

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

Level appears in verdict artifact metadata so reviewers have context. It is
never read back as decision input.

**Rule 3 — Readiness level is not a maturity score and MUST NOT be used as a
performance or quality KPI.**

Level 3 means the repo has cross-reference capability enabled. It does not mean
the team is better, the AI is more reliable, or the code is higher quality.
Using level as a KPI produces incentives to game the checklist rather than
improve actual governance behaviour.

**Rule 4 — Progression is capability expansion, not a mandatory upgrade path.**

A repo that stays at Level 2 indefinitely is not a failure. Cross-reference
(Level 3) is useful for repos where fabricated file claims are a realistic risk.
For many repos, Level 2 content governance is the appropriate steady state.
Upgrade when the capability is needed, not because the number is lower.

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

**Note on activation:** In the current framework, cross-reference is always
active once Level 2 structural prerequisites are met — the capability is in
the framework code, not in per-repo configuration. A repo that reaches
Level 2 is immediately structural Level 3.

Whether the cross-reference loop has been *observed* in practice is captured
separately in `closeout_activation_state` (`active` / `pending`). Prior
verdict artifacts affect `activation_state` only — not the structural level.

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

## Positioning of working_state_update

`working_state_update` is not a degraded or "dirty" tier. It is the primary
carrier of ongoing session reality.

**working_state is the primary carrier of ongoing reality.
verified_state is a filtered subset for high-confidence use.**

A repo that consistently produces `working_state_update` is doing useful work.
Memory that is 80% working_state is dramatically more useful than memory that
is 0% because the `verified` bar is never reached. Do not treat `working_state`
as something to be avoided or cleaned up.

## Cross-reference is an inconsistency signal, not verification

**Cross-reference increases the cost of fabrication, but does not guarantee
correctness.**

A file that exists may not have been meaningfully changed. A tool artifact that
exists may predate the current session. A repo that passes all cross-reference
checks is a repo where no detectable inconsistency was found — not a repo where
all claims are proven true.

Level 3 raises the cost of naive or accidental fabrication. It does not
eliminate the possibility of deliberate fabrication. This distinction matters
for how you communicate the system's guarantees to external reviewers.

## Non-goals

- Readiness level is not a score or grade
- Higher level does not mean the repo is "better governed"
- Level 3 does not prevent a sufficiently motivated agent from gaming the system
- This spectrum does not replace the verdict artifact as the authoritative record
- Readiness level appears in verdict metadata but is never read back as decision input
