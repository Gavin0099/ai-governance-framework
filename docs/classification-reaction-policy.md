# Classification Reaction Policy：classification 變化如何反映到 surface

## 目的

這份文件定義 governance classification 發生變化時，downstream surface 應該如何反應。
它與 `docs/classification-transition-semantics.md` 的分工是：

- `transition semantics`：哪些 transition 合法、原因如何分類
- `reaction policy`：當 transition 發生時，warning、artifact、summary tool 應如何回應

---

## 目前支援的 reaction surfaces

### 1. `session_end` warnings

觸發條件：
- `classification_changed == True`

輸出方式：
- downgrade 時，在 `warnings[]` 追加 `classification_downgrade` advisory
- anomaly upgrade 時，在 `warnings[]` 追加 `classification_anomaly` advisory

落點：
- `session_end` return dict 的 `warnings[]`

### 2. Verdict artifact escalation

觸發條件：
- `classification_changed == True`

輸出方式：
- `override_or_escalation.governance_escalation_present = true`
- `governance_escalation_type` 允許值：
  - `classification_downgrade`
  - `classification_anomaly_upgrade`

這裡的 escalation type 用來讓 consumer 知道這是一個治理層升級訊號，而不是把 classification 本身包裝成新的 authority。

### 3. Classification session summary tool

目的：
- 讓 reviewer / maintainer 可以觀察一段時間內 classification 的變化分布

主要輸出：
- `downgrade_count`
- `anomaly_count`
- `conservative_downgrade_rate`
- `policy_flags`
- `reason_distribution`
- `effective_class_distribution`

## `policy_flags` 語義

| Flag | 類型 | 觸發條件 | 說明 |
|---|---|---|---|
| `anomaly_alert` | hard invariant | `anomaly_count > 0` | 代表 proxy inconsistency 或流程異常 |
| `classifier_review` | drift signal | `conservative_downgrade_rate > threshold` | 代表 downgrade 過多，需回頭檢查 classifier / adapter |
| `taxonomy_breach` | schema contract | unknown reason values 出現 | 代表 `reclassification_reason` 超出 taxonomy |

## `policy_ok` 的解讀

`policy_ok = False` 不代表系統已經 hard failure。  
它代表這個 classification surface 出現需要 triage 的訊號，可能是：
- hard invariant 被觸發
- drift signal 累積
- schema breach 出現

consumer 不應把 `policy_ok` 直接解讀成 verdict。

## Conservative Downgrade Threshold

`conservative_downgrade_rate` 的 threshold 應被視為 drift indicator，不是 zero-tolerance invariant。

它的意義是：
- 觀察 adapter / observation baseline 是否過度保守
- 檢查 agent class 是否總是被單一 proxy 壓低
- 讓 reviewer 發現 classification evidence 是否過度偏向降級

因此這個 rate 不應被用來：
- 要求它永遠等於 0
- 作為單次 session 的 hard failure 條件

## 目前不做的 reaction

這份文件目前**不做**：
- 因 downgrade 自動改寫 final verdict
- 因 anomaly 直接 block session
- 讓 classification summary 變成 machine authority

## 一句總結

`classification_reaction_policy` 的目標，是把 classification 變化安全地投射到 warning、artifact 與 summary surface，而不是把 classification 本身變成新的裁決來源。
