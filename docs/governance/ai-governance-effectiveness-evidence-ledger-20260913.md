# AI Governance effectiveness — evidence ledger

> **Date**: 2026-09-13
> **Baseline**: `main` at `75578e50`
> **Kind**: evidence interpretation ledger. Not a policy, not a backlog.

## Purpose

- Freeze the current evidence classification for governance slimming and
  correctness work.
- Keep separate what is currently conflated: experimental result, structural
  reading of a specification, single case study, and repeated observation.

**This ledger does not generate tasks and does not authorize framework
modification.** An entry recorded here is a statement about what is currently
supported by what evidence, at what strength. Acting on any entry requires its
own separate decision. Finding is not task.

## Correction note

An earlier hypothesis that `pre-push` discarded pushed-ref stdin was rejected
before implementation, after tracing stdin consumption into
`external_tree_inventory_guard.py`. Entries 3 and 4 record the corrected
position. No implementation was performed on the rejected hypothesis.

## Evidence classes

| Class | Meaning |
|---|---|
| `CONTROLLED` | Fixed conditions, treatment and control, difference attributable |
| `DERIVED` | A structural contradiction or gap directly checkable in the canonical source |
| `CASE_STUDY` | One real engineering case with executable evidence, no control arm |
| `OBSERVED` | Same pattern seen across repositories or events, no causal control |
| `NEEDS_EVIDENCE` | Plausible hypothesis, insufficient for a policy decision |
| `NOT_PROVEN` / `COUNTEREVIDENCE` | Current data does not support the stronger claim, or refutes it |

`DERIVED` is not weaker than `OBSERVED`. For claims about what a rule says, it
is stronger: it does not depend on sampling, and one re-read can refute it.

---

## 1. Old unconditional hard stop blocked current-state recovery

- **Evidence class**: `CONTROLLED`
- **Evidence**: two repositories (`financial-pdf-reader`, `meiandraybook`),
  repo-level replication 2/2; hard-stop arm recovered current implementation
  0/6, read-only reconciliation arm 6/6.
- **Claim ceiling**: establishes that the *old* unconditional-stop design
  blocked recovery. It says nothing about the current rule, and it was not
  re-run at the current 250/12000 threshold. The A/B forbade memory cleanup in
  both arms, so the cleanup-and-continue path was never tested. Not run by the
  author of this ledger.
- **Disposition**: historical evidence.
- **Superseded by**: entry 2. The rule this measured no longer exists on `main`;
  PR #172 replaced the unconditional stop with a bounded-maintenance exception.
- **Do not**: cite this as controlled evidence about the current rule.

## 2. Current bounded-maintenance exception has an incomplete verification path

- **Evidence class**: `DERIVED`
- **Evidence**: `governance/SYSTEM_PROMPT.md` at `75578e50`. §7.4 states
  "EMERGENCY 保護 context 品質與安全的 task continuation，不是所有 repo mutation
  的全域禁止" and permits already-authorized bounded maintenance when all six
  conditions hold. Condition 2 requires 「必要狀態已獨立核對」— state already
  independently verified. Across the whole document, 「獨立核對」occurs only in
  that condition, "git" occurs nowhere, and §2.2 authorizes reading only
  `PLAN.md` and `memory/**` — the sources that may themselves be stale.
- **Claim ceiling**: the exception *presupposes* an independent verification it
  never authorizes performing. This is a structural gap, not a measured failure
  rate. No behavioural experiment has been run against the current rule.
- **Disposition**: current GAP.
- **Supersedes**: entry 1 as the statement of the live problem.
- **Note**: the correct framing is completing an existing exception's
  prerequisite, not adding a new carve-out.

## 3. Pre-push subject binding — blocking path is bound

- **Evidence class**: `DERIVED`
- **Evidence**: `scripts/hooks/pre-push` does not read its own stdin, but stdin
  is inherited by its children, and the blocking check consumes it:
  `external_tree_inventory_guard.py --pre-push-updates` calls
  `parse_pre_push_updates(sys.stdin)` and scans raw Git object bytes for the
  refs actually being pushed.
- **Finding**: the blocking newly-reachable-object scan **is** bound to the
  pushed refs. An earlier hypothesis that the hook discarded the pushed-ref
  stdin, and that the blocking gate therefore validated the wrong subject, is
  **rejected**.
- **Claim ceiling**: this covers the object-closure scan only. It is not a claim
  that every pre-push check is subject-bound — see entry 4.
- **Disposition**: hypothesis invalidated before implementation. No change was
  made to the hook.

## 4. Residual subject-binding items, neither a blocking correctness gap

Two pre-push checks are not bound to the pushed ref. Neither is the
false-negative risk entry 3 originally claimed.

**4a. Version-bump advisory describes the wrong subject**

- **Evidence class**: `CASE_STUDY`
- **Evidence**: the hook calls `version_bump_guard.py --head-ref HEAD`, i.e. the
  current checkout's HEAD, inside a block it labels
  "version bump recommendation (advisory)" and terminates with `|| true`.
  Observed instance: a `--dry-run` push of a 3-file branch printed
  "test surface changed" for `tests/test_review_*.py` files absent from the
  pushed ref. That message originates at `version_bump_guard.py:62`.
- **Classification**: advisory accuracy / operational hygiene, **not** a
  blocking safety failure.
- **Claim ceiling**: the output can mislead a reader about what is being pushed.
  It has not been shown to have caused a wrong decision.

**4b. Runtime smoke subject semantics are unresolved**

- **Evidence class**: `DERIVED`
- **Evidence**: the hook runs `run-runtime-governance.sh --mode smoke` against
  `SELF_SMOKE_ROOT`'s working tree, and this check is blocking. `PLAN.md`
  already records the related observation that `pre_task_check` reads
  `project_root / "PLAN.md"` from the working tree.
- **Open question**: whether this check's contract subject is the *active
  framework checkout* or the *pushed candidate ref*. If the former, reading the
  working tree is correct by design and nothing is wrong.
- **Disposition**: semantics review required. **Do not** rebind it to a pushed
  SHA before that question is answered — doing so could convert a correct check
  into a category error.

## 5. Behavioral verification closes a real evidence gap

- **Evidence class**: `CASE_STUDY`
- **Evidence**: `ruiyi-life-map` #81 follow-up. Date-boundary regression
  executed every one of the 302 advertised days plus both out-of-range
  endpoints: 302/302 accepted, both outside days correctly refused. Runtime
  behaviour suite mounted the real component: 7/7, covering focus,
  visibilitychange, timer refresh, pinned-date protection and return-to-today
  listener re-establishment. The prior coverage was `code.includes()` over
  component source.
- **Result**: **product bugs found = 0.** All three interim failures were test
  harness faults, not product defects.
- **Claim ceiling**: establishes that behavioral evidence is more trustworthy
  than source-string evidence. It does **not** establish that behavioral
  verification finds more defects or that it has favourable ROI. n = 1, no
  control arm.
- **Disposition**: KEEP, adopted on **evidence-quality** grounds, not on
  defect-yield grounds. This caveat is permanent and must travel with the entry.
- **Secondary observation**: when a stronger verification capability is first
  introduced, early failures are more likely to come from the harness than from
  the product. Do not escalate a first-run failure to PRODUCT BUG before ruling
  out methodology.

## 6. Review PASS does not mean still current at delivery

- **Evidence class**: `CASE_STUDY`
- **Evidence**: candidate `dc66e923` passed a full multi-round review, including
  four blocker fixes. Before delivery, `main` advanced and the candidate's
  central premise — that the current rule is an unconditional stop — was no
  longer true. The review was not wrong; the baseline moved.
- **Claim ceiling**: one case. It does not support re-reviewing everything
  before every delivery.
- **Disposition**: current GAP — review and evidence currency. The minimal shape
  is a delivery-time check of whether the reviewed assumptions still hold, not
  automated full re-review.
- **Danger signature**: everything is green. CI passes, review passes, the
  document has no defect of its own.

## 7. Truth bound to the wrong tool environment

- **Evidence class**: `CASE_STUDY`
- **Evidence**: `ai-governance-framework` #173. CI pins Node 22.13.0 (npm 10).
  A lockfile regenerated locally on Node 24 (npm 11) dropped the hoisted
  `@emnapi/core` and `@emnapi/runtime` entries; `npm ci` passed locally and
  failed on CI with `Missing: @emnapi/core@1.10.0 from lock file`. Neither
  `--os=linux` nor `--cpu=x64` restored them. Regenerating with `npm@10.9.2`
  fixed it and reduced the diff from 164 insertions / 68 deletions to 111
  insertions / 0 deletions, verified under both npm majors.
- **Claim ceiling**: supports a narrow conclusion — for artifacts as sensitive
  to package-manager version as a lockfile, the generating and validating
  environments must be aligned. It does not support a general toolchain identity
  framework covering OS, compiler, Python, Java or shell.
- **Disposition**: repo-local concrete fix, `ruiyi` / consuming repos.

## 8. Governance also blocks legitimate work

- **Evidence class**: `OBSERVED`
- **Evidence**: the pre-push installation-integrity self-check assumes
  `<toplevel>/.git` is a directory and probes `<toplevel>/.git/hooks/pre-push`;
  in a linked worktree `.git` is a file, so a legitimate push is rejected as
  `INSTALLATION_MISMATCH`. Also style enforcement and over-strong causal
  attribution in consumer repositories.
- **Claim ceiling**: fail-closed. These reject things that should pass; none has
  been shown to pass something that should fail.
- **Disposition**: SIMPLIFY / bounded enforcement candidates.

## 9. Exact artifact / commit / binary identity has caught real problems

- **Evidence class**: `OBSERVED`
- **Evidence**: stale binary detected in CFU; release evidence needing to be
  bound to the correct revision; consumer identity cases.
- **Disposition**: **KEEP.** Strongest KEEP in this ledger — multiple
  repositories, real catches.
- **Note**: this is what makes entry 3 matter. A PASS means something only when
  it was measured against the right object.

## 10. Claim ceiling as a control

- **Evidence class**: `OBSERVED`
- **Evidence**: repeated cases where partial verification would otherwise have
  been reported as full completion — managed PASS vs Windows acceptance, package
  complete vs device qualification, local PASS vs delivered on main.
- **Disposition**: **KEEP.**

## 11. Current state can drift across memory, PLAN and Git

- **Evidence class**: `OBSERVED`
- **Claim ceiling**: establishes that drift exists. Does **not** establish that
  drift causes wrong action — see entry 16.

## 12. Duplicated records carry maintenance cost

- **Evidence class**: `OBSERVED`
- **Evidence**: smoke heading promotion, repeated delivery closeouts, the same
  narrative across PLAN, memory, receipt and knowledge base.
- **Mechanism observed**: the `active-task-summary` projection surface grows
  monotonically, and `memory_record` derives idempotency solely from a marker
  line present in that file, so the surface cannot shrink without weakening
  dedup for the removed identities.
- **Claim ceiling**: SIMPLIFY candidate. Which copies are safe to remove is not
  established.

## 13. Finding inflation can hide the real defect class

- **Evidence class**: `OBSERVED`
- **Evidence**: `ruiyi-life-map` #83 accumulated 19 inline findings across seven
  review rounds; the three P1s were one recurring defect class — existing data
  not preserved before writes — raised three times in successive rounds.
- **Claim ceiling**: suggests review should converge on unclosed invariants
  rather than finding counts. Not measured.

## 14. Governance pipeline cost

- **Evidence class**: `NEEDS_EVIDENCE`
- **Missing**: token, wall-clock and engineer-time quantification.

## 15. Governance-of-governance maintenance cost

- **Evidence class**: `NEEDS_EVIDENCE`
- **Missing**: which records are necessary provenance and which are ceremony.

## 16. Overall governance ROI

- **Evidence class**: `NEEDS_EVIDENCE`
- **Data points available**, deliberately one of each sign:
  - *Avoided rework*: the currency check on `dc66e923` stopped a stale delivery
    before a PR and review round were spent on it. Cost was one document
    comparison.
  - *No contribution*: for the #173 lockfile defect, the local pre-push gate
    passed and CI caught the problem afterwards.
- **Method caveat**: the second data point is a **coverage gap**, not a gate
  failure. The pre-push hook never claimed to validate lockfile synchronisation.
  Scoring a gate against a failure mode outside its scope produces spurious
  zeros. Any future gate × failure-mode analysis must first separate
  `IN_SCOPE_AND_CAUGHT`, `IN_SCOPE_BUT_MISSED`, `OUT_OF_SCOPE` and
  `NOT_APPLICABLE`. Only `IN_SCOPE_BUT_MISSED` is a gate failure.

## 17. Stale memory necessarily causes wrong product action

- **Evidence class**: `NOT_PROVEN`
- **Evidence against**: fresh-context probes where the agent recovered current
  work unaided.
- **Disposition**: not a general conclusion. Not a basis for rebuilding the
  memory framework.

## 18. More gates means more reliability

- **Evidence class**: `NOT_PROVEN`
- **Disposition**: gate count is not a maturity measure. At most, specific gates
  have local value.

## 19. Every consumer needs the same framework fix

- **Evidence class**: `COUNTEREVIDENCE`
- **Evidence**: cases where a suspected framework fix was `NOT_REQUIRED` for the
  consumer, and a consumer hook identity concern that proved to be a
  misdiagnosis.
- **Disposition**: no fleet-wide blanket rollout. Replay a trimming slice
  against a repository that actually experienced that pain point.

---

## KEEP and GAP are separate

**KEEP** — existing controls with evidence behind them:

| Control | Evidence class |
|---|---|
| Exact artifact / commit / binary identity | `OBSERVED`, multiple repositories |
| Claim ceiling | `OBSERVED`, multiple cases |
| Bounded independent review | `OBSERVED` |
| Stop / downgrade / withdraw | `OBSERVED` |
| Behavioral verification | `CASE_STUDY`, n = 1, adopted for evidence quality, product bugs found = 0 |

**GAP** — capabilities that are absent, not present:

| Gap | Evidence class |
|---|---|
| Current-state verification path for the bounded exception | `DERIVED` |
| Runtime-smoke subject semantics (unresolved, may be correct by design) | `DERIVED` |
| Review / evidence currency at delivery | `CASE_STUDY` |
| Tool-environment binding for version-sensitive artifacts | `CASE_STUDY` |

A gap in the second table must never be quoted as if it were a control in the
first.

## Truth Binding

`Truth Binding` — is what the agent currently treats as true bound to the right
time, object, baseline and environment? — is recorded here as an **analysis
lens, not a component**.

It is descriptively useful: entries 2, 6 and 7 are binding failures, and 4b is
an unresolved binding question. It
is not prescriptively unified: the remedies differ completely — a currency check
for time and baseline, passing the subject explicitly for object, pinning and
verifying the tool version for environment. A single "Truth Binding" mechanism
would only group four unrelated implementations under one name.

**Do not build a Truth Binding framework. Use it to ask whether two problems are
the same problem.**
