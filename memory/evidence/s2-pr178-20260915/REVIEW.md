# S2 PR178 resolution and standalone upgrade

Owner authorized the bounded S2 execution after PR181 delivery. Base is
`a743d2e19a4101cbbb82ea33bff95286f721b358`; original PR head is
`663d13d2a5bb5e241e7879f864b9d2ebff26ff14`.

DONE: the declared Lenovo composition can upgrade through the standalone
installer as well as the existing F-7 hook path, while unknown changes remain
refused. This is an engineering merge scope, not consumer qualification.

## Finding and correction

The original P2 is introduced by PR178 and blocks its advertised standalone
upgrade support. `reproduction.log` records the direct-upgrade failure before
the fix. The new acceptance path requires exact full composition equality with
a hook blob reachable from the selected framework checkout's HEAD, using the
already validated committed consumer fragment. Other refs and parent-repo
history are not used. Missing historical proof remains a refusal.

No marker-only allowance, declaration relaxation, new manifest/schema, gate
relaxation, or consumer-script execution is introduced. Per-file atomic writes
remain unchanged. The original updater implementation and its pre-update
mutation checks remain in place.

## Validation

- `python -m pytest tests/test_composed_hook.py tests/test_hook_installer.py tests/test_external_governance_submodule_updater.py::test_apply_does_not_complete_when_hook_advisory_source_missing -q`: 70 passed; `targeted-tests.xml`.
- Candidate-root `bash scripts/run-runtime-governance.sh --mode enforce`: runtime smoke PASS, 201 passed; `precommit.log`.
- Direct standalone function and real CLI upgrade match independently constructed complete hook bytes; second install preserves bytes/mtime.
- Unknown extra content, removed extension, changed framework gate, absent history and unrelated-branch history remain refused.
- Existing tests cover F-7 mutation guard, hook refresh, atomic replacement failure, declaration provenance, and each gate's rejection propagation.
- `resolution.json`: all three conflicted memory files retain complete main contents and original PR-only appended records.

The earlier full disposable F-7 reports under `memory/evidence/f7-h1-20260914/`
remain historical. They are not described as newly rerun consumer qualification.
The current tests establish scoped installer/updater behavior; no production
consumer update, native lifecycle activation, fleet qualification, or full F-7
repeat-success claim is made. Source archives/shallow history may require
retrieving the old framework history before standalone upgrade can proceed.

Author-process review found no remaining blocker in this correction. Independent
review and remote checks must target the final pushed HEAD before merge. Exact
HEAD owner merge attestation remains a separate gate. Original dirty workspace,
managed SessionStart integration, S3 disposition and S4 cleanup are excluded.
