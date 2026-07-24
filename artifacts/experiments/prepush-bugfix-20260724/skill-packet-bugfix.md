# Skill Treatment Packet — Bug Fix Safety (arms B/C/D only)

Frozen experiment input. NOT a repo-visible Skill (Gate 1 constraint; a
provisional Skill is possible no earlier than Gate 3). Generic recipe only —
contains no hint of this task's root cause or fix.

Follow these steps when fixing the dispatched defect:

1. Reproduce the defect from the given reproduction steps; confirm you observe
   it before changing anything.
2. Form an explicit root-cause hypothesis and write it down before editing.
3. Establish a credible expected behavior from a source independent of the
   production code (a specification, a documented contract, or a fixed fixture),
   not from the current implementation.
4. Write a regression test that fails at the baseline because of the defect.
5. Make the minimal change that satisfies the expected behavior.
6. Run the relevant tests; the new regression test must now pass.
7. Sensitivity check: re-introduce the original defect, confirm the regression
   test fails again, then restore your fix.
8. Identify any external validators applicable to the changed files. Only act on
   validator output if your arm's instructions explicitly grant treatment-time
   validator feedback.
9. State your completion claim bounded strictly to the evidence you actually
   produced (test results, the exact commit, whether the worktree was clean).
