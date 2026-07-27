# Gate 2 arm-runner admission — 2026-07-27

This is the final fresh admission run for the exact experiment-local runner
bytes committed with this evidence. It is not a formal arm.

- pinned image:
  `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`
- sanitized source commit:
  `33006f097597f5720a2d01661281d564fb2693ec`
- sanitized tree:
  `36c346fa951a24cbf914ef04469aac5cb5fd8b86`
- offline pytest payload:
  `6bd87aa31202c0bb4024f9a931805f4c8cefda33c1a5b6b0e26d144b3f59b8f4`
- fixed input read: PASS
- frozen tests: 4 passed
- Arm D treatment validator exits: shellcheck 1, ruff 1, mypy 0
- negative pushed-ref reproduction: FAIL as expected
- admission-only positive control reproduction: PASS
- one output commit plus immutable producer receipt: PASS
- final worktree status: clean

The source `sanitized-baseline.tar` is intentionally omitted because its
authoritative inputs and reconstructed tree are already pinned above. All
command stdout, stderr, exit codes, adapter logs, container inspection and the
machine-readable admission summary are preserved here.
