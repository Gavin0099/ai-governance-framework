# Known Incidents

## GI-001 - Memory Authority Misresolution

- Severity: Medium (repeated authority-boundary violation; no destructive impact observed)
- Scope: cross-repository (`usb-logic-trace-correlator`, `ai-governance-framework`)
- Status: Cross-repository recurrence observed; escalation triggered; authority semantics and bounded fixture/detector work adopted, without host-private detection or runtime enforcement for this incident.

Pattern:
- Agent resolved and wrote to an external memory path before applying repo-local governance memory authority.

Observed behavior:
- Occurrence 1 (`usb-logic-trace-correlator`): an operational record was first written outside repo-local `memory/`, then corrected after review.
- Occurrence 2 (`ai-governance-framework`, observed 2026-08-20): Claude Code wrote and indexed a persistent project-memory record outside repo-local `memory/`, although the repository already declared `external_memory_allowed: false` and `operational_records_must_stay_under_memory_root: true`.

Occurrence 2 provenance and limits:
- Preserved from [PR #80](https://github.com/Gavin0099/ai-governance-framework/pull/80), implementation commit [`688b3a69d60748f8d79103fb9a1abdbc014607ce`](https://github.com/Gavin0099/ai-governance-framework/blob/688b3a69d60748f8d79103fb9a1abdbc014607ce/governance/fleet/known_incidents.md). That incident record describes a 3,015-byte `governance-portfolio-census-2026-08-20.md` file and a private index entry, containing operational observations and future-use claim boundaries.
- The repository memory-authority declaration predates the reported write: commit `5f3911bd9` introduced the structured block on 2026-05-28; the incident records the private write as 2026-08-20.
- The private file, index and filesystem timestamps were workstation observations. They are not committed or independently replayable repository evidence. This forward-port preserves the reported observation; it does not repeat private-directory inspection or revalidate the private file.
- No destructive impact was observed in the recorded incidents. This does not establish behavior for other agents, users, hosts or repositories.

Corrective action and current capability boundary (2026-09-15):
- Initial response: add the structured `memory_authority` block and an adoption-packet prohibition on operational records outside the declared `memory_root`. Occurrence 2 demonstrates that declaring the boundary alone did not prevent this observed host-private write.
- M-1 authority semantics: adopted in main through the [memory surface authority contract](../MEMORY_SURFACE_AUTHORITY_CONTRACT.md). Canonical storage and writer provenance do not automatically make a record current truth.
- M0 fixture: separately owner-authorized on 2026-08-24 and in main. The [fixture admissibility contract](../MEMORY_RECONCILIATION_FIXTURE_ADMISSIBILITY_CONTRACT.md) admits one synthetic, redacted, test-only pair; it does not validate host-private behavior.
- M1a limited detector: in main under its [exact-byte detector contract](../MEMORY_RECONCILIATION_EXACT_BYTE_DETECTOR_CONTRACT.md). It reports raw-byte equality for two caller-admitted records; it does not scan private roots or establish real-memory reconciliation.
- Host-private write detection and runtime enforcement of this incident boundary are not provided by these deliveries. Existing repo-local checks must not be represented as observing writes they cannot access.

Escalation condition:
- Triggered on 2026-08-20: the same pattern was reported in the second repository. The original "if a second repo" condition is no longer pending.
- The adopted authority semantics, test-only fixture and limited detector do not close the host-private observation gap. Any proposed host integration must separately define host cooperation or an explicit operator entrypoint, allowed roots, privacy boundaries, a natural caller and acceptance conditions, and obtain owner authorization.
- This incident update authorizes no private scanning, retired host-memory synchronization, detector expansion, runtime integration, schema, hook, gate or enforcement change.

Claim ceiling:
- May claim: the preserved incident evidence records recurrence across two repositories and meets the documented escalation threshold; the bounded M-1/M0/M1a deliveries listed above are in main.
- Must not claim: the private evidence was independently replayed; external memory was deleted or synchronized; host-private writes are detected or prevented; all host sessions share the behavior; or GI-001 is resolved by the documentation update.
