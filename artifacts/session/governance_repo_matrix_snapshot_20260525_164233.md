# Governance Repo Matrix Snapshot

- generated_at: 2026-05-25T16:46:56
- json: E:\BackUp\Git_EE\ai-governance-framework\artifacts\session\governance_repo_matrix_snapshot_20260525_164233.json

## Confidence
- company: LOW (9/9 smoke pass)
- private: LOW (10/11 smoke pass)
- repo-native governance candidate ratio (overall): 2/20 (0.1)
- repo-native governance verified ratio (overall): 2/20 (0.1)
- repo-native governance candidate ratio (company): 2/9 (0.2222)
- repo-native governance verified ratio (company): 2/9 (0.2222)
- repo-native governance candidate ratio (private): 0/11 (0)
- repo-native governance verified ratio (private): 0/11 (0)
- scope-normalized verified ratio (required only): 2/10 (0.2)

## Notes
- Negative-path and drift tests run with temporary mutation and restoration.
- Enumd regression checks use static adapter consistency probes plus fallback detection.
- repo-native candidate ratio uses hooks/framework-lock/agents signals only.
- repo-native verified ratio is fail-closed: candidate plus repo-local evidence linked to repo HEAD and within current matrix window, with dirty state explained.

## Per-Repo Classification
| repo | tier | class | hooks | fw | agents | dirty_ok | evidence | head_ok | ts_ok | blockers -> action |
|---|---|---|---|---|---|---|---|---|---|---|
| hp-firmware-stresstest-tool | required | matrix_only | Y | N | N | Y | N | N | N | fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; no_evidence -> run closeout |
| cli | required | matrix_only | N | N | Y | Y | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| CFU | required | partial | Y | Y | N | Y | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; no_evidence -> run closeout |
| IsptoolRefine2018_EndUser_Tool | required | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| lenoveo-isp-tool-avalonia | required | partial | Y | Y | N | Y | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; no_evidence -> run closeout |
| gl_electron_tool | required | matrix_only | N | N | N | Y | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Command_Line_Tool | required | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| General_End_User_Tool | required | matrix_only | N | N | Y | Y | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; no_evidence -> run closeout |
| SpecAuthority | recommended | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| ai-governance-framework | required | matrix_only | N | N | N | Y | Y | N | Y | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; head_commit_match=false -> run closeout |
| Bookstore-Scraper | recommended | partial | Y | Y | N | N | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Enumd | recommended | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| FinancialAdvisorGPT | exempt | matrix_only | N | N | N | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Hearth | exempt | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Kernel-Driver-Contract | required | matrix_only | Y | N | N | Y | Y | N | N | fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Mirra | recommended | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| SpecAuthority | recommended | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| verilog-domain-contract | recommended | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| writing-contract | recommended | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| ZoneTruth | recommended | matrix_only | N | N | N | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
