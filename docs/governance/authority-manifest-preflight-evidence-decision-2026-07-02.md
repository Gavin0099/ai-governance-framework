# AUTHORITY_MANIFEST Preflight Evidence Decision - 2026-07-02

## Decision

Maintain the AUTHORITY_MANIFEST preflight path as **Unreleased candidate-only**
for now.

Do not collect or claim real harness consumer evidence until a separate slice
names a real harness consumer, defines its evidence contract, and records
consumer-side behavior outside the repo-side simulation.

## Why This Is The Safer Next Step

Current repo evidence proves a read-only candidate generator and a no-write
preflight consumer simulation. It does not prove prompt-cache behavior, harness
adoption, cache reuse, or runtime enforcement.

The existing preflight path emits reviewer-facing decisions:

- `reuse_candidate`: the manifest is readable, drift is acceptable, and
  authority did not change; this is weaker than actual cache reuse.
- `reload_required`: authority changed or a cache-invalidating condition exists;
  the harness should reload authority files.
- `cache_unsafe`: the manifest is missing, malformed, wrong-schema, critical, or
  overclaims prompt-cache enforcement; no cache reuse claim is supported.
- `not_checked`: the consumer did not evaluate the manifest; no cache reuse
  claim is supported.

Because the current implementation is a repo-side simulation, collecting "real
harness evidence" now would either require expanding scope into harness/provider
integration or risk inflating a candidate receipt into an adoption claim. The
clean next state is therefore: candidate tooling remains documented, tested, and
explicitly unreleased.

## Evidence Already Present

- `governance_tools/authority_manifest.py` is documented as a read-only
  candidate generator and says it is detection/accountability only, not prompt
  cache behavior or enforcement.
- `governance_tools/authority_manifest_preflight.py` is documented as a
  no-write simulation that emits `AUTHORITY_MANIFEST_PREFLIGHT_RECEIPT v0.1`
  with `cache_behavior_claim=not_observed` and
  `runtime_enforcement_claim=not_enforced_by_repo`.
- `tests/test_authority_manifest_preflight.py` covers malformed or wrong-schema
  manifests as `cache_unsafe`, authority changes as `reload_required`, and
  unchanged acceptable manifests as `reuse_candidate`.
- `docs/governance/prompt-cache-harness-consumer-contract-2026-06-29.md`
  already states that repo-side tooling must not claim harness actions occurred
  unless the harness emits evidence.
- `PLAN.md` and `CHANGELOG.md` keep the generator and preflight consumer under
  Unreleased candidate surfaces, without release, hook, CI, gate, or enforcement
  claims.

## Evidence Gaps Before Real Harness Collection

Real harness consumer evidence should not be collected or claimed until these
gaps are closed:

- A named harness consumer exists, with owner, version, commit, or executable
  entrypoint.
- The harness actually consumes an `AUTHORITY_MANIFEST v1` payload or generated
  manifest path.
- The harness records a preflight receipt before deciding whether to reuse or
  reload authority context.
- The evidence shows consumer-side action, not just repo-side recommendation:
  reload occurred for `reload_required`, no reuse occurred for `cache_unsafe`,
  and any reuse path is still explicitly weaker than provider cache-hit proof.
- Negative-path evidence exists for malformed, missing, wrong-schema, critical
  drift, and authority-changed inputs.
- The evidence links to concrete base/head refs, manifest content, receipt
  content, and dirty-tree/staleness handling.
- The claim boundary remains reviewable: harness behavior may be observed, but
  provider cache hit/miss behavior is still not proven unless provider evidence
  is supplied.

## Not Claimed

This decision note does not claim:

- prompt cache implementation;
- cache hit/miss monitoring;
- actual cache reuse;
- real harness adoption;
- provider integration;
- runtime hook, CI, pre-push, or gate enforcement;
- canonical authority promotion for `AUTHORITY_MANIFEST`;
- release readiness for `v1.3.0`;
- mode, auth, tool-denial, or compaction receipt adoption;
- cross-repo writes or consuming-repo verification.

## Reopen Criteria

Reopen real harness evidence collection only when a future DONE scope includes:

- the exact harness consumer to inspect;
- allowed files or artifacts;
- required receipt fields;
- positive and negative evidence cases;
- validation commands;
- claim ceiling and non-claims;
- commit/push intent.

Until then, the next correct state is:

```text
AUTHORITY_MANIFEST preflight path: Unreleased candidate-only
Consumer evidence collection: not yet authorized or evidenced
Claim ceiling: repo-side read-only candidate tooling and simulation only
```
