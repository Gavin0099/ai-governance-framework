# Rule Registry Classification Decision — 2026-07-13

## Decision

Owner-approved reconciliation of the framework rule registry after a read-only
registry/artifact consistency audit and external-contract inventory.

The registry uses three independent classification axes:

- `artifact_state`: whether an artifact exists now;
- `ownership`: which authority controls the rule semantics and activation;
- `activation_mode`: how an implemented pack may enter runtime selection.

Machine values use underscores: `context_aware` and `explicit_only`.

## Approved Classification

| Pack | Artifact | Ownership | Activation | Decision |
| --- | --- | --- | --- | --- |
| `common` | implemented | framework | always | Framework baseline |
| `cpp` | implemented | framework | context_aware | Framework language pack |
| `csharp` | implemented | framework | context_aware | Framework language pack |
| `python` | implemented | framework | context_aware | Framework language pack |
| `swift` | implemented | framework | context_aware | Framework language pack |
| `avalonia` | implemented | framework | context_aware | Framework UI pack |
| `refactor` | implemented | framework | context_aware | Task-text-triggered framework scope pack |
| `kernel-driver` | implemented | framework | context_aware | Framework baseline plus contract override |
| `gl-hub-vendor-cmd` | implemented | external-contract | explicit_only | External contract activation authority |
| `release` | planned | framework | none | Preserve reserved slot; suppress operational output |
| `typescript` | planned | framework | none | Preserve adoption candidate slot; suppress operational output |
| `electron` | planned | framework | none | Preserve reserved slot; suppress operational output |
| `firmware_isr` | planned | unresolved | none | Re-review by 2026-10-13 |
| `nextjs` | — | — | — | Remove stale declaration and routing |
| `supabase` | — | — | — | Remove stale declaration and routing |
| `review_gate` | — | — | — | Remove stale declaration and universal routing |

The implemented list contains nine names. This matches the nine physical pack
folders distributed under `governance/rules/`.

## Authority Findings

### Kernel driver

`kernel-driver` is a framework baseline. The external
`Kernel-Driver-Contract` also declares `rules/kernel-driver`; runtime resolves
contract rule roots before the framework root, so the contract-local content is
an intentional override rather than evidence that both artifacts are identical.

### GL hub vendor commands

`gl_electron_tool/contract.yaml` declares domain `gl-hub-vendor-cmd` and carries
the same `spec-truth.md` content as the framework compatibility mirror. Git
history shows the framework artifact predates the consumer sync. Therefore the
external contract is the activation authority, but this decision does not claim
that the external repository authored the original text.

### Firmware ISR

The USB hub firmware contract and the Windows kernel-driver contract both carry
interrupt-safety rules, but they do not share APIs, memory models, or evidence
requirements. `firmware_isr` remains planned with unresolved ownership and must
not be merged into either authority without a later review.

## Enforced Invariants

1. Planned entries cannot enter active, preview, warning, skill, or agent
   outputs.
2. The names of implemented registry entries equal the names of physical
   framework pack folders, in both directions.
3. `explicit_only` entries are never context-classified. They remain loadable
   only through an explicit runtime or contract request.
4. Registry parsing accepts legacy `load_mode`, exposes a compatibility alias,
   and tolerates unknown future metadata.
5. `nextjs`, `supabase`, and `review_gate` have no registry or hard-coded
   classification route after reconciliation.

## Scope Boundary

This decision does not move or modify any external contract artifact, remove
the framework GL-hub compatibility mirror, implement contract
`default_rule_packs`, change rule-root precedence, or claim token reduction.

## Evidence Basis

- Registry/artifact audit: 15 declarations, 9 physical framework folders,
  seven declarations without artifacts, and one folder without a declaration.
- External contract inventory under `E:\BackUp\Git_EE`.
- Owner approval in the 2026-07-13 reconciliation session.
- Independent review approving the three-axis model and the classifications
  above, with the implemented-folder completeness condition incorporated here.
