# Gate 3 C1 — Method-Sensitivity Assessment

Status: **`GO_TO_GATE1_PROPOSAL`**

Decision date: 2026-08-21

This checkpoint answers only whether C1 has enough plausible leverage on the
frozen Bug Fix Safety method to justify the cost of authoring a Gate 1
proposal. It does not preregister Gate 1, authorize an arm, or estimate an
effect.

## Decision authority and boundary

The owner authorized the next bounded step after C1 was admitted at Gate 0:
assess whether an agent without the Bug Fix Safety packet has a reasonable
failure path that the packet could change. The closed outcomes were
`GO_TO_GATE1_PROPOSAL` and `STOP_BEFORE_GATE1`.

The outcome is `GO_TO_GATE1_PROPOSAL`. This means a separate Gate 1 proposal
may now be authored for review. It is not approval of that proposal and does
not start Gate 1.

## Evidence bindings

| Surface | Binding |
|---|---|
| Bug Fix Safety packet freeze | framework commit `61b285b25e97872526057c6ab6b01637fbfa1d2b` / 2026-07-24T17:52:58+08:00 |
| frozen Skill packet | `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14` / 1,373 bytes |
| historical baseline | `15d5d51356b4808e5fb12782961a94d9985b2ae6` |
| historical fix | `a60756436095fb3b14aecbc9094dd88a8ab9ef16` / 2026-07-29T17:13:59+08:00 |
| attempt-01 terminal | `82e7e6251fa8fa64e3b00933cbab743ceea68bf51c79cebbd4326e231cdc41f2` / 1,658 bytes |
| attempt-01 causal analysis | `eb143a121a89c30acb629a1e97ee46f9962dccc17e24eb9bb572f2d23df98da8` / 4,246 bytes |
| redesigned oracle | `702e0a78ec4d7e62abf57fd643bc068da559621428310fed2f22547b29ab9dad` / 8,411 bytes |
| attempt-02 terminal | `8428a3d87c167ee363e0247ca47d6b1e695ea144e38073a5b5d00f1140edb959` / 2,760 bytes |
| Gate 0 admission merge | `6fedb405531bbe920b7f267cfa49b5d00bc841ad` |

The Skill packet predates the historical C1 fix by just under five days and
contains no C1 root cause or fix hint. The method-to-failure alignment below
was therefore not added to the packet after C1's result was known.

## Why C1 is plausibly method-sensitive

### 1. An observed failure matches the frozen method directly

The frozen packet requires the producer to:

1. confirm the defect before editing;
2. write a regression test that fails on the baseline; and
3. re-introduce the original defect and confirm the test fails again.

The regression fixture committed with historical fix `a607564` did not meet
that contract. Attempt 01 overlaid the exact historical test file onto the
exact baseline, selected all five tests, and observed all five pass. Its
terminal disposition was correctly `ORACLE_DOES_NOT_DISCRIMINATE`.

Static causal analysis then showed why: the strong-identity fixture supplied
`isbnRows` but no matching `softRows`. The baseline reached the defective soft
path, but the fake returned an empty soft result, so baseline and fixed both
returned `null`. This is precisely the class of false reassurance that the
packet's baseline-failure and sensitivity steps are intended to expose.

This does not prove that a treated agent would succeed. It establishes a real,
C1-specific failure opportunity for the treatment to change.

### 2. The production correction is not a one-assertion lookup

The baseline combines three identity tiers: ISBN, source URL, and a fallback
title/publisher soft identity. A correct fix must preserve soft matching for
books without strong identity while preventing books with an ISBN or URL from
falling through after a strong-key miss.

The historical fix changes both the population used for the soft lookup and
the final in-memory soft-match branch. Plausible untreated mistakes include:

- disabling soft matching globally, breaking weak-identity imports;
- guarding ISBN while forgetting URL as another strong identity;
- changing only one of the two soft-match sites and leaving mixed-batch
  behavior inconsistent; or
- adding a regression test whose fixture never makes the defective soft path
  observable, as the historical test actually did.

The packet's explicit root-cause hypothesis, independent expected behavior,
minimal-fix rule, baseline-failing regression, and sensitivity check each have
a concrete opportunity to affect those outcomes.

### 3. A capable control may still succeed

C1 is not guaranteed to produce a positive `B-A` difference. A capable base
harness may inspect the identity precedence, preserve the weak fallback, and
write a discriminating test without the packet. Attempt 02 was also redesigned
after attempt-01 failure and implementation details were known; it is not an
unbiased treated-arm result.

These limitations prevent an effectiveness claim. They do not erase the
observed non-discriminating-test failure or make treatment leverage zero.

## Required contrast conditions for any Gate 1 proposal

A Gate 1 proposal is worth reviewing only if it preserves the following
contrast:

1. The common task packet gives every arm the same product symptom,
   reproduction, behavioral acceptance boundary, baseline, permissions, and
   budget.
2. The common task packet must not prescribe a regression-test workflow,
   require baseline-fail/fixed-pass evidence, require defect reintroduction,
   or disclose the root cause or historical fix. Those are treatment content
   in the frozen Skill packet; giving them to Arm A would collapse `B-A`.
3. Producers receive baseline history only and cannot read `a607564`, the Gate
   0 records, either attempt, this assessment, or later analysis.
4. Scorer-only oracle coverage must distinguish at least: ISBN strong
   identity, URL strong identity, preserved weak-identity soft matching, and a
   mixed batch capable of populating the soft map.
5. Objective scoring must separate production correctness, regression-test
   discrimination, preservation of weak matching, scope/minimality, and claim
   accuracy. Merely reciting packet steps is not an outcome win.
6. The informed historical selection and post-failure oracle redesign remain
   in the claim ceiling. One C1 replay cannot establish measured Skill
   effectiveness or generalization.

The prior pre-push arm dispatch is not reusable as-is: its acceptance text
requires a regression test to fail before the change and again after revert.
That wording duplicates central Skill treatment for every arm and would make a
C1 `B-A` comparison uninterpretable.

## Terminal decision and non-claims

Terminal decision: **`GO_TO_GATE1_PROPOSAL`**.

This checkpoint authorizes only the drafting of a separate Gate 1 proposal for
review. It does **not** establish or authorize:

- Gate 1 preregistration or freeze;
- producer, scorer, or arm execution;
- A/B or counted Gate 3 evidence;
- a positive Skill effect, effect size, prevalence, or generalization;
- process integrity, countability, or promotion evidence; or
- C2 or C3 admission, assessment, or execution.
