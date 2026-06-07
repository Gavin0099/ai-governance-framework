# Codex Stop Hook Verification - 2026-06-06

Status: partial verification - real session-end firing still pending

## Scope

Verify whether the configured Codex Stop hook path is executable enough to support
the next real-session verification step.

This artifact does not claim that Codex Stop hooks have fired automatically at
session end. It records only the local command-path and display smoke evidence
available during the active Codex session.

## Configuration Observed

- Hook config: `.codex/hooks.json`
- Hook event: `Stop`
- Hook command after repair:
  `C:\Users\daish\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe d:\ai-governance-framework\codeburn\phase1\codeburn_session_display.py`
- Display opt-in: `CODEBURN_SHOW_VISIBLE_IO_SUM=1`

## Finding

The previous hook command used `python`, but neither `python` nor `py` was
available in the Codex shell PATH during this session. That made the configured
hook command non-executable in this environment.

The local `.codex/hooks.json` command was updated to use the bundled Codex
workspace Python executable.

## Evidence

### Failed command-path probe

Command:

```powershell
$env:CODEBURN_SHOW_VISIBLE_IO_SUM='1'; '{}' | python codeburn/phase1/codeburn_session_display.py --no-db --debug-hook-json --verbose-reason
```

Result:

```text
FAIL - python was not recognized as a cmdlet, function, script file, or operable program
```

Additional probes:

```text
py --version: FAIL - py was not recognized
where.exe python: FAIL - no match
where.exe py: FAIL - no match
```

### Passing command-path smoke

Command:

```powershell
$env:CODEBURN_SHOW_VISIBLE_IO_SUM='1'; '{}' | C:\Users\daish\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe d:\ai-governance-framework\codeburn\phase1\codeburn_session_display.py --no-db --debug-hook-json --verbose-reason
```

Result:

```text
PASS - command exited 0
PASS - latest Codex transcript discovered
PASS - provider displayed as codex
PASS - visible I/O summary displayed
PASS - no DB write requested via --no-db
```

Observed display summary:

```text
provider : codex
turns    : 22
input    : 1.5M tokens (reconstructed)
output   : 8,976 tokens (reconstructed)
visible I/O token sum displayed as Class C observation
```

### Passing hook-equivalent command smoke

Command:

```powershell
$env:CODEBURN_SHOW_VISIBLE_IO_SUM='1'; $env:CODEBURN_DB='C:\tmp\codex-stop-hook-smoke.db'; '{}' | & 'C:\Users\daish\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'd:\ai-governance-framework\codeburn\phase1\codeburn_session_display.py'
```

Result:

```text
PASS - command exited 0
PASS - hook-equivalent command ran without --no-db
PASS - DB write path redirected to C:\tmp for smoke isolation
PASS - latest Codex transcript discovered
PASS - visible I/O summary displayed
```

Observed display summary:

```text
provider : codex
turns    : 25
input    : 1.8M tokens (reconstructed)
output   : 10,851 tokens (reconstructed)
visible I/O token sum displayed as Class C observation
```

## Claim Boundary

Claimable now:

- The CodeBurn session display script is executable with bundled Python.
- The script can discover the current Codex transcript from fallback discovery.
- The script can display Codex visible I/O summary when `CODEBURN_SHOW_VISIBLE_IO_SUM=1`.
- The hook-equivalent command path runs successfully when DB output is redirected.
- The previous `.codex/hooks.json` command path was not executable in this shell.
- The local `.codex/hooks.json` command path has been repaired for this machine.

Not claimable yet:

- Codex Stop hook fired automatically at real session end.
- Codex hook coverage is `A (verified)`.
- Codex closeout behavior is equivalent to Claude Code.
- Codex memory write behavior has been observed in a real closeout.
- Claude-vs-Codex AB protocol can be run with Tier A verified Codex coverage.

## Next Required Observation

End a real Codex session and confirm that the Stop hook output is visible without
manual invocation. If visible, update `docs/hook-coverage-model.md` from
`A (unverified)` to `A (verified)` with the verification date and cite this
artifact plus the real session-end observation.

## Real-Session Observation Checklist

Use this checklist after the next real Codex session ends. Do not run these as a
manual smoke substitute; this checklist is for observing whether the configured
Stop hook fires automatically.

### Required evidence to record

- Session end timestamp in local time and UTC.
- Whether CodeBurn output appeared automatically after the Codex session ended.
- Whether the output used the repaired bundled Python hook command.
- Whether the output identified `provider : codex`.
- Whether a visible I/O summary appeared when `CODEBURN_SHOW_VISIBLE_IO_SUM=1`.
- Whether the output preserved the Class C / not decision-authoritative boundary.
- Whether the session required any manual command invocation after Stop.
- Whether any hook error, missing transcript, or no-token status panel appeared.

### Pass condition for `A (verified)` upgrade

All of the following must be true:

- The output appears automatically at real session end.
- No manual command invocation is needed after the session ends.
- The output is attributable to `.codex/hooks.json` Stop hook execution.
- The displayed transcript is from the just-ended Codex session, not a stale fallback.
- The output exits without blocking session close.

If any condition is false or unknown, keep Codex at `A (unverified)` and append
the observed failure or ambiguity to this artifact instead of updating
`docs/hook-coverage-model.md`.

### Observation record template

```text
real_session_observation:
  observed_at_local: <YYYY-MM-DD HH:MM TZ>
  observed_at_utc: <YYYY-MM-DDTHH:MM:SSZ>
  codex_session_id_or_transcript_stem: <id-or-unknown>
  automatic_stop_hook_output_visible: yes | no | unknown
  manual_invocation_used_after_stop: yes | no
  hook_source_attributable_to_codex_hooks_json: yes | no | unknown
  provider_detected: codex | claude | unknown
  latest_transcript_matches_ended_session: yes | no | unknown
  visible_io_summary_displayed: yes | no | unknown
  class_c_boundary_displayed: yes | no | unknown
  hook_exit_or_close_blocking_issue: none | <describe>
  decision: keep_A_unverified | upgrade_candidate
  notes: <short notes>
```

### Current Codex session pending record

```text
real_session_observation:
  observed_at_local: 2026-06-06 - user reported after prior Codex session ended
  observed_at_utc: unknown - exact session-end timestamp not captured
  codex_session_id_or_transcript_stem: unknown - no automatic Stop hook output available
  automatic_stop_hook_output_visible: no
  manual_invocation_used_after_stop: unknown
  hook_source_attributable_to_codex_hooks_json: no
  provider_detected: unknown
  latest_transcript_matches_ended_session: unknown
  visible_io_summary_displayed: no
  class_c_boundary_displayed: no
  hook_exit_or_close_blocking_issue: output_not_observed
  decision: keep_A_unverified
  notes: User reported no visible Stop hook output after the prior Codex session ended; keep Codex at A (unverified) and investigate hook firing or output visibility before any upgrade.
```

### Claim rule

Only `decision: upgrade_candidate` plus all pass conditions above may support a
future `A (verified)` documentation update. This artifact alone remains partial
verification until the real-session observation is filled.
