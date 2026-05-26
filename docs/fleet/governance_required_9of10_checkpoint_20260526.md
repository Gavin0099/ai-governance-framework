# Governance Required 9 of 10 Checkpoint — 2026-05-26

## Summary

- verified required repos: 9
- newly verified: ai-governance-framework
- verified path type: framework_lock (self-referential) + agents_fix (self-governance sections)
- evidence type: pre-existing closeout_receipt (head_ok=Y, ts_ok=Y were already passing)
- dirty dependency: dirty_true=9, dirty_false=0, expected_dirty_ttl_valid=9
- remaining required blockers: 1 repo (Kernel-Driver-Contract)
- schema changes: none
- evidence contract changes: none
- metric changes: none
- special exception: none

## Semantic Caveat (Self-Governance)

This repo governs itself. The verified status means:
- `ai-governance-framework` has an admissible evidence chain
- framework.lock.json records the self-assessment baseline (adopted_release=1.2.0)
- _self_reference_note is present in lock: self-verification does not prove framework correctness

Self-verification != framework correctness. The verified ratio reflects evidence chain integrity, not governance model validity.

## Verified Required Repos (9/10)

| repo | ev_tier | path |
|---|---|---|
| Command_Line_Tool | hw_or_build | previously verified |
| IsptoolRefine2018_EndUser_Tool | hw_or_build | previously verified |
| CFU | tier_3 | previously verified |
| cli | unknown | previously verified |
| lenoveo-isp-tool-avalonia | tier_3 | previously verified |
| gl_electron_tool | tier_2 | previously verified |
| General_End_User_Tool | tier_2 | previously verified |
| hp-firmware-stresstest-tool | tier_3 | 2026-05-26 session |
| **ai-governance-framework** | **ci_strict** | **this session (self-governance)** |

## This Session — ai-governance-framework

- governance/framework.lock.json: created (self-referential; adopted_release=1.2.0, adopted_commit=39820de, _self_reference_note present)
- AGENTS.md: added 4 governance:key sections (risk_levels/must_test_paths/escalation_triggers/forbidden_behaviors) scoped to framework development risks — session_end_hook, gate_policy, evidence-admissibility, verified-definition integrity
- preflight: ready=true, fw_version_known=true, fw.state=current, agents_calibration=repo_specific_minimal, 0 errors

## Remaining Required Blockers (1/10)

| repo | blockers |
|---|---|
| Kernel-Driver-Contract | fw_unknown, agents=scaffold (domain contract + governance calibration coexistence problem), head_commit_match=false, timestamp_stale |

## Matrix Snapshot

- snapshot: governance_repo_matrix_snapshot_20260526_145448.md (pre-commit baseline)
- new snapshot: pending matrix rerun after commit 40219e4
- scope-normalized verified ratio (required only): 9/10 (0.9) — pending confirmation
