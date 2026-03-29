# PLAN.md — AI Governance Framework

> **專案類型**: 開源治理工具框架
> **技術棧**: Markdown / Python / Bash
> **複雜度**: L2
> **預計工期**: 2026/03 ~ 2026/06
> **最後更新**: 2026-03-29
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)

---

## 📋 專案目標

讓 AI 協作從「看到一句話就開工」變成「先讀規範、看計畫、確認邊界、必要時停機」，並使框架本身達到「別人也能複製採用」的成熟度。

**Bounded Context**:
- 治理文件的設計與維護（8 大法典）
- 配套工具的開發與強化（governance_tools/）
- 採用路徑的建立（文件、範例、驗證工具）

**不負責**:
- 特定 AI 模型的 fine-tuning
- 企業級 RBAC / 存取控制
- 非 AI 協作的專案管理工具

---

## 🏗️ 當前階段

```
階段進度:
├─ [✓] Phase A: 框架基礎建立       (2026/03/05 完成)
├─ [✓] Phase B: 可採用性基礎        (2026/03/05 完成)
├─ [✓] Phase C: 工具強化            (2026/03/05 完成)
└─ [✓] Phase D: 整合成熟            (2026/03/06 完成)
```

**當前 Phase**: **維護期 / Alpha adoption hardening**

---

## 📦 Phase 詳細規劃

### Phase A: 框架基礎建立 (已完成 ✓)

**目標**: 建立完整的 8 大法典與配套基礎設施

**任務清單**:
```
├─ [✓] 8 大法典文件撰寫完成
├─ [✓] governance_tools/ 初版 (memory_janitor + linear_integrator)
├─ [✓] deploy_to_memory.sh 修正（來源路徑、PLAN.md 模板自動生成）
├─ [✓] docs/ 補齊缺失文件 (architecture-theory, governance-vs-prompting)
├─ [✓] PLAN.md 整合進 SYSTEM_PROMPT.md §2 初始化流程
└─ [✓] 04_review_log.md 機制建立
```

**Gate 條件**: ✅ 全部通過

---

### Phase B: 可採用性基礎 (已完成 ✓)

**目標**: 讓「別人 15 分鐘內能體感框架價值」

**任務清單**:
```
├─ [✓] B1. Governance Contract Validator  (2026/03/05 完成)
├─ [✓] B2. PLAN.md Freshness 機制  (2026/03/05 完成)
├─ [✓] B3. memory_janitor 改為 copy+pointer+manifest  (2026/03/05 完成)
└─ [✓] B4. 範例 toy repo + demo log  (2026/03/05 完成)
```

**Gate 條件**:
- [x] Validator 能機器判定 AI 初始化是否合規
- [x] PLAN.md 有 freshness 欄位且有工具提醒
- [x] memory_janitor 歸檔後原檔保留 pointer
- [x] Toy repo 可讓新用戶照做並體感「AI 開始問計畫」

---

### Phase C: 工具強化 (已完成 ✓)

**目標**: 讓 governance_tools 達到可信賴的生產品質

**任務清單**:
```
├─ [✓] C1. 工具輸出支援 --format json（接 CI/dashboard）  (2026/03/05 完成)
├─ [✓] C2. memory_janitor 加入單元測試  (2026/03/05 完成)
├─ [✓] C3. linear_integrator 加入錯誤處理、rate limit、敏感資訊防寫入  (2026/03/05 完成)
└─ [✓] C4. Git hook 一鍵安裝（PLAN.md 過期擋 commit）  (2026/03/05 完成)
```

**Gate 條件**:
- [x] 所有工具有 --format json 輸出
- [x] memory_janitor 測試覆蓋率 ≥ 70%（47 tests, 71%）
- [x] linear_integrator 有明確的 source of truth 策略文件

---

### Phase D: 整合成熟 (已完成 ✓)

**目標**: 定義同步策略，讓框架能在團隊環境落地

**任務清單**:
```
├─ [✓] D1. Linear 同步策略文件（PLAN vs Linear 誰為準、衝突解法）  (2026/03/05 完成)
├─ [✓] D2. GitHub Actions + GitLab CI 實際 YAML 設定檔  (2026/03/06 完成)
└─ [✓] D3. 第二個平台整合（Notion integrator + 策略文件）  (2026/03/06 完成)
```

**Gate 條件**:
- [x] Linear 整合有明確的「單一 Source of Truth」定義
- [x] 有可運行的 CI 範例（GitHub Actions + GitLab CI）
- [x] 第二平台（Notion）有完整整合工具與策略文件

---

## 🔥 當前聚焦 — 維護期 / Alpha adoption hardening

**所有 Phase（A/B/C/D）已完成**。目前重點是把框架從「功能已具備」推進到「外部讀者更容易採用與評估」。

**本輪已完成**:
- [x] direct CLI entrypoint import-path 修復（`change_control_summary.py` 等）✓ 2026/03/15
- [x] `requirements.txt` 建立並對齊 GitHub Actions 依賴安裝 ✓ 2026/03/15
- [x] `start_session.md` 最小 quickstart 文件 ✓ 2026/03/15
- [x] `quickstart_smoke.py` onboarding smoke，並接入 `verify_phase_gates.sh` ✓ 2026/03/15
- [x] `example_readiness.py` 範例集健康度檢查 ✓ 2026/03/15
- [x] GitHub Actions 新增 strict runnable-example validation ✓ 2026/03/15
- [x] workflow entry layer 第一版規格與 tranche-1 Claude workflow skills（`tech-spec` / `precommit` / `codex-review-fast` / `create-pr`）✓ 2026/03/25

**待處理（技術債與品質提升）**:
- [x] 補齊工具單元測試（state_generator）✓ 2026/03/21 — 78% 覆蓋率
- [x] 補齊工具單元測試（linear_integrator、notion_integrator）✓ 2026/03/21
- [x] 評估 BUG-003（記憶壓力多維度指標）✓ 2026/03/21 — 決定修：已加字元數閾值（soft 8000 / hard 10000 / critical 12000），防止單行塞大量內容繞過行數限制，結案
- [x] 補齊對外 release-facing 信號 ✓ 2026/03/21 — CHANGELOG post-alpha entry 補齊；framework 自身已完成 --adopt-existing 並通過 drift check 12/12
- [x] Cross-repo governance baseline distribution system ✓ 2026/03/21 — init / adopt-existing / upgrade / refresh-baseline 四個 lifecycle；governance_drift_checker 12 checks；plan_required_sections vs plan_section_inventory 語義分離；governance:key 錨點
- [ ] 持續收斂 example / onboarding path，降低首次採用摩擦
- [ ] 持續補強 practical interception coverage（git hook、CI gate、external onboarding），降低 direct commit 或非標準工作流繞過檢查的機率
- [ ] 持續補強 workflow embedding（contract discovery、runtime smoke、reviewer handoff、change-control flow），讓治理更自然嵌入日常開發流程

**Alpha → Beta 升級 Gate（明確驗收標準）**:
- [x] 至少一個外部專案完整跑完 session_start → pre_task → post_task 全程（不需要作者介入）✓ 2026/03/28 — Hearth (household-finance)，三個 harness 全通過
- [ ] 獨立 reviewer 能在無引導情況下完成 onboarding 並提交第一個 governance-compliant session
- [x] state_generator / linear_integrator / notion_integrator 單元測試補齊（覆蓋率 ≥ 70%）✓ 2026/03/21 — state 78% / linear 96% / notion 72%
- [x] BUG-003 評估完畢，決定修或列為已知限制 ✓ 2026/03/21

**邊界說明**:
- 這裡的補強方向是 **commit/merge-time governance**
- 不包含 IDE 內部攔截或 code generation 階段的全面控制

---

## 🔥 下一輪聚焦 — Beta 收斂

**目標**: 確保 Beta Gate 剩餘條件（獨立 reviewer 無引導完成 onboarding）、持續補強 CI gate 覆蓋率與 onboarding 摩擦。

---

## ⛔ 暫停授權項目 — Entry Layer（E1–E5）

**狀態: 已從 sprint 移出。在 justification 完成前，不授權任何 runtime 擴張。**

> E1–E5 moved out of sprint, 2026-03-30
> status: needs justification
> no runtime expansion authorized from these items yet

**E2 撤回記錄**:
- `workflow_entry_observer` 曾短暫接入 `session_start`（2026-03-30），隨即撤回
- 撤回理由：已導入新 import、新觀測來源、新 dict key，跨過 runtime boundary，但未被證成存在必要性
- 這不是「可有可無的小整理」，而是撤回一個未被證成的 runtime 擴張

**各項當前定性**:

| 項目 | 定性 |
|------|------|
| E1: schema alignment | 目前碰巧相容，但未被設計過，不能 build on top |
| E2: observer → session_start | 已撤回；需先定義消費者是誰、在哪裡用 |
| E3: enforcement feedback | 既存 surface，但角色未定義；不得納入規劃直到角色明確 |
| E4: repo_type | 高風險 matrix explosion；需先確認是否只是 contract abstraction 沒做乾淨 |
| E5: memory refactor | 連 problem statement 都沒有，不得以 sprint item 身分存在 |

**解封條件**: 完成 `docs/entry-layer-boundary.md` + `docs/entry-layer-justification.md`，且 justification 能回答：
- 如果 entry layer 永遠不存在，framework 會失去什麼不可接受的能力？
- 為什麼這個缺口不能在 pre_task_check 解？

**當前阻礙**: 無

**已決策**:
- ✅ Validator 使用正規表達式驗證（更彈性，支援 markdown code block 與純文字兩種格式）
- ✅ state_generator.py 使用 YAML 輸出（pyyaml 非必要，自製序列化避免依賴）
- ✅ PLAN.md 為 Single Source of Truth，Linear / Notion 為從屬同步目標
- ✅ plan_required_sections（治理強制）與 plan_section_inventory（觀察快照）分開，--adopt-existing 不強加 mandate
- ✅ governance:key anchor pattern 確立：section 識別靠 key，不靠 heading 文字，支援多語言 repo
- ✅ lifecycle 四段定義：init / adopt-existing / upgrade / refresh-baseline，各有明確觸發條件

---

## 📊 待辦清單 (Backlog)

### 高優先 (P0)
- [x] B1. Governance Contract Validator（AI 初始化合規性機器驗證）✓ 2026/03/05
- [x] B2. PLAN.md Freshness（最後更新日 + owner + Git hook 提醒）✓ 2026/03/05
- [x] B3. memory_janitor copy+pointer+manifest（修補 audit trail 缺口）✓ 2026/03/05

### 中優先 (P1)
- [x] B4. Toy repo 範例專案 + terminal demo log ✓ 2026/03/05
- [x] C1. 工具輸出 --format json ✓ 2026/03/05
- [x] C2. memory_janitor 單元測試 ✓ 2026/03/05
- [x] C3. linear_integrator 錯誤處理強化 ✓ 2026/03/05
- [x] D1. Linear 同步策略文件 ✓ 2026/03/05
- [x] workflow entry-layer spec + tranche-1 workflow skills（`tech-spec` / `precommit` / `codex-review-fast` / `create-pr`）✓ 2026/03/25
- [~] E1–E5. Entry Layer 相關項目 — 暫停授權，pending justification（2026-03-30）

### 低優先 (P2)
- [x] C4. Git hook 一鍵安裝 ✓ 2026/03/05
- [x] D2. GitHub Actions + GitLab CI 範例（實際 YAML 設定檔）✓ 2026/03/06
- [x] D3. Notion 整合（notion_integrator.py + 策略文件）✓ 2026/03/06

---

## 🚫 不要做 (Anti-Goals)

❌ **框架邊界（持續有效）**:
- 不要做 GUI 工具（CLI 優先）
- 不要重構已穩定的 8 大法典核心文件
- 不要加 AI model fine-tuning（超出 Bounded Context）
- 不要做 Notion/Linear → PLAN.md 自動反寫（雙向同步競爭）

---

## 🤖 AI 協作規則

**AI 在實作任何功能前，必須確認**:

1. ✅ 這項任務在「本週聚焦」或「下一步」中嗎?
2. ✅ 是否在「維護期待辦清單」或 Backlog 中?
3. ✅ 是否在「不要做」清單中?

**如果不符合上述條件**:
- 先詢問是否調整 PLAN
- 不要自行決定優先級
- 提供明確的選項 (A/B/C)

---

## 🎯 Gate 與驗收標準

### Phase B Gate

**功能完整性**:
- [x] Validator 腳本可機器執行，輸出合規/不合規結論
- [x] PLAN.md freshness 欄位存在且工具能偵測過期
- [x] memory_janitor 歸檔後原檔有 pointer，有 manifest 紀錄

**工具品質**:
- [x] 所有新工具有 --help 說明
- [x] 所有新工具有 --dry-run 模式

**文件完整性**:
- [x] README.md 同步更新新功能
- [x] 每個新工具有對應的使用說明

---

## 📅 里程碑

| 里程碑 | 目標日期 | 狀態 | 交付物 |
|---|---|---|---|
| M1: 框架基礎完成 | 2026/03/05 | ✅ | 8 大法典 + 基礎工具 |
| M2: 可採用性基礎 | 2026/03/05 | ✅ | Validator + Freshness + Toy repo |
| M3: 工具品質提升 | 2026/03/05 | ✅ | JSON 輸出 + 測試 + 錯誤處理 |
| M4: 整合成熟 | 2026/03/06 | ✅ | Linear 策略 + CI 範例 + Notion 整合 |

---

## 📝 已知問題

| ID | 問題 | 嚴重程度 | 狀態 | 負責人 |
|---|---|---|---|---|
| BUG-001 | memory_janitor --execute 為移動而非複製+pointer，audit trail 有洞 | P0 | ✅ 已修 (B3) | GavinWu |
| BUG-002 | Linear 整合無 source of truth 定義，有雙主系統風險 | P1 | ✅ 已修 (C3, docs/linear-source-of-truth.md) | GavinWu |
| BUG-003 | 記憶壓力只靠行數，單一指標有被規避的風險 | P2 | ⏳ 待評估 | GavinWu |

---

## 🔧 技術債務追蹤

| ID | 債務描述 | 預計償還時間 | 優先級 |
|---|---|---|---|
| DEBT-001 | memory_janitor 無單元測試，regex 脆弱 | ✅ C2 完成 (71% coverage) | P1 |
| DEBT-002 | linear_integrator 無 rate limit / 敏感資訊防護 | ✅ C3 完成 (retry + scan_sensitive) | P1 |
| DEBT-003 | 工具輸出為純文字，無法接 CI pipeline | ✅ C1 完成 (all tools --format json) | P1 |

---

## 🔄 變更歷史

| 日期 | 變更內容 | 原因 |
|---|---|---|
| 2026/03/05 | 建立 PLAN.md，啟動 Phase B | 框架分析後確立下一步 roadmap |
| 2026/03/05 | 完成 B1 Governance Contract Validator | B1-a/b/c/d 全部完成，validator 支援 human/json 輸出 |
| 2026/03/05 | 完成 C4 Git hooks 一鍵安裝 | pre-commit CRITICAL 擋 commit，pre-push 軟性警告 |
| 2026/03/05 | 完成 C2 memory_janitor 單元測試 | 47 tests，71% coverage，超過 70% gate |
| 2026/03/05 | 完成 C1 --format json 標準化 | memory_janitor --plan 補齊；所有工具 JSON 輸出一致 |
| 2026/03/05 | 完成 C3 linear_integrator 強化 | retry/timeout/URLError/敏感掃描/JSON 輸出；source of truth 文件 |
| 2026/03/05 | Phase C Gate 全部通過 | C1+C2+C3+C4 完成，進入 Phase D |
| 2026/03/06 | 完成 D2 GitHub Actions + GitLab CI | 實際 YAML 設定檔；governance.yml + .gitlab-ci.yml |
| 2026/03/06 | 完成 D3 Notion 整合 | notion_integrator.py + docs/notion-source-of-truth.md；Phase D Gate 全部通過 |
| 2026/03/15 | Alpha adoption hardening | requirements / quickstart / example readiness / CI strict example validation / release-facing docs |
| 2026/03/25 | 定義 workflow entry-layer contract spec | 以 `tech-spec` → `precommit` → `create-pr` 的最小閉環，釘住 artifact、edge、recognition 與 consequence classes，避免 workflow skill 漂成獨立第二系統 |
| 2026/03/25 | 完成 tranche-1 Claude workflow skills | 新增 `tech-spec`、`precommit`、`codex-review-fast`、`create-pr` 四個 workflow skills，並更新 `.claude/README.md` 索引 |
| 2026/03/25 | 接上 quality-only control loop，並拆出 workflow observation lane | shared runtime enforcement 會累積 7-day quality trend 並透過既有 risk signal substrate 影響下一次 `session_start`；同時新增 observation-only workflow artifact recognition，避免把 workflow completeness 混入 quality/risk 語意 |
| 2026/03/25 | 收斂 observation lane 命名與 consumer guardrail | 將 `workflow_score` 改為 `observation_coverage`，並新增 machine-readable interpretation contract，禁止把 `missing` / `unverifiable` 直接翻譯成 compliance、bypass、block 或 task-level policy |
| 2026/03/25 | 補上防組合濫讀與 diagnostic-only 邊界 | 明確禁止 observation-only 單點或組合推論導出 compliance / intent / policy violation 類結論，並將 `failure_source_class` 限定為 diagnostic aid，避免滑成第二套裁決 taxonomy |
