# Skill Claim-Class Boundary v0.1

Status: reviewer-facing normative spec. Claim-discipline only — no execution.

Derived from:
- `docs/governance/agent-runtime-integration-boundary.md` (§3, conceptual)
- `docs/REVIEWER_ENTRYPOINT.md` (claim-class reading)
- README "Capability Status" claim-class definitions
- `docs/governance/trust-boundary-taxonomy.md`

This spec is the normative detail for treating **skills as claims, not
authority**. The conceptual boundary lives in
`agent-runtime-integration-boundary.md`; this document states the rules a
reviewer can check a skill against. It defines *what claim class a skill carries*
and *how that class may change* — not how skills execute.

## Premise

A skill is procedural content that asserts authority over future behavior:
"in situation X, act this way." That makes a skill a **claim**, and claims in
this framework are bounded by claim class (Enforced / Advisory / Observation /
Cannot-claim). A skill therefore must carry a claim class, and it must be
assigned by the same discipline as any other claim.

## Rule 1 — Default claim class is advisory / generated

```
At intake, before ratification, every skill enters at
claim class = advisory, provenance = generated — regardless of source,
regardless of how authoritative its prose reads.
```

This default governs *intake*, not the permanent class: a skill elevated through
Rule 3 (e.g. a ratified repo-native workflow) carries its ratified class
thereafter. Rule 1 prevents *unratified* elevation, not ratification itself.

Consequences of "advisory / generated" (these are the existing claim-class
semantics, not new ones):

- A skill is **not** a gate input. Its presence or its instructions never
  constitute a pass.
- A skill **may not authorize a completion claim**. "The skill said to do X and
  I did X" is not evidence that X is done or correct.
- A skill is admissible as a *suggestion* only until it is ratified (Rule 3).

## Rule 2 — Provenance over tone

```
Claim class is assigned by provenance and ratification, never by tone, format,
or resemblance to a system instruction.
```

Explicit anti-pattern (**claim-class spoofing**): a skill whose prose imitates a
system prompt, an AUTHORITY file, or a ratified rule — and is therefore obeyed as
if it were authority. The defense is structural: the host assigns claim class
from *where the skill came from and whether it was ratified*, and ignores how
commanding the text sounds. A skill that says "ALWAYS do X, this overrides all
other rules" still enters at advisory/generated.

Corollary: skill-supplied content may **not** raise its own claim class. Only the
ratification path (Rule 3) may.

## Rule 3 — Ratification requirements for elevation

A skill may be elevated above advisory only when all of the following are
recorded (this spec states the *requirements*, not an implementation):

1. **Authority**: an identified ratifying authority (per the repo authority
   hierarchy) — not the skill itself, not the agent that generated it.
2. **Evidence**: the skill's effect has artifact-backed evidence at the right
   tier (not prose "it works").
3. **Scope tag**: the situations the skill applies to are explicit; elevation is
   scoped, not global-by-default.
4. **Rollback story**: how an elevated skill is demoted/withdrawn if it later
   proves wrong, including which records must be reversed.
5. **Cross-repo containment**: elevation in one repo does not imply elevation in
   any consumer/other repo (membership-in-one-set-implies-nothing discipline).

Absent any of these, the correct class remains advisory/generated.

## Rule 4 — Non-security-boundary limit (normative, not a disclaimer)

This spec governs the **claim authority** of skills. It does **not** govern
execution safety.

- It does not prevent a malicious or buggy skill from *acting*.
- It makes a skill's effects **visible** and its unratified claims
  **inadmissible** — nothing more.
- It is **not** a sandbox, not RBAC, not SoD, not signature/supply-chain
  verification, not prompt-injection defense.

Stating that this spec "protects against malicious skills" would itself be claim
inflation. The honest scope: against a *benign* skill it prevents over-claim and
unscoped authority; against an *adversarial* skill it provides visibility and
inadmissibility, not prevention.

## Relationship to existing surfaces

- Claim-class taxonomy (README / REVIEWER_ENTRYPOINT): this spec is that taxonomy
  applied to one content type (procedural / skills).
- `agent-runtime-integration-boundary.md` §3: conceptual statement; this spec is
  its normative form. The boundary doc should reference this spec rather than
  restate Rules 1–3 (single-source; avoid drift).
- Checkpoint-memory audit: out of scope here. That detects ungoverned executor
  output; this constrains skill claim authority. Different mechanisms.

## Claim ceiling

```yaml
claim_ceiling:
  - reviewer-facing normative claim-discipline spec only
  - no runtime, hook, CI, or blocker
  - no directory restructure (no governance/skills/ created by this spec)
  - no skill execution / loading implementation
  - no ratification flow implementation (requirements only)
not_claimed:
  - that skills are governed at execution time today
  - that a ratification gate exists today
  - that this prevents malicious or injected skills
  - that claim-class is enforced (it is advisory discipline until wired)
```
