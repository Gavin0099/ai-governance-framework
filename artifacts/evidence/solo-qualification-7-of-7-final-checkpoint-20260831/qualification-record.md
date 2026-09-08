# Solo Historical Replay Qualification — Final 7-of-7 Evidence Checkpoint

Date: 2026-08-31

Status: `QUALIFICATION_PHASE_CLOSED / 7 OF 7 VALID SLOTS QUALIFIED`

Track: `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`

## 1. Purpose and claim boundary

This checkpoint preserves the remaining qualification dispositions and the
instruments that produced them after the earlier 4-of-7 checkpoint. It records
the original A5/ordinal-058 negative result and the frozen-order replacement by
A5-prime/ordinal-059 rather than rewriting the history as an uninterrupted pass.

This record does **not** re-execute an oracle, recreate discarded raw runner
output, create a Pair ID or Attempt ID, authorize a Solo arm, or establish any
Formal Gate 3 evidence. The copied harnesses are evidence copies, not a harness
lifecycle migration or authorization to execute from this directory.

Frozen selection source:

- Commit: `c56b6258e4414d3c4699d9663da378674618224a`
- Blob: `d517fa6caacd95368d997802480d74162b709fcd`
- SHA-256: `3502f517b7c42300d5ae15e077b67acaa3d7379bc620a85efdf38a490e37d67c`
- Path: `docs/governance/solo-historical-replay-selection-state-candidate-20260830.md`

Prior evidence checkpoint:

- Commit: `49dcd8e5d9c2bcd699b22b18d8e30bc4aeafd136`
- Path: `artifacts/evidence/solo-qualification-4-of-7-checkpoint-20260830/`
- Preserved there: Pair 0, original A1 disposition, A2, A3 V2, and the three
  corresponding available instruments.

## 2. Preserved instrument manifest

Each file under `harnesses/` is a byte-exact copy of the instrument that
produced the stated disposition. Source and evidence-copy SHA-256 values were
checked for equality at checkpoint creation.

| Evidence copy | Source at checkpoint | SHA-256 | Bytes | LF | CR | BOM |
|---|---|---|---:|---:|---:|---|
| `harnesses/a1-repro-harness.ps1` | `.qualification_tmp/solo-20260830/a1-repro-harness.ps1` | `8a0629e8784c9b0c87e74f6b9e92b620f6c9fd539bc0a5fa7b157070f44b3ede` | 11,094 | 279 | 0 | no |
| `harnesses/a4-harness.ps1` | `.qualification_tmp/solo-20260830/a4-harness.ps1` | `30d27a4bc21c0993526a8a0c194b30b9b8fd6df985411b3f81e23c17789a5674` | 11,110 | 279 | 0 | no |
| `harnesses/a5-ordinal058-harness.ps1` | `.qualification_tmp/solo-20260830/a5-harness.ps1` | `161795dbf8ebdcb4bb8f34eee3064a2c2a8bb87ba0c41ec4a2f9b9ec00ebd6fa` | 19,771 | 445 | 0 | no |
| `harnesses/a5-prime-ordinal059-harness.ps1` | `.qualification_tmp/solo-20260830/a5-prime-ordinal059-harness.ps1` | `33b30461a85d7381eba20a9531f9f4d6de4ec5ab8292ec0b49da3a4c9151bc8a` | 18,026 | 434 | 0 | no |
| `harnesses/a6-harness.ps1` | `.qualification_tmp/solo-20260830/a6-harness.ps1` | `10fb725ed7c56e6aaf40354a0b729e6850d0e0f665a4759679d60fd873443f7d` | 10,955 | 278 | 0 | no |

## 3. Additional qualification dispositions

### A1 — reproducibility rerun — Bookstore-Scraper

- Base: `6e673dc46457d469dd98e5993139194eceeb1211`
- Historical fix: `56d1b82372a995fc07431b4583f43237092babf4`
- Oracle: `tests/test_scraper_regressions.py`
- Oracle blob: `3349ede3fe8e7497204f0dd72d647629a33c7995`
- Required case:
  - `test_tony_kids_schema_instock_accepts_http_uri_variant`
- Instrument SHA-256: `8a0629e8784c9b0c87e74f6b9e92b620f6c9fd539bc0a5fa7b157070f44b3ede`
- Observed Base result: 1/1 required case produced behavioral failure.
- Observed Fix result: 1/1 required case passed.
- Added disposition: `REPRODUCIBILITY_RERUN_QUALIFIED`.

This rerun supplements rather than overwrites the original A1 record. The
earlier `QUALIFIED / INSTRUMENT_NOT_DURABLY_CAPTURED` history remains true.

### A4 — specification ambiguity — Bookstore-Scraper

- Base: `f3f5317e306bbab8173dc4cc356df4a38f4bdf7a`
- Historical fix: `bc81cd50a93cb813352eb9c26beadabda8e54c6d`
- Oracle: `tests/test_prepare_group_buy.py`
- Oracle blob: `aeebf20e622e27a5b573016ab50158e71ddb2615`
- Required cases:
  - `test_arbitrary_remote_target_is_rejected_before_any_network[https://evil.example]`
  - `test_arbitrary_remote_target_is_rejected_before_any_network[https://meiandraybook.meiraybooks.workers.dev.evil.example]`
- Instrument SHA-256: `30d27a4bc21c0993526a8a0c194b30b9b8fd6df985411b3f81e23c17789a5674`
- Observed Base result: 2/2 required cases produced behavioral failure.
- Observed Fix result: 2/2 required cases passed.
- Accepted qualification disposition: `QUALIFIED`.

### A5/ordinal 058 — cross-file change — Hearth

- Base: `61124b55e777357749beb82d3f724dec7978bdd2`
- Historical fix: `1aacc03b69d06fc5bc965f509b18582f28e1892b`
- Oracle files/blobs:
  - `apps/api/tests/auth-accounts.test.ts` — `e582f2ad2b4df9886f8981fd6aa3da76b6ecb97c`
  - `apps/api/tests/pdf-credit-card.test.ts` — `b2f33040f0c0d9ed99f049b3e48b6af31935b1ab`
- Frozen required-case count: 12; the exact case set is embedded in the
  preserved instrument.
- Instrument SHA-256: `161795dbf8ebdcb4bb8f34eee3064a2c2a8bb87ba0c41ec4a2f9b9ec00ebd6fa`
- Decisive failing case:
  - `POST /api/import/credit-card-tw prefers posted date over transaction date`
- Exact contradiction: the fixture description `超商` is categorized by the
  historical fix implementation as `生活`, while the same fix-version oracle
  asserts `其他`.
- Observed Fix result: at least one frozen required case failed. Therefore the
  fix did not satisfy its own frozen oracle, and the complete no-pruning set
  could not meet the bidirectional rule.
- Accepted qualification disposition: `NOT_QUALIFIED`.

This negative result is retained permanently. It is task/oracle evidence, not a
harness failure, and it must not be rewritten as a pass after replacement.

### A5 replacement provenance — ordinal 058 to ordinal 059

Static selection did not reveal ordinal 058's fix/oracle contradiction. The
bidirectional rule exposed that the candidate did not satisfy the pre-existing
eligibility requirement that the oracle discriminate the historical defect and
be satisfied by the historical fix.

The owner explicitly reopened only the cross-file slot and required mechanical
continuation under the already frozen candidate order. The next candidate was
ordinal 059. No other slot was reopened, reordered, or chosen according to an
observed treatment/control outcome; Solo attempts were still zero.

### A5-prime/ordinal 059 — cross-file replacement — Hearth

- Base: `ae38c181d7445a2b5fa5313b6c6524117fd26a6c`
- Historical fix: `16be08713b406b27c0000bece08455542ab2d015`
- Oracle: `apps/api/tests/auth-accounts.test.ts`
- Oracle blob: `e671805702827d4685b7e36515287d3b61fd519d`
- Required cases:
  - `GET /api/portfolio/net-worth returns database_error when price snapshot lookup fails`
  - `GET /api/portfolio/fx-rates returns database_error when holdings lookup fails`
- Instrument SHA-256: `33b30461a85d7381eba20a9531f9f4d6de4ec5ab8292ec0b49da3a4c9151bc8a`
- Observed Base result: both required cases produced behavioral failure and
  each executed exactly once. The Base continued past the intended failed
  lookup into later database access rather than returning the required
  `database_error` response.
- Observed Fix result: both required cases passed and each executed exactly
  once.
- Workspace-resolution evidence: Base and Fix each resolved
  `@hearth/shared` inside their corresponding temporary snapshot roots.
- Harness exit: `0`.
- Accepted qualification disposition: `QUALIFIED`.

### A6 — over-engineering-prone — Bookstore-Scraper

- Base: `675027485e762e4b457f1c1da7c61b6f6a065d81`
- Historical fix: `218c73cd9898015372cac95b01cf34c5d64e328c`
- Oracle: `tests/test_scraper_regressions.py`
- Oracle blob: `3596e257991e7150762b03fc1667e05ee28553e5`
- Required case:
  - `test_holiu_stops_when_page_contains_no_new_products`
- Instrument SHA-256: `10fb725ed7c56e6aaf40354a0b729e6850d0e0f665a4759679d60fd873443f7d`
- Observed Base result: 1/1 required case produced behavioral failure.
- Observed Fix result: 1/1 required case passed.
- Accepted qualification disposition: `QUALIFIED`.

## 4. A3 superseded instruments excluded from this bundle

The following bytes are intentionally not copied into this final evidence
bundle because neither instrument produced the accepted A3 qualification:

- `6070786822dcd48c801a484fb86c4a1da174170eaa8e19d7c57d6b9b6cd6f809`:
  `SUPERSEDED / HARNESS_FAILURE / NOT_USED_FOR_FINAL_QUALIFICATION`. It had been
  frozen for an earlier attempt but failed before oracle execution.
- `b2223ed71fbc8e9c3a0c1b9852f33e3ec152c13dea7118ad33a59b2f8e05993d`:
  `NOT_ADOPTED / NOT_USED_FOR_QUALIFICATION`.

The accepted A3 instrument remains the V2 identity preserved by the prior
checkpoint: `4d44bd7d55c000460e082f3576550a3fc829417a67dc6bdef81a66ec063fe2a2`.

## 5. Final qualification rollup

| Slot | Final disposition | Durable instrument state |
|---|---|---|
| Pair 0 | `QUALIFIED` | Preserved by `49dcd8e5` |
| A1 | `QUALIFIED` + `REPRODUCIBILITY_RERUN_QUALIFIED` | Original limitation retained; rerun instrument preserved here |
| A2 | `QUALIFIED` | Preserved by `49dcd8e5`; contamination history retained there |
| A3 | `QUALIFIED` | V2 preserved by `49dcd8e5` |
| A4 | `QUALIFIED` | Preserved here |
| A5/058 | `NOT_QUALIFIED` | Negative candidate and instrument preserved here |
| A5-prime/059 | `QUALIFIED` | Replacement slot instrument preserved here |
| A6 | `QUALIFIED` | Preserved here |

Resulting state:

- Valid qualification slots satisfied: `7/7` (Pair 0 plus A1–A6, with
  ordinal 059 replacing rejected ordinal 058 in the A5 slot).
- Original candidates that were not qualified: `1` (A5/ordinal 058).
- Solo Pair IDs: `0`.
- Solo Attempt IDs: `0`.
- Control/Treatment arm executions: `0`.
- Formal Gate 3 counted evidence: `0`.

The qualification phase is closed. The Solo Evaluation phase is ready for a
separate owner decision but has not begun. This checkpoint does not authorize
Pair/Attempt creation, ledger creation, task execution, cleanup of
`.qualification_tmp`, memory updates, reconciliation, push, or any conversion
of Solo evidence into Formal Gate 3 evidence.
