# ADR-0003 — Inline instruction redundancy in `AGENTS.md` vs the agent document budget

Status: **Proposed — not adopted.** This record measures a collision, answers
what can be answered today, and lays out options. **It decides nothing and
authorizes no implementation.** No code, test, baseline, contract or consumer
repository is changed by it.

Date: 2026-10-27

Surface: `baselines/repo-min/AGENTS.md`, the managed block propagated by
`governance_tools/external_governance_submodule_updater.py`, and the on-demand
documents under `governance/`.

Numbering note: ADR-0002 is in flight in
Gavin0099/ai-governance-framework#258 and is not on `main` at the time of
writing. This record is numbered 0003 to avoid a filename collision. Nothing
here depends on 0002.

Relationship to #260: that open proposal carries the `minimal / standard /
strict` tiering analysis and the per-repository governance-file ratios. This
record deliberately does **not** restate it. The two are complementary — #260
argues about how much governance a repository should carry; this one measures
one specific surface and the limit it collides with — and neither depends on the
other.

## What the owner authorized, and what they did not

Recorded here because it bounds the record itself.

| | |
| --- | --- |
| Authorized | this PROPOSED ADR candidate |
| Priority | real measurement of what the Codex document budget actually loads and cuts |
| Paused | extracting the ~15 KB of inline rules |
| Declined | the 1,176-byte partial extraction — the gain does not justify it, and absence of a failing test is not evidence that moving it is safe |
| Not authorized | changing any existing test or governance contract |
| Not authorized | any change to the 12+ adopted consumer repositories |

Two framings from the owner govern how the evidence below should be read, and
they are adopted verbatim as constraints on this record:

1. **"A test requires this content" does not prove "this design can never
   change."** The tests below establish what the *current* contract demands.
   They do not establish that 15 KB of fully inline instruction is the only way
   to reach the same reliability.
2. **"No test pins it" does not prove "it is safe to move."** Test-quality
   guidance affects how every later change is validated. Whether a section can
   move is a question about meaning, not about which assertions happen to exist.

## Conflict check — `ARCHITECTURE.md` §6.2

Performed before writing this record, as §6.2 requires and as its closing line
makes a governance failure to omit.

| Step | Result |
| --- | --- |
| 1. related titles in `docs/adr/` | `0001-gate3-native-directory-handle-boundary.md` is the only record on `main`. `0002-session-envelope-is-identity-not-closeout-obligation.md` exists only on the open branch of #258 and was read before writing this |
| 2. conflicts found | **none.** 0001 decides Windows native directory-handle ownership and close semantics (`CloseHandle`, handle lifetime) and never mentions instruction surfaces, document loading or `AGENTS.md`. 0002 decides what `artifacts/runtime/sessions/` means for closeout ownership and shares no surface with this record |
| 3. supersession or escalation | neither applies; nothing is superseded. The decision this record asks for would, if taken, reverse a prior **unrecorded** decision (see "The prior decision" below). That is why it needs a record of its own rather than a refactor |
| 4. links to related ADRs | `0001` (no overlap); `0002` (no overlap, in flight in #258). With 0002 this record shares only a reasoning pattern, recorded in `memory/03_knowledge_base.md` as "a mechanical signal is not the semantic property it resembles" |

## Triggers — `ARCHITECTURE.md` §6.1

| Trigger | Fires? |
| --- | --- |
| boundary partitioning | **yes** — which surface carries which instruction responsibility: the always-read `AGENTS.md` or the on-demand `governance/*.md` |
| long-lived interface placement | **yes** — the pinned status vocabulary is matched as literal text by a propagation tool, three test files and one validator. Where those tokens live *is* the interface |
| cross-platform loading strategy | **partially** — agent-platform document loading, not OS platform. Recorded as partial rather than claimed as a full trigger |
| memory ownership strategy | no |
| ABI or calling convention | no |

Two triggers fire, so this record is required rather than optional.

## Context: two goals that are both right

**Goal A — the agent must see the rules that matter.** Writing them into
`AGENTS.md` removes the risk that an agent never loads an on-demand document.

Goal A has a measured limit that must be stated before the options are read:
**inline placement raises visibility; it does not prove the model received the
text, and this framework cannot currently observe the difference.**
`runtime_hooks/core/session_start.py` sets
`_instruction_found = any(f.exists() for f in _instruction_candidates)` and then
`_instruction_loaded = "true" if _instruction_found else "unknown"`, reported
with `source: "observed"`; the audit path passes `allowed_governance_files` as
`files_loaded`. Those are existence and allow-list signals under names that
sound like load confirmation. The surrounding code is honest elsewhere —
`context_integrity` stays `unknown`/`assumed` and `injection_reliance` is
`none` — so this is an observation gap, not a demonstrated breach. But it means
no figure in this record, and no claim in any option below, may be read as
evidence that inline text reached a model.

That is the same shape as the defect in #256 (an envelope's existence read as a
closeout obligation) and as the defect this branch's sibling PR #261 fixes (a
successful `install` read as a runnable command). The pattern is recorded in
`memory/03_knowledge_base.md` as "a mechanical signal is not the semantic
property it resembles"; this is its third instance on a different surface.

**Goal B — the rules must not crowd out other rules.** The agent's
project-instruction budget is finite; an over-long instruction file loses part
of itself.

81% of `baselines/repo-min/AGENTS.md` is one section that applies only when a
human asks to check, update or adopt AI Governance. An attempt was made to move
it to an on-demand document behind a trigger block; the framework's own tests
rejected the move. The section is a **deliberate** inline copy, and it says so:

> This baseline is a propagated, managed consumer instruction copy of the
> canonical manual-update reporting vocabulary in
> `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`. It is intentionally explicit

So the question is not "should duplicated text be de-duplicated". It is which
failure is preferred when Goal A and Goal B cannot both be maximized.

## Q1 — What does the budget actually load, and what is actually cut?

### Mechanics, from the Codex source

`codex-rs/config/src/config_toml.rs` and `codex-rs/core/src/agents_md.rs`:

- `DEFAULT_PROJECT_DOC_MAX_BYTES = 32 * 1024` (32,768 bytes).
- Per directory, the first existing of `AGENTS.override.md`, then `AGENTS.md`,
  then configured fallback names wins. **Each directory contributes at most one
  file.**
- Directories are discovered by walking **cwd upward to the project root, then
  reversing**, so files are concatenated **root first, cwd last**. The root
  `AGENTS.md` consumes the budget before any nested file.
- The budget is a **total**, shared across entries and across environments:
  `remaining` starts at `project_doc_max_bytes` and is reduced after each entry.
  Once it reaches 0, later candidate files are **not read at all**.
- Over budget, the file is **truncated, not skipped**: `data.truncate(remaining)`
  then `tracing::warn!(path, remaining_bytes, "project doc exceeds remaining
  budget; truncating")`. The warning exists at `warn` level — not silent in
  code, but invisible in ordinary use.
- Truncation is byte-level and the result passes through
  `String::from_utf8_lossy`, so a Traditional Chinese file can be cut
  mid-character into replacement characters.
- Host-supplied user/thread instructions are prepended by the loader but are not
  read by it. Whether a host counts them against this budget is **not
  established here**.

### Static projection over the repositories available on this machine

Computed from the files on disk, assuming the root file is the first and only
entry and that the budget is the 32,768-byte default. Consumer repositories are
labelled rather than named: this record is public and two of them are private.
The measurement script and the mapping are in the session that produced this
record.

| repository | root instruction file | bytes | result |
| --- | --- | ---: | --- |
| this framework | `AGENTS.md` | 29,806 | fits; **2,962 bytes** of budget left for every nested file combined |
| consumer A (public) | `AGENTS.md` | 29,224 | fits; 3,544 left |
| consumer B (public) | `AGENTS.md` | 12,341 | fits; 20,427 left |
| consumer C (private) | `AGENTS.md` | 39,093 | **over by 6,325 bytes** |
| consumer D (private) | `AGENTS.md` | 34,498 | **over by 1,730 bytes** |

For the two that exceed the budget, what falls past the cut:

| | cut tail | headings lost | `governance:key` anchors lost | mid-character cut |
| --- | ---: | --- | --- | --- |
| consumer C | 6,325 bytes, 114 lines | `## Governance Contract Output (MANDATORY)`, `### 2.8 Governance Contract Output`, `### When SYSTEM_PROMPT.md is not loaded` | **none** | no |
| consumer D | 1,730 bytes, 35 lines | `### When SYSTEM_PROMPT.md is not loaded` | **none** | no |

### What this corrects

The hypothesis going in was that the cut lands on the repo-specific
`forbidden_behaviors` section, because the five `governance:key` anchors in
`baselines/repo-min/AGENTS.md` (lines 353, 361, 378, 394, 411) all sit **after**
the 16 KB section. The ordering fact is true, and it does mean those anchors are
the last content in the baseline and therefore the most exposed *if* a file is
cut at that point.

**The measurement does not support the hypothesis.** In both repositories that
actually exceed the budget, no `governance:key` anchor is lost. What is lost is
the **Governance Contract Output block** — the instruction that tells the agent
to emit the `[Governance Contract]` block at defined checkpoints, together with
the `When SYSTEM_PROMPT.md is not loaded` fallback notice that tells the agent
what to report when its governance context is incomplete.

That is a worse loss than it first looks, and it is self-concealing: the cut
removes precisely the instruction whose absence makes the omission invisible. An
agent that never received the contract-block instruction does not know it was
supposed to emit one, so the symptom is silence rather than an error.

It also means the exposure is **not** caused by the 16 KB update-intent section
in these two repositories: in both, the tail is a projection block appended after
the baseline content. Shrinking the update-intent section would move the cut
point, not remove the cause.

### What is still unmeasured

- **A real Codex session.** This is a static projection. It does not prove what
  any session loaded, and it assumes the default budget with no host-supplied
  instructions counted. Confirming it requires reading what a real session
  received, or the `warn` line from a run with logging enabled.
- Whether each repository's local Codex configuration already raises
  `project_doc_max_bytes`. A per-machine `~/.codex/config.toml` override would
  change the result for that machine only, invisibly to CI and to any other
  checkout.
- Claude's own loading behaviour. It has no equivalent documented byte budget
  established here; nothing in this record should be read as a measurement of it.
- Nested instruction files. A nested file is read only when cwd is at or below
  its directory, and consumer C's vendored framework copy (26,403 bytes) would
  receive **0 bytes** in that case, because the root file has already exhausted
  the budget. Not verified in a real session.

## Q2 — The options, and what each one risks

### Option 1 — Change nothing

- **Risk:** every adopted repository reads 16.6 KB of update-intent instruction
  at the start of every session for a rule that applies to a minority of them,
  and two repositories measured above are already losing their tail.
- **Benefit:** the inline guarantee holds; zero change risk; nothing touched.

### Option 2 — Reorder: keep the full inline contract, put the safety boundary first

The owner's third alternative, and the only option that addresses the measured
failure without removing any instruction.

- **What it is:** keep every byte of the inline contract, but order the file so
  the forbidden behaviours, the safety boundaries and the contract-output
  obligation come **before** the long update-intent vocabulary, which currently
  sits in the middle and pushes everything after it toward the cut.
- **Benefit:** it reduces the chance that a *critical* rule is the one lost,
  which is the only thing the measurement actually shows going wrong. It
  requires no reversal of the inline decision and no reduction in what the agent
  is told.
- **Cost:** it does **not** reduce bytes or token cost at all. Something is
  still cut when a file is over budget; reordering only chooses what.
- **Caution:** `tests/test_protected_baselines_keep_routing_and_memory_sections_as_siblings`
  already asserts a specific *order* of sections in the two `AGENTS.base.md`
  files (`## AI Governance Update Routing` before `## Memory Update Triggers`
  before the table). Section order is therefore already contract in places, and
  a reordering proposal has to state which orderings it preserves.
- **Open question this option raises:** is ordering even load-bearing for an
  agent that receives the whole file? It matters only in the truncation case.
  If the budget is raised, reordering buys nothing.

### Option 3 — Keep the pinned vocabulary inline, compress the prose around it

- **Headroom:** up to about 10.2 KB (see Q3), with no test change.
- **Cost:** a content rewrite of a governance instruction. It needs review of
  meaning, not a mechanical move, and a shorter instruction can be a worse
  instruction. It should proceed subsection by subsection with the pinned tokens
  asserted after each step.

### Option 4 — Move the section out, keep a trigger block

What was attempted and reverted. Measured: `baselines/repo-min/AGENTS.md`
19,859 → 4,995 bytes; propagated block 16,619 → 2,056 bytes; the moved body
verified byte-identical (16,020 bytes).

- **Requires:** rewriting assertions in three test files and reconsidering
  `_response_envelope_surface_conflicts`. That is a reversal of the prior
  decision, not an adjustment — and it is explicitly not authorized.
- **Risk:** an agent that does not read `governance/*.md` loses the
  update-intent safety rules entirely, which is the failure the current design
  exists to prevent. A trigger block can *order* the agent to read the file;
  ordering is not loading.
- **Note:** availability is not the weak point. `adopt_governance._ensure_governance_markdown_pack`
  copies every `governance/*.md` (38 files, 401,757 bytes) into each adopted
  repository, so a cited `governance/…` path does exist there.

### Option 5 — Make the budget visible instead of shrinking the file

- **What it is:** a check that fails when the **total** project-instruction bytes
  a repository would hand an agent exceed a threshold set below 32,768.
- **Benefit:** turns a silent cut into a visible failure, and is the only option
  that protects a repository whose `AGENTS.md` grows for reasons unrelated to
  this section — which is exactly what the measurement found in consumers C
  and D.
- **Cost:** a new CI check and a threshold to agree on. It must measure the
  total, not one file.
- **Raising the limit is a separate lever, and it is not necessarily
  machine-local.** `project_doc_max_bytes = 65536` in a personal
  `~/.codex/config.toml` applies to one machine, invisibly to CI and to every
  other checkout — that one does hide the problem rather than measure it. But
  Codex's config loader documents a **Project** layer at `.codex/config.toml`
  inside the repository, ranking above the user config, so a raised budget can
  be committed and reviewed like any other setting. Whether this particular key
  is honoured at the project layer is **not documented** in the loader
  reference and must be verified before relying on it. Either way, raising the
  ceiling does not establish that the content deserves to be resident: a bigger
  budget and a shorter instruction are independent questions.

Options 2, 3 and 5 compose. Option 4 excludes nothing but requires the reversal.

## Q3 — Can inline content be reduced without lowering update-flow reliability?

### Measurements

| | bytes | lines |
| --- | ---: | ---: |
| `baselines/repo-min/AGENTS.md` | 19,859 | 424 |
| `## AI Governance Update Intent Rule` section (lines 21–351) | 16,059 (81%) | 331 |
| block the submodule updater propagates (heading → `## Repo-Specific Risk Levels`, so it also carries the Memory Workflow Router) | 16,619 | — |
| `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` | 23,804 | — |

### What is pinned inline, and by what

| subsection | bytes | pinned tokens |
| --- | ---: | --- |
| (preamble) | 3,218 | status-line vocabulary; the 結果 / 原因 / 下一步 opening; adoption-table ordering; the authorization boundary |
| `### Response Envelope Boundary` | 2,225 | `human_readable_adoption_summary: NOT REPORTED`; the invalid-conclusion and valid-partial-conclusion examples |
| `### AI Governance Check Vs Update Intent` | 6,316 | `manual_update` and `destructive_manual_update` templates; `幫我更新最新版 AI Governance`; `governance_tools.f7_full_update`; `update_report_complete=false`; `completion_claim_allowed=false`; the propagated-copy statement |
| `### Test Quality Expectations` | 1,176 | **none** |
| `### F-7 Full Update Semantics` | 2,956 | `幫我更新最新版 AI Governance` only, and that token also appears in the subsection above |

Enforcers:

- `tests/test_update_protocol_manual_status.py` —
  `test_update_protocol_and_baseline_share_manual_status_contract`, and
  `test_all_agent_baselines_route_latest_update_intent_to_f7_and_guard_table_relay`,
  which iterates all four baseline files and requires the F-7 routing tokens and
  both guard flags in each.
- `tests/test_adopt_governance.py` —
  `test_adopted_response_rules_remain_current_after_f7_sections`, which runs a
  real `adopt_existing` into a disposable repository and asserts the **adopted**
  `AGENTS.md` carries the Response Envelope content.
- `tests/test_external_governance_submodule_updater.py` —
  `test_submodule_apply_installs_plain_language_update_opening`, which requires
  the propagated block itself to carry the three-line opening and the worked
  valid-partial-conclusion example.
- `governance_tools/f7_full_update._response_envelope_surface_conflicts`, a
  validator asserted to return `[]` for an adopted repository.

Three test files and one validator — a contract, not an incidental assertion.
`tests/test_governance_drift_checker.py` and `tests/test_f7_full_update.py` read
the baseline only as a fixture and pin no content.

### The byte floor

The pinned subsections are 14,715 bytes. The token, template and example text
they must carry is 4,493 bytes:

| pinned item | bytes |
| --- | ---: |
| status-line block | 1,474 |
| invalid + valid conclusion examples, with the instruction-file-sync paragraph | 1,078 |
| three-line opening paragraph | 667 |
| `destructive_manual_update` template block | 469 |
| `manual_update` template block | 457 |
| propagated-copy statement | 348 |
| **total** | **4,493** |

The ~10.2 KB difference is prose around the pinned vocabulary. That is an
**upper bound** on what a rewrite could recover without touching a test — not a
claim that all of it is removable while the instruction stays as clear.

### What the tests do and do not prove

They prove the current contract requires this text in these files. They do not
prove that fully inline text is the only way to reach the same reliability, and
**making an assertion pass is not evidence that an agent still behaves
correctly.** The converse also holds: `### Test Quality Expectations` carries no
pinned token, and that is not evidence that moving it is safe — it is guidance
that shapes how every later change is validated, so its placement is a question
about meaning. The owner has declined to move it on that basis.

### Duplication against the canonical protocol doc

Compared paragraph by paragraph; line wrapping differs between the files, so an
exact-line diff overstates uniqueness (it reports 49%).

| subsection | paragraphs also in `AI_GOVERNANCE_UPDATE_PROTOCOL.md` |
| --- | ---: |
| (preamble) | 63% |
| `### Response Envelope Boundary` | 42% |
| `### AI Governance Check Vs Update Intent` | 57% |
| `### Test Quality Expectations` | 25% |
| `### F-7 Full Update Semantics` | 0% |
| overall | 41% (40 of 97 paragraphs) |

Not uniform, and the one subsection entirely absent from the protocol doc is the
F-7 stage list.

## Q4 — How to validate with a real consumer, not by editing tests

Any proposal from Q2 must be accepted or rejected on **observed agent
behaviour**, not on a green suite. A sufficient validation, in the order it has
to happen:

1. **Disposable consumer, real layout.** A fresh repository with the framework
   as a registered pinned submodule and a clean framework checkout, adopted
   through `adopt_governance`. Not a synthetic fixture.
2. **A/B, not before/after-only.** Run the same scenarios twice — once with the
   current inline baseline, once with the candidate — in separate disposable
   consumers, so the comparison is behavioural.
3. **Three scenarios per arm, in a real agent session**, on each agent platform
   that the proposal claims to serve:
   - **update:** ask to update AI Governance in the wording a human would use.
     Pass requires routing to F-7 and a report carrying the required status
     vocabulary and the adoption summary — not a pointer-only success claim.
   - **refusal:** a situation that must *not* be reported as current — for
     example only instruction files changed. Pass requires `not_verified` and a
     refusal to collapse instruction-file sync into a framework update.
   - **formal closeout:** an explicit closeout. Pass requires a valid candidate,
     an owner-authorized release and a correct generation increment.
4. **Evidence:** the session transcript and the agent's actual report retained
   as artifacts, plus a receipt anchored to the commit under test. An assertion
   edited to pass is not evidence and does not count.
5. **Honest non-claims.** One session is not a distribution; agent output is
   nondeterministic. A single passing arm shows the rule *can* be followed, not
   that it *will* be. Note also that during the #233 step 3 acceptance the
   `claude` CLI could not complete API turns, so identity and lifecycle were
   real while agency was not — that failure mode must be reported, never
   substituted for.

## The prior decision this record would reverse

The inline copy was decided and enforced but never recorded as an ADR.
Reconstructed from artefacts: the section's own "intentionally explicit"
statement; the test name
`test_update_protocol_and_baseline_share_manual_status_contract`, which says the
protocol and the baseline *share* the contract; and `memory/2026-06-07.md`,
which records F-7 Full Update Semantics being added to the baseline
deliberately.

Its premise: **an agent cannot be assumed to load an on-demand document**, so a
rule whose violation causes a false "AI Governance is current" claim must live in
the file that is always read.

That premise has not been shown to be wrong. What is new is that its cost is now
measurable, and that on one agent platform it collides with a hard limit.

## Recommendation — not a decision

Option 5 first, because the measurement shows the budget is already being
exceeded for reasons that have nothing to do with the update-intent section, and
a check is the only thing that makes that visible rather than silent. Option 2
answers the measured failure without removing instruction, and should be
evaluated against the ordering that is already contract. Option 3 is where the
bytes are and is ordinary reviewable work. Option 4 should be taken only if the
owner decides the on-demand loading guarantee is acceptable, which is a decision
about failure modes rather than file size.

The engineering goal this record serves is not a smaller `AGENTS.md` and not a
green suite. It is the same correctness, traceability and safety from less rule
text and less context — and redundancy that buys measurable reliability is worth
keeping.

## Deliberately not decided

- Whether the premise "an agent cannot be assumed to load an on-demand document"
  still holds per agent platform. It is platform-specific and was not tested.
- The threshold for Option 5, and whether it fails or warns.
- Whether the same question applies to the other three baseline files
  (`AGENTS.base.md` at root and in `baselines/repo-min/`), which the F-7 routing
  test also iterates. Only `baselines/repo-min/AGENTS.md` was measured.
- Whether `_ensure_governance_markdown_pack` copying all 38 governance documents
  (401,757 bytes) into every adopted repository is worth revisiting. Adjacent,
  measured for context, out of scope here.
- What should happen to the two repositories already over budget. They are over
  for a reason this record does not address.
- Whether the `instruction_loaded` signal should be renamed, or made into a real
  load confirmation. It is adjacent and it undermines Goal A, but it is a
  different surface (`session_start.py`) and belongs to its own change.
- The automatic risk classifier. `governance_tools/task_level_detector.py`
  matches English substrings and has no data-destruction category in
  `L0_VETO_KEYWORDS`, so `add UI button to delete saved game files` classifies
  as L0. Verified independently on blob `ba23c38d`, but out of scope here: it
  decides how much process a task gets, not which surface carries an
  instruction.

## Not claimed

- **No decision is taken and no implementation is authorized by this record.**
- The budget figures are a **static projection**, not a real Codex session.
- No independent review of these measurements has happened.
- The reverted Option 4 attempt was validated in the framework repository only,
  never in an adopted repository, because the framework's own tests rejected it
  first.
- The per-repository governance-file ratios that prompted this work are not
  measured here, and nothing in this record depends on them.
