# Memory Pipeline

This directory contains the first durable-memory pipeline slice.

Modules:

- `active_task_round_trip.py`: write, resolve, retrieve, and exactly verify one
  caller-authorized active-task projection before returning canonical LF
  context bytes
- `session_snapshot.py`: capture session output into `memory/candidates/`
- `memory_curator.py`: reduce noise and produce curated runtime artifacts
- `promotion_policy.py`: classify candidate memory promotion decisions
- `memory_promoter.py`: promote reviewed candidates into `memory/03_knowledge_base.md`

Design rule:

- Candidate memory is not durable truth.
- Promotion requires an explicit reviewer identity.
- Curated artifacts should preserve proposal-time architecture impact concerns and expected evidence when available.
- Curated artifacts should also preserve `proposal_summary` recommendations, concerns, and evidence expectations when present.
- Curated artifacts should preserve domain contract context when the session ran with an external contract.
  - minimum retained fields: `contract_source`, `contract_name`, `contract_domain`, `plugin_version`
  - this keeps durable audit outputs understandable in multi-domain governance environments

R0 boundary:

- The active-task round trip consumes the canonical writer and logical resolver;
  it does not redefine either one.
- Only one exact active-task identity and projection payload can render one
  canonical context line. Malformed, missing, ambiguous, or mismatched state
  fails closed.
- Caller-admitted non-resolved authority states preserve their disposition and
  return zero context bytes.
- R0 does not provide semantic retrieval, RAG, update, supersession, deletion,
  crash recovery, MRCSP detector integration, or a public result transport
  schema.
