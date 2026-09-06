# Queue range selection

Repair the supplied offline Python queue helper so selecting entries by an
inclusive numeric sequence range includes entries at both endpoints. Preserve
the original order, duplicate entries and the input collection. An empty input
or a lower bound greater than the upper bound must return an empty list.

The supplied helper interface is select_entries(entries, lower, upper), where
entries is a list of (sequence_number, payload) tuples and bounds and sequence
numbers are integers. Return a new list containing the selected original tuples.
Preserve behavior for entries strictly inside or outside the requested range.

Work only in the supplied offline snapshot. Limit edits to queue_range.py and
directly related regression tests. Use only the installed Python standard
library and unittest. Do not install dependencies, access the network, inspect
external repositories or historical fixes, or read files outside the supplied
workspace and designated temporary directory. Do not access credentials,
evaluator materials or other executions' outputs.

Deliver the modified workspace and a concise final response explaining the
change, the validation actually performed, its observed results and any
remaining limitation. Do not claim a test passed unless it ran successfully.
Do not commit or push.
