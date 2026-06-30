---
status: design-only
authority: proposal
runtime_change: false
enforcement_change: false
credential_use: false
model_run: false
audited_external_repo: E:/BackUp/Git_EE/hermes-agent
audited_external_head: 5bf23ff
---

# Real Hermes No-Write Model-Run Evidence Plan

## Problem

The framework has a Hermes accepted-input adapter and a separate Hermes
`no_agent` local observer line, but it still has no evidence from a real Hermes
model/provider invocation.

The next useful step is not to install a provider integration or claim runtime
governance. The next useful step is to define how a future, explicitly
authorized Hermes model/provider run could produce reviewable evidence without
changing Hermes source, using provider credentials in this repository, or
expanding enforcement.

This plan exists to prevent three claim errors:

- treating the accepted-input adapter as proof that real Hermes is governed;
- treating a future model response as proof of truth or reliability;
- treating a captured output artifact as a non-bypassable governance gate.

## Current Repository Truth

The current framework state supports only the following claims:

- `runtime_hooks/adapters/hermes/HERMES_RUNTIME_INTERFACE.md` defines an
  accepted-input adapter interface. It is not a verified specification of the
  public Hermes runtime.
- The Hermes adapter accepts `response_file` aliases such as `output_file`,
  `assistant_response_path`, `transcript_path`, and `result_file`; the runtime
  must still provide the artifact.
- `docs/governance/hermes-real-integration-contract-spec-2026-06-22.md`
  records a read-only audit of `E:/BackUp/Git_EE/hermes-agent` at head
  `5bf23ff`.
- That audit found useful cooperative surfaces, including CLI entrypoints,
  tool middleware, plugin hooks, tool invocation, memory lifecycle hooks, cron
  artifacts, and async delegation events.
- That audit did not prove any single Hermes hook is a non-bypassable
  chokepoint.
- The same audit found that general interactive and ACP Hermes execution did
  not naturally emit a generic `response_file` / `output_file`; final output is
  stream/protocol shaped except for cron output artifacts.
- `PLAN.md` currently states that the Hermes executor-adapter line has
  accepted-input adapter coverage and `observed_six_scheduled_runs` for the
  separate `no_agent` observer, but does not claim true Hermes model
  integration, provider-free runtime, model-generated tool-call reliability, or
  non-bypassable governance wrapping.

Additional static diagnosis on 2026-06-30 observed the local Hermes checkout at:

```text
E:/BackUp/Git_EE/hermes-agent
HEAD: 5bf23ff
branch: main tracking origin/main
ahead/behind: 0/0
dirty state: untracked artifacts/ only
```

The static diagnosis did not run Hermes CLI, did not read credential values,
did not run a provider/model call, and did not modify either repository.

## Target Outcome

Define the minimum evidence contract for a future no-write real Hermes
model/provider run.

The future run, if separately authorized, should produce a reviewable packet
that answers:

- which Hermes checkout and entrypoint were used;
- which provider/model identifiers were selected, without disclosing secret
  values;
- whether tools were disabled or constrained;
- what final output was emitted;
- where the output artifact was materialized;
- which framework adapter input fields were produced;
- what the evidence does and does not prove.

## Scope

This plan covers only a future evidence-producing run design.

In scope:

- static-first preflight requirements;
- credential-name discovery without credential-value access;
- tool-disablement or tool-constrained run boundaries;
- output materialization requirements;
- framework adapter payload requirements;
- reviewer packet contents;
- failure paths and stop conditions.

Out of scope:

- running Hermes;
- reading `.env` values or credential store values;
- installing dependencies;
- fetching repositories;
- modifying Hermes source;
- modifying framework runtime hooks;
- wiring CI, hooks, gates, or enforcement;
- implementing provider prompt cache;
- implementing a Hermes plugin;
- claiming real Hermes governance compliance.

## Affected Surfaces

Framework-side surfaces:

- `runtime_hooks/adapters/hermes/HERMES_RUNTIME_INTERFACE.md`
- `runtime_hooks/adapters/hermes/normalize_event.py`
- `runtime_hooks/adapters/hermes/pre_task.py`
- `runtime_hooks/adapters/hermes/post_task.py`
- `runtime_hooks/examples/hermes/post_task.native.json`
- `docs/governance/hermes-real-integration-contract-spec-2026-06-22.md`

External Hermes surfaces to re-check before any future run:

- `pyproject.toml`
- `hermes_cli/main.py`
- `run_agent.py`
- `agent/conversation_loop.py`
- `agent/turn_finalizer.py`
- `agent/agent_runtime_helpers.py`
- `agent/tool_executor.py`
- `hermes_cli/runtime_provider.py`
- `hermes_cli/providers.py`
- `acp_adapter/entry.py`

These external paths are point-in-time observations. A future run must either
pin the Hermes checkout to the audited head or re-run the static preflight
against the then-current head.

## Boundary and API Considerations

### 1. Static-first preflight

Before any Hermes process is started, the operator must collect:

- Hermes repo path;
- Hermes `HEAD`;
- branch and upstream;
- tracked dirty state;
- selected entrypoint candidate;
- provider/model configuration source names;
- intended output artifact path;
- tool execution policy.

Do not inspect `.env` contents, personal secret stores, browser tokens, or
provider credential values. It is acceptable to identify required key names from
source code, docs, config schema, or provider registry metadata.

### 2. Provider/model boundary

A future run may record provider/model identifiers, but must not record secret
values.

Allowed evidence:

- provider id such as `openrouter`, `anthropic`, `openai-codex`, `xai`, or
  another Hermes provider slug;
- model id string;
- config source type such as `env_key_name`, `config_yaml_key`, `oauth_account`,
  or `external_process`;
- credential key names, for example `ANTHROPIC_TOKEN`, `OPENAI_BASE_URL`, or
  provider registry key names.

Forbidden evidence:

- API key values;
- OAuth token values;
- bearer tokens;
- refresh tokens;
- `.env` file contents;
- screenshots or logs that expose secrets.

### 3. Tool execution boundary

The first real model/provider run should be tool-disabled or tool-constrained.

Preferred first run:

```text
tools: disabled
prompt: ask for a short deterministic text response
expected behavior: final text only, no tool call
```

If Hermes cannot run with tools disabled, the run must use an allowlist of
non-mutating tools and record the allowlist. A run with write-capable tools,
terminal tools, browser automation, delegation, memory writes, or MCP dispatch
is out of scope for the first evidence packet.

No claim may say tool governance is non-bypassable unless a separate
chokepoint audit proves every relevant provider/model tool path flows through a
single mandatory governance surface.

### 4. Output materialization boundary

The future run must create a stable artifact before the framework adapter can
consume it.

Acceptable artifact forms:

- captured stdout final response;
- captured ACP final-response protocol content;
- Hermes session/transcript record if it contains the final response and can be
  referenced without exposing secrets;
- a wrapper-produced JSON file containing the final response and metadata.

Minimum artifact fields:

- `artifact_schema`;
- `hermes_repo`;
- `hermes_head`;
- `entrypoint`;
- `provider`;
- `model`;
- `tool_policy`;
- `prompt_hash` or redacted prompt text;
- `final_response`;
- `final_response_source`;
- `captured_at`;
- `not_claimed`.

The artifact must be written to a reviewable temp or artifacts path chosen for
the run. It must not be silently written into canonical framework memory.

### 5. Raw capture versus governance response artifact

The future run has two separate artifact classes:

1. raw Hermes capture artifact
   - captures what Hermes emitted through stdout, ACP final-response protocol
     content, transcript/session storage, or another reviewed capture surface;
   - proves only that output was captured at the stated boundary;
   - is not automatically a framework `post_task` `response_file`.
2. governance wrapper or sidecar response artifact
   - references or embeds the raw capture artifact;
   - preserves the raw artifact provenance, including path, hash when
     available, capture boundary, provider/model identifiers, and redaction
     status;
   - contains the framework-required `[Governance Contract]` block if it will
     be passed directly as `response_file` / `output_file` to the existing
     Hermes `post_task` adapter.

The existing shared adapter runner treats any non-empty `response_file` for a
non-trivial `post_task` as contract-bearing evidence. A raw Hermes capture that
contains only model output and metadata will not satisfy that path unless it is
wrapped or paired with a separately reviewed governance response artifact.

This plan does not implement the wrapper, sidecar, or any native-artifact
predicate. It only defines the evidence boundary that a later explicitly
authorized run must respect.

### 6. Adapter payload boundary

If the future run produces a governance response artifact that satisfies the
boundary above, the framework Hermes adapter payload may use:

```json
{
  "workspace": ".",
  "task": "Real Hermes no-write model/provider evidence run",
  "risk": "medium",
  "oversight": "review-required",
  "memory_mode": "candidate",
  "output_file": "<path-to-captured-response-artifact>",
  "event_name": "post_task",
  "run_id": "<operator-chosen-run-id>"
}
```

This payload is accepted-input evidence only. It does not prove that Hermes
internally enforced AI Governance.

## Claim Ceiling

If the future run succeeds, the maximum claim is:

```text
A real Hermes model/provider invocation emitted a captured final response
artifact under a no-write evidence plan, and a governance response artifact was
shaped into the framework Hermes accepted-input post_task contract.
```

It still must not claim:

- provider reliability;
- future run success;
- prompt-cache behavior;
- provider cache hit/miss;
- model reasoning correctness;
- tool-call reliability;
- non-bypassable governance wrapping;
- Hermes source compliance;
- hook/CI/gate enforcement;
- framework canonical memory write;
- release readiness.

## Failure Paths or Risk Points

1. Credential leakage
   - Risk: logs or artifacts expose API keys or OAuth tokens.
   - Control: record key names only; redact provider logs; do not read `.env`.

2. Side-effectful CLI path
   - Risk: a help/config command imports code that reads config, initializes
     providers, writes caches, or prompts setup.
   - Control: static-first inspection; run no Hermes command unless the path is
     separately proven no-write and no-provider.

3. Tool execution side effect
   - Risk: the model emits a tool call and mutates files, memory, browser
     state, remote services, or subprocesses.
   - Control: first run must disable tools or use a strict read-only allowlist.

4. Output artifact ambiguity
   - Risk: the operator captures a partial stream or non-final message.
   - Control: artifact must identify `final_response_source` and capture
     boundary; partial output must be labeled partial.

5. Raw artifact submitted as `post_task` evidence
   - Risk: a raw Hermes capture artifact is passed directly as `response_file`
     even though it lacks the framework `[Governance Contract]` block required
     by the current adapter path for non-trivial post-task evidence.
   - Control: raw capture and governance response artifacts must be separated;
     direct `post_task` submission requires a wrapper or sidecar-reviewed
     response artifact with the required governance contract block.

6. Middleware overclaim
   - Risk: a cooperative hook is described as enforcement.
   - Control: all evidence packets must preserve the existing non-bypassability
     non-claim.

7. Memory authority confusion
   - Risk: Hermes internal memory or session transcript is treated as framework
     canonical memory.
   - Control: Hermes memory/transcript is runtime evidence only; canonical
     framework memory still requires `governance_tools.memory_record`.

## Evidence Plan

Before a future run:

1. Record Hermes repo identity:
   - `git rev-parse --short HEAD`
   - `git status --short --branch`
   - upstream and ahead/behind if available.

2. Static-check entrypoint and side effects:
   - inspect selected entrypoint source;
   - confirm whether it imports provider/config code before argument handling;
   - do not execute entrypoint if no-write status is uncertain.

3. Record config surface by name only:
   - provider slug;
   - model id;
   - env/config key names;
   - credential source type.

4. Define tool policy:
   - `tools_disabled` preferred;
   - otherwise `read_only_allowlist` with exact tool names;
   - write-capable tools are excluded from the first run.

5. Define output artifact destination:
   - path;
   - artifact schema;
   - redaction policy;
   - final response source.

6. Run only after separate explicit authorization:
   - no run is authorized by this plan;
   - provider/model execution requires a new DONE with credential and model-run
     authorization.

After a future run:

1. Inspect the captured artifact.
2. Create or identify the governance response artifact that references or wraps
   the raw capture and contains the required `[Governance Contract]` block if it
   will be submitted to the existing `post_task` adapter.
3. Shape an accepted-input Hermes `post_task` payload with `output_file`
   pointing at that governance response artifact, not at an unwrapped raw
   capture.
4. Run the existing Hermes adapter/post-task check only if the artifact path is
   present and contains no secrets.
5. Report evidence and non-claims separately.

## Implementation Tranche Recommendation

Recommended next tranche:

```text
DONE = perform a no-write preflight packet for one explicitly selected Hermes
provider/model run; static-first; no model execution until the operator
explicitly approves provider credential use and run command.
```

Do not implement a Hermes plugin, runtime hook, CI gate, or enforcement path
before one real no-write model/provider evidence packet exists and is reviewed.
