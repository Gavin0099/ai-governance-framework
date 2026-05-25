# Governance Repo Matrix Snapshot

- generated_at: 2026-05-25T15:08:06
- json: E:\BackUp\Git_EE\ai-governance-framework\artifacts\session\governance_repo_matrix_snapshot_20260525_150414.json

## Confidence
- company: LOW (9/9 smoke pass)
- private: LOW (10/11 smoke pass)
- repo-native governance candidate ratio (overall): 1/20 (0.05)
- repo-native governance verified ratio (overall): 1/20 (0.05)
- repo-native governance candidate ratio (company): 1/9 (0.1111)
- repo-native governance verified ratio (company): 1/9 (0.1111)
- repo-native governance candidate ratio (private): 0/11 (0)
- repo-native governance verified ratio (private): 0/11 (0)

## Notes
- Negative-path and drift tests run with temporary mutation and restoration.
- Enumd regression checks use static adapter consistency probes plus fallback detection.
- repo-native candidate ratio uses hooks/framework-lock/agents signals only.
- repo-native verified ratio is fail-closed: candidate plus repo-local evidence linked to repo HEAD and within current matrix window, with dirty state explained.

## Per-Repo Classification
| repo | class | hooks | fw | agents | dirty_ok | evidence | head_ok | ts_ok | blockers -> action |
|---|---|---|---|---|---|---|---|---|---|
| hp-firmware-stresstest-tool | matrix_only | Y | N | N | N | N | N | N | fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| cli | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| CFU | partial | Y | Y | N | N | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| IsptoolRefine2018_EndUser_Tool | partial | Y | Y | N | Y | Y | Y | Y | agents=scaffold -> write repo-specific AGENTS.md |
| lenoveo-isp-tool-avalonia | partial | Y | Y | N | N | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| gl_electron_tool | matrix_only | N | N | N | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Command_Line_Tool | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| General_End_User_Tool | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| SpecAuthority | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| ai-governance-framework | matrix_only | N | N | N | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Bookstore-Scraper | partial | Y | Y | N | N | N | N | N | agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Enumd | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| FinancialAdvisorGPT | matrix_only | N | N | N | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| Hearth | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Kernel-Driver-Contract | matrix_only | Y | N | N | N | Y | N | N | fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| Mirra | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| SpecAuthority | matrix_only | N | N | Y | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| verilog-domain-contract | partial | N | Y | Y | N | Y | N | N | hooks_ready=false -> install hooks; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
| writing-contract | matrix_only | N | N | Y | N | N | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; dirty_unexplained -> add expected_dirty.json; no_evidence -> run closeout |
| ZoneTruth | matrix_only | N | N | N | N | Y | N | N | hooks_ready=false -> install hooks; fw_unknown -> add framework.lock.json; agents=scaffold -> write repo-specific AGENTS.md; dirty_unexplained -> add expected_dirty.json; head_commit_match=false -> run closeout; timestamp_stale -> run closeout |
