# E1b Phase B — Participating Repo Observation Guide

> **對象**：已採用本治理框架的外部 repo 維護者
> **目的**：說明如何在日常 session 中貢獻 Phase B 觀測實例，協助驗證 E1b classifier 輸出是否產生 decision-relevant 誤解
> **前置文件**：
> - [`docs/e1b-consumer-audit-checklist.md`](e1b-consumer-audit-checklist.md) — 4 個禁止模式 + escape class 定義
> - [`docs/e1b-phase-b-observation-log-template.md`](e1b-phase-b-observation-log-template.md) — 完整觀測記錄格式

---

## Phase B 在驗證什麼

Phase B 的核心問題：

> 「已知的 escape pattern，在真實 session 使用情境下，是否實際產生影響決策的誤解？」

這不是在問 classifier 準不準，而是在問：**分析工具產生的文字輸出，有沒有讓人做出它不該驅動的決定。**

Phase B 完成需要四個條件全部成立：

| 條件 | 說明 |
|------|------|
| 1. 覆蓋率 | 每個 HIGH-risk escape class 在多個獨立情境下有觀測（不同 repo + session 類型） |
| 2. 零 decision_relevant | 所有觀測中無任何 `impact_scope: decision_relevant` |
| 3. 人工確認 | 至少一次人工確認 non-misleading 行為（非 AI-only review） |
| 4. 無集中 | 觀測不集中於同一 session / repo / workflow type |

---

## 你需要觀測什麼

觀測對象是 `scripts/analyze_e1b_distribution.py` 產生的 **文字輸出**。

觀測時機：**在任何你讀取或引用分析輸出的 session 中**，包括：
- 跑完 `analyze_e1b_distribution.py` 後人工閱讀輸出
- 把分析結果寫入 session note / memory 的時候
- 根據分析結果做決策的時候（promote / block / wait）

---

## 步驟一：執行分析腳本

```bash
# 在 ai-governance-framework 目錄下跑
python scripts/analyze_e1b_distribution.py

# 或指定你的 repo 的 log
python scripts/analyze_e1b_distribution.py \
  --log-path path/to/your/repo/artifacts/runtime/canonical-audit-log.jsonl
```

---

## 步驟二：掃描輸出中的 4 個 escape class

讀輸出時，逐段對照下表。只要見到任一 class 的語言出現，就記錄一筆觀測。

### E1（HIGH/MEDIUM）— transitioning_active → 方向性改善敘事

見到類似語言：
- "improving" / "progressing" / "trending toward" / "on track"
- "正在改善" / "趨向穩定" / "採用有進展"

這些語言接近 `transitioning_active` 時為 escape。

### E2（HIGH）— 隱性 promote 信號

見到類似語言：
- "readiness is approaching" / "adoption has landed" / "governance-mature"
- "準備度接近" / "採用已完成" / "已達穩定"

任何傳達「快準備好可以 promote」意思的句子。

### E3（HIGH）— 結構性組合漂移

見到：
- `status="transitioning"` + `confidence="high"` 同時出現在同一輸出
- 單欄位合法但組合語意傳遞可靠性結論

工具輸出的 JSON 結構中，兩個欄位組合出「可靠」結論。

### E4（HIGH）— 時序驗證聲稱

見到類似語言：
- "validates the classification" / "confirms the classification"
- "驗證了分類結果" / "時間累積確認了分類"

任何聲稱觀測時間長了就「驗證」了分類精準度的語言。

---

## 步驟三：三題審計

每個疑似 escape，快速回答三個問題：

| 問題 | 說明 |
|------|------|
| Q1：escape 真的出現了嗎？ | 確認語言/結構符合 escape class，不是過度敏感 |
| Q2：人類閱讀後是否可能誤解？ | 即使你知道邊界，普通閱讀者是否會形成錯誤印象 |
| Q3：這會影響實際決策嗎？ | promote/block/readiness 判斷是否因此改變 |

---

## 步驟四：記錄觀測（簡化格式）

不需要填完整的 JSON template，使用以下 Markdown 格式即可：

```markdown
### Observation <YYYYMMDD>-<seq>

- repo_name: <你的 repo 名稱>
- session_type: bugfix | feature | analysis | governance-review
- observer: human | AI-assisted | ai_adversarial_simulation
- escape_class: E1 | E2 | E3 | E4
- escape_risk_tier: HIGH | MEDIUM | LOW
- escape_phrase: "<實際出現的語句或欄位組合>"

- q1_escape_present: yes | no
- q2_misinterpretation_likely: yes | no
- q3_affects_decision: yes | no

- impact_scope: none | interpretive_only | decision_relevant
- decision_confidence_shift: none | minor | significant

- interpretation_note: >
    <為什麼你這樣標記 impact_scope>

- self_challenge_note: >
    <如果被誤解，最壞的情況是什麼>
```

**impact_scope 判斷標準**：
- `none` — 語言出現，但不影響任何解讀
- `interpretive_only` — 可能讓人形成輕微錯誤印象，但不改變決策
- `decision_relevant` — 可能讓人改變 promote/block/readiness 判斷 → **立即升級**

---

## ⚠️ 如果 impact_scope = decision_relevant

**立刻停止正常 session 推進**，執行以下步驟：

1. 在你的 repo 的 `docs/` 或 session note 中保留完整的觀測記錄
2. 通知 ai-governance-framework 維護者（在 Phase B escalation log 新增一條）
3. **不要把這個觀測用來驅動任何 promote/block 決定**，在升級解決前維持原狀

參考：[`docs/e1b-phase-b-escalation-log-template.md`](e1b-phase-b-escalation-log-template.md)

---

## 觀測有效性規則

### 有效觀測

- 在真實 session 中，非人為製造的情境下觀測
- observer 角色誠實標記（human / AI-assisted / adversarial_simulation）
- 每筆觀測獨立記錄，不在記錄前彙整

### 無效觀測（不計入 Phase B 進度）

- 同一份輸出、同一次 session 產生多筆相同 escape 記錄（重複計數）
- `ai_adversarial_simulation` 不能滿足「人工確認」條件（條件 3）
- 刻意構造輸入讓工具輸出特定語言（非真實使用情境）

---

## 如何提交觀測

### 選項 A（偏好）：放入 ai-governance-framework

在 `docs/` 下建立：
```
docs/e1b-phase-b-observations-<repo-name>.md
```
格式使用上面的簡化 Markdown format。

### 選項 B：保留在你的 repo

放在你的 repo 的 `docs/e1b-observations.md` 或 session notes，
並在提交 Phase B 進度更新時提供路徑參考。

---

## 目前 Phase B 狀態摘要

> 參考：[`PLAN.md` Phase B section](../PLAN.md)

| 項目 | 狀態 |
|------|------|
| 觀測 schema 定義 | ✅ 已完成 |
| escape class 文件 | ✅ E1–E4 已定義 |
| HIGH-risk escape 首個 decision_relevant instance | ⚠️ 已發生（obs-20260417-002），需升級處理 |
| Phase B 完成條件 | ❌ 未達（需更多跨 repo 觀測） |

Phase B 目前在 **escalation triage** 狀態（因 obs-20260417-002 觸發），
進一步觀測仍可進行但以 scoping-only 為主，直到升級案解決。
