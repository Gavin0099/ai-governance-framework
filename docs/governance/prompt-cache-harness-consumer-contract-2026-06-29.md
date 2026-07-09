# Prompt-Cache Harness Consumer Contract Proposal - 2026-06-29

> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.

Status: PENDING
Scope: docs-only harness consumer contract proposal
Runtime behavior change: no
Tooling behavior change: no
Test behavior change: no
CI behavior change: no
Hook / pre-push / gate behavior change: no
Prompt-cache implementation: no
Enforcement change: no

## Problem

The repository now has a read-only `AUTHORITY_MANIFEST v1` candidate generator.
That generator can report authority-file membership, hash sources, drift status,
and base/head authority-change invalidation signals.

What is still missing is a real consumer boundary.

Without a named consumer, `AUTHORITY_MANIFEST` remains useful as reviewer-facing
detection/accountability evidence, but it does not yet explain how a prompt-cache
harness would use the signal. If the next step jumps directly to release prep,
receipt tooling, cache behavior claims, or enforcement, the repository risks
inflating a repo-side manifest into a prompt-cache implementation.

This proposal defines the first real harness consumer in a narrow, reviewable
way.

## Current Repository Truth

Observed in the current repository before this proposal:

- `governance_tools/authority_manifest.py` exists and generates
  `AUTHORITY_MANIFEST v1` as a read-only candidate artifact.
- `tests/test_authority_manifest.py` exists and covers baseline-derived
  authority files, unchanged and changed base/head invalidation, stable manifest
  hash behavior, JSON serialization, and CLI JSON output.
- `python -B -m governance_tools.authority_manifest --project-root . --base-ref
  HEAD~1 --head-ref HEAD --format human` reports:
  - `schema=AUTHORITY_MANIFEST v1`
  - `status=candidate`
  - `authority_changed_between_refs=False`
  - `governance_drift_checker.severity=ok`
  - `repo_enforces_prompt_cache=False`
  - claim ceiling: detection/accountability only, not prompt-cache enforcement.
- `python -B -m governance_tools.governance_drift_checker --repo . --format
  human` reports `ok=True`, `severity=ok`, and all listed checks PASS.
- `CHANGELOG.md` has an Unreleased entry for the candidate generator.
- `PLAN.md` still contains planning text that says the generator is a candidate
  implementation tranche. That planning text is now stale relative to the
  implemented generator, but this proposal does not refresh PLAN.
- The existing cache-aware docs repeatedly state the key boundary:
  prompt-cache runtime behavior is harness/provider controlled; the repository
  can provide detection/accountability surfaces only.

No current repository evidence shows:

- a harness reads `AUTHORITY_MANIFEST`;
- a prompt cache is enabled, controlled, or measured by this repository;
- cache hit/miss is observed;
- invalidation is enforced by hooks, CI, runtime gates, or a provider;
- release `v1.3.0` is prepared or published.

## Target Outcome

Define the first real prompt-cache harness consumer as:

```text
AUTHORITY_MANIFEST preflight consumer
```

This consumer is a no-write session-harness preflight step. It reads an
`AUTHORITY_MANIFEST v1` candidate before a harness decides whether cached
authority context is safe to reuse.

The consumer does not implement prompt caching. It classifies whether authority
context reuse would be:

- `reuse_candidate`
- `reload_required`
- `cache_unsafe`
- `not_checked`

The output is a receipt for main-thread inspection, not an authority source and
not an automatic gate.

## Scope

This docs-only proposal adds:

- `docs/governance/prompt-cache-harness-consumer-contract-2026-06-29.md`

Future implementation, if approved separately, may add one no-write consumer
simulation and one focused test file. That future tranche is not implemented by
this proposal.

## Non-Goals

This proposal does not:

- implement prompt caching;
- enable or configure provider cache behavior;
- observe cache hit/miss;
- add cache pricing or token accounting;
- add runtime hooks;
- add CI, pre-push, gate, or enforcement wiring;
- change `governance_tools/authority_manifest.py`;
- change `governance_tools/governance_drift_checker.py`;
- change `.governance/baseline.yaml`;
- change memory writer behavior;
- change AGENTS.md, governance routers, or prompt loading policy;
- prepare or publish release `v1.3.0`;
- authorize cross-repo writes;
- claim automatic agent compliance.

## Affected Surfaces

This proposal affects only one docs surface:

- `docs/governance/prompt-cache-harness-consumer-contract-2026-06-29.md`

Future implementation surfaces, if separately authorized, should be limited to:

- one new no-write consumer/simulation module under `governance_tools/`;
- one focused test file under `tests/`;
- optional docs wording only if needed to preserve claim ceilings.

Any future change to runtime hooks, CI, pre-push, gate policy, prompt-cache
provider integration, or release surfaces is out of scope and needs its own
reviewed DONE.

## Consumer Identity

Name:

```text
AUTHORITY_MANIFEST_PREFLIGHT_CONSUMER v0.1
```

Role:

```text
Read a candidate AUTHORITY_MANIFEST and emit a no-write reuse decision receipt.
```

Authority class:

```text
derived evidence consumer
```

The consumer is not a canonical authority source. It consumes authority evidence
from `AUTHORITY_MANIFEST`, which itself derives from `.governance/baseline.yaml`
and `governance_drift_checker.py`.

## When The Harness Reads It

The first supported read point is session preflight:

```text
session start or thread resume, before reusing cached authority context
```

Optional later read points, not part of the first implementation tranche:

- before compaction handoff;
- before review packet handoff;
- before cross-thread delegation;
- before release/handoff bundle generation.

The first tranche should not integrate with all read points. It should prove one
preflight path first.

## Input Contract

The consumer input should be:

```text
project_root:
base_ref:
head_ref:
manifest_json:
expected_manifest_schema: AUTHORITY_MANIFEST v1
```

The manifest may be generated immediately before the consumer runs, or supplied
as a JSON file. Supplying a JSON file must still be no-write from the consumer's
perspective.

Minimum required manifest fields:

- `schema`
- `status`
- `base_ref`
- `head_ref`
- `authority_files`
- `checks.governance_drift_checker.severity`
- `invalidation.authority_changed_between_refs`
- `repo_enforces_prompt_cache`
- `claim_ceiling`
- `non_claims`

## Output Receipt

The consumer should emit a receipt shaped like:

```text
AUTHORITY_MANIFEST_PREFLIGHT_RECEIPT v0.1
repo:
base_ref:
head_ref:
manifest_schema:
manifest_status:
manifest_hash:
authority_changed_between_refs:
governance_drift_severity:
repo_enforces_prompt_cache:
decision:
decision_reason:
required_action:
cache_behavior_claim:
runtime_enforcement_claim:
evidence_refs:
not_claimed:
```

Decision values:

| Decision | Meaning |
| --- | --- |
| `reuse_candidate` | Manifest is readable, candidate status is understood, authority did not change between refs, and drift severity is acceptable. A harness may consider cached authority context reusable, but the repo does not prove cache reuse occurred. |
| `reload_required` | Authority changed between refs or the manifest reports a condition that should invalidate cached authority context. The harness should reload authority files before relying on cached context. |
| `cache_unsafe` | Manifest is missing, malformed, wrong schema, says `repo_enforces_prompt_cache=true`, or drift severity is critical. The harness should not treat cache reuse as safe. |
| `not_checked` | Consumer did not run or could not evaluate the manifest. No cache reuse claim is supported. |

Required action values:

- `none`
- `reload_authority_files`
- `discard_cached_authority_context`
- `manual_review`
- `not_applicable`

The receipt must include:

```text
cache_behavior_claim: not_observed
runtime_enforcement_claim: not_enforced_by_repo
```

until a separate harness/provider integration supplies real cache evidence.

## Decision Rules

Minimum rule set:

1. If manifest is unreadable or schema is not `AUTHORITY_MANIFEST v1`:
   - decision: `cache_unsafe`
   - required_action: `manual_review`

2. If `repo_enforces_prompt_cache` is not `false`:
   - decision: `cache_unsafe`
   - required_action: `manual_review`

3. If `checks.governance_drift_checker.severity` is `critical`:
   - decision: `cache_unsafe`
   - required_action: `manual_review`

4. If `invalidation.authority_changed_between_refs` is `true`:
   - decision: `reload_required`
   - required_action: `reload_authority_files`

5. If the manifest is readable, schema is valid, drift severity is `ok` or
   warning-class, and authority did not change between refs:
   - decision: `reuse_candidate`
   - required_action: `none`

6. If the consumer cannot determine one of the required fields:
   - decision: `not_checked`
   - required_action: `manual_review`

These rules are intentionally conservative. They classify prompt-cache reuse
eligibility; they do not perform reuse.

## Boundary And API Considerations

### Main Thread Gate

The receipt is evidence to inspect. It is not permission to:

- push;
- commit;
- write memory;
- edit another repo;
- perform destructive actions;
- claim prompt-cache behavior;
- skip review.

Main thread retains action authority. User authorization remains required for
push, cross-repo writes, destructive operations, release publish, or memory
state changes.

### Harness Boundary

The repository may propose the preflight consumer, but the real harness must
decide whether and how to:

- load cached authority context;
- discard cached authority context;
- reload authority files;
- report provider cache hit/miss;
- preserve cache evidence across compaction.

Repo-side tooling must not claim those harness actions occurred unless the
harness emits evidence.

### Provider Boundary

Provider prompt-cache behavior remains outside repo control. The consumer must
not infer:

- cache hit;
- cache miss;
- cache TTL;
- cache read/write cost;
- cache key;
- provider-specific behavior.

## Failure Paths Or Risk Points

1. Consumer becomes fake enforcement
   - Risk: `reuse_candidate` is misread as cache reuse or permission to skip
     reload.
   - Boundary: receipt is evidence only; main/harness must act separately.

2. Manifest becomes a parallel authority source
   - Risk: preflight consumer trusts manifest as canonical authority.
   - Boundary: manifest remains derived from baseline/drift truth.

3. Cache behavior overclaim
   - Risk: repo claims cache hit/miss without provider or harness evidence.
   - Boundary: `cache_behavior_claim` remains `not_observed`.

4. Review bypass
   - Risk: a clean preflight receipt is treated as review approval.
   - Boundary: review receipts and preflight receipts are separate.

5. Release inflation
   - Risk: this proposal is treated as v1.3.0 readiness.
   - Boundary: release prep remains a separate docs/release slice.

6. Speculative expansion
   - Risk: adding compaction, tool-denial, mode receipts, CI, or runtime hooks
     before the first consumer is proven.
   - Boundary: first tranche is one no-write preflight simulation only.

## Evidence Plan

For this docs-only proposal:

- `git diff --check -- docs/governance/prompt-cache-harness-consumer-contract-2026-06-29.md`
- ASCII/trailing-whitespace check for this file
- scope check showing only this file changed
- read-only review focused on:
  - no prompt-cache implementation claim;
  - receipt is evidence, not authority;
  - no enforcement/gate behavior;
  - consumer has one narrow preflight read point.

For a future implementation tranche:

- focused unit test for unreadable/malformed manifest -> `cache_unsafe`;
- focused unit test for wrong schema -> `cache_unsafe`;
- focused unit test for `authority_changed_between_refs=true` ->
  `reload_required`;
- focused unit test for unchanged/ok manifest -> `reuse_candidate`;
- focused unit test that `cache_behavior_claim=not_observed`;
- CLI smoke with explicit manifest input or generated manifest input;
- no-write assertion: no artifact, memory, baseline, hook, CI, or repo mutation.

## Implementation Tranche Recommendation

If this proposal is reviewed and accepted, the next implementation tranche
should be:

```text
Implement a no-write AUTHORITY_MANIFEST preflight consumer simulation that reads
AUTHORITY_MANIFEST JSON and emits AUTHORITY_MANIFEST_PREFLIGHT_RECEIPT v0.1.
```

Recommended allowed files for that future tranche:

- `governance_tools/authority_manifest_preflight.py`
- `tests/test_authority_manifest_preflight.py`

Forbidden in that future tranche unless separately authorized:

- prompt-cache provider integration;
- cache hit/miss tracking;
- runtime hook wiring;
- CI/pre-push/gate wiring;
- release prep;
- baseline rewrite;
- memory behavior change;
- cross-repo write behavior;
- compaction or tool-denial receipt tooling.

Review level:

```text
Claude/human high-rigor review is recommended before implementation, because
this contract defines the boundary between repo-side evidence and harness-side
prompt-cache behavior.
```

For this docs-only proposal alone, a normal read-only sub-agent review is
sufficient before commit. Claude/human review becomes more valuable before the
implementation tranche or any release claim.

## Claim Ceiling

This proposal may claim only:

- the first prompt-cache harness consumer boundary is proposed;
- the proposed consumer is no-write and preflight-only;
- the proposed receipt is evidence to inspect, not authority;
- `AUTHORITY_MANIFEST` remains candidate detection/accountability evidence;
- prompt-cache behavior remains harness/provider controlled.

This proposal must not claim:

- prompt cache is implemented;
- cache hit/miss is observed;
- a harness has adopted the manifest;
- cached authority context is actually reused or discarded;
- runtime hooks, CI, pre-push, gates, or enforcement changed;
- v1.3.0 is prepared or publishable;
- release docs are complete;
- PLAN is refreshed;
- memory behavior changed.

## Review Questions

Reviewers should answer:

1. Does the proposal name a real first consumer rather than another abstract
   receipt?
2. Does the preflight decision rule avoid claiming prompt-cache behavior?
3. Does `reuse_candidate` remain weaker than actual cache reuse?
4. Does the receipt remain evidence-to-inspect rather than authority?
5. Are implementation files for the next tranche narrow enough?
6. Is Claude/human high-rigor review correctly recommended for implementation
   but not required for this docs-only proposal?
