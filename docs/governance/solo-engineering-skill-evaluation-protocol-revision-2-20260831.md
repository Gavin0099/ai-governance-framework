# Solo Engineering Skill Evaluation Protocol — Revision 2

Status: **CANDIDATE / NOT ADOPTED / NO EXECUTION AUTHORITY**

Source: `docs/governance/solo-ledger-anonymization-revision-2-solo-profile-20260831.md`, SHA-256 `e0cd3d4fca39c37c9baad8b0ef2b976cdff910ce997b95c6b241e644e4178741`.

Sibling locators (not authority or hashes):

- Operations: `docs/governance/solo-evaluation-execution-contract-revision-2-20260831.md`, **Solo Evaluation Execution Contract — Revision 2**, normative §§3–11 (“Runtime and budget”–“R2 shakedown procedure”).
- Data/interfaces: `docs/governance/solo-attempt-ledger-v2-schema-implementation-contract-20260831.md`, **Solo Attempt Ledger v2 — Schema and Implementation Contract**, normative §§2–11 (“Files and identities”–“Conformance gates”).

A later owner-adoption record binds the three path/title/SHA-256/blob/commit identities.

## 1. Purpose and authority

**P01.** Question: should the owner keep the frozen Engineering Skill? Results are `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`: never effect estimates, Formal Gate 3 evidence, prior-evidence repair or authority to reopen provider research.

**P02.** No R2 Pair/Attempt precedes adoption of all three exact identities. Adoption authorizes neither implementation nor execution; each needs separate later authority.

**P03.** R2 prospectively supersedes the legacy protocol, execution contract and `solo_attempt_ledger.v1`; their bytes and evidence stay immutable.

## 2. Study, legacy and ceiling

**P04.** Slots: new non-analytic `R2-SHAKEDOWN` plus analytic A1–A6; A5 uses qualified ordinal 059 and forbids 058. Each Pair has CONTROL/TREATMENT and at most one canonical Attempt per arm.

**P05.** Legacy Pair `solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040` remains `PAIR_CREATED / 0 attempts` until adoption, then is permanently `PRE_ATTEMPT_TERMINATION`; never resumed/reused; no new v1 event. R2-SHAKEDOWN gets a new Pair ID, inherits no handle/label/order/controller state and must pass before any analytic Pair ID.

**P06.** Fixed N means initiated attempts. Ceiling: 14, two per slot; never raised.

## 3. Freeze, parity and blinding

**P07.** Pre-Pair freeze: task/category, Base/historical Fix, oracle/cases, scope, runtime, budget, tools/permissions, sole treatment difference, realized order, rubric and failure rules. Results never change selection.

**P08.** Only TREATMENT receives the exact frozen Skill packet; CONTROL receives none. All other task, snapshot, oracle, prompt, runtime, budget, tools, permissions and scoring inputs are equal.

**P09.** Realized order is controller-secret, pre-Pair frozen and absent from public, execution and scoring contexts.

**P10.** Both outputs finish before scoring. Labels/presentation order are independent of lifecycle handles/execution order. The scorer gets only identity-stripped outputs and rubric, cannot join them to Attempts; scores precede unblinding; public data cannot reveal CONTROL/TREATMENT.

## 4. Attempts and failures

**P11.** IDs are never deleted, reused, rebound, overwritten or silently replaced. Pre-ID infrastructure failure consumes none; task exposure initiates. Any later crash, timeout, abandonment, misuse, incorrect/no solution, regression, scope violation, excess cost or contamination stays its result. An admitted-but-unexposed ID stays reserved. STOP never retries. Retry/replacement/further shakedown needs a new revision-bound owner decision and preserves prior evidence.

**P12.** Use `SUCCESS`, `AGENT_FAILURE`, `HARNESS_FAILURE` or `UNCLASSIFIED`; count UNCLASSIFIED as assigned-arm AGENT_FAILURE. Harness failures stay visible.

## 5. Evaluation and decision

**P13.** Order: frozen oracle/cases; regression, build/type/lint/API/scope; cost; blind quality scoring. Human judgment is only for a frozen unresolved-dispute rule. Correctness/regression/scope outrank plausibility, size and cost. Report dispositions and per-arm attrition before identity reveal.

**P14.** Across A1–A6, `CONTINUE` iff (a) Treatment wins more, has no unique critical regression and no higher AGENT_FAILURE count; or (b) correctness/failure counts tie and Treatment improves at least two of elapsed time, tokens, review rounds. `STOP_USE` iff Control wins more, Treatment alone has a critical regression, or Treatment has more AGENT_FAILUREs. Else `INCONCLUSIVE`. Costs use paired medians; no per-category effect claim.

## 6. R2 shakedown

**P15.** R2-SHAKEDOWN proves freezing, isolation, oracle lifecycle, v2 ledger, anonymization, blind scoring and authenticated unblinding. PASS needs recorded fail-closed evidence for wrong key, package/tag corruption, wrong evaluation/Pair/artifact binding, premature unblinding and zero sentinel leakage into public Git/ledger/stdout/stderr/execution/scoring contexts. Failure stops before A1–A6.

## 7. Proportionality and stop

**P16.** Threat: controller error contaminating blind scoring, not third-party attack. Not claimed: durable nonce registry, custom byte-level JSON/Unicode protocol, ciphertext provenance, statistical cryptographic proof or protection from deliberate key use.

**P17.** After all five shakedown criteria pass, design expansion stops. Reopen cryptographic design only when published data actually recovers CONTROL/TREATMENT; missing hardening alone is insufficient.

## 8. Size and non-goals

**P18.** Maximum: 6,000 UTF-8 bytes, LF. No appendix, second protocol, contract, schema, validator or subsystem may carry study decisions to evade it. This protocol states what must hold; sibling contract/schema state how to operate/represent it.

This file creates no ledger, Pair, Attempt, implementation, score or unblinding; authorizes no adoption, execution, cleanup or push; changes no legacy evidence.
