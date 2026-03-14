# Knowledge Base

## Runtime Governance Maturity Snapshot

- The repository now operates as an AI Coding Runtime Governance Framework prototype with a full runtime spine:
  `session_start -> pre_task_check -> post_task_check -> session_end -> memory pipeline`.
- Multi-harness runtime support exists for Claude Code, Codex, and Gemini through native payload normalization, shared events, adapters, and dispatcher routing.
- Rule-pack governance is no longer limited to language packs; it now includes scope, language, framework, platform, and custom categories.
- Proposal-time governance is active. `architecture_impact_estimator.py` and `change_proposal_builder.py` produce structured previews before implementation begins.
- Reviewable change-control artifacts are now part of the governance surface via startup handoff notes, JSON envelopes, `change_control_summary.py`, and `change_control_index.py`.
- The runtime governance loop is real, but interception coverage is not yet fully closed across every developer and agent entrypoint.

## Evidence And Enforcement

- Evidence ingestion currently supports `pytest-text`, `junit-xml`, `sdv-text`, `msbuild-warning-text`, `sarif`, and `wdk-analysis-text`.
- Evidence is not only collected; it already feeds runtime validation through:
  - `failure_completeness_validator.py`
  - `refactor_evidence_validator.py`
  - `public_api_diff_checker.py`
  - `driver_evidence_validator.py`
  - `architecture_drift_checker.py`
- Current enforcement is evidence-aware and boundary-aware, but it is not yet a full semantic policy decision engine.

## Domain Extension Seam

- The repository now has an external domain validator seam rather than a fully mature plugin platform.
- `contract.yaml` discovery, external rule roots, validator preflight, and advisory validator execution are already working.
- The first domain vertical slice exists through `examples/usb-hub-contract/`, which validates firmware-specific constraints inside the governance runtime.
- Firmware evidence routing can currently infer interrupt context from explicit fields, `diff_text`, unified diff snippets, changed source files, and file-based `diff_file` inputs.
- This seam is intentionally advisory-first while payload shape and enforcement semantics are still being learned from real domain workflows.
- Multi-domain reviewer artifacts now preserve shared contract context:
  - `contract_source`
  - `contract_name`
  - `contract_domain`
  - `plugin_version`
  - `contract_risk_tier`
- Current built-in domain governance tiers are intentionally small and explicit:
  - `kernel-driver` = `high`
  - `firmware` = `medium`

## Boundary To Protect

- Packs provide governance context.
- Skills provide behavior guidance.
- Runtime checks and policies make decisions.
- Suggestions remain advisory and must not silently mutate the active contract.
- The repository should continue to act as a governance framework, not become a generic AI orchestration OS.

## Positioning

- The repository's rarest asset is the runtime governance lifecycle:
  `AI coding -> governance runtime -> evidence -> artifacts -> reviewer`.
- Rule packs and validators matter, but they derive their value from this runtime governance pipeline rather than replacing it.
- The current system should be described as a governance framework prototype with:
  - a complete runtime governance skeleton
  - an external domain validator seam
  - a first firmware domain vertical slice

## Planned Integration Direction

- A planned next step is to integrate the framework with `USB-Hub-Firmware-Architecture-Contract` as an external domain extension, not by merging repos.
- The intended seam is `contract.yaml` discovery, with the framework responsible for lifecycle/runtime governance and the firmware repo responsible for domain facts, rule packs, and validators.
- The next proof point after USB-Hub should be a second domain slice so the abstraction can be validated beyond firmware alone.

## EDA / IC Python Governance Fit

- Python in IC design is a strong candidate for Way B governance, not because Python syntax is hard, but because project-local context is deep and proprietary.
- The strongest initial fits are:
  - Cocotb or Python-based verification harnesses
  - reference / golden models for DSP, accelerator, or protocol behavior
  - EDA flow automation, log parsing, and script-based validation around internal toolchains
- The main AI failure mode here is likely to be "syntactically correct, contextually dangerous":
  - wrong DUT signal mapping
  - incorrect timing or handshake assumptions
  - fixed-point / pipeline mismatches when translating reference models
  - unsafe assumptions about internal EDA tool versions, paths, or CI rules
- This means an eventual IC-oriented contract should focus on fact capture and evidence routing, not language tutoring.
- A sensible first adoption path would be:
  - keep existing Python verification libraries as Way A assets
  - add contract-driven facts for register maps, signal maps, timing constraints, or internal tool boundaries
  - use post-task validation to check whether generated scripts reference real project facts rather than hallucinated names
- This domain looks suitable, but only if introduced through a narrow slice first rather than a broad "EDA platform" abstraction.

## IC / SoC Domain Expansion Notes

- A second-pass review suggests the highest-value IC governance path should be prioritized by:
  - mistake cost
  - machine-readability difficulty
- Under that lens, the likely order is:
  - `P0`: SoC integration
  - `P1`: RTL design
  - `P2`: IC verification
  - `P3`: CAD automation
- The key positioning correction is important:
  - the framework should not promise to "prevent" complex RTL failures such as CDC bugs
  - in these domains it is often more realistic to act as a risk declarer and reviewer-focusing system
- A likely RTL governance shape would therefore require AI to surface explicit risk declarations, not claim deep automatic understanding of clock-domain behavior.
- A strong concrete candidate for early IC automation is address-map governance:
  - convert XML / spreadsheet specs into machine-readable `address_map.json`
  - validate generated integration outputs against overlap / collision rules
  - this is attractive because the failure cost is high while the validator logic is mostly numeric and interval-based
- If IC adoption starts, the safer structure is still:
  - one `IC-Verification-Contract` or similarly scoped contract first
  - then split into narrower repos only after real workflow pressure appears
- For IC verification specifically, Cocotb-style signal mapping remains one of the best narrow-slice entry points because:
  - the AI blind spot is clear
  - the facts are often already present in structured specs
  - it fits the framework's current contract-first, reviewer-assist model

## Working Agreement

- For this repository, each task should be completed, reviewed, committed, and pushed before starting the next task.
- Task sequencing should favor small, isolated changesets so integration progress remains easy to audit and rollback.

