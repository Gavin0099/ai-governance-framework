# ZoneTruth 外部 Repo 治理分析

> 來源：https://github.com/Gavin0099/ZoneTruth
> 分析日期：2026-05-22
> 分析工具：ai-governance-framework（CodeBurn v1.1）
> 分析等級：Class C — 單次 session 觀察，非第三方驗證審計

---

## 1. Repo 基本識別

| 欄位 | 內容 |
|---|---|
| Repo | Gavin0099/ZoneTruth |
| 領域 | `ai-governance`（依 contract.yaml） |
| 主要語言 | Python 68.5% |
| 異常元件 | Swift 12.4% — 用途未確認 |
| 聲稱版本 | v1.2 |
| contract.yaml | 存在 |
| AGENTS.md | 存在 |

---

## 2. 治理就緒度檢查清單

| 表面 | 狀態 | 備註 |
|---|---|---|
| `contract.yaml` | 存在 | 結構最小但有效 |
| `rule_roots` 已定義 | 是 — `governance/rules` | 內容未驗證 |
| `validators` 已定義 | 封鎖 — 空值 | 無領域驗證器登記 |
| `AGENTS.md` | 存在 | 雙層層級（工作區 / Repo） |
| 證據等級標注 | 缺失 | v1.2 指標未標注等級 |
| 禁用詞彙審查 | 通過 | README 未發現 FCP 違規 |
| Checklist 文件 | 存在於 docs/ | 未與 contract validators 掛鉤 |

---

## 3. README 聲明分析（v1.2）

### 3a. 有界聲明 — 正確陳述

README 明確列出框架**不**聲稱的內容：

- 工程品質提升證明 — 未聲稱
- 推理能力提升證明 — 未聲稱
- 確定性認知控制 — 未聲稱
- 機器權威合規判定 — 未聲稱
- 通用語意正確性驗證 — 未聲稱
- 對模糊推理的自動真相判斷 — 未聲稱
- 無審查者監督的長期語意漂移 — 未聲稱

ADVISORY：此 NOT-claims 清單是 README 中最強的治理信號。其存在降低了語言層面的權威膨脹風險。

### 3b. 指標（v1.2 測試結果）

| 指標 | 數值 | 等級 | 備註 |
|---|---|---|---|
| `scope_violation_count`（範圍違規次數） | 0 | 未標注 | 單一評估者，n=5 |
| `evidence_traceability`（證據可追溯性） | 5/5 | 未標注 | 內部評分 |
| `claim_overreach_count`（主張逾越次數） | 0 | 未標注 | 單一評估者 |
| `semantic_consistency`（語意一致性） | 4/5 | 未標注 | 內部評分 |
| `tokens_per_actionable_fix`（每次修復 token 數） | 約 8,630 | 標注「代理指標」 | 正確有界 |
| `actionable_fix_latency_sec`（每次修復延遲秒數） | 405 | 未標注 | 未說明不確定性 |

ADVISORY：這些指標由單一評估者對 n=5 同質測試案例進行內部測量。應視為觀察性指標，而非經驗證的治理基準。證據等級：Class C（單次 session 觀察，單方記錄）。

### 3c. 方法論限制 — 已正確揭露

README 明確說明：

- 單一評估者（無評分者間可靠性）
- 同質測試集（n=5，單一套件重點）
- 文件修正為主；程式碼場景待量化
- A/B 組指標不對稱（B 組較完整）

ADVISORY：這些揭露已正確有界。「無法聲稱在所有程式碼庫 / 任務類型上的通用有效性」是正確框架。此降低了語意預授權風險。

---

## 4. contract.yaml 缺口分析

目前狀態：

```yaml
name: ai-governance-framework-contract
plugin_version: "1.0.0"
domain: ai-governance
rule_roots:
  - governance/rules
validators:
  # 空值
```

BLOCKED surface：validators 欄位為空。治理框架可透過 contract.yaml 發現此 repo，但無法執行任何領域專屬驗證。目前模式：僅顧問性（無執行強制）。

若要從顧問模式升級為執行模式，至少需在 `validators` 欄位登記一個可呼叫的驗證器，指向 `governance/rules` 中的實作。

---

## 5. AGENTS.md 層級評估

觀察到雙層架構：

- 第一層 — 工作區層級：個人隱私、外部通訊閘道、記憶體存取限制
- 第二層 — Repo 層級：「在 repo 工作時，repo 治理優先於工作區指示」

此層級設計正確。Repo 層級治理在 repo 任務中優先於工作區指示，是正確的優先順序規則。

ADVISORY：AGENTS.md 中提及的「代理無關收尾規則（agent-agnostic closeout rule）含收據文件與記憶體資格評估」，呼應主治理框架的 session_end 模式。這是框架相容性的正向信號。

---

## 6. Swift 元件（12.4%）— 未解決

ADVISORY：Swift 佔程式碼庫 12.4% 對於治理框架而言屬異常。常見解釋：

- macOS/iOS 展示工具（治理報告的圖形介面）
- 平台特定掛鉤或通知器
- 前期專案遺留程式碼

此表面不在已確認的治理 rule_roots 範圍內。在 Swift 元件的用途被確認，且明確納入或排除於治理範圍之前，此為未驗證邊界。

---

## 7. 證據等級上限

根據現有證據，ZoneTruth v1.2 結果最大允許主張如下：

| 主張類型 | 允許狀態 | 限制條件 |
|---|---|---|
| 「在 5 個文件任務中展現邊界紀律」 | 允許 | 在聲明範圍內 |
| 「零範圍違規」 | 允許（需附 n=5 限定） | 必須帶樣本數 |
| 「通用有效治理」 | FORBIDDEN | 無跨程式碼庫證據 |
| 「經驗證的審計追蹤」 | FORBIDDEN | validators 空、單一評估者 |
| 「生產就緒的執行強制」 | FORBIDDEN | validators 空 |

FROZEN INVARIANT：證據等級上限由最弱環節決定——單一評估者 + n=5 + validators 空 = Class C 觀察性，非執行強制等級。

---

## 8. 導入就緒度

| 閘道 | 狀態 |
|---|---|
| contract.yaml 存在 | 通過 |
| domain 已定義 | 通過 |
| rule_roots 已定義 | 通過 — 內容未驗證 |
| validators 已登記 | 失敗 — 空值 |
| 證據等級已標注 | 失敗 — 缺失 |
| Swift 元件已界定範圍 | 失敗 — 未確認 |

**判定**：部分就緒。導入在結構上可行（contract.yaml 可被發現），但在未登記 validators 的情況下，執行閘道無法啟動。

**執行強制導入前的最低行動項目**：

1. 在 contract.yaml 中登記至少一個 validator
2. 為 v1.2 指標標注證據等級（建議 Class C）
3. 確認 Swift 元件範圍（納入範圍或明確排除）

---

## 9. 總結

ZoneTruth 在語言層面展現良好的語意姿態（NOT-claims 清單、誠實揭露、代理指標標注）。結構性缺口在於執行基礎設施：validators 為空且指標未標注等級。此 repo 可被治理框架發現，但未受執行強制保護。

本分析為 Class C — 對公開 repo 內容的單次 session 單一分析師觀察。不得作為經驗證的審計或認證使用。
