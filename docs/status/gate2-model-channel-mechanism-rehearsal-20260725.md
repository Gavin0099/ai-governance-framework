# Gate 2 Model-Channel Mechanism Rehearsal — 2026-07-25

Status: **owner-performed rehearsal, reported to and recorded by this design
session. Not independently re-executed by this session's own tool calls in this
turn.** Validates one architectural assumption for Gate 2 (Section G of amendment
v2: the model control plane must sit outside the network-none tool sandbox).
Touches **no** Gate 2 packet, no sanitized baseline, no frozen or signed artifact.
Is **not** a producer or scorer context and does not count toward Gate 2
execution.

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

The model control plane (the owner, standing in for an out-of-band agent) never
entered the container; all commands were issued via `docker exec` from a host
session that retains normal network/API access — the pattern amendment v2
requires: *tools execute inside the offline sandbox; the model channel stays
outside it.*

## Results (as reported)

| Check | Result |
|---|---|
| sandbox reads `NONCE.txt`, writes `/work/result.txt` | PASS, value identical |
| model control plane operates from outside the container | PASS, all commands via `docker exec`, never "entered" |
| container network | unreachable (`wget` timeout, "Network unreachable") |
| framework repo / host mounts (`/d/ai-governance-framework`, `/host_mnt/...`, `/mnt/d/...`, `/c/Users`) | unreachable |
| Docker socket | unreachable |
| root filesystem | read-only (`touch /etc/...` failed) |
| `/work` (tmpfs) | writable, owned by non-root uid 65532 |
| `/input` mount | read-only, write rejected |
| `/input` contents | exactly the two allowlisted files, nothing extra |
| pre-existing 12 containers (meiandraybook-related) | 12 before and after, untouched |
| container cleanup | removed after the test; no persistent host state change |

## What this establishes

The **mechanism** amendment v2 requires — tool execution isolated behind
`--network none`, with the model channel operating from outside via `docker
exec` rather than being installed inside the offline container — is buildable
and was exercised end to end on a throwaway repo. This closes the open question
of *whether* an out-of-band model channel is achievable on this host; it does
not itself supply a Gate 2 producer or scorer.

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
