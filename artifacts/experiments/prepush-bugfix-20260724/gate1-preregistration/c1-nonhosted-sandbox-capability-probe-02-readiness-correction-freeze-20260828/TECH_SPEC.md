# Technical specification: Probe-02 readiness correction

## Observed failure

Probe-01 consumed its one owner-authorized pipeline invocation before an atomic
attempt claim because a fresh Git checkout did not materialize the empty
`gate1-execution` parent. No terminal, sandbox helper launch, control execution,
hosted request, auth read, qualification attempt, or randomization occurred.
Probe-01 is immutable and may not be repaired or retried.

## Correction

One Git-tracked anchor materializes the parent. `required_parent_roots` in the
manifest is the single machine-readable source for its path, provenance, type,
containment, reparse policy, expected children and write-evidence requirement.
No parallel Markdown checklist is authoritative.

The non-hosted readiness probe validates the exact commit and identity, checks
the parent and anchor, performs exclusive sentinel create, fsync, exact
readback and delete, and emits a bounded receipt without creating a formal
attempt claim. The receipt and a separate independent-review packet use fixed
repo-external paths. The formal streamed bootstrap accepts only the owner-bound
review-packet digest. The driver revalidates receipt, review, identity, anchor
and live parent projection before loading the verified Probe-01 engine.

The engine is loaded from its exact Git source binding, never the working tree.
Only the attempt id, manifest path and terminal enrichment are adapted. The
negative-control, absolute-Python control, sandbox argv, minimal environment,
CLI binding and cleanup logic remain the reviewed Probe-01 bytes.

## Ownership boundary

- Before atomic claim: failure consumes the pipeline authority but cannot emit
  a claimed-attempt terminal.
- After atomic claim: every bounded exception must produce one terminal.
- Concurrent loser: no cleanup, no terminal, no access to winner evidence.

## Two-execution stop rule

The observation window is Probe-02 plus Qualification-03. Intended-surface
requirements are explicit and machine evaluated. A failure category not in the
frozen allowlist becomes `NEW_UNMODELED_INFRASTRUCTURE` and immediately yields
`STOP_BEFORE_FURTHER_FORMAL_ATTEMPT`. Window expiry, time pressure and near-pass
claims cannot override the stop. Further formal attempts require a runtime
dependency inventory, an execution state-machine audit and a new owner decision.

## Claim ceiling

This freeze establishes reviewable implementation bytes and contracts only. It
does not establish readiness PASS, capability launchability, sandbox
qualification, execution convergence, randomization, or arm results.
