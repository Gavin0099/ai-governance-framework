# Governance Repo Matrix Snapshot

- generated_at: 2026-05-26T16:34:43
- json: E:\BackUp\Git_EE\ai-governance-framework\artifacts\session\governance_repo_matrix_snapshot_20260526_163158.json

## Confidence
- company: LOW (9/9 smoke pass)
- private: LOW (10/11 smoke pass)
- repo-native governance candidate ratio (overall): 10/20 (0.5)
- repo-native governance verified ratio (overall): 9/20 (0.45)
- repo-native governance candidate ratio (company): 8/9 (0.8889)
- repo-native governance verified ratio (company): 7/9 (0.7778)
- repo-native governance candidate ratio (private): 2/11 (0.1818)
- repo-native governance verified ratio (private): 2/11 (0.1818)
- scope-normalized verified ratio (required only): 9/10 (0.9)
- verified dirty dependency (required verified only): total=9, dirty_true=9, dirty_false=0, expected_dirty_ttl_valid=9

## Notes
- Negative-path and drift tests run with temporary mutation and restoration.
- Enumd regression checks use static adapter consistency probes plus fallback detection.
- repo-native candidate ratio uses hooks/framework-lock/agents signals only.
- repo-native verified ratio is fail-closed: candidate plus repo-local evidence linked to repo HEAD and within current matrix window, with dirty state explained.

## Per-Repo Classification
| repo | tier | ev_tier | class | hooks | fw | agents | dirty_ok | evidence | head_ok | ts_ok | blockers -> action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hp-firmware-stresstest-tool | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| cli | required | unknown | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| CFU | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| IsptoolRefine2018_EndUser_Tool | required | tier_3 | repo_native_candidate | Y | Y | Y | Y | Y | N | Y | head_commit_match=false -> run closeout |
| lenoveo-isp-tool-avalonia | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| gl_electron_tool | required | tier_2 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| Command_Line_Tool | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| General_End_User_Tool | required | tier_2 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| SpecAuthority | recommended | ci_strict | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| ai-governance-framework | required | ci_strict | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| Bookstore-Scraper | recommended | ci_strict | partial | Y | Y | N | N | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Enumd | recommended | ci_strict | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| FinancialAdvisorGPT | exempt | unknown | matrix_only | N | N | N | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Hearth | exempt | unknown | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Kernel-Driver-Contract | required | hw_or_build | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| Mirra | recommended | unknown | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| SpecAuthority | recommended | ci_strict | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| verilog-domain-contract | recommended | audit_mode | partial | N | Y | Y | N | N | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| writing-contract | recommended | unknown | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| ZoneTruth | recommended | ci_strict | matrix_only | N | N | N | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
