---
status: template
authority: proposal
runtime_change: false
enforcement_change: false
credential_use: false
model_run: false
hermes_source_change: false
---

# First Real Hermes Model-Run Preflight Packet Template

## Purpose

This template defines the evidence packet that must be filled before the first
real Hermes model/provider run is authorized for governance evidence collection.

It is a preflight packet only. It does not authorize credential use, a provider
call, a Hermes CLI invocation, a model run, wrapper implementation, runtime
adapter changes, hook changes, CI changes, gate changes, or enforcement changes.

## Use Rules

- Fill this packet before requesting approval for a real provider/model run.
- Record credential key names only. Never record or print credential values.
- Keep `provider_run_authorized: false` until a later explicit instruction
  authorizes provider credential use and model execution.
- Do not run Hermes CLI commands from this template.
- Do not treat this packet as proof of provider safety, Hermes validation,
  runtime governance, tool-call governance, or prompt-cache behavior.
- The raw Hermes capture artifact is not automatically a governance
  `post_task response_file`.
- A governance wrapper or sidecar response artifact is required before a
  non-trivial Hermes output can be passed through the current `post_task`
  adapter path as a response file.

## Packet Template

```yaml
packet_schema: hermes_real_model_run_preflight.v0.1
packet_status: draft
provider_run_authorized: false
operator_approval_required: true
review_required_before_run: true
created_at: "<YYYY-MM-DDTHH:MM:SS+TZ>"
created_by: "<operator-or-agent>"
claim_ceiling: preflight_packet_only_not_provider_safety

hermes_checkout:
  repo_path: "E:/BackUp/Git_EE/hermes-agent"
  head: "<short-or-full-commit>"
  branch: "<branch>"
  upstream: "<remote>/<branch-or-none>"
  ahead_behind: "<ahead>/<behind-or-unknown>"
  dirty_state_summary: "<clean | dirty-summary>"
  untracked_artifacts_policy: "<keep | ignore | archive-before-run | blocker>"
  notes: []

entrypoint:
  candidate: "<hermes | hermes-agent | hermes-acp>"
  source_file: "<path-to-entrypoint-source>"
  static_no_write_assessment: "<summary-from-source-inspection>"
  cli_execution_allowed_in_preflight: false
  no_provider_import_path_proven: "<true | false | unknown>"
  notes: []

provider_model:
  provider_id: "<provider-id>"
  model_id: "<model-id>"
  api_mode: "<chat | responses | acp | other>"
  credential_source_type: "<env | config | profile | other>"
  credential_key_names:
    - "<KEY_NAME_ONLY>"
  credential_value_policy: never_record_never_print
  secret_value_read: false
  notes: []

tool_policy:
  mode: tools_disabled
  write_capable_tools_allowed: false
  mcp_dispatch_allowed: false
  browser_or_terminal_tools_allowed: false
  filesystem_write_allowed: false
  network_targets_allowed:
    - "<provider-api-only-after-explicit-approval>"
  read_only_allowlist: []
  notes: []

prompt:
  intent: "<minimal deterministic smoke prompt>"
  prompt_text_or_redacted_summary: "<prompt text or summary>"
  prompt_hash: "<sha256-after-finalization>"
  expected_response_shape: "<short final answer, no tool call>"
  notes: []

raw_capture_artifact:
  path: "<artifact-path-after-run>"
  artifact_schema: "<stdout_stream | acp_event_log | transcript | session_record | other>"
  capture_boundary: "<stdout | acp_final_response | transcript | session_record>"
  final_response_source: "<field-or-event-name>"
  redaction_status: "<not-needed | redacted | pending-review>"
  expected_sha256_after_run: "<sha256-after-run>"
  contains_governance_contract_block: "<true | false | unknown>"
  post_task_response_file_eligible: false
  notes:
    - "Raw capture proves capture only; it is not automatically framework-compliant response evidence."

governance_response_artifact:
  path: "<wrapper-or-sidecar-path-after-run>"
  wrapper_or_sidecar: "<wrapper | sidecar>"
  contains_governance_contract_block: required_if_post_task_response_file
  source_artifact_path: "<raw-capture-artifact-path>"
  source_artifact_sha256: "<sha256-after-run>"
  provenance_preserved: "<true | false | unknown>"
  post_task_response_file_eligible: "<true | false | unknown>"
  not_claimed:
    - raw_capture_is_framework_compliant_by_default
    - wrapper_implementation_exists_from_this_template
    - adapter_acceptance_without_contract_block
  notes: []

adapter_payload:
  path: "<candidate-post-task-payload-path>"
  event_name: post_task
  output_file_points_to: governance_response_artifact
  response_file_points_to: governance_response_artifact
  run_id: "<run-id>"
  memory_mode: candidate
  oversight: review-required
  adapter_execution_authorized: false
  notes:
    - "Do not run the adapter until the governance response artifact has been reviewed for secrets and contract shape."

pre_run_stop_conditions:
  - dirty_or_untracked_state_not_accepted
  - credential_key_name_not_identified
  - credential_value_would_be_read_or_printed
  - cli_path_not_proven_no_write_before_provider_call
  - tool_disablement_not_available
  - raw_capture_path_not_defined
  - governance_wrapper_or_sidecar_path_not_defined
  - provider_run_authorized_not_true
  - reviewer_has_not_approved_this_packet

future_command_placeholder:
  command: "<not authorized by this template>"
  may_execute_only_after: "separate explicit DONE authorizing provider credential use and model run"
  expected_write_targets: "<none outside declared artifact paths>"
  expected_network_target: "<provider endpoint only>"

post_run_review_required:
  inspect_raw_capture_artifact: true
  inspect_governance_wrapper_or_sidecar: true
  verify_no_secret_values_in_artifacts: true
  verify_raw_capture_hash_matches_packet: true
  verify_wrapper_references_raw_capture_hash: true
  run_post_task_adapter_only_after_artifact_review: true
  commit_or_memory_write_authorized_by_this_packet: false

not_claimed:
  - real_hermes_validation
  - provider_safety_approval
  - provider_reliability
  - future_run_success
  - semantic_correctness
  - tool_call_governance
  - non_bypassable_enforcement
  - prompt_cache_behavior
  - hook_ci_gate_or_enforcement_change
  - canonical_memory_write
  - release_readiness
```

## Review Checklist

- The packet names the exact Hermes checkout, commit, branch, upstream, and dirty
  state.
- The packet lists credential key names only and confirms no credential values
  were read, printed, copied, or stored.
- The packet keeps tool execution disabled for the first real model/provider
  evidence run unless a later reviewed packet explicitly changes that policy.
- The packet identifies the raw capture artifact path and final response source.
- The packet identifies the governance wrapper or sidecar artifact path before
  any `post_task` adapter run is attempted.
- The packet states that a non-trivial `post_task response_file` must contain a
  `[Governance Contract]` block under the current adapter behavior.
- The packet keeps `provider_run_authorized: false` until a later explicit
  operator instruction authorizes provider credential use and model execution.

## Non-Claims

This template does not prove that Hermes can safely run a provider model, that
the selected provider or model is reliable, that the Hermes runtime is governed,
that tool calls are non-bypassable, that a wrapper or sidecar implementation
exists, that prompt caching is implemented, or that any release is ready.

The only claim supported by this file is that a preflight packet format exists
for reviewing the first real Hermes model-run evidence attempt before any
provider execution.
