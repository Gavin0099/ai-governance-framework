# Gate 2 Model-Channel Rehearsal (model → adapter → container → model) — 2026-07-25

Status: **rehearsal performed by a separate harness session and reported here.**
This design session did **not** run the three-stage test; it independently
re-verified the container's isolation properties and the nonce's hash while the
rehearsal container was still alive (see "Independent verification" below), and
deliberately never read the nonce plaintext.

This closes the model-side link that the
[host-to-container bridge rehearsal](../../../status/gate2-model-channel-mechanism-rehearsal-20260725.md)
was correctly found *not* to cover. It is **not** a Gate 2 arm, **not** a
producer or scorer context, and does **not** make Gate 2 startable.

## Architecture under test

```
model session (has network)
      → managed tool adapter (host side, verb-allowlisted)
          → container (--network none)
              → result
      → model uses the result
```

The previous rehearsal exercised only the middle link with a human operator.
This one puts a real model session at both ends.

## Environment (fresh, throwaway)

- New dummy git repo: `README.md` + `NONCE.txt`, commit `3684125`.
- Repo and nonce exist **only in container tmpfs**; the value was never written
  to host disk, and the dispatching session did not read the plaintext.
- Container: `alpine/git` — deliberately **not** `gate2-runtime:pinned`, so this
  does not re-verify validator pins.
- Flags: `--network none --read-only --cap-drop ALL --security-opt
  no-new-privileges --user 65532:65532`, with `/work` and `/tmp` as tmpfs.

## Managed adapter (not free-form command execution)

`repo_tool.sh` accepts exactly three verbs — `ls`, `log`, `read <file>` —
with regex-allowlisted arguments. It does **not** pass a shell string into the
container, and it logs every call.

Pre-flight hostile inputs, both rejected with exit 2:
- `read ../../etc/passwd` (path traversal)
- `sh -c id` (verb injection)

## Three-stage evidence (as reported)

1. **Model tool request** — adapter log, two entries:
   `verb=ls exit=0` and `verb=read arg=NONCE.txt exit=0 out_bytes=48`.
2. **Container execution / output** — executed inside the network-none container
   as uid 65532; output sha256 `e5e44c3b…`.
3. **Model uses the result** — the fresh session reported the nonce as 48
   characters and independently derived: length 48, last six characters
   uppercase `7936E1`, 36 digits / 12 letters.

Mechanical check performed without the truth value entering the dispatching
session's context: in-container comparison returned `NONCE_MATCH`, the reported
value's sha256 matched the pre-stored file hash (`SHA_MATCH`), and all three
derived properties were correct.

## Independent verification by this design session

Performed against the live container via `docker inspect` / `docker exec`,
without reading the nonce plaintext:

| Property | Measured |
|---|---|
| `NetworkMode` | `none` |
| `ReadonlyRootfs` | `true` |
| `CapDrop` | `[ALL]` |
| `SecurityOpt` | `[no-new-privileges]` |
| `User` | `65532:65532` |
| `Binds` | `[]` — **no host bind mounts at all** |
| `Mounts` | only `volume:/git` (image-provided) |
| network reachability | `wget` did not succeed |
| `NONCE.txt` present in tmpfs | yes, 49 bytes (48 chars + newline) |
| `NONCE.txt` sha256 | `18030d3bffd6a8db80a7f2f28e98364a256a3f22ecf5f816a7cdae251611f61c` |

**Exit-code discrepancy, recorded rather than smoothed over:** the harness
reported `wget_rc=1`; this session measured `143`. 143 is `128+15` (SIGTERM),
i.e. `timeout 5` killed a *hanging* wget, whereas `1` is wget's own failure
return. Both establish "no network egress", but by different mechanisms — the
difference is the invocation wrapper, not the isolation result. (Given this
work's repeated exit-code-masking problems, the precise value is worth keeping.)

Container count: 12 pre-existing + 1 rehearsal = 13. The 12 pre-existing
containers were untouched.

## Cannot claim

- **The "fresh model session" was a subagent dispatched by the harness session**
  — same host, same account, same harness. Its answer-blindness rests on prompt
  isolation plus the nonce being obtainable only inside the container. It is
  **not** an independently provisioned operator context, and does not satisfy
  the Gate 2 requirement for producer/scorer contexts that are neither the
  design session nor the author.
- **Adapter exclusivity is a prompt constraint corroborated by logs, not a
  technical guarantee.** The subagent was not technically stripped of other
  tools; had it bypassed the adapter with a direct `docker exec`, the adapter
  log would not record it. Log and self-report are consistent, which is
  corroboration, not enforcement.
- `alpine/git` was used, so validator pins were **not** re-verified (that is the
  separate, already-recorded post-sign preflight).
- No Gate 2 packet was used, no arm ran, nothing was scored.
- This does not constitute the 4 producer + 2 scorer contexts, and does not make
  Gate 2 startable.
- This session did not itself run the three-stage test; it verified the
  container properties and the nonce hash only.

## What this does establish

The model → adapter → container → model loop is **mechanically viable** on this
host: a model session with network access can drive tool execution that lands
inside a network-none container and correctly consume a value that exists only
there. The remaining gaps for Gate 2 are about **provisioning and independence**
(separately provisioned answer-blind contexts, technically-enforced adapter
exclusivity), not about whether the channel shape works.
