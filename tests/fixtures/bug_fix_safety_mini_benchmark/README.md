# Bug Fix Safety mini benchmark — preparation candidate

Status: READY FOR VALIDATION / NOT OWNER-ADOPTED. Exactly three tasks; difficulty
labels are design hypotheses, not calibrated difficulty or model results.

## Purpose and current boundary

Prepare independently specified cases before any future evaluation. Existing
`governance_tools/skill_evaluation_lite_live.py` has fixed queue-range task,
oracle and AST admission rules. It is unchanged. This pack is NOT wired to it;
in particular nested graph traversal may require later runner compatibility work.
No model, CONTROL/TREATMENT run, scoring, or unblinding occurs in preparation.

Each task defines the public specification and allowed source/test filenames,
a deliberately buggy baseline, literal oracle answers, required regression
categories and task-specific rubric. `validation_variants.py` contains manually
authored reference/incorrect fixtures solely to check oracle sensitivity. These
are not arm submissions and do not establish Skill effectiveness.

## Material separation for a later run

| Recipient | Permitted material |
|---|---|
| Both arms | That task's `TASK.md`, `baseline.py`; identical execution constraints |
| Treatment only | Separately selected, unchanged Bug Fix Safety packet |
| Evaluator | `cases.json`, reference/incorrect variants, validation evidence |
| Fresh scorer | Public task, shared `RUBRIC.md` + task `RUBRIC.md`, anonymous final source/test/explanation, permitted oracle summary, version-bound regression evidence |

Do not send this README, task difficulty/arm labels, fixture paths, cases,
reference repairs, incorrect repairs or preparation diagnostics to the arms.
Do not send arm mapping, original runtime paths or investigative records to the
scorer. Evaluator expected answers are held out, not required author tests.
Public specifications disclose required test categories, not the private case list.

All oracle values are literal, reasoned from public contracts, never calculated
from reference code or observed model output. `regression_case_ids` select concrete
cases with the same independent expectations; they are a preservation panel,
not additional independent samples or an automatic Regression Safety score.

## Fixed review snapshot

`manifest.json` records bytes/SHA-256/Git blob for the files in this pack except
itself. Its own identity is recorded with validation under `memory/evidence/`.
The manifest is a prospective review snapshot, not historical custody, owner
adoption, a new framework schema, or authorization for real execution.
Any subsequent oracle/spec/rubric edit invalidates this snapshot and needs review
before a future run. Do not tune answers after seeing evaluation outputs.

## Validation (no model)

From repository root:

```powershell
& .\.venv\Scripts\python.exe -B tests/fixtures/bug_fix_safety_mini_benchmark/validate_preparation.py --output memory/evidence/bugfix-mini-benchmark-prep-20260908/validation.json
```

The fixture-local check verifies snapshot identities, reproduces each named
defect, checks the reference against all literal answers, and proves each wrong
repair fixes the public symptom but fails a different declared case. It also
checks the regression preservation panel and records results case by case.
This is not a consumer runner, production validator or scoring engine.

## Interpretation and deferred work

Claim ceiling: `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`.
No Strict equivalence, OS isolation, Formal/counting eligibility, stable Skill
benefit or average cost reduction is established. Easy intentionally resembles
the prior queue-range calibration task; it is not novel independent evidence
against that prior observation. Three selected tasks can reveal patterns and
counterexamples but cannot establish statistical stability or general efficacy.

Regression evidence admission is specified in the shared rubric before runs.
No fairness claim about future runtime/auth/model identities is made here.
Future task consumption, fresh contexts, execution/version-binding evidence and
separate scoring/unblinding authorization must be resolved in a later slice.
Do not change runner/Skill/scorer, rerun history, commit or push in preparation.

