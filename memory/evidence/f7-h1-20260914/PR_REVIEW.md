# H1 — canonical composed-hook support

Implementation commit: `c2198010c6bb181d250aa0161125b861051fdcab`.
Owner decision: publish H1 separately for PR review; merge is not authorized in this round.
DONE: the existing committed Lenovo composition is accepted by F-7 without accepting unknown hook edits or dropping its extension during hook replacement.

## Change and authority

The adapter recognizes the reviewed declaration/wiring/fragment from Lenovo consumer commit `3a4278c4bd2a18548b4920f2e999372be1834d44`. It checks HEAD/index/worktree provenance and reconstructs the entire expected hook; it does not execute the declaration scripts or expose a plugin API.
Unknown edits, missing declared extension and dirty/missing declaration sources remain refused. After a base update, the complete new composition is prepared before one atomic file replacement. Atomicity is per hook file, not all F-7 mutations.
Canonical fixture bytes are retained with narrowly scoped LF and trailing-blank-line attributes. `fixture-checkout-check.json` verifies exported fixture bytes under core.autocrlf=true.

## Validation and reviewer map

- `tests/test_composed_hook.py`: raw/declared acceptance, unknown/missing extension refusal, declaration provenance, gate failure propagation, base change, repeat stability, replacement failure and declaration-removal downgrade refusal.
- `final-targeted.xml`: 63 passed (focused composition, installer and the restored missing-source regression).
- `validation.json`: earlier broader related run had 150 passed, 1 failed, 1 skipped. The missing-source diagnostic failure was fixed and passed in the final focused run; this is not presented as a fresh all-green broad run.
- `pr-precommit.log`: `bash scripts/run-runtime-governance.sh --mode enforce` completed smoke and 201 tests; scope is the wrapper's suite, not every repository test.
- `base-fresh-update-check.json`: formal disposable F-7 advanced to local fixture base `8f076d6dd4979708b2dd62b1d6809cb823cbe7de`, full composition matched and extension count stayed one.
- `final-candidate-consumer-check.json`: final candidate accepted the updated composed hook, repeat install preserved bytes and mtime.
- `formal-f7-repeat-check.json`: second F-7 was blocked by the existing dirty receipt guard; hook bytes and mtime stayed unchanged. Full F-7 repeat success is not claimed.
- `pr-subject.json`: exact implementation and blob binding.

Review to date is author self-review and execution evidence, not independent approval. The shell tests use a test-only PowerShell shim for rejection propagation, not certification of the consumer validator. No real consumer update, adoption commit, runtime qualification, M1 behavior, R1 work or fleet claim.

Original raw replay reports and earlier response snapshots remain local-only in this evidence directory; the curated files named above are the PR evidence allowlist. The original dirty primary workspace and unrelated memory-policy candidates are excluded.

## Memory check boundary

The canonical writer produced daily, review-log and active-task records bound to the implementation commit. pr-memory-check.json reports the guard ran and no current blockers. Provenance and metadata advisories remain: logs under memory/evidence are review evidence, not formal admissibility or whole-memory completeness proof.
