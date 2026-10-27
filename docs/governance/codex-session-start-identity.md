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

New Codex sessions use envelope version `1.1`. Its `repo_binding.consumer_root`
is the resolved consumer Git worktree root checked against the native cwd and
installed root at SessionStart; `repo_binding.source=codex_session_start` is a
provenance label, not authentication. The shared reader validates the complete
binding, provider and contained session path. Same HEAD does not make two
worktrees the same consumer. This is correctness binding, not a security boundary.

### VS Code

VS Code uses the same contract with its own identity (#225, #227):
`provider=github-copilot-vscode`, `repo_binding.source=vscode_session_start`,
created through `establish_bound_session` in
`runtime_hooks/core/_bound_session_start.py` with `.vscode-start.lock`. A
session id one provider created is never adopted by the other.

- **Installed root.** Codex checks the payload cwd against the `--project-root`
  written at install time. For VS Code the equivalent anchor is the installed
  bridge's own location, `<root>/.github/hooks/ai-governance-lifecycle.py`: a
  payload whose cwd resolves to a different worktree is rejected and nothing is
  written. When the bridge runs from anywhere else (the framework source, in
  development or tests) there is no install anchor and the root comes from the
  payload.
- **Payload rules (as for Codex).** Only `hook_event_name=SessionStart` may
  establish or preserve an identity; any other or missing event is rejected
  before any write. VS Code's Local harness currently always sends
  `source=new`; Codex's `resume`/`compact` sources are not claimed as VS Code
  features. The bridge only guards against them: if a payload ever says
  `resume` or `compact`, an existing identity is required and no start time is
  invented.
- **Bridge newer than framework.** If the framework the bridge resolves has no
  `_bound_session_start`, it can neither write nor read a VS Code `1.1`
  envelope; the bridge keeps that framework's legacy `1.0` envelope and reports
  `session_envelope_binding=legacy` with
  `session_envelope_binding_reason=framework_without_root_bound_support`. This
  is the only downgrade, and it keeps the identity rules: the event and
  installed-root checks run in the bridge before the framework import; an
  existing identity is preserved, never rewritten; one owned by another
  provider is refused; and `resume`/`compact` without an identity is refused.
  Only an absent `runtime_hooks.core._bound_session_start` counts as "too old" —
  a broken dependency inside it, or a module without `establish_bound_session`,
  is reported as an error with nothing written.
- **Supported harness: VS Code Local only.** The installed hook file is
  Copilot-format (`sessionStart` in `.github/hooks/ai-governance-copilot.json`,
  `--surface auto`). VS Code's Local harness maps that configuration and sends
  its own snake_case payload (`session_id`, `hook_event_name`), routed to
  `vscode` and bound. VS Code's Copilot harness sends the camelCase Copilot
  payload (`sessionId`), routed to `copilot` (`provider=github-copilot`): it
  keeps the unbound `1.0` envelope and cannot prepare a summary. Binding that
  surface is not approved and would be a separate trust decision.

Both payload shapes are tested through the real installer and the installed
`sessionStart` command. Neither harness has been verified in a running editor.

The shared reader supports both `1.0` and `1.1` before the adapter emits `1.1`.
Existing `1.0` envelopes remain byte-preserved and usable by existing closeout;
they have no qualified root binding and must not be treated as root-bound by a
future preparation entry. Resume/compact never backfill old identities. New `1.1`
envelopes are published atomically; malformed, copied-to-wrong-root or unknown
versions reject without rebinding. Existing consumed sessions are never reset.

Deploy reader support before enabling the new writer on any formal path. A
SessionStart hook using this version paired with an older closeout reader is
not qualified: inspect the actual framework locations bound by both commands
before activation. Do not downgrade written envelopes to make an old reader pass.
This change neither activates consumers nor implements candidate preparation.

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

### Claude Code

Claude Code uses the same identity contract with `provider=claude`,
`repo_binding.source=claude_session_start`, through
`runtime_hooks/adapters/claude_code/session_lifecycle.py` (design: #231,
`docs/proposals/2026-10-claude-code-session-lifecycle.md`). The installer
(`manage_agent_closeout install --agent claude`) manages a SessionStart and a
SessionEnd hook and removes any legacy governance Stop closeout: Claude Code's
`Stop` fires after every response, not at session end.

- **SessionStart**: `startup`/`clear`/`fork` create an identity; `resume`/`compact`
  preserve an existing one. A `resume` without an identity (older Claude Code may
  report a fork that way) never invents one: the session stays unbound and the
  context says saving is unavailable. The cwd is matched by Git worktree root, so
  Claude may start in a subdirectory. Another provider's identity is never
  adopted.
- **Read-back**: SessionStart injects at most 800 characters of the latest
  checkpointed summary, used only when the candidate's SHA-256 matches the
  checkpoint, marked as data, from this worktree's Claude sessions only.
  Ambiguous states are reported (`exit_unconfirmed`, `checkpoint_mismatch`,
  `UNKNOWN`), never presented as success.
- **SessionEnd**: writes a resumable checkpoint to
  `artifacts/runtime/session-checkpoints/<session_id>.json` (timeout 5 s); no
  completion marker and no consumption, so `claude --resume` can continue and
  save again. Receipts-style fields use `trigger_mode=native_hook` with the
  payload's `hook_event_name`/`reason` as evidence. SessionEnd may not run at
  all; the next SessionStart derives the state from what is on disk.
- **Formal closeout stays explicit.** The shared closeout allows one owning
  session per worktree: after a session prepares a summary, a *new* session can
  read it back but cannot save its own until the previous session's formal
  closeout releases ownership. SessionStart says so when it applies.
- **Install reports what it cannot promise.** `install` and `verify` carry a
  `closeout_readiness` field. The save-progress command SessionStart declares
  needs the framework to be a registered submodule of the project root and the
  root's governance markers (`AGENTS.md`, `governance/`) to be present; neither
  was checked at install time, so a configuration-only `installed` was reported
  for layouts where that command had no success path (#257). Preconditions that
  are unmet and preconditions that could not be read are reported separately, and
  transient state — a dirty framework checkout, a moved gitlink — stays with the
  pipeline's own fail-closed validation rather than being predicted here.
- **Inherited `GIT_*` overrides.** The preparation entry rejects inherited Git
  environment overrides, because its readers must not be handed a different
  repository or index. Interactive helper selectors (`GIT_EDITOR`,
  `GIT_SEQUENCE_EDITOR`, `GIT_PAGER`) are tolerated and dropped from every child
  Git environment: they name a program Git may launch, cannot redirect what Git
  reads, and an agent harness sets `GIT_EDITOR` unconditionally, which made the
  declared command impossible to run as declared (#257). Every other `GIT_*` name
  is still rejected before any runtime write.

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
