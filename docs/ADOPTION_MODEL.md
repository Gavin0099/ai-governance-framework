# Adoption Model — Consumer Role Taxonomy

This document classifies *consumer roles* before any tooling question is
asked. The governing rule:

> **Classification must precede tooling.** A consumer's role determines its
> automation ceiling and its evidence duty. No update tooling may be
> designed, extended, or claimed for a consumer class that has not been
> classified with evidence.

This exists to prevent a specific failure mode: seeing the words "F-7",
"adoption", or "consumer" and assuming every repository can receive the
same tooling at full rollout. It cannot. The F-7 updater scope overreach
this rule guards against is documented in PLAN.md.

Alignment: these consumer roles are the adoption-facing view of the P1-I
scope taxonomy (PLAN.md, "Scope taxonomy"). Scope sets are defined by
evidence duty; membership in one set implies nothing about the others.
If this document and PLAN.md disagree, PLAN.md wins.

## Consumer classes

### 1. Submodule consumer

Consumes the framework as a git submodule, without managed updates.

| Aspect | Definition |
|---|---|
| Required evidence | `framework.lock` / submodule pointer currentness |
| Allowed claims | "Pointer at framework commit X"; structural presence of governance files |
| Prohibited claims | "Updated" or "full update completed" from a pointer-only change (the exact inflation F-7 exists to prevent); any per-update verification claim |
| Upgrade path | → F-7 consumer, via managed F-7 onboarding plus per-update verification evidence |

### 2. F-7 consumer (subset of submodule consumers)

Submodule consumer whose updates run through the managed F-7 update
contract.

| Aspect | Definition |
|---|---|
| Required evidence | Per-update F-7 verification evidence: apply evidence, advisory hooks present, AGENTS routing, closeout receipt |
| Allowed claims | `full_update_completed` for a specific update with bound evidence; post-apply verified state |
| Prohibited claims | Fleet rollout completion or consumer generality from any single consumer's evidence (one slice, one evidence) |
| Upgrade path | Terminal for the submodule path |

### 3. External contract repo

Consumes governance *contracts* (contract.yaml, rules, validators), not
the framework codebase.

| Aspect | Definition |
|---|---|
| Required evidence | Contract validation evidence (validator runs, fixtures) |
| Allowed claims | Contract conformance at a validated commit |
| Prohibited claims | Runtime governance, hook enforcement, or framework-currentness claims — contract conformance is not runtime adoption |
| Upgrade path | Independent axis; a repo may also be a fleet or submodule member, but each role carries its own evidence duty |

### 4. Copy-based (audit-only)

Has copied framework files into its tree instead of consuming a submodule.

> **Naming guard**: this class is supported for *classification and audit
> wording only* — **not** automatic full-update execution. Do not read
> "audit-only" support as "copy-based consumers are supported". Automated
> update for copy-based consumers is **unsupported** (zero consumer
> evidence exists; claim ceiling: not solved).

| Aspect | Definition |
|---|---|
| Required evidence | Provenance audit: which files were copied, from which framework commit, with drift inventory against that commit |
| Allowed claims | "Copy detected, audited against framework commit X, drift inventory attached" |
| Prohibited claims | "Supported", "current", "governed", any update-automation claim, any currentness claim without a fresh audit |
| Upgrade path | Migrate to submodule consumer — the only path to managed updates. No copy-based update tooling will be designed before a classified copy-based consumer with audit evidence exists |

### 5. Unsupported / unknown

Any repository not classified into classes 1–4.

| Aspect | Definition |
|---|---|
| Required evidence | None admissible — classification is the prerequisite |
| Allowed claims | None |
| Prohibited claims | All adoption, governance, and currentness claims |
| Upgrade path | Classify first (read-only diagnosis), then enter the appropriate class with its evidence duty |

## How to use this taxonomy

1. **Before onboarding**: classify the target repo read-only. If
   classification is ambiguous, stop at diagnosis — a classification slice
   must not silently become a remediation slice.
2. **Before claiming**: check the class's allowed/prohibited claims. The
   automation ceiling is the class's, not the tooling's.
3. **Before building tooling**: a class with no classified consumer
   evidence gets no tooling. Failure-driven, not speculative.
