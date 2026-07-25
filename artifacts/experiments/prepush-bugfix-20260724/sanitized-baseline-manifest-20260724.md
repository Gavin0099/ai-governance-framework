# Sanitized Producer Baseline — allowlist export (Finding 2 resolution)

Status: **built + negatively verified.** This replaces the raw-bundle approach for
producer contexts. A checkout denylist was insufficient: a producer holding the
raw bundle / `.git` could still run `git show HEAD:memory/2026-07-24.md` or
`git ls-tree -r HEAD` to read meta-artifacts even under a sparse checkout —
working-tree invisibility is not technical unreachability. The fix is an
**allowlist export into a fresh git object database** that never contains the
meta blobs at all.

## Construction (reproducible — MUST pin line endings)

> **CORRECTION 2026-07-25 (pending owner re-sign).** The original command was not
> hermetic: its result depends on the host's `core.autocrlf` / gitattributes.
> Worse, on a `core.autocrlf=true` host the export produces **CRLF working files
> while `git add` normalizes the blobs back to LF — so the tree hash still equals
> `36c346fa…` and the frozen invariant PASSES, yet the files a validator actually
> reads are CRLF.** Verified: ShellCheck then emits **80+ spurious `SC1017`
> ("literal carriage return") errors**, which would silently corrupt the Arm D
> treatment. The tree hash alone therefore does NOT protect the run.

```
git -c core.autocrlf=false archive --format=tar 33006f09 \
    scripts/hooks/pre-push scripts/lib \
    governance_tools/version_bump_guard.py tests/test_version_bump_guard.py \
  | tar -x -C <sanitized-dir>
cd <sanitized-dir> \
  && git -c core.autocrlf=false init && git config core.autocrlf false \
  && git add -A \
  && git commit -m "sanitized baseline export from 33006f097597 (allowlist only)"
```

**Mandatory post-export check (in addition to the tree hash):** every exported
file must be LF-only in the working tree, e.g.

```
! grep -rlU $'\r' <sanitized-dir> --exclude-dir=.git    # must find nothing
```

## Frozen record

- `source_baseline_commit` = `33006f097597f5720a2d01661281d564fb2693ec`
- Allowlist (the only paths a producer receives):

| path | blob sha1 @ 33006f09 |
|---|---|
| governance_tools/version_bump_guard.py | 7d2a51924a7567ce5da336653480c9964806ffa5 |
| scripts/hooks/pre-push | 5b388f1aa83bd9b2027d1144d981b99979c51120 |
| scripts/lib/python.sh | 6213400218e4a8b8813866bd9e6f32ac84e960a3 |
| tests/test_version_bump_guard.py | 32a5731271859be1a744444518c3b8b4393e4778 |

- `sanitized_tree` = `36c346fa951a24cbf914ef04469aac5cb5fd8b86`
- `sanitized_commit` = `048b0a541a57fb52c3d8942daff480d7ca1d82fd` (design-env; the
  commit sha varies with author/date, so the authoritative invariant is the
  sanitized_tree + the allowlist blob hashes, not the commit sha)
- Total objects in the sanitized repo: **11** (4 blobs + trees + 1 commit).
- The producer receives THIS repo (fresh `.git`), never the baseline bundle.

## Negative verification (must all hold)

Explicitly excluded, and confirmed unreachable by filesystem, `git show`, AND
`git rev-list --objects --all`:
- `memory/2026-07-24.md` — FS absent, `git show HEAD:` unreachable, 0 rev-list objects.
- `PLAN.md` — FS absent, `git show HEAD:` unreachable, 0 rev-list objects.
- `docs/governance/evidence-backed-engineering-skill-program-*` — unreachable.
- `docs/status/gate0-prepush-*` and the amendments — unreachable.
- `git rev-list --objects --all | grep -icE 'memory/|PLAN\.md|gate0|evidence-backed|experiment'`
  → **0**.

## Positive

- `scripts/hooks/pre-push` contains the buggy `--head-ref HEAD` (bug intact).
- `governance_tools/version_bump_guard.py` present (the code under test).

## Caveat

This resolves the *frame-leak* isolation gap for the producer's git surface. It
does not by itself constitute the full Gate 2 environment: the sanitized repo
must still be placed in an execution environment with no network and no host-repo
mount, the pinned validators installed, and the dispatch packet added, before any
answer-blind producer runs. No arm was run; the bug was not solved.
