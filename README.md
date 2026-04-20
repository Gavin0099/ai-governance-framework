# AI Governance Framework

> 這是一個面向 AI-assisted development 的 `machine-interpretable governance runtime`。  
> 它聚焦於 task / session 層級的 `execution`、`evidence`、`decision`、`memory / state` 與 reviewer-facing governance surfaces。

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## 目前定位

這個 repo 的核心不是單純的 prompt discipline，也不是泛用 agent platform，而是：

- 把治理規則整理成可被 runtime 消費的 canonical source
- 把 session 開始、執行、結束收斂成可驗證的治理流程
- 把 memory / closeout / reviewer handoff / status surface 變成可追蹤的輸出
- 讓 consuming repo 能以 adopt / readiness / drift / source audit 的方式接入

目前已經涵蓋的主要面向：

- `execution`
- `evidence`
- `decision`
- `memory / state`
- `reviewer surface`

## 明確不主張的範圍

本 repo **不是**：

- full execution harness
- machine-authoritative advisory system
- generic multi-agent orchestration platform
- full agent-ready determinism substrate

這些 non-claims 很重要。它們不是附註，而是目前 repo 邊界的一部分。

## 主要組成

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

## 版本狀態

正式 release-facing 版本目前仍是：

- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/releases/README.md](docs/releases/README.md)

`main` 分支在這之後已有較多 hardening、runtime、adoption、advisory、closeout 與文件整理進展。  
因此：

- release docs 代表正式對外版本
- `README.md`、`docs/status/`、`memory/` 代表主分支較新的現況

## 快速驗證

```bash
pip install -r requirements.txt
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

## 導入到其他 repo

完整 adopt 路徑：

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

如果你只需要最小治理骨架，可以先用：

- [examples/starter-pack/](examples/starter-pack/)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)

但 starter-pack 不等於完整 adopt，它只是一個最小治理起點。

延伸閱讀：

- [docs/consuming-repo-adoption-checklist.md](docs/consuming-repo-adoption-checklist.md)
- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
