# Governance Required 8 of 10 Checkpoint — 2026-05-26

## Summary

- verified required repos: 8
- newly verified: hp-firmware-stresstest-tool
- verified path type: framework_lock + agents_fix + closeout
- evidence type: closeout_receipt
- dirty dependency: dirty_true=8, dirty_false=0, expected_dirty_ttl_valid=8
- remaining required blockers: 2 repos (ai-governance-framework, Kernel-Driver-Contract)
- schema changes: none
- evidence contract changes: none
- metric changes: none
- special exception: none

## Verified Required Repos (8/10)

| repo | ev_tier | path |
|---|---|---|
| Command_Line_Tool | hw_or_build | previously verified |
| IsptoolRefine2018_EndUser_Tool | hw_or_build | previously verified |
| CFU | tier_3 | previously verified |
| cli | unknown | previously verified |
| lenoveo-isp-tool-avalonia | tier_3 | previously verified |
| gl_electron_tool | tier_2 | previously verified |
| General_End_User_Tool | tier_2 | previously verified |
| **hp-firmware-stresstest-tool** | **tier_3** | **this session** |

## This Session — hp-firmware-stresstest-tool

- framework.lock.json: created (adopted_release=1.2.0, adopted_commit=bbb4f1d, interface=1, compatible=>=1.0.0,<2.0.0)
- AGENTS.md: filled (4 sections — subprocess/OCI-tool/log-parser/loop specifics; agents_calibration.status=repo_specific_minimal)
- closeout: valid (gate_blocked=false, linked_head_commit=b30c7a1b == repo HEAD, timestamp_in_window=true)
- preflight: external_repo_readiness ready=true, 0 errors, 0 warnings

## Remaining Required Blockers (2/10)

| repo | blockers |
|---|---|
| ai-governance-framework | fw_unknown, agents=scaffold |
| Kernel-Driver-Contract | fw_unknown, agents=scaffold, head_commit_match=false, timestamp_stale |

## Matrix Snapshot

- snapshot: governance_repo_matrix_snapshot_20260526_145448.md
- generated_at: 2026-05-26T14:57:50
- scope-normalized verified ratio (required only): 8/10 (0.8)
