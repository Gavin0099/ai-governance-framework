# Shared closeout ownership: R2 v1

## Coverage and deployment boundary

Only `governance_tools.session_closeout_entry.main()` is the protected formal
receipt-producing entry. It requires an existing qualified R1 v1.1 session
and prepared R2 owner. Missing ownership rejects before the pipeline; no legacy
fallback is provided. Merging this code does not authorize consumer activation.
Existing installers and smoke producers do not implicitly create R2 ownership.

`run()`, direct `session_end_hook` / runtime-core calls, `scripts/run_closeout.ps1`,
`closeout.ps1`, and `processed_closeout_check` remain legacy/unprotected.
Arbitrary filesystem writers are outside this cooperative correctness contract.
Candidate preparation, summary generation, SessionStart installation, gate policy,
promotion and consumer activation are not implemented by R2.

## API and persistent state

`execution_exclusion(consumer_root)` verifies the Git worktree root and yields a
process/thread-scoped lease. Windows uses a nonblocking OS byte-range lock;
POSIX uses a nonblocking advisory flock. Failure rejects; no local-mutex fallback.
The lock file is neither truncated nor deleted. Process exit releases execution
exclusion, never persistent ownership.

Under the same lease:

1. `acquire_owner(lease, session_id, candidate_identity, text_digest)` reserves
   an append-only candidate path/hash and matching text hash, increments generation
   and atomically publishes `HOLD / preparation_pending` before payload writes.
2. The caller writes candidate and text from its inputs. R2 authors neither.
3. `confirm_prepared(lease, session_id, generation)` verifies latest candidate,
   exact payload bytes and R1 session binding, then publishes `OWNED`.
4. Protected main calls `begin_closeout` before its first shared-text read.
   This reserves a timestamp-sortable exact receipt identity and publishes
   `HOLD / closeout_pending`. The same OS lease spans the entire pipeline.
5. Receipt publication is atomic, schema-validated and read back. Finalization
   verifies completion, exact reserved receipt, payload hashes and full receipt
   SHA256; publishes an immutable release record, then `RELEASED` owner with
   read-back. Only then may another session acquire ownership.

Storage is under `artifacts/runtime/shared-closeout/`: `execution.lock`,
`owner.json`, `releases/<generation>.json`. Candidate paths are session-scoped
under `artifacts/runtime/closeout_candidates/`; text remains the shared
`artifacts/session-closeout.txt`. Path redirection and escaping are rejected.

A same-session unconsumed preparation retry must reserve a new candidate;
previous candidates are never changed or deleted. Another session cannot take
an OWNED/HOLD generation. Consumed sessions cannot prepare again.

Initial adoption requires no shared text, unexplained ownership/release artifacts,
or active/orphan/incomplete lifecycle evidence. The bounded inventory covers
sessions, candidates, closeout candidates, completions, closeouts, curated,
summaries, verdicts, traces and receipts. Unknown states are not implicitly FREE.
There is no automatic cleanup or migration.

## Receipt compatibility

Outer receipt schema stays v1.5. Optional strict `r2_binding` records extension
schema v1.0, consumer root, session ID, positive integer generation, candidate
path/SHA256, expected text digest and reserved receipt identity. It is forbidden
on earlier outer versions. Legacy receipts omit it and remain schema-valid.
Text digest is not the SHA256 of the complete published receipt.

The reserved name uses `closeout_receipt_<UTC timestamp>_r2_<UUID>.json`, preserving
existing timestamp-based latest-receipt ordering without changing those readers.

## Crash recovery

Completion is not release. Gate blocked is not ownership failure: a completed
pipeline with a fully published valid receipt can release ownership, without
changing whether its evidence is admissible.

If receipt publication succeeds but release is interrupted, the owner stays HOLD.
Use only the explicitly reserved identity:

```text
python -m governance_tools.shared_closeout_ownership reconcile-release --consumer-root <root> --session-id <id> --generation <generation> --receipt-identity <reserved-id>
```

Reconciliation holds the same OS exclusion, checks current owner/session/generation,
completion, reserved receipt schema/binding/checksum and retained payloads. It
never scans for a latest receipt, reruns closeout, regenerates summaries, or resets
completion. An already-published exact release record is reused unchanged; a
conflicting record rejects. Exact already-RELEASED reconciliation is idempotent.
Missing/partial/malformed receipt or mismatched ownership remains fail-closed.

Publication guarantees atomic visibility and process-crash recovery, not power-loss
durability or protection against hostile filesystem writers. Windows and POSIX
backends require separate platform evidence; local Windows tests do not qualify
POSIX or native host lifecycle activation.

## Observed manual-fallback compatibility limit

The existing receipt writer does not emit the seven output-mode/enforcement fields
already required by v1.5 for `trigger_mode=manual_fallback`. Protected main rejects this trigger before acquiring the OS lock, changing
ownership or entering the pipeline. The prepared session stays unconsumed and
its artifact bytes remain unchanged. Direct legacy receipt writer behavior is unchanged. R2 does not fabricate those fields or relax
the schema. Manual-fallback success is not qualified by this slice; this is a
separate delivery decision before activating that path. Synthetic/native-mode
fixture success does not qualify manual fallback.
