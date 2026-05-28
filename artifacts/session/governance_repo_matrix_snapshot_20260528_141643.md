# Governance Repo Matrix Snapshot

- generated_at: 2026-05-28T14:20:05
- json: E:\BackUp\Git_EE\ai-governance-framework\artifacts\session\governance_repo_matrix_snapshot_20260528_141643.json

## Confidence
- company: LOW (9/9 smoke pass)
- private: LOW (10/12 smoke pass)
- repo-native governance candidate ratio (overall): 10/20 (0.5)
- repo-native governance verified ratio (overall): 10/20 (0.5)
- repo-native governance candidate ratio (company): 8/9 (0.8889)
- repo-native governance verified ratio (company): 8/9 (0.8889)
- repo-native governance candidate ratio (private): 2/12 (0.1667)
- repo-native governance verified ratio (private): 2/12 (0.1667)
- scope-normalized verified ratio (required only): 10/10 (1)
- structural readiness (required candidate_or_above): 10/10 (1)
- freshness blocked count (required): 0
- evidence freshness window (days): 7
- verified dirty dependency (required verified only): total=10, dirty_true=10, dirty_false=0, expected_dirty_ttl_valid=10
- detector_errors_total: total=0, reports_found=20, reports_missing=0

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
| gl_electron_tool | required | tier_2 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| Command_Line_Tool | required | tier_3 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| General_End_User_Tool | required | tier_2 | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| SpecAuthority | recommended | ci_strict | matrix_only | N | N | Y | Y | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). |
| ai-governance-framework | required | ci_strict | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| Bookstore-Scraper | recommended | ci_strict | matrix_only | Y | N | N | Y | Y | Y | Y | fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; agents -> Update repo-specific AGENTS.md after human review. |
| Enumd | recommended | ci_strict | matrix_only | N | N | Y | Y | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). |
| FinancialAdvisorGPT | exempt | unknown | matrix_only | N | N | N | N | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; agents -> Update repo-specific AGENTS.md after human review.; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty. |
| Hearth | exempt | unknown | matrix_only | N | N | Y | N | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty. |
| Kernel-Driver-Contract | required | hw_or_build | repo_native_verified | Y | Y | Y | Y | Y | Y | Y | none |
| Mirra | recommended | unknown | matrix_only | N | N | Y | Y | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). |
| usb-logic-trace-correlator | unknown | unknown | matrix_only | N | Y | N | Y | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; agents -> Update repo-specific AGENTS.md after human review. |
| verilog-domain-contract | recommended | audit_mode | matrix_only | N | N | Y | N | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty. |
| writing-contract | recommended | unknown | matrix_only | N | N | Y | N | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty. |
| ZoneTruth | recommended | ci_strict | matrix_only | N | N | N | N | Y | Y | Y | hooks -> python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all; fw -> Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).; agents -> Update repo-specific AGENTS.md after human review.; dirty_ok -> Review dirty state and expected_dirty TTL before declaring explainable dirty. |

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
- adopted_but_observed_missing_surfaces: (none)
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
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: hooks_config, framework_lock
### ai-governance-framework
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### Bookstore-Scraper
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: agents_calibration, framework_lock
### Enumd
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: hooks_config, framework_lock
### FinancialAdvisorGPT
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: agents_calibration, hooks_config, expected_dirty, framework_lock
### Hearth
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: hooks_config, expected_dirty, framework_lock
### Kernel-Driver-Contract
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: (none)
### Mirra
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: hooks_config, framework_lock
### usb-logic-trace-correlator
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: agents_calibration, hooks_config
### verilog-domain-contract
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: hooks_config, expected_dirty, framework_lock
### writing-contract
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: hooks_config, expected_dirty, framework_lock
### ZoneTruth
- drift_status: current
- repo_baseline: 2026-05-27
- framework_baseline: 2026-05-27
- adopted_surfaces: hooks_config, framework_lock, agents_calibration, expected_dirty, closeout_evidence, head_commit_match, timestamp_freshness
- missing_required_surfaces: (none)
- adopted_but_observed_missing_surfaces: agents_calibration, hooks_config, expected_dirty, framework_lock

## Remediation Suggestions
### SpecAuthority
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
### Bookstore-Scraper
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
### Enumd
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
### FinancialAdvisorGPT
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
### Hearth
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
### Mirra
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
### usb-logic-trace-correlator
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
### verilog-domain-contract
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
### writing-contract
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |
### ZoneTruth
| blocker | remediation_type | command | action | human_required | verification_source |
|---|---|---|---|---|---|
| hooks | verified_command | python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all | (none) | false | E:\BackUp\Git_EE\ai-governance-framework\governance_tools\manage_agent_closeout.py |
| fw | manual_action | (none) | Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy). | true | (none) |
| agents | human_required | (none) | Update repo-specific AGENTS.md after human review. | true | (none) |
| dirty_ok | human_required | (none) | Review dirty state and expected_dirty TTL before declaring explainable dirty. | true | (none) |

## Adoption Task Packets
### Adoption Task Packet: SpecAuthority

#### Target Repo
- Repo: SpecAuthority
- Path: E:\BackUp\Git_EE\SpecAuthority

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw
- missing_required_surfaces: (none)
- adopted_but_observed_missing: hooks_config, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | Y | rerun_required | pending |
| expected_dirty | Y | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: fw, agents
- missing_required_surfaces: (none)
- adopted_but_observed_missing: agents_calibration, framework_lock

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
| hooks_config | Y | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | N | rerun_required | pending |
| expected_dirty | Y | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw
- missing_required_surfaces: (none)
- adopted_but_observed_missing: hooks_config, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | Y | rerun_required | pending |
| expected_dirty | Y | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw, agents, dirty_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: agents_calibration, hooks_config, expected_dirty, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | N | rerun_required | pending |
| expected_dirty | N | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw, dirty_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: hooks_config, expected_dirty, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | Y | rerun_required | pending |
| expected_dirty | N | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw
- missing_required_surfaces: (none)
- adopted_but_observed_missing: hooks_config, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | Y | rerun_required | pending |
| expected_dirty | Y | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
### Adoption Task Packet: usb-logic-trace-correlator

#### Target Repo
- Repo: usb-logic-trace-correlator
- Path: E:\BackUp\Git_EE\usb-logic-trace-correlator

#### Goal
Bring this repo's AI Governance surfaces back in sync with the current framework baseline and matrix findings.

#### Current Findings
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, agents
- missing_required_surfaces: (none)
- adopted_but_observed_missing: agents_calibration, hooks_config

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
| hooks_config | N | rerun_required | pending |
| framework_lock | Y | rerun_required | pending |
| agents_calibration | N | rerun_required | pending |
| expected_dirty | Y | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw, dirty_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: hooks_config, expected_dirty, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | Y | rerun_required | pending |
| expected_dirty | N | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw, dirty_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: hooks_config, expected_dirty, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | Y | rerun_required | pending |
| expected_dirty | N | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

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
- trigger_reason: blockers
- drift_status: current
- blockers: hooks, fw, agents, dirty_ok
- missing_required_surfaces: (none)
- adopted_but_observed_missing: agents_calibration, hooks_config, expected_dirty, framework_lock

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
| hooks_config | N | rerun_required | pending |
| framework_lock | N | rerun_required | pending |
| agents_calibration | N | rerun_required | pending |
| expected_dirty | N | rerun_required | pending |
| closeout_evidence | Y | rerun_required | pending |
| head_commit_match | Y | rerun_required | pending |
| timestamp_freshness | Y | rerun_required | pending |

#### Non-Claims
- do not claim permanent verified status
- do not claim all future runs will pass
- do not claim semantic correctness proof
- do not claim authority boundary changes
