# Evidence-Backed Engineering Skill Program — Review-Only Plan

Status: DRAFT for owner review. No Engineering Skill is built, no
experiment is run, no validator / schema / runtime / hook / CI / gate /
enforcement is added or changed by this document. No engineering method is
claimed effective.

Scope boundary: this document defines *how* the program would study
engineering methods as Skills. It does not authorize any study to start. Each
study still passes Gate 0 and Gate 1 (Section 8) before any run.

Review provenance: the direction, four-layer boundary, four-arm experiment
shape, and candidate taxonomy were discussed in the 2026-07-24 owner review
thread. This draft records that discussion for review; it does not claim a
durable approval record until the approved plan and canonical memory are
committed.

## 0. Non-Claims

This plan does not establish, and no reader may infer, any of:

- that any Engineering Skill improves task success;
- that adding an external validator reduces real defects;
- that the existing codex-review-fast A/B result transfers to any other Skill
  (the first run had a blinding-protocol defect because condition labels were
  not stripped; the
  [corrected blind rerun](../../artifacts/evidence/skill-ab/codex-review-fast-20260709/result-blind.json)
  remained `decision_effect=negative` on a *single constructed seeded* task;
  see `memory/2026-07-09.md`; neither run is evidence about Bug Fix);
- that any method below is a roadmap commitment; all appendix methods are
  deferred candidates only;
- that Gate 3's minimum of three work-items is a statistically powered
  inference; Gate 3 is a screening decision only;
- that reaching Gate 4 equals framework-level G4 achieved.

## 1. Problem

Mature software engineering has repeatable methods that *may* improve agent
work (bug fixing, refactoring, API change, feature delivery, and more). Parts
of these already live in governance docs, but the program has **not** shown:

- that an agent stably adopts the method;
- that adoption actually improves the product outcome;
- that the improvement exceeds time / token / human cost;
- which methods belong in an advisory Skill vs. a Governance rule.

Goal: **find engineering-method combinations that produce repeatable,
measurable improvement on real AI-coding tasks** — not to catalog knowledge.

## 2. Four-Layer Responsibility

| Layer | Responsibility | Must not |
|---|---|---|
| Engineering Skill | Tell the agent how to do the task | Claim its own work is verified |
| Harness | Load the Skill, run tools, persist output | Raise its own governance authority |
| External Validator | Provide an independent check signal | Be treated as product correctness |
| AI Governance | Decide when to use, persist evidence, bound claims | Re-implement a linter or the method itself |

This matches the existing boundary at
[memory/03_knowledge_base.md:59](../../memory/03_knowledge_base.md) (Packs
provide governance context; Skills provide behavior guidance; runtime/policy
decides).

Naming: use **Engineering Skill** / **Engineering Skill Recipe**. Do **not**
reuse the framework's existing *Pack* authority semantics.

## 3. First Study Object — Bug Fix Safety Skill

Studied first because its testing rules are the most complete, original defects
are usually reproducible, independent expected values are easiest to obtain,
and before/after comparison (fails before fix, passes after) is directly
measurable when the oracle is fixed.

Candidate recipe (frozen only at Gate 1):

1. Reproduce the defect
2. Form a root-cause hypothesis
3. Establish a credible expected behavior (independent of production logic)
4. Write a regression test that fails before the fix
5. Make the minimal fix
6. Run the relevant tests
7. Check test sensitivity by re-introducing the original defect, then restore
   the candidate output; the blind scorer independently repeats the frozen
   sensitivity check on every arm
8. Identify applicable external validators; during the experiment, only Arm D
   may receive or act on their execution-time output
9. Bound the completion claim to the evidence

## 4. Four-Arm Experiment

All four arms start from the **same baseline commit**. All arms keep the common
baseline safety/permission rules; A/B does not mean removing safety, only not
loading the Skill and the experimental governance content under test.

| Arm | Condition | Effect measured |
|---|---|---|
| A | Base harness | Control |
| B | Harness + Bug Fix Skill | Skill effect |
| C | Harness + Skill + task-specific Governance | Added effect of evidence/claim bounding |
| D | Harness + Skill + Governance + External Validator | Added effect of a mature validator |

Difference reading: `B−A` = Skill useful?; `C−B` = Governance changes outcome or
only adds cost?; `D−C` = validator finds additional problems?

Two validator roles must remain separate:

- **Treatment-time validator feedback:** only Arm D receives the frozen
  validator result before its output is committed. A/B/C do not receive or act
  on that result.
- **Post-hoc scoring validator:** after every arm output is committed and
  hidden, the blind scorer may run the same frozen validator against all four
  outputs. These results measure residual findings and cannot be fed back to
  the producing arm.

## 5. Task and Environment Control

Task admissibility:

- Originates from a **real product bug**, not fabricated to fit the Skill.
- Has clear reproduction steps.
- Has a credible behavior source: spec, bug report, owner acceptance criteria,
  or a fixed fixture.

Run control:

- All four arms use the same starting commit.
- Same model, versions, tool permissions, and budget.
- Each arm uses a fresh context (no cross-contamination).
- Each arm uses an isolated worktree or branch.
- Outputs are scored under the frozen rubric by scorer(s) blind to arm
  identity; the second-scorer subset follows Section 6.

One frozen natural bug replayed four times is a **controlled replay**, not four
natural cases.

## 6. Scoring

Primary outcome metrics:

- Product result meets an independent acceptance criterion.
- Regression test fails at baseline and passes after the fix.
- Regression test fails again when the original defect is re-introduced.
- No new scoped regression is introduced.
- The agent's completion claim matches the actual evidence.

Cost metrics: owner interventions; rework count; wall-clock time;
token / tool-call count; change scope; validator false positives; final
accept/reject ratio.

Oracle boundary: Semgrep / oasdiff / linters are independent verification
signals only; none is a complete product oracle by itself.

**Claim-evidence scoring:** Gate 1 freezes a rule-based mismatch checklist for
machine-checkable completion claims (for example, claimed test success vs.
receipt exit code / linked output commit). Semantic claims that remain
judgment-dependent are independently scored on a pre-registered subset by a
second blind scorer. The result reports raw agreement and every disagreement;
a single uncalibrated scorer judgment is not admissible for this metric.

**Uniform-oracle rule:** if mutation testing or another
**scoring oracle** is used to compare outputs, it is applied **post-hoc by the
blind scorer, identically to all four arms A/B/C/D**. A scoring oracle must
never be attached only to treated arms, or the treatment condition and
measurement change together and the difference cannot be attributed. This
does not prohibit Arm D's separately declared treatment-time validator
feedback; that feedback is frozen at Gate 1 and kept unavailable to A/B/C.

## 7. Evidence and Commit / Receipt Anchoring

Each arm must persist: common baseline commit; baseline instruction-set hash;
the arm's output commit; model/harness version; experimental treatment-packet
hash; Governance instruction hash; validator version and config hash; the raw
run log; test and validator results; the actual output commit each receipt
points to; and whether the worktree was clean.

Verification is preferably run after `checkout` to the arm's output commit, to
avoid the recurring "receipt points to a commit that is not the tested version"
failure.

**Evidence Provenance is an admissibility gate, not a score. Receipt types are
explicit:**

- The authoritative validation artifact for every test / validator command is
  a **test-evidence receipt**, whose field is `linked_commit`. Every such
  receipt must satisfy `linked_commit == the arm's actual output commit`, and
  the worktree must be clean at capture time.
- If a session closeout receipt is also retained, its distinct field
  `linked_head_commit` must bind to the same output commit. It supplements but
  does not replace command-level test-evidence receipts.
- Failure of either required binding disqualifies the affected arm from
  comparison rather than merely reducing its score. A new run requires a new
  pre-registered execution; an invalid result must not be repaired in place.
- Advisory only, **not** claimed as fully auto-decidable: whether a commit is
  semantically atomic (one logical change). Kept as guidance.

## 8. Staged Decision Gates

- **Gate 0 — Candidate task valid.** A real bug, a common baseline, and a
  credible oracle exist. If not, stop; do not manufacture a bug.
- **Gate 1 — Pre-registration.** Freeze, before any run: the four arms; task and
  baseline; baseline safety/permission instruction set; an experimental Skill
  treatment packet frozen as an experiment input but not registered as a
  repo-visible Skill; task-specific Governance treatment; oracle; outcome
  metrics; cost metrics; decision thresholds; claim-evidence mismatch
  checklist and second-scorer subset/disagreement procedure; validator
  version/config and treatment-time availability; commit and receipt anchoring
  method; blinding and randomization method.
- **Gate 2 — Single pilot.** One four-arm replay of one natural bug. May only
  judge whether the process runs, evidence anchors correctly, and metrics score
  objectively. A single bug cannot declare the Skill effective.
- **Gate 3 — Preliminary effect.** Accumulate at least 3 separately originated
  natural bug work-items across at least 2 consumer repos. Each task is
  separately pre-registered under the same experiment protocol, does not
  duplicate another task's root cause, and is not run only in one agent
  session. Only after clearing the pre-approved improvement threshold may the
  frozen treatment packet be materialized as a repo-visible **provisional**
  Skill. This is a screening decision, not statistically powered inference.
- **Gate 4 — Transfer.** The provisional Skill must further pass on at least one
  held-out consumer environment not used to make the Gate 3 decision, at a
  different work time, preferably with a different agent or reviewer, real
  product outcomes, and comparable human and execution cost. This normally
  implies a third consumer repo unless the pre-registration names and justifies
  another genuinely held-out environment. It still does **not** equal
  framework-level G4 achieved.
- **Gate 5 — Promote to Governance rule.** Only if all hold: the same failure
  mode recurs in natural work; advisory Skill alone is insufficient to control
  the risk; the rule is objectively decidable; false-positive rate and cost are
  acceptable; explicit owner approval. Otherwise it stays a Skill, not a rule /
  hook / gate.

## 9. Stop Conditions

Classify stop outcomes instead of treating every limit as the same result:

- **INVALID — exclude the affected run/task from comparison:** no credible
  oracle; arms do not share the same baseline; model/context contamination;
  required receipt-to-output binding fails; or execution requires changing
  enforcement to make the experiment look successful. An invalid result is not
  evidence for or against the Skill.
- **NEGATIVE — stop promotion and retire, rewrite, or leave the treatment
  unused:** after the pre-registered decision sample, the Skill does not improve
  the outcome, improvement is smaller than cost, or validator false positives
  cancel the gain. A negative result is a valid result.
- **INSUFFICIENT — hold at the current gate and collect held-out evidence:**
  results remain limited to the same owner, same repo, same agent environment,
  or a short time window. This is not a negative effect and does not invalidate
  a Gate 2 pilot, but it cannot support promotion.

## 10. Appendix — Candidate Method Inventory (Deferred Candidates Only)

Everything here is a **deferred candidate**, not an implementation commitment or
a scheduled roadmap.

**Axis note:** the tiers below mix two independent axes. Read them as:

- *Priority tiers* (研究優先序): "Priority study" vs "Deferred study" — a
  research-order axis.
- *Cross-cutting role* (作用範圍) is **not a priority level.** Cross-cutting
  methods are applied uniformly across all arms / all task types regardless of
  which task-type study is running (e.g., the same oracle scored on A/B/C/D).

### 10.1 Priority study candidates (task-types with strong independent oracles)

| Method | Independent oracle | In-repo validator status | Oracle caveat |
|---|---|---|---|
| Bug Fix | regression test fail→pass; re-introduce defect | `failure_completeness_validator.py` exists | first study object |
| Security Fix | reproducible exploit PoC; Semgrep/CodeQL **SARIF** | SARIF format is ingestible; Semgrep/CodeQL execution is not integrated | *suggested* second, not decided; not the only arm-D task |
| API Change | public-API diff | `public_api_diff_checker.py` exists; oasdiff is an unverified external candidate | diff shows shape change, not full behavioral compat |
| Data Migration | forward+backward migration, idempotency, rollback | pgTAP exists in a consumer; no framework-wide integration is claimed | replay proves the tested path, not all data states |
| Dependency Update | existing suite green + API diff + changelog | external audit tooling is a candidate; availability/integration is unverified | these three **do not** fully prove compatibility |
| Performance | benchmark numbers (repeated, variance-controlled) | none dedicated | baseline design, environment noise, and product significance still need judgment |

Any of Security / API Change / Dependency / Data Migration can exercise Arm D
with a candidate mature validator after availability, version pinning, and
integration are verified; Security is only the **suggested** second candidate.

### 10.2 Cross-cutting methods (role, applied to all arms — not a priority level)

| Method | What it is | Note |
|---|---|---|
| Evidence Provenance | receipt↔output-commit binding + clean worktree | **admissibility gate** (Section 7); commit atomicity advisory only |
| Mutation testing | test-sensitivity oracle | applied post-hoc, identically to all arms (Section 6) |
| Property-based / fuzz testing | independent-input generation vs. invariants | supports the independent-expected-value rule |
| Failure-path completeness *(optional)* | does the change handle failure paths? | `failure_completeness_validator.py` exists; experiment adapter/config/fixture cost is unmeasured |
| Safe rollout | canary / feature-flag / rollback discipline | can also be its own study object; adds deployment evidence but does **not** auto-qualify a case (still needs product replay + governance-changed-agent-action evidence) |

Note: `git bisect` is **not** cross-cutting — it applies only when a regression
must be located, so it belongs as a **Bug Fix sub-method**, and only converges
reliably when the good/bad predicate is reproducible and historical commits are
buildable.

### 10.3 Deferred study (weak oracle or high cost)

- Pure readability / maintainability refactor (subjective "better"; behavior-
  preservation half is already covered by characterization tests).
- Concurrency / race-condition fixes (nondeterministic; even TSAN/stress is
  flaky).
- UX / usability (human outcome is partly subjective).
- Accessibility (some WCAG checks are machine-verifiable, but automated checks
  are not a complete accessibility or user-outcome oracle).

## 11. Current Disposition

- Recommended status: **needs owner review** — this is a major-feature
  direction; the scope and thresholds should be approved before anything runs.
- Repo state before drafting: tracked HEAD was clean and `main` aligned with
  `origin/main`; the current worktree contains this in-scope untracked draft.
- Proposal-time check: only existing `common,python` rules apply; no reason
  found to modify shared runtime.
- Memory workflow: no active blocker at drafting.

## 12. First Approvable Tranche (DONE)

DONE = create this Evidence-Backed Engineering Skill Program plan document in
`ai-governance-framework`, recording the Skill / Harness / External Validator /
Governance responsibility boundary, the Bug Fix four-arm experiment, natural
task sourcing, independent oracle, common blind scoring, metrics, commit and
receipt evidence anchoring, decision gates, and stop conditions; add the
candidate-method appendix classified into priority study / cross-cutting
methods / deferred study, all marked **deferred candidates, not implementation
commitments**; sync PLAN and active task; record today's memory via the
canonical writer; run scoped validation; commit and push to `origin/main`. Do
not create or modify any Skill; do not run the experiment; do not add any
validator, schema, runtime, hook, CI, gate, or enforcement; and do not declare
any engineering method effective.
