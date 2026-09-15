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

This PR adds a separately invoked SessionStart installer and adapter only.
Existing Stop handlers, closeout writer, guard and canonical schema are unchanged.
No real consumer activation, framework upgrade, Stop/SessionEnd migration,
automatic envelope backfill, or S2 work is included.
Missing resume/compact identity deliberately remains an error.
