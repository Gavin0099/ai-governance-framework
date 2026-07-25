# gate2-admission-canary — a disposable end-to-end dry run of the producer channel

A review approved the guard's deny logic but refused admission on the ground
that nobody had shown the channel could carry an actual producer job, or that
its evidence was complete. This is that demonstration, deliberately run on a
throwaway target:

- **not** the frozen sanitized baseline (`36c346fa…`) — a dry run that fails
  must not contaminate or consume a real arm;
- **not** another live repo — its toolchain and risks would confound the test;
- a planted defect with no governance content and no interesting answer, so
  nothing about the Gate 2 treatment can leak or be learned from it.

```
canary-repo/          src/calc.py (add(2,3) returns -1), tests/test_calc.py, TASK.md
policy_canary.json    the contract: ls read write test diff status report -- and nothing else
canary_adapter.sh/py  the only sanctioned path in; policy-driven, argv-only, never a shell string
setup_canary.sh       build + seed the isolated container
harness_emulator.py   drives the documented hook contract (NOT Claude Code -- see limits)
run_canary.py         the run: isolation attestation, workflow, bypasses, duplicates, failure, controls
test_canary_conformance.py   policy and adapter describe the same channel (18 checks)
evidence/             transcript, adapter log, verification, console output, container attestation
```

## Running it

```bash
bash setup_canary.sh && python run_canary.py
python ../producer-guard/verify_transcript.py \
  --transcript evidence/transcript.jsonl --adapter-log evidence/adapter-log.jsonl
```

## What the run does, and what it showed

**Phase 0 — what the box actually is** (9 checks, read back from the daemon):
`--network none`, read-only rootfs, `CapDrop: [ALL]`, `no-new-privileges`, uid
65532, **no host bind mount at all**, `/work` a tmpfs, no docker socket, and the
pinned image id `sha256:e6df7283…`. The repo is streamed in over stdin, so the
container has no path back to the framework repo even if the channel broke.

**Phase 1 — the producer vertical slice, entirely through the channel.** Read
the task, the code and the test; run the test (**exit 1**, `FAILED
(failures=2)`); write the fix; run the test again (**exit 0**, `OK`); read the
diff and status; emit a result artifact. The container attests each write's
sha256 itself. The artifact was read back out afterwards, by the operator over
`docker exec` — there is deliberately no verb that takes anything *out* of the
sandbox.

**Phase 2 — 22 bypass attempts, all refused before execution**: direct
`docker exec`/`cp`/`-u 0`, host answer surfaces, `git -C` the framework repo,
`curl`, chaining and redirection after a legal call, command substitution,
traversal and `.git/` writes, an unmapped verb, a look-alike adapter, an extra
argument, and seven non-Bash tools. The adapter log contains **zero** rejected
lines — nothing reached the adapter at all.

**Phase 3 — two byte-identical calls** stay individually correlated by their own
`tool_use_id`. This is exactly what the previous command-digest matching could
not do.

**Phase 4 — a genuinely failing call** (`read nosuchfile.txt`) delivered as
`PostToolUseFailure`, correlated to its request by the same id. The failing test
in phase 1 was delivered the other way, as a `PostToolUse` with a non-zero exit,
so both delivery shapes are covered.

**Phase 5 — four negative controls**, each of which must block *before* anything
runs: unwritable transcript, missing `tool_use_id`, unset `GATE2_POLICY`,
malformed policy. Each blocked with exit 2, and the adapter's sequence counter
did not advance — proof the call never executed, not merely that it was not
recorded.

Result: **35 steps, 4 controls, 9 isolation facts as expected; 13 executed
calls; 15/15 artifact-only audit checks pass** (`evidence/verification.json`).

## What this does NOT establish

**No model was in the loop.** `harness_emulator.py` is a Python stand-in that
performs the documented hook sequence. The run therefore proves what the guard,
adapter, container and transcript do *when driven per the published contract* —
it does not prove Claude Code drives them that way. Specifically unobserved:

- that Claude Code supplies `tool_use_id` on all three events (documented, not
  observed here);
- that it honours an exit-0 deny JSON as a block;
- whether a non-zero Bash exit arrives as `PostToolUse` or `PostToolUseFailure`
  (both are handled, so either is fine — but which one happens is unknown);
- the real structure of `tool_response` for Bash (`RESPONSE_SHAPE` in the
  emulator is an assumption; the post hook also tolerates a plain string).

Closing that gap needs one real producer session with these hooks wired, on a
disposable target, whose only purpose is to capture the payloads. It cannot be
closed from this design session, which knows the canary's answer.

This canary is also **not** a Gate 2 arm, does not touch the frozen tree, does
not consume a producer or scorer context, and does not move Gate 2 off 0/4.

## Disposal

```bash
docker rm -f gate2-admission-canary
```

The container is disposable and holds nothing that is not reproducible from
`canary-repo/` plus `setup_canary.sh`.
