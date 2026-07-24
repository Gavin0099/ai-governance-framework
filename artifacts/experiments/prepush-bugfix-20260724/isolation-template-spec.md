# Gate 2 Isolation Execution Environment — TEMPLATE (Docker-verified, with two findings)

Status: **the isolation MECHANISM is verified in a real container; the template is
NOT yet production-ready** — a real run caught two defects that must be fixed
first (below). No arm was run, no bug solved, no scorer built.

## Docker availability is environment-specific (not a "who checked wrong")

Both observations are true and consistent — it is an environment difference:
- In this **Claude / host session**, Docker **is** available: daemon 29.6.2
  running, `docker ps` works (live containers), WSL `docker-desktop` distro
  running. A container isolation environment is buildable here, and was built.
- In a **CodexSandboxOffline** session, `docker` is **NOT_FOUND** on PATH.

So the container evidence below is valid for the host session; it does not claim
Docker is available in every session.

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

Epistemic note: this is not "execution is the only cure". Structural checks
(`git bundle verify`) passing does not prove the behavioral path works, so for an
**operational** claim, end-to-end execution is a necessary *stronger* form of
evidence — but it is still not sufficient on its own: it must use representative
data/conditions and an independent oracle. Here the "oracle" was the concrete
expected outcome (a non-empty checkout at the exact baseline sha).

## Finding 2 (RESOLVED via allowlist export — a denylist was insufficient)

The negative probe flagged `memory/2026-07-24.md` present in the baseline clone.
Investigated: at 33006f09 it contains **0** pre-push-answer hits (the answer is
NOT leaked) but describes the four-arm study frame; so do `PLAN.md`, the program
docs, and `artifacts/ab-*`.

A checkout **denylist** does not fix this: a producer holding the raw bundle /
`.git` can still `git show HEAD:memory/2026-07-24.md` or `git ls-tree -r HEAD`
even under a sparse checkout. Working-tree invisibility ≠ technical
unreachability.

**Correct fix (built + verified):** an **allowlist export into a fresh git object
database** — see `sanitized-baseline-manifest-20260724.md`. The producer receives
a repo whose object DB contains ONLY the allowlisted code (11 objects, 4 files);
`git show HEAD:memory/…` genuinely fails because those blobs are not in the DB.
Negatively verified by filesystem, `git show`, and
`git rev-list --objects --all` (0 meta objects). The producer never receives the
raw bundle.

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
