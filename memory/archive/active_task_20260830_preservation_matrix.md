# Active-task replacement preservation matrix — 2026-08-30

Status: **PRE-CUTOVER CANDIDATE / INDEPENDENTLY APPROVED**

Frozen predecessor:

- path: `memory/01_active_task.md`
- verified archive: `memory/archive/active_task_20260830_021544.md`
- SHA-256: `38680653be7302482a0736af7d2ab92a282bc3fa311362f7a56db90c04824d78`
- Git blob: `0ebf087ea6d6ddac4cc6362475401576a7bc2ce9`
- bytes/chars/LF/CR: `11447 / 11435 / 159 / 0`
- BOM/trailing LF: `false / true`

Replacement candidate:
`memory/archive/active_task_20260830_replacement_candidate.md`

- SHA-256: `af8ea689932f374963830a27f124b90912ff238f0482830cf173ce1cf1279624`
- bytes/chars/LF/CR: `8661 / 8659 / 122 / 0`
- independent reviewer: `/root/amendment_fidelity_review`
- verdict: `APPROVED` with `0` blocking findings and `0` warnings
- review scope: the sole corrected delta is `44 historical / 19 prospective`
  to `43 historical / 20 prospective`; the other 17 rows are byte-identical to
  the previously reviewed candidate, and all 18 rows preserve their decision effect.

| Predecessor item and anchor | Class | Preservation mode | Replacement location | Authority / decision effect | Review |
| --- | --- | --- | --- | --- | --- |
| `Current Focus`: consumed A/B pair is `NON_SUCCESS`; no reuse/retry/replacement; credentials, preflight and live unauthorized | irreversible state | verbatim semantic core | `Irreversible State And Prohibitions` item 1 | unchanged; no authority restored | `PASS` |
| rev9 `92004c3f...` is `CHANGES_REQUESTED/HIGH`; architecture STOP; no rev10 | irreversible state + authority status | exact digest/status plus semantic equivalent | `Current Gate 3 State` item 2; authority index `rev9 rejected bytes` | unchanged; rejected bytes not promoted or revived | `PASS` |
| historical Gate 2/A-B evidence cannot be retrospectively repaired or counted | irreversible/countability state | reviewed semantic equivalent | `Irreversible State And Prohibitions` item 2 | unchanged; no countability restored | `PASS` |
| native-path claim corrected twice; N3c-2 created objects versus borrowed `base`/ancestors | effective claim ceiling | operative corrected wording preserved | `Claim Ceiling` item 2 | unchanged; neither prior overclaim reintroduced | `PASS` |
| M3-b-1 mutation evidence boundary: `80b2a74c` recorded result but harness unavailable; `fa10dda8` onward has no mutation evidence | effective claim ceiling | reviewed semantic equivalent with exact commit anchors | `Claim Ceiling` item 4 | unchanged | `PASS` |
| no Gate 3/effectiveness/reachability/implementation/consumer/enforcement/clean-workspace claims | effective claim ceilings | reviewed semantic equivalents | `Claim Ceiling` items 1–7 | unchanged or narrower; no positive claim introduced | `PASS` |
| PLAN external-pin authority exact identity | authority reference/status | exact existing committed pointer | authority index `Gate 3 funding authority` | unchanged | `PASS` |
| Release-Order design `e0101978...` is reviewed/committed design only | authority reference/status | exact existing committed pointer plus nonclaims | authority index `Release-Order design` | unchanged; not promoted to provider/implementation proof | `PASS` |
| source-set closure `dec86ce9...` | authority reference/status | exact existing committed pointer; owner-adoption status stated separately | authority index `Authority source-set closure` and following adoption note | adopted status preserved without claiming commit bytes say adopted | `PASS` |
| predicate register `8e67c874...`, 63 rows | authority reference/status | exact existing committed pointer; owner-adoption status stated separately | authority index `Closed-source predicate register` and following adoption note | adopted blocker surface preserved; no new predicate | `PASS` |
| unavailable standalone eight-step referent remains unresolved | authority status / unresolved | exact pointer to adopted closure disposition | authority index `Authority source-set closure` | unresolved preserved; no reconstruction | `PASS` |
| M3-b-2A/B-1/M3-b-2B/M3-b-3/M4 status and lack of authorization | irreversible/current work state | semantic compression with exact critical tokens | `Other Retained Workstream State` items 1–3 | unchanged; dirty work not authorized or discarded | `PASS` |
| PR #95/public visibility/Support/Finding 33 effective latest states | irreversible/current state | reviewed semantic equivalent using latest effective predecessor entries | `Other Retained Workstream State` item 4 | earlier superseded private-state wording not revived | `PASS` |
| F-7 correction complete/inactive; no expansion absent new failure | authority/current state | reviewed semantic equivalent | `Other Retained Workstream State` item 5 | unchanged | `PASS` |
| four predecessor `Open Risks` | open risk | semantic equivalent, no disposition | `Open Risks` items 1–4 | all remain open | `PASS` |
| unsafe janitor and one-final-attempt stop rule | operational authority/status | exact committed pointers plus semantic equivalent | authority index memory rows; `Irreversible State And Prohibitions` item 4 | fail-closed and no-third-candidate boundary preserved | `PASS` |
| provider work follows relocation but is not authorized by cutover | authorization boundary | semantic equivalent | `Current Gate 3 State` item 4; `Next Decision Boundary` | no automatic continuation | `PASS` |
| prior executor wrapper noncompletion is not a machine-wide fact | effective claim ceiling | owner correction preserved verbatim in substance | `Claim Ceiling` item 6 | executor-scoped only; no full gate PASS | `PASS` |

Review result: **APPROVED** for replacement SHA-256
`af8ea689932f374963830a27f124b90912ff238f0482830cf173ce1cf1279624`.

Every row and the overall result were independently accepted for the exact
replacement SHA-256 above. Any later byte change invalidates this approval.
