# SessionStart PR evidence

## Current candidate validation

The candidate was re-tested in `codex-session-start-20260915` immediately before
the implementation commit. This supersedes the earlier statement that its 27
tests had not been reverified in the current checkout.

- `python -m pytest tests/test_codex_session_start.py tests/test_codex_windows_hook_command.py -q --junitxml=memory/evidence/codex-session-start-20260915/tests.xml`: **27 passed**, 20.39 seconds.
- `bash scripts/run-runtime-governance.sh --mode enforce`: **smoke passed; 201 focused tests passed**, 40.88 seconds for pytest. This is not the full repository suite.
- `tests.xml` and `precommit.log` are the corresponding raw evidence.
- Native Windows tests execute the generated PowerShell command with JSON stdin;
  the scoped handoff test uses the real closeout entry after compact.
- This is author-process validation, not independent PR review or live native
  Codex SessionStart event qualification.

## Lenovo consumer evidence is separate

The owner reported a successful SessionStart smoke on
`lenoveo-isp-tool-avalonia`. Its current-candidate artifact path and source
identity have not yet been verified in this task.

What was actually found during the read-only consumer pass:

- The September 15 daily memory contains real closeout failure records with
  canonical status `missing` and hook status `stale_or_mismatched`.
- `artifacts/evidence/test-results/external-repo-smoke-20260909.json` reports
  `session_start_ok=true`, generated **2026-09-09T06:34:35Z**, using framework
  **a6a2d62251fbc87900484f0e44ef1737de2188f5**.
- That historical smoke predates this candidate. It is not evidence that this
  adapter was installed or succeeded on Lenovo, and is not candidate commit
  qualification. No consumer files were changed by this PR task.

Do not combine these observations into a claim that the Lenovo closeout bug was
fixed. A current-candidate successful consumer smoke remains unverified here.

## Delivery boundary

This PR adds a separately invoked SessionStart installer and adapter, plus the
owner-authorized P1 repair requiring explicit Codex closeout identity. The core
also rejects shared fallback pointing at a Codex envelope. Existing Stop event
routing, canonical writer/schema and historical receipt criteria are unchanged.
No real consumer activation, framework upgrade, Stop/SessionEnd migration,
automatic envelope backfill, or S2 work is included.
Missing resume/compact identity deliberately remains an error.

## P1 remediation evidence (supersedes original merge eligibility)

Review of `bcdf866d` found that concurrent Codex sessions can overwrite the shared
pointer, allowing missing-ID closeout to consume the other session. The owner
explicitly authorized expanding this PR to reject that fallback. The isolated
reproduction and remediation evidence are stored in
`memory/evidence/codex-session-start-p1-20260915/`.

- Current focused run: **62 tests passed**, including invalid/missing/conflicting
  IDs, zero side effects on rejection, explicit native/manual A while pointer
  selects B, receipt linked to the actual fixture HEAD, and non-Codex compatibility.
- Original 27 tests remain a separate earlier candidate run; they are not Lenovo
  consumer qualification and do not alone validate this later repair.
- New exact-HEAD independent review and CI must be obtained after pushing.
