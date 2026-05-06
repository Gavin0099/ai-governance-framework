# AI Governance Framework

> ?™æ˜¯ä¸€?‹é¢??AI-assisted development ??`machine-interpretable governance runtime`?? 
> å®ƒè??¦æ–¼ task / session å±¤ç???`execution`?`evidence`?`decision`?`memory / state` ??reviewer-facing governance surfaces??

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
## Token Cross-Repo Controlled Slice Closeout (2026-05-06)

### Closeout Status
Status: closed for current controlled slice

This package establishes:
- cross-repo distribution slice evidence
- interpretation guard
- citation requirement
- documented misuse scenarios

This package does not establish:
- full regression coverage
- token correctness
- production readiness
- automated misuse enforcement
- runtime decision safety

Reopen only when:
- a new repository is added
- token contract changes
- citation or misuse wording changes
- sentinel run detects drift

Primary references:
- [docs/payload-audit/token-cross-repo-summary-2026-05-05.md](docs/payload-audit/token-cross-repo-summary-2026-05-05.md)
- [docs/payload-audit/token-cross-repo-index-2026-05-06.md](docs/payload-audit/token-cross-repo-index-2026-05-06.md)
- [docs/payload-audit/token-observability-misuse-scenarios-v0.1.md](docs/payload-audit/token-observability-misuse-scenarios-v0.1.md)

## ?®å?å®šä?

?™å€?repo ?„æ ¸å¿ƒä??¯å–®ç´”ç? prompt disciplineï¼Œä?ä¸æ˜¯æ³›ç”¨ agent platformï¼Œè€Œæ˜¯ï¼?

- ?Šæ²»?†è??‡æ•´?†æ??¯è¢« runtime æ¶ˆè²»??canonical source
- ??session ?‹å??åŸ·è¡Œã€ç??Ÿæ”¶?‚æ??¯é?è­‰ç?æ²»ç?æµç?
- ??memory / closeout / reviewer handoff / status surface è®Šæ??¯è¿½è¹¤ç?è¼¸å‡º
- è®?consuming repo ?½ä»¥ adopt / readiness / drift / source audit ?„æ–¹å¼æ¥??

?®å?å·²ç?æ¶µè??„ä¸»è¦é¢?‘ï?

- `execution`
- `evidence`
- `decision`
- `memory / state`
- `reviewer surface`

## ?ç¢ºä¸ä¸»å¼µç?ç¯„å?

??repo **ä¸æ˜¯**ï¼?

- full execution harness
- machine-authoritative advisory system
- generic multi-agent orchestration platform
- full agent-ready determinism substrate

?™ä? non-claims å¾ˆé?è¦ã€‚å??‘ä??¯é?è¨»ï??Œæ˜¯?®å? repo ?Šç??„ä??¨å???

## ä¸»è?çµ„æ?

### Runtime Hooks

- [runtime_hooks/core/session_start.py](runtime_hooks/core/session_start.py)
- [runtime_hooks/core/pre_task_check.py](runtime_hooks/core/pre_task_check.py)
- [runtime_hooks/core/post_task_check.py](runtime_hooks/core/post_task_check.py)
- [runtime_hooks/core/session_end.py](runtime_hooks/core/session_end.py)

`scripts/run-runtime-governance.sh` is the shared enforcement entrypoint used by runtime hooks and CI.

### Governance Tools

- [governance_tools/](governance_tools/)
- [governance_tools/adopt_governance.py](governance_tools/adopt_governance.py)
- [governance_tools/governance_drift_checker.py](governance_tools/governance_drift_checker.py)
- [governance_tools/external_repo_readiness.py](governance_tools/external_repo_readiness.py)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)

### Canonical Governance Source

- [governance/](governance/)
- [governance/AGENT.md](governance/AGENT.md)
- [governance/SYSTEM_PROMPT.md](governance/SYSTEM_PROMPT.md)
- [governance/TESTING.md](governance/TESTING.md)
- [governance/ARCHITECTURE.md](governance/ARCHITECTURE.md)
- [governance/RULE_REGISTRY.md](governance/RULE_REGISTRY.md)

### Reviewer / Status Surface

- [docs/status/README.md](docs/status/README.md)
- [docs/status/runtime-governance-status.md](docs/status/runtime-governance-status.md)
- [docs/status/trust-signal-dashboard.md](docs/status/trust-signal-dashboard.md)
- [docs/status/reviewer-handoff.md](docs/status/reviewer-handoff.md)

## Phase D Governance Authority

`v1.2.0` å¢å?äº?Phase D close semantics ??authority contract ??runtime structural enforcement??

**Constitutional authority contract**ï¼š[governance/PHASE_D_CLOSE_AUTHORITY.md](governance/PHASE_D_CLOSE_AUTHORITY.md)
**Runtime implementation**ï¼š[governance_tools/phase_d_closeout_writer.py](governance_tools/phase_d_closeout_writer.py)

### å·²æ? runtime ?¯æ´ï¼ˆF1?“F11ï¼?

- Artifact å­˜åœ¨?§è? schema é©—è?ï¼ˆfail-closedï¼?
- `reviewer_id` / `confirmed_at` / `confirmed_conditions` æ¬„ä?å®Œæ•´??
- F10/F11ï¼šminimum confirmed_conditions coverageï¼? ?‹å?è¦æ?ä»¶ï?
- Machine-readable failure outputï¼ˆ`failure_code` / `failure_class` / `remediation`ï¼?
- VRB-3 exception override ?ç¢ºæ¨™è???`unsupported`ï¼ˆä??¯é?é»˜ç„¡?ˆï?

### å°šæœª??runtime ?ªå??µæ¸¬ï¼ˆreviewer-attested / audit-invalidatableï¼?

- F12?“F15ï¼šlegitimacy failuresï¼ˆself-review / proxy review / wrong scope / retroactive signingï¼?
- F4ï¼šartifact immutability hashï¼ˆpost-issuance modificationï¼?
- F16/F17ï¼šexception authority artifact pathï¼ˆå?ç´„å?ç¾©ä?è·¯å?ï¼Œruntime å°šæœªå¯¦ä?ï¼?

**æº–ç¢º?è¿°**ï¼šPHASE_D_CLOSE_AUTHORITY has runtime-aligned structural enforcement v0.1.
Legitimacy failures remain reviewer-attested and audit-invalidatable.
This is not full runtime enforcement of the constitutional contract.

---

## ?ˆæœ¬?€??

- [CHANGELOG.md](CHANGELOG.md)
- [docs/releases/README.md](docs/releases/README.md)
- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)

`main` ?†æ”¯??v1.1.0 ä¹‹å?å·²æ?è¼ƒå? hardening?runtime?adoption?advisory?closeout ?‡æ?ä»¶æ•´?†é€²å???
v1.2.0 = Phase D governance baseline freeze + runtime structural enforcement v0.1??

## å¿«é€Ÿé?è­?

```bash
pip install -r requirements.txt
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

## å°å…¥?°å…¶ä»?repo

å®Œæ•´ adopt è·¯å?ï¼?

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

å¦‚æ?ä½ åª?€è¦æ?å°æ²»?†éª¨?¶ï??¯ä»¥?ˆç”¨ï¼?

- [examples/starter-pack/](examples/starter-pack/)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)

ä½?starter-pack ä¸ç??¼å???adoptï¼Œå??ªæ˜¯ä¸€?‹æ?å°æ²»?†èµ·é»ã€?

å»¶ä¼¸?±è?ï¼?

- [docs/consuming-repo-adoption-checklist.md](docs/consuming-repo-adoption-checklist.md)
- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)

