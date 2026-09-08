# Skill Evaluation Lite — one real task

Slice 2 connects fresh model patch generation, real host oracle/regression
execution, and a third fresh model scoring context to the existing Lite score
freeze/unblinding coordinator. This is one queue-range pipeline validation,
not a benchmark of general Skill effectiveness. The synthetic entry remains.

## Run boundary

`governance_tools.skill_evaluation_lite_live` accepts an explicit config, Skill
packet and new output directory. The config records absolute Codex/Python
executable paths, lengths and SHA-256, model selector, existing Codex HOME and
Skill SHA-256. It checks binary/Skill bytes before creating the run root and
checks the relevant binary again before every launch. No bare executable lookup,
shell invocation or automatic retry occurs. Configuration is this run's input,
not a new authority registry or proof of full dynamic-runtime custody.

Both arms receive the same fixed task/baseline, structured response schema,
model and reasoning setting. Only the second arm receives the existing Bug Fix
Safety recipe. The recipe's reproduction/sensitivity steps cannot all be enacted
in this patch-generation-only adapter: models produce source, tests and an honest
summary without tools; the host subsequently executes the submitted code. This
does not validate the Skill's complete interactive workflow. An adapter with an
interactive tool loop requires separate work and evidence before claiming that.

Codex launches a new `exec` session each time, without resume/fork, with user
config and project docs excluded, host Skill discovery disabled, and shell,
code execution, apps, plugins, browser, multi-agent, memories and hooks disabled.
Only passive model messages/reasoning and one completed turn are accepted.
Any observed tool event fails the run; event validation is a detection boundary,
not an OS proof that no access could occur. No global configuration is changed.
CLI is directed to the existing HOME; usable authentication is not guaranteed.
Environment uses an allowlist, without inherited
PATH/PYTHONPATH/GIT selectors or credentials copied into artifacts. Local paths
in controller receipts are not scorer inputs. The built-in normal read-only CLI
sandbox is not removed; Strict readiness/quiescence/AppContainer are not invoked.

## Evidence flow

Generated source/test submissions must satisfy a narrow queue-range Python AST
subset before import; host file/network/process/introspection operations are
rejected. This is not a general sandbox or a proof that arbitrary Python is safe.
Host subprocesses use the pinned Python, isolated mode, fixed cwd and 15-second
timeout. The oracle's ten fixed expected cases are independent of generated code
and tests. Model failure/timeout, unverifiable oracle result or changed source/test
bytes stop the run. An oracle FAIL remains correctness FAIL, not scorer opinion.

`host-observation.jsonl` adapts actual file readbacks and observed unittest
completion to the unchanged queue-range regression consumer. Its command names
are semantic operation names (`Get-Content ...`, `python -m unittest -v`), NOT
literal commands run by an arm or historical Codex events. The corresponding
`*.request.json` and `*.result.json` preserve actual absolute argv, stdout,
stderr, status and elapsed time. Source/test bytes are checked after execution;
digests are captured at collection for later projection. There is no claim of
historical custody recovery. Unknown/stale/missing evidence stays unconfirmed.

The consumer strips metadata and validates payload/rubric identity material.
The scorer receives only the anonymous outputs, test evidence, correctness and
fixed rubric (including task contract and baseline). It receives no mapping,
Skill recipe, old bundle or prior conversation. It is a fresh context with
restricted supplied inputs; OS-attested isolation is NOT CLAIMED.

Both scores are validated and saved with readback before unblinding. Full-run
authorization is explicitly selected by `--authorize-unblinding-after-freeze`;
the coordinator additionally checks the exact freeze digest. The report never
changes scores. Outputs are create-once files, and a second invocation cannot
reuse the output directory. This is not a tamper-proof durable resume system.

## Invocation

```powershell
& .\.venv\Scripts\python.exe -B -m governance_tools.skill_evaluation_lite_live --config <config.json> --skill <recipe.md> --output <new-directory> --authorize-unblinding-after-freeze
```

No manual application shutdown or external PowerShell handoff is part of this
entry. Run it inside the normal Codex session. One run uses two model generation
calls and one scorer call, plus host oracle/tests. Client model wait is bounded
at 600 seconds; process timeout is not success and does not trigger retry.

## Acceptance and limitations

Only actual completion may produce `REAL_LITE_END_TO_END_VALIDATED`.
Adapter unit tests using fake model transport do not establish that claim for
a real run. Tests exercise actual host Python/oracle, leakage rejection, tool
event rejection, missing completion, input pins, no replay and freeze ordering.

All reports retain `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`.
Do not infer Strict equivalence, OS isolation, Formal/counting eligibility,
general Skill efficacy or long-term value. Record time and human interventions;
do not infer measured cost reduction without a comparable baseline. Existing
rounds, scores, Strict sources and P1 UNKNOWN remain unchanged. No push.

## First live invocation: blocked

The single 2026-09-08 invocation stopped at the first model call with HTTP 401
(`Missing bearer or basic authentication in header`), `turn.failed`, and process
exit 1. No arm output, oracle, scorer, freeze or report was produced. The adapter
did not retry or start the second arm. Codex itself emitted websocket/HTTPS
reconnection attempts inside that one invocation; "no retry" here means no
adapter-level replay, not one HTTP request. Existing-runtime configuration
warnings were also observed and are preserved, not attributed as the auth cause.

Evidence: `memory/evidence/p2-lite-slice2-20260908/live/`. Implementation tests and
review passed, but **REAL_LITE_END_TO_END_VALIDATED is not established**. Neither
real model compatibility nor reduced real-evaluation cost has been demonstrated.
No credential changes, second invocation, P1 probe, Strict change or push followed.

## Auth and warning compatibility follow-up

The subsequent owner-authorized auth slice explicitly selects the existing
`keyring` store while retaining `--ignore-user-config`; no login or user config
change is needed. Its one live turn completed with exit 0 and a response, but the
parser falsely classified runtime `item.error` warnings as tool access.

The parser now full-matches only the three observed 0.153.4 warning forms:
required Elevated sandbox fallback, the specific unstable skill-discovery flag,
and disabled Code Mode host. Unknown errors, extra error fields, unfinished error
events, missing completion, nonzero exits and tool events still fail closed.
This does not suppress diagnostics or assert that runtime configuration is clean.
Raw results remain unchanged; `runtime-warnings.json` retains exact warning text,
and a completed report includes warnings per arm/scorer. These host diagnostics
are excluded from anonymous scorer input because they may contain local paths.
The recognizer is deliberately version-bounded; new diagnostics require review.

After targeted tests, independent review and the scoped compatibility commit,
the owner authorizes one new real Lite invocation. Failure is preserved and stops
the adapter; no automatic retry, historical replacement, or push is authorized.
