# G4 Manual Work-Item Case 002 - Independent Adoption Verification (HBPlus.Avalonia)

Event date: 2026-06-25
Record written: 2026-08-06 (retrospective; see Recording Boundary)
Repository: `hbplus.avalonia` (HBPlus.Avalonia)
Developer: Standy (`standy.huang`) — **not a framework author**
Work item: determine whether the governance framework was actually adopted in
this repo, rather than merely present as files
Classification: independent non-author consumer case; governance domain
Case status: outcome observed for this work item
G4 status: NOT ACHIEVED

## Plain-Language Result

A developer who did not write the framework adopted it into his own repo, then
independently asked whether the adoption was real rather than nominal. He re-ran
the official adoption tool, wrote a 131-line verification report, and recorded
17/17 drift checks passing — while in the same report documenting three limits
showing the runtime layer could not execute standalone in his environment.

Six weeks later the framework independently named a **related** gap — surfaces
present but enforcement absent — as the stated premise of its own PR #24
remediation. Related, not identical: see "Related Adoption-Surface Findings".

This is one independent, non-author governance-domain case. It is not proof of
transfer, sustained benefit, or that governance benefit exceeds its cost. It is
also not evidence of multi-observer convergence on a single defect.

## Recording Boundary

This record was written on 2026-08-06 from repository evidence, six weeks after
the events. Nothing here was observed live by the framework owner at the time.
Every claim below is anchored to a commit, file, or memory record that exists in
the consumer repository and can be re-read independently. Where a claim rests on
testimony rather than an artifact, it is labelled.

## Work-Item Boundary

This case groups one causal chain — "is this adoption real?" — as a single work
item:

- the initial thin adoption and the runtime-hooks copy (2026-06-24),
- their removal during submodule conversion (2026-06-25),
- the re-run of the official adoption tool and the verification report
  (2026-06-25),
- the decision not to re-adopt the runtime hooks (2026-07-08), which cites the
  same limits the report recorded.

It does **not** count each commit, each memory record, or each session as a
separate G4 sample. The 2026-07-08 native-callback engineering work is a
different work item and is recorded separately as Case 003.

Start condition:

- The repo was adopted on 2026-06-24 via thin adoption (`397c59b`), with
  2,915 lines of `runtime_hooks/core/*.py` copied into the repo (`4d2c504`).
- No independent verification existed that adoption was functional rather than
  file-present.

End condition:

- A durable verification report concluded adoption was correct per official
  documentation, and in the same document recorded the runtime-execution limits
  that the drift checker did not surface.
- **Thirteen days later** (2026-07-08) the same limits were cited, unprompted,
  to decline an action that would have satisfied a CI warning without adding
  enforcement.

## Evidence Chain

| Stage | Observed evidence | Boundary |
|---|---|---|
| Adoption attempt 1 | `397c59b` (2026-06-24) "Adopt ai-governance-framework baseline"; `4d2c504` same day copies 2,915 lines of `runtime_hooks/core/*.py` into the repo | Proves adoption occurred; proves nothing about whether it functioned |
| Correction | `2ff8b65` (2026-06-25) "adopt AI governance framework as submodule consumer" — the same commit **removes** the copied runtime hooks | The re-adoption one day later is the observable signal that attempt 1 was judged insufficient |
| Verification artifact | `7eb19e4` (2026-06-25) adds **`doc/research/governance-import-test-report-2026-06-25.md`** (historical path), 131 lines, written in the developer's own language. Renamed to its **current path `doc/report/governance-import-test-report-2026-06-25.md`** by `e6d4ffd` (2026-07-22, `R100`, content unchanged) | A self-authored verification record, not a tool output. Both paths are recorded because the historical path is the one `7eb19e4` can be checked against |
| Positive result recorded | Report §5: `governance_drift_checker` `ok=True`, 17/17 PASS, all checks enumerated; framework pytest 209 passed / 3170 deselected | Tool results as recorded in the report; not re-executed for this case record |
| **Negative result recorded in the same report** | Report §6, three limits: (1) `governance_tools` is not self-contained — `python -m governance_tools.*` raises `ModuleNotFoundError` without the framework root on `PYTHONPATH`; (2) `runtime_hooks/core/*.py` cannot execute standalone, needing the framework's `governance_tools` and `runtime_injection_snapshot.v0.yaml`; (3) `framework_version` reports `<unknown>` | This is the load-bearing evidence: a passing adoption verdict and a documented non-functional runtime layer, in one artifact |
| Downstream decision effect | `memory/2026-07-08.md`, first record: declines to copy `runtime_hooks/core/{session_start,pre_task_check,post_task_check}.py` because the framework ships adapters for claude_code/codex/gemini/hermes and none for VS Code Copilot Chat, so copying "would only silence the CI drift-checker expansion_boundary warning without providing any real runtime enforcement in this harness" | An independent developer identifying and refusing a compliance-theater action, with the reasoning recorded durably |
| Claim discipline without supervision | That same record is self-marked `commit: UNCOMMITTED`, `memory_binding: unbound` | No fabricated commit anchor for work that was not committed |
| Sustained use after the case | 21 dated memory files spanning 2026-06-29 to 2026-08-05; 81 session-derived records; 75 bound / 6 unbound | Establishes the adoption persisted; does not by itself establish benefit |

## Correlation With Framework Change

Between 2026-07-01 and 2026-07-03 the framework produced a dense burst of
adoption-reporting changes, including user-facing maturity status, "require
adoption status in governance update reports", the adoption feature table and
its localization, "require human adoption summary in update reports", onboard
adoption reporting, and on 2026-07-03 `45c6f494` "expose adoption table rows in
update JSON".

The framework's own memory for 2026-07-01/02 states the purpose as making
adoption completeness visible "so consuming repos can see report-only adoption
completeness signals during AI Governance adoption/update flows".

**Causal boundary — this is the weakest link in this record.** The timing is
consistent, the stated purpose is consistent, and the framework owner attests
that this consumer's adoption difficulty prompted the change. But **no framework
memory record, commit message, or design note names this consumer as the
trigger**. The causal claim therefore rests on owner testimony, not on a durable
artifact.

This is itself a finding. `memory/00_long_term.md` step 2 of the consumer-driven
loop requires recording the observed problem and its practical impact *before*
proposing a fix. That step was not performed for this change, which is why the
causal link had to be reconstructed from memory six weeks later.

## Related Adoption-Surface Findings

**Four evidence paths identified related adoption-surface failures. They do not
represent four independent observers, and they are not one identical defect.**
An earlier draft of this record claimed both; that claim is withdrawn.

The **evidence chain as a whole** surfaces three related problems. They come
from three different places and must not be attributed to one source:

| # | Problem | Nature | **Source** |
|---|---|---|---|
| A | Governance tooling is not invocable from a consumer root — `python -m governance_tools.*` raises `ModuleNotFoundError` unless the framework root is on `PYTHONPATH`; and `runtime_hooks/core/*.py` cannot execute standalone, needing the framework's `governance_tools` and `runtime_injection_snapshot.v0.yaml` | Packaging / topology | **Report §6.1–6.2** |
| B | No VS Code Copilot Chat adapter exists, so copying `runtime_hooks/core/*.py` would silence a CI warning without adding enforcement in this harness | Missing platform support | **`memory/2026-07-08.md`, first record** — *not* the report |
| C | Drift checks pass 17/17 while the runtime layer is non-functional | Detector-without-consequence | **Reviewer synthesis of report §5 + §6** — this framing is not stated in the report itself |

The report's §6 also records a third limitation not carried into the table
above because nothing downstream depends on it: **`framework_version` reports
`<unknown>`** (§6.3), which the report notes does not affect any check verdict.
It is listed here so this record does not silently drop part of its own source.

The four evidence paths and what each does and does not establish:

| Path | Date | Relates to | Boundary |
|---|---|---|---|
| This case (HBPlus evidence chain: report §5–§6 + `memory/2026-07-08.md`) | 2026-06-25 onward | A, B, C | The only path here authored by a non-author of the framework |
| Three-repo adoption analysis (Zephyr / CFU / gl_sdk), P0-2 "統一 Submodule-aware CLI" | 2026-08-06 | A | **Same 2026-08-06 investigation as the row below** |
| Framework-side source verification (`governance_tools` has no `__init__.py` / `__main__.py`; `run_first_import_validation.py` holds two contradictory topology assumptions) | 2026-08-06 | A | This was a verification *of* the row above, not a separate observation. The two together count as **one** investigation |
| PR #24 premise (`docs/enforcement-chain-gaps-2026-08-05.md`) | 2026-08-05 | C only | A separate framework remediation. Establishes that a gap exists between a detector and any consequence. It does **not** establish that this gap is the `PYTHONPATH` / submodule topology problem |

Corrected count: **two separately dated evidence lines** — this consumer case
(2026-06-25) and the framework-side 2026-08-06 investigation — plus a separate
framework remediation (PR #24) addressing problem C.

"Separately dated" is deliberately weaker than "independent". **Only the HBPlus
line is established as an independent non-author case.** There is no evidence
that the 2026-08-06 investigation was unaware of, or uninfluenced by, the HBPlus
result; the framework owner had access to both. Absent that evidence, the two
lines cannot be called independent of each other, and this record makes no such
claim. The same applies to PR #24: it is dated earlier, but its causal
independence from the HBPlus material is not established.

What survives: problem A was recorded by a non-author six weeks before the
framework's own investigation reached it. That remains a real and useful signal.
What does not survive: any claim of four-way convergence, or of multiple
mutually independent observers.

## Owner Interventions

| Item | Status |
|---|---|
| Live guidance from the framework owner during this work | **None — owner attestation, Gavin, 2026-08-06.** Git history can show independent authorship; it cannot prove the absence of side-channel help. Treat as testimony. |
| Consumer developer informed that this work is being recorded as G4 evidence | Yes — confirmed by the framework owner, 2026-08-06 |
| Owner corrections to the consumer's conclusions | None recorded |

## Observable Cost

| Measure | Value | Boundary |
|---|---|---|
| Adoption attempts | 2 (thin, then submodule) within 2 days | Countable |
| Code churn from the failed first approach | 2,915 lines added then removed | Countable |
| Verification artifact | 131 lines, self-authored | Countable |
| Elapsed span of the causal chain | 2026-06-24 to 2026-07-08 | Countable |
| Human minutes | **Not measured** | Cannot compare |
| Tokens | **Not measured** | Cannot compare |
| Rework baseline (what this would have cost without governance) | **Not available** | No counterfactual |

Benefit-over-cost therefore remains unestablished, as in Case 001.

## Outcome And Recurrence

Outcome: adoption was verified rather than assumed, the non-functional runtime
surface was documented rather than papered over, and the documented reasoning
prevented a later compliance-theater action.

Recurrence: a 2026-08-06 external analysis reported related findings in three
repositories (Zephyr, CFU, gl_sdk). **This case did not independently revalidate
those repositories and does not establish that the defect remains open in them.**
No durable per-repository reference (report path, commit, or evidence artifact)
is recorded here, so the three-repository claim is reported second-hand and must
not be counted as verified recurrence until such references exist.

What is verified in this repository: the consumer-side mitigation — adding the
framework root to `PYTHONPATH`, or invoking from the framework checkout rather
than the consumer root — is a workaround, not a fix. The module-invocation form
(`python -m governance_tools.*`) is **not** a mitigation here: report §6.1
records that it still raises `ModuleNotFoundError` when run from the consumer
root. It works only from the framework checkout, where the framework root is
already the working directory.

## Transfer Gap

- One independent developer, one repository, one agent surface (VS Code Copilot
  Chat). This does not establish transfer.
- The consumer's environment differs from the framework author's in a way the
  framework does not support: **there is no VS Code Copilot Chat adapter.**
  Static adoption persisted, and the framework's official adoption and drift
  validation did work — what was not established is **runtime enforcement for
  this agent surface**.
- No second non-author has been observed.

## Known Limitation Of The Current Checkout

At the time of writing, the consumer repository's framework submodule checkout
is `737fcd48` (2026-06-24) while the parent-recorded pin is `048201c`
(2026-07-15) — the checkout is **821 commits behind the pin**. This is a stale
checkout that never advanced, not an uncommitted forward update.

Consequence for this record: for consumer memory records dated after
2026-07-15, which framework version was actually in effect is ambiguous. The
evidence used in this case is all dated 2026-06-25 to 2026-07-08, before the pin
date, so it is unaffected. Any future case drawing on later records must
establish the effective checkout first.

## G4 Contribution And Claim Ceiling

Contributes:

- The first **independent non-author** case in this project's G4 record.
- A second consumer owner, and a new agent surface (VS Code Copilot Chat).
- A governance-domain outcome, not only a product-domain one.
- One non-author observation of an adoption-surface problem (A) recorded six
  weeks before the framework's own investigation reached it.

Does not contribute:

- Comparable cost. Human time, tokens, and a rework baseline are all absent.
- Proof of causation for the 2026-07-01/03 framework change; that is testimony.
- Transfer, sustained comparability, or benefit-over-cost.
- **Multi-observer convergence.** There are two separately dated evidence
  lines, not four, they address related but distinct problems, and their
  independence *from each other* is not established — only the HBPlus line is
  established as an independent non-author case.
- **Verified cross-repository recurrence.** The three-repository report is
  second-hand here and was not revalidated.

Supportable scope of this case, stated plainly: **the first recorded
independent non-author case — one developer, one repository, one agent
surface.**

**G4 remains NOT ACHIEVED.** What changes is that the independence axis is no
longer zero. It is one.

## Next Observation

1. Record the observed problem *before* the next framework change, so causal
   links do not have to be reconstructed. This case exists because that step was
   skipped once already.
2. If a VS Code Copilot Chat adapter is ever built, this consumer is the natural
   replay site — and the replay would be the first real transfer test.
3. Do not build measurement tooling to strengthen this record. The missing
   pieces are cost measurement and a second non-author, neither of which a new
   schema, ledger, or dashboard can produce.
