# AI Governance 變異驗證：權威優先序弱化

狀態：`PENDING`

## 目的

本文件把既有的權威優先序弱化案例整理成第一份文件用語規範樣板。
重點是讓人類敘事以中文為主，同時保留既有腳本、報告、場景、違規碼與
欄位名稱，確保工程追蹤不斷線。

這不是新的執行結果，也不是新的保護宣稱。它只是將既有
`precedence_bypass` 變異驗證紀錄套用到「中文敘事 + 英文識別字」格式。

## 對應識別字

- 變異場景：`precedence_bypass`
- 紅燈檢查腳本：`governance_tools/mutation_proof_runner_phase2.py`
- 變異報告：`artifacts/governance/mutation-proof-phase2-report-2026-06-06.json`
- 變異目錄：`docs/e1-mutation-catalog.md`
- 預期違規碼：`authority_precedence_active_blocks_release`
- 違規欄位：`release_block_reasons`
- 受保護邊界：`lifecycle_effective_by_escalation`
- 主要治理表面：`escalation_authority_writer`
- 次要訊號：`authority_state_active`
- 測試樣本識別字：`test-active-precedence-esc`

## 預期結果

套用權威優先序弱化變異後，對應檢查應該偵測到
`authority_precedence_active_blocks_release`。

若對應檢查沒有偵測到預期違規碼，表示變異逃過測試，紅燈檢查執行腳本
應以非零結束碼回報。

## 既有驗證紀錄

- 語法檢查：未執行，本文件未修改程式碼。
- 測試結果：未執行，本文件未重跑變異檢查。
- 紅燈檢查腳本結果：沿用既有報告，狀態為 `VULNERABLE`。
- 原始場景：`precedence_bypass`
- 原始狀態：`VULNERABLE`
- 原始旗標：`mutation_survived: true`
- 原始結束碼：`exit_code: 1`

既有報告的解讀是：`VULNERABLE` 表示目標變異仍被視為逃過測試，治理缺口
已被記錄。它不等於整個治理系統失效，也不等於此案例已取得
`PROTECTED` 宣稱。

## 部分冗餘說明

`docs/e1-mutation-catalog.md` 記錄：移除權威優先序迴圈檢查後，
`validate_prewrite_payload` 仍會留下 `authority_state_active` 這個次要訊號。

這代表此案例有部分冗餘，但不足以宣稱 `PROTECTED`。完整繞過仍需要兩個
變異同時成立：

1. 移除 `escalation_authority_writer.py` 中的權威優先序迴圈檢查。
2. 移除 `validate_prewrite_payload` 中產生 `authority_state_active` 的檢查。

因此，本文件只能說明既有報告中的權威優先序弱化案例與部分冗餘狀態，
不能把它升格成完整保護證明。

## 用語規範套用狀態

本文件已套用 `docs/governance/ai-governance-document-language-style-guide-2026-06-27.md`
的已採用格式：

- 人類敘事以中文為主。
- 既有腳本、報告、場景、違規碼、欄位名稱與原始旗標保留原文。
- 保留原文的識別字使用 backtick。
- `survived` 類語意以「變異逃過測試」描述。
- 「測試結果」與「紅燈檢查腳本結果」分開陳述。

## 宣稱上限

本文件只能宣稱：

- `precedence_bypass` 已被整理成第一份文件用語規範樣板。
- 既有 `2026-06-06` 報告記錄此案例為 `VULNERABLE`。
- 既有 catalog 記錄此案例有 `authority_state_active` 部分冗餘。

本文件不得宣稱：

- 權威優先序弱化案例已被完整保護。
- 任何新測試已執行。
- 任何 code、test、mutation ID 或 runtime 行為已修改。
- 整個治理模型正確。
- 其他變異案例已被覆蓋。
- 文件用語規範會自動套用到其他儲存庫。
