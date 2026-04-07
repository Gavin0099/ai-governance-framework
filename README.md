# AI Governance Framework

> 一個給 AI-assisted development 使用的 repo-level governance runtime。  
> 它的目標不是替代模型能力，而是在 task / session 邊界上，把 decision、evidence、memory、review 變成可檢查、可追溯、可重建的工程系統。

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## 目前定位

這個 repo 仍然可以準確描述為一個 `AI governance framework`，但它已經不只是 prompt / 規則包裝層，也不只是靜態政策文件集合。

目前比較準確、且有邊界的描述是：

- 一個面向 AI-assisted development 的 `machine-interpretable governance runtime`
- 具備可執行的 `decision boundary`、可審查的 artifact，以及 state-aware 的 session governance
- 橫跨 `execution`、`evidence`、`decision`、`memory / state`、`reviewer surface`

目前已經成立的能力：

- 真正可執行的 runtime loop：  
  `session_start -> pre_task_check -> post_task_check -> session_end`
- 帶有 `decision_context` 的 verdict / trace / session artifact
- reviewer-visible 的 advisory semantics，可降低誤讀但不擴張 verdict authority
- 可被檢視的 execution / state integrity signal，而不是隱藏的 prompt 政策來源

目前**不主張**的範圍：

- 完整的 execution harness
- machine-authoritative 的 advisory system
- 通用型 `multi-agent orchestration platform`
- 在所有 tool surface 上都已達成 full agent-ready determinism

## 這個框架要解決什麼

AI 協作工作流最常見的崩壞方式，不是模型突然變弱，而是缺少跨 task / session 的工程約束：

- AI 沒有穩定的 task entry / exit discipline
- session 切換後，decision 依據和 evidence 容易漂移
- reviewer 看得到輸出，但看不到輸出是在什麼完整度上下文下做出的
- repo 內的規則、artifact、memory、adoption 狀態缺少一致的治理骨架

這個 framework 的核心主張是：

> 不要只靠 prompt 要求 AI 做對事。  
> 要把 decision boundary、artifact、memory、review surface 做成可執行的 runtime 路徑。

## 核心流程

```text
AI
  -> session_start
  -> pre_task_check
  -> task execution
  -> post_task_check
  -> session_end
  -> reviewable artifacts / memory governance
```

這個流程的意義不是攔截每一個 token，而是讓 repo 在 task / session 邊界上有一致的 governance spine。

## 核心組成

### 1. Runtime Hooks

位置：

- [runtime_hooks/core/session_start.py](runtime_hooks/core/session_start.py)
- [runtime_hooks/core/pre_task_check.py](runtime_hooks/core/pre_task_check.py)
- [runtime_hooks/core/post_task_check.py](runtime_hooks/core/post_task_check.py)
- [runtime_hooks/core/session_end.py](runtime_hooks/core/session_end.py)

作用：

- `session_start`：建立 task / contract / plan 的起始治理上下文
- `pre_task_check`：在 task 開始前做 rule / boundary / injection / advisory 檢查
- `post_task_check`：在 task 執行後檢查 evidence、validator、policy violation
- `session_end`：輸出可審查的 session artifact，並附帶 `decision_context`

### 2. Governance Tools

位置：

- [governance_tools/](governance_tools/)

主要用途：

- adopt / refresh 基線
- drift 檢查
- external repo readiness / onboarding
- release / trust signal / reviewer handoff
- runtime surface manifest / execution coverage / memory sync signal

常見入口：

- [governance_tools/adopt_governance.py](governance_tools/adopt_governance.py)
- [governance_tools/governance_drift_checker.py](governance_tools/governance_drift_checker.py)
- [governance_tools/quickstart_smoke.py](governance_tools/quickstart_smoke.py)
- [governance_tools/external_repo_readiness.py](governance_tools/external_repo_readiness.py)

### 3. Governance Source

位置：

- [governance/](governance/)

這裡放的是 repo engineering governance 的 canonical source，例如：

- [governance/AGENT.md](governance/AGENT.md)
- [governance/SYSTEM_PROMPT.md](governance/SYSTEM_PROMPT.md)
- [governance/TESTING.md](governance/TESTING.md)
- [governance/ARCHITECTURE.md](governance/ARCHITECTURE.md)
- [governance/governance_decision_model.v2.6.json](governance/governance_decision_model.v2.6.json)

### 4. External Domain Contract Seam

這個 framework 的一個關鍵特點，是它不只治理本 repo，還支援 external domain contract seam：

- `contract.yaml` discovery
- external rule root
- validator preflight / execution
- `hard_stop_rules`
- domain-specific enforcement slice

目前 repo 已有的代表性 slice 包括：

- USB hub / firmware 相關 example
- kernel driver contract path
- IC verification contract path

### 5. Memory / State

這裡的 `memory` 指的是 repo memory 與 session artifact，不等於 host-agent 自己的平台記憶。

目前已存在的治理面向包括：

- memory schema completeness
- memory sync policy / signal
- session artifact 中的 `decision_context`

相關文件：

- [docs/host-agent-memory-gap.md](docs/host-agent-memory-gap.md)
- [docs/host-agent-memory-sync-policy.md](docs/host-agent-memory-sync-policy.md)
- [docs/decision-context-bridge.md](docs/decision-context-bridge.md)

### 6. Reviewer / Status Surface

這個 repo 很重視 reviewer-visible output，而不是只在內部藏機制。

穩定入口：

- [docs/status/README.md](docs/status/README.md)
- [docs/status/runtime-governance-status.md](docs/status/runtime-governance-status.md)
- [docs/status/trust-signal-dashboard.md](docs/status/trust-signal-dashboard.md)
- [docs/status/reviewer-handoff.md](docs/status/reviewer-handoff.md)

## 正式發版狀態

目前正式 `release-facing` 狀態：

- 正式版本：`v1.1.0`（2026-03-22）
- release note：[docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- previous release：[docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)
- changelog：[CHANGELOG.md](CHANGELOG.md)
- release index：[docs/releases/README.md](docs/releases/README.md)

補充說明：

- 目前正式對外 release-facing 狀態仍以 `v1.1.0` 為準。
- `main` 分支在這之後已累積多個 post-release hardening、runtime、adoption、advisory、decision-context 相關改動。
- 這些變更目前反映在 `README.md`、`docs/status/`、`memory/` 與相關技術文件中，但**尚未整理成新的正式 release note**。

因此：

- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md) 代表最後一個正式發版狀態
- `README.md` 與 `docs/status/` 反映的是目前 `main` 分支較新的能力邊界

## 目前主分支已具備的進展

除了 `v1.1.0` 正式內容之外，`main` 已經往前推進了幾條重要主線：

- DBL first slice 已進入 runtime decision path
- reviewer onboarding / beta gate 已拆成 human 與 agent-assisted 兩條
- agent-assisted adoption 已有第一份可審查 baseline
- runtime surface manifest 與 execution coverage first slice 已落地
- `decision_context` 已進入 artifact，並開始被 reviewer surface 消費
- advisory slice v1 已收斂為一個受限、reviewer-visible、non-verdict-bearing 的語義基礎層

如果你要看這些較新的現況，請優先讀：

- [docs/status/runtime-governance-status.md](docs/status/runtime-governance-status.md)
- [docs/decision-context-bridge.md](docs/decision-context-bridge.md)
- [docs/advisory-slice-boundary.md](docs/advisory-slice-boundary.md)

## 適合什麼樣的 repo

這個 framework 目前比較適合：

- 有明確 `PLAN.md` / `contract.yaml` / reviewer surface 的 repo
- 需要 task / session 邊界治理的 AI-assisted development workflow
- architecture-sensitive 或 domain-sensitive 的 coding repo
- 想做 external contract seam、mixed enforcement、reviewable artifact 的團隊

相對不適合：

- 只想要 prompt 範本、不想引入治理骨架的 repo
- 不願意維護 `PLAN.md` / `contract.yaml` / baseline 的 repo
- 把它當成 IDE 內每個 action 都攔截的 per-action sandbox

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 跑 quickstart smoke

```bash
python governance_tools/quickstart_smoke.py \
  --project-root . \
  --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

預期類似：

```text
[quickstart_smoke]
ok=True
summary=ok=True | pre_task_ok=True | session_start_ok=True | contract=...
```

### 3. 跑 drift check

```bash
python governance_tools/governance_drift_checker.py --repo . --framework-root .
```

### 4. 看 runtime surface / coverage 狀態

```bash
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

## 導入到其他 repo

如果要把這個 framework 導入到別的 repo，標準入口是：

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

常用參數：

- `--target PATH`：目標 repo
- `--framework-root PATH`：明確指定 framework root
- `--refresh`：重算 baseline 與 inventory
- `--dry-run`：只預覽，不落檔

相關文件：

- [docs/consuming-repo-adoption-checklist.md](docs/consuming-repo-adoption-checklist.md)
- [docs/hearth-memory-schema-validation.md](docs/hearth-memory-schema-validation.md)
- [docs/hearth-memory-schema-run-2026-04-01.md](docs/hearth-memory-schema-run-2026-04-01.md)

## Submodule 使用邊界

如果這個 repo 被其他 repo 以 `submodule` 或 nested checkout 方式引用：

- 這個 repo 是獨立 workspace，不是 parent repo 的延伸
- 不能把這個 repo 的 `memory/`、`artifacts/`、`governance/` 和 parent repo 混用
- submodule pointer 更新屬於 parent repo 的決策，不應默認 framework checkout 前進就等於 parent repo 已採用新版本

相關說明：

- [AGENTS.md](AGENTS.md)

## 常用命令

### Governance Tools

```bash
python governance_tools/adopt_governance.py --target /path/to/repo
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/external_repo_readiness.py --repo /path/to/repo --framework-root .
python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/reviewer_handoff_summary.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --format human
```

### Runtime Hooks

```bash
python runtime_hooks/core/pre_task_check.py --contract ./contract.yaml --format human
python runtime_hooks/core/session_start.py --project-root . --plan PLAN.md --format human
python runtime_hooks/core/post_task_check.py --response-file ai_response.txt --format human
python runtime_hooks/core/session_end.py --project-root . --session-id demo-session
```

### Smoke

```bash
python runtime_hooks/smoke_test.py --event-type session_start
python runtime_hooks/smoke_test.py --harness claude_code --event-type pre_task
```

### Shared Enforcement Entrypoint

`scripts/run-runtime-governance.sh` is the shared enforcement entrypoint used by runtime hooks and CI.
See [runtime_hooks/README.md](runtime_hooks/README.md) for details.

## 建議閱讀順序

如果你第一次進這個 repo，建議順序：

1. [docs/status/reviewer-handoff.md](docs/status/reviewer-handoff.md)
2. [docs/status/trust-signal-dashboard.md](docs/status/trust-signal-dashboard.md)
3. [docs/status/runtime-governance-status.md](docs/status/runtime-governance-status.md)
4. [docs/technical-overview.zh-TW.md](docs/technical-overview.zh-TW.md)
5. [docs/decision-boundary-layer.md](docs/decision-boundary-layer.md)
6. [docs/decision-context-bridge.md](docs/decision-context-bridge.md)
7. [docs/agent-native-positioning.md](docs/agent-native-positioning.md)

## 限制與邊界

目前這個 repo 仍然是有意識地 bounded：

- 不是 full execution harness
- 不是 generic multi-agent OS
- 不是 enterprise-wide AI compliance suite
- 不是把每個 advisory signal 都升格成 machine-facing authority

如果你想看目前已明講的限制，請看：

- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)

## 相關文件

- [docs/technical-overview.zh-TW.md](docs/technical-overview.zh-TW.md)
- [docs/runtime-governance-update.md](docs/runtime-governance-update.md)
- [docs/decision-boundary-layer.md](docs/decision-boundary-layer.md)
- [docs/decision-boundary-first-slice.md](docs/decision-boundary-first-slice.md)
- [docs/decision-context-bridge.md](docs/decision-context-bridge.md)
- [docs/agent-native-positioning.md](docs/agent-native-positioning.md)
- [docs/competitive-landscape.md](docs/competitive-landscape.md)
- [runtime_hooks/README.md](runtime_hooks/README.md)
- [governance_tools/README.md](governance_tools/README.md)
- [memory_pipeline/README.md](memory_pipeline/README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
