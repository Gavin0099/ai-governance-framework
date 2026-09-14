# AI Governance effectiveness — evidence ledger

> **Date**: 2026-09-13
> **Baseline**: `main` at `75578e50`
> **Kind**: evidence interpretation ledger. Not a policy, not a backlog.
> **Original assessment**: `54ffb007`
> **Reconciled**: 2026-09-13 — see *Reconciliation as of 2026-09-13*
> **Subsequent reconciliation**: 2026-09-14 — see *Reconciliation as of 2026-09-14*

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

Entries 7 and 16 carry factual corrections to the original frozen assessment
(`54ffb007`): the event source and the pushed lockfile mechanism in entry 7, and
the event source and the hook claim in entry 16. These were wrong when written.
Changes in status caused by later evidence are not corrections and are recorded
only under the dated reconciliation sections below.

## Provenance precision (2026-09-14)

Throughout this ledger, `dc66e923` denotes a **local unpublished historical
candidate**. It is a provenance locator only: not remotely retrievable from the
repository and not authority. Its references preserve the recorded historical
case; they do not supply an independently retrievable review or a current-state
verification result.

`afdb60b3` and `7e61e733` are **local historical commit identities**. The
following remote counterparts are **patch-equivalent**, not the same commits
and not identity-equivalent. The mapping was mechanically rechecked on
2026-09-14 with `git show --pretty=format: --no-ext-diff <commit> | git patch-id --stable`;
each pair produced the stable patch-id shown below.

| Local historical commit | Remotely retrievable patch-equivalent commit | Stable patch-id |
|---|---|---|
| `afdb60b38c63941758a47668f3585045c1923761` | `678850c7e5f4e2ce63aa0040c44ef85af1844488` | `b2f63c38636529d6c6591847f7d6e72225aec1d5` |
| `7e61e733518956d2f2cbe85a8f3115926a001dd8` | `f18860b32b5e11932faca36ba92239ea5d0a12a0` | `70c006b5ee50893f50ae656f7345a8b245f2837f` |

Remote availability was checked through GitHub's commit API and
`git ls-remote origin refs/heads/codex/review-delivery-integration`, which
resolved to `f18860b32b5e11932faca36ba92239ea5d0a12a0`; both remote
counterparts are reachable from that anchor. Patch equivalence does not transfer
commit identity, review coverage, adoption or delivery authority. This
clarifies provenance only; it does not reassess S2, S3 or S4, or change the
2026-09-13 delivery snapshot.

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

- **Reconciliation**: status changed after this assessment; see *Reconciliation as of 2026-09-13*.
- **Factual correction (2026-09-14)**: the exclusivity inference above is
  withdrawn; see *Entry 2 — correction of the original authorization premise*
  in the 2026-09-14 reconciliation. Retained wording is historical, not a
  supported current conclusion.

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

- **Reconciliation**: status changed after this assessment; see *Reconciliation as of 2026-09-13*.

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

- **Reconciliation**: status changed after this assessment; see *Reconciliation as of 2026-09-13*.

## 7. Truth bound to the wrong tool environment

- **Evidence class**: `CASE_STUDY`
- **Evidence**: `ruiyi-life-map` #87. CI pins Node 22.13.0 (npm 10). A lockfile
  regenerated locally with npm 11.6.2 and pushed at `e96eace` carried the hoisted
  `@emnapi/core` and `@emnapi/runtime` upgraded to `1.11.3`, conflicting with the
  exact `1.10.0` that `@rolldown/binding-wasm32-wasi` requires; `npm ci` passed
  locally and failed on CI with `Missing: @emnapi/core@1.10.0 from lock file`.
  An intermediate local regeneration with npm 11 dropped the hoisted entries
  instead, and neither `--os=linux` nor `--cpu=x64` restored them. Regenerating
  with `npm@10.9.2` fixed it and reduced the diff from 164 insertions / 68
  deletions to 111 insertions / 0 deletions, verified under both npm majors.
- **Correction**: the original frozen ledger attributed this event to framework
  PR #173 and described the pushed lockfile change as dropped entries.
  Subsequent source verification established that the event was ruiyi PR #87,
  and that pushed head `e96eace` upgraded the relevant entries to `1.11.3`.
- **Claim ceiling**: supports a narrow conclusion — for artifacts as sensitive
  to package-manager version as a lockfile, the generating and validating
  environments must be aligned. It does not support a general toolchain identity
  framework covering OS, compiler, Python, Java or shell.
- **Disposition**: repo-local concrete fix, `ruiyi` / consuming repos.

- **Reconciliation**: status changed after this assessment; see *Reconciliation as of 2026-09-13*.

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
  - *No contribution*: for the ruiyi #87 lockfile defect, the installed local
    pre-push hook did not block the successful push, and CI caught the problem
    afterwards. The exact checks the hook executed were not established.
  - *Correction*: the original frozen ledger attributed this data point to
    framework PR #173 and stated that the local pre-push gate passed. The event
    was ruiyi PR #87, and a hook that did not block a push is not evidence that
    its checks ran and passed.
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

_As frozen in the original assessment `54ffb007`. The reconciled classification is under *Reconciliation as of 2026-09-13*; do not quote the GAP table below as current._

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

## Reconciliation as of 2026-09-13

This section records how evidence gathered after the original assessment
changed the status of its entries. The original assessment above is retained as
written, apart from the factual corrections marked in entries 7 and 16. Nothing
here generates a task or authorizes framework modification.

Every delivery or protection state below is a snapshot at this reconciliation
point and is not maintained by this ledger. Reverify it before relying on it as
current authority.

Anchors used at this reconciliation point: framework `origin/main` `75578e50`
and ruiyi `origin/main` `e673799`, both fetched on 2026-09-13.

### Entry 2 — current-state verification path

Resolved as a governance gap by the owner-adopted contract
`docs/governance/current-state-claim-verification-20260913.md` at commit
`8838027b`. At this reconciliation point (2026-09-13) the adopted contract is
local and has not been incorporated into canonical main. Canonical delivery
status is not maintained by this ledger and must be reverified before relying on
it as current-main authority.

### Entries 3 and 4 — pre-push subject binding

The original blocking-subject hypothesis is invalidated, as entry 3 already
records. 4a, the version-bump advisory describing the wrong subject, is advisory
hygiene and deferred. 4b, the runtime-smoke subject semantics, remains a
semantics-review question only; nothing is to be rebound before that question is
answered.

### Entry 6 — review PASS and currency

Not a single gap. It separates into four statements:

- **Reviewed-head currency semantics**: covered by canonical doctrine on main at
  `75578e50` — `governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md`, section
  "Reviewed-head preservation", and `governance/REVIEW_CRITERIA.md` §2.2. Not a
  governance gap.
- **Mechanical enforcement of reviewed-head currency**: not present on main at
  this reconciliation point (2026-09-13); no reviewed-head check was found in
  its governance tools, scripts or workflows. Local commits `afdb60b3` and
  `7e61e733` implement one and were not on main at that point. Whether to deliver
  them is a delivery decision, not a governance gap, and their status must be
  reverified.
- **Explicit baseline dependency**: handled by the adopted contract's
  `HISTORICAL -> CURRENT_STATE` bridge and derived-inference revalidation. The
  `dc66e923` premise was stated explicitly in that document.
- **Implicit or unrecorded baseline dependency**: observation only. No case has
  been reproduced in which an unrecorded baseline moved, an old review PASS was
  then accepted by a delivery path, and the decision was wrong as a result.

### Entry 7 — tool environment

- **Reproduced failure**: a lockfile generated with npm 11.6.2 and pushed at
  `e96eace` was rejected by `npm ci` on CI (Node 22.13.0, npm 10), and a Codex
  review reported the same rejection on npm 11.4.2. It did not reach main.
- **Detection**: in the reproduced case the required `test` check, which runs
  `npm ci`, detected and blocked it through the normal pull-request path.
- **Universal enforcement**: no. At this reconciliation point (2026-09-13) ruiyi
  branch protection required `test` and `governance-drift` with
  `enforce_admins` false, so an administrator could bypass the required checks.
  Protection settings are not maintained by this ledger.
- **npm 10 lockfile breaking npm 11 contributors**: not reproduced. At the
  anchor `e673799`, a real `npm ci` of ruiyi's lockfile passed under both npm
  10.9.2 and npm 11.6.2.
- **Written npm-major guidance**: absent; `dependency_pins.md` explicitly leaves
  lockfile synchronisation to `npm ci`.
- **Result**: an npm-major pin or binding is not justified, and knowledge-base
  guidance is not justified yet. The reproduced case supports only that a
  mismatched generator can produce an incompatible lockfile, which the existing
  required `npm ci` check detected.

### Entry 16 — overall ROI

The source and hook wording are corrected in place. The classification of the
second data point as a coverage gap rather than a gate failure is unchanged, and
overall ROI remains `NEEDS_EVIDENCE`.

### KEEP and GAP, reconciled

**KEEP**: unchanged from the original assessment.

| Original GAP | Status at this reconciliation point |
|---|---|
| Current-state verification path for the bounded exception | Resolved as a governance gap by the owner-adopted contract `8838027b`; local at 2026-09-13 |
| Runtime-smoke subject semantics | Unresolved; semantics review only |
| Review / evidence currency at delivery | Withdrawn as a single gap; see entry 6 above |
| Tool-environment binding for version-sensitive artifacts | Withdrawn as a gap; see entry 7 above |

Unresolved observations retained: runtime-smoke subject semantics; implicit
review baseline dependency; version-bump advisory accuracy.

### Truth Binding

The lens is unchanged. Its listed environment remedy, pinning and verifying the
tool version, is not supported by the entry 7 evidence: in the reproduced case
the existing required `npm ci` check detected the incompatible lockfile, and no
pin is recommended.


## Reconciliation as of 2026-09-14

This is a subsequent dated observation, not a rewrite of the 2026-09-13
reconciliation. S1 was owner-adopted locally at `8838027b` on 2026-09-13 and
was not canonical on main at that reconciliation point; that snapshot remains
unchanged.

S1 subsequently underwent evidence/provenance, anchor-OID and lifecycle
amendments. The unpublished-source clarification and `REAL`, `RECORDED-ONLY`
qualification were followed by owner re-adoption; the current-state anchor was
then bound once to an immutable OID, followed by a further owner re-adoption.
Those intervening amendments are retained in the commit history and the
canonical contract's correction note and adoption metadata.

### Entry 2 — correction of the original authorization premise

The original assessment incorrectly treated the memory-synchronization list in
`governance/SYSTEM_PROMPT.md` §2.2 at `75578e50` as an exclusive authorization
boundary. It lists required synchronization inputs; it does not prohibit reading
other repository sources. The same baseline's §2.3 addresses proportionate
exploration, and `AGENTS.md` permits reading and exploring repository files.
The absence of the word `git` therefore does not establish that independent
verification was unauthorized.

The entry 2 inference that the exception "never authorizes" verification, and
its `DERIVED` authorization-gap conclusion on that basis, are withdrawn as
unsupported from the outset. This is a factual correction, not a claim that the
rule changed later. The original wording and the 2026-09-13 reconciliation
remain historical records; neither should be used to assert an exclusive-read
restriction. This correction does not reassess S1's separately evidenced
current-state claim contract, its adoption or delivery, or S2/S3/S4.

### S1 canonical delivery

[PR #174](https://github.com/Gavin0099/ai-governance-framework/pull/174) was
merged at `2026-09-14T02:19:39Z`.

| Identity | Verified value |
|---|---|
| Reviewed exact head | `407406dadcbcafaa51b752da07eaf699ed886e5a` |
| Merge commit | `1b212de77f6ced71e50a57c8f43bbe80c393264c` |
| Canonical blob | `98a993115bd717ac9f46756c2df1805b71978407` |
| Canonical path | `docs/governance/current-state-claim-verification-20260913.md` |

At this reconciliation point, the current-state verification contract is
**owner-adopted + canonical on main**.

The checks were bound to the remote `main` OID
`1b212de77f6ced71e50a57c8f43bbe80c393264c`, resolved on 2026-09-14:
PR #174 reports `MERGED` with the exact head and merge commit above; its
completed Codex review identifies `407406dadc`; `git merge-base --is-ancestor`
confirms the full reviewed head is reachable from that main OID; and
`git ls-tree` at that OID returns the canonical path and blob above. The
contract's owner re-adoption metadata and the owner's 2026-09-14 reconciliation
instruction establish adoption; merge status alone is not adoption authority.

Current delivery state is a dated observation and must be reverified before
being relied on as present-day repository state.

This update completes S0's provenance and subsequent-state account only. It
does not reopen S1-S4 analysis, reassess S2/S3/S4, create a task or governance
rule, change memory, or decide S0 delivery.
