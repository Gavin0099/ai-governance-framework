# Post-Sign Image Preflight — 2026-07-25

Status: **DONE.** Verifies the pinned runtime image and the LF-clean sanitized
baseline against the owner-signed, canonically-promoted candidate packets.
Scope is verification only: **no producer or scorer context was created, no
arm ran, Gate 2 was not started.**

## What this checks

That nothing regressed between the independent review (which approved the
corrected hashes) and canonical promotion (which pointed the manifest at them):
same image, same baseline reconstruction procedure, same exact validator
commands, re-measured directly.

## Image identity (unchanged since the original preflight)

```
sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168
```

## Baseline reconstruction (canonical procedure, re-run)

- `git -c core.autocrlf=false archive` + `git -c core.autocrlf=false init` on
  the four allowlisted files from `33006f09`.
- Resulting tree: `36c346fa951a24cbf914ef04469aac5cb5fd8b86` — **matches**.
- LF-only check (`grep -rlU $'\r'`): **no CRLF found**.

## Canonical candidate packets (re-hashed, unchanged since signature)

| File | sha256 | Matches signed value |
|---|---|---|
| `candidate/validator-pins-v2.md` | `877896c7672b1f47383e19ab00a38049344634c12c328a205a1651c6da4bf46d` | yes |
| `candidate/validator-expectation-DESIGNER-ONLY-v2.md` | `61e1e52743e78ad9d38bd50e311978f5d49f513d617a48fd9a9b5a0901d02092` | yes |

## Isolation probes (same run flags as the original preflight)

| Check | Result |
|---|---|
| identity | `uid=65532 gid=65532` |
| `/d/ai-governance-framework`, `/host_mnt/...`, `/mnt/d` | unreachable |
| `/var/run/docker.sock` | unreachable |
| network (`git ls-remote https://github.com`) | blocked |
| rootfs writable | no (read-only) |
| workspace (`/work` tmpfs, uid/gid pinned) writable | yes |
| pre-existing containers | 12 before and after (untouched) |

## Validator versions (in-container)

`shellcheck 0.10.0`, `ruff 0.6.9`, `mypy 1.11.2` — all confirmed.

## Exact commands, direct exit-code measurement (no pipe / no substitution)

| Command | Result | Exit | Matches signed expectation v2 |
|---|---|---|---|
| `shellcheck --shell=bash --severity=style scripts/hooks/pre-push` | `SC1090` only | **1** | yes |
| `ruff check --no-cache --line-length 100 --target-version py312 --select E,F,W,I,B governance_tools/version_bump_guard.py` | `E501`, `I001` | **1** | yes |
| `mypy --no-incremental --python-version 3.12 --warn-unused-ignores --warn-return-any --no-implicit-optional governance_tools/version_bump_guard.py` | "Success: no issues found in 1 source file" | **0** | yes |

**No regression found.** The signed, canonically-promoted candidate packets
still describe reality exactly.

## Explicitly NOT done in this slice

- No producer context, no scorer context.
- No out-of-band model control plane.
- No arm run, no scoring.
- No Gate 2 start command.

## Still required before Gate 2

Four answer-blind producer contexts, two arm-identity-blind scorer contexts, an
out-of-band model control plane, stamped model/permission constants, and a
separate explicit owner "start Gate 2" command. Neither this design session nor
the author may act as producer or scorer.
