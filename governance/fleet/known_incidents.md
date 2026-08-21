# Known Incidents

## GI-001 - Memory Authority Misresolution

- Severity: Medium (repeated authority-boundary violation; no destructive impact observed)
- Scope: cross-repository (`usb-logic-trace-correlator`, `ai-governance-framework`)
- Status: Recurred across repositories; escalation condition met; owner decision on framework-level validation pending

Pattern:
- Agent resolved and wrote to an external memory path before applying repo-local governance memory authority.

Observed behavior:
- Occurrence 1 (`usb-logic-trace-correlator`): an operational record was first written outside repo-local `memory/`, then corrected after review.
- Occurrence 2 (`ai-governance-framework`, observed 2026-08-20): Claude Code wrote and indexed a persistent project-memory record under `C:\Users\<user>\.claude\projects\E--BackUp-Git-EE-ai-governance-framework\memory\` even though this repository already declared `external_memory_allowed: false` and `operational_records_must_stay_under_memory_root: true`.

Occurrence 2 evidence boundary:
- Workstation inspection confirmed a 3,015-byte `governance-portfolio-census-2026-08-20.md` file and an entry for it in the adjacent private `MEMORY.md`; the record contains portfolio governance observations and durable future-use claim boundaries, so it is classified as an operational record rather than a personal preference or disposable cache.
- The repository memory-authority declaration predates the write: commit `5f3911bd9` added the structured block on 2026-05-28, while filesystem metadata places the private-memory write on 2026-08-20.
- The private file and its filesystem timestamps are workstation observations, not committed or independently replayable repository evidence. They support this incident record but do not establish behavior for other users, agents, hosts, or repositories.

Corrective action:
- Add structured `memory_authority` block near the top of governance instructions.
- Add adoption packet forbidden change preventing operational records outside declared `memory_root`.
- Do not introduce framework-level memory contract or receipt unless the pattern recurs across repos.
- Record occurrence 2 in this existing incident instead of opening a parallel incident or silently treating private project memory as governance authority.
- Do not scan private directories, restore the retired host-agent memory sync signal, or implement a detector from this incident update alone.

Escalation condition:
- Met on 2026-08-20: the same pattern was observed in a second repo (`ai-governance-framework`).
- Any later framework-level validation proposal must first define host cooperation or an explicit operator entrypoint, allowed roots, privacy boundaries, a natural caller, and an acceptance condition. Until the owner approves that trust model, keep validation unimplemented.

Claim ceiling:
- May claim: two distinct repositories have now produced the same external-memory authority misresolution pattern, so the recorded cross-repository escalation condition is met.
- Must not claim: external memory was deleted or synchronized; repo-local guards can observe host-private writes; a report-only detector is feasible or approved; all Claude Code, Agent, or harness sessions share this behavior; or framework-level enforcement exists.
