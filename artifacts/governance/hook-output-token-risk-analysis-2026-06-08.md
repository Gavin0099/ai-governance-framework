# HOOK-OBS-1 Hook Output Token-Risk Analysis - 2026-06-08

## Scope

Advisory-only analysis of runtime hook, pre-task, post-task, and session-end
output surfaces that may create high-token / low-value agent-visible noise.

This artifact does not change hook output behavior, validators, schemas,
runtime behavior, CodeBurn ingestion, Minimal Rule Selection, router audit, or
enforcement behavior.

## Current Output Source Inventory

| source_file | hook_stage | output_type | agent_visible | artifact_path | known_output_fields | token_risk | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `runtime_hooks/core/session_start.py` | session_start | human lines / JSON / audit log | yes | yes | `ok`, `rules`, `contract_source`, `suggested_rules_preview`, `warnings`, `proposal_summary`, `validator_preflight` | high | Human output can include suggested rules, warnings, proposal details, and contract context. |
| `runtime_hooks/core/pre_task_check.py` | pre_task | structured result consumed by session_start | indirect | no/unknown | warnings, suggestions, advisory signals, impact preview, boundary effects | medium-high | Warning strings can become session_start output and may repeat repo-signal detail. |
| `runtime_hooks/core/post_task_check.py` | post_task | hook result / snapshot context | yes/unknown | yes | post-task status, runtime context, artifact references | medium | Mostly useful when concise; risky if full context is emitted inline. |
| `runtime_hooks/core/session_end.py` | session_end wrapper | closeout / runtime packet emission | yes | yes | session result, closeout paths, runtime packet references | medium | Should prefer artifact paths over inline packet content. |
| `governance_tools/session_closeout_entry.py` | closeout helper | closeout entry / receipt path context | yes/unknown | yes | closeout fields, evidence refs, receipt paths | medium | Useful for closeout, but full field echo can be noisy. |
| `governance_tools/session_end_hook.py` | session_end | human result / JSON / warnings / gate summary | yes | yes | `ok`, `gate_verdict`, `codeburn_token_summary`, `closeout_status`, `warnings`, `errors`, `gate_policy`, `canonical_path_audit`, `memory_authority` | high | Human output is broad and can include many advisory blocks. Highest risk when full output is pasted back to agent. |

## Token-Risky Output Patterns

| pattern | example source | risk | why risky | recommended output style |
| --- | --- | --- | --- | --- |
| Full smoke logs inline | pre-push runtime-governance smoke output | high | Long repeated blocks for multiple harnesses are often not decision-relevant after PASS. | One-line status plus artifact path. |
| Full JSON artifact inline | `session_start.py --format json`, `session_end_hook.py --format json` | high | Large structured payloads inflate prompt tokens and obscure the few fields needed by reviewers. | Store JSON artifact; print hash/path/counts. |
| Repeated rule / contract previews | `suggested_rules_preview`, active rules, expected validators | medium-high | Same rule lists repeat across session_start/pre_task outputs. | Emit changed/missing items only. |
| Repeated warning strings with repo signals | pre_task suggestions forwarded into session_start output | medium-high | Warnings include file lists and may repeat every run. | Emit warning count plus top 1-3 codes; full detail in artifact. |
| Full closeout field echo | session_end / closeout helper | medium | Useful for one closeout but expensive when pasted into next prompt. | Print result, blocker, artifact path, and not-claimed summary. |
| Complete artifact content in final response | manual closeout or push summaries | high | Duplicates committed artifacts in chat context. | Link file path and summarize key fields. |

## Advisory Hook Output Summary Contract Draft

This is a proposal only. No hook output behavior changed in this phase.

```yaml
hook_output_summary_contract:
  mode: advisory_proposal
  enforcement: not_claimed
  applies_to:
    - session_start
    - pre_task_check
    - post_task_check
    - session_end
  proposed_output_shape:
    - one-line status
    - warning count
    - artifact path
    - next required action
    - fixed status enum
  avoid_inline:
    - full smoke logs
    - full JSON artifacts
    - repeated rule text
    - full validator details unless failure requires it
```

Target human shape:

```text
Hook result: PASS | WARN | FAIL | NOT RUN
Relevant routers: [...]
Warnings: <count>
Artifact: <path>
Required action: <one line | none>
Not claimed: <short list>
```

## CodeBurn Before/After Measurement Protocol

This protocol is for future observation only. Token reduction is NOT CLAIMED.

Baseline collection:

- collect at least 10 current sessions;
- prefer 15 current sessions;
- classify by task type:
  - review
  - implementation
  - closeout
  - memory/write
  - governance update
  - push-only sync
- record prompt/completion tokens where provider logs expose them;
- keep Class C observation-only semantics;
- do not compare across providers as billing truth;
- do not treat one session delta as evidence.

After-change comparison rules:

- compare same task type only;
- compare same or similar model/runtime only;
- report median and range, not a single sample;
- mark provider/model/runtime drift when present;
- keep `total_tokens` absent unless a future separate contract redefines it;
- token reduction is NOT CLAIMED until after comparable before/after data exists.

Measurement thresholds:

```text
minimum_baseline_samples = 10
preferred_baseline_samples = 15
minimum_after_samples = 10
comparison_metric = median prompt_tokens / completion_tokens by task_type
```

## Minimal Protocol Bundle Deferral

Minimal protocol bundle proposal is deferred.

Reasons:

- agent actual protocol-file loading is not directly observable from current data;
- current evidence supports hook output analysis, not context bundle optimization;
- AGENTS router-preserving split may already reduce instruction surface noise;
- bundle proposal requires CodeBurn baseline data first.

Deferred condition:

- 10-15 sessions classified by task type;
- observed token-heavy task categories;
- evidence that hook/pre-task output meaningfully contributes to prompt token load.

## Claim Ceiling

CLAIMED:

- current hook/pre-task/session output sources inventoried at advisory level;
- high-token / low-value output patterns identified;
- advisory-only hook output summary contract draft defined;
- CodeBurn before/after measurement protocol defined;
- Minimal protocol bundle proposal deferred.

NOT CLAIMED:

- token usage reduced;
- MRS classifier exists;
- Minimal Rule Selection is operational;
- agent context is hard-constrained;
- hook output behavior changed;
- validators changed;
- schemas changed;
- runtime behavior changed;
- router audit exists;
- high-risk path checker exists;
- minimal protocol bundles validated;
- CodeBurn billing truth;
- cross-provider token comparability;
- future HOOK-OBS or HOOK-OPT phases committed.
