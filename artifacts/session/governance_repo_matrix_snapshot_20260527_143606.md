# Governance Repo Matrix Snapshot

- generated_at: 2026-05-27T14:39:09
- json: E:\BackUp\Git_EE\ai-governance-framework\artifacts\session\governance_repo_matrix_snapshot_20260527_143606.json

## Confidence
- company: LOW (9/9 smoke pass)
- private: LOW (10/11 smoke pass)
- repo-native governance candidate ratio (overall): 10/19 (0.5263)
- repo-native governance verified ratio (overall): 7/19 (0.3684)
- repo-native governance candidate ratio (company): 8/9 (0.8889)
- repo-native governance verified ratio (company): 7/9 (0.7778)
- repo-native governance candidate ratio (private): 2/11 (0.1818)
- repo-native governance verified ratio (private): 0/11 (0)
- scope-normalized verified ratio (required only): 7/10 (0.7)
- structural readiness (required candidate_or_above): 10/10 (1)
- freshness blocked count (required): 0
- evidence freshness window (days): 7
- verified dirty dependency (required verified only): total=7, dirty_true=7, dirty_false=0, expected_dirty_ttl_valid=7

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
| IsptoolRefine2018_EndUser_Tool | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| lenoveo-isp-tool-avalonia | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| gl_electron_tool | required | tier_2 | repo_native_candidate | Y | Y | Y | Y | Y | N | Y | head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| Command_Line_Tool | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| General_End_User_Tool | required | tier_2 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| SpecAuthority | recommended | ci_strict | matrix_only | N | N | Y | N | Y | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>"; ts_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| ai-governance-framework | required | ci_strict | repo_native_candidate | Y | Y | Y | Y | Y | N | Y | head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| Bookstore-Scraper | recommended | ci_strict | partial | Y | Y | N | N | N | N | N | agents -> Update repo-specific AGENTS.md after human review.; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; evidence -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| Enumd | recommended | ci_strict | partial | N | Y | Y | N | Y | N | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| FinancialAdvisorGPT | exempt | unknown | matrix_only | N | N | N | N | N | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; agents -> Update repo-specific AGENTS.md after human review.; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; evidence -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| Hearth | exempt | unknown | partial | N | Y | Y | N | Y | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>"; ts_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| Kernel-Driver-Contract | required | hw_or_build | repo_native_candidate | Y | Y | Y | Y | Y | N | Y | head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| Mirra | recommended | unknown | matrix_only | N | N | Y | N | N | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; evidence -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| verilog-domain-contract | recommended | audit_mode | partial | N | Y | Y | N | N | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; evidence -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| writing-contract | recommended | unknown | matrix_only | N | N | Y | N | N | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; evidence -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |
| ZoneTruth | recommended | ci_strict | matrix_only | N | N | N | N | Y | N | N | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; agents -> Update repo-specific AGENTS.md after human review.; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty.; head_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>"; ts_ok -> python -m governance_tools.session_closeout_entry --project-root "<repo>" |

## Baseline Drift
### hp-firmware-stresstest-tool
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### cli
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### CFU
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### IsptoolRefine2018_EndUser_Tool
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### lenoveo-isp-tool-avalonia
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### gl_electron_tool
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: head_commit_match
### Command_Line_Tool
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### General_End_User_Tool
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### SpecAuthority
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### ai-governance-framework
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: head_commit_match
### Bookstore-Scraper
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### Enumd
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### FinancialAdvisorGPT
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### Hearth
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### Kernel-Driver-Contract
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: head_commit_match
### Mirra
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### verilog-domain-contract
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### writing-contract
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)
### ZoneTruth
- drift_status: unknown
- repo_baseline: 
- framework_baseline: 2026-05-27
- adopted_surfaces: (none)
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing_surfaces: (none)

## Remediation Suggestions
### gl_electron_tool
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### SpecAuthority
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | false | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
| ts_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### ai-governance-framework
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### Bookstore-Scraper
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| evidence | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### Enumd
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### FinancialAdvisorGPT
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | false | (none) |
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| evidence | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### Hearth
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
| ts_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### Kernel-Driver-Contract
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### Mirra
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | false | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| evidence | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### verilog-domain-contract
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| evidence | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### writing-contract
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | false | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| evidence | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
### ZoneTruth
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | false | (none) |
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
| head_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |
| ts_ok | verified_command | python -m governance_tools.session_closeout_entry --project-root "<repo>" | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\session_closeout_entry.py |

## Adoption Task Packets
### Adoption Task Packet: gl_electron_tool

#### Target Repo
- Repo: gl_electron_tool
- Path: E:\BackUp\Git_EE\gl_electron_tool

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: blockers
- drift_status: current
- blockers: head_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: head_commit_match

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: SpecAuthority

#### Target Repo
- Repo: SpecAuthority
- Path: E:\BackUp\Git_EE\SpecAuthority

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, fw, dirty_ok, head_ok, ts_ok
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: ai-governance-framework

#### Target Repo
- Repo: ai-governance-framework
- Path: E:\BackUp\Git_EE\ai-governance-framework

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: blockers
- drift_status: current
- blockers: head_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: head_commit_match

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: Bookstore-Scraper

#### Target Repo
- Repo: Bookstore-Scraper
- Path: E:\BackUp\Git_EE\Bookstore-Scraper

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: agents, dirty_ok, evidence
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: Enumd

#### Target Repo
- Repo: Enumd
- Path: E:\BackUp\Git_EE\Enumd

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, dirty_ok, head_ok
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: FinancialAdvisorGPT

#### Target Repo
- Repo: FinancialAdvisorGPT
- Path: E:\BackUp\Git_EE\FinancialAdvisorGPT

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, fw, agents, dirty_ok, evidence
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: Hearth

#### Target Repo
- Repo: Hearth
- Path: E:\BackUp\Git_EE\Hearth

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, dirty_ok, head_ok, ts_ok
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: Kernel-Driver-Contract

#### Target Repo
- Repo: Kernel-Driver-Contract
- Path: E:\BackUp\Git_EE\Kernel-Driver-Contract

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: blockers
- drift_status: current
- blockers: head_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: head_commit_match

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: Mirra

#### Target Repo
- Repo: Mirra
- Path: E:\BackUp\Git_EE\Mirra

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, fw, dirty_ok, evidence
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: verilog-domain-contract

#### Target Repo
- Repo: verilog-domain-contract
- Path: E:\BackUp\Git_EE\verilog-domain-contract

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, dirty_ok, evidence
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: writing-contract

#### Target Repo
- Repo: writing-contract
- Path: E:\BackUp\Git_EE\writing-contract

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, fw, dirty_ok, evidence
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: ZoneTruth

#### Target Repo
- Repo: ZoneTruth
- Path: E:\BackUp\Git_EE\ZoneTruth

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: both
- drift_status: unknown
- blockers: hooks, fw, agents, dirty_ok, head_ok, ts_ok
- missing_required_surfaces: agents_calibration, timestamp_freshness, head_commit_match, hooks_config, expected_dirty, closeout_evidence, framework_lock
- adopted_but_observed_missing: (none)

#### Allowed Changes
- repo-specific AGENTS.md fleet overlay section
- governance/framework.lock.json
- governance metadata required by the current baseline
- evidence / closeout artifacts generated by verified commands

#### Forbidden Changes
- domain contract content above fleet overlay boundary
- framework global rules or rule precedence
- application source code unrelated to governance adoption
- enforcement behavior unless explicitly requested and verified

Fleet overlay boundary rule:
- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`
- You must not modify domain contract content above that boundary.

#### Required Actions
1. Fix only listed blockers/missing surfaces/observed-missing surfaces.
2. Use only `verified_command` items from remediation suggestions as copy-paste commands.
3. For `human_required` items, document required review and stop short of speculative automation.
4. Update `adopted_surfaces` only when the surface is actually installed/verified.
5. Do not change forbidden files/sections.

#### Done Definition
- targeted blockers resolved or explicitly marked human-required
- missing required surfaces resolved or explicitly human-required
- no previously passing signal has regressed to failing
- framework.lock.json adopted_surfaces matches installed surfaces
- forbidden files/sections unchanged

#### Before/After Signal Table (required output)
| Signal | Before | After | Status |
|---|---|---|---|
| hooks_config | current_snapshot | rerun_required | pending |
| framework_lock | current_snapshot | rerun_required | pending |
| agents_calibration | current_snapshot | rerun_required | pending |
| expected_dirty | current_snapshot | rerun_required | pending |
| closeout_evidence | current_snapshot | rerun_required | pending |
| head_commit_match | current_snapshot | rerun_required | pending |
| timestamp_freshness | current_snapshot | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
