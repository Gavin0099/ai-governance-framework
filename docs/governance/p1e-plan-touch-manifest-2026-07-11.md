# P1-E PLAN-Touch Manifest — 2026-07-11

Status: observation evidence; corrective read-only manifest

Scope: commits on `main` that touched `PLAN.md`, from 2026-06-12 through
2026-07-11 inclusive. No PLAN, gate, hook, CI, or writer behavior changed.

## Method

The authoritative commit set is:

```powershell
git log main --since=2026-06-12 --until=2026-07-11T23:59:59+08:00 --format=%H -- PLAN.md
```

For each resulting commit, canonical daily memory records were inspected for
either (a) an exact `commit` field match or (b) an explicit commit hash in the
record text. Date proximity, subject similarity, and an unbound `WORKTREE`
record are **not** treated as a correspondence. That prevents this manifest
from inventing a semantic PLAN-touch ground truth that the P1-E report was not
designed to provide.

The report command was re-run at this snapshot:

```powershell
.venv\Scripts\python.exe -X utf8 -m governance_tools.deferred_debt_report --project-root . --as-of 2026-07-11 --format json
```

It reported 698 session-derived records: `updated=55`,
`not_applicable=343`, `deferred=7`, `not_declared=44`, `pre_field=249`, and
`malformed=0`. The post-field declaration rate is `405 / 449 = 90.2%`.

## Directly Auditable Correspondence Entries

| PLAN commit | Matching canonical memory record(s) | Formal field | Prose / correction variant | Denominator disposition and reason |
| --- | --- | --- | --- | --- |
| `c2f72521` | `memory/2026-07-11.md`, `commit=c2f72521` | `updated` | none | Excluded from semantic FN rate: exact pairing proves declaration only, not whether every PLAN change was semantically reconciled. |
| `ded1b43b` | `memory/2026-07-11.md`, two records with `commit=ded1b43b` | `updated`; later `not_applicable` provenance correction | later record corrects evidence provenance, not the PLAN declaration | Same exclusion. |
| `16f3dbee` | `memory/2026-07-10.md`, `commit=16f3dbee` | `updated` | none | Same exclusion. |
| `628456e0` | `memory/2026-07-10.md`, `commit=628456e0` | `updated` | none | Same exclusion. |
| `6f7938b9` | `memory/2026-07-10.md`, `commit=6f7938b9` | `updated` | none | Same exclusion. |
| `b82b6582` | `memory/2026-07-10.md`, two records with `commit=b82b6582` | `updated` | evidence-provenance correction retained separately | Same exclusion. |
| `39c2c877` | `memory/2026-07-10.md`, three records with `commit=39c2c877` | initial `not_declared`; later corrections `updated` | initial writer-era omission was later corrected | Not a tool false positive: the tool correctly reports the initial missing formal field. Do not erase this history by counting the corrected record as an original pass. |
| `815d6879` | `memory/2026-07-10.md`, `commit=815d68791b75…` | `updated` | full SHA form | Same exclusion. |
| `9a787970` | `memory/2026-07-10.md`, `commit=9a787970` | `updated` | none | Same exclusion. |
| `57cecc8e` | `memory/2026-07-10.md`, `commit=57cecc8e5a8f…` | `updated` | full SHA form | Same exclusion. |
| `6818b5b6` | `memory/2026-07-10.md`, `commit=6818b5b6` | `updated` | push record is additional, not the primary pairing | Same exclusion. |
| `e0330120` | `memory/2026-07-10.md`, `commit=e0330120` | `updated` | record names the amendment commit within the same reconciliation event | Same exclusion. |
| `31fa4d09` | `memory/2026-07-06.md`, `commit=31fa4d09` | `updated` | none | Same exclusion. |

One further commit, `de6cbaf9`, has only an **indirect** textual reference in a
later push record (`memory/2026-07-10.md`, `commit=4057aa70`,
`plan_reconciliation=not_applicable`). It is retained as an indirect
observation, not counted as an exact pair.

## No Durable Direct Correspondence

The following 42 PLAN commits have no exact canonical-memory `commit` match
and no explicit hash reference in a canonical session-derived record under the
method above:

```text
c22dcc02 55a32428 af3287f6 1e7d27a4 d521c933 748c505c 66395377
174ce74d bda3424e 60e3277b 9a3ff715 688ebc68 caeabfdb 61954401
7728c99f ebe9d1d2 33f76949 1924de09 2756661f ace5a62e 9acb1790
ce6de50b 1673f18c d7301ede 292ff013 1330d923 4fbffa34 ed14dbfb
64d10af2 3e16f6c1 a3a57310 c197d880 147f4b78 bc015a1f 4cd9853a
4020763d b2d19312 4de4ac00 7c561d2d cbffa03e a5135c01 e65c948b
```

These are not automatically false negatives. The canonical writer often
records a later memory commit, a push-chain commit, or (historically) a
`WORKTREE` placeholder rather than the exact PLAN commit. The current evidence
therefore does not support a complete commit-to-memory semantic denominator.

## Recomputed FP/FN Boundary

- **Tool FP rate:** not computable from this sample. There are no audited cases
  showing that `deferred_debt_report` labelled a record `not_declared` when a
  valid formal `plan_reconciliation` field was present.
- **Tool FN rate:** not computable from this sample. The report intentionally
  does not infer PLAN-touch semantics from prose or Git diffs.
- **Semantic PLAN-touch FN rate:** not computable. The prior `4 / 38 = 10.5%`
  figure is withdrawn: its stated 38 anchors did not reconcile with its listed
  33 passes plus 4 misses, and the present reproducible manifest establishes
  only 13 direct pairs plus one indirect reference.
- **Observed advisory signal:** `not_declared=44` remains real, and its growth
  since the two-week checkpoint warrants a future decision discussion. It is
  an association between observed writer output and declaration coverage, not
  evidence that advisory mode caused or failed to cause any behavior.

## Claim Ceiling

Can claim: the four-week P1-E observation window has a reproducible report
snapshot and a manifest that exposes the current identity-linkage limit.

Cannot claim: a quantified semantic FN rate, a zero FP rate, causal effect of
advisory output, PLAN synchronization correctness, or authorization for P1-F
blocking enforcement.
