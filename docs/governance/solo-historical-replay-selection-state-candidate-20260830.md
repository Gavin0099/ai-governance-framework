# Solo Historical Replay Selection-State Candidate

Status: **CANDIDATE / NOT ADOPTED / PRE-ID / QUALIFICATION NOT RUN**

## 1. Boundary

This artifact freezes the proposed source universe, eligibility rules, seven
historical replay tasks, exact oracle cases and the later qualification rule.
It does not create a Pair ID or Attempt ID and does not authorize an oracle
run, arm execution, task replacement or use of any result.

The controlling Solo protocol is commit
`5778fe230fc5581916240828a03edfdb9259c791`, blob
`cfb2624622d3c3ae56998091265cf8a396d9530a`, SHA-256
`0eb4561564edf1620038900f46c441b30204fb939499556c60fcc921822a00cf`,
anchor `Study configuration`. All results remain
`NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`.

## 2. Closed historical candidate universe

The source order is fixed as follows. Each row binds the repository name and
the reachable-history boundary used for reconstruction.

| Order | Repository | Pinned HEAD | Candidate count |
|---:|---|---|---:|
| 1 | `AITradeExecutor` | `36370f43e18d2dc82ce566d06b04a6a2a97e8277` | 1 |
| 2 | `Ashfall` | `0241d07beb8eb46b6e20d156de9405f050a403d0` | 5 |
| 3 | `Bookstore-Scraper` | `92210a321d4622e6a92763ed942e6a3545cf8125` | 19 |
| 4 | `english-vocab-trainer` | `eff02f731173dba14b493cbc929a28226cb551e4` | 26 |
| 5 | `Enumd` | `628ba60ed9254f87c21bebc362258e84eb08bee5` | 1 |
| 6 | `financial-pdf-reader` | `699f31591affa6dbeeb8026b89be8f6ae7f3b1d7` | 3 |
| 7 | `Hearth` | `90e7adb08bacb7f87f0837b1b6ff74e3e6358f3d` | 10 |
| 8 | `meiandraybook` | `d3bf324f4057ed862fe110223145d5dba7d3c966` | 26 |
| 9 | `Mirra` | `0d7e33168de9b416f863627b3f3f301a7b763419` | 0 |
| 10 | `ruiyi-life-map` | `59cd69f2e78f556af43383225f34f181271f7b5d` | 30 |
| 11 | `usb-if-hub-spec-reference` | `edaef1d035853dd7cdd6d22a238d2b227a763a59` | 7 |
| 12 | `ZoneTruth` | `31c50bc9264bdaf76c8b6ecde067b2541fefd33d` | 19 |

For each pinned history, take non-merge commits returned by `git log HEAD` in
its default order when the complete commit message matches, case-insensitively:

```text
(^|[^A-Za-z])(fix|bug|repair|regression|correct|resolve)([^A-Za-z]|$)
```

Retain a commit only if at least one changed path matches:

```text
(?i)(^|/)(tests?|__tests__|specs?)(/|$)|(^|/)(test_|.*[._-]test\.|.*[._-]spec\.)
```

The canonical compact sequence is exactly 147 UTF-8 lines, each formatted as
three-digit global ordinal, TAB, repository name, TAB, full commit SHA, LF.
Schema `ordinal-tab-repo-tab-commit-lf-v1` has:

- SHA-256: `dfd5460ee2654a0f4d07e40c5f447f04249e3feffcac8d101787dedd738c9963`
- bytes: `8,910`
- LF: `147`
- first row: `001<TAB>AITradeExecutor<TAB>cbf8f97c1c7aa94e1180c80c4b110e8542da33dc`
- last row: `147<TAB>ZoneTruth<TAB>837129ff6cb50b271340514d454aada7b9dc3ec0`

The earlier `c47656d8...` value described a richer uncommitted serialization.
It is provenance, not the canonical compact serialization above; the repository
order, pinned histories, filter and 147-candidate membership are unchanged.

`ai-governance-framework` is excluded from the source universe. A toolchain
filter never removes a historical candidate from this universe; it only marks
that candidate ineligible for the current execution environment.

## 3. Eligibility and category assignment

A task is eligible only when all of the following are established before any
Pair ID exists:

1. The historical fix is a natural, non-synthetic bug fix and has one parent.
2. The proposed base is exactly that parent.
3. Each designated oracle case asserts observable behavior through an interface
   present in both base and fix; it must not require the historical structure.
4. Exact fix-version oracle bytes can be applied unchanged to base and fix.
5. The parent snapshot, task wording, paths and visible fixtures contain no
   known solution-bearing historical diff, commit-message or partial-fix leak.
6. The toolchain required by the designated oracle files, not merely another
   toolchain at repository root, is available in the execution environment.
7. Expected arm performance, repository diversity and apparent task appeal do
   not affect selection or replacement.

Pair 0 is the first eligible simple task and is outside analytic categories.
Analytic tasks use the fixed categories below. When a task could fit more than
one description, apply the first specific description that is established by
pre-result historical evidence; `straightforward` is the fallback:

1. `specification ambiguity`: competing target interpretations must be resolved;
2. `root-cause analysis`: the visible symptom does not identify the causal parser
   or normalization defect;
3. `regression`: the historical evidence explicitly records a lost prior or
   already-intended behavior;
4. `cross-file change`: one behavior must remain consistent across multiple
   production adapters or surfaces;
5. `small over-engineering-prone bug`: a narrow guard or termination defect has
   a direct behavior oracle and does not require architecture expansion;
6. `straightforward fix`: a direct local input/output mismatch not classified
   above.

This category mapping supports aggregate comparison only. It cannot support a
per-category effect claim.

## 4. Frozen seven-task selection

| Slot | Category | Repository | Base | Historical fix |
|---|---|---|---|---|
| Pair 0 | shakedown/simple | `Bookstore-Scraper` | `e478409971dd8e72335966350fcfaee2a6cdb8b0` | `c9cd494bfa087a86d5e1c34702a2ad7997ad7b7b` |
| A1 | straightforward fix | `Bookstore-Scraper` | `6e673dc46457d469dd98e5993139194eceeb1211` | `56d1b82372a995fc07431b4583f43237092babf4` |
| A2 | root-cause analysis | `Hearth` | `861e304a5cf19492cc74b1a780b77c6bc1c68ae8` | `cf197f2d8275cb326ae9c8e1a1ae896116481e11` |
| A3 | regression | `english-vocab-trainer` | `04e320233efb6ad8d49bf80c59374918ee126bce` | `f1da14b857dc3fa8831215360f818f9600042c3e` |
| A4 | specification ambiguity | `Bookstore-Scraper` | `f3f5317e306bbab8173dc4cc356df4a38f4bdf7a` | `bc81cd50a93cb813352eb9c26beadabda8e54c6d` |
| A5 | cross-file change | `Hearth` | `61124b55e777357749beb82d3f724dec7978bdd2` | `1aacc03b69d06fc5bc965f509b18582f28e1892b` |
| A6 | small over-engineering-prone bug | `Bookstore-Scraper` | `675027485e762e4b457f1c1da7c61b6f6a065d81` | `218c73cd9898015372cac95b01cf34c5d64e328c` |

The natural-bug and category evidence is frozen as follows. Historical subjects
are selection evidence and must not be shown to future arms.

| Slot | Historical subject | Frozen behavioral task and category rationale |
|---|---|---|
| Pair 0 | `fix Grimm prices and validate Chinglin` | Parse comma-separated Grimm list/original prices without truncation; direct deterministic parser behavior makes this the shakedown/simple task. |
| A1 | `Fix schema availability normalization for TonyKids` | Treat the HTTP and HTTPS Schema.org `InStock` URI variants equivalently; a direct local normalization mismatch with one behavior case. |
| A2 | `Fix Sinopac insurance statement parsing` | Recover an inline insurance header and policy row through the existing exported parser; the visible missing record does not itself identify the section-boundary and policy-start root cause. |
| A3 | `fix(daily): lead every route with the reviewed child-friendly words` | Restore the already-intended reviewed-first day-one ordering in the real plan builder; the history explicitly records that helper coverage stayed green while product behavior regressed. |
| A4 | `fix(import): restrict secret-bearing write targets` | Reject arbitrary remote write targets before network activity; correctness depends on resolving the allowed `local`/exact-production/other-remote target semantics. |
| A5 | `fix(import): use posted date for all credit-card parsers` | Apply posted date consistently across the import endpoint and multiple bank parser surfaces; this is the cross-file consistency task. |
| A6 | `fix(holiu): stop repeated category page loops` | Stop when another category page contains no new products; a narrow termination guard is intentionally the over-engineering-prone task. |

Interpretation limitation: three analytic tasks come from `Bookstore-Scraper`,
two from `Hearth` and one from `english-vocab-trainer`. The aggregate result may
substantially reflect these repeatedly sampled codebases and is not a general
cross-repository effect estimate. Repository diversity is not a post-selection
replacement criterion.

## 5. Exact designated oracle cases

All test names below are required. A file blob is not authority to add another
case from the same file. Non-listed cases are outside the bug oracle.

### Pair 0 — Grimm thousands-separated prices

- File: `tests/test_scraper_regressions.py`
- Base blob: `1affc13898961fe1a09b85e90f8a39d3d9501d81`
- Oracle blob: `93ad7d9d56b1534bd180af83ba69ad23e64f3c6b`
- Required cases:
  - `test_grimm_parse_price_preserves_thousands_separator_value`
  - `test_grimm_parse_price_prefers_original_price_with_thousands_separator`
- Command: `./.venv/Scripts/python.exe -m pytest -q <file>::<case>` once per
  required case.

### A1 — TonyKids availability URI normalization

- File: `tests/test_scraper_regressions.py`
- Base blob: `286311330e2925477d35a7b41b227c059e002299`
- Oracle blob: `3349ede3fe8e7497204f0dd72d647629a33c7995`
- Required case: `test_tony_kids_schema_instock_accepts_http_uri_variant`
- Command: `./.venv/Scripts/python.exe -m pytest -q <file>::<case>`.

### A2 — Sinopac inline insurance section

- File: `apps/api/tests/pdf-credit-card.test.ts`
- Base blob: `4f9a7e401cd02aa6c93c0adb3a83c439c736f75c`
- Oracle blob: `66a04b07a46cae8143f3cfdf4c882ad28fd01e72`
- Required case: `parseSinopacInsuranceSection handles inline insurance header and policy rows`
- Command template:
  `node --test --import tsx --test-name-pattern="^<exact case>$" <file>`.

`parseSinopacInsuranceSection` exists and is exported at both base and fix; the
case does not depend on a fix-only symbol.

### A3 — real-route day-one ordering

- File: `src/lib/dailyLearning.test.ts`
- Base blob: `955be3ba122d7bec45f762a0f4562469e52b6a69`
- Oracle blob: `dac278c808d31093382b79737f1392d441bd379d`
- Required cases:
  - `shows reviewed words first on the Starters route`
  - `shows reviewed words first on the Movers route`
  - `shows reviewed words first on the cefr-a1 route`
  - `shows reviewed words first on the cefr-a2 route`
  - `shows reviewed words first on the gept-elementary route`
- Command template:
  `./node_modules/.bin/vitest.cmd run <file> -t "^<exact case>$"`.

The primary-school cases using fix-added `includeAllWords` and the phonics guard
are expressly excluded. The earlier candidate
`46f6e8b9e86fa8dfda82d299203f4b0e316e15ce` is excluded because its oracle
imports the fix-added path `scripts/lib/native-vocabulary-catalog-code.mjs`.

### A4 — remote write-target classification

- File: `tests/test_prepare_group_buy.py`
- Base blob: `c0c2d7acb49567ce7438c98fa86d576c0c8ffa0e`
- Oracle blob: `aeebf20e622e27a5b573016ab50158e71ddb2615`
- Required parametrized case:
  `test_arbitrary_remote_target_is_rejected_before_any_network`
- Required parameters:
  - `https://evil.example`
  - `https://meiandraybook.meiraybooks.workers.dev.evil.example`
- Command: `./.venv/Scripts/python.exe -m pytest -q <file>::<case>`; both
  parameter instances must execute.

The historical supporting blob
`48d87bde3a56335bcbf6a25a6eca904b3e0aaf2e` from
`tests/test_verify_production_handoff.py` is not a designated oracle. Its new
cases import fix-only `classify_write_target`; collection failure at base would
not be evidence of the bug. The designated case instead calls the stable
`_verify_production_target_before_write` behavior present in both revisions.

### A5 — posted date across credit-card import surfaces

- File: `apps/api/tests/auth-accounts.test.ts`
  - Base blob: `fc523412395cc3511902200f2e2b3240b3dca9a3`
  - Oracle blob: `e582f2ad2b4df9886f8981fd6aa3da76b6ecb97c`
- File: `apps/api/tests/pdf-credit-card.test.ts`
  - Base blob: `5cb1dd0011c8810a159a490b655ba2c54da1ae00`
  - Oracle blob: `b2f33040f0c0d9ed99f049b3e48b6af31935b1ab`
- Required cases:
  - `POST /api/import/credit-card-tw prefers posted date over transaction date`
  - `parseSinopacPdfTransactions handles purchases, cashback, installments, and ignores autopay`
  - `parseSinopacPdfTransactions keeps current installment amount when statement uses spaced colon and full-width digits`
  - `parseEsunPdfTransactions limits parsing to detail sections and handles cashback plus installment rows`
  - `parseTaishinPdfTransactions handles ROC full-date rows with trailing country code`
  - `parseTaishinPdfTransactions applies previous-year heuristic for MM/DD rows in early-year statements`
  - `parseCtbcPdfTransactions handles ROC full-date rows with amount before card suffix`
  - `parseCtbcPdfTransactions applies previous-year heuristic for MM/DD rows in early-year statements`
  - `parseCtbcPdfTransactions falls back to full-text scan when rows are not separated by newlines`
  - `parseMegaPdfTransactions handles full ROC year dates with fullwidth description on same line`
  - `parseMegaPdfTransactions handles description on adjacent line (date+amount row without description)`
  - `parseCtbcPdfTransactions recovers transaction rows from noisy token stream with cover-page summary fragments`
- Command template:
  `node --test --import tsx --test-name-pattern="^<exact case>$" <file>` once
  per required case.

Old transaction-date expectations in the parent file are not designated
oracle bytes. They remain equally visible to both arms and may point toward the
stale behavior; the frozen task expectation and agent-hidden fix-version oracle
control correctness. The exact blobs and case list above are the oracle.

### A6 — repeated category-page termination

- File: `tests/test_scraper_regressions.py`
- Base blob: `f859a91ee1c816df4d07a8259861623ce3e2fcc1`
- Oracle blob: `3596e257991e7150762b03fc1667e05ee28553e5`
- Required case: `test_holiu_stops_when_page_contains_no_new_products`
- Command: `./.venv/Scripts/python.exe -m pytest -q <file>::<case>`.

## 6. Current-environment executability evidence

The eligibility check is oracle-level and read-only. Observed tools are:

- `Bookstore-Scraper`: repo-local Python `3.12.13`, pytest `9.0.3`;
- `Hearth`: Node `24.13.0`, npm `11.6.2`, repo-local tsx `4.21.0`;
- `english-vocab-trainer`: Node `24.13.0`, npm `11.6.2`, repo-local Vitest
  `4.1.10`;
- `swift`: unavailable; `xcodebuild`: unavailable.

Therefore Swift/XCTest candidates remain in the 147-candidate universe but are
`INELIGIBLE_TOOLCHAIN` for this execution environment. This includes the former
ZoneTruth Pair 0/A4 proposals and the former english-vocab-trainer A3 whose
designated oracle was XCTest. Installing Swift is not part of this selection.

Tool availability is not oracle qualification. It must be rechecked before the
later qualification run; a mismatch is a harness stop, not a task failure.

## 7. Bidirectional oracle qualification rule

Qualification is a later, separately authorized slice. It must materialize base
and fix in isolated locations without modifying the consumer repositories. For
each task, place the exact fix-version oracle blob(s) at the listed path(s) in
both materializations and run the same listed command for each required case.

Every required case must satisfy both directions:

```text
base + exact oracle bytes -> FAIL at the expected behavioral assertion
fix  + exact oracle bytes -> PASS
```

The runner must prove that the exact named case executed. Zero-match, skipped,
collection, import, dependency, setup, timeout or tool failure is a harness
failure and is not a qualifying base failure. Unlisted cases cannot determine
qualification.

The required case set is not dynamically pruned. If any required case fails to
show the expected base behavioral failure or fails at fix, the entire task is
`NOT_QUALIFIED` and the slice must STOP. It may not select a replacement, create
a Pair ID or revise this artifact without a new revision-bound owner decision.

## 8. Leakage and claim ceiling

Future arm prompts and worktrees must not expose historical fix commit messages,
diffs, solution-bearing branch/tag names or the hidden oracle sources. Private
repository status only lowers training-contamination risk; risk remains unknown.

No task has been qualified by this artifact. No oracle was run. No Pair ID,
Attempt ID, ledger, Control arm or Treatment arm exists. The selection remains
a candidate until exact adoption and separate qualification authorization.
