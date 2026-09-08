# Inclusive queue selection

Repair `select_entries(entries, lower, upper)` in `queue_range.py`.
Inputs: a list of two-element lists `[sequence, payload]`, where sequence and
bounds are integers and payload is a string. Return a NEW outer list containing
exactly entries whose sequence lies in the inclusive range `[lower, upper]`.
Retain input order and duplicate entries; do not mutate input. Sharing unchanged
entry objects is permitted. Empty input or reversed bounds yields a new empty
list. Unsorted and negative sequences are valid. Inputs meet these types; no
extra coercion, validation or exception policy is requested.

Reproducer: `select_entries([[1, "a"], [2, "b"]], 1, 3)` should return both entries;
the supplied baseline loses the entry at the lower boundary.

Allowed changes: only `queue_range.py` and `test_queue_range.py`. Preserve the
function name/signature and behavior above. Python standard library only; tests
use unittest. No external I/O, dependencies, runtime changes or test suppression.
Return complete source/test files and a concise causal explanation. Do not claim
tests ran unless actual execution evidence is available.

Required regression categories: both endpoints and equal bounds; duplicates and
input order; empty/reversed ranges; non-mutation and new outer list; negative
sequences/no matches. Test assertions must specify expected values independently.

