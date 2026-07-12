# Runtime Treatment Census — Live-Invoker Check (Candidate I, 2026-07-12)

Status: read-only follow-up to census candidate G. This checks configured
entrypoints, not code reachability or efficacy. No hook, runtime, adapter, or
census disposition is changed here.

## Question and classification rule

Candidate G established that `session_start` has no current session-hook
caller in this framework or the checked consumer. This check asks a narrower,
re-checkable question for all 33 pinned census units: **which units have an
observed local configured invoker today?**

Classification uses the current framework worktree's `.claude/settings.json`,
`.codex/hooks.json`, and tracked `.github/hooks/session-end.json`, plus static
entrypoint search. It is deliberately not a fleet-wide or telemetry claim.

| Class | Meaning |
| --- | --- |
| `local_live_configured` | A current local harness configuration invokes the runtime path. |
| `manual_campaign_test_only` | Code is reachable through CLI, smoke, examples, campaigns, or tests, but no current local harness configuration invokes it. |
| `non_executable_carrier` | Prompt/template data, not a runtime entrypoint. |

## Mechanical entrypoint evidence

- Local `.claude/settings.json` has a `Stop` hook that calls
  `governance_tools/session_closeout_entry.py`; it reaches
  `session_end_hook` and then `runtime_hooks/core/session_end.py`.
- Local `.codex/hooks.json` has only a `Stop` hook for
  `codeburn_session_display.py`; it does not invoke a runtime treatment
  entrypoint.
- Neither local configuration defines `SessionStart`, `pre_task`, or
  `post_task` runtime hooks. The tracked `.github/hooks/session-end.json` is
  a session-end configuration pointing to a different checkout, not evidence
  of a current local runtime caller.
- `shared_adapter_runner.py` and `dispatcher.py` can route all three event
  types, but static reachability is not an installed hook. Their callers are
  smoke, test, example, or manual paths in the checked source set.

## Census classification (33/33)

| Class | Units | Count | Basis |
| --- | --- | ---: | --- |
| `local_live_configured` | `session_end.py`, `_canonical_closeout.py` | 2 | Claude Stop → `session_closeout_entry` → `session_end_hook` → `session_end`; canonical closeout is part of that lifecycle. |
| `manual_campaign_test_only` | `session_start.py`, `pre_task_check.py`, `post_task_check.py`, `decision_policy_v1_runtime.py`, `_canonical_closeout_context.py`, `evidence_integrity_gate.py`, `payload_audit_logger.py`, `human_summary.py` | 8 | Treatment/core units are reached from session-start, pre/post, or manual core paths; no configured local invoker exists for those events. |
| `manual_campaign_test_only` | `dispatcher.py`, `shared_adapter_runner.py`, `shared_normalizer.py`, `runtime_path_overrides.py`, `smoke_test.py` | 5 | Runtime plumbing is exercised by manual/replay/smoke paths, not a configured local native hook. |
| `manual_campaign_test_only` | Claude, Codex, Gemini, and Hermes adapter trios (normalizer/pre-task/post-task) | 12 | Adapter programs route correctly when invoked, but no checked local configuration calls any adapter pre/post/session-start path. |
| `manual_campaign_test_only` | `examples/hermes/stub_runner.py` | 1 | Explicit example/stub runner only. |
| `non_executable_carrier` | Copilot instructions template, multi-validator `AGENTS.md`, three YAML templates | 5 | Instruction/template data; not a runtime invoker. |

**Total: 2 + 26 + 5 = 33.**

## Findings

1. The closeout/audit boundary has a configured local entrypoint. It must not
   be collapsed into the treatment-layer conclusion.
2. The treatment layer (`session_start`, injection, pre-task advisories), all
   pre/post adapters, and their routing path have **no observed configured
   local invoker**. Their prior “consumer known” notes establish historical
   structural paths, not current delivery.
3. This makes the census's large `decision_evidence=none` pool more legible:
   lack of observed effect is compatible with a dormant delivery path. It does
   not prove any unit useless, dead, or safe to retire.

## Owner decision boundary

Whether to wire a session-start or adapter path into live harness sessions is
an architecture/enforcement decision. It could change execution cost,
evidence volume, and user-visible workflow; this census follow-up therefore
does not install a hook or recommend automatic wiring. Any implementation must
be a separate owner-approved slice with real-session and failure-path evidence.

## Claim ceiling

- Does not prove no other machine, untracked user setting, or external repo
  invokes these units.
- Does not prove the local Stop hook fired during this check, only that its
  current configuration targets the closeout path.
- Does not change retention, merge, retirement, or enforcement disposition for
  any census unit.
