# Solo Historical Replay Qualification — 4-of-7 Evidence Checkpoint

Date: 2026-08-30

Status: `EVIDENCE_CHECKPOINT / QUALIFICATION 4 OF 7`

Track: `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`

## 1. Purpose and claim boundary

This checkpoint makes the confirmed Pair 0, A1, A2, and A3 qualification
dispositions and the surviving instruments durable before A4–A6 work begins.
It does **not** recreate discarded runner output, re-execute an oracle, create a
Pair ID or Attempt ID, or establish any Formal Gate 3 evidence.

The record is retrospective preservation of already observed and owner-reviewed
qualification outcomes. Where the original runner identity or raw output is no
longer available, that limitation remains explicit rather than inferred.

Frozen selection source:

- Commit: `c56b6258e4414d3c4699d9663da378674618224a`
- Blob: `d517fa6caacd95368d997802480d74162b709fcd`
- SHA-256: `3502f517b7c42300d5ae15e077b67acaa3d7379bc620a85efdf38a490e37d67c`
- Path: `docs/governance/solo-historical-replay-selection-state-candidate-20260830.md`

## 2. Preserved instrument manifest

The files under `harnesses/` are byte-exact evidence copies of the instruments
that remain available. Copying them here does not migrate the harness lifecycle
or authorize future execution from this directory.

| Evidence copy | Source at checkpoint | SHA-256 | Bytes | LF | CR | BOM |
|---|---|---|---:|---:|---:|---|
| `harnesses/pair0-harness.ps1` | `.qualification_tmp/solo-20260830/pair0-harness.ps1` | `3745fe8091315c3bcc2ca294814b18e627d704dd121724694c7f8471e6846817` | 10,919 | 279 | 0 | no |
| `harnesses/a2-harness.ps1` | `.qualification_tmp/solo-20260830/a2-harness.ps1` | `bfaf46372a5f43a05a50474c29817c39bcb845681e09dc26f49e8d45df480920` | 16,080 | 400 | 0 | no |
| `harnesses/a3-v2-harness.ps1` | `.qualification_tmp/solo-20260830/a3-harness-config-runner-candidate-v2.ps1` | `4d44bd7d55c000460e082f3576550a3fc829417a67dc6bdef81a66ec063fe2a2` | 31,461 | 427 | 0 | no |

## 3. Qualification dispositions

### Pair 0 — shakedown/simple — Bookstore-Scraper

- Base: `e478409971dd8e72335966350fcfaee2a6cdb8b0`
- Historical fix: `c9cd494bfa087a86d5e1c34702a2ad7997ad7b7b`
- Oracle: `tests/test_scraper_regressions.py`
- Oracle blob: `93ad7d9d56b1534bd180af83ba69ad23e64f3c6b`
- Required cases:
  - `test_grimm_parse_price_preserves_thousands_separator_value`
  - `test_grimm_parse_price_prefers_original_price_with_thousands_separator`
- Instrument SHA-256: `3745fe8091315c3bcc2ca294814b18e627d704dd121724694c7f8471e6846817`
- Observed Base result: 2/2 required cases produced behavioral failure.
- Observed Fix result: 2/2 required cases passed.
- Harness output token: `HARNESS_SELF_TEST_REPRODUCED`.
- Accepted qualification disposition: `QUALIFIED`.

Pair 0 is the pre-declared shakedown pair and is not an analytic Solo pair.

### A1 — straightforward fix — Bookstore-Scraper

- Base: `6e673dc46457d469dd98e5993139194eceeb1211`
- Historical fix: `56d1b82372a995fc07431b4583f43237092babf4`
- Oracle: `tests/test_scraper_regressions.py`
- Oracle blob: `3349ede3fe8e7497204f0dd72d647629a33c7995`
- Required case:
  - `test_tony_kids_schema_instock_accepts_http_uri_variant`
- Instrument identity: `NOT_DURABLY_CAPTURED`.
- Observed Base result: 1/1 required case produced behavioral failure.
- Observed Fix result: 1/1 required case passed.
- Accepted qualification disposition: `QUALIFIED`.

The exact A1 runner source and raw output were not preserved durably at the time
of execution. This checkpoint does not guess that identity and does not claim
byte-level reproducibility for the original A1 run.

### A2 — root-cause analysis — Hearth

- Base: `861e304a5cf19492cc74b1a780b77c6bc1c68ae8`
- Historical fix: `cf197f2d8275cb326ae9c8e1a1ae896116481e11`
- Oracle: `apps/api/tests/pdf-credit-card.test.ts`
- Oracle blob: `66a04b07a46cae8143f3cfdf4c882ad28fd01e72`
- Required case:
  - `parseSinopacInsuranceSection handles inline insurance header and policy rows`
- Instrument SHA-256: `bfaf46372a5f43a05a50474c29817c39bcb845681e09dc26f49e8d45df480920`
- Observed Base result: 1/1 required case produced behavioral failure.
- Observed Fix result: 1/1 required case passed.
- Accepted qualification disposition: `QUALIFIED`.

Corrected-run workspace-resolution evidence, normalized because the temporary
snapshot UUIDs were deleted after execution:

- Base: `<base snapshot>\packages\shared\src\index.ts`
- Fix: `<fix snapshot>\packages\shared\src\index.ts`
- Both resolved paths were verified inside their corresponding snapshot roots.

Prior audit trail:

- An earlier A2 run produced Base PASS / Fix PASS while
  `node_modules/@hearth/shared` escaped to the live
  `D:\Hearth\packages\shared` workspace.
- That result is retained as
  `INVALIDATED_BY_HARNESS_CONTAMINATION / HARNESS_FAILURE`.
- It is not a task-level `NOT_QUALIFIED` outcome and was not used for the final
  A2 disposition.

### A3 — regression — english-vocab-trainer

- Base: `04e320233efb6ad8d49bf80c59374918ee126bce`
- Historical fix: `f1da14b857dc3fa8831215360f818f9600042c3e`
- Oracle: `src/lib/dailyLearning.test.ts`
- Oracle blob: `dac278c808d31093382b79737f1392d441bd379d`
- Required cases:
  - `shows reviewed words first on the Starters route`
  - `shows reviewed words first on the Movers route`
  - `shows reviewed words first on the cefr-a1 route`
  - `shows reviewed words first on the cefr-a2 route`
  - `shows reviewed words first on the gept-elementary route`
- Instrument SHA-256: `4d44bd7d55c000460e082f3576550a3fc829417a67dc6bdef81a66ec063fe2a2`
- Independent fidelity review: `PASS` for this exact instrument identity.
- Observed Base result: 5/5 required cases produced behavioral failure; each
  target executed exactly once with zero unintended executed assertions.
- Observed Fix result: 5/5 required cases passed; each target executed exactly
  once with zero unintended executed assertions.
- Harness exit: `0`.
- Harness disposition: `QUALIFIED`.

The earlier A3 bundle-loader harness
`6070786822dcd48c801a484fb86c4a1da174170eaa8e19d7c57d6b9b6cd6f809`
remains negative harness evidence only. It failed before oracle execution and
did not produce an A3 task outcome. The V1 correction candidate
`b2223ed71fbc8e9c3a0c1b9852f33e3ec152c13dea7118ad33a59b2f8e05993d`
was not adopted and did not produce the qualification disposition above.

## 4. Current boundary

- Qualification dispositions completed: Pair 0, A1, A2, A3 (`4/7`).
- Qualification not executed: A4, A5, A6.
- Solo Pair IDs: `0`.
- Solo Attempt IDs: `0`.
- Control/Treatment arm executions: `0`.
- Formal Gate 3 counted evidence: `0`.

This checkpoint does not authorize A4–A6 harness creation or execution, Solo
task execution, reconciliation with canonical runtime logs, memory updates, or
push. Future qualification work must retain the route-split claim ceiling.
