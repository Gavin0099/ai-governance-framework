---
status: design-only
authority: proposal
phase_gate: phase-e-pause-gated
runtime_change: false
enforcement_change: false
audited_external_repo: E:/BackUp/Git_EE/hermes-agent
audited_external_head: 5bf23ff251ed54961f5560d2d2f95474dcc09386
tranche_0_chokepoint_audit: completed-read-only
tranche_0_5_final_output_audit: completed-read-only
---

# Real Hermes Integration Contract Spec

## Problem

The current Hermes support in this repository is an accepted-input adapter
scaffold. It proves that the framework can reshape a Hermes-like payload into
the shared runtime hook contract, but it does not prove that the public
`nousresearch/hermes-agent` runtime is actually governed.

The read-only audit of the real Hermes checkout at
`E:/BackUp/Git_EE/hermes-agent` found useful cooperative hook surfaces:

- CLI entrypoints in `pyproject.toml`:
  - `hermes = "hermes_cli.main:main"`
  - `hermes-agent = "run_agent:main"`
  - `hermes-acp = "acp_adapter.entry:main"`
- tool request and tool execution middleware in `hermes_cli/middleware.py`
- plugin hooks in `hermes_cli/plugins.py`
- tool invocation in `agent/agent_runtime_helpers.py`
- memory lifecycle hooks in `agent/memory_manager.py`
- cron artifacts in `cron/jobs.py` and `cron/scheduler.py`
- async delegation completion events in `tools/async_delegation.py`

The audit did not prove that any single hook is a non-bypassable chokepoint.
That uncertainty is the central integration risk.

Tranche 0 later tested that uncertainty directly. The result strengthened the
boundary: `run_tool_execution_middleware` is not a universal chokepoint at the
audited Hermes head. It is a useful cooperative hook surface, but confirmed
independent dispatch paths exist that call `handle_function_call` directly.

Tranche 0.5 then tested a separate assumption behind the proposed
`response_file` mapping: whether real Hermes naturally materializes final output
as a file. It does not for the general interactive and ACP paths observed at the
audited head. General Hermes output is stream/protocol shaped; cron output is
the only observed natural file artifact surface.

## Target Outcome

Define the contract for a future real Hermes integration without implementing
it in this slice.

The contract must allow a reviewer to distinguish:

- what Hermes can cooperatively emit or expose;
- what the framework can validate;
- what remains attestation-only;
- what is explicitly not a security boundary or non-bypassable enforcement
  claim.

## Scope

This spec covers the design boundary for a future Hermes integration pinned to
the audited external Hermes head:

```text
E:/BackUp/Git_EE/hermes-agent
5bf23ff251ed54961f5560d2d2f95474dcc09386
```

In scope:

- map Hermes tool middleware to candidate `pre_task` / `post_task` evidence
  points;
- map final assistant output to a framework-compatible `response_file`;
- classify cron output artifacts as possible evidence inputs;
- classify async delegation completion events as possible child-task evidence;
- classify memory manager hooks as observable but non-canonical relative to
  this framework's memory protocol;
- document chokepoint uncertainty as an open question;
- preserve the current accepted-input adapter claim ceiling.

## Non-goals

This spec does not:

- implement a Hermes plugin;
- modify `runtime_hooks/`;
- modify `governance_tools/`;
- modify Hermes source code;
- install or run Hermes;
- wire CI, hooks, or gates;
- claim Gate 3 is open;
- claim runtime enforcement;
- claim non-bypassability;
- claim semantic correctness;
- claim Hermes internal memory is framework canonical memory;
- claim cron, skills, delegation, or tool execution are already governed.

## Affected Surfaces

### Existing framework surfaces

- `runtime_hooks/adapters/hermes/HERMES_RUNTIME_INTERFACE.md`
- `runtime_hooks/adapters/hermes/normalize_event.py`
- `runtime_hooks/adapters/hermes/pre_task.py`
- `runtime_hooks/adapters/hermes/post_task.py`
- `runtime_hooks/examples/hermes/`
- `docs/governed-agents/hermes.md`

### External Hermes surfaces observed at audited head

- `pyproject.toml`
- `run_agent.py`
- `hermes_cli/middleware.py`
- `hermes_cli/plugins.py`
- `agent/agent_runtime_helpers.py`
- `agent/tool_executor.py`
- `agent/memory_manager.py`
- `tools/approval.py`
- `tools/async_delegation.py`
- `tools/process_registry.py`
- `tools/cronjob_tools.py`
- `cron/jobs.py`
- `cron/scheduler.py`
- `tools/skills_tool.py`
- `agent/curator.py`

These external surfaces are point-in-time observations. Any future
implementation must re-audit them against the then-current Hermes commit or pin
the dependency to `5bf23ff`.

## Boundary and API Considerations

### 1. Cooperative hook, not proven gate

Hermes exposes behavior-changing middleware:

- `apply_tool_request_middleware`
- `run_tool_execution_middleware`

It also exposes plugin hooks including `pre_tool_call` and `post_tool_call`.
These are the most promising integration points, but they are cooperative
surfaces: Hermes calls them. They are not proven non-bypassable boundaries.

Contract rule:

```text
Middleware may be used as an observation and shaping point.
Middleware must not be described as a gate unless a separate chokepoint audit
proves every tool execution path flows through it.
```

### 2. Chokepoint uncertainty

The initial audit proved at least one tool path reaches
`run_tool_execution_middleware`, but did not prove it is the only path.

Tranche 0 read-only chokepoint audit found:

- `handle_function_call` is the broader dispatch surface
  (`model_tools.py:876` at audited Hermes head).
- `run_tool_execution_middleware` wraps only a subset of paths and should not
  be treated as the dispatch authority.
- independent entry paths directly call `handle_function_call`, including:
  - `tools/code_execution_tool.py:561`
  - `tools/code_execution_tool.py:834`
  - `agent/transports/hermes_tools_mcp_server.py:158`
- some `agent/tool_executor.py` branches use execution middleware helpers, but
  the call graph is not a single enforced middleware rail.

Conclusion:

```text
No single proven Hermes tool-execution chokepoint exists at audited head
5bf23ff. Enforcement-by-single-hook is structurally unsupported by the
observed call graph.
```

Open question:

```text
OQ-HERMES-1: Can Hermes expose or accept a single explicit governance
observation surface for all tool execution paths without relying on
run_tool_execution_middleware as a universal gate?
```

Until this is answered, the integration claim ceiling remains:

```text
cooperative observation / attestation boundary
```

not:

```text
non-bypassable runtime enforcement
```

### 3. Response file mapping

The framework's Hermes accepted-input adapter requires `post_task` evidence to
include `response_file` or an accepted alias such as `output_file`.

Tranche 0.5 read-only final-output materialization audit found that real Hermes
does not generally emit such a file:

- interactive CLI output is printed to stdout by the conversation loop;
- ACP output is returned as a protocol message carrying final response content;
- final-response text is built in memory before emission;
- cron jobs naturally write markdown output under Hermes cron output storage;
- no general `--response-file` / `--output-file` style final-response artifact
  path was observed.

Therefore the existing `response_file` contract remains valid for this
framework's adapter, but it is not naturally satisfied by real Hermes general
execution. A real integration must choose one of these routes:

1. cron-artifact attestation:
   - treat Hermes cron output markdown files as evidence;
   - limited to cron/scheduled work;
   - no general interactive/ACP coverage claim.
2. stream / ACP capture adapter:
   - capture stdout or ACP final-response protocol content;
   - write a framework-compatible response artifact;
   - new component, not proven by existing fixtures.

Future Hermes integration should write or provide a response artifact containing
at least:

- `session_id` as the primary trace axis for audited Hermes head `5bf23ff`;
- `thread_id` when available as secondary correlation;
- `run_id` when available as an optional run marker;
- final output source type:
  - `stdout_stream` for interactive CLI capture;
  - `acp_final_response` for ACP protocol capture;
  - `cron_output_file` for Hermes cron markdown artifacts;
- capture boundary:
  - `native_file_artifact` for cron output;
  - `stream_capture_adapter` for stdout capture;
  - `protocol_capture_adapter` for ACP final-response capture;
- source path or capture destination if a file is produced;
- audited Hermes commit or runtime version;
- capture timestamp if generated by a wrapper.

Trace-id rule:

```text
Use session_id as the primary correlation key. thread_id may supplement it.
run_id may be recorded when present. Do not use conversation_id as the primary
id for real Hermes integration at audited head 5bf23ff; it was not observed as
the dominant trace field.
```

- final assistant response;
- model/provider if available;
- tool call summary if available;
- middleware trace if available;
- source Hermes commit or runtime version if available.

This artifact can then be passed to the existing Hermes `post_task` adapter as
`response_file`.

Non-claim:

```text
The response_file proves what was emitted as final output. It does not prove the
output is true, complete, or semantically correct.
```

Additional non-claim:

```text
Real Hermes general execution does not currently prove native response_file
emission. Any response_file for interactive or ACP paths requires an explicit
capture adapter or wrapper.
```

### 4. Cron evidence

Hermes cron jobs store scheduled job metadata and output under Hermes home:

- `~/.hermes/cron/jobs.json`
- `~/.hermes/cron/output/<job_id>/<timestamp>.md`

Future integration may treat cron output files as evidence artifacts, but only
with explicit provenance:

- job id;
- job name;
- scheduled vs manual run;
- run timestamp;
- delivery status;
- output path;
- error / delivery_error if any.

Non-claim:

```text
Cron output proves a Hermes cron execution produced a file. It does not prove
the job was governed end-to-end or that delivery succeeded unless delivery
status is explicitly present.
```

### 5. Async delegation evidence

Hermes async delegation pushes completion events to
`process_registry.completion_queue` with `type="async_delegation"`.

Future integration may ingest these events as child-task evidence if the event
contains:

- delegation id;
- parent session key;
- goal;
- role/toolsets/model;
- status;
- summary or error;
- dispatched/completed timestamps.

Non-claim:

```text
An async delegation completion event proves a child result was reported back to
the parent rail. It does not prove the child was governed unless the child
session also emits compatible governance evidence.
```

### 6. Memory non-claims

Hermes memory has several surfaces:

- SQLite session persistence;
- external memory provider sync;
- `memory` tool writes;
- provider `on_memory_write`;
- provider `on_session_end`;
- provider `on_delegation`.

These are Hermes runtime memory surfaces. They are not this framework's
canonical memory protocol.

Contract rule:

```text
Hermes memory events may be observed as runtime evidence.
They must not be treated as framework canonical memory unless they are converted
through governance_tools.memory_record or another explicitly approved canonical
writer.
```

## Failure Paths or Risk Points

1. Middleware bypass
   - Risk: a tool path bypasses `run_tool_execution_middleware`.
   - Evidence: Tranche 0 confirmed direct `handle_function_call` call paths
     outside the execution middleware wrapper.
   - Consequence: integration observes only some tool execution if it relies on
     that middleware alone.
   - Required before enforcement claim: a different single explicit governance
     surface or upstream runtime change; current call graph does not support a
     single-hook enforcement claim.

2. Plugin registration drift
   - Risk: Hermes plugin APIs change after audited head.
   - Consequence: integration silently stops observing hooks.
   - Required mitigation: pin or re-audit external Hermes head.

3. Response artifact missing
   - Risk: real Hermes general execution emits final output as stream/protocol
     content rather than a file.
   - Evidence: Tranche 0.5 found stdout/ACP final-response emission for general
     paths and natural file output only for cron artifacts.
   - Consequence: framework `post_task` evidence cannot be grounded in real
     Hermes output unless output is captured or cron artifacts are in scope.
   - Required mitigation: choose cron-artifact attestation or build an explicit
     stream/ACP capture adapter before claiming real-output response_file
     alignment.

4. Cron / delegation detached execution
   - Risk: scheduled or async work completes outside the parent session's
     normal final-response path.
   - Consequence: parent response_file omits real work.
   - Required mitigation: capture cron and delegation evidence separately.

5. Memory authority confusion
   - Risk: Hermes memory is mistaken for framework canonical memory.
   - Consequence: non-canonical memory writer regression.
   - Required mitigation: keep memory non-claims explicit.

6. Security-boundary overclaim
   - Risk: cooperative hooks are described as enforcement.
   - Consequence: same failure class as prior source-hook vs installed-hook and
     checker-vs-CI-trigger overclaims.
   - Required mitigation: label integration as observation/attestation until
     non-bypassability is proven.

## Evidence Plan

Before any implementation tranche:

1. Reconfirm external Hermes head.
   - Evidence: exact commit hash.

2. Chokepoint audit.
   - Status: completed read-only for audited head `5bf23ff`.
   - Evidence: call graph spot-check confirmed independent direct
     `handle_function_call` paths and partial execution middleware coverage.
   - Result: `run_tool_execution_middleware` must not be described as a
     universal gate.

3. Response artifact dry-run.
   - Status: not yet valid for real Hermes general paths.
   - Evidence needed: either a cron output artifact fixture from the audited
     Hermes shape, or a stream/ACP capture fixture that explicitly models the
     new capture adapter boundary.
   - Non-evidence: a fixture that merely uses framework aliases such as
     `assistant_response_path` without proving that real Hermes emits those
     fields.

4. Cron artifact sample.
   - Evidence: fixture or copied sample output, not live secrets.

5. Async delegation sample.
   - Evidence: fixture event matching `type="async_delegation"` shape.

6. Memory classification test.
   - Evidence: documentation or test proving Hermes memory events are classified
     as runtime observations, not canonical framework memory.

No live Hermes secrets, network services, gateway sessions, or scheduled jobs
are required for the first implementation tranche.

## Implementation Tranche Recommendation

### Tranche 0: Read-only chokepoint audit

Completed as a read-only audit.

DONE:

```text
Audit whether all Hermes tool execution paths at audited HEAD 5bf23ff pass
through run_tool_execution_middleware; produce a path table only.
```

Result:

```text
run_tool_execution_middleware is not a universal chokepoint. Confirmed
independent direct dispatch paths call handle_function_call outside that
middleware surface. Hermes integration remains observation/attestation only.
```

Non-goals:

- no code changes;
- no plugin implementation;
- no governance adapter changes;
- no enforcement claim.

### Tranche 1: Fixture-only response_file contract

Only after Tranche 0.5 and explicit approval.

Do not add a fixture that claims to be real-Hermes-shaped unless its payload
shape is grounded in one of the two observed output routes:

- cron output markdown artifact; or
- an explicit stream/ACP capture adapter contract.

Rejected fixture direction:

```text
Do not label a framework-alias accepted-input fixture as real-Hermes-shaped
merely because it carries audit metadata. Alias mapping tests are useful, but
they do not prove real Hermes output shape.
```

Preferred next design decision:

```text
Choose Tranche 1A cron-artifact attestation or Tranche 1B stream/ACP capture
adapter before adding new fixtures.
```

### Tranche 1 route decision

Decision date: 2026-06-22

Decision:

```text
Proceed with Tranche 1A first: cron-artifact attestation.
Defer Tranche 1B: stream / ACP capture adapter.
```

Decision matrix:

| Route | Evidence surface | Coverage | Implementation cost | Claim risk | Decision |
|---|---|---|---|---|---|
| Tranche 1A: cron-artifact attestation | Native Hermes cron markdown output under cron output storage | Cron / scheduled work only | Low | Low | Proceed first |
| Tranche 1B: stream / ACP capture adapter | Captured stdout or ACP `final_response` protocol content written to framework `response_file` | Interactive / ACP paths | Medium / high | Medium / high | Defer |

Rationale:

- Tranche 1A uses the only naturally materialized file artifact observed in
  Tranche 0.5.
- Tranche 1A does not require wrapping Hermes stdout, ACP protocol handling, or
  tool dispatch.
- Tranche 1A preserves the current observation / attestation claim ceiling.
- Tranche 1B would require a new capture component and has higher risk of being
  misread as runtime governance or enforcement.

Tranche 1A allowed scope:

- add a cron-output-shaped fixture grounded in the audited Hermes cron artifact
  path shape;
- test that the existing Hermes `post_task` adapter can consume that fixture as
  a framework-compatible response artifact;
- record provenance fields needed for reviewer attestation:
  - `session_id` if available;
  - cron job id;
  - cron job name if available;
  - output markdown path;
  - run timestamp;
  - audited Hermes commit;
  - source type `cron_output_file`.

Tranche 1A non-claims:

- no interactive / ACP coverage;
- no stream capture;
- no runtime enforcement;
- no tool-execution non-bypassability;
- cron provenance fields are fixture-resident reviewer-facing fields only;
  they are not propagated, parsed, or machine-attested by the Hermes adapter in
  this tranche;
- no claim that cron job delivery succeeded unless delivery status is present;
- no claim that cron output is semantically correct.

Tranche 1B remains a separate future decision. It must not be inferred from
Tranche 1A success.

Claim ceiling:

```text
fixture-backed response_file mapping exists for the selected output route only
```

not:

```text
real Hermes final responses are governed
```

### Tranche 2: Cooperative observer plugin prototype

Only after Tranche 1 and explicit owner approval.

Build a Hermes plugin that records middleware/tool observations and writes a
response artifact. It must be disabled by default and must not claim
non-bypassability.

### Tranche 3: Enforcement decision

Out of scope for this spec.

Any move from observation/attestation to blocking enforcement requires a
separate OP-HC decision with false-positive risk, rollback path, and
non-bypassability evidence.

## Claim Ceiling

Supported by this spec:

- real Hermes integration has identified cooperative hook surfaces;
- audited external head is pinned to `5bf23ff`;
- Tranche 0 confirmed `run_tool_execution_middleware` is not a universal
  chokepoint;
- Tranche 0.5 confirmed real Hermes general final output is stream/protocol
  shaped, with cron output as the observed natural file artifact surface;
- response_file, cron output, async delegation, and memory observation
  boundaries are defined;
- chokepoint uncertainty is explicit.

Not supported by this spec:

- real Hermes governance is implemented;
- Hermes tool execution is non-bypassable;
- `run_tool_execution_middleware` is a universal tool-execution gate;
- `handle_function_call` is safe to monkey-patch or treat as governance
  authority;
- real Hermes general execution naturally emits `response_file`;
- a framework-alias accepted-input fixture is real-Hermes-shaped without
  output-materialization evidence;
- Hermes memory is canonical framework memory;
- cron or async delegation are governed;
- Gate 3 is open;
- runtime enforcement or CI enforcement changed;
- semantic correctness is verified.
