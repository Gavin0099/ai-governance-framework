# Codex SessionStart identity

This bounded adapter establishes identity for Codex native SessionStart events.
It uses the existing envelope writer. It does not itself run session closeout or
create closeout candidates. The PR also rejects ambiguous Codex closeout fallback
identity, following the separately authorized P1 repair; canonical schema,
envelope writer and Stop event routing remain unchanged.

## Install

From the framework checkout, explicitly name the consumer Git root:

```powershell
python runtime_hooks/adapters/codex/session_start.py --install --project-root E:/path/to/consumer
```

Installation adds one SessionStart group to `.codex/hooks.json`, preserving
existing Stop and consumer hook values. The framework script location and
consumer root are bound at installation. On Windows, the command uses the
installer's Python executable and encoded PowerShell transport. Repeated
installation with the same binding is a no-op; differing owned bindings and
malformed configuration are refused rather than silently replaced.
Inspect the generated config and accept Codex's native hook trust prompt if
required. Do not install from a temporary checkout that will be removed.

## Identity contract

The native payload must contain SessionStart, a supported source, a safe
explicit session_id, and cwd within the installed Git root. No ID is generated
and no root is taken from a prior session's pointer.

| Event condition | Behavior |
|---|---|
| startup / clear, new ID | Write envelope through the existing writer |
| Existing valid envelope, any supported source | Preserve every envelope byte; refresh runtime current-session pointer |
| resume / compact, no envelope | Report failure; do not invent the original start time |
| Invalid envelope / wrong root / unsafe ID | Report failure without replacing identity |
| Existing completion marker | Preserve consumption; never delete or reset completion |
| Concurrent same-ID startup | One writer; conflicting invocation reports failure without resetting identity |

The adapter's exclusive lock is removed on ordinary success/failure. If the
process is killed while holding it, the next event reports that startup is
already running. Diagnose process/lock ownership before removing a stale lock;
there is no automatic recovery that can rewrite identity.

The adapter only produces the envelope, not candidate task_intent/work_summary.
Binding can still reject closeout when no current-session candidate exists.
It does not retroactively repair sessions that started without the hook.
Existing candidates remain eligible across resume/compact because started_at
is preserved. Completed sessions remain consumed.

## Event boundary and evidence

### Concurrent-session closeout identity

The repository-wide current-session marker remains a convenience pointer, not
authority to consume a Codex candidate. Codex native integrations must pass
`--agent-id codex` and a valid `session_id` in stdin. Missing, malformed, unsafe,
or conflicting identity fails before the pipeline. Exit 1 reports a failed hook;
it does not request a new Codex turn via exit 2.

Manual Codex closeout must name the intended session explicitly:

```powershell
python governance_tools/session_closeout_entry.py --project-root E:/path/to/consumer --agent-id codex --session-id actual-session-id --trigger-mode manual_fallback --format json
```

CLI and stdin identities must agree when both are supplied. The core closeout
hook also rejects an untagged/manual fallback pointing at a Codex envelope,
so the previously reproduced missing-ID path cannot consume another Codex
session. Other providers' existing fallback behavior is retained; callers must
not intentionally disguise a Codex invocation as another provider. Existing
receipt schema and historical records are unchanged.

Codex synthetic smoke creates a unique `codex-smoke-*` envelope and passes that
identity explicitly. It cannot consume an existing session's candidate. Like
the existing envelope writer, it advances the repository's convenience marker;
run smoke in an isolated test repo. Its receipt proves synthetic pipeline
execution, not a real session's valid content or native lifecycle activation.

Official hook documentation distinguishes SessionStart from turn Stop and
session SessionEnd: <https://learn.chatgpt.com/docs/hooks>.
Changing closeout from Stop to SessionEnd is a separate decision. This slice
does not assert end-to-end closeout correctness or qualify Codex lifecycle
behavior solely from isolated tests.

Validation:

```powershell
python -m pytest tests/test_codex_session_start.py tests/test_codex_windows_hook_command.py -q
```

P1 regression and receipt compatibility:

```powershell
python -m pytest tests/test_codex_closeout_identity.py tests/test_codex_session_start.py tests/test_codex_windows_hook_command.py tests/test_agent_closeout_receipt.py tests/test_session_closeout_entry_no_ledger_write.py -q
```

Tests exercise JSON stdin, Windows native PowerShell command transport,
space/quote paths, stable envelope bytes, candidate binding, consumption,
missing/invalid identity, wrong root, and preserving unrelated hooks.
