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

## Current correction after independent review of 323b2af7

Three introduced P2 findings block the prior candidate: replacement refs could
authorize unrelated framework objects; simplified history missed a merged side
base; installer-only unsupported profiles could fall back to raw installation.
All three were reproduced (`round2-reproduction.log`) and corrected together.
The adjacent consumer HEAD check also reproduced replacement-ref masking of an
uncommitted declaration (`consumer-replacement-reproduction.log`) and now ignores
replacement objects. The changes preserve full-content matching and pinned
declaration validation.

Latest complete-source run: the same targeted command above passed **74 tests**
(`final-tests.xml`); candidate-root precommit passed smoke and **201 tests**
(`final-precommit.log`). The earlier 70-test run and 323b2af7 CI are historical.
Independent re-review and CI must target the new final pushed HEAD.

## Current correction after independent review of caeed219

The next two P2s were reproduced in `round3-reproduction.log`: worktree-only
absence missed a profile still tracked by HEAD/index; deletion commits aborted
the historical search before an older valid blob. The installer now inventories
index and HEAD before classifying absence, and skips tree revisions without the
hook path. Staged and unstaged full-profile removals reject fresh installation.
The existing removed-profile test now expects the earlier explicit declaration
error instead of an overlap list; both reject and preserve the installed hook.

Final current-source validation: **77 passed** in `round3-final-tests.xml` using
the same complete targeted command; runtime smoke and **201 passed** in
`round3-precommit.log`. The intermediate run had 76 passes and the old assertion
failure; after correcting that expectation the complete suite was rerun green.
Earlier 74-test evidence and caeed219 CI are historical. Fresh independent review
and CI are required for this new candidate; no consumer qualification is added.

## Current correction after independent review of e794dba2

P2 in issue comment 5677100462: a dangling pre-push symlink bypassed the
existence check and could be replaced without preservation. Attribution:
introduced; current-decision impact: yes; disposition: fix now. The declared
profile guard now checks symlink identity independently of target existence.
Both existing and dangling links must be refused and left untouched.

Local targeted validation: **77 passed, 2 skipped** (`symlink-tests.xml`).
Windows lacks symlink creation privilege, so these two new cases did not run
locally; the local pre-fix attempt is not reproduction evidence. The external
reviewer's exact-head finding supplies the observed failure. Linux tests raise
on symlink creation failure rather than skipping, so fresh Linux CI must pass
before these cases can be claimed verified. Runtime smoke and **201 tests**
passed (`symlink-precommit.log`). Prior e794dba2 CI is historical. Independent
review and CI must qualify the final pushed correction HEAD.
