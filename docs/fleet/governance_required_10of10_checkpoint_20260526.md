# Governance Required 10 of 10 Checkpoint — 2026-05-26

## Summary

- verified required repos: 10
- newly verified: Kernel-Driver-Contract
- verified path type: domain-contract-separated-calibration (Option B)
- evidence type: governance/framework.lock.json (fw) + AGENTS.md fleet_overlay section (agents)
- dirty dependency: dirty_true=10, dirty_false=0, expected_dirty_ttl_valid=10
- remaining required blockers: none
- schema changes: none
- evidence contract changes: none
- metric changes: none
- special exception: none

## Kernel-Driver-Contract Onboarding Notes

This repo required a non-standard path. Standard onboarding writes governance:key sections
directly into AGENTS.md. For Kernel-Driver-Contract, AGENTS.md is a domain contract document
(KSTATE/IRQL/IRP/dispatch rules). Fleet governance calibration must not modify or contaminate
domain authority.

### Resolution: Option B (domain-contract-separated-calibration)

Files changed in Kernel-Driver-Contract:
- `governance/framework.lock.json` — new; fixes fw=N
- `AGENTS.md` — fleet_overlay section appended below `## Related Documents`; fixes agents=scaffold

Domain contract sections (lines 1–178): untouched.
Fleet overlay section (lines 183–225): governance:key sections with kernel-driver-specific content.
Boundary markers: `<!-- governance:section_start=fleet_overlay -->` / `<!-- governance:section_end=fleet_overlay -->`

### Option A Deferred

The agents_calibration checker (`agents_calibration_maturity.py:138`) hard-codes
`repo_root / "AGENTS.md"`. No alternate path support. Option A (separate
`governance/fleet.AGENTS.md` + contract.yaml declaration) was deferred:
- blast radius: checker change covers all 20 repos
- trigger: wait for 2nd domain-contract repo with same pattern before implementing

### Decision Gate Result

```
checker_alternate_path_supported: false
worth adding framework capability (Option A): defer
selected option: B
pollution risk accepted: yes (machine-readable boundary markers)
domain contract owner confirmed: yes (2026-05-26)
```

## IsptoolRefine2018 Head Drift (Incidental)

IsptoolRefine2018 surfaced as a secondary blocker during the 10/10 run
(head_commit_match=false). Two governance commits had moved HEAD after the last closeout.
Resolved with manual_fallback session closeout. This is fail-closed behaviour working
correctly — not a deficiency or governance gap.

## Final State

| repo | class | ev_tier |
|---|---|---|
| hp-firmware-stresstest-tool | repo_native_verified | tier_3 |
| cli | repo_native_verified | unknown |
| CFU | repo_native_verified | tier_3 |
| IsptoolRefine2018_EndUser_Tool | repo_native_verified | tier_3 |
| lenoveo-isp-tool-avalonia | repo_native_verified | tier_3 |
| gl_electron_tool | repo_native_verified | tier_2 |
| Command_Line_Tool | repo_native_verified | tier_3 |
| General_End_User_Tool | repo_native_verified | tier_2 |
| ai-governance-framework | repo_native_verified | ci_strict |
| Kernel-Driver-Contract | repo_native_verified | hw_or_build |

scope-normalized verified ratio: 10/10 (1.0)
snapshot: governance_repo_matrix_snapshot_20260526_164649
