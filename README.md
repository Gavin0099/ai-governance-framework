# AI Governance Framework

讓 AI 任務「可追蹤、可審核、可交接」的治理框架。

## 這個 Repo 解決什麼問題？
在 AI/Agent 幫你執行工作時，常見痛點是：
- 你不知道它到底做了哪些步驟
- 你不知道輸出是否有足夠證據可驗證
- 團隊很難在 reviewer 之間一致地判斷結果

這個 repo 提供可機器讀取的治理流程，讓你在每次任務後得到：
- execution evidence（執行證據）
- reviewer 可讀的審核面（status / handoff）
- 非決策型觀測訊號（例如 token observability）

一句話：
**它不是幫你自動下決策，而是幫你把 AI 執行過程變成可驗證的證據。**

## 你可以用它做什麼？
- 在任務前後掛上治理 hook（session_start / pre_task_check / post_task_check / session_end）
- 產生結構化審核輸出（JSON + 人可讀摘要）
- 做跨 repo 的證據彙整（例如 token distribution slice）
- 做 adoption / drift 檢查，確認 consuming repo 是否仍符合治理基線

## 最小使用流程（先跑起來）

### 1) 安裝依賴
```bash
pip install -r requirements.txt
```

### 2) 跑快速 smoke（驗證框架可用）
```bash
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
```
這一步會：
1. 檢查最小治理流程是否可執行
2. 產生基本 execution/governance 證據
3. 提供人可讀結果供 reviewer 確認

### 3) 跑 drift 與 surface 檢查
```bash
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```
這一步會：
- 檢查治理設定是否漂移
- 檢查 runtime surface 與 coverage 是否仍在預期範圍

## 你會得到什麼輸出？（範例）
任務結束後，你會看到類似以下的結構化欄位：

```json
{
  "decision_usage_allowed": false,
  "analysis_safe_for_decision": false,
  "token_observability_level": "step_level",
  "token_source_summary": "mixed(provider, estimated)",
  "provenance_warning": "mixed_sources"
}
```

解讀重點：
- `decision_usage_allowed=false`：不可直接拿去做自動決策/封鎖
- `token_*`：觀測用途（效率/可見度），不是權威決策訊號

## 核心目錄

### Runtime Hooks
- [runtime_hooks/core/session_start.py](runtime_hooks/core/session_start.py)
- [runtime_hooks/core/pre_task_check.py](runtime_hooks/core/pre_task_check.py)
- [runtime_hooks/core/post_task_check.py](runtime_hooks/core/post_task_check.py)
- [runtime_hooks/core/session_end.py](runtime_hooks/core/session_end.py)

### Governance Tools
- [governance_tools/](governance_tools/)
- [governance_tools/adopt_governance.py](governance_tools/adopt_governance.py)
- [governance_tools/governance_drift_checker.py](governance_tools/governance_drift_checker.py)
- [governance_tools/external_repo_readiness.py](governance_tools/external_repo_readiness.py)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)

### 治理規範來源（Canonical Source）
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

## 這個 Repo「不是」什麼
- 不是自動決策引擎
- 不是 production readiness 的單一證明
- 不是 full regression 的替代品
- 不是通用多代理編排平台

## Cross-Repo Token Controlled Slice（目前收斂狀態）

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

參考文件：
- [docs/payload-audit/token-cross-repo-summary-2026-05-05.md](docs/payload-audit/token-cross-repo-summary-2026-05-05.md)
- [docs/payload-audit/token-cross-repo-index-2026-05-06.md](docs/payload-audit/token-cross-repo-index-2026-05-06.md)
- [docs/payload-audit/token-observability-misuse-scenarios-v0.1.md](docs/payload-audit/token-observability-misuse-scenarios-v0.1.md)

## Release / 版本
- [CHANGELOG.md](CHANGELOG.md)
- [docs/releases/README.md](docs/releases/README.md)
- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)

## 在其他 Repo 套用
```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

延伸文件：
- [examples/starter-pack/](examples/starter-pack/)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)
- [docs/consuming-repo-adoption-checklist.md](docs/consuming-repo-adoption-checklist.md)
- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
