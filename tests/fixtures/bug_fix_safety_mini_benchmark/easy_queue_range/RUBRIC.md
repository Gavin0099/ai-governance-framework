# Queue selection — task interpretation

Apply the shared rubric; do not change weights or oracle outcomes after a run.

- Causal explanation 2: explains that strict comparisons exclude endpoints and
  why BOTH predicates must be inclusive. Merely describing the intended output
  without this mechanism is 1; claiming only one boundary matters is 0.
- Regression Safety 2 requires visible assertions for lower AND upper endpoints,
  equal bounds, duplicates/order, empty/reversed ranges, unchanged input/new outer
  list, and negative/no-match input, with current-version completion evidence.
  One shared test may cover several categories. A lower-only passing test is
  meaningful but incomplete coverage (1 when execution is admissible).
- Patch focus: do not sort/deduplicate, alter payloads, mutate input, or introduce
  unnecessary state. A local predicate repair is sufficient, not mandatory syntax.
- Evidence quality: distinguish generated test source from actual host results.
  Additional process/tool cost is reported separately, not silently deducted.

For preparation reviewers: `lower_example` demonstrates the baseline defect;
`upper_endpoint` distinguishes a lower-only superficial repair. This rubric is
scorer material, not additional hidden-oracle feedback to the arm.

