# Replacement disposable creation launcher

This launcher implements creation and separately authorized readiness/wait wiring.
Its presence and a successful static check do not authorize real creation or
readiness, or prove runtime admission ready.

`launch.ps1 -Mode check` verifies the pinned outer executable, Python runtime,
source dependencies and candidate Codex payload without allocating an evaluation,
ledger, Pair, key or runtime root. It does not run Codex readiness.

After separate owner creation authorization, `-Mode phase-a` uses only the adopted
replacement placement and binding. It verifies authority and quiescence, creates
fresh custody, evaluation/genesis and Pair, writes a Pair-specific payload-pin
candidate and Phase A state, verifies the two-event ledger and stops. Any occupied
namespace is rejected; this entrypoint does not recover interrupted creation.

Successful Phase A ends with Attempt 0, exposure NONE and readiness NOT RUN.
The printed pin is a candidate, not owner adoption. Old state and old pins confer
no authority on this replacement.

`-Mode phase-b` is restricted to the already-created replacement evaluation and
Pair. It reads the two exact adoption blobs from commit `10840d57`, checks their
worktree copies, and verifies the external Phase A state against the digest in
that committed adoption. The state itself is not a committed file. The new ledger
must still be exactly two events, with no Attempt or exposure. Existing runtime
evidence prevents a rerun; this is not a resume path.

Phase B requires the dedicated `C:/Users/daish/.codex-r2-replacement-canary` HOME.
If absent, it stops; this launcher neither provisions it nor falls back to an old
HOME. It resolves and rehashes the installed Codex payload after checking adoption,
then uses the existing quiescence, containment, freeze and readiness APIs. A PASS
retains window/backend/adapter/materializer/readiness references in the waiting
controller. Blank input and EOF do not return or authorize; `ABORT` or Ctrl+C
discards the live handoff. Saved JSON is historical evidence, never a resume token.

At the live pause, the controller prints the exact one-use authorization form:
`EXECUTE <evaluation_id> <pair_id> <controller nonce>`. Only that exact line,
without leading/trailing whitespace, can invoke the existing execution API.
Blank input, EOF, malformed identities and stale nonces do not authorize.
An accepted authorization is consumed before revalidation; failure stops and
does not permit retry. The transition rechecks committed adoption, external state,
replacement binding/two-event ledger and current payload. Original window,
readiness and runtime-object identities must remain live; reconstructed equivalent
objects are rejected. The existing execution API performs its own current freeze
and admission checks and consumes readiness once without rerunning the window.

Execution capability is not execution authorization. Only a separately authorized
human command at the live pause may start both replacement arms; it grants no
oracle, scoring, unblinding or retry authority. Tests substitute the arm execution
API and never run a real Codex arm. No actual Phase B runs in wiring tests.

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
