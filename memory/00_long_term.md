# Long-Term Memory

## Identity And Account Mapping
- GitHub upload account: `Gavin0099`
- GitLab upload account: `GavinWu`
- git config user.email for GitLab pushes: `Gavin.Wu@genesyslogic.com.tw`

## Conventions
- Long-term memory must live in `memory/00_long_term.md` (not repo-root `MEMORY.md`).
- In main sessions, after every push, write a short daily memory entry with `what changed`, `commit`, `tests`, and `next step`.
- External/private tool memory (for example `C:\Users\reiko\.claude\projects\...\memory\MEMORY.md`) is not cross-agent governance authority; canonical cross-agent memory must be copied into repo `memory/`.

## Workflow Preferences
- User requires a strict loop: after each completed change, update the corresponding `memory/YYYY-MM-DD.md` entry and push.
- User requires every completed change to be pushed to both `gitlab` and `origin` (GitHub), with author identity intentionally separated per remote.

## Governance State (cross-agent readable facts)

> This section is the authoritative in-repo governance state for agents that cannot
> access Claude Code's private project memory (C:\Users\reiko\.claude\projects\...\memory\MEMORY.md).
> Update this section whenever phase state or version changes.

### Framework Version
- Current release: **v1.2.0** (Phase D governance baseline freeze + runtime structural enforcement v0.1)
- Badge source: `README.md`; release notes: `CHANGELOG.md`

### Phase Status (as of 2026-04-28)
| Phase | Status | Notes |
|-------|--------|-------|
| A | completed | governance core baseline |
| B | completed | adoption / validator / freshness / memory |
| C | completed | runtime governance, DBL, observation surfaces |
| D | **completed** | reviewer closeout signed 2026-04-28T11:59:44Z by Gavin0099 |
| E | in_progress | failure decision boundary, exclusion governance, usage enforcement |

### Phase D Closeout Artifact
- Canonical path: `artifacts/governance/phase-d-reviewer-closeout.json`
- Reviewer: `Gavin0099`
- Confirmed at: `2026-04-28T11:59:44Z`
- Status: `ok=True`, `failures=[]`, `missing_required_conditions=[]`
- Authority contract: `governance/PHASE_D_CLOSE_AUTHORITY.md`

### Phase D Required Conditions (exact tokens — F10/F11 enforcement)
The following 5 strings must appear verbatim in `confirmed_conditions` for
`assess_phase_d_closeout()` to return `ok=True`:
```
reviewer_independent_of_author
phase_c_surface_gap_resolved
validator_output_reviewed
fail_closed_semantics_accepted
no_unresolved_blocking_conditions
```
Source: `governance_tools/phase_d_closeout_writer.py::REQUIRED_CONDITIONS`

### Runtime Capability Boundary (v1.2.0)
- **Runtime-enforced (F1–F11)**: artifact presence, schema, writer identity, reviewer_id,
  confirmed_conditions presence, confirmed_at, verdict, required condition coverage (5 tokens),
  VRB-3 exception path explicitly `unsupported`
- **Reviewer-attested only (F12–F15)**: self-review prohibition, proxy review (RI-2),
  wrong scope (RI-4), retroactive signing — runtime cannot machine-verify
- **Not yet implemented**: F4 immutability hash, F16/F17 exception authority artifact path
