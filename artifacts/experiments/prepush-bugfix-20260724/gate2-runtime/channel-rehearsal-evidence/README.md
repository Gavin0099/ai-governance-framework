# Model-Channel Rehearsal — Durable Evidence Bundle (2026-07-25)

Purpose: let a reviewer verify the `model → adapter → container → model` chain
**from repo artifacts alone, without reading the nonce plaintext**. Addresses the
blocking review finding that the rehearsal record held only summaries.

Run `sh verify-chain.sh` (offline) or `sh verify-chain.sh <container>` (also
re-derives digests live, while the rehearsal container exists). Exit 0 = all
checks passed. Both modes passed when this bundle was committed.

## Contents

| File | What it proves |
|---|---|
| `repo_tool.sh` | the actual adapter: verb allowlist (`ls`/`log`/`read`), regex-checked args, no shell string into the container, logs every call |
| `adapter-log.txt` | the two model-driven calls of the run: `verb=ls exit=0`, `verb=read arg=NONCE.txt exit=0 out_bytes=48`, each with an output sha256 |
| `adapter-preflight-log.txt` | hostile inputs rejected: `read ../../etc/passwd` and `sh -c id` both `exit=REJECTED` |
| `container-inspect.json` | full `docker inspect`: `NetworkMode=none`, `ReadonlyRootfs=true`, `CapDrop=[ALL]`, `no-new-privileges`, `User=65532:65532`, `Binds=null` |
| `nonce_file_sha256.txt` | digest of the nonce file as stored (49 bytes, with trailing LF) |
| `reported_sha256.txt` | digest computed from the value the model reported back |
| `verify-chain.sh` | the re-runnable checker |

## Digest reconciliation (the review's specific ask)

Two different digests appear, and the relationship is now **mechanically proven**
rather than asserted:

```
NONCE.txt as stored        = 49 bytes (48 chars + trailing LF)
  sha256                   = 18030d3bffd6a8db80a7f2f28e98364a256a3f22ecf5f816a7cdae251611f61c

NONCE.txt minus trailing LF = 48 bytes   <-- what the adapter returns
  sha256                   = e5e44c3b1493ef6bb87feae8e5b2b539ed19ef0d297faf34a90e3015ba0e299e
                             ^ identical to adapter.log's out_sha256 for `read NONCE.txt`
```

Normalisation rule: **remove exactly one trailing LF**. Verified live in-container
by `verify-chain.sh <container>` (`live (file minus trailing LF) digest == adapter
output digest` → PASS).

`reported_sha256.txt == nonce_file_sha256.txt` (`18030d3b…`), i.e. the value the
model reported re-hashes to the stored file digest — the `SHA_MATCH` result.

## Model follow-up claims, mechanically re-checked in-container

Checked without emitting plaintext:

| Model claim | Verified |
|---|---|
| length 48 | **yes** (`len=48`) |
| 36 digits | **yes** |
| 12 letters | **yes** |
| last six characters `7936E1` | **yes, under case normalisation only** — the stored suffix contains a lowercase `e`; uppercased it equals `7936E1`. An exact-case comparison against `7936E1` returns NO. |

That last row is recorded precisely rather than rounded to "correct": the model's
report was accurate about the characters but presented them uppercased.

## Known gap — not in this bundle

**Raw model request/response transcripts are absent.** The adapter log is a
faithful record of what the model *caused* (verb, arg, exit, output digest) but
it is not the model's own message stream, and this design session was not the
one that dispatched the model. A reviewer can therefore verify:

- that exactly those two tool calls happened, with those outputs;
- that the reported value re-hashes to the file digest;
- that the derived properties are true;

but **cannot** verify from artifacts alone that a model, rather than a human,
issued them. That link rests on the dispatching session's report. Closing it
requires capturing the transcript at dispatch time in a future run.

## Standing limits (unchanged)

- The "fresh model session" was a subagent on the same host/account/harness —
  not an independently provisioned operator context.
- **Adapter exclusivity is not technically enforced.** The subagent retained
  other tools; a direct `docker exec` bypass would not appear in `adapter-log.txt`.
  This must be technically blocked before resource admission, not merely
  prompted and self-reported.
- `alpine/git` was used, so validator pins were **not** re-verified here.
- No Gate 2 packet, no arm, no scoring. This is not 4+2 contexts and does not
  make Gate 2 startable.
