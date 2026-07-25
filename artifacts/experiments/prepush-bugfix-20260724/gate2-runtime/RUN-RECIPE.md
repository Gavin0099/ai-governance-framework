# Gate 2 runtime image — build + verified run recipe

Status: **image built and synthetically preflighted. NO arm has run, no producer
or scorer context exists, and this is NOT a Gate 2 start.**

## Build (network allowed; downloads are hash-verified)

```
docker build -t gate2-runtime:pinned .
```

- Image (content-addressed, this build):
  `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`
- Base: `python:3.12-slim-bookworm`
- ShellCheck 0.10.0 tarball sha256 verified in-build:
  `6c881ab0698e4e6ea235245f22832860544f17ba386442fe7e9d629f8cbedf87`
- Ruff/mypy installed with `pip --require-hashes` from `requirements.lock.txt`
  (ruff 0.6.9, mypy 1.11.2, mypy_extensions 1.0.0, typing_extensions 4.12.2).
- The build fails if any pin drifts (explicit `--version | grep` gate).
- Validators only: **arm packets are not baked in**, so one image cannot leak a
  treatment between arms; each arm mounts its own packet read-only at run time.

## Verified run flags (all preflight checks passed with exactly these)

Dispatch **must** use the immutable image ID, never the mutable `:pinned` tag,
and must record the ID + platform identically for all four arms:

```
IMG=sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168   # linux/amd64
docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /work:rw,nosuid,uid=65532,gid=65532,size=512m \
  --cap-drop ALL --security-opt no-new-privileges \
  "$IMG" <command>
```

Three defects found by preflight/rehearsal, all now encoded above / below:
- `/work` **must** carry `uid=65532,gid=65532`; a bare `--tmpfs /work` is
  root-owned and the non-root user cannot write to it.
- **ruff must be run with `--no-cache`** (or `--cache-dir` on a writable tmpfs)
  whenever its cache target would land on a read-only filesystem — the default
  `.ruff_cache` sits beside the scanned tree, so a read-only source mount makes
  ruff exit 2 with "Failed to initialize cache". That abort is not a validator
  result and must never be recorded as one. (It is the cache location, not
  `--read-only` per se, that triggers it.)
- **Windows / git-bash path-conversion trap:** `docker run -v`, `docker exec`,
  and `docker cp` silently mis-translate Unix container paths (e.g. `/input`)
  into Windows paths (e.g. `C:\Program Files\Git\input`) unless
  `MSYS_NO_PATHCONV=1` is exported first. The symptom — "file not found" inside
  the container — looks exactly like an isolation/mount failure but is a shell
  artifact, not a security-boundary failure. Always set
  `export MSYS_NO_PATHCONV=1` before any `docker run -v` / `docker exec` /
  `docker cp` on this host. Found during the
  [model-channel mechanism rehearsal](../../../status/gate2-model-channel-mechanism-rehearsal-20260725.md).

## Synthetic preflight results (this image, these flags)

| Check | Result |
|---|---|
| identity | `uid=65532 gid=65532` (non-root) |
| shellcheck | `version: 0.10.0` |
| ruff | `ruff 0.6.9` |
| mypy | `mypy 1.11.2 (compiled: yes)` |
| rootfs writable | no (read-only) |
| workspace writable | yes (tmpfs with uid/gid) |
| `/d/ai-governance-framework`, `/host_mnt/...`, `/mnt/d` | unreachable |
| `/var/run/docker.sock` | unreachable |
| network (`git ls-remote https://github.com`) | blocked |
| synthetic sanitized repo | `git init` + commit OK, 7 objects / 2 files |
| validators on synthetic code | shellcheck / ruff / mypy each exit 0 |
| pre-existing containers | 12 before and after (none stopped or removed) |

## Explicitly NOT done

- No framework repo, raw bundle, or Docker socket was ever mounted.
- No real arm, no producer context, no scorer context, no scoring.
- The real sanitized repo (tree `36c346fa…`) was **not** copied in; the preflight
  used a throwaway synthetic repo only.

## Still required before Gate 2 can start

1. Four **answer-blind** producer contexts (A: sanitized repo + dispatch;
   B: +Skill packet; C: +Governance packet; D: +validator pins/treatment-time
   feedback), each an independent filesystem + conversation, run in order
   [D, C, A, B].
2. Two **arm-identity-blind** scorer contexts receiving only the anonymized
   packet/receipt/marker, the handoff verifier, and the frozen rubric.
3. An **out-of-band model control plane**: `--network none` also cuts the model
   API, so the agent's tools must be inside the offline sandbox while the model
   channel stays outside it (a managed runner). A CLI agent installed *inside*
   this network-less container cannot run.
4. Identical model build / non-treatment permissions / 60 tool calls / 30 min,
   stamped at dispatch.
5. A separate, explicit owner "start Gate 2" command.

Neither this design session nor the author may act as a producer or scorer.
