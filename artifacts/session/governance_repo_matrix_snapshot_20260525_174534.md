# Governance Repo Matrix Snapshot

- generated_at: 2026-05-25T17:49:08
- json: E:\BackUp\Git_EE\ai-governance-framework\artifacts\session\governance_repo_matrix_snapshot_20260525_174534.json

## Confidence
- company: LOW (9/9 smoke pass)
- private: LOW (10/11 smoke pass)
- repo-native governance candidate ratio (overall): 3/20 (0.15)
- repo-native governance verified ratio (overall): 3/20 (0.15)
- repo-native governance candidate ratio (company): 3/9 (0.3333)
- repo-native governance verified ratio (company): 3/9 (0.3333)
- repo-native governance candidate ratio (private): 0/11 (0)
- repo-native governance verified ratio (private): 0/11 (0)
- scope-normalized verified ratio (required only): 3/10 (0.3)

## Notes
- Negative-path and drift tests run with temporary mutation and restoration.
- Enumd regression checks use static adapter consistency probes plus fallback detection.
- repo-native candidate ratio uses hooks/framework-lock/agents signals only.
- repo-native verified ratio is fail-closed: candidate plus repo-local evidence linked to repo HEAD and within current matrix window, with dirty state explained.

## Per-Repo Classification
| repo | tier | ev_tier | class | hooks | fw | agents | dirty_ok | evidence | head_ok | ts_ok | blockers -> action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hp-firmware-stresstest-tool | required | tier_3 | matrix_only | Y | N | N | Y | N | N | N | fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; no_evidence -> run closeout |
| cli | required | unknown | matrix_only | N | N | Y | Y | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| CFU | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| IsptoolRefine2018_EndUser_Tool | required | hw_or_build | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| lenoveo-isp-tool-avalonia | required | tier_3 | partial | Y | Y | N | Y | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; no_evidence -> run closeout |
| gl_electron_tool | required | tier_2 | partial | N | Y | Y | Y | Y | N | N | hooks_ready=false -> install hooks; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Command_Line_Tool | required | hw_or_build | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| General_End_User_Tool | required | tier_2 | matrix_only | N | N | Y | Y | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; no_evidence -> run closeout |
| SpecAuthority | recommended | ci_strict | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| ai-governance-framework | required | ci_strict | matrix_only | N | N | N | Y | Y | N | Y | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; head_commit_match=false -> run closeout |
| Bookstore-Scraper | recommended | ci_strict | partial | Y | Y | N | N | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Enumd | recommended | ci_strict | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| FinancialAdvisorGPT | exempt | unknown | matrix_only | N | N | N | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Hearth | exempt | unknown | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Kernel-Driver-Contract | required | hw_or_build | matrix_only | Y | N | N | Y | Y | N | N | fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Mirra | recommended | unknown | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| SpecAuthority | recommended | ci_strict | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| verilog-domain-contract | recommended | audit_mode | partial | N | Y | Y | N | N | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| writing-contract | recommended | unknown | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| ZoneTruth | recommended | ci_strict | matrix_only | N | N | N | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
