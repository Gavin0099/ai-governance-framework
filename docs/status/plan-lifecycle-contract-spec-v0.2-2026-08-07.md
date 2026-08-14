# PLAN lifecycle contract — spec v0.2 (2026-08-07)

> **Docs-only, report-only.** This spec changes no parser, no template, no
> consumer PLAN, and no adoption or refresh behaviour. It defines what the
> contract *should* say so that implementation can be reviewed against it later.
> **It is not implementation authorization.** T1 / T2 / T2b remain unstarted.
>
> **v0.2 records five owner decisions ratified 2026-08-07** (retention,
> heading aliases, `- [>]`, non-conforming PLANs, report-only thresholds),
> recorded in "Ratified decisions" and folded into the sections below.
> **The contract is not closed:** the §5 heading contract — canonical list,
> legacy alias list, precedence, multi-heading behaviour — is still undefined.
> See "Open items that remain".
>
> Evidence base: `docs/status/plan-fleet-census-2026-08-07.md` (Revision 3.2 text,
> `method_version: census-3.3` artifact)
> and `artifacts/plan-census/plan-fleet-census-2026-08-07.json` (45 rows,
> 38 assertions, all passing). Every quantitative claim below traces to that
> artifact.
>
> Scope note: this spec governs PLAN.md across **all** adopting repositories.
> The framework's own PLAN rollover
> (`plan-selective-rollover-manifest-2026-08-07.md`) is the first manual pilot
> and stays blocked until this contract is approved.

## Why a contract is needed — three measured facts

1. **`parse_backlog_counts` cannot return a non-zero value for any well-formed
   PLAN** using the intended `## Backlog` → `### P0/P1/P2` grammar. Its section
   extraction terminates at the first H3, so the sub-headings it requires can
   never appear in the body it searches. Fleet result: **0 reported** against
   **55 structural backlog rows** actually present.
2. **The template and the parsers disagree on headings.** The template emits
   `## Active Sprint`; `parse_sprint_tasks` accepts only `## Current Sprint`.
   **3 of 45** directories carry a parser-compatible sprint heading.
3. **Failure is expressed as zero, not as "unknown".** Both parsers return an
   empty result when they cannot find their structure, which is
   indistinguishable from "there is genuinely no open work".

The consequence is that a repository can be fully adopted, pass drift checks,
and still have its entire planning surface invisible to the summarizer — with no
signal that anything is wrong.

## 1. Item types

A PLAN records five distinct things. **In the framework's own PLAN they are all
written as checkboxes**, which is why it has 16 unchecked items of which only 4
are work. The fleet is not uniform in this: 49 inline-priority rows
(`- P1: …`) exist elsewhere, following the template rather than the checkbox
form. The contract must cover both.

| Type | Required form | Rationale |
|---|---|---|
| **Work item** | `- [ ]` / `- [x]` | Completable. A checkbox implies it can one day be checked |
| **Acceptance criteria** | Sub-bullet or prose **directly under its work item** | Must not be separated from the task it qualifies |
| **Standing constraint / claim boundary** | `CLAIMED:` / `NOT CLAIMED:` prose in a claim-boundary section | Never completable. A `- [ ]` that can never be checked is a permanent line and the section can only grow |
| **Gated / deferred / blocked work** | Checkbox **plus an explicit hold state and its reason** | Still work; must not be mistaken for history because it has not moved |
| **Historical result** | Archive prose | Not planning surface |

**Rule.** A `- [ ]` asserts "this can be completed". Recording a permanent
policy as an unchecked checkbox is a category error, and it is the mechanism by
which PLANs grow without bound.

## 2. State semantics

| Marker | Meaning | Must be surfaced as |
|---|---|---|
| `- [ ]` | open work | open |
| `- [x]` | completed | done |
| `- [>]` | in progress | **open**, and reported **separately from `[ ]`** — see below |
| hold: `gated` | blocked by a named decision or ratification | open, with the gate named |
| hold: `deferred` | intentionally postponed to a named condition | open, with the condition named |
| hold: `blocked` | waiting on review, signature, or an external party | open, with the blocker named |

**Decision 3 (ratified).** `- [>]` means `in_progress` and counts as open work.
It appears 4 times in the fleet and is currently matched by **neither** parser —
counted as neither open nor closed. One of the four is this framework's own
`PLAN.md:57` Phase E marker, so forbidding the glyph would require rewriting a
marker that carries real meaning.

Reporting requirement: `in_progress` and `not_started` must be **counted and
surfaced separately**. Collapsing them into a single "open" figure would make
work-in-flight disappear from the report, which is the same class of loss this
contract exists to prevent.

Hold state must carry its reason. "Gated by P2-E ratification" is usable;
"gated" alone is not.

## 3. Parser result contract

**A parser must never express "I could not understand this" as a count of zero.**

Every PLAN-reading tool returns a status alongside its data:

| Status | Meaning | Counts |
|---|---|---|
| `parsed` | section found and understood, items present | **valid** |
| `empty` | section found and understood, genuinely no items | **valid, and must be zero** |
| `unparsed` | section found, structure not understood | **`null` or absent — never zero** |
| `unsupported` | no section of this kind exists in this PLAN | **`null` or absent — never zero** |

`empty` and `unparsed` must be distinguishable by the caller. A summarizer that
reports `P0=0 P1=0 P2=0` when it means `unparsed` is producing a false negative
that no downstream consumer can detect — the defect this census measured.

Rules:

- Counts are meaningful for `parsed` and `empty`, and for `empty` the count is
  necessarily zero. For `unparsed` and `unsupported` the count field must be
  `null` or absent — emitting `0` is what makes the current defect invisible.
- A tool that returns `unparsed` must name what it expected and what it found.
- **Fleet aggregation must report all four populations with an explicit
  denominator**, e.g. `parsed 12 / empty 5 / unparsed 11 / unsupported 17 of
  45`. Reporting only `unparsed` separately is insufficient: a repository with
  no section at all would still be silently excluded from the denominator, which
  is a second way to manufacture a reassuring total.

### 3.1 Placeholder semantics

A section may be present, understood, and legitimately hold nothing. The current
template ships two placeholder forms, and one of them is a checkbox:

| Template line | Section | Problem if taken literally |
|---|---|---|
| `- [ ] (no tasks yet)` | `## Active Sprint` | counted as **one open task** — a phantom item in every freshly adopted repo |
| `- P1: (none)` | `## Backlog` | counted as one backlog row |

The contract must state, explicitly, which of these map to `empty`:

- a section whose body has no items at all;
- a section holding only recognised placeholder text — the declared set must be
  enumerated, not pattern-guessed, and must at minimum cover `(none)` and
  `(no tasks yet)`;
- a section holding only comments (`<!-- … -->`).

**A placeholder must never be reported as work.** Whichever forms are recognised
must yield `empty` with a count of zero, not `parsed` with a count of one. Any
form *not* on the declared list is real content and counts.

**Mixed sections.** When a section holds both placeholders and real items,
ignore the placeholders, return **`parsed`**, and count only the real items.
`empty` applies only when *nothing* real remains after placeholders are
discarded — a mixed section must never be collapsed to `empty`.

### 3.2 Applicability — a second, independent dimension

**Decision 4 (ratified).** `parse_status` and `applicability` are **orthogonal**
and must both be recorded. An earlier draft forced a choice between
`unsupported` and "exemption"; that conflated *"the tool could not read this"*
with *"this repository is not required to comply"*.

| Field | Values |
|---|---|
| `parse_status` | `parsed` \| `empty` \| `unparsed` \| `unsupported` |
| `applicability` | `required` \| `optional` \| `exempt` |

A repository may legitimately be both `parse_status=unsupported` **and**
`applicability=exempt`, and that combination must not be reported as a parser
failure.

**Default — scoped, not global.** `applicability` is derived from the
repository's active `plan_required_sections` declaration, not applied blanket:

| Situation | `applicability` |
|---|---|
| surface listed in the active `plan_required_sections` | `required` |
| surface not listed | **`optional`** — *not* `exempt` |
| surface that is `required` but has owner-approved evidence for an exception | `exempt` |

Making everything `required` by default would **extend the current mandate**,
which this spec has no authority to do. Verified: this repository's
`.governance/baseline.yaml` does **not** set `plan_required_sections`, and
`adopt_governance.py` states that adoption does not impose sections on an
existing repo. A blanket `required` default would silently make 45 repositories
non-compliant against a rule nobody enabled.

`applicability` is **never inferred from a PLAN's shape** — a repository does
not become exempt by being unreadable, and does not become required by being
tidy.

**Exemption evidence.** `exempt` is only valid with a recorded basis:

- who approved it (a named owner, not a tool);
- the date;
- the reason;
- a review-by date or the condition that would end the exemption.

An `exempt` marking without that evidence is invalid and the repository reverts
to `required`.

**Denominators.** Every repository stays in the **fleet total**, always. Only
the **compliance denominator** may exclude owner-approved exemptions, and any
report doing so **must state the excluded count alongside it** — e.g.
`38/42 compliant (3 exempt, 45 total)`. Reporting `38/42` alone would be a third
way to manufacture a reassuring total, after the silent zero and the missing
`unsupported` population.

## 4. Template ↔ parser conformance

**Rule: the adoption template is a conformance fixture.** Whatever the template
emits must parse, and whatever the parser requires must be emitted.

Required, bidirectional:

- A fixture built from the template must parse with status **`parsed` or
  `empty`**, whichever its content warrants, for every section the parser reads.
  The as-shipped template is placeholder-only, so its expected result is
  **`empty`** — requiring `parsed` here would force the parser to treat
  `(no tasks yet)` as a real task.
- A fixture built from the parser's documented grammar must round-trip through
  the template's structure.
- Both directions run in CI. A template change that breaks parsing, or a parser
  change that orphans the template, fails.

This single rule would have caught all three measured facts above at the moment
they were introduced.

## 5. Heading compatibility and legacy range

The fleet uses at least these sprint headings: `## Active Sprint` (the
template), `## Current Sprint` (the only one the parser accepts), plus Chinese
and emoji-bearing forms such as `## 進行中任務（Sprint）` and
`## 🔥 本輪聚焦（Sprint 2026-05-23）`. **37** sprint-bearing H2 headings exist
across 45 directories; some files carry more than one.

**Decision 2 (ratified) — a hybrid model, not purely repo-local:**

| Layer | Owned by | Rule |
|---|---|---|
| **Canonical headings** | framework, centrally | the names the parser guarantees to read |
| **Legacy aliases** | framework, **closed list** | existing forms that must stay readable; the list is enumerated, never extended by pattern |
| **Consumer aliases** | repository, in `contract.yaml` | optional localized names, declared explicitly |
| **Anything undeclared** | — | **not guessed.** An unrecognised heading yields `unsupported`, never a heuristic match |

Purely repo-local aliasing was rejected because it would let every repository
define its own canonical, removing the shared baseline the contract exists to
provide.

**Scope warning.** `contract.yaml` has **no PLAN alias field today** — verified:
it references `PLAN.md` only as a file path — and the parser is not
contract-aware. Consumer aliases therefore require a new schema key and a
contract-reading parser. **That work must not be folded silently into T1**; it
is tranche **T2b** below.

**Still undefined — these are open, and they are parser-observable behaviour,
not implementation detail:**
- **Precedence** when a file carries several candidate sections.
- **Multi-heading behaviour** — measure one, all, or refuse.
- **Non-conforming PLANs** — `usb-logic-trace-correlator` (487 lines) has no
  `##` sections at all; `Kernel-Driver-Contract` and
  `USB-Hub-Firmware-Architecture-Contract` have zero. The answer cannot be
  "silently score them as compliant".

## 6. Rollover, archive, freshness

**Rollover.** Define when a PLAN rolls over, what may move, and what must stay.
What must stay: current phase, active work with hold states, claim boundaries,
next measurable slice, archive pointer.

**Archive.** Under the census's documented detection rule — a file matching
`*plan*archive*` / `*archive*plan*` at depth ≤ 3, or a PLAN link whose target
contains `archive` — **0 of 45** directories were detected. This rules out that
naming and linking convention; it does **not** establish that no historical
preservation or retirement mechanism exists in any other form. The contract must
define:

- archive location and naming;
- provenance per archived block — source section, date, originating commit;
- a successor pointer when a constraint is superseded rather than completed;
- reachability: one link from the root PLAN.

**Never silently delete.** A constraint that is lifted records the basis on
which it was lifted. A superseded constraint names its successor. Content may
move; it may not vanish.

**Retention — Decision 1 (ratified).** At each **recorded** PLAN maintenance
checkpoint, the items observed as completed at that moment move to archive. The
overdue signal is **checkpoint-scoped, not item-scoped**: report when
`today - last_recorded_checkpoint_date > 7 days`. No per-item completion age is
measured, because no completion-date field exists — see below. **Automatic
deletion is forbidden** in all cases.

> **Unassigned reason code — new open item.** This checkpoint-overdue signal has
> no ratified code. `plan_freshness_overdue` was ratified for a *different*
> measurement — document staleness, `today - Last Updated`, §7 — and §6's own
> freshness table lists "document date" as a distinct signal from the rest.
>
> **The principle, stated correctly:** a reason code **may** carry several
> triggers — `plan_rollover_candidate` already accepts both a size arm and an
> accumulation arm — but it must not mix problems with **different semantics and
> different dispositions**. Document staleness asks the owner to refresh a date;
> checkpoint overdue asks them to run a rollover. Same code, different action:
> that is the conflation to avoid. An earlier edit in this revision mapped
> retention onto `plan_freshness_overdue`; that was wrong and is withdrawn.
> Whether this becomes a fifth code or a third arm of an existing one is an
> owner decision, not a drafting choice — see "Open items that remain".

"Until the next checkpoint" is only executable if a checkpoint is observable, so
a checkpoint must be **measurable**, not narrative:

- it is **recorded**, with a date, in the PLAN or an archive index — a
  checkpoint nobody wrote down did not happen;
- **no per-item completion date is assumed.** Verified: neither `PLAN.md`, the
  adoption template, nor the parsers carry `completed_at`, `completion_date` or
  any equivalent. An earlier draft measured "completion date vs today"; that
  field does not exist, so the rule was unexecutable;
- the overdue signal is therefore **checkpoint-scoped**, not item-scoped:
  the checkpoint-overdue signal fires when
  `today - last_recorded_checkpoint_date > 7 days`. A repository that never
  records a checkpoint has no last-checkpoint date and therefore trips the
  signal immediately — it cannot exempt itself by omission;
- at each recorded checkpoint, the items observed as completed **at that moment**
  move to archive. **No item-specific overdue claim is made.** If per-item aging
  is ever wanted, it requires a completion-date schema defined in its own spec;
  it must not be assumed here;
- "one phase" or "one planning window" was rejected as the unit: this
  framework's own phases run for months, and phase-length retention is what
  produced a 1742-line PLAN with a section titled "Current Sprint - 2026-06-10".

**Freshness.** A date is not freshness. The framework's own PLAN was updated
2026-07-30 while its largest section is titled "Current Sprint - 2026-06-10".
Report separately:

| Signal | Question |
|---|---|
| document date | is `Last Updated` within threshold? |
| sprint currency | does the sprint section describe present work? |
| item hygiene | do active items carry owner and hold state? |
| archive reachability | is the archive linked and present? |
| summary completeness | did every required parser return `parsed` **or** `empty`? `unparsed` and `unsupported` are the incomplete population |

First version is **report-only**. Format divergence must not block a consumer.

## 7. Consumer migration

- **Report-only first.** A consumer may be told its PLAN does not conform. It
  may not have its PLAN rewritten.
- **No automatic rewriting**, ever, without per-repository owner approval.
- **Migration output is a proposal** — a disposition manifest naming every item
  and its destination — not an edit.
- **Threshold-triggered, and split by reason — Decision 5 (ratified).** A single
  composite trigger was rejected: it packages parser-correctness defects as
  tidying advice, and they are not the same problem.

  | Reason code | Trigger | Threshold |
  |---|---|---|
  | `plan_parse_unreadable` | any section returns `unparsed` | **none — always signalled** |
  | `plan_required_section_unsupported` | a `required` surface returns `unsupported` | none |
  | `plan_rollover_candidate` | size or accumulation | `logical_lines > 600` **OR** (checklist items ≥ 20 **AND** completed ratio ≥ 80%) |
  | `plan_freshness_overdue` | **document staleness** | the existing rule: `today - Last Updated > 7 days`, reported independently |

  **Completed-ratio denominator, stated explicitly.** The ratio is computed over
  **checklist items only** — `[ ]`, `[x]`, `[>]` — and **excludes** recognised
  placeholders, standing constraints, claim boundaries and prose. The `≥ 20`
  item floor uses the same denominator. Without both constraints a four-item
  PLAN with three done would trip at 75–100% and be told to roll over; and a
  PLAN whose "completions" are actually standing constraints would score as
  finished work.

  **Eligibility — when the ratio may not be computed at all.** Both the ratio
  and the `≥ 20` floor require:

  - the section's `parse_status` is `parsed`; **and**
  - work-item classification is complete — every checklist item is resolved to
    work / acceptance criteria / standing constraint / status note.

  If either precondition fails, the ratio and the floor are **`not_available`**,
  and `plan_rollover_candidate` may fire only on the `logical_lines > 600` arm.
  **Falling back to a raw checkbox ratio is forbidden.** The framework's own
  pilot found 11 of its 16 unchecked items were standing constraints, and no
  tool can currently make that distinction reliably — a raw ratio would silently
  score policy as progress.

  The first two codes carry **no threshold**: a parser that cannot read a
  section is a correctness signal, and suppressing it below a size cutoff would
  hide exactly the defect this contract was written for.

  All thresholds are **provisional and report-only**, to be recalibrated after
  the T3 observation window.

  Median PLAN is 109 logical lines; 38 of 45 are under 262 and **5** exceed 600.
  **Most repositories do not cross the size trigger. That does not establish
  PLAN health or semantic hygiene.** What the census observed: all 45 inputs
  returned a backlog count of 0; 26 carry a `## Backlog` heading; 3 carry a
  parser-compatible sprint heading. Whether a given repository is *affected*
  depends on its `applicability`, which is not yet determined, so no "45 of 45
  are affected" conclusion is drawn. A mandatory gate on all 45 would still be
  governance surface without a demonstrated benefit.
- **Adoption and refresh must not reset a consumer's PLAN** to template shape.

## 8. Implementation tranches — strictly ordered

Nothing here is authorized by this spec. The order matters because each stage
makes the next measurable.

**T1 and T2 must be released atomically.** Fixing only the parsers does not make
the current template readable — the template emits `## Active Sprint` where the
parser wants `## Current Sprint`, and `- P1: …` where the parser wants `### P1`
plus a checkbox. Those are three independent incompatibilities, and repairing
the H3 truncation removes only one. A shipped T1 without T2 would be a version
that is newly correct and still cannot read its own template; it must not be
available for adoption.

| Tranche | Scope | Gate |
|---|---|---|
| **T1** | Parser correctness: H2-only section extraction; four-state result; **accept the current template grammar as well as the new canonical grammar** | Contract approved. Fixture-covered both ways. No template change |
| **T2** | Converge the template onto the canonical grammar; bidirectional conformance fixtures in CI | Reviewed separately from T1, **released in the same release as T1** — no intermediate version published for adoption |
| **T2b** | `contract.yaml` PLAN-alias schema key + a contract-aware parser, so consumer-declared aliases work | Separate design review. **Must not be folded into T1** — no such schema exists today |
| **T3** | Report-only fleet signal — the four reason codes above, no writes | T1+T2 released and replayed in at least one consumer. T2b only if consumer aliases are in scope |
| **T4** | Migration proposals as disposition manifests, per repository, owner-approved | T3 has run long enough to show real signal quality |
| **T5** | Any enforcement | **Requires its own owner authorization.** Completing T1–T4 does not authorize it |

**Backward compatibility is a T1 requirement, not a migration concern.** 41
unique PLAN contents exist today and none of them changes when T1 ships.

**Three different things must not be confused, and the census artifact is only
the first of them:**

| Name | What it is | What it cannot do |
|---|---|---|
| **Replay manifest** (`plan-fleet-census-2026-08-07.json`) | 45 rows of expected observations: `source_id`, SHA-256, headings, counts, parser output | **Not executable input.** It holds no PLAN text, so it cannot be fed to a parser |
| **Local fleet replay corpus** | the 45 PLAN files under `fleet_root` on the author's machine | **Not portable and not CI-usable.** Resolution from `source_id` + `fleet_root` must be defined before any replay claims to cover the fleet |
| **CI fixture set** | owner-reviewed, de-identified, representative grammar fixtures | Small by design; it is not the fleet |

Treating the manifest as the fixture set would repeat the pattern recorded in
`memory/03_knowledge_base.md:151`, *"Summary-Only Cross-Boundary Evidence
Anti-Pattern"*, whose principle is that a restatement of a stage does not
independently establish that stage and that durable raw artifacts must be
preserved per hop. **A summary is not an execution input.** The manifest's role
is to be the *expected* side of a before/after diff, never the input side.

**Corpus binding is a precondition for any replay.** Before parsing a
`source_id`, recompute the PLAN's SHA-256 and compare it to the replay
manifest. On mismatch the run must report **`stale corpus / recensus
required`** for that row and must not count it as a valid replay. Comparing a
changed PLAN against stale expected observations is not the same evidence, and
silently proceeding would reintroduce exactly the problem the manifest exists to
prevent.

**Two acceptance suites, because the first transition has no comparable
baseline.** The current parsers return only counts and lists — there is no
`parsed` / `empty` / `unparsed` / `unsupported` field to compare against. Any
"before status" at the first transition would be fabricated.

*Suite A — first T1 transition (no before-status exists):*

1. SHA-256 binding verified per `source_id`, as above.
2. For surfaces the **old** parser recognised correctly, compare counts
   directly; those are real before-values.
3. For surfaces the old parser had no status for, the new status is judged
   against an **owner-reviewed expected fixture or an independent raw
   inventory** — never against an invented "before: unparsed".
4. Placeholder repairs are **intentional deltas and must be listed as such**:
   a phantom `- [ ] (no tasks yet)` becoming `empty` / 0 is a fix, not a
   regression, and must appear in the diff with that label.
5. False zeros becoming positive counts are likewise intentional deltas.

*Suite B — regression after T1 is in service (status exists on both sides):*

1. `parsed` / `empty` must not regress to `unparsed` / `unsupported`.
2. An item recognised before must still be recognised after.
3. Every status or count change is explained per `source_id` in an explicit
   before/after diff. Silent movement is a failure even when the new number
   looks better.

Suite B's status invariants are **not applicable** to the first transition.

**Legacy readability, stated narrowly:** forms the parser currently recognises
correctly must not regress. The other observed heading forms — 37 sprint-bearing
headings across the fleet, most of them not currently readable — are **not
promised readable**; whether they become aliases depends on the owner's alias
decision in §5, which is not yet complete — see "Open items that remain".

**T5 needs more than a clean signal.** Before any enforcement:

- an owner authorization specific to enforcement, separate from contract
  approval;
- observed failures that enforcement would have prevented, not hypothetical
  ones;
- a demonstrated benefit that exceeds the maintenance cost of the gate;
- a false-positive rate measured over T3's reporting window.

Enforcement is not assumed to be desirable and is not the natural endpoint of
this sequence.

The framework's own PLAN rollover pilot may proceed once the contract is
approved, independently of T1–T5, because it is manual and repo-local.

## Ratified decisions (owner, 2026-08-07)

| # | Decision | Where it lands |
|---|---|---|
| 1 | Archive at each **recorded** maintenance checkpoint; **checkpoint-scoped** overdue signal when `today - last_recorded_checkpoint_date > 7 days`; **no per-item completion age**, no automatic deletion. ⚠️ its reason code is unassigned — see open items | §6 |
| 2 | **Hybrid** aliases: canonical + legacy closed list centrally, consumer aliases declared in `contract.yaml`, nothing guessed | §5, T2b |
| 3 | `- [>]` = `in_progress`, counts as open, **reported separately from `not_started`** | §2 |
| 4 | `parse_status` and `applicability` are **orthogonal**. `applicability` is **scoped, not global**: listed in active `plan_required_sections` → `required`; not listed → **`optional`**; `exempt` only for a `required` surface with recorded owner evidence. Exclusions must state their count | §3.2 |
| 5 | Report-only signal split into **four reason codes**; the two correctness codes have **no threshold**; completed-ratio denominator is checklist items only | §7 |

**Open items that remain.** The five policy decisions above are ratified, but
the heading contract in §5 is **not complete**. Still undefined:

1. the exact list of canonical headings;
2. the exact closed list of legacy aliases;
3. precedence when a file carries several candidate sections;
4. multi-heading behaviour — parse all, pick one, or refuse;
5. **the reason code for the checkpoint-overdue signal** (§6). Decision 5
   ratified four codes and `plan_freshness_overdue` among them measures
   *document* staleness. The checkpoint measurement is distinct and currently
   has no code. Reusing `plan_freshness_overdue` would put two *dispositions*
   behind one code — refresh a date vs run a rollover.

   **Reviewer suggestion, not a decision:** make checkpoint overdue a **third
   trigger arm of `plan_rollover_candidate`**, carrying
   `trigger_detail=checkpoint_overdue`. Its disposition matches that code's
   existing arms — prompt a rollover — and it keeps the four ratified codes
   intact rather than introducing a fifth. The owner decides.

These determine what the parser observably does, so the contract is **not
closed** until they are settled. v0.2 does not claim otherwise, and it does not
grant implementation authorization either.

## Explicitly not claimed

- **No implementation is authorized**, including the parser fix, despite it
  being the clearest defect on record.
- **No consumer PLAN is in scope for modification.**
- **Item semantics across the fleet are `NOT ASSESSED`.** The census counts
  checkboxes, not work. The framework's own pilot found 11 of its 16 unchecked
  items were standing constraints; the same is likely elsewhere and is
  unmeasured.
- **No claim that any consumer is doing anything wrong.** Where the fleet
  diverges from the parser, the evidence points at the parser first and the
  template second.
- **No estimate of migration cost.** The framework's own pilot has not run, so
  there is no measured basis for one.
