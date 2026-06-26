# Bookstore-Scraper Diagnosis Disposition - 2026-06-26

Status:

```text
docs-only
diagnosis-disposition
no consumer repair
no tooling behavior change
no governance authority change
no enforcement change
```

## Purpose

This note records the disposition of the 2026-06-26 read-only
Bookstore-Scraper adoption diagnosis.

The diagnosis was useful for framework learning, but it did not authorize or
perform a consumer-repo repair. This note keeps that distinction explicit so the
framework-side evidence is not later misread as Bookstore-Scraper readiness,
repair, or adoption completion.

## Current Repository Truth

Observed from the framework repo after the diagnostic work:

- `governance_tools/adoption_doctor.py` now surfaces
  `hook_config_framework_root` and warns when a repo-owned framework path or
  initialized framework submodule exists but installed hooks point to an
  external framework checkout.
- `docs/governance/operator-prompt-playbook-2026-06-26.md` records the
  prompt-side workflow for bounded modes, claim ceilings, and sub-agent review
  receipts.
- No framework tooling, hook, CI, gate, enforcement, or readiness behavior was
  changed by this disposition note.

Observed from the Bookstore-Scraper diagnosis:

- `adoption_doctor` reported `adoption_class=submodule_consumer`,
  `self_contained=yes`, `runtime_capable=not_checked`,
  `submodule_pin=behind_local_tracking`, and
  `hook_config_framework_root=external`.
- `external_repo_readiness.py` reported `ready=False`, with the main blocking
  state being `PLAN.md` freshness critical.
- The Bookstore-Scraper parent repo had dirty state plus branch divergence
  relative to its local `origin/main`: `ahead 1, behind 25`.
- The local ahead commit was a governance submodule pointer update, while the
  local remote-tracking branch already had later governance/F-7 related commits.
- The working tree included mixed categories of local state: governance
  baseline/PLAN changes, large `exports/latest/tienwei*` product outputs,
  scratch evidence, Playwright MCP artifacts, and a temporary embedded
  framework checkout at `.tmp_ai_governance_latest/`.

All Bookstore-Scraper facts above were observed without fetch, repair, commit,
or push.

## Disposition

The Bookstore-Scraper diagnosis is dispositioned as framework-side learning,
not consumer-repo completion.

Resolved for the framework:

- The earlier adoption-doctor blind spot was exercised and shown to be closed:
  a static `self_contained=yes` report can now coexist with an explicit
  `hook_config_framework_root=external` warning when hooks execute from an
  external framework checkout.
- The operator workflow learned from the session is recorded in the prompt
  playbook, including the main-thread action gate and sub-agent receipt review
  pattern.

Not resolved for Bookstore-Scraper:

- parent repo dirty state;
- parent branch divergence;
- `PLAN.md` freshness and readability;
- framework submodule pin drift;
- hook root pointing to an external framework checkout;
- temporary embedded framework checkout cleanup;
- readiness failure.

## Framework-Side Learning

Two framework-side learnings should carry forward.

First, adoption diagnostics must keep static repository layout separate from
runtime hook execution.

Static evidence can show that a repo-owned framework checkout exists, but hook
configuration may still execute from an external framework checkout. The doctor
must therefore report the hook execution axis explicitly instead of letting
`self_contained=yes` imply runtime self-contained execution.

Second, consumer repair sequencing must start with parent repository ownership
and dirty-state classification.

Bookstore-Scraper had product export changes, governance state changes,
untracked scratch evidence, ignored local artifacts, an embedded temporary
framework checkout, and parent branch divergence at the same time. A direct
PLAN repair, hook repair, submodule update, pull, or rebase would have mixed
consumer product state with governance repair.

## Non-Claims

This note does not claim:

- Bookstore-Scraper is repaired;
- Bookstore-Scraper is ready;
- Bookstore-Scraper was fetched, pulled, rebased, committed, or pushed;
- Bookstore-Scraper hooks were repaired;
- Bookstore-Scraper submodule pin was updated;
- Bookstore-Scraper `PLAN.md` was fixed;
- Bookstore-Scraper temporary artifacts were deleted;
- `adoption_doctor`, readiness, hooks, CI, pre-push, gates, runtime smoke, or
  enforcement behavior changed because of this note;
- sub-agent review receipts are authority.

## Scope Boundaries

In scope:

- record the diagnosis disposition;
- record that no consumer repair was performed;
- record the framework-side learning about external hook-root mismatch and
  parent dirty-state sequencing.

Out of scope:

- editing Bookstore-Scraper;
- editing `governance_tools/**`;
- changing readiness semantics;
- changing hook install behavior;
- changing runtime governance behavior;
- changing memory protocol;
- cleaning, archiving, or deleting Bookstore-Scraper artifacts;
- prescribing a broad Bookstore-Scraper recovery plan.

## Evidence Plan

Validation for this disposition note is limited to:

- scope check: exactly this docs file is added;
- ASCII-only content;
- no trailing whitespace;
- `git diff --check` for this file.

No runtime tests are required because this is a docs-only disposition note.

## Next Planning Effect

Do not continue repairing Bookstore-Scraper from the framework thread unless a
new explicit Bookstore-Scraper `DONE` is provided.

If the framework continues, the next framework-side slice should be a separate
proposal or diagnostic refinement only after a new observed failure requires it.
The current evidence does not require an immediate adoption-doctor, readiness,
hook, CI, or enforcement change.
