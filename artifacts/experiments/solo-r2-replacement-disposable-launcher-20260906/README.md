# Replacement disposable creation launcher

This launcher implements creation wiring only. Its presence and a successful
static check do not authorize real creation or prove runtime admission ready.

`launch.ps1 -Mode check` verifies the pinned outer executable, Python runtime,
source dependencies and candidate Codex payload without allocating an evaluation,
ledger, Pair, key or runtime root. It does not run Codex readiness.

After separate owner creation authorization, `-Mode phase-a` uses only the adopted
replacement placement and binding. It verifies authority and quiescence, creates
fresh custody, evaluation/genesis and Pair, writes a Pair-specific payload-pin
candidate and Phase A state, verifies the two-event ledger and stops. Any occupied
namespace is rejected; this entrypoint does not recover interrupted creation.

Successful Phase A ends with Attempt 0, exposure NONE and readiness NOT RUN.
The printed pin is a candidate, not owner adoption. There are no readiness,
execution, adoption or resume modes. A future consumer must separately verify
and obtain adoption of the exact new pin; old state and old pins confer no
authority on this replacement.

The manifest preserves the prior outer launcher's executable and standard-library
inventory. Six source pins are updated to the independently reviewed production
bytes committed at `de85d2f8` and present at `54bf67b0`. Its
`replacement_binding_source_commit` records that checked provenance; the actual
launch decision uses exact bytes, not an assumption that HEAD remains fixed.
The current installed Codex path is recorded only as candidate payload metadata.
No old payload-pin adoption is imported, even when payload bytes match.

Tests use isolated temporary repositories and custody paths for real creation
APIs, with host quiescence/identity observations substituted. Outer wrapper tests
exercise `check` only, including source, manifest, dependency and payload drift,
hostile ambient selectors and rejection of unsupported continuation modes.
These tests prove wiring and rejection behavior, not real-host creation,
readiness, arm execution or completed A/B evaluation.
