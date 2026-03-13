# Memory Pipeline

This directory contains the first durable-memory pipeline slice.

Modules:

- `session_snapshot.py`: capture session output into `memory/candidates/`
- `memory_curator.py`: reduce noise and produce curated runtime artifacts
- `promotion_policy.py`: classify candidate memory promotion decisions
- `memory_promoter.py`: promote reviewed candidates into `memory/03_knowledge_base.md`

Design rule:

- Candidate memory is not durable truth.
- Promotion requires an explicit reviewer identity.
- Curated artifacts should preserve proposal-time architecture impact concerns and expected evidence when available.
