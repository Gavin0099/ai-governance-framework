# 02_workflow.md — AI 協作工作流程

> **適用範圍**: 使用 AI Governance Framework 的所有協作會話
> **最後更新**: 2026-11-28

---

## 整體工作流程

```
1. AI Session 啟動
   └─ 讀取 SYSTEM_PROMPT.md（8 大法典）
   └─ 讀取 PLAN.md（計畫與邊界）
   └─ 輸出 [Governance Contract] 宣告

2. 任務執行
   └─ 確認任務在 PLAN.md 範圍內
   └─ 執行前確認：「符合計畫、不逾越邊界、必要時停機」

3. 任務同步（可選）
   └─ linear_integrator --sync  → 同步到 Linear
   └─ notion_integrator --sync  → 同步到 Notion

4. 記憶管理
   └─ memory_janitor --check    → 確認壓力狀態（僅量測）
   └─ memory_janitor --execute  → 已 fail-closed（UnsafeCleanupBlocked），不可用於歸檔
   └─ CRITICAL / EMERGENCY：python -m governance_tools.active_task_cutover
      prepare → Agent 撰寫 replacement candidate → verify → Owner 授權後 cutover
      prepare / verify 不修改 active memory；cutover 需 --authorization 與
      --authorized-candidate-sha256 綁定 Owner 核准的候選檔 SHA-256；必要時 rollback

5. PLAN.md 維護
   └─ 完成任務後更新「最後更新」日期
   └─ plan_freshness.py 自動在 CI 與 Git hook 中檢查
```

---

## 平台整合策略

### PLAN.md 為 Single Source of Truth

所有任務以 PLAN.md 為準。外部平台（Linear、Notion）為唯讀鏡像，不反向寫回。

詳見：
- [docs/linear-source-of-truth.md](../docs/linear-source-of-truth.md)
- [docs/notion-source-of-truth.md](../docs/notion-source-of-truth.md)

### CI 自動化

每次 push / PR 自動執行：
- `plan_freshness.py` — PLAN.md 新鮮度（CRITICAL 擋 push）
- `memory_janitor --check` — 記憶壓力（advisory；EMERGENCY 使該 job 失敗，CRITICAL 警告）

詳見：`.github/workflows/governance.yml` / `.gitlab-ci.yml`

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [SYSTEM_PROMPT.md](../governance/SYSTEM_PROMPT.md) | AI 核心意識，8 大法典 |
| [AGENT.md](../governance/AGENT.md) | Agent 身份定義 |
| [ARCHITECTURE.md](../governance/ARCHITECTURE.md) | 架構設計原則 |
| [HUMAN-OVERSIGHT.md](../governance/HUMAN-OVERSIGHT.md) | 人類監督機制 |
| [PLAN.md](../PLAN.md) | 當前計畫（專案根目錄） |
| [governance_tools/README.md](../governance_tools/README.md) | 工具使用說明 |
