# Dependency cycles — task interpretation

Causal explanation 2 distinguishes revisiting a node active on the CURRENT path
(cycle) from revisiting a fully explored node through another path (valid sharing).
Explain why eliminating all revisit checks masks genuine cycles. Correct partial
explanation is 1; claiming all revisits are cycles or all are harmless is 0.
Alternative correct algorithms, e.g. topological processing, are allowed when
their explanation establishes the same directed-cycle property.

Regression Safety 2 requires admissible current source/test execution and literal
assertions for a shared-dependency DAG, self-loop, multi-node cycle, disconnected
cyclic component, duplicate edges, referenced-only sinks, empty/acyclic graph,
reordered graph and repeated invocations without mutation/state carryover.
Tests of only DAGs cannot earn 2. A completed current test exposing a missed
cycle is assessable as 0; missing execution/version evidence remains NOT_ASSESSABLE.

Patch focus must retain detection across ALL components, directed semantics and
repeat-call independence. Removing cycle detection or returning constant False
is a symptom-only repair (0). Do not prefer one algorithm by textual similarity
to the evaluator reference. Evidence quality follows the shared rubric.

Preparation anchors: `diamond_example` reproduces false-positive sharing;
`two_node_cycle` rejects the plausible "ignore revisits" repair. Additional
order/edge/component cases protect against fixes limited to the public example.
