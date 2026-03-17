# PLAN.md — AI Governance Framework

> **專案類型**: 開源治理工具框架
> **技術棧**: Markdown / Python / Bash
> **複雜度**: L2
> **預計工期**: 2026/03 ~ 2026/06
> **最後更新**: 2026-03-15
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

**待處理（技術債與品質提升）**:
- [ ] 補齊工具單元測試（state_generator、linear_integrator、notion_integrator）
- [ ] 評估 BUG-003（記憶壓力多維度指標）
- [ ] 補齊對外 release-facing 信號（GitHub Releases 實體頁面、alpha release note 對外同步）
- [ ] 持續收斂 example / onboarding path，降低首次採用摩擦
- [ ] 持續補強 practical interception coverage（git hook、CI gate、external onboarding），降低 direct commit 或非標準工作流繞過檢查的機率
- [ ] 持續補強 workflow embedding（contract discovery、runtime smoke、reviewer handoff、change-control flow），讓治理更自然嵌入日常開發流程

**Alpha → Beta 升級 Gate（明確驗收標準）**:
- [ ] 至少一個外部專案完整跑完 session_start → pre_task → post_task → session_end → memory promotion 全程（不需要作者介入）
- [ ] 獨立 reviewer 能在無引導情況下完成 onboarding 並提交第一個 governance-compliant session
- [ ] state_generator / linear_integrator / notion_integrator 單元測試補齊（覆蓋率 ≥ 70%）
- [ ] BUG-003 評估完畢，決定修或列為已知限制

**邊界說明**:
- 這裡的補強方向是 **commit/merge-time governance**
- 不包含 IDE 內部攔截或 code generation 階段的全面控制

**當前阻礙**: 無

**已決策**:
- ✅ Validator 使用正規表達式驗證（更彈性，支援 markdown code block 與純文字兩種格式）
- ✅ state_generator.py 使用 YAML 輸出（pyyaml 非必要，自製序列化避免依賴）
- ✅ PLAN.md 為 Single Source of Truth，Linear / Notion 為從屬同步目標

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
