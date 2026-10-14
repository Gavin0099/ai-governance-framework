# S2 case-varied non-product exclusion repair

External review: P2 from chatgpt-codex-connector, PR210 discussion4266084468, reviewed original f7215e60. The shared case-sensitive helper predates S2, while S2 exposes a new GDScript false-positive path. Current original-head merge impact YES: capitalized Tests/DOCS/Fixtures violate the frozen non-product exclusion. Disposition fix now; original P2 severity preserved.

Implementation 88824c4db3533221ff7b75ee5c6d8a7c25ac1d33 changes only governance_tools/rule_pack_suggester.py and tests/test_rule_pack_suggester.py. Exact path components are casefolded against the existing seven-root exclusion; no substring filtering, new roots, confidence thresholds, activation, Runtime, CI or schema changes. Both filesystem and Git-visible inventory use this helper, so existing language/framework exclusion receives the same intended correction.

Failure-first fixture evidence: case-exclusion-red-rendered.txt records 8 failed exclusion examples plus 1 passing product control. Cases include Tests, DOCS, Fixtures, Examples, Archive, Artifacts, AI-Governance-Framework and nested Runtime/FiXtUrEs, with .gd and .py. Valid Scripts/TestsRunner remain product signals. Fixed committed tests: case-exclusion-committed-tests.json/.xml/.txt record 75 passed linked to implementation HEAD. Standard local precommit: case-exclusion-precommit.txt records shared smoke plus 207 Runtime tests passed.

Independent reviewer /root/independent_gdscript_review examined the working correction and found it appropriate and bounded, with no additional blocker. Literal boundary fixtures are independent of the filtering algorithm. Final committed delivery HEAD review and hosted CI still required; working feedback is not final-head approval.

Earlier INDEPENDENT_REVIEW.md and S2_FINAL_INDEPENDENT_REVIEW.md are historical predecessor-head reviews, superseded for repaired-head merge readiness. Their recorded observations are retained, not rewritten. S1 merged normally at06b9890655f60eb0b1c12617f6bb3f5c3ecf8ede; its PR CI38499275801 and post-merge CI38499890143 passed. Original S2 CI38499926428 passed but cannot qualify the new repaired head.

Memory evidence-root formal provenance qualification remains unclaimed. Active-task memory remains CRITICAL and is not expanded. No release, consumer pin/F7, Godot native/gameplay or full-adoption claim. This repair does not weaken merge protection; owner exact-head authority and final independent review/checks remain separate predicates.

Failure output rendering removes trailing whitespace only. Original raw case-exclusion-red.txt is preserved locally and excluded from the commit; raw SHA256 60d06d44dec89b24bfd9db9a498b1613385bdf3a9a2ff3c6dbdc0cf9b5e730b7. The committed rendering preserves every diagnostic/count and is not formal provenance qualification.
