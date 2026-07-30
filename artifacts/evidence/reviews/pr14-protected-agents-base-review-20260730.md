# PR #14 Protected `AGENTS.base.md` Review

- Review date: 2026-07-30
- Review status: APPROVED for canonical baseline acceptance
- Reviewed merge commit: `9a78e76a5b4d379610f9248e312a0d4b67eb8008`
- First parent: `c25110f46c8826ce0afbe9b96a0dcef62d034657`
- Pull request: `#14` (`codex/single-pr-closeout-policy`)
- Protected surface: `AGENTS.base.md`

## Exact Change Reviewed

The protected-file delta adds one bounded rule: when an implementation needs a
canonical closeout companion, the implementation and closeout remain separate
commits but use one branch and one pull request by default. A successful merge,
push, or remote verification is delivery evidence and does not independently
create another memory commit or pull request. A follow-up slice requires a new
defect, omitted required governance state, or explicit owner authorization.

## Authority And Consistency

- The merged wording is a faithful compact projection of
  `governance/MEMORY_PROTOCOL.md` under `Single-PR Closeout Contract`.
- The same projection was applied to
  `baselines/repo-min/AGENTS.base.md` in the reviewed merge.
- The merge itself records owner acceptance into `main`; this review records
  why the protected hash may be refreshed.

## Findings

No blocking or warning finding was identified in the exact
`c25110f4..9a78e76a` protected-file delta.

The change does not alter the canonical writer, receipt schema, runtime hooks,
promotion rules, gate policy, CI enforcement, or branch protection.

## Claim Boundary

This artifact approves only the reviewed PR #14 protected-file delta for
canonical baseline acceptance. It does not make baseline refresh a general
authorization mechanism. A refreshed hash proves consistency with the reviewed
state; it does not prove that future protected-file changes are authorized.

## Reproducible Evidence

```text
git show -s --format="commit=%H%nparents=%P%nsubject=%s%nbody=%b" 9a78e76a
git diff c25110f4 9a78e76a -- AGENTS.base.md
git diff --name-status c25110f4 9a78e76a
```
