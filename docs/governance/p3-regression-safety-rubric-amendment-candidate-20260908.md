# P3 prospective Regression Safety amendment candidate

Status: CANDIDATE / NOT ADOPTED / NOT IMPLEMENTED.
Purpose: distinguish insufficient evidence from complete evidence of defective
submitted regression protection. This is not a request for more evidence fields.

## Current repository truth

The frozen shared rubric at
`tests/fixtures/bug_fix_safety_mini_benchmark/RUBRIC.md` treats failures before
assertions execute as NOT_ASSESSABLE. Easy's preserved scorer inputs already
include complete source/test text, NameError diagnostics, exit 1 and test counts.
The completed P2 round remains governed by its original rubric.

`governance_tools/skill_evaluation_lite_benchmark.py` currently maps any test error
to an unconfirmed execution projection. This candidate does not change that
behavior. A future consumer must not claim this amendment is operational merely
because this document or its illustrative fixtures exist.

## Proposed normative delta (prospective only)

When complete version-bound execution evidence shows that the submitted source
or tests themselves prevent required regression assertions from executing,
Regression Safety is scored **0**, not NOT_ASSESSABLE. Examples include
submission-caused import, syntax or collection errors. The failing command must
actually have been attempted, and evidence must establish that the submitted
bytes violate the task's predeclared execution contract. Failures attributable
to the harness or environment, missing evidence, and unresolved attribution
remain **NOT_ASSESSABLE**.

This is the sole exception added to the existing pre-assertion/zero-test
NOT_ASSESSABLE rule. Zero discovered tests alone does not establish submission
fault. A syntax failure with zero tests may qualify for 0 only when the complete
receipt proves a parser/loader attempt on the exact submitted version and the
failure is attributable to those bytes. Missing completion or test-count evidence
must not be manufactured or interpreted as an observed zero.

## Attribution and version boundary

Use the existing evidence categories: complete subject/test contents, both
execution-version identities matched to final versions, actual command and
completion/exit status, test-count/phase information and diagnostics, plus the
predeclared task and loading contract. A scorer receives identity-stripped
versions of these materials; no arm mapping or local absolute paths are added.

An exception name, nonzero exit, model explanation, or asserted
`submission_caused=true` flag is not proof of attribution. The same NameError can
come from a submitted test or from a broken host wrapper. Import failure can also
come from an unavailable dependency or incorrect harness import path. Identify
the failing source/phase and check the declared contract; if the evidence cannot
separate these causes, keep NOT_ASSESSABLE. If the harness supplied ambiguous
instructions about injecting a symbol, a missing import alone cannot establish
the required contractual attribution.

Version identity and execution outcome are distinct facts. A test error does not
itself prove stale/unknown source versions, and known current versions do not
prove tests passed. Do not reconstruct missing binding from exception text or
upgrade an existing NOT_CONFIRMED receipt by assumption.

## Unchanged scoring and historical boundary

- Current-version assertion failures and tautological protection retain 0.
- Current, passing but incomplete meaningful coverage retains 1.
- Current, passing independent assertions covering every required category retain 2.
- All other dimensions and oracle/quality separation remain unchanged.
- Score freeze, anonymous input and authorized-unblinding ordering remain unchanged.
- Easy's historical regression rating and total remain NOT_ASSESSABLE. No old
  bundle, rubric, score, oracle result, report or round is changed or rescored.

Only a separately adopted future rubric may use this delta, fixed before model
execution/scoring. It is not activated by candidate review or fixture validation.

## Six illustrative fixtures and expected judgments

The specimens in `tests/fixtures/p3_regression_rubric_candidate/cases.json` use a
small synthetic contract: subject.py defines transform(value) = value + 1; tests
must import transform explicitly, and no harness symbol injection is promised.
Required passing categories are positive and zero inputs, with literal expected
values. The harness must be able to load the two files in the declared directory.

| Fixture | Established observation | Prospective judgment |
|---|---|---|
| missing_evidence | Completion exit evidence is withheld | NOT_ASSESSABLE |
| harness_failure | Host wrapper raises NameError before loading submission | NOT_ASSESSABLE |
| submitted_test_missing_import | Current submitted test references an unimported symbol | 0 |
| submitted_source_syntax_error | Parser fails on current submitted subject syntax | 0 |
| assertion_failure | Current test executes an independent assertion that fails | 0 |
| complete_regression_pass | Both required independent categories execute and pass | 2 |

The fixture tests reproduce these observed conditions and bind unchanged source/
test bytes. Expected judgments are predeclared review examples, not a new scoring
engine. Passing them does not prove a real scorer applies the proposed semantics.

## Scope, affected surfaces and next boundary

This slice adds only this candidate, its six synthetic fixture specimens and
focused fixture-validation tests, plus minimum PLAN/memory evidence. No production
API/schema, evidence pipeline, live runner, Skill, Strict policy or frozen fixture
changes. No model execution, commit, push, or rubric adoption in this slice.

DONE: candidate and reproducible examples ready for independent review.
After review, owner adoption and any necessary future-only consumer compatibility
work need their own scope. In particular, the existing error-to-NOT_CONFIRMED
projection remains an unresolved integration prerequisite, not implicitly fixed.

Claim ceiling: NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY;
candidate semantics and illustrative fixture validation only. No retroactive
quality advantage, general Skill efficacy, or production enforcement is claimed.
