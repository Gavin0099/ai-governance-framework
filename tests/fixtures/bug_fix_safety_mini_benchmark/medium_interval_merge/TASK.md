# Merge strictly overlapping half-open intervals

Repair `merge_intervals(intervals)` in `interval_merge.py`.
Input is a list of `[start, end]` integer pairs, always with start < end. Each
pair represents a non-empty half-open interval `[start, end)`. Input may be
unsorted, duplicate or nested. Return a new list of new two-element lists,
sorted by start then end, merging all transitively STRICTLY overlapping intervals.
Intervals that only touch (`next.start == current.end`) must remain separate.
Do not mutate or reorder the input, and do not return aliases of its inner lists.
Empty input returns a new empty list. Inputs are valid; invalid/reversed intervals
and non-integer endpoints are outside this task. No approximate arithmetic needed.

Reproducer: `merge_intervals([[1, 10], [2, 3]])` should return `[[1, 10]]`;
the baseline incorrectly shortens the covered interval to `[[1, 3]]`.

Allowed changes: only `interval_merge.py` and `test_interval_merge.py`. Preserve
the function name/signature and policies above. Python standard library/unittest
only; no I/O/dependencies, runtime changes or disabled tests. Return complete
source/test files and causal explanation. Do not claim unobserved execution.

Required regression categories: nesting cannot shrink extent; transitive overlap;
touching remains separate; unsorted/disjoint/duplicate input; empty/negative
endpoints; input unchanged and output lists do not alias input.

