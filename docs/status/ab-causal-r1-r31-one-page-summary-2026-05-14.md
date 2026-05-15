# AB Causal Program One-Page Summary (r1-r31)

As-of: 2026-05-14
Conclusion posture: bounded, non-upgrade

## Phase Snapshot

| Phase | Run Range | Core Result | Gate Status | What This Supports | What This Does NOT Support |
|---|---|---|---|---|---|
| Baseline / Early Execution | r1-r8 | Initial execution scaffolding and measurement path established | N/A | process bootstrapping and artifact lineage | any causal claim |
| First Reproducibility Signal | r9-r10 | same-setting directional consistency observed | reproducibility signal only | observable uplift not likely pure noise in this setup | mechanism isolation |
| Multi-window Confirmation | r11-r15 | direction consistency and required checks completed (with addendum backfill path) | provisionally_confirmed (bounded) | conditional reproducibility under current protocol | generalized robustness |
| Condition-break Round 1 | r16-r19 | mixed outcomes; stress windows failed | causal-strength-unchanged | mechanism boundary is observable | causal-strength upgrade |
| Condition-break Round 2 | r24-r27 | r24 fail; r25-r27 pass but policy-sensitive | causal-strength-unchanged | pass can be achieved under relaxed policy envelope | mechanism-stable pass under strict policy |

## Cross-Program Readout (r1-r31)

1. Reproducibility maturity: strong (within bounded protocol/task distribution).
2. Auditability maturity: strong (windowed evidence lineage and commit traceability).
3. Causal-strength maturity: unchanged (not upgraded).
4. Robustness under stress: insufficient (policy-sensitive pass dominates in latest windows).
5. Current primary risk: policy sensitivity (outcome depends on relaxation configuration).

## Claim Boundary (Current)

Allowed:
- "Observable uplift is conditionally reproducible under the current protocol."
- "Causal strength remains unchanged after condition-break validation."
- "Latest passes are policy-sensitive and therefore non-upgradeable for causal claims."

Not allowed:
- "Mechanism is robustly confirmed."
- "Causal strength upgraded."
- "Generalized performance across broader distributions is established."

## Why Upgrade Is Blocked

- Condition-break windows include fails in stress/ambiguity settings.
- Policy-sensitive-pass signals indicate dependence on policy relaxation rather than stable mechanism.
- Upgrade guard correctly blocks causal-strength promotion when policy sensitivity is present.

## Next Required Work (already planned)

1. Policy-relaxation ablation matrix (strict vs A/B/C combinations).
2. Guardrail/placebo regression per ablation cell.
3. Failure taxonomy layered summary using observation logs.
4. Enforce-mode restore readiness test before restoring strict pre-push enforcement.

Reference plan:
- `docs/status/policy-sensitivity-reduction-test-plan-r28-r31-2026-05-14.md`
