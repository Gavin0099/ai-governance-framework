# AI Governance 變異契約：authority precedence 未接線盲點

狀態：`VULNERABLE`（claim-ceiling 已澄清；enforcement 未接）
日期：2026-07-04
範圍：report-only baseline + 宣稱澄清；不改 enforcement、不接 precedence

## 目的

本文件把 authority-document precedence 未接 runtime enforcement 的盲點固定成
可回歸的 `VULNERABLE` baseline，並記錄本切片唯一的動作：**宣稱澄清**。

GOVERNANCE_ENTRY 宣告 7 級 precedence 與 hard rule「lower-precedence signals
must never override higher-precedence authority」。但唯一排序 authority 的函式
`authority_loader.resolve_conflict`（canonical>reference>derived）**runtime 零
caller**，`can_override` / `overridden_by` frontmatter 欄位無任何 runtime 決策
消費者。runtime（`session_start`）只做載入過濾（audience/default_load）與
human-only 排除，**不做 precedence 衝突裁決**。

本切片不接 enforcement。它只在 GOVERNANCE_ENTRY 加 claim-ceiling 註記，並把此
gap 登記為 baseline，避免把宣告的憲法規則誤讀成 runtime 機器強制保證。決策脈絡
見 OP-HC memo（Option 0）。

## 對應識別字

- 契約 ID：`self_governance_authority_precedence`
- 主要治理表面：`governance_tools/authority_loader.py`、`runtime_hooks/core/session_start.py`
- 測試檔：`tests/test_self_governance_authority_precedence_mutation_contract.py`
- 目錄登記：`docs/e1-mutation-catalog.md`
- 變異類型：`Negative Fixture`
- 目前狀態：`VULNERABLE`

## Scenario S1：`Unenforced Authority Precedence`（VULNERABLE baseline）

對抗性輸入 / 情境：

- 兩份載入的 governance 文件在語義上衝突，或存在宣告的 `overridden_by` 覆蓋方向。

目前觀察：

- `resolve_conflict` 存在且單元測試可通過，但 runtime 無 caller。
- `session_start` 不呼叫任何 precedence 裁決；載入集合由 audience/default_load
  決定，順序為檔名字母序，不反映 authority 高低。
- `can_override` / `overridden_by` 被解析與 `authority_metadata_consistency`
  鏡射，但無 runtime 行為效果。

期望 baseline：

- focused test 應固定 `resolve_conflict` 無 runtime caller、且宣告的覆蓋方向不被
  runtime 強制。
- 若未來接上 precedence enforcement（OP-HC Option 1/2），此測試應失敗，要求更新
  本契約與 catalog 狀態，並附其自己的 enforcement mutation contract。

## 範圍

本切片只允許：

- 在 GOVERNANCE_ENTRY 加 claim-ceiling 註記（precedence 為 advisory，非 runtime
  保證）。
- 在 `docs/e1-mutation-catalog.md` 登記 report-only `VULNERABLE` baseline。
- 新增 focused test，固定目前未接線行為。

## 非目標

本切片不做：

- 不接 `resolve_conflict` 進任何 runtime 路徑。
- 不讓 `can_override` / `overridden_by` 產生 runtime 行為。
- 不新增 blocking 或 advisory 的 precedence 裁決。
- 不改 hook、pre-push、CI、schema 或 gate policy。
- 不定義「authority conflict」的操作型模型；那是 Option 1/2 的前置阻塞。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_authority_precedence_mutation_contract.py -q`
- `git diff --check`

測試通過的含義：

- precedence 未接 runtime enforcement 已被 report-only test 固定。
- GOVERNANCE_ENTRY 的 claim-ceiling 註記與實際 runtime 行為一致。

測試通過不代表：

- precedence 已被強制。
- `resolve_conflict` / `overridden_by` 已有 runtime 效果。
- 任何 enforcement、gate、hook 行為已改變。

## 宣稱上限

本文件只能宣稱：

- authority precedence 未接線盲點已被文件化並在宣稱面澄清。
- 目前未接線行為已登記為 report-only `VULNERABLE` baseline。
- focused test 可回歸目前行為。

本文件不得宣稱：

- authority precedence 已受 runtime 強制或 `PROTECTED` 保護。
- override 方向已被 runtime 驗證。
- OP-HC Option 1/2 已被採納或實作。
