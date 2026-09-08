# Interval merge — task interpretation

Apply shared evidence admission and scoring. Causal explanation 2 identifies
replacement of the accumulated end as the shrinkage cause, describes preserving
the maximum extent through nesting/transitive overlap, and respects strict
overlap rather than adjacency. Correct but partial explanation is 1; changing
the touching policy to cure the example is a wrong explanation/repair.

Regression Safety 2 requires current-version test execution plus independent
assertions for nesting, transitive chains, touching pairs, unsorted/disjoint and
duplicate intervals, empty/negative inputs, non-mutation and no inner-list aliases.
Visible tests covering only the nesting example are incomplete (1 if admissible).
Shared-rubric missing/stale/execution-failure rules take precedence over coverage.

Patch focus 2 preserves half-open semantics and sorted output without shortening
coverage or altering caller-owned data. No required algorithm, exact line count
or preference for matching the reference implementation. Evidence quality must
accurately attribute execution and acknowledge actual failed checks.

Preparation anchors: `nested_example` fails the baseline; `touching_pair` rejects
a plausible max-end repair that incorrectly imports closed-interval semantics.

