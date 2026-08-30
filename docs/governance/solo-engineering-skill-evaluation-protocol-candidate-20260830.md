# Solo Engineering Skill Evaluation Protocol Candidate

Status: **ADOPTED / NOT AUTHORIZED FOR EXECUTION**

## 1. Purpose and authority boundary

This protocol asks whether the owner should keep using the Engineering Skill.
All results are
`NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`.

The controlling route split is commit
`ea46e4018b266d63ff0597ab4109d02b360b7b91`, blob
`c2a2241ed550979824ea6e51a00fd2acc8e3782f`, SHA-256
`ae29a84498d8f339ac6fb18f4eaa1d1685aca4445d6c584af74fc87191eff4bf`,
anchors `Formal Gate 3 disposition`, `Solo Evaluation boundary` and `Reopening
rule`.

This protocol cannot produce Formal Gate 3 evidence, repair any terminal
`NON_SUCCESS` pair or reopen provider research. Formal Gate 3 remains
`NOT_ESTABLISHED / STOPPED`; its counted-evidence census remains `0`.

## 2. Study configuration

- One pre-declared shakedown pair: `Pair 0`.
- Six analytic pairs: `Pair 1` through `Pair 6`.
- Total: seven pair IDs and fourteen assigned attempts, one Control and one
  Treatment per pair.
- Breadth categories: straightforward fix, root-cause analysis, regression,
  specification ambiguity, cross-file change and small over-engineering-prone
  bug; one eligible natural bug each.
- Results support aggregate comparison only. No per-category or per-type effect
  claim is permitted because analytic `n=1` per category.

Pair 0 uses the first eligible simple bug and is outside analytic categories.
After it passes, Pair 1–6 use the first eligible bug per category. Each task has
one category; expected performance cannot affect selection or replacement.

## 3. Freeze before any attempt

Before creating a pair ID, freeze and retain:

- protocol identity and execution authorization;
- eligibility and category rules;
- bug report, expected behavior, repository and base-commit identity;
- task success criteria and allowed modification scope;
- identical model/build, budget, tools and permissions for both arms;
- arm order, cache state and anonymous scoring labels;
- oracle/test bytes or Git identity, written before either patch is visible;
- failure reasons, critical-regression definition and terminal decision rule.

Only Treatment has the Skill. Arms use isolated fresh contexts from the same
base. Order is pre-randomized or alternated and recorded; the first arm's patch
and reasoning are not exposed to the second.

## 4. Outcome and scoring hierarchy

Apply the same frozen evidence to both arms in this order:

1. deterministic bug oracle and hidden regression tests;
2. build, type, lint, performance, API and allowed-diff checks when applicable;
3. elapsed time, tokens, tool calls and review rounds;
4. identity-stripped blind automated quality scoring under a fixed rubric;
5. human judgment only for a pre-defined unresolved dispute.

Hidden tests are complete before either patch is seen. Owner-authored tests are
`agent-hidden`, not owner-blind. Blind scoring uses a fresh context and, when
available, a different model family; unavailable separation is reported.

Patch size and cost are diagnostics, not correctness substitutes. Correctness,
regression and scope compliance take precedence.

## 5. Attempt ledger and selection discipline

Create the pair ID and both arm records before execution. Each ends as
`SUCCESS`, `AGENT_FAILURE`, `HARNESS_FAILURE` or `UNCLASSIFIED`; retain outputs
and reason.

- `AGENT_FAILURE`: the assigned path exceeds budget, violates scope or produces
  no evaluable patch; count it as that arm's failure.
- `HARNESS_FAILURE`: frozen infrastructure prevents evaluation independently of
  patch quality. It is excluded from correctness comparison but remains visible
  in attrition.
- `UNCLASSIFIED`: count conservatively as assigned-arm `AGENT_FAILURE`.

IDs cannot be deleted, reused, overwritten or replaced. Reruns cannot replace
initiated attempts and exceed this study unless a revision-bound owner decision
authorizes a new one. Fixed `N` means initiated attempts, not completed samples.

Report attrition separately for Control and Treatment. Material asymmetry lowers
confidence in surviving-patch comparisons and is itself a reliability result.

## 6. Pair 0 shakedown

Pair 0 tests freezing, isolation, oracle, ledger, anonymization and unblinding.
It is always excluded from product comparison; retain both attempts and
dispositions.

Pair 0 cannot be replaced or repeated. If it reveals a protocol, oracle or
ledger defect, STOP before creating Pair 1–6 IDs. Any correction requires a new
protocol exact identity and revision-bound owner authorization.

## 7. Analytic decision rule

For Pair 1–6, the only arm satisfying the oracle without disqualifying
regression or scope violation wins; equal statuses tie. Costs use paired medians
across evaluable pairs.

- `CONTINUE`: Treatment correctness wins exceed Control wins, Treatment has no
  unique critical regression, and Treatment `AGENT_FAILURE` count is not higher;
  or correctness and agent-failure counts tie while Treatment improves at least
  two of elapsed time, tokens and review rounds.
- `STOP_USE`: Control correctness wins exceed Treatment wins, Treatment has a
  unique critical regression, or Treatment `AGENT_FAILURE` count is higher.
- `INCONCLUSIVE`: every other outcome, including insufficient evaluable pairs or
  attrition that prevents an honest comparison.

These are personal decisions, not effect estimates. Report every disposition,
per-arm attrition and metric before revealing arm identity.

## 8. Size, execution and claim ceiling

`6,000 bytes` is the compactness ceiling, not byte-neutrality. Amendments
may change length but must remain within it; otherwise STOP and revisit scope.
No appendix, second file, schema, validator or subsystem may bypass it. Semantic
correctness takes priority.

Adoption does not authorize task selection, IDs, tests, scorers, execution,
rehearsal, implementation, network activity, memory changes, cleanup or push.
Execution needs a separate revision-bound owner decision.
