# AI Governance Framework

> 一個面向 AI-assisted development 的 repo-level governance runtime。  
> 它把 task / session 的 decision、evidence、memory、review surface 收成可被檢查與追溯的 bounded runtime，而不是只靠 prompt discipline 的鬆散協作。

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## 目前定位

這個 repo 目前比較準確的描述是：

- 一個用於 AI-assisted development 的 `machine-interpretable governance runtime`
- 它把 `execution`、`evidence`、`decision`、`memory / state`、`reviewer surface` 串成可檢查的 runtime workflow
- 它不是只提供 prompt 規範，而是提供可落地的 task / session governance spine

目前已成立的核心包括：

- runtime loop：`session_start -> pre_task_check -> post_task_check -> session_end`
- `decision_context` 已進入 verdict / trace / session artifact
- reviewer-visible 的 advisory semantics 已成立，但仍刻意保持 non-verdict-bearing
- execution / state integrity signal 已有 bounded observation surface

目前**不主張**的範圍：

- full execution harness
- machine-authoritative advisory system
- generic `multi-agent orchestration platform`
- full agent-ready determinism

這些 non-claims 是定位的一部分，不是附註。這個 repo 仍保有 prototype boundary，屬於 bounded runtime，而不是全面展開的 AI runtime platform。

## 核心結構

### 1. Runtime Hooks

- [runtime_hooks/core/session_start.py](runtime_hooks/core/session_start.py)
- [runtime_hooks/core/pre_task_check.py](runtime_hooks/core/pre_task_check.py)
- [runtime_hooks/core/post_task_check.py](runtime_hooks/core/post_task_check.py)
- [runtime_hooks/core/session_end.py](runtime_hooks/core/session_end.py)

### 2. Governance Tools

- [governance_tools/](governance_tools/)
- [governance_tools/adopt_governance.py](governance_tools/adopt_governance.py)
- [governance_tools/governance_drift_checker.py](governance_tools/governance_drift_checker.py)
- [governance_tools/quickstart_smoke.py](governance_tools/quickstart_smoke.py)
- [governance_tools/external_repo_readiness.py](governance_tools/external_repo_readiness.py)

### 3. Governance Source

- [governance/](governance/)
- [governance/AGENT.md](governance/AGENT.md)
- [governance/SYSTEM_PROMPT.md](governance/SYSTEM_PROMPT.md)
- [governance/TESTING.md](governance/TESTING.md)
- [governance/ARCHITECTURE.md](governance/ARCHITECTURE.md)
- [governance/governance_decision_model.v2.6.json](governance/governance_decision_model.v2.6.json)

### 4. Reviewer / Status Surface

- [docs/status/README.md](docs/status/README.md)
- [docs/status/runtime-governance-status.md](docs/status/runtime-governance-status.md)
- [docs/status/trust-signal-dashboard.md](docs/status/trust-signal-dashboard.md)
- [docs/status/reviewer-handoff.md](docs/status/reviewer-handoff.md)

## 版本狀態

目前最後一個正式對外 release-facing 版本仍是：
- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/releases/README.md](docs/releases/README.md)

`main` 分支後續已包含較新的 post-release hardening、runtime、adoption、advisory、decision-context 變更；請用 `README.md`、`docs/status/` 與 `memory/` 理解當前狀態，不要把它們倒推成已正式發版能力。

## 快速開始

```bash
pip install -r requirements.txt
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

## 導入到其他 repo

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

參考：
- [docs/consuming-repo-adoption-checklist.md](docs/consuming-repo-adoption-checklist.md)
- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
