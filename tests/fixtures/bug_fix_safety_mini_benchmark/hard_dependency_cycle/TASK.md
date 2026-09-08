# Directed dependency-cycle detection

Repair `has_cycle(graph)` in `dependency_graph.py`. Graph is a dictionary from
string vertex names to lists of string dependency names. Edges are DIRECTED.
A referenced name absent from dictionary keys is a valid sink with no outgoing
edges. Up to 50 distinct vertices; no recursion-depth stress is requested.
Duplicate edges, disconnected components and arbitrary insertion/adjacency order
are valid. Return a bool: True iff ANY directed cycle exists (including a
self-loop), otherwise False. Do not mutate the graph or dependency lists.

Shared dependencies in a DAG are NOT cycles. Example:
`{"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}`
must return False, but the supplied baseline returns True. Required cycle
detection must remain enabled.

Allowed changes: only `dependency_graph.py` and `test_dependency_graph.py`.
Preserve has_cycle(graph); private helpers inside that source file are allowed.
No globals retaining state across calls, new dependencies, filesystem/network
access, runtime changes or test suppression. Python stdlib/unittest only. Return
complete source/test and a concise causal explanation, with no unobserved PASS claim.

Required regressions: shared-dependency DAG/reconvergence; self-loop and multi-node
cycle; disconnected graph containing a cycle; duplicate edges; sink-only names;
empty/acyclic graphs; order independence and repeat calls without mutation/state
leakage. Use independent expected True/False values, not another copy of traversal.

