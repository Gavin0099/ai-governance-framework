# Gate 2 Producer Guard — technical adapter exclusivity + transcript capture

Closes the two must-fix items a review raised against the channel rehearsal:

1. **Adapter exclusivity was prompt-plus-log corroboration, not enforcement** —
   a direct `docker exec` bypass simply would not appear in `adapter-log.txt`.
2. **Raw model request/response transcripts were never captured** — so artifacts
   alone could not distinguish a model from a human issuing the tool calls.

Both are now handled by one mechanism: a `PreToolUse` hook that decides, and a
`PostToolUse` hook that records the result.

## What is technically enforced

`gate2_producer_guard.py` runs **before** any tool call in the producer context
and returns a `deny` decision unless the call is exactly:

```
<sanctioned adapter>  ls
<sanctioned adapter>  log
<sanctioned adapter>  read <name matching ^[A-Za-z0-9._-]{1,64}$>
```

Denied by construction, all proven by `test_producer_guard.py` (41 checks, all
passing):

| Bypass route | Result |
|---|---|
| `docker exec` / `docker cp` / `docker run` | denied |
| reading host answer surfaces (`memory/`, `docs/status/gate0-*`) | denied |
| `git -C <framework repo>` | denied |
| any non-Bash tool (`Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `Task`) | denied |
| chaining / redirect / substitution (`;` `&&` `\|` `>` `$( )` backticks, newline) | denied |
| argument abuse (`../../etc/passwd`, `..`, over-long, extra tokens) | denied |
| verb abuse (`sh`, `exec`, `eval`, `write`, `LS`, `read2`) | denied |
| a look-alike `repo_tool.sh` at another path | denied (resolved-path compare) |
| guard unconfigured (`GATE2_ADAPTER` unset) | denied (fail-closed) |

The adapter path is compared by `os.path.realpath`, so a relative path, symlink
or copy cannot stand in for the sanctioned script.

## What the transcript captures

`GATE2_TRANSCRIPT` (JSONL). Every call produces a `pre_tool_use` event and, when
allowed, a matching `post_tool_use` event:

```
{"event":"pre_tool_use","run_id":…,"request_id":…,"tool":"Bash",
 "command":…,"command_sha256":…,"verb":"read","arg":"NONCE.txt",
 "decision":"allow","reason":…,"session_id":…}
{"event":"post_tool_use","run_id":…,"command_sha256":…,
 "output_sha256":…,"output_len":…}
```

`command_sha256` correlates the two halves, and `adapter-log.txt` independently
records the same call with its own `out_sha256`. That yields the chain a
reviewer can follow from artifacts alone:

```
model request (pre_tool_use)  →  adapter (adapter-log.txt)
      →  container output  →  model (post_tool_use output digest)
```

**Digests, never payloads.** A nonce that exists only inside the container must
not be copied into the transcript, so the guard records hashes and lengths.

## Wiring (producer context ONLY)

Put this in the **producer context's** settings — never the design session's:

```json
{"hooks": {
  "PreToolUse":  [{"hooks":[{"type":"command",
     "command":"python <abs>/gate2_producer_guard.py"}]}],
  "PostToolUse": [{"hooks":[{"type":"command",
     "command":"python <abs>/gate2_producer_posttool.py"}]}]
}}
```

Environment: `GATE2_ADAPTER` (required, absolute path), `GATE2_RUN_ID`,
`GATE2_TRANSCRIPT`.

## Honest limits — read before treating this as sufficient

- **Enforcement is harness-scoped.** It holds for a producer running under a
  harness that honours `PreToolUse` decisions with these hooks configured. It is
  not a kernel or container boundary: an operator who runs the agent *without*
  this configuration gets no protection. Resource admission must therefore
  verify the hook is actually active in each producer context, not assume it.
- **It does not by itself prove a model rather than a human issued a call.** It
  proves the harness saw a tool call from the agent session and what that call
  was. Combined with the session id and the dispatch record it is much stronger
  than the previous self-report, but a determined operator with host access
  remains outside its scope.
- **Not yet exercised against a real producer run.** The 41 checks are unit and
  subprocess level. Its first real use will be the resource-admission dry run.
- The guard mirrors the adapter's verb/arg contract. If the adapter's contract
  ever changes, both must change together or the guard will wrongly deny.

## Defect found by these tests, kept as a note

The first version banned backslash as a shell metacharacter, which denied
**every legitimate call on Windows**, since the adapter path contains
backslashes — a guard so fail-closed it was useless. Backslash is now permitted
(quotes, `$`, backticks, newlines and all chaining characters remain banned, so
it can at most escape a space, which then fails the strict verb/arg patterns). A
Windows-path regression test guards against reintroducing it.
