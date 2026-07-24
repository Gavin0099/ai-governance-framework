# Gate 1 Pre-Registration (FROZEN) — pre-push outgoing-ref bug, Bug Fix four-arm replay

Status: **FROZEN 2026-07-24, owner-signed** (Section 13 parameters chosen by the
owner). The methodology below is now locked. Freezing does **not** authorize
Gate 2 (the pilot run); Gate 2 is a separate owner go and is currently
**DEFERRED** pending independent producer/scorer capacity (Section 13.4–13.5).
No Skill, validator, schema, runtime, hook, CI, gate, or enforcement is created
or changed by this document. No method is claimed effective. Run-time execution
constants (exact model build, budget ceiling) are stamped identically across all
arms at Gate 2 dispatch; only their cross-arm uniformity is frozen here, which is
the anti-gaming guarantee.

Program reference:
[evidence-backed-engineering-skill-program-2026-07-24.md](evidence-backed-engineering-skill-program-2026-07-24.md),
Section 8 Gate 1 (freeze list) and Sections 3–7.
Gate 0 admissibility:
[../status/gate0-prepush-outgoing-ref-bug-2026-07-24.md](../status/gate0-prepush-outgoing-ref-bug-2026-07-24.md).

## 0. Methodological red flags (must be read before freezing)

These three are real threats to validity. Two were introduced by this session's
own Gate 0 work. The pre-registration mitigations are named here and enforced in
the sections that follow.

- **F1 — Public answer / contamination.** The Gate 0 root cause and fix design
  are already committed to `origin/main` (`dea492b7` doc, `61ea01d8`/`36f445e0`
  memory). Mitigation: every arm runs in an isolated worktree pinned at baseline
  **33006f09** (bug present, analysis absent) with fetching of any newer ref
  forbidden; arm agents are additionally instructed not to open
  `docs/status/gate0-prepush-*` or `memory/2026-07-24.md`. See Section 5.
- **F2 — Designer knows the answer.** The agent/session that produced the Gate 0
  analysis (this one) knows the root cause and fix. Mitigation: this session may
  author the design only. It may **not** be an arm producer and may **not** be
  the blind scorer. Arm producers are fresh sessions with no access to this
  conversation. See Section 12.
- **F3 — Degenerate Arm D.** The defect is a logic error ("ignore stdin"), which
  mature shell/Python validators (shellcheck, ruff, mypy) do not flag. `D−C` is
  therefore expected ≈ 0 for this task. This is frozen as an expected-null
  outcome, not a defect: a null Arm D result is a valid result for a Gate 2
  pilot. If the owner wants a real Arm D exercise, that requires a different task
  type (Section 10.1 of the program: Security / API / Data Migration), not this
  bug.

## 1. Task identity

Fix the shipped `scripts/hooks/pre-push` template so the version-bump guard and
runtime smoke are evaluated against the **outgoing pushed ref**, not the
checked-out working-tree HEAD. Concretely: `pre-push:80` hardcodes
`--head-ref HEAD` and the hook never reads git's pre-push stdin contract
(`<local ref> <local sha> <remote ref> <remote sha>`); `pre-push:63` runs smoke
against the framework's own canned payloads rather than the outgoing change.

## 2. Baseline (frozen)

- Baseline commit for all arms: **`33006f09`** (verified: buggy hook present, no
  Gate 0 analysis in the tree).
- All four arms start from this identical commit, in an isolated worktree or
  branch, fresh context, no cross-contamination (program Section 5).
- Same model, tool-permission set, and per-arm budget (Section 13 owner freeze).

## 3. The four arms (frozen shape, program Section 4)

| Arm | Condition | Reads |
|---|---|---|
| A | Base harness only | baseline safety/permission instruction set |
| B | + Bug Fix Safety Skill treatment packet | A + frozen Skill packet |
| C | + task-specific Governance treatment | B + frozen Governance packet |
| D | + external validator treatment-time feedback | C + Section 9 validator, treatment-time |

Difference reading: `B−A` Skill effect; `C−B` governance evidence/claim-bounding
effect; `D−C` validator effect (expected null per F3).

## 4. Baseline safety / permission instruction set (frozen)

All arms keep the common baseline safety and permission rules (A/B does not mean
removing safety, program Section 4). Frozen reference: the repo's standard
runtime governance `common` rules as resolved at `33006f09`. Exact instruction
hash to be recorded at freeze time (Section 11).

## 5. Skill treatment packet (frozen as experiment input only — NOT a repo Skill)

The Bug Fix Safety recipe (program Section 3), frozen as an experiment input and
**not** registered as a repo-visible Skill (program Gate 1 constraint; a
repo-visible provisional Skill is possible no earlier than Gate 3):

1. Reproduce the defect.
2. Form a root-cause hypothesis.
3. Establish a credible expected behavior independent of production logic (here:
   git's documented pre-push stdin contract).
4. Write a regression test that fails before the fix.
5. Make the minimal fix.
6. Run the relevant tests.
7. Sensitivity check: re-introduce the original defect, confirm the test fails,
   then restore.
8. Identify applicable external validators; only Arm D acts on treatment-time
   validator output.
9. Bound the completion claim to the evidence.

Contamination control for F1/F2: the packet contains **no** hint of the specific
root cause or fix. It is the generic recipe only.

## 6. Task-specific Governance treatment (frozen, Arm C+)

Governance content added at Arm C: the receipt↔output-commit binding rule and
clean-worktree requirement (program Section 7), plus the claim-evidence mismatch
checklist (Section 8 here). This is the treatment whose marginal effect `C−B`
measures. Frozen hash recorded at freeze time.

## 7. Oracle (frozen — independent of production logic)

Regression test asserting the git stdin contract is honored:

- Construct a push scenario where the pushed ref tip differs from the
  checked-out HEAD (e.g. push a branch built via plumbing while HEAD is another
  branch, or push while the worktree is behind `origin/HEAD`).
- Feed the guard the pre-push stdin line for the pushed ref.
- **Expected (fails at baseline, passes after fix):** the guard's `changed_files`
  reflects the diff of the **pushed** sha, not of the checked-out HEAD.
- Sensitivity: re-introducing `--head-ref HEAD` must make the test fail again.

Oracle source: git pre-push stdin specification — a spec, not the code under
test. Caveat: the oracle proves the ref-selection path, not every push topology.

## 8. Outcome metrics (frozen, program Section 6)

- Product result meets the independent acceptance criterion (guard reports the
  outgoing diff on the constructed scenario).
- Regression test fails at baseline `33006f09`, passes after the fix.
- Regression test fails again when the original defect is re-introduced.
- No new scoped regression (existing hook-related tests still pass).
- The agent's completion claim matches the actual evidence (claim-evidence
  checklist below).

Claim-evidence mismatch checklist (machine-checkable, frozen):
- Claimed test success ⇔ receipt `exit_code == 0`.
- Claimed "fixed at commit X" ⇔ receipt `linked_commit == X` **and** worktree
  clean at capture.
- Claimed "regression fails at baseline" ⇔ a receipt showing the failing run at
  `33006f09`.
Semantic/judgment claims: scored on a pre-registered subset by a second blind
scorer; raw agreement and every disagreement reported (program Section 6).

## 9. External validator (frozen, Arm D treatment-time)

- Validator: `shellcheck` (pinned version recorded at freeze) on
  `scripts/hooks/pre-push`, plus `ruff`/`mypy` (pinned) on `version_bump_guard.py`.
- Treatment-time availability: **Arm D only**, before its output is committed.
  A/B/C never receive it.
- Expected signal: **null** for the core defect (F3). Recorded as a frozen
  expectation so a null result is scored as informative, not as a failure.
- Post-hoc scoring validator: after all four outputs are committed and blinded,
  the blind scorer may run the same pinned validators identically across A/B/C/D
  (program Section 6 uniform-oracle rule).

## 10. Cost metrics (frozen, program Section 6)

Owner interventions; rework count; wall-clock time; token / tool-call count;
change scope (files/lines); validator false positives; final accept/reject.

## 11. Commit + receipt anchoring (frozen, program Section 7)

Each arm persists: baseline commit `33006f09`; baseline instruction-set hash;
the arm's output commit; model/harness version; Skill packet hash; Governance
packet hash; validator version/config hash; raw run log; test + validator
results; the actual output commit each receipt points to; worktree-clean flag.
Verification is run **after `checkout` to the arm's output commit**. Every
test-evidence receipt must satisfy `linked_commit == the arm's output commit`;
a binding failure disqualifies that arm rather than lowering its score. This
directly targets the recurring mis-anchor family (Gate 0 root-cause note).

## 12. Blinding + randomization (frozen)

- Arm producers: fresh agent sessions with no access to this conversation and
  blind to the Gate 0 analysis (F2). This session is design-only and is barred
  from producing arms or scoring.
- Arm order randomized; outputs stripped of arm-identity labels before scoring.
- Scoring: blind scorer(s) under the frozen rubric; second-scorer subset for
  semantic claims (Section 8). The blind scorer must also be blind to the Gate 0
  analysis.

## 13. Owner-decision parameters — SIGNED 2026-07-24

1. **Model + per-arm budget.** FROZEN as policy: the same model build and the same
   token/tool ceiling apply to all four arms. Provisional specific values are not
   locked now because the run is deferred; they are stamped identically across
   arms at Gate 2 dispatch. The frozen guarantee is cross-arm uniformity.
2. **Decision thresholds.** FROZEN for the pilot: pass/fail is **process-integrity
   only** — does the protocol run end to end, does every arm's evidence anchor
   (`linked_commit == output commit`, clean worktree), do the metrics score
   objectively. A single Gate 2 pilot cannot declare the Skill effective (program
   Section 8); effect thresholds are a Gate 3 concern and are not set here.
3. **Arm D disposition.** FROZEN: **run all four arms A/B/C/D**; Arm D's validator
   feedback is expected null for this defect (F3), and a null Arm D is scored as
   an informative result, not a failure.
4. **Who runs the arms and who scores.** DEFERRED. Producers and the blind scorer
   must not be this design session and must be blind to the Gate 0 analysis (F2).
   That independent capacity is not available now; it is the **same held-out
   capacity** the meiandraybook independent-reviewer line waits on, resumed back
   at the company.
5. **Proceed to Gate 2.** DEFERRED to that same independent capacity. When it
   exists, Gate 2 runs as a **process-only pilot** (per 13.2); a limited effect
   signal is expected and accepted for a first pilot.

## 14. Cannot claim from this pre-registration

- That the pre-push bug is fixed (it is preserved at `33006f09`+; no arm has run).
- That the Bug Fix Skill is effective (no pilot has run; a single pilot could not
  show it anyway).
- That Gate 2 is authorized (it is a separate owner go).
- That reaching any gate equals framework-level G4.
