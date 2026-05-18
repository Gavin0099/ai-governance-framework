# Governance Statefulness Risk

**Recorded**: 2026-05-18
**Context**: After MOB Verifier v0.2 + boundary freeze session

## What changed this session

The system acquired **governance statefulness** — it now holds:

- Policy memory (hearth-obligation-policy-v0.1.md)
- Deferred list (frozen, explicit)
- Claim ceiling (bounded_reconstruction with temporal applicability filtering)
- Boundary freeze (three anti-drift statements)

This is qualitatively different from earlier sessions. Before: the verifier
was a tool. After: the verifier + policy + memory form a governance substrate
that can be misread, ossified, or silently invalidated.

## Why the boundary freeze matters

The three sentences written this session:

    pre_convention ≠ clean
    gap_observed ≠ confirmed gap
    batch scan ≠ historical pattern proof

These are **anti-reinterpretation markers**. Their purpose is to prevent
future semantic overconsumption — the pattern where artifact output gets
quietly upgraded:

    absence of gap_observed → "governance clean"
    gap_observed count → "governance failure rate"
    batch scan observations → "historical trend evidence"

The danger is not malicious reinterpretation. It is **natural language drift**:
someone reads a summary, loses the qualifier, and the claim ceiling silently
rises in their mental model without any explicit decision.

## The four stale governance memory risks

Once a system has governance statefulness, the dominant future risk is not
hallucination — it is **stale memory**.

| Risk | Pattern | Symptom |
|------|---------|---------|
| Policy fossilization | Deferred list never revisited | Old deferrals treated as permanent policy |
| Artificial capability cap | Claim ceiling never updated | System can do more than it claims, or claims more than it can |
| Silent invalidation | Architecture changes bypass old boundary | Boundary wording still present but no longer maps to real system |
| Semantic ossification | Memory wording reused as ritual | Words copied without checking whether the referent still exists |

## Architectural principle: meaning travels with the record

`gap_claim_allowed=False` is a structural attribute of the record itself,
not a note in a procedure document. The difference matters:

- Procedure doc: reviewer must remember to check before consuming
- Structural field: consumer must actively discard the field to bypass it

This is why the boundary is architecture-coupled, not process-coupled.
Silent invalidation becomes visible the moment a consumer reads the schema.

## When governance memory revalidation becomes necessary

Not now (2026-05-18). The current freeze is healthy.

Revalidation triggers (any one is sufficient):

1. MOB rule ontology changed (new obligation type added or removed)
2. Record schema changed (fields added, renamed, or removed)
3. Consumer path added (new system reads verifier output)
4. Summary or dashboard added (aggregation introduces new consumption semantics)
5. convention_start semantics changed (global gate → per-MOB gate, or date revised)

## Revalidation entry point: consumer contract tests, not verifier tests

The verifier produces correct records. The failure mode is not in the verifier.

Silent invalidation most likely arrives via a **correct reader with incorrect
consumption semantics** — a new consumer that reads the record faithfully
but uses its meaning incorrectly.

Therefore the revalidation entry point is **consumer contract tests**:

    pre_convention record must not enter gap aggregation
    gap_claim_allowed=False must block gap consumption pipeline
    summary must preserve claim ceiling field unchanged

These tests do not exist yet — no consumer path exists yet. They should be
written at the moment a consumer path is added, not before. Writing them
speculatively creates the same fossilization risk they are meant to prevent.

## What NOT to do

- Do not revalidate as a ritual ("it's been N months, let's check").
  Revalidate only when a trigger condition above is met.
- Do not write consumer contract tests speculatively — write them when
  a real consumer path exists.
- Do not merge revalidation with capability expansion — different operations,
  different evidence requirements.
- Do not treat a passing revalidation as a claim ceiling upgrade.
