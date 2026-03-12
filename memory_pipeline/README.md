# Memory Pipeline

This directory contains the first durable-memory pipeline slice.

Modules:

- `session_snapshot.py`: capture session output into `memory/candidates/`
- `memory_promoter.py`: promote reviewed candidates into `memory/03_knowledge_base.md`

Design rule:

- Candidate memory is not durable truth.
- Promotion requires an explicit reviewer identity.
