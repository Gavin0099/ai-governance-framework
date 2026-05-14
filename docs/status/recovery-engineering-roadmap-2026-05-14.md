# Recovery Engineering Roadmap

As-of: 2026-05-14  
Objective: move from observability-first to fault-tolerant runtime behavior.

## Workstreams

1. Rollback graph
- define rollback edges between states/actions
- mark non-recoverable edges explicitly

2. Compensating actions
- define compensation playbooks for each compensating/irreversible action class

3. Partial failure recovery
- isolate failed branch without restarting whole task
- preserve successful sub-results with consistency checks

4. State reconciliation
- checkpoint diff, authority diff, memory drift scan
- deterministic merge/reject policy

5. Deadlock breaker
- detect cyclic multi-agent dependency
- deterministic arbitration + timeout/freeze

## Milestone Gates

- M1: rollback graph defined for top 10 action paths
- M2: compensation playbooks available for all compensating classes
- M3: partial-recovery path tested in at least 3 failure classes
- M4: reconciliation workflow integrated with incident logging
- M5: deadlock breaker tested with synthetic adversarial scenarios
