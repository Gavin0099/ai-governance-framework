# AI Governance Framework — 完整技術文件

> **版本**：v1.1.0 · 2026-03-22
> **作者**：GavinWu672
> **Repo**：github.com/Gavin0099/ai-governance-framework

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [架構設計](#2-架構設計)
3. [治理憲法：8 大法典](#3-治理憲法8-大法典)
4. [Runtime Hooks：執行時治理](#4-runtime-hooks執行時治理)
5. [Governance Tools：靜態工具集](#5-governance-tools靜態工具集)
6. [Memory Pipeline：AI 記憶系統](#6-memory-pipelineai-記憶系統)
7. [External Domain Contract Seam：外部合約接縫](#7-external-domain-contract-seam外部合約接縫)
8. [Examples：可執行範例](#8-examples可執行範例)
9. [CI / CD 整合](#9-ci--cd-整合)
10. [採用指南](#10-採用指南)
11. [已知限制與誠實評估](#11-已知限制與誠實評估)
12. [Before / After 對比](#12-before--after-對比)
13. [快速指令參考](#13-快速指令參考)

---

## 1. 專案概覽

### 1.1 一句話定義

一套讓 AI 工具（Claude、Codex、Gemini 等）在你的工程專案中「按規矩辦事」的可執行治理運行時框架，不只是靜態政策文件，而是在每次 AI session 邊界實際攔截、驗證、審計的完整工具鏈。

### 1.2 解決的核心問題

多數 AI 協作工作流的崩壞方式都一樣，不是模型不夠好，而是沒有任何機制在跨 session 之間保持一致性：

- AI 忘記你兩天前做的決策
- 它偏離了你目前的 sprint 或開發階段
- 它越過了本來不應該碰的架構邊界
- 它完成任務後什麼可查的紀錄都沒留下
- 沒有 drift 偵測，技術債在不知不覺中累積

### 1.3 框架定位

這個框架在 **task 和 session 邊界**治理，不在模型的 token generation 內部。它不是：

- 企業級 AI 模型治理（NIST AI RMF / EU AI Act 合規）
- AI 輸出的技術強制攔截（每個 token 都被約束）
- 替代 code review 或 QA 流程
- 多 AI agent 的資源隔離或 RBAC 存取控制

### 1.4 專案規模

> 下列統計為此版本文件整理時的快照，後續可能隨 repo 演進而變動。

| 維度 | 數字 |
|------|------|
| Python 模組總數 | 211 個 `.py` 檔 |
| `governance_tools/` 工具集 | 70 個工具，共 18,490 行程式碼 |
| `runtime_hooks/` 執行時 hook | 20 個檔，共 2,294 行 |
| `memory_pipeline/` 記憶系統 | 5 個模組，共 722 行 |
| `tests/` 測試套件 | 98 個測試檔，共 19,805 行 |
| 測試總數 | 1,333 個自動化測試 |
| GitHub commits | 300+ |
| 目前版本 | v1.1.0（2026-03-22） |

---

## 2. 架構設計

### 2.1 五層架構總覽

框架採用由上而下的五層設計，每層職責明確：

```text
┌─────────────────────────────────────────────────────────┐
│  Layer 0：AI 工具層                                       │
│  Claude · Codex · Gemini（透過 Adapter 接入）             │
├─────────────────────────────────────────────────────────┤
│  Layer 1：Runtime Hooks（執行時鉤子）                     │
│  session_start → pre_task → post_task → session_end      │
├───────────────┬──────────────────┬──────────────────────┤
│  Layer 2a     │  Layer 2b        │  Layer 2c            │
│  Governance   │  Static Tools    │  Memory Pipeline     │
│  Constitution │  governance_tools│  memory_pipeline/    │
│  8 大法典     │  / 70 個工具     │  記憶管理            │
├───────────────┴──────────────────┴──────────────────────┤
│  Layer 3：External Domain Contract Seam（接縫）           │
│  contract.yaml 自動發現 · validator preflight            │
│  hard_stop_rules 強制執行                                 │
├───────────────┬──────────────────┬──────────────────────┤
│  Layer 4a     │  Layer 4b        │  Layer 4c            │
│  USB-Hub-FW   │  Kernel-Driver   │  IC-Verification     │
│  Contract     │  Contract        │  Contract            │
└───────────────┴──────────────────┴──────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        │  CI / Git hooks                 │
        │  governance.yml · exit codes    │
        └─────────────────────────────────┘
```

### 2.2 Engine + Plugin 分離模式

框架最核心的設計決策是 Engine 與 Plugin 的完全分離：

- **Engine**（`ai-governance-framework`）：通用治理邏輯、流程控制、驗證閉環
- **Plugin**（各 domain 合約 repo）：領域專業規則，可插拔、可替換、可獨立版本化
- **接縫**（`contract.yaml`）：標準化介面，Engine 透過它自動發現並載入 Plugin

這意味著你可以在不修改 Engine 的情況下，新增任意新的 domain 合約，例如新晶片類型的驗證規則。

### 2.3 Governance Decision Model v2.6

`governance/governance_decision_model.v2.6.json` 是整個 runtime 行為的機器可查規格：

| 欄位 | 說明 |
|------|------|
| `enforcement_model` | 違規如何影響 verdict：stop / escalate / degrade / record-only |
| `decision_ownership_matrix` | 每個治理決策的 owner 是誰、誰可以 override、是否需要留下 trace |
| `policy_precedence_matrix` | Runtime / Repo / Domain / Reviewer 政策的優先級覆蓋規則 |
| `evidence_trust_matrix` | 哪些來源的 evidence 可信、信任程度如何分級 |
| `violation_impact_matrix` | 違規的嚴重性如何對應到 CI gate 行為 |
| `determinism_contract` | fallback 行為的確定性保證，runtime 不確定時的強制行為 |

### 2.4 三層 Governance 文件體系

| Tier | 文件 | 載入條件 |
|------|------|----------|
| 0 | `SYSTEM_PROMPT.md`、`HUMAN-OVERSIGHT.md`、`PLAN.md` | 每次對話強制載入 |
| 1 | `AGENT.md`、`ARCHITECTURE.md`、`TESTING.md`、`REVIEW_CRITERIA.md` | 任務觸發載入 |
| 2 | `NATIVE-INTEROP.md` | 涉及 P/Invoke、ABI、native 邊界時 |

高優先級文件與低優先級文件發生衝突時，AI 必須停止並升級，不得自行解決衝突。

---

## 3. 治理憲法：8 大法典

`governance/` 目錄存放 8 份核心治理文件，構成 AI 在此 repo 中的行為憲法。

### 3.1 SYSTEM_PROMPT.md（v5.3）—— 核心意識

最高優先級文件，每次對話強制載入。

**身份定義**：Governance-first coding agent，角色涵蓋 Implementer / Rule Enforcer / Risk Gatekeeper / Memory Steward

**強制初始化 8 步驟**（缺任一步驟 → STOP）：

1. Header 驗證：確認 `LANG` / `LEVEL` / `SCOPE`
2. Memory sync：讀取 `PLAN.md` 和 `memory/` 目錄
3. Pre-exploration gate：確認任務類型和工具比例
4. Bounded context 宣告：明確負責什麼、明確不負責什麼
5. 動態載入宣告：宣告本次 session 需要載入哪些治理文件
6. ADR 衝突檢查：掃描 `docs/adr/` 確認無未解決衝突
7. 記憶壓力檢查：檢查 `memory/01_active_task.md` 行數
8. Governance contract 輸出：輸出結構化的合規宣告塊

**三段決策模型**：

- `Continue`：低風險、有界、evidence 可在本地取得
- `Escalate`：方向不確定、多條合理路徑、架構影響不明
- `Stop`：硬性安全或架構紅線、治理文件衝突、正確性無法捍衛

**核心原則**：Correctness > Speed，Clarity > Volume，Explicit trade-offs > Hidden debt

> 停機是真正紅線的成功條件，而非對正常工程不確定性的預設回應。

**Governance contract 輸出格式**（在 task 開始、里程碑完成、scope 變更時輸出）：

```text
[Governance Contract]
LANG     = <C | C++ | C# | ObjC | Swift | JS | Python>
LEVEL    = <L0 | L1 | L2>
SCOPE    = <feature | refactor | bugfix | I/O | tooling | review | governance | kernel-driver>
PLAN     = <current phase> / <sprint> / <task>
LOADED   = <comma-separated list of loaded governance docs>
CONTEXT  = <context name> -> <responsible for X>; NOT: <not responsible for Y>
PRESSURE = <SAFE|WARNING|CRITICAL|EMERGENCY> (<line count>/200)
```

### 3.2 HUMAN-OVERSIGHT.md（v3.1）—— 人工監督協議

優先級第二，定義何時繼續、何時升級、何時停機。

**升級程序**（escalate 時必須做到）：

1. 說明不清楚之處
2. 說明繼續的風險
3. 提出 1 到 3 個具體選項與預期影響
4. 等待人工方向，禁止在實質模糊下自行選擇方向

### 3.3 AGENT.md（v4.3）—— 行為合約

定義 AI 的分級行為與執行管道：

**L0 快速通道**（僅限以下條件全部成立）：

- scope 限於排版、命名、格式等 presentation-only 工作
- 無 domain 邏輯變更、無邊界穿越、無 I/O 或 native interop

**L0 禁止事項**（即使在 L0 也不得做）：

- native interop、記憶體所有權變更
- 引入條件行為、retry / acquisition / sequencing 邏輯
- schema 變更、API contract 變更

**L1 一般任務**：需完整 Analyze → Define → Test → Implement 四階段

**L2 關鍵任務**：核心 domain 邏輯、native 邊界、韌體 flash 路徑、安全性，必須完整套用 `ARCHITECTURE.md` 和 `TESTING.md`，不得在未取得人工授權下縮減。

**Auditor 子模式**：`SCOPE = review` 時執行管道暫停，切換為批判性驗證者角色。

### 3.4 ARCHITECTURE.md（v4.2）—— 架構邊界

**元件分類**：每個被觸及的元件必須可分類為 Domain / Application / Adapter / Infrastructure，且必須能回答「負責什麼」和「明確不負責什麼」。

**L1+ 工作必須先回答**：

- 屬於哪個 bounded context
- 是否涉及 native API 或外部系統
- 是否需要 Anti-Corruption Layer

**紅線**：提議的變更穿越硬性邊界，或無法被一致分類 → STOP

### 3.5 TESTING.md —— 品質守門

依任務等級規定測試深度，L2 任務禁止在未取得人工授權下縮減測試要求。

### 3.6 REVIEW_CRITERIA.md —— 審查協議

`SCOPE = review` 時的行為規範，AI 切換為懷疑性驗證者，不再是實作者。

### 3.7 NATIVE-INTEROP.md —— 原生互操作

涉及 P/Invoke、ABI、native library、記憶體所有權時的安全規則，Tier 2 按需載入。

### 3.8 PLAN.md —— 專案範疇

Sprint 焦點、Phase 狀態、Anti-Goals 的單一真相來源。每週更新，freshness 機制自動偵測過期。

---

## 4. Runtime Hooks：執行時治理

### 4.1 Session 生命週期四個攔截點

| Hook | 時機 | 核心職責 | 行數 |
|------|------|----------|------|
| `session_start` | AI 開始工作前 | 載入 PLAN + contract，設定 session context，L0 domain gate 檢查 | 449 行 |
| `pre_task_check` | 每個 task 開始前 | 根據 rules + risk level 對任務做 gate 檢查，rule pack 選擇 | 389 行 |
| `post_task_check` | 任務完成後 | 驗證 AI 輸出，呼叫 `run_domain_validators()`，產生 verdict artifact | 655 行 |
| `session_end` | Session 結束時 | 寫入 reviewable artifact，觸發 memory pipeline，session 狀態歸檔 | 542 行 |

### 4.2 Multi-AI Tool Adapter

`runtime_hooks/adapters/` 提供三種 AI 工具的標準化接入層：

- `claude_code`：Claude Code CLI adapter，支援 `AGENTS.md` 格式
- `codex`：OpenAI Codex adapter
- `gemini`：Google Gemini adapter

換工具不需要重寫任何治理邏輯，只需切換 adapter。`shared_normalizer.py` 負責跨 adapter 的事件標準化。

### 4.3 Payload Audit 系統（Token 優化）

環境變數 `GOVERNANCE_PAYLOAD_AUDIT=1` 啟用完整的 token 量測記錄：

| 路徑 | Before | After | 削減 |
|------|--------|-------|------|
| L0 + L1（嚴格可比基線） | 44,073 tokens | 28,114 tokens | -36.2% |
| 整體觀察（全部路徑） | 104,696 tokens | 49,202 tokens | -53.0% |
| KDC summary-first onboarding | 60,623 tokens | 37,142 tokens | -38.7% |

### 4.4 Rule Pack 系統

| Pack 名稱 | 用途 | 載入模式 |
|-----------|------|----------|
| `common` | 通用基線規則 | always（所有 repo） |
| `refactor` | 重構指導規則 | context_aware |
| `python` | Python 程式碼標準 | context_aware |
| `cpp` | C/C++ 程式碼標準 | context_aware（韌體 / Driver repo） |
| `csharp` | C# 程式碼標準 | context_aware |
| `swift` | Swift 程式碼標準 | context_aware |
| `kernel-driver` | Kernel / Driver 特定約束 | context_aware（KDC repo） |
| `avalonia` | Avalonia UI 框架規則 | context_aware |
| `typescript` | TypeScript / Node.js 標準 | context_aware |
| `electron` | Electron IPC 安全規則 | context_aware |
| `nextjs` | Next.js routing 規則 | context_aware |
| `supabase` | Supabase RLS 和 auth 規則 | context_aware |
| `firmware_isr` | ISR 安全和 RTOS 約束 | context_aware（韌體 repo） |
| `release` | Release 檢查清單規則 | context_aware（release session） |
| `review_gate` | Review gate 檢查清單 | context_aware（review session） |

---

## 5. Governance Tools：靜態工具集

`governance_tools/` 包含 70 個工具，總計 18,490 行程式碼。

### 5.1 採用與 Drift 偵測

#### adopt_governance.py（790 行）

跨平台採用工具（macOS / Linux / Windows），取代舊版 bash-only 的 `init-governance.sh`：

- 複製 `AGENTS.base.md`（protected）、建立缺失的 `AGENTS.md` / `contract.yaml` / `PLAN.md` 模板
- 生成 `.governance/baseline.yaml`，包含 sha256 雜湊 + 四層語意（PROVENANCE / INTEGRITY / CONTRACT / OBSERVED）
- `--refresh` 模式：重新雜湊現有 baseline，不複製模板
- `--dry-run` 模式：預覽計畫動作，不寫入任何檔案
- 自動種入 `.github/workflows/governance-drift.yml`（如果目標 repo 尚未有 CI workflow）
- `AGENTS.base.md` 缺少引用時自動修復，避免第一次 drift 檢查失敗

#### governance_drift_checker.py（780 行）

16 項具名 drift 檢查，涵蓋四個類別：

| # | 檢查項 | 說明 | 失敗後果 |
|---|--------|------|----------|
| 1 | `baseline_present` | `baseline.yaml` 是否存在 | CRITICAL |
| 2 | `protected_file_sentinel` | `AGENTS.base.md` 是否存在（hash 驗證） | CRITICAL |
| 3 | `plan_fresh` | `PLAN.md` 是否在 freshness threshold 內 | WARNING |
| 4 | `contract_valid` | `contract.yaml` 是否符合 minimum legal schema | CRITICAL |
| 5 | `hooks_installed` | Git hooks 是否安裝（optional） | INFO |
| 6 | `plan_required_sections` | `PLAN.md` 是否包含必要的 `##` heading | ERROR |
| 7 | `baseline_hashes_match` | tracked 檔案的 sha256 是否與 baseline 吻合 | CRITICAL |
| 8 | `agents_base_referenced` | `AGENTS.base.md` 是否被 contract 引用 | ERROR |
| 9 | `contract_required_fields` | `contract.yaml` 是否包含必填欄位 | CRITICAL |
| 10 | `doc_drift` | 文件是否與程式碼同步 | WARNING |
| 11 | `arch_drift` | 架構邊界是否漂移 | WARNING |
| 12 | `example_readiness` | `examples/` 是否可跑 | WARNING |
| 13 | `contract_no_placeholders` | `contract.yaml` 是否仍有 `<...>` 模板 token | ERROR |
| 14 | `agents_sections_filled` | `AGENTS.md` 的必要 section 是否填寫 | ERROR |
| 15 | `plan_inventory_current` | `PLAN.md` heading 是否與 baseline inventory 吻合 | WARNING |
| 16 | `contract_not_framework_copy` | `contract.yaml` 是否逐字複製自框架模板 | ERROR |

### 5.2 Violation Triage 系統

#### violation_triage.py（548 行）

完整的違規審查流水線：

- **generate 模式**：將工具的 JSON 輸出轉換為 triage 模板，合併現有的人工標注
- **evaluate 模式**：讀取 triage 檔案，評估 CI gate 結果

違規類型：

| 類型 | 意義 |
|------|------|
| `TP`（真陽性） | 真實違規，需修復程式碼 |
| `FP`（假陽性） | 規則或 validator 問題，需修復框架規則 |
| `FN`（漏報） | 框架 bug，最高優先，需修復框架本身 |

Exit code 語意：

| Exit code | 意義 | CI 行為 |
|-----------|------|---------|
| `0` | 通過（或僅有 FP 違規） | 繼續 |
| `1` | 有 TP 或未審查的 CRITICAL 違規 | Block，需修復或標注 triage |
| `2` | 有 FN（框架 bug） | Block，最高優先，需修復框架 |

只有 **CRITICAL 且未審查** 的違規才會 block CI。

### 5.3 Public API Diff Checker

#### public_api_diff_checker.py（674 行）

跨語言靜態 API 分析，偵測破壞性 API 變更：

- C# public / protected internal API 萃取（含 namespace、class、method 解析）
- C++ public class / struct / virtual function 萃取
- Swift public / open class / struct / enum / protocol / func 萃取
- 跨版本 API diff，可在 CI 中阻擋未預期的 API 破壞

### 5.4 Release Pipeline

完整的 release 準備工具鏈：

| 工具 | 功能 |
|------|------|
| `release_readiness.py`（418 行） | 檢查 README、CHANGELOG、release notes、trust dashboard 等 release 文件是否就緒 |
| `release_package_snapshot.py`（397 行） | 快照目前的 release 狀態，供 reviewer 比對 |
| `release_package_summary.py` | 產出人類可讀的 release 摘要 |
| `trust_signal_overview.py`（308 行） | 聚合 quickstart、examples、governance audit、外部 domain repo 的信任訊號 |
| `trust_signal_snapshot.py`（714 行） | 發布穩定的信任訊號快照頁面到 `docs/status/generated/` |
| `reviewer_handoff_summary.py` | 產出給 reviewer 的交接摘要，含 session history 和 domain 合約狀態 |

### 5.5 第三方整合（Notion + Linear）

#### notion_integrator.py（567 行）

從 `memory/01_active_task.md` 解析任務，自動建立 Notion Database Page：

- 任務 ID 寫回本地，防止重複建立
- 送出前掃描敏感資訊（防止 secret 洩漏）
- API 失敗時優雅降級，不影響本地工作流
- 零第三方依賴（純 stdlib：`urllib`、`json`、`re`）
- 環境變數：`NOTION_API_KEY` + `NOTION_DATABASE_ID`

#### linear_integrator.py（500 行）

與 Linear issue tracker 的雙向同步：

- 從 `memory/01_active_task.md` 解析任務，自動建立 Linear Issue
- 雙向同步狀態（Linear ↔ active_task）
- 每個操作記錄在 `memory/03_knowledge_base.md`，可審計
- 零第三方依賴（純 stdlib）

### 5.6 其他重要工具

| 工具 | 說明 |
|------|------|
| `architecture_drift_checker.py` | 偵測架構邊界是否漂移 |
| `architecture_impact_estimator.py` | 估算變更對架構的衝擊範圍 |
| `change_control_summary.py` | 變更控制摘要，追蹤變更歷史 |
| `contract_validator.py` | 驗證 AI 回覆是否包含合規的 Governance Contract 初始化宣告 |
| `domain_validator_loader.py`（321 行） | 載入並執行 domain plugin 的 validators |
| `external_repo_readiness.py`（451 行） | 評估外部 repo 是否符合採用條件 |
| `framework_risk_signal.py` | 計算框架整體風險訊號 |
| `l0_domain_gate.py` | L0 任務的 domain 邊界 gate 檢查 |
| `memory_janitor.py`（394 行） | 記憶管理：歸檔、壓縮、pointer 管理 |
| `payload_audit_logger.py`（355 行） | Token 量測與 payload 審計記錄 |
| `plan_freshness.py`（315 行） | `PLAN.md` freshness 檢查，支援 threshold 設定 |
| `reasoning_compressor.py` | 壓縮 AI 推理過程，降低 context token 消耗 |
| `rule_classifier.py`（312 行） | 依 `repo_type` / `task_type` 分類適用的 rule pack |
| `state_generator.py` | 生成可重現的 session 狀態快照 |
| `task_level_detector.py` | 自動偵測任務應分類為 L0 / L1 / L2 |
| `workflow_entry_observer.py` | 觀察 AI 工作流進入點，偵測 bypass 路徑 |

---

## 6. Memory Pipeline：AI 記憶系統

### 6.1 記憶架構

Memory pipeline 解決 AI 最根本的問題：每次對話都是從零開始。框架通過結構化的記憶管理讓 AI 跨 session 保持狀態：

| 記憶檔案 | 用途 | 更新時機 |
|----------|------|----------|
| `memory/01_active_task.md` | 目前任務狀態（最常用，200 行上限） | 里程碑完成、commit 準備、任務關閉 |
| `memory/02_tech_stack.md` | 技術架構和工具鏈事實 | 架構決策時 |
| `memory/03_knowledge_base.md` | 故障排除和反模式 | 發現新 gotcha 或解法時 |
| `memory/04_review_log.md` | review 完整記錄 | 每次 review 完成後 |

**更新原則**：不記錄每個 micro-step，只記錄 session 重啟後仍有意義的狀態變化。

### 6.2 記憶壓力管理

系統根據 `memory/01_active_task.md` 行數自動分級：

| 等級 | 行數範圍 | 行為 |
|------|----------|------|
| `SAFE` | 0 到 179 行 | 正常繼續 |
| `WARNING` | 180 到 199 行 | 警告並避免低訊號更新 |
| `EMERGENCY` | 200+ 行 | 強制停機，清理記憶後才能繼續 |

### 6.3 Memory Pipeline 模組

| 模組 | 功能 | 行數 |
|------|------|------|
| `session_snapshot.py` | 在 session 邊界捕捉完整的記憶快照 | 73 行 |
| `memory_curator.py` | 篩選並保留高信噪比的記憶項目 | 350 行 |
| `memory_promoter.py` | 將 curator 選出的項目提升為長期記憶 | 111 行 |
| `promotion_policy.py` | 定義什麼條件下的記憶值得升級為長期保存 | 163 行 |
| `memory_layout.py` | 記憶檔案結構的 schema 定義 | 25 行 |

---

## 7. External Domain Contract Seam：外部合約接縫

### 7.1 設計理念

Domain contract seam 是框架最關鍵的可擴展性設計。你的韌體規則、Driver 限制、IC 驗證需求各自住在獨立的 repo，透過 `contract.yaml` 插入框架的治理流程。Engine 負責載入和執行，你負責定義規則。

### 7.2 contract.yaml 結構（Minimum Legal Schema）

每個 domain plugin repo 的根目錄必須有 `contract.yaml`，最小必填欄位：

```yaml
name: "my-domain-contract"
framework_interface_version: "1.0"
framework_compatible: true
domain: "firmware"
```

完整欄位還可包含：`hard_stop_rules`、`plan_freshness_threshold_days`、`documents`、`ai_behavior_override`。

### 7.3 已驗證的 Domain Plugins

| Plugin repo | Domain | Hard-stop rules | Advisory rules（僅建議） |
|-------------|--------|-----------------|---------------------------|
| USB-Hub-Firmware-Architecture-Contract | firmware | HUB-004（interrupt safety） | HUB-001（firmware review） |
| Kernel-Driver-Contract | kernel-driver | KD-002、KD-003（pool allocation） | KD-005（pool-allocation guidance） |
| IC-Verification-Contract | ic-verification | ICV-001（verification gate） | ICV-002（clock / reset declaration） |

### 7.4 Domain Enforcement Matrix

`external_contract_policy_index.py` 可產出跨 domain repo 的 enforcement posture 比較表，回答：

- 哪些 domain 仍是 advisory-only
- 哪些 domain 已支援 mixed enforcement
- 哪些 rule ID 目前通過 `hard_stop_rules` 路由

### 7.5 Validator 執行閉環

`post_task_check.py` 在任務完成後自動呼叫 `run_domain_validators()`：

1. `domain_validator_loader.py` 從 `contract.yaml` 發現並載入 validator
2. validator preflight 確認 validator 可執行
3. 執行各 domain validator，收集 evidence
4. `hard_stop_rules` 中的違規直接觸發 stop verdict
5. verdict 和 trace 寫入 `artifacts/runtime/`

---

## 8. Examples：可執行範例

### 8.1 範例清單

| 範例 | 適用場景 | 包含的 Validators |
|------|----------|-------------------|
| `usb-hub-contract` | USB Hub 韌體架構合約 | `interrupt_safety_validator.py` |
| `cpp-userspace-contract` | C++ userspace 安全規則 | `cpp_mutex_safety` / `cpp_raw_memory` / `cpp_reinterpret_cast` |
| `csharp-arch-contract` | C# 架構合約 | `domain_pinvoke_validator` |
| `nextjs-byok-contract` | Next.js BYOK 安全合約 | `byok_key_propagation` / `route_rate_limit` |
| `multi-validator-contract` | 多 validator 組合 | `architecture_drift` / `driver_evidence` / `failure_completeness` / `refactor_evidence` |
| `starter-pack` | 最小版本（3 個文件，5 分鐘起步） | 無（僅核心文件） |
| `todo-app-demo` | 簡單 demo 應用展示 | 基本 governance 流程展示 |
| `chaos-demo` | 故意觸發 governance failure 的壓力測試 | edge case 測試 |

### 8.2 usb-hub-contract 深度解析

最貼近工作場景的範例，包含：

- `USB_HUB_ARCHITECTURE.md`
- `USB_HUB_FW_CHECKLIST.md`
- `contract.yaml`
- `validators/interrupt_safety_validator.py`
- `fixtures/`
- `rules/hub-firmware/safety.md`

### 8.3 `.claude/skills/` —— Claude Code 專用技能

| 技能 | 用途 |
|------|------|
| `codex-review-fast` | 快速 code review 流程 |
| `create-pr` | PR 建立流程（含 governance 檢查） |
| `domain-contract-authoring` | 撰寫新 domain contract 的引導流程 |
| `external-onboarding` | 外部 repo 採用框架的 onboarding 流程 |
| `precommit` | commit 前的 governance 驗證 |
| `reviewer-handoff` | 交接給 reviewer 的標準流程 |
| `runtime-smoke` | runtime governance 快速健康檢查 |
| `tech-spec` | 技術規格文件撰寫 |

---

## 9. CI / CD 整合

### 9.1 GitHub Actions Workflow

`.github/workflows/governance.yml` 定義完整的 CI 治理管道：

- 每次 push 自動執行 drift check（16 項）
- contract validator 驗證合約格式
- examples readiness 確保範例可執行
- trust signal 快照發布
- domain enforcement matrix 更新

### 9.2 GitLab CI

`.gitlab-ci.yml` 提供 GitLab 環境的治理檢查設定，目標涵蓋與 GitHub Actions 對應的 governance 驗證流程。

### 9.3 Git Hooks

`scripts/run-runtime-governance.sh` 是 CI 和 Git hook 的標準進入點：

```bash
bash scripts/run-runtime-governance.sh --mode enforce
bash scripts/run-runtime-governance.sh --mode ci
```

### 9.4 Exit code 語意

| Exit code | 意義 | CI 行為 |
|-----------|------|---------|
| `0` | 通過（或僅有 FP 違規） | 繼續 |
| `1` | 有 TP 或未審查的 CRITICAL 違規 | Block，需修復或標注 triage |
| `2` | 有 FN（框架 bug） | Block，最高優先，需修復框架 |

---

## 10. 採用指南

### 10.1 五分鐘快速起步

```bash
python governance_tools/quickstart_smoke.py \
  --project-root . \
  --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

預期輸出：

```text
[quickstart_smoke]
ok=True
summary=ok=True | pre_task_ok=True | session_start_ok=True | contract=firmware/medium
```

### 10.2 採用現有 Repo

```bash
python governance_tools/adopt_governance.py --target /path/to/repo --dry-run
python governance_tools/adopt_governance.py --target /path/to/repo
python governance_tools/adopt_governance.py --target /path/to/repo --refresh
```

| Flag | 效果 |
|------|------|
| `--target PATH` | 目標 repo 路徑（預設當前目錄） |
| `--framework-root PATH` | Override 框架根目錄（預設自動發現） |
| `--refresh` | 重新雜湊現有 baseline，不複製模板 |
| `--dry-run` | 預覽計畫動作，不寫入任何檔案 |

### 10.3 已驗證的 Repo 類型

| Repo 類型 | 範例 | 採用結果 |
|-----------|------|----------|
| Service（最小後端） | Express HTTP wrapper（ziwei-service） | 採用摩擦識別後修復 |
| Tooling（Python validator 集合） | governance_tools 子集 | 採用摩擦識別後修復 |
| Product（Next.js + Supabase + Claude） | Mirra | `ready=True`，drift 16/16 PASS |
| Governance-heavy | ai-governance-framework 本身 | self-hosting |
| 底層合約 repo | Kernel-Driver-Contract | contract loading、validator preflight 和 summary-first onboarding 全驗證 |

尚未驗證：大型 monorepo / multi-package workspace、data pipeline 或 ML repo、無 PLAN 概念且不打算加入的 repo。

### 10.4 Starter Pack（最小版本）

對 2 到 3 人的初創小團隊，`examples/starter-pack/` 提供最小可行版本：

- 只需 3 個文件：`SYSTEM_PROMPT.md` + `PLAN.md` + `memory_janitor.py`
- 5 分鐘可跑起來
- 簡化版 Governance Contract 只有 2 個欄位（PLAN + PRESSURE）
- 認知負擔從 8 法典 + 工具降到 3 個文件

### 10.5 Freshness Threshold 設定

| 設定來源 | 值 | 優先級 |
|----------|----|--------|
| 框架預設 | 14 天 | 最低 |
| `PLAN.md` policy | 自定義 | 中 |
| `contract.yaml` `plan_freshness_threshold_days` | 自定義 | 最高 |

> 覆蓋超過 14 天時會觸發 guardrail warning。threshold 來源在 drift 輸出中標示清楚。

---

## 11. 已知限制與誠實評估

> 一個聲稱「治理 AI」的框架，若無法誠實描述自己的邊界與失敗案例，就是把「合規儀式」當成「實際安全」。

### 11.1 核心限制

| 等級 | 限制 | 緩解措施 | 狀態 |
|------|------|----------|------|
| L1 | AI 遵守治理文件屬指導性，非技術強制。長對話中可能逐漸遺忘治理文件，開始自行擴大範圍 | `memory_janitor` 監控壓力；每次對話重申 Governance Contract | 部分解決（session drift 自動偵測未完成） |
| L2 | `PLAN.md` 標記完成不等於功能真的完成，Phase 完成依賴人工宣告 | CI `phase-gates` job 提供可驗證條件 | 部分解決（功能完整性驗證未自動化） |
| L3 | 沒有量化的治理遵守率指標，難以證明框架有效 | 暫無自動化指標 | 未解決 |
| L4 | 8 大法典 + 工具對初創小團隊認知負擔偏高 | Starter Pack 最小版本（3 文件） | 部分解決（漸進升級路徑自動化工具未完成） |

### 11.2 攔截覆蓋率尚未完全閉合

目前 runtime hooks 無法覆蓋：

- IDE 本地編輯路徑
- Direct push 到 repo（繞過 pre-commit hook）
- 不支援 `AGENTS.md` 的 AI 工具

### 11.3 尚未壓力測試的假設

- 框架在長達 4 週的連續專案中是否仍有效
- 多人協作（3+ 工程師）時 `PLAN.md` 衝突解法是否足夠
- AI 模型升級後治理行為是否一致
- 大型 monorepo 或 multi-package workspace 的採用
- data pipeline 或 ML repo 的適用性

### 11.4 下一個 Gate

目前最重要的未完成 gate：**獨立審查者不靠作者引導也能完成 onboard**。

---

## 12. Before / After 對比

### Before（無治理框架）

```text
── 對話 1 ────────────────────────────────
User: 幫我加個快取功能
AI:   好的，我來實作 Redis 快取...
      [直接開始寫程式，沒有確認是否在計畫範圍內]

── 對話 8（3 天後）─────────────────────
User: 為什麼這個 bug 還沒修？
AI:   我不確定上次的狀態...
      [前幾次對話的決策已消失在 context 中]
```

結果：AI 不知道優先級，每次對話重新理解，越長越失控，技術債在不知不覺中累積。

### After（有治理框架）

```text
── 對話 1 ────────────────────────────────
User: 幫我加個快取功能
AI:   [Governance Contract] 已讀取
      PLAN.md 本週目標：修復 BUG-003、補齊測試覆蓋率
      快取功能在 Backlog P2，不在本週範圍。
      選項：A) 移入本週（影響現有優先項）B) 維持 P2 C) 調整計畫

── 對話 8（3 天後）────────────────────────
[memory_janitor --check: SAFE (45/200 lines)]
User: 為什麼這個 bug 還沒修？
AI:   根據 PLAN.md 已知問題 BUG-003，狀態為「待評估」。
      上次決策：優先完成 Phase D Gate 後才評估。
      現在要處理嗎？
```

結果：AI 主動確認優先級、記憶有管理機制、決策可追溯、偏離可偵測。

---

## 13. 快速指令參考

### 靜態治理工具

```bash
python governance_tools/contract_validator.py --file ai_response.txt
python governance_tools/plan_freshness.py --plan PLAN.md
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/external_repo_readiness.py --repo /path/to/repo
python governance_tools/reviewer_handoff_summary.py \
  --project-root . --plan PLAN.md --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/trust_signal_overview.py \
  --project-root . --plan PLAN.md --release-version v1.1.0 \
  --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/external_contract_policy_index.py \
  --repo /path/to/USB-Hub-Firmware-Architecture-Contract \
  --repo /path/to/Kernel-Driver-Contract \
  --repo /path/to/IC-Verification-Contract \
  --format human
```

### Runtime Hooks

```bash
python runtime_hooks/core/session_start.py \
  --project-root . --plan PLAN.md \
  --rules common,refactor --task-text "Refactor Avalonia boundary"
python runtime_hooks/core/pre_task_check.py \
  --rules common,python,cpp --risk high --oversight review-required
python runtime_hooks/core/post_task_check.py \
  --file ai_response.txt --risk medium \
  --oversight review-required --checks-file checks.json
python runtime_hooks/core/session_end.py \
  --project-root . --session-id 2026-03-12-01 \
  --runtime-contract-file contract.json \
  --checks-file checks.json --response-file ai_response.txt
```

### Smoke Test

```bash
python runtime_hooks/smoke_test.py --harness claude_code --event-type pre_task
python runtime_hooks/smoke_test.py --harness codex --event-type session_start
python runtime_hooks/smoke_test.py --event-type session_start
```

### CI / Hooks

```bash
bash scripts/run-runtime-governance.sh --mode enforce
bash scripts/run-runtime-governance.sh --mode ci
```

---

## 14. 延伸設計

- [docs/decision-boundary-layer.md](docs/decision-boundary-layer.md)
- [docs/decision-boundary-first-slice.md](docs/decision-boundary-first-slice.md)

---

*ai-governance-framework v1.1.0 · github.com/Gavin0099/ai-governance-framework*

## 延伸閱讀

- [Decision Boundary Layer](decision-boundary-layer.md)
- [Decision Boundary First Slice](decision-boundary-first-slice.md)
- [Machine-Interpretable Positioning](agent-native-positioning.md)
