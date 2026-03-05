# PLAN.md — AI Governance Framework

> **專案類型**: 開源治理工具框架
> **技術棧**: Markdown / Python / Bash
> **複雜度**: L2
> **預計工期**: 2026/03 ~ 2026/06
> **最後更新**: 2026/03/05
> **Owner**: GavinWu

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
├─ [🔄] Phase B: 可採用性基礎       (進行中，預計 2026/04/15)
├─ [⏳] Phase C: 工具強化           (待開始，預計 2026/05/15)
└─ [⏳] Phase D: 整合成熟           (待開始，預計 2026/06/30)
```

**當前 Phase**: **Phase B — 可採用性基礎**

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

### Phase B: 可採用性基礎 (進行中 🔄)

**目標**: 讓「別人 15 分鐘內能體感框架價值」

**任務清單**:
```
├─ [✓] B1. Governance Contract Validator  (2026/03/05 完成)
├─ [⏳] B2. PLAN.md Freshness 機制
├─ [⏳] B3. memory_janitor 改為 copy+pointer+manifest
└─ [⏳] B4. 範例 toy repo + demo log
```

**Gate 條件**:
- [x] Validator 能機器判定 AI 初始化是否合規
- [ ] PLAN.md 有 freshness 欄位且有工具提醒
- [ ] memory_janitor 歸檔後原檔保留 pointer
- [ ] Toy repo 可讓新用戶照做並體感「AI 開始問計畫」

---

### Phase C: 工具強化 (待開始 ⏳)

**目標**: 讓 governance_tools 達到可信賴的生產品質

**任務清單**:
```
├─ [⏳] C1. 工具輸出支援 --format json（接 CI/dashboard）
├─ [⏳] C2. memory_janitor 加入單元測試
├─ [⏳] C3. linear_integrator 加入錯誤處理、rate limit、敏感資訊防寫入
└─ [⏳] C4. Git hook 範例（PLAN.md 過期提醒）
```

**Gate 條件**:
- [ ] 所有工具有 --format json 輸出
- [ ] memory_janitor 測試覆蓋率 ≥ 70%
- [ ] linear_integrator 有明確的 source of truth 策略文件

---

### Phase D: 整合成熟 (待開始 ⏳)

**目標**: 定義同步策略，讓框架能在團隊環境落地

**任務清單**:
```
├─ [⏳] D1. Linear 同步策略文件（PLAN vs Linear 誰為準、衝突解法）
├─ [⏳] D2. CI/CD 整合範例（GitHub Actions）
└─ [⏳] D3. 第二個平台整合（Jira 或 Notion）
```

**Gate 條件**:
- [ ] Linear 整合有明確的「單一 Source of Truth」定義
- [ ] 有可運行的 CI 範例（GitHub Actions）

---

## 🔥 本週聚焦 (Sprint 1)

**Sprint 1** (2026/03/05 - 2026/03/16)

**目標**: 完成 B1 Governance Contract Validator

**任務清單**:
- [x] B1-a. 定義 AI 合規回覆的固定 header 格式 (4h) — SYSTEM_PROMPT.md §2 ⑦
- [x] B1-b. 撰寫 `governance_tools/contract_validator.py` (6h) — 支援 human/json 輸出、退出碼
- [x] B1-c. 更新 SYSTEM_PROMPT.md — 要求 AI 輸出固定 header (2h)
- [x] B1-d. 更新 README.md — 說明 validator 用法 (2h)

**下一步**:
1. B2 PLAN.md Freshness 機制
2. B3 memory_janitor copy+pointer 修正

**當前阻礙**: 無

**已決策**:
- ✅ Validator 使用正規表達式驗證（更彈性，支援 markdown code block 與純文字兩種格式）

---

## 📊 待辦清單 (Backlog)

### 高優先 (P0)
- [x] B1. Governance Contract Validator（AI 初始化合規性機器驗證）✓ 2026/03/05
- [ ] B2. PLAN.md Freshness（最後更新日 + owner + Git hook 提醒）
- [ ] B3. memory_janitor copy+pointer+manifest（修補 audit trail 缺口）

### 中優先 (P1)
- [ ] B4. Toy repo 範例專案 + terminal demo log
- [ ] C1. 工具輸出 --format json
- [ ] C2. memory_janitor 單元測試
- [ ] C3. linear_integrator 錯誤處理強化
- [ ] D1. Linear 同步策略文件

### 低優先 (P2)
- [ ] C4. Git hook 範例
- [ ] D2. GitHub Actions CI 範例
- [ ] D3. Jira / Notion 整合

---

## 🚫 不要做 (Anti-Goals)

❌ **Phase B 禁止**:
- 不要做 GUI 工具（先讓 CLI 可靠）
- 不要做 Jira 整合（Phase D 才做）
- 不要重構已穩定的 8 大法典核心文件（Phase B 不碰文件架構）
- 不要加 AI model fine-tuning（超出 Bounded Context）

---

## 🤖 AI 協作規則

**AI 在實作任何功能前，必須確認**:

1. ✅ 這項任務在「本週聚焦」或「下一步」中嗎?
2. ✅ 是否符合當前 Phase B 的範圍（可採用性基礎）?
3. ✅ 是否在「不要做」清單中?

**如果不符合上述條件**:
- 先詢問是否調整 PLAN
- 不要自行決定優先級
- 提供明確的選項 (A/B/C)

---

## 🎯 Gate 與驗收標準

### Phase B Gate

**功能完整性**:
- [ ] Validator 腳本可機器執行，輸出合規/不合規結論
- [ ] PLAN.md freshness 欄位存在且工具能偵測過期
- [ ] memory_janitor 歸檔後原檔有 pointer，有 manifest 紀錄

**工具品質**:
- [ ] 所有新工具有 --help 說明
- [ ] 所有新工具有 --dry-run 模式

**文件完整性**:
- [ ] README.md 同步更新新功能
- [ ] 每個新工具有對應的使用說明

---

## 📅 里程碑

| 里程碑 | 目標日期 | 狀態 | 交付物 |
|---|---|---|---|
| M1: 框架基礎完成 | 2026/03/05 | ✅ | 8 大法典 + 基礎工具 |
| M2: 可採用性基礎 | 2026/04/15 | 🔄 | Validator + Freshness + Toy repo |
| M3: 工具品質提升 | 2026/05/15 | ⏳ | JSON 輸出 + 測試 + 錯誤處理 |
| M4: 整合成熟 | 2026/06/30 | ⏳ | Linear 策略 + CI 範例 |

---

## 📝 已知問題

| ID | 問題 | 嚴重程度 | 狀態 | 負責人 |
|---|---|---|---|---|
| BUG-001 | memory_janitor --execute 為移動而非複製+pointer，audit trail 有洞 | P0 | ⏳ 待修 | GavinWu |
| BUG-002 | Linear 整合無 source of truth 定義，有雙主系統風險 | P1 | ⏳ 待修 | GavinWu |
| BUG-003 | 記憶壓力只靠行數，單一指標有被規避的風險 | P2 | ⏳ 待評估 | GavinWu |

---

## 🔧 技術債務追蹤

| ID | 債務描述 | 預計償還時間 | 優先級 |
|---|---|---|---|
| DEBT-001 | memory_janitor 無單元測試，regex 脆弱 | Phase C | P1 |
| DEBT-002 | linear_integrator 無 rate limit / 敏感資訊防護 | Phase C | P1 |
| DEBT-003 | 工具輸出為純文字，無法接 CI pipeline | Phase C | P1 |

---

## 🔄 變更歷史

| 日期 | 變更內容 | 原因 |
|---|---|---|
| 2026/03/05 | 建立 PLAN.md，啟動 Phase B | 框架分析後確立下一步 roadmap |
| 2026/03/05 | 完成 B1 Governance Contract Validator | B1-a/b/c/d 全部完成，validator 支援 human/json 輸出 |
