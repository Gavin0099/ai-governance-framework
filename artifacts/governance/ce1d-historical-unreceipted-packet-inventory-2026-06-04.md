# CE-1D Historical Unreceipted Packet Inventory - 2026-06-04

## Scope

Read-only inventory of claim-enforcement raw packet directories that are visible
to the CE-1D.4 receipt validator but do not have compact receipt rows.

This artifact does not migrate, delete, rewrite, or receipt any packet.

Command used:

```powershell
python -m governance_tools.claim_enforcement_receipt_validator --repo-root . --format json
```

Additional summary command used the same validator library and both CE-1D raw
packet roots:

```text
artifacts/session/claim-enforcement
artifacts/claim-enforcement
```

## Validator Result

| field | value |
| --- | ---: |
| receipt rows | 112 |
| valid receipt rows | 112 |
| invalid receipt rows | 0 |
| parse errors | 0 |
| unreceipted raw packet directories | 203 |
| overall_valid | false |

Interpretation:

- `overall_valid=false` is caused by unreceipted raw packet coverage gaps.
- The compact receipt rows themselves parsed and validated structurally.
- This is inventory evidence only, not a cleanup or migration result.

## Root Classification

| raw packet root | unreceipted count | interpretation |
| --- | ---: | --- |
| `artifacts/session/claim-enforcement` | 0 | no unreceipted runtime-root packets observed by this run |
| `artifacts/claim-enforcement` | 203 | legacy/repo-facing raw packet coverage gaps remain |

## Date Classification

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
| `20260601` | 1 |
| non-session UUID | 1 |

Month-level summary:

| month bucket | count |
| --- | ---: |
| `202605` | 201 |
| `202606` | 1 |
| non-session UUID | 1 |

## Current Dirty Packet Boundary

The validator reported one UUID-shaped unreceipted packet:

```text
a5938e4e-07d0-4d4f-ac04-426ec4a5564a
```

This path is also visible as an untracked local artifact under
`artifacts/claim-enforcement/`.

Boundary:

- included in this inventory because CE-1D validator reports it;
- not inspected for semantic content;
- not migrated, deleted, staged, or receipted.

## Representative Session IDs

First 10 validator-reported unreceipted packet IDs:

```text
a5938e4e-07d0-4d4f-ac04-426ec4a5564a
session-20260507T055152-20d770
session-20260507T055153-9a6f48
session-20260507T055203-9ae2c0
session-20260514T104430-64056e
session-20260514T105258-41611a
session-20260514T105339-14311e
session-20260515T083006-38c920
session-20260515T083347-7ffdc6
session-20260515T083808-8e80b3
```

Last 10 validator-reported unreceipted packet IDs:

```text
session-20260529T025147-66b6d5
session-20260529T032647-7bffb8
session-20260529T032836-65851d
session-20260529T033105-fb5b35
session-20260529T045835-10b9d6
session-20260529T080500-24e167
session-20260529T082512-feea4c
session-20260529T084310-20da4e
session-20260529T084732-9ba1e3
session-20260601T044502-d10b08
```

## Recommended Next Step

Do not clean or migrate immediately.

The safe next step is a separate advisory classification proposal that decides
which buckets should be:

- left as historical legacy evidence;
- converted into compact receipt rows;
- moved out of repo-facing artifact space;
- ignored because they are local runtime-only artifacts.

Any cleanup must be a separate scoped slice with explicit approval.

## Claim Ceiling

CLAIMED:

- CE-1D historical unreceipted packet inventory;
- validator-reported counts by root and date bucket;
- receipt rows are structurally valid in this run;
- unreceipted packet coverage gap remains.

NOT CLAIMED:

- raw packet semantic validity;
- receipt truthfulness;
- packet migration;
- packet cleanup;
- compact receipt backfill;
- blocking gate readiness;
- evidence relevance;
- historical repair;
- current dirty workspace cleanup.
