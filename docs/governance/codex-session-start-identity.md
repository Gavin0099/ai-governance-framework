# Codex SessionStart identity

This bounded adapter establishes identity for Codex native SessionStart events.
It uses the existing envelope writer. It does not run session closeout, create
closeout candidates, or modify the canonical schema, guard, or Stop handler.

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

Official hook documentation distinguishes SessionStart from turn Stop and
session SessionEnd: <https://learn.chatgpt.com/docs/hooks>.
Changing closeout from Stop to SessionEnd is a separate decision. This slice
does not assert end-to-end closeout correctness or qualify Codex lifecycle
behavior solely from isolated tests.

Validation:

```powershell
python -m pytest tests/test_codex_session_start.py tests/test_codex_windows_hook_command.py -q
```

Tests exercise JSON stdin, Windows native PowerShell command transport,
space/quote paths, stable envelope bytes, candidate binding, consumption,
missing/invalid identity, wrong root, and preserving unrelated hooks.
