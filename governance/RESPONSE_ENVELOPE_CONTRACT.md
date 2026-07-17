---
audience: agent-runtime
authority: reference
can_override: false
overridden_by: AGENT.md
default_load: on-demand
---

# Response Envelope Contract v0.5

> v0.2 (2026-06-24): added the Evidence Term Glossing plain-language
> requirement (advisory; not validated by `response_envelope_validator.py`).
> v0.3 (2026-06-24): added the Next-Step Judgment required closing section
> (advisory; decision-readability for completion-class reports).
> v0.4 (2026-07-17): added an opt-in mechanical response-quality check to
> `response_envelope_validator.py` (`--check-response-quality`); default
> validator behavior is unchanged, and no gate enables the check.
> v0.5 (2026-07-18): added an opt-in plain-summary check
> (`--check-plain-summary`) after direct owner feedback that a
> structurally valid report was still unreadable; default behavior remains
> unchanged, and no gate enables either check.

## Purpose

This contract defines the minimum governance fields for structured agent
responses when a response is produced by a recognizable workflow event.

The goal is not compression. The goal is to keep task authority, scope, claim
ceiling, evidence, and risk disclosure separate enough that reviewers can audit
what was done, what was claimed, and what remains unproven.

## Authority Boundary

This contract is a reporting convention and reviewer-facing schema.

It does not change:
- closeout runtime enforcement
- evidence admissibility rules
- claim ceiling semantics
- risk disclosure semantics
- session_end hook behavior
- gate policy behavior

## Event-Driven Mode Rule

`mode` must describe the workflow event that produced the response. It must not
be treated as an agent-selected style preference.

Every envelope that includes `mode` must also include `mode_source`.

Allowed initial mode mappings:

| Event | mode | mode_source |
| --- | --- | --- |
| session_end hook completed | `CLOSEOUT` | `session_end_hook` |
| in-progress status update | `PROGRESS` | `intermediate_update` |
| scoped files staged for commit | `PRE_COMMIT` | `git_staged_diff` |
| validation command completed | `VALIDATION` | `validation_command` |
| out-of-scope change detected | `SCOPE_ALERT` | `scope_boundary_check` |

Agents may fill the envelope content, but they must not choose a higher-authority
mode than the event source supports.

## Required Fields

Minimum response envelope:

```yaml
mode: CLOSEOUT
mode_source: session_end_hook
task: RS-Drift-2 presentation cleanup
task_authority: user_request
scope:
  - specs/verification_status.md
  - specs/en/verification_status.md
done:
  - packet statistics moved to Evidence Packet Summary section
claim_ceiling:
  - reporting convention documented only
  - no runtime enforcement claim
not_claimed:
  - new verified entries
  - generated statistics
  - governance cleanup
evidence_refs:
  - command: validate_wiki_frontmatter.py
    result: PASS
  - command: npm.cmd run build
    result: PASS
risk:
  - zh page incidental cleanup; existing mojibake text organized, no statistics semantic change claimed
next_action: scoped stage and commit, then review staged diff
```

Required field meanings:
- `mode`: event-derived response mode.
- `mode_source`: source event or command that justifies the mode.
- `task`: bounded task label or short task description.
- `task_authority`: source of authority for the task.
- `scope`: exact files, artifacts, or surfaces covered by the response.
- `done`: completed work inside scope.
- `claim_ceiling`: explicit upper bound on what the response is asserting.
- `not_claimed`: explicit claim ceiling for this response.
- `evidence_refs`: validation commands, artifacts, or reviewer sources supporting the `done` claim.
- `risk`: scope drift, incidental cleanup, claim inflation, or evidence maturity risks.
- `next_action`: one concrete next step, or `none` when no next action is being recommended.

## task_authority Values

Allowed values:
- `user_request`: explicitly requested or authorized by the user.
- `followup`: directly follows a previously authorized task without expanding scope.
- `hook_trigger`: produced by a workflow hook or runtime event.
- `autonomous`: initiated by the agent without direct user authorization.

If `task_authority: autonomous`, the response must include a `risk` entry that
explains why the work did not exceed the current DONE boundary.

## evidence_refs Rules

Each evidence reference must include:
- `command` or `artifact`
- `result`

Valid `result` values:
- `PASS`
- `FAIL`
- `NOT RUN`
- `NOT PRESENT`
- `NOT CLAIMED`

`PASS` must include a command, artifact, or source that can be independently
checked. Bare `PASS` is not valid.

`evidence_refs` does not upgrade semantic authority. It records what evidence
exists for the stated claim ceiling.

## Claim Ceiling Preservation

`done`, `claim_ceiling`, and `not_claimed` must remain separate.

Do not merge unverified implications into `done`. If a capability was not
validated, proven, or authorized in the current scope:
- state the positive boundary under `claim_ceiling`
- list the non-asserted items under `not_claimed`
- keep the existing completion report `Cannot claim this session` section when
  using the longer Rule 7 report

## Risk Disclosure Preservation

The `risk` field is required because incidental work is otherwise easy to hide
inside narrative prose.

Risk entries should disclose:
- incidental cleanup
- scope drift
- claim inflation
- evidence maturity limits
- autonomous work boundary concerns

Do not replace `risk` with confidence scores, effort estimates, or broad impact
analysis.

## Evidence Term Glossing (Plain-Language Requirement)

When a report surfaces machine or governance field tokens — for example
`active_non_canonical_writer=0`, `completion_claim_allowed=True`,
`plan_reconciliation: deferred:<reason>`, guard counts, or any
identifier-shaped audit field — each surfaced token must be paired with a
one-line plain-language meaning in the session language.

Rules:
- Do not strip evidence for readability. The raw field is the reviewer's
  independent-recheck basis; removing it is a regression. The requirement is to
  ADD a plain-language gloss next to the field, not to replace the field with
  prose.
- Lead with a plain-language conclusion (done / not done, which canonical path,
  guard passed?, commit / push state), THEN list the evidence fields with their
  glosses. The audit ledger and the human handoff are two layers, not one.
- Separate this-session counts from pre-existing or historical counts. When a
  count predates the current change (for example a historical
  `non_canonical_writer` total), say so explicitly so it is not misread as
  caused this session.
- Fixed-vocabulary tokens (`PASS`, `FAIL`, `NOT RUN`, `NOT CLAIMED`,
  `NOT PRESENT`) and field identifiers remain as written; the gloss is added in
  the session language, consistent with the Result-First Final Report Format
  rule.

Owner-facing summary structure (added 2026-07-12 after two observed
comprehension failures: an onboarded engineer could not decode adoption
state, and the owner could not act on a jargon-dense progress summary until
it was rewritten in plain language):

- Open with one plain sentence saying what this line of work is and where it
  stands, before any codes or metrics.
- Prefer a short table of "problem found → what was changed" over narrative
  paragraphs when reporting multi-step work.
- When the owner must decide something, list each decision as a numbered
  question and state what reply closes it (for example: "回『可以』即完成").
- Any work-item code (P1-C, F-7, E2, census unit names) gets its
  plain-language purpose on first use in the report; the PLAN Work Item
  Glossary is the source.
- Method self-commentary (process praise, cadence narration) goes last or is
  omitted; it must never displace the decision questions.

Authority boundary: this is an advisory reviewer-facing convention. The
structural `response_envelope_validator.py` does not check glossing or
summary structure, and no gate blocks a report that omits them. A report
from an agent that does not load this contract will not follow it. This
requirement reduces reviewer decoding burden; it is not mechanically
enforced. Repositories that adopt and load this framework contract can use
the same reporting rules; adoption alone does not guarantee application.

## Next-Step Judgment (Required Closing Section)

A completion report exists so a human can decide the next step, not as an
archive. Reports for completion-class tasks (governance checks, code changes,
validation, memory / provenance, commit / push, handoff / reviewer summary)
must close with a Next-Step Judgment containing:

- `status`: done / partially done / not done
- `basis to trust`: which tests, commits, or artifacts support the status
- `recommended action`: exactly one of — can merge / needs review / needs more
  validation / do not touch yet — with a one-line reason
- `cannot claim`: which conclusions still cannot be asserted

This section answers the three questions a reader needs in order to act: Is it
done? Why should I believe it? How do I decide what to do next? It complements
`claim_ceiling` and `not_claimed` (which bound what is asserted) by stating the
recommended decision, not just the evidence.

The purpose is decision readability, not formality. Do not replace the plain
recommended action with a wall of fields; the reader must be able to tell the
next move at a glance.

Authority boundary: advisory, same as the rest of this contract. No gate
enforces the presence or shape of a Next-Step Judgment.

## Opt-In Mechanical Response-Quality Check (v0.4)

`response_envelope_validator.py --check-response-quality` adds a structural
check for the plain-language reporting posture above. It is off by default;
without the flag the validator's behavior, output shape, and exit codes are
unchanged.

When enabled, an envelope must additionally contain each of these field
labels exactly once. Label, value, and position are bound to the same field
occurrence, so a duplicate label after `evidence_refs` cannot satisfy an
empty label before it:

- `conclusion`: the plain-language conclusion (maps to the "open with one
  plain sentence" rule).
- `recommended_action`: the recommended decision (maps to the Next-Step
  Judgment `recommended action`).
- `next_action`: one concrete next step, or `none`.

Checks performed (error codes):

- `quality_missing_field`: a quality field label is absent.
- `quality_duplicate_field`: a quality field label appears more than once;
  duplicates are rejected rather than merged.
- `quality_empty_field`: a quality field has no content or placeholder content
  (`tbd`, `n/a`, `see above`, or `none` — except `next_action`, where `none`
  is an allowed explicit value). Leading list markers (`- `) are stripped
  before this check, so `- TBD` is still placeholder content.
- `quality_field_after_evidence`: a quality field appears after
  `evidence_refs`, violating conclusion-before-technical-evidence ordering.

Boundaries:

- The check is label/position structural only. It cannot judge whether the
  content is actually plain language, whether the recommended action uses the
  advisory vocabulary (can merge / needs review / needs more validation / do
  not touch yet), or whether the conclusion is true. Those remain advisory
  and human-reviewed.
- Evidence Term Glossing and the summary structure rules above remain
  advisory and are still not validated.
- No hook, CI job, gate, or default invocation enables this flag; enabling it
  anywhere is a separate, owner-authorized change.

## Opt-In Plain-Summary Check (v0.5)

`response_envelope_validator.py --check-plain-summary` targets the reader
acceptance test behind this contract: within the first few lines a reader
must be able to answer three questions — can we act now, why, and what is
the next step. It was added after an observed failure: a report passed the
v0.4 structural check yet the owner could not act on it without a rewrite.

When enabled, an envelope must contain each of `conclusion`, `reason`, and
`next_action` exactly once, before `evidence_refs`, and each value must read
as a sentence rather than a bare verdict word.

Checks performed (error codes):

- `plain_summary_missing_field` / `plain_summary_duplicate_field` /
  `plain_summary_empty_field` / `plain_summary_field_after_evidence`: same
  occurrence-bound structure rules as the v0.4 quality check, applied to
  `conclusion`, `reason`, `next_action`.
- `plain_summary_token_without_gloss`: the value contains fixed-vocabulary
  machine tokens (`APPROVED`, `CHANGES_REQUESTED`, `PASS`, `FAIL`,
  `needs review`, `can merge`, `none`, ...) but no accompanying prose. A
  token is acceptable only next to a plain-language gloss in the same field
  (for example `needs review — 驗證器變更需人工確認後才能合併`).
- `plain_summary_not_prose`: the value has no machine token but fewer than 6
  letters/digits/CJK characters — too short to be a sentence.

Divergence from the v0.4 quality check: `next_action: none` is NOT accepted
here. An explicit no-action must be written as a sentence.

Honest boundary (do not inflate this check):

- This is a structural proxy. It can verify that sentence-shaped conclusion,
  reason, and next-step fields exist before the technical detail; it cannot
  verify that a human actually understands them. A jargon-dense value with
  enough characters will pass. Validation raises the probability of a
  readable report; it does not prove readability. The real success signal
  remains direct reader feedback.
- No semantic scoring, no AI judgment, no readability metrics.
- No hook, CI job, gate, or default invocation enables this flag; enabling
  it anywhere is a separate, owner-authorized change.

## Non-Goals

This contract intentionally does not add:
- confidence scores
- effort estimates
- generic impact analysis
- new runtime gates
- automatic semantic verification
- automatic mode inference beyond the listed event mappings
- automatic plain-language gloss validation or enforcement

## Relationship To Existing Rule 7 Reports

The existing result-first completion report remains valid.

Use this envelope when a compact event-driven response is needed, or when a
tooling layer needs structured fields before rendering the existing completion
report.

The envelope must preserve the same claim discipline as Rule 7:
- `NOT CLAIMED` means the capability or conclusion is not asserted.
- `NOT PRESENT` means the mechanism, artifact, or enforcement does not exist.
- `PASS` must reference a command or source.

## Result-First Final Report Format

Final reports should be result-first, not process-first.

Content language must match the session language. Sub-field labels
(`structural`, `build`, `semantic`, `behavioral`, `ext evidence`, `scope drift`,
`claim inflation`, `evidence maturity`) and fixed vocabulary tokens (`PASS`,
`FAIL`, `NOT RUN`, `NOT CLAIMED`, `NOT PRESENT`) remain in English. Section
headers may be translated.

English session format:

```text
1. Result: Done / Not done
2. Capability increased:
3. Changed files:
4. Validation:
   - structural:    PASS — <command> | FAIL — <command> | NOT RUN
   - build:         PASS — <command> | FAIL — <command> | NOT RUN
   - semantic:      NOT CLAIMED | PASS — human review: [reviewer/date]
   - behavioral:    NOT PRESENT | verified — [how]
   - ext evidence:  NOT PRESENT | [source and scope]
5. Risk:
   - scope drift:        none | [description]
   - claim inflation:    none | [description]
   - evidence maturity:  [one line]
6. Incidental cleanup:   none | file=[path] reason=[why] semantic_change=no
7. Governance surface change: none / list
8. Remaining blocker:
9. Cannot claim this session:
   - [list what was NOT validated, NOT verified, NOT proven — required, never omit]
```

Chinese session format:

```text
1. 結果：完成 / 未完成
2. 能力提升：
3. 變更檔案：
4. 驗證：
   - structural:    PASS — <指令> | FAIL — <指令> | NOT RUN
   - build:         PASS — <指令> | FAIL — <指令> | NOT RUN
   - semantic:      NOT CLAIMED | PASS — 人工審查：[審查者/日期]
   - behavioral:    NOT PRESENT | 已驗證 — [如何]
   - ext evidence:  NOT PRESENT | [來源與範圍]
5. 風險：
   - scope drift:        none | [說明]
   - claim inflation:    none | [說明]
   - evidence maturity:  [一行說明]
6. 附帶清理：   none | file=[路徑] reason=[原因] semantic_change=no
7. Governance surface 變更：none / 列舉
8. 剩餘阻擋：
9. 本次無法宣告：
   - [列出未驗證、未確認、未證明的項目 — 必填，不得省略]
```

## Golden Examples

Schema-only change:

```text
1. Result: Done
2. Capability increased: section_refs schema extended
3. Changed files: wiki/port-status.md
4. Validation:
   - structural:    PASS — grep section_refs wiki/port-status.md
   - build:         NOT RUN — markdown-only change
   - semantic:      NOT CLAIMED
   - behavioral:    NOT PRESENT
   - ext evidence:  NOT PRESENT
5. Risk:
   - scope drift:        none
   - claim inflation:    none
   - evidence maturity:  structural layer only; no semantic verification
6. Incidental cleanup:   none
7. Governance surface change: none
8. Remaining blocker:     none
9. Cannot claim this session:
   - semantic correctness of section references
   - PDF-level content verification
```

Pilot attachment change:

```text
1. Result: Done
2. Capability increased: 4 port entries have section_refs attached
3. Changed files: wiki/port-status.md, wiki/zh/port-status.md
4. Validation:
   - structural:    PASS — validate_wiki_frontmatter (exit 0)
   - build:         PASS — npm run build (exit 0)
   - semantic:      NOT CLAIMED
   - behavioral:    NOT PRESENT
   - ext evidence:  NOT PRESENT
5. Risk:
   - scope drift:        none — pilot limited to 4 existing entries
   - claim inflation:    none — claim_level unchanged (inferred)
   - evidence maturity:  build-verified only; high-risk coverage below original plan
6. Incidental cleanup:   none
7. Governance surface change: none
8. Remaining blocker:     PORT_OVER_CURRENT not in pilot — high-risk coverage gap
9. Cannot claim this session:
   - bit-level semantic verification of attached spec sections
   - high-risk boundary condition coverage (PORT_OVER_CURRENT not in pilot)
   - verified status upgrade
```

Failed or partial validation:

```text
1. Result: Not done — build failed
2. Capability increased: none
3. Changed files: wiki/port-status.md (uncommitted)
4. Validation:
   - structural:    PASS — validate_wiki_frontmatter (exit 0)
   - build:         FAIL — npm run build (exit 1, error above)
   - semantic:      NOT CLAIMED
   - behavioral:    NOT PRESENT
   - ext evidence:  NOT PRESENT
5. Risk:
   - scope drift:        none
   - claim inflation:    none — task not complete
   - evidence maturity:  build failure; no completion evidence
6. Incidental cleanup:   none
7. Governance surface change: none
8. Remaining blocker:     build error must be resolved before commit
9. Cannot claim this session:
   - task complete
   - any validation above build layer
```
