# Gate 2 Host-to-Container Tool-Control Bridge Rehearsal — 2026-07-25

> **Scope correction (2026-07-25, post-review).** This document was first titled
> a "model-channel mechanism rehearsal" and claimed it closed the out-of-band
> model-channel question. That was an over-claim and is withdrawn. **No model
> session and no model tool adapter participated** — a human issued `docker exec`
> from the host where an agent's tool-call loop would be. What was actually
> exercised is a **host-to-container tool-control bridge** plus the container's
> isolation properties. The filename is kept for link stability; the title and
> claims are corrected.

Status: **owner-performed rehearsal, reported to and recorded by this design
session. Not independently re-executed by this session's own tool calls.**
Exercises the *container-side half* of the Gate 2 architecture (amendment v2
Section G: tool execution isolated behind `--network none`). It does **not**
exercise the model-side half. Touches **no** Gate 2 packet, no sanitized
baseline, no frozen or signed artifact. Is **not** a producer or scorer context
and does not count toward Gate 2 execution.

## What was tested

A throwaway synthetic repo (`README.md` + `NONCE.txt` containing a random value
`258502d6…`) inside a generic `alpine:3.20` container — deliberately **not**
`gate2-runtime:pinned` — with the exact flags amendment v2 / RUN-RECIPE require:

```
--network none --read-only \
--tmpfs /tmp:rw,noexec,nosuid,size=64m \
--tmpfs /work:rw,nosuid,uid=65532,gid=65532,size=512m \
--cap-drop ALL --security-opt no-new-privileges
```

A **human operator** (the owner) issued every command via `docker exec` from a
host session that retains normal network/API access, and never entered the
container. This occupies the position an agent's tool-call loop would occupy,
but it **is not** such a loop: no model session was in the path, and no tool
adapter translated a model request into a container execution.

## Results (as reported)

| Check | Result |
|---|---|
| sandbox reads `NONCE.txt`, writes `/work/result.txt` | PASS, value identical |
| host-side operator drives the container from outside | PASS, all commands via `docker exec`, never "entered" (human operator, **not** a model session) |
| container network | unreachable (`wget` timeout, "Network unreachable") |
| framework repo / host mounts (`/d/ai-governance-framework`, `/host_mnt/...`, `/mnt/d/...`, `/c/Users`) | unreachable |
| Docker socket | unreachable |
| root filesystem | read-only (`touch /etc/...` failed) |
| `/work` (tmpfs) | writable, owned by non-root uid 65532 |
| `/input` mount | read-only, write rejected |
| `/input` contents | exactly the two allowlisted files, nothing extra |
| pre-existing 12 containers (meiandraybook-related) | 12 before and after, untouched |
| container cleanup | removed after the test; no persistent host state change |

## What this establishes — and what it does not

**Establishes:** a host-to-container tool-control bridge works on this host. A
process outside the sandbox can drive commands into a `--network none`,
`--read-only`, non-root container, get correct results back (the nonce
round-tripped), and the container's isolation properties hold under exactly the
amendment-v2 flag set.

**Does NOT establish:** that the out-of-band *model* channel works. The
architecture Gate 2 needs is
`model session (network) → tool adapter → container (no network) → result → model`.
This rehearsal exercised only the middle link, with a human where the model and
its adapter belong. Nothing here shows that a real agent's tool loop can drive
this container, nor that a managed tool adapter exists for it.

**Remaining bounded validation** (still a mechanism rehearsal, still on a dummy
repo, still not a Gate 2 arm): a fresh real model session *outside* the sandbox,
a managed tool adapter that executes *only* inside the `--network none`
container, capturing (a) the model's tool request, (b) the container execution
and its output, and (c) a subsequent model response that correctly uses a nonce
returned by the tool. Must not use a Gate 2 packet and must not count as an arm.

## Operational finding worth keeping — Windows path-conversion trap

On this Windows + git-bash host, `docker run -v`, `docker exec`, and `docker cp`
silently mis-translate Unix-style container paths (e.g. `/input`) into Windows
paths (e.g. `C:\Program Files\Git\input`) unless `MSYS_NO_PATHCONV=1` is set.
The failure mode — "file not found" inside the container — looks exactly like an
isolation or mount failure, but is a shell path-rewriting artifact, not a
security-boundary failure. Anyone running these images from a Windows git-bash
shell will hit this. Recorded as a runbook note in
[gate2-runtime/RUN-RECIPE.md](../../artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/RUN-RECIPE.md).

## Cannot claim

- **That a real model session participated, or that a managed model tool adapter
  was exercised** — a human issued the commands.
- **That the out-of-band model-to-tool-to-model architecture is closed.** Only
  the container-side link was exercised.
- That this can be described as an end-to-end model-channel rehearsal.
- That this session independently re-executed or verified the nonce test itself
  (it is recorded as reported by the owner, who performed it).
- That the pinned `gate2-runtime:pinned` image or the validator pins were
  re-tested here (a generic `alpine:3.20` was used; validator-pin verification
  is the separate post-sign preflight already recorded).
- That any Gate 2 producer or scorer context now exists.
- That Gate 2 may start, that any arm has run, or that the Bug Fix Skill or
  validator treatment is effective.
- That four same-source sanitized producer repos, the two blind scorer contexts,
  or a real Gate 2 dispatch have been built — all remain outstanding.
