# AI Governance Framework

> 這是一個面向 AI-assisted development 的 `machine-interpretable governance runtime`。  
> 它聚焦於 task / session 層級的 `execution`、`evidence`、`decision`、`memory / state` 與 reviewer-facing governance surfaces。

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
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

## Phase D Governance Authority

`v1.2.0` 增加了 Phase D close semantics 的 authority contract 與 runtime structural enforcement。

**Constitutional authority contract**：[governance/PHASE_D_CLOSE_AUTHORITY.md](governance/PHASE_D_CLOSE_AUTHORITY.md)
**Runtime implementation**：[governance_tools/phase_d_closeout_writer.py](governance_tools/phase_d_closeout_writer.py)

### 已有 runtime 支援（F1–F11）

- Artifact 存在性與 schema 驗證（fail-closed）
- `reviewer_id` / `confirmed_at` / `confirmed_conditions` 欄位完整性
- F10/F11：minimum confirmed_conditions coverage（5 個必要條件）
- Machine-readable failure output（`failure_code` / `failure_class` / `remediation`）
- VRB-3 exception override 明確標記為 `unsupported`（不是默默無效）

### 尚未有 runtime 自動偵測（reviewer-attested / audit-invalidatable）

- F12–F15：legitimacy failures（self-review / proxy review / wrong scope / retroactive signing）
- F4：artifact immutability hash（post-issuance modification）
- F16/F17：exception authority artifact path（合約定義了路徑，runtime 尚未實作）

**準確描述**：PHASE_D_CLOSE_AUTHORITY has runtime-aligned structural enforcement v0.1.
Legitimacy failures remain reviewer-attested and audit-invalidatable.
This is not full runtime enforcement of the constitutional contract.

---

## 版本狀態

- [CHANGELOG.md](CHANGELOG.md)
- [docs/releases/README.md](docs/releases/README.md)
- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)

`main` 分支在 v1.1.0 之後已有較多 hardening、runtime、adoption、advisory、closeout 與文件整理進展。
v1.2.0 = Phase D governance baseline freeze + runtime structural enforcement v0.1。

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
