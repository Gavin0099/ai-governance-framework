# Cache-Aware Agent Harness Design Note

Status: PENDING
Date: 2026-06-27
Scope: governance design note only
Sources:
- Anthropic, "Lessons from building Claude Code: prompt caching is everything"
  https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything
- Anthropic pricing documentation
  https://docs.anthropic.com/en/docs/about-claude/pricing

## Purpose

This note captures a pending governance interpretation of Anthropic's Claude
Code prompt-caching architecture. It is not an adopted runtime rule, not a
permission model change, and not evidence that this repository's harness already
implements cache-aware execution.

This note is based on Anthropic Claude prompt-caching semantics. Other model
providers may expose different cache behavior, cache lifetimes, cache keys, or
pricing models. Cross-provider adoption requires separate validation.

The main lesson is that long-running coding agents should be designed around
cache hit rate, not merely around shorter prompts. Prompt caching is prefix
based: stable content at the beginning of the request can be reused, while small
changes near the front can invalidate a large cached prefix.

As of this note, Anthropic pricing treats cache reads as lower-cost input than
ordinary input, while cache writes are priced above ordinary input depending on
cache duration. That supports treating cache stability as an efficiency concern,
not as a safety or correctness authority.

## Core Observation

For long-task agents, prompt caching is a harness architecture concern.

The stable prefix should contain durable, deterministic material:

- system instructions;
- fixed tool definitions or stable tool stubs;
- stable repository authority files, identified by path, content hash, and base
  ref;
- governance protocol summaries that do not change during the task.

Dynamic or high-churn material should appear later:

- current user request;
- current branch, HEAD, and base commit;
- authority-file hash changes;
- dirty tree status or summarized dirty-tree receipt;
- command outputs;
- reviewer receipts;
- closeout candidates;
- memory updates;
- current evidence and claim ceiling.

The design goal is not simply "fewer tokens." A better goal is:

```text
large stable prefix + dynamic tail + auditable state transitions
```

## Governance Translation

The article maps cleanly onto this repository's agent workflow:

| Agent concern | Cache-aware design pressure | Governance boundary |
| --- | --- | --- |
| Mode changes | Avoid changing tool schemas mid-session | Mode must be represented by protocol state and runtime gates |
| Review work | Use sub-agents for bounded skeptical review | Sub-agent returns receipt; main thread owns action |
| Tool overload | Use deferred tool loading or stable stubs | Tool discovery must not become hidden authority escalation |
| Compaction | Preserve the same prefix when summarizing | Summary must retain authority, evidence, dirty state, and claim ceiling |
| Memory | Treat memory writes as dynamic artifacts | Memory must still use canonical writer and protocol checks |
| Push / mutation | Do not encode permission only in prompt text | Runtime permission gate remains separate from cache stability |

## Proposed Local Principle

```text
Cache stability is an efficiency requirement.
Runtime permission is a safety requirement.
Do not trade one for the other.
```

This means the system may keep tool schemas stable for cache reasons, but write,
push, destructive action, memory mutation, and authority changes must still be
controlled by explicit runtime gates, repo rules, and user authorization where
applicable.

## Safety Invariant

Cache stability must never preserve stale authority or bypass runtime safety.
The harness should intentionally invalidate or bypass cache when repository
authority, permission policy, tool schema, model identity, branch or base commit,
or user authorization state changes.

A cache miss caused by correctness, freshness, or safety is expected behavior,
not an operational failure.

Stable tool visibility is not operational authorization. A tool may remain
visible for cache stability while still being unavailable at runtime due to
mode, repo policy, user authorization, dirty-tree constraints, or side-effect
class.

## Candidate Implications If Adopted

### 1. Sub-agent review should be preferred for non-trivial work

If this note is adopted, bounded sub-agent review should become the preferred
review mechanism for non-trivial, claim-sensitive, mutation-adjacent, or
governance-sensitive work, subject to tool availability and runtime permission
gates.

If the harness provides a bounded sub-agent API, the main thread should use the
canonical spawn, wait, input, and close lifecycle defined by the operator
playbook. For the current harness candidate, this may correspond to
`multi_agent_v1.*` where available.

The main thread should:

- send a bounded read-only task;
- wait for a structured `REVIEW_RECEIPT`;
- spot-check load-bearing evidence;
- decide whether to fix, commit, request push authorization, or stop.

The sub-agent should not own commit, push, memory write, or final claim
authority.

Candidate minimum receipt shape:

```text
REVIEW_RECEIPT v1
scope:
base_ref:
artifacts_read:
commands_run:
evidence:
findings:
unsupported_claims:
not_checked:
risk:
recommendation:
```

The reviewer must not return only "looks good." It must produce an auditable
receipt that names the evidence checked and the claims it does not support.

### 2. Sidebar threads are not the default review path

Visible sidebar Codex threads are useful when the user explicitly wants a
separate user-visible thread. They should not be silently substituted for
sub-agent tools.

If sub-agent tools are unavailable, the main thread should report that
limitation before using any fallback.

### 3. Modes should be stable protocol state, not tool-list churn

Review mode, implementation mode, diagnosis mode, and push-gate mode should not
require changing the tool schema whenever possible. The safer design is:

- stable tool definitions or deferred tool stubs;
- explicit mode markers in the dynamic tail;
- runtime permission checks for writes, pushes, and destructive actions.

### 4. Compaction must preserve governance semantics

A cache-safe compaction is not merely shorter text. It must carry forward:

- current user intent;
- base branch, HEAD commit, and last verified commit;
- committed and uncommitted scope;
- dirty tree exclusions;
- files intentionally excluded from scope;
- evidence checked;
- tests or commands run, with pass, fail, or unknown status;
- tests or checks explicitly not run;
- review receipt status;
- open risks and unresolved reviewer findings;
- claim ceiling;
- cannot-claim list;
- pending authorization boundaries;
- next allowed action;
- next forbidden action.

Dropping these fields can make the next session cheaper while making its claims
less reliable.

### 5. Tool search is an architecture feature

Deferred tool loading is not just convenience. It can reduce context churn and
protect the stable prefix from large or changing schemas.

However, tool discovery must remain auditable. Loading a tool must not be
treated as authorization to use it for mutation, cross-repo writes, push, or
external side effects.

Candidate audit record for deferred tool discovery:

- tool name;
- tool version or schema hash;
- reason for loading;
- requesting thread or agent;
- side-effect class;
- permission gate consulted;
- whether user authorization was required;
- whether mutation was attempted or blocked.

## Glossary

- Claim ceiling: the strongest claim this session can support from its evidence.
- Runtime gate: a harness or repository check that controls whether a side
  effect is allowed.
- Authority files: repo-local instructions and governance files whose content
  determines execution rules.
- Dirty-tree receipt: a summarized record of modified, staged, and untracked
  files, including explicit exclusions from scope.
- Canonical writer: the approved tool or path for writing structured governance
  memory or records.

## Non-Goals

This note does not:

- change runtime permissions;
- add or remove tools;
- alter memory protocol;
- authorize push automation;
- authorize reviewer sub-agents to mutate files;
- prove that current sessions achieve good cache hit rates;
- define an incident threshold for cache misses;
- prefer cache stability over correctness, freshness, or safety;
- require preserving stale authority files for cache hit rate;
- make Anthropic-specific cache behavior a cross-provider assumption;
- define tool visibility as permission to execute a tool;
- make sub-agent review mandatory for trivial or low-risk work.

## Open Questions

Before adopting this as a formal governance rule, decide:

- Which prompt layers are considered stable prefix in this harness?
- Which fields must always remain in compaction summaries?
- Should cache hit rate become a monitored operational signal?
- What is the minimum acceptable receipt shape for sub-agent review?
- Which tool schemas should be stable stubs versus deferred full definitions?
- Where should runtime permission gates live so they are independent of prompt
  obedience?
- Which changes must intentionally invalidate the stable prefix?
- How are authority-file versions, hashes, and base refs represented?
- Which dynamic-tail messages are harness-authored versus model-authored?
- How are mode markers protected from user spoofing?
- What audit record is required when a deferred tool schema is loaded?
- Which tasks require sub-agent review, and which are exempt as trivial?

## Pending Disposition

Recommended next step:

```text
Keep this note as PENDING, revise through review, then decide whether to promote
a smaller operator-playbook rule and a separate harness-design spec.
```

Promotion requires removing adopted-rule ambiguity, preserving the safety
invalidation invariant, defining a minimum receipt shape, and separating
provider-specific cache assumptions from local policy.

Until that review and promotion decision happens, this document is pending
analysis only.
