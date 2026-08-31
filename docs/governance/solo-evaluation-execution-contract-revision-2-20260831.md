# Solo Evaluation Execution Contract — Revision 2

Status: **CANDIDATE / NOT ADOPTED / NO IMPLEMENTATION OR EXECUTION AUTHORITY**

Normative design source: `docs/governance/solo-ledger-anonymization-revision-2-solo-profile-20260831.md`, SHA-256 `e0cd3d4fca39c37c9baad8b0ef2b976cdff910ce997b95c6b241e644e4178741`.

Sibling locators (paths and titles only; not identity bindings):

- Study semantics: `docs/governance/solo-engineering-skill-evaluation-protocol-revision-2-20260831.md`, **Solo Engineering Skill Evaluation Protocol — Revision 2**, normative §§1–8 (“Purpose and authority”–“Size and non-goals”).
- Data/interfaces: `docs/governance/solo-attempt-ledger-v2-schema-implementation-contract-20260831.md`, **Solo Attempt Ledger v2 — Schema and Implementation Contract**, normative §§2–11 (“Files and identities”–“Conformance gates”).

A later owner-adoption record must bind all three exact path/title/SHA-256/blob/commit identities. This file specifies operations, not study decisions or ledger representation.

## 1. Scope and claim ceiling

This contract operationalizes the adopted protocol only after separate adoption, implementation and execution authorities exist. It creates no ledger, Pair, Attempt, snapshot, score or unblinding; changes no legacy evidence; and authorizes no execution, cleanup, commit or push.

## 2. Frozen evaluation inputs

The only slots are `R2-SHAKEDOWN` and analytic A1–A6. A5 uses qualified ordinal 059; ordinal 058 is forbidden. Each Pair binds the frozen category, repository, task, historical Base/Fix, oracle, required cases, qualification evidence and rubric. Results cannot alter selection or any frozen input.

## 3. Runtime and budget

**E01.** Both arms use model selector `gpt-5.6-sol` and reasoning effort `high`. Before exposure, record the runtime-reported model/build, Codex client and host identities; available values must match across arms. If no immutable backend build is exposed, record literal `UNAVAILABLE` and claim only selector, effort and exposed-identity equality. Any available mismatch is `PRE_ATTEMPT_INFRA_FAILURE / STOP`.

**E02.** Per arm: 1,800 seconds from task exposure; 60 top-level host-recorded tool calls; zero retry after terminal disposition; fresh context; no conversation reuse. Provider cache control is `UNAVAILABLE`, so cache equivalence is not claimed. No application-level prior-arm context or artifact may enter either arm.

## 4. Tools and permissions

**E03.** Both arms receive the same offline isolated consumer snapshot. Allowed: repository read/search, scoped editing, local shell, repository build/test/type/lint, read-only Git inspection of the snapshot, and diff/status of that arm's changes. Denied: network, web/connectors, package installation, credentials, secrets, subagents, external messaging, consumer-repository mutation, qualification artifacts, historical-fix refs/diffs/messages, hidden oracle bytes/results, controller state and the other arm's output. Writes are limited to the arm snapshot and designated temporary root. A prohibited-tool attempt after admission is recorded agent behavior, never a silent retry.

## 5. Sole treatment difference

**E04.** CONTROL receives no Skill packet. TREATMENT receives exactly one additional developer instruction after common baseline context and before the identical task prompt:

- path `artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md`;
- Git blob `a37320e37f587fc45f9fd5797d91bb9f2762ac71`;
- SHA-256 `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14`;
- `1,373 bytes / 24 LF / 0 CR`.

The packet is instruction-injected, not copied into the snapshot. Neither arm receives treatment-time validator output. Task, historical Base, visible files, oracle, prompt, runtime, budget, tools, permissions and scoring inputs remain equal. Any further difference is `ARM_PARITY_FAILURE / STOP`.

## 6. Controller order and isolation

**E05.** For every slot, read 32 bytes from the OS CSPRNG, compute `SHA-256(UTF8("solo-r2-arm-order-v1") || 0x00 || entropy)`, and use the low bit of its first byte (`0`: CONTROL then TREATMENT; `1`: TREATMENT then CONTROL). Seal the entropy, result and candidate Pair ID as `ORDER_FROZEN` before appending `PAIR_CREATED`. Later controller-state phases must retain them unchanged. Realized order/entropy are absent from public artifacts and execution/scoring contexts. RNG, digest or sealing failure is pre-Pair `CONTROLLER_ORDER_FAILURE / STOP`.

**E06.** Controller, execution and scoring are separate access domains. Only the controller may access key material and `sealed_controller_state`, create `blind_scoring_bundle`, or perform separately authorized unblinding. An execution context gets its arm snapshot and common task inputs only; it cannot access controller state, scoring bundles or the other arm. A fresh scoring context gets only the frozen rubric and `blind_scoring_bundle`; it cannot access key material, sealed state, lifecycle ledger, v1 disclosure context, controller conversation or execution chronology. Context roots and inherited environment must enforce these denials.

## 7. Admission and consumption

**E07.** Before Pair creation, validate frozen task/oracle/qualification identities, controller-secret order seal and the applicable protocol/schema authorities. Before an Attempt handle is generated, validate Pair binding, isolated snapshot, path/CWD containment, required executables, identical runtime/tool/permission/budget configuration, fresh context, writable v2 ledger, controller boundary and absence of task/hidden-oracle exposure. Failure before handle creation consumes no attempt and is `PRE_ATTEMPT_INFRA_FAILURE / STOP`. Admission order is: generate the opaque handle; durably append `ATTEMPT_ADMITTED`; expose the task; immediately append `TASK_EXPOSED`.

**E08.** Initiated-attempt consumption begins only at task exposure. A durably admitted handle whose exposure fails remains permanently reserved as `ADMITTED_NOT_EXPOSED / STOP` and does not count as initiated; it is never reused, deleted or rebound. Once exposed, the attempt counts against its slot and the total ceiling regardless of outcome.

## 8. Terminal handling

**E09.** After exposure, crash, timeout, abandonment, prohibited-tool use, incorrect/no solution, build/test failure, regression, scope violation, excessive cost, contamination or evaluator failure remains the canonical result. Classify only as `SUCCESS`, `AGENT_FAILURE`, `HARNESS_FAILURE` or `UNCLASSIFIED`; analytic accounting treats `UNCLASSIFIED` as assigned-arm `AGENT_FAILURE`. Append/fsync failure, identity mismatch, isolation breach, arm-parity uncertainty, oracle mutation or unclassifiable infrastructure state is fail-closed `STOP`. No STOP authorizes retry or replacement.

## 9. Evaluation procedure

**E10.** Apply the same frozen oracle and required cases to both outputs, then regression, build/type/lint/API and allowed-scope checks, cost capture, and blind quality scoring in that order. Record observable correctness, required-case counts, regressions, scope compliance and frozen cost metrics. Cost includes elapsed milliseconds, tokens when exposed, top-level tool calls and review rounds. Controller evidence records an unavailable host metric as literal `UNAVAILABLE`; public v2 emits only the available non-negative numeric fields permitted by its closed schema. No plausibility judgment overrides oracle, regression or scope evidence; no oracle or metric definition changes after results.

## 10. Blind scoring workflow

**E11.** Both Pair outputs must be terminal before scoring preparation. The controller strips every lifecycle/Git join field, creates independent opaque presentation keys and presentation order, and seals the mapping as specified by the ledger contract. The fresh scorer receives only the two identity-stripped outputs and frozen rubric in `blind_scoring_bundle`. It submits both scores before any unblinding request. Scoring lifecycle events are Pair-level. Unblinding is a later explicit controller operation requiring separate authority and authenticated opening; premature requests are `PREMATURE_UNBLINDING / STOP` without mapping disclosure.

## 11. R2 shakedown procedure

**E12.** Before any A1–A6 Pair ID, execute one new `R2-SHAKEDOWN` Pair through admission, both arms, oracle lifecycle, v2 ledger, bundle preparation, blind scoring and authorized authenticated unblinding. Retain fail-closed evidence for wrong key, package/tag corruption, wrong evaluation/Pair/artifact binding and premature unblinding, plus a zero-occurrence sentinel check across public Git/ledger, stdout/stderr and all execution/scoring contexts. Also verify v1 bytes remain unchanged and no public data joins scoring identity to an Attempt or arm. Any failure stops before A1; no replacement shakedown exists without a new revision-bound owner decision.

This candidate retains the Solo threat model and limitations in the protocol/design source. It does not add nonce durability, a custom byte-level serialization protocol, third-party cryptographic claims or another study rule.
