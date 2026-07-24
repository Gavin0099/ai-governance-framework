# Gate 2 Isolation Execution Environment — TEMPLATE (Docker-verified, with two findings)

Status: **the isolation MECHANISM is verified in a real container; the template is
NOT yet production-ready** — a real run caught two defects that must be fixed
first (below). No arm was run, no bug solved, no scorer built.

## Correction: Docker IS available

An earlier version of this file, following a review claim, said Docker was
`NOT_FOUND`. That was wrong for this machine. Verified: Docker daemon **29.6.2**
running, `docker ps` works (there are live containers), WSL `docker-desktop`
distro running. So a container-based isolation environment is buildable here, and
was built.

## What was actually verified (real container, answer-safe)

```
docker run --rm --network=none -v <bundle-dir>:/baseline:ro alpine/git \
  sh -c 'git clone -b prepush-baseline /baseline/…​.bundle /work && cd /work && …'
```

Because the host repo is **not mounted** and `--network=none`, the "cannot read"
results are real isolation, not the operator choosing not to look:

- **NEG host repo unreachable:** `/d/ai-governance-framework`,
  `/host_mnt/d/…`, `/mnt/d/…` all absent inside the container. PASS.
- **NEG network off:** `git ls-remote https://github.com` → DNS blocked. PASS.
- **NEG answer analysis absent:** `docs/status/gate0-prepush-*`,
  `docs/governance/gate1-prereg-*amendment*` absent in the baseline clone. PASS.
- **POS baseline:** clone HEAD == `33006f097597f5720a2d01661281d564fb2693ec`,
  3664 files, buggy hook present. PASS.

## Finding 1 (FIXED) — the frozen bundle cloned EMPTY

The frozen procedure used `refs/tmp/prepush-baseline`. `git bundle verify` passed,
but `git clone` produced an **empty** working tree (`refs/tmp/*` is not a branch,
so clone had nothing to check out). Only caught by actually cloning in the
container. Fix (amendment v2 Section A): use a real branch
`git branch -f prepush-baseline 33006f09` and clone with
`git clone -b prepush-baseline`. Re-verified: 3664-file checkout at 33006f09.

## Finding 2 (OPEN) — baseline leaks the experimental FRAME

The negative probe flagged `memory/2026-07-24.md` present in the baseline clone.
Investigated: at 33006f09 it contains **0** pre-push-answer hits (the answer is
NOT leaked) but describes the Engineering Skill Program / Gate 0 / four-arm study.
So do `PLAN.md`, `docs/governance/evidence-backed-engineering-skill-program-*`,
and `artifacts/ab-*`. A producer cloning the full tree would learn it is an A/B
subject — meta-contamination, not answer leakage.

**Required before Gate 2 (frozen denylist, pending):** reduce the producer
checkout to the code under test (`scripts/hooks/`, `governance_tools/`, `tests/`,
supporting modules) + the dispatch packet; denylist `memory/`, `PLAN.md`, the
program/gate docs, and `artifacts/ab-*` / `artifacts/experiments/*`.

## Still resource-gated / owner-gated

- Producer-checkout denylist frozen and applied (Finding 2).
- Pinned validators installed in the run image (network was off for the isolation
  probe; install in a build phase with network, then run network-off).
- Four **answer-blind** producer contexts + two **arm-identity-blind** scorers,
  none being this design session or the author.
- Model build / permissions / tool-call caps stamped.
- A separate explicit owner "start Gate 2" command.

The isolation MECHANISM works; the template is not production-ready until
Finding 2's denylist is frozen and applied and validators are installed.
