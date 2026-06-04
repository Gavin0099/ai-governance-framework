# CE-1D Bucket A Advisory Disposition Policy - 2026-06-04

## Scope

Advisory disposition policy proposal for CE-1D Bucket A:

```text
201 historical 2026-05 legacy session packets under artifacts/claim-enforcement/
```

DONE boundary:

```text
propose CE-1D Bucket A advisory disposition policy for the 201 historical legacy packets, without moving, deleting, receipting, staging packets, or changing validator behavior.
```

## Evidence Inputs

This policy is based on previously committed CE-1D inventory and classification
artifacts:

- `artifacts/governance/ce1d-historical-unreceipted-packet-inventory-2026-06-04.md`
- `artifacts/governance/ce1d-unreceipted-packet-advisory-classification-2026-06-04.md`
- `artifacts/governance/ce1d-bucket-b-single-packet-review-2026-06-04.md`
- `artifacts/governance/ce1d-bucket-c-dirty-packet-audit-2026-06-04.md`

No Bucket A packet directories were moved, deleted, staged, receipted, or
rewritten for this policy proposal.

## Bucket A Population

Bucket A contains the historical 2026-05 legacy `session-*` cluster:

| date bucket | count |
| --- | ---: |
| `20260507` | 3 |
| `20260514` | 3 |
| `20260515` | 20 |
| `20260518` | 12 |
| `20260520` | 36 |
| `20260521` | 34 |
| `20260522` | 61 |
| `20260527` | 3 |
| `20260528` | 18 |
| `20260529` | 11 |
| total | 201 |

The population is distinct from:

- Bucket B: `session-20260601T044502-d10b08`
- Bucket C: `a5938e4e-07d0-4d4f-ac04-426ec4a5564a`

## Recommended Default Disposition

Recommended disposition:

```text
retain_in_place_as_historical_legacy_raw_packets
```

This means:

- leave Bucket A packet directories in their current legacy root;
- do not backfill compact receipt rows by default;
- do not delete as hygiene cleanup;
- do not migrate to the newer runtime packet root;
- do not stage or recommit packet directories;
- keep validator behavior unchanged.

## Rationale

Bucket A is historical path-debt, not current runtime evidence.

The 201 packets are pre-CE-1D legacy artifacts under
`artifacts/claim-enforcement/`. Bulk action would create more governance risk
than value unless a reviewer explicitly requests cleanup or backfill:

- bulk backfill could create false repair claims by making old local runtime
  packets look like current compact receipt evidence;
- bulk deletion could destroy historical debugging context;
- bulk migration could blur old legacy-root evidence with the newer
  `artifacts/session/claim-enforcement/` runtime-root convention;
- staging packet directories would expand the current scope beyond an advisory
  policy proposal.

## Allowed Future Actions

Future CE-1D work may open a separate scoped slice for one of these actions:

| future action | allowed only if | non-claims |
| --- | --- | --- |
| retain policy confirmation | reviewer accepts historical raw packet retention as acceptable debt | not cleanup, not receipt repair |
| archival policy proposal | reviewer wants a cleaner repo-facing artifact layout | not deletion unless explicitly approved |
| sampled source-context audit | reviewer wants to understand representative 2026-05 packet provenance | not full 201-packet semantic audit |
| compact receipt backfill design | reviewer decides historical packets should become receipt-covered evidence | not admissible until evidence criteria are defined |
| cleanup/deletion proposal | reviewer explicitly asks whether historical orphan packets can be removed | not allowed without destructive-action approval |

## Required Guardrails For Any Future Non-Retention Action

Any future action other than retaining Bucket A in place must define:

- exact packet population;
- whether packet directories may be staged;
- whether packet directories may be moved;
- whether packet directories may be deleted;
- whether compact receipts may be generated;
- how false repair claims are prevented;
- how legacy local-only runtime evidence is distinguished from admissible
  compact receipt evidence;
- validation commands and expected failure mode if unreceipted packets remain.

## Trigger Conditions

Do not advance beyond retain-in-place unless at least one trigger exists:

- reviewer asks for CE-1D cleanup or archival policy;
- validator output becomes noisy enough to block unrelated review work;
- a release or publication package requires repo-facing artifact cleanup;
- historical packet retention creates measurable confusion in evidence review;
- a consuming repo needs a documented CE-1D historical debt policy.

Absent those triggers, Bucket A should stay in place as known historical debt.

## Proposed Next Action

No immediate cleanup or migration.

If CE-1D continues, the safest next slice is:

```text
CE-1D local-runtime orphan cleanup policy
```

That future slice should cover Bucket B and Bucket C local-runtime orphan
handling separately from Bucket A historical legacy retention.

## Claim Ceiling

CLAIMED:

- advisory disposition policy proposal for Bucket A;
- default recommendation:
  `retain_in_place_as_historical_legacy_raw_packets`;
- trigger conditions for future archival, cleanup, migration, or backfill
  consideration;
- no packet movement, deletion, staging, receipting, or validator behavior
  change.

NOT CLAIMED:

- Bucket A packets are valid compact receipt evidence;
- Bucket A packets should be backfilled;
- Bucket A packets should be deleted;
- Bucket A packets should be migrated;
- historical packet truthfulness;
- evidence relevance;
- semantic correctness;
- cleanup readiness;
- validator completeness;
- runtime enforcement.

## Validation

Suggested scoped validation for this policy slice:

```text
git diff --check -- artifacts/governance/ce1d-bucket-a-advisory-disposition-policy-2026-06-04.md PLAN.md
```
