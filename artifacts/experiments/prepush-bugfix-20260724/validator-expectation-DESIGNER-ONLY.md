# Validator Expectation — DESIGNER / SCORER ONLY (NEVER give to a producer)

WITHHELD FROM PRODUCERS. This file states the expected validator signal and the
reasoning behind it, which reveals the defect's nature. It must never be placed
in a producer/arm environment. It is for the experiment designer and the blind
scorer's post-hoc analysis only, and even the blind scorer reads it only after
all arm outputs are committed and blinded.

Enforcement: the producer-environment file allowlist (isolation spec, amendment
v2 Section C) does NOT include this file. Its presence in the repo does not place
it in any arm environment.

## Expected signal: NULL

The three pinned validators (shellcheck / ruff / mypy) are expected to produce no
finding that identifies the defect. The defect is a control-flow / argument-
passing error, not a shell-syntax, style, import, or type smell, so these tools
have no rule that flags it. A null Arm D result is therefore scored as an
informative expected outcome, not as a failure.

## Consequence for D−C

Because the treatment-time validator feedback in Arm D is expected to be empty
for this defect, `D−C` is expected ≈ 0 for this task. This is a known limitation
of using a logic bug as an Arm D exercise (program Section 10.1); it does not
invalidate the pilot.
