# Gate 2 Admission Canary — Producer-Channel Dry Run, 2026-07-26

Status: **mechanism dry run on a disposable target, driven by a harness
emulator. No model session participated. Not a Gate 2 arm; touches no packet, no
sanitized baseline, no frozen or signed artifact; Gate 2 remains 0/4 arms and
0/2 scorers.**

Answers the three blocking findings the 2026-07-26 review raised against
`352168d7` (producer guard). Each is addressed by a change plus an exercise that
would have caught the original defect.

## Finding 1 — "the adapter cannot do the producer's job"

The sanctioned adapter admitted only `ls`, `log`, `read`, so a producer could
not change code, run a test, or produce a result: safe but unusable.

**Change.** The verb/argument contract moved out of the code and into a policy
JSON that the guard *and* the adapter both load
(`gate2-runtime/producer-guard/gate2_policy.py`). The canary contract
(`policy_canary.json`) admits `ls read write test diff status report` — enough
to do the job, and nothing more: no verb runs an arbitrary command, none reaches
the network, none writes outside the workspace, none takes anything out of the
sandbox. File content travels as base64 in an argument and is streamed to
`cp /dev/stdin` inside the container, so no content ever passes through a shell.

**Exercise.** The full vertical slice ran through the channel against a
disposable canary repo whose `add(2, 3)` returned `-1`: read task/code/test →
`test` **exit 1** (`FAILED (failures=2)`) → `write` the fix → `test` **exit 0**
(`OK`) → `diff` → `status` → `report`. 13 executed calls, all through the
adapter. The result artifact was read back out of the container afterwards by
the operator, not by the producer.

## Finding 2 — "the transcript cannot be uniquely correlated"

The pre hook minted its own `request_id`; the post hook did not keep it and
matched on a command digest, so two identical calls were indistinguishable.
Failures had no event at all, and the two sides hashed different things.

**Change.** Every event is keyed by the harness-supplied `tool_use_id`, which
the published hooks reference confirms is present on `PreToolUse`,
`PostToolUse` **and** `PostToolUseFailure`. `PostToolUseFailure` is now wired to
the same recorder. The two sides share one observable definition — the adapter
hashes the exact bytes it prints under `s.rstrip("\r\n")`, the post hook hashes
`tool_response["stdout"]` under the identical normalisation — and the digest of
the whole structured response is kept separately and explicitly not compared.
A payload with no `tool_use_id` is blocked, because an uncorrelatable call is
not evidence.

**Exercise.** Two byte-identical `read src/calc.py` calls stayed individually
resolvable; a genuinely failing call arrived as `PostToolUseFailure` under its
request's id; the failing test arrived the other way, as a `PostToolUse` with a
non-zero exit. Both delivery shapes are covered because which one Claude Code
actually uses is not yet observed.

## Finding 3 — "transcript writes fail open"

Both `_emit()` calls swallowed `OSError`: pointing `GATE2_TRANSCRIPT` at an
unwritable location produced `allow`, exit 0, and no audit record.

**Change.** The guard proves the transcript is writable *before* deciding and
blocks with exit 2 if it is not; `emit()` no longer swallows anything.

**Exercise.** Four negative controls — unwritable transcript, missing
`tool_use_id`, unset `GATE2_POLICY`, malformed policy — each blocked with exit 2
**and** left the adapter's sequence counter unchanged, which is the proof the
call never executed rather than merely went unrecorded.

## Warnings

- **Deny protocol.** Exit 2 discards stdout JSON, so the previous "JSON *and*
  exit 2" was a contradiction. One protocol now: allow and decided deny both
  exit 0 carrying the decision JSON; only undecidable/unauditable states exit 2,
  with the reason on stderr and no JSON.
- **Check count.** The README claimed 41 where the suite printed 46. The suite
  now prints its own count (currently **88**) and the README quotes that number.

## Independent verification

`verify_transcript.py` reads **only** the transcript and the adapter log — never
the guard, the adapter or the container — and applies 15 checks: one terminal
event per allowed call under its own id; none for denied calls; no orphan
results; allowed-call count equals adapter executed-line count; ordered
verb+argument-digest join; shared stdout digest agreement; zero adapter-side
rejections (anything it rejected is a guard escape); one policy digest
throughout, on both sides.

`test_verify_transcript.py` then breaks a consistent evidence pair thirteen ways
and requires the specific check that should catch each to fail. A verifier
nobody has tried to fool is not evidence.

| Suite | Result |
|---|---|
| `producer-guard/test_producer_guard.py` | 88 checks, all pass |
| `producer-guard/test_verify_transcript.py` | 13 mutation checks, all pass |
| `admission-canary/test_canary_conformance.py` | 18 checks, all pass |
| `run_canary.py` | 9 isolation facts, 35 steps, 4 controls — all as expected |
| `verify_transcript.py` over the run | 15 checks, all pass |

Evidence: `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/evidence/`
(`transcript.jsonl`, `adapter-log.jsonl`, `verification.json`, `run-report.json`,
`run-console.txt`, `container-inspect.json`, `container-result.json`).

## Container properties, read back from the daemon

`--network none`, read-only rootfs, `CapDrop: [ALL]`, `no-new-privileges`, uid
65532, **no host bind mount**, `/work` a tmpfs, no docker socket, image
`sha256:e6df7283…` (the pinned build). The canary repo was streamed in over
stdin — nothing from the host is mounted, so the container has no path back to
the framework repo even if the channel failed.

## What this does NOT establish

- **No model was in the loop.** The dispatcher was `harness_emulator.py`, a
  Python stand-in performing the documented hook sequence. The run proves what
  the guard, adapter, container and transcript do when driven per the published
  contract; it does not prove Claude Code drives them that way. Unobserved: that
  Claude Code supplies `tool_use_id` on all three events, that it honours an
  exit-0 deny JSON as a block, which post event a non-zero Bash exit produces,
  and the real shape of `tool_response`.
- **Enforcement remains harness-scoped**, not a kernel boundary. An operator who
  runs a producer without these hooks configured gets no protection at all, so
  resource admission must verify the hooks are live in each producer context
  rather than assume it.
- The read-only rehearsal adapter `repo_tool.sh` still implements its contract
  in bash; only the canary adapter is genuinely policy-driven.

## Defect found by this exercise

The first canary run reported **every step passing while the adapter never
executed once**: the driver resolved `bash` to WSL's launcher, which failed with
a bare exit 1, and the driver checked only that a call had been *allowed*, never
that it had *succeeded*. Allowed steps now assert exit code and expected output,
and the emulator refuses to guess at a shell. Recorded because a green dry run
that ran nothing is precisely the failure mode admission testing exists to
catch.

## Next step

One real producer session with these hooks wired, on a fresh disposable target,
whose sole purpose is to capture the actual hook payloads and confirm the four
unobserved harness behaviours. It cannot be this design session, which knows the
canary's answer. Only after that, and after review, does a separate
admission-only context on a fresh export of frozen tree `36c346fa…` become
appropriate — verifying image, tree, packet allowlist, hooks, permissions and
isolation only, with no bug dispatch, not counted as an arm.
