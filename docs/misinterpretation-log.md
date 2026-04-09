# Misinterpretation Log

> 目的：收集 reviewer 與 adopter 在真實使用中出現的誤讀、誤用與解讀偏差，作為模型是否應擴張的主要證據來源。
>
> **這不是 bug tracker。**  
> 它記錄的是：系統輸出本身也許沒有錯，但人如何把它讀錯、用錯。
>
> **entry 記 observation，不記 conclusion。**  
> entry 應描述：
> - 看到了什麼
> - 該欄位真正的語義是什麼
>
> 至於 severity、grouping、是否值得擴模型，應該在 review 時再推導。  
> 如果 entry 一開始就把 expansion argument 一起寫進去，那是把 conclusion 偽裝成 evidence。
>
> **Interpretive language test：**  
> 在提交 entry 前先問自己：這句話是否還保留其他解讀空間？  
> 如果完全沒有，通常已經不是 observation，而是 verdict。
>
> **Expansion trigger：**  
> 這份 log 是新增模型維度的主證據來源。不要只靠理論就擴模型。
>
> **Observation period：**  
> 從 commit `608be20`（2026-04-05）開始。  
> 10 次 reviewer interaction 或 30 天後關窗，屆時統一 review。

---

## 如何新增一筆 Entry

```text
### YYYY-MM-DD - <short description>

**Affected field:** repo_readiness_level | closeout_activation_state | activation_recency | reviewer mapping
**Misinterpretation type:** over-reading | under-reading | category confusion | decision leak
**Severity:** low | medium | high
**What was observed:** <reviewer/adopter 實際做了什麼、說了什麼>
**What the field actually means:** <這個欄位真正語義是什麼>
**Correction applied:** <doc update, code change, or no action>
**Resolution status:** doc_updated | training | ignored | requires_model_change | open
**Owner:** reviewer | team | framework
**Signal for model expansion:** yes | no | watch
```

---

## Entry Types

| Type | Description |
|------|-------------|
| `over-reading` | 把較弱 signal 誤讀成更強保證 |
| `under-reading` | 因為「不能拿來做決策」就直接忽略這個欄位 |
| `category confusion` | 把 structural level、activation state、quality、usage 混在一起 |
| `decision leak` | 把 activation state / readiness level 偷渡進 verdict 或 memory promotion |

## Severity Levels

| Severity | Definition |
|----------|------------|
| `low` | 誤讀造成錯誤 mental model，但沒有導致錯誤行動 |
| `medium` | 誤讀導致錯誤 reviewer action，例如走錯 triage path |
| `high` | 直接碰到 decision boundary，例如 allow/deny 或 memory promotion 被影響 |

**High-severity exception：**  
若單一 `high` event 已直接碰到 decision boundary，可提前觸發 intervention，不必等到標準兩次門檻。

**Severity judgment rule：**  
只有真的碰到 allow/deny、memory promotion、policy precedence 這類 decision boundary，才算 `high`。  
概念混淆、triage 錯誤、mental model 不清楚，原則上應落在 `medium` 或 `low`。

**Medium severity guard：**  
`medium` 不是終局分類，而是持續觀察狀態。若同一類 `medium` 在短時間內多次 recurrence，應重新評估 severity 與 owner。

**Semantic grouping rule：**  
recurrence 要按語義根因分組，不按表面措辭分組。  
例如：
- `activation used as quality proxy`
- `activation used as usage signal`
- `activation used as decision input`

雖然字面不同，但都屬 activation boundary violation，應算同類 recurrence。  
反過來也不能 over-group，把根因不同的 entry 硬湊成同一類，只為了快點達到 trigger threshold。

## Resolution Status

| Status | Meaning |
|--------|---------|
| `doc_updated` | 透過文件更新處理 |
| `training` | 透過 reviewer guidance / onboarding 更新處理 |
| `ignored` | 確認屬於可接受 ambiguity，不處理 |
| `requires_model_change` | 文件已不足，必須靠模型層擴張 |
| `open` | 尚未解決 |

追蹤 resolution status 的目的，是避免把 adoption lag 誤判成 structural model gap。

## Owner

| Owner | Meaning | Responsible action |
|-------|---------|--------------------|
| `reviewer` | 主要是個別 reviewer 行為修正 | reviewer 自行回看正確解讀 |
| `team` | adoption / training gap | team 更新 onboarding 或 shared convention |
| `framework` | 模型或文件層級需調整 | framework maintainer 評估 doc update 或 model expansion |

`owner` 在 log entry 當下就要先給，不是等 resolution 後才補。  
若後續發現 owner 判錯，可以更新。

**Framework owner guard：**  
若 `owner = framework`，要補一句說明：為什麼這不是 reviewer 或 team 層就能處理的問題。  
否則 `framework` 很容易變成責任垃圾桶。

---

## Log Entries

*(empty - observation phase begins after commit `608be20`, 2026-04-05)*

---

## Pending Watch Items

這些是預測會發生、但尚未真正觀測到的誤讀風險。  
若真發生，再移入正式 log entries。

| Field | Predicted misread | Severity if occurs | Status |
|-------|-------------------|--------------------|--------|
| `observed/recent` | 被讀成「健康」或「正在維護中」 | medium | watch |
| `pending` | 被讀成「快 ready 了」 | low | watch |
| `observed/stale` | 不先查 wiring 就直接推成 adoption stopped | medium | watch |
| `activation_state` | 被拿去影響 verdict 或 memory promotion | high | watch |
| `repo_readiness_level=3` | 被讀成「治理運作正常」 | medium | watch |
| `activation_state` | 因為「不能拿來做決策」而被完全忽略 | low | watch |

---

## Expansion Proposal Quality Gate

任何 triggered expansion proposal 在進 review 前，都必須回答以下問題：

1. **這個 proposal 想解決哪一種具體 misinterpretation？**  
   必須點名對應 log entry。不能只給理論。

2. **為什麼 documentation 不夠？**  
   要說明已嘗試過哪些 doc update / wording / guard clause，以及它們為何無法止住 recurrence。

3. **如果不加這個 dimension，風險是什麼？**  
   必須描述具體 harm，例如 reviewer error rate、decision boundary violation、特定 failure mode。

4. **至少指出一個尚未觀測、但可能相關的 area。**  
   這不是要求立刻修，而是要求提案者證明：自己沒有把目前觀察範圍誤當成整個 search space。

5. **如果這個 proposal 是錯的，未來會看到什麼具體 failure？**  
   proposal 必須可被未來 observation falsify，否則只是一種 preference。

### Counterfactual Check（接受前必填）

```text
Observation:
<log entry 真正顯示了什麼，純事實，不寫 verdict>

Alternative mechanism:
<還有哪個具體機制，也能產生同樣 observation，但不代表需要模型擴張>

Why this mechanism fails to explain the data:
<為什麼 alternative 不足以解釋目前 evidence>

Which part of this reasoning are you least confident about?
<必填，且必須是 decision-relevant uncertainty>
```

若無法填完這四格，proposal 就不算通過 quality gate。

---

## Expansion Proposal Log

所有 proposal，包括 rejection，都應記在這裡。  
否則同一個 proposal 會被不斷重新提出，浪費 review cycle。

```text
### YYYY-MM-DD - <proposal title>

**Triggered by:** <log entry or watch item reference>
**Proposed dimension:** <name>
**Status:** accepted | rejected | deferred
**Decision date:** YYYY-MM-DD
**Rejection reason / deferral condition:** <required if rejected or deferred>
```

若 `status = rejected`，一定要填 rejection reason。  
若 `status = deferred`，一定要寫 reopen condition。開放式 deferral 視同 rejection。

*(empty - no proposals yet)*

---

## Model Expansion Trigger Rule

新增維度（例如 `recent_closeout_quality`）只有在滿足以下任一條件時才合理：

### Standard path（two-instance rule）

1. 同一類 misinterpretation 在不同 context 下至少出現兩次  
2. 現有三維模型無法只靠 documentation 解決  
3. 這個 misinterpretation 的成本高於新增維度的複雜度成本

### High-severity exception

單一 `high` severity 事件，如果直接碰到 decision boundary，可立即進 expansion proposal review。

### 不能單獨觸發 expansion 的情況

- 純理論或預測風險
- 兩次 instance 都以 `doc_updated` 收尾
- 只靠現場解釋就能解掉的 reviewer confusion

### Negative pressure rule

如果 observation window 內沒有 repeated misinterpretation，這本身就是證據，表示當前模型也許已經夠用。  
預設狀態是 stability，不是 expansion。

但這條 rule 只有在真的有 reviewer interaction 時才有效。  
沒有觀察，不代表 sufficiency。

---

## Observation Window End Checklist

觀察窗關閉時，至少檢查：

- [ ] 共有幾筆 log entry？
- [ ] 有沒有任何 `high` severity？
- [ ] 有沒有任何 `requires_model_change`？
- [ ] watch item 有哪些仍未出現？
- [ ] `doc_updated` 之後，誤讀是否真的停止 recurrence？
- [ ] 現有三維模型是否仍足夠？
- [ ] 這個 window 中有哪些 assumption 還沒被任何 falsification signal 測到？
- [ ] 若已有 falsification event，之後具體改了什麼？
