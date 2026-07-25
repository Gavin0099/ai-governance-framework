# Gate 2 producer guard — adapter exclusivity, one contract, auditable transcript

A `PreToolUse` hook that decides, a `PostToolUse` / `PostToolUseFailure` hook
that records the result, a policy file both the guard and the adapter load, and
a verifier that reads only the resulting artifacts.

| File | Role |
|---|---|
| `gate2_policy.py` | the verb/argument contract, loaded by guard **and** adapter |
| `policy_rehearsal.json` | contract for the read-only rehearsal adapter (`repo_tool.sh`) |
| `gate2_producer_guard.py` | PreToolUse hook — decides, and refuses to decide unauditably |
| `gate2_producer_posttool.py` | PostToolUse **and** PostToolUseFailure — records the result |
| `verify_transcript.py` | artifact-only auditor: does this evidence join up? |
| `test_producer_guard.py` | 88 hostile checks |
| `test_verify_transcript.py` | 13 mutation checks — proves the verifier catches breakage |

## What is technically enforced

The guard returns `deny` unless the call is exactly the sanctioned adapter with
a verb and arguments the policy admits. The adapter path is compared by
`os.path.realpath` **and** required to exist, so a relative path, a symlink, a
copy or a bogus path cannot stand in for it.

| Bypass route | Result |
|---|---|
| `docker exec` / `docker cp` / `docker run` | denied |
| reading host answer surfaces (`memory/`, `docs/status/…`) | denied |
| `git -C <framework repo>` | denied |
| network egress (`curl`) | denied |
| any non-Bash tool (`Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `Task`) | denied |
| chaining / redirect / substitution (`;` `&&` `\|` `>` `$( )` backticks, newline) | denied |
| argument abuse (`../../etc/passwd`, `.git/config`, `..`, over-long, extra tokens) | denied |
| verb abuse (`sh`, `exec`, `eval`, `LS`, `read2`) | denied |
| a look-alike adapter at another path | denied |
| guard unconfigured, policy missing or malformed | **blocked** (exit 2) |

## One contract, not two

The verb/argument contract is a policy JSON that the guard and the adapter both
load, and whose `policy_id` + `sha256` are stamped into every transcript event
and every adapter log line. The verifier fails the run if the two sides ever
show different policy digests. The previous design wrote the contract twice —
regexes in the guard, a `case` statement in the adapter — which a review flagged
as guaranteed future drift.

The loader is strict: unknown keys, unanchored patterns, bad regexes and missing
fields all raise, and the guard then blocks. A contract that cannot be fully
understood must not admit anything.

## The output contract

The published hook semantics are that stdout JSON is processed **only** at exit
0, and that exit 2 blocks with stderr as the reason. Mixing the two — printing a
deny JSON *and* exiting 2, as the first version did — means the JSON is
discarded. So:

| Situation | stdout | exit |
|---|---|---|
| allow | allow JSON | 0 |
| decided deny (route or policy violation) | deny JSON | 0 |
| **undecidable or unauditable** — no policy, malformed policy, no `tool_use_id`, transcript unwritable, guard defect | reason on **stderr** | **2** (blocks) |

## The transcript, and why it cannot go quietly missing

Every event is keyed by the harness-supplied **`tool_use_id`**, the same id
present on `PreToolUse`, `PostToolUse` and `PostToolUseFailure`. Correlation is
by identity, not by re-hashing the command — two byte-identical calls stay
individually resolvable, which command-digest matching could not do.

```
{"event":"pre_tool_use","tool_use_id":"toolu_…","verb":"write",
 "args_summary":["src/calc.py","<b64 len=444 sha256=4adc0630…>"],
 "args_sha256":…,"command_sha256":…,"decision":"allow",
 "policy_id":"admission-canary-1","policy_sha256":…}
{"event":"post_tool_use","tool_use_id":"toolu_…","stdout_sha256":…,
 "observable_source":"tool_response.stdout","response_keys":[…]}
```

Three fixes a review demanded, all now in place:

- **`PostToolUseFailure` is wired.** A failed call produces a terminal event
  under the same `tool_use_id`, so failures are part of the chain rather than a
  hole in it.
- **One shared observable.** The adapter hashes the exact bytes it writes to
  stdout under `s.rstrip("\r\n")`; the post hook hashes `tool_response["stdout"]`
  under the identical normalisation. Those two digests are what the verifier
  joins. The digest of the whole structured response is kept separately and is
  explicitly *not* comparable with the adapter's.
- **An unwritable transcript blocks the call.** The old `_emit()` swallowed
  `OSError`, so pointing `GATE2_TRANSCRIPT` at an unwritable path produced allow
  decisions with no audit record at all. The guard now proves the transcript is
  writable *before* deciding, and blocks with exit 2 if it is not.

Digests, never payloads: content that exists only inside the container is never
copied out into the transcript, and a large argument (a base64 file body) is
reduced to a digest.

## Verifying a run from artifacts alone

```bash
python verify_transcript.py --transcript t.jsonl --adapter-log a.jsonl
```

15 checks, including: every allowed call has exactly one terminal event under
its own id; no denied call has one; no orphan results; allowed-call count equals
adapter executed-line count; ordered verb+argument-digest join; the shared
stdout digest agrees on both sides; the adapter rejected nothing (anything it
rejected is something the guard should have stopped); one policy throughout.

`test_verify_transcript.py` breaks a consistent evidence pair thirteen ways —
missing result, duplicated result, orphan result, result for a denied call,
altered digest, extra adapter line, reordered log, guard escape, changed policy,
lost or duplicated correlation id — and requires the specific check that should
catch each one to fail. A verifier nobody has tried to fool is not evidence.

## Wiring (producer context ONLY)

```json
{"hooks": {
  "PreToolUse":         [{"matcher":"*","hooks":[{"type":"command",
     "command":"python <abs>/gate2_producer_guard.py"}]}],
  "PostToolUse":        [{"matcher":"*","hooks":[{"type":"command",
     "command":"python <abs>/gate2_producer_posttool.py"}]}],
  "PostToolUseFailure": [{"matcher":"*","hooks":[{"type":"command",
     "command":"python <abs>/gate2_producer_posttool.py"}]}]
}}
```

Environment: `GATE2_ADAPTER` and `GATE2_POLICY` (both required, absolute),
`GATE2_RUN_ID`, `GATE2_TRANSCRIPT`.

## Honest limits — read before treating this as sufficient

- **Enforcement is harness-scoped.** It holds for a producer running under a
  harness that honours `PreToolUse` decisions with these hooks configured. It is
  not a kernel or container boundary: an operator who runs the agent *without*
  this configuration gets no protection. Resource admission must verify the hook
  is actually active in each producer context, not assume it.
- **No model has yet driven it.** The end-to-end exercise
  ([admission canary](../admission-canary/README.md)) was driven by a harness
  *emulator* implementing the documented hook contract. What Claude Code itself
  does — that it supplies `tool_use_id` on all three events, that it honours an
  exit-0 deny JSON, whether a non-zero Bash exit arrives as `PostToolUse` or
  `PostToolUseFailure`, and the real shape of `tool_response` — is taken from
  the published hooks reference and has **not** been observed here.
- **It does not by itself prove a model rather than a human issued a call.** It
  proves the harness saw a tool call from the agent session and what that call
  was.
- The rehearsal adapter `repo_tool.sh` still implements its own contract in
  bash; `policy_rehearsal.json` describes it but does not drive it. Only the
  canary adapter is genuinely policy-driven. Treat `repo_tool.sh` as superseded.

## Defects found by these tests, kept as notes

- The first guard banned backslash as a shell metacharacter, which denied
  **every legitimate call on Windows**, since the adapter path contains
  backslashes — a guard so fail-closed it was useless. A Windows-path regression
  test guards against reintroducing it.
- The first canary driver reported every step as passing while the adapter never
  executed once: it resolved `bash` to WSL's launcher, which failed with a bare
  exit 1, and the driver only checked *that* a call was allowed, never that it
  succeeded. Allowed steps now assert exit code and expected output.
