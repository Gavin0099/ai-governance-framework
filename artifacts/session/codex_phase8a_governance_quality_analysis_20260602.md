# Codex AI Governance 套用後回應品質分析

<!-- Session: 585cfd62-322d-4bde-8f87-786a096ea010 -->
<!-- Date: 2026-06-02 -->
<!-- Subject: usb-if-hub-spec-reference Phase 7A/7B/7C/8A Codex response quality review -->
<!-- Status: corrected — 3 adjustments applied (baseline gap, Phase 7B risk, Tier system) -->

## 0. 評估限制聲明

本分析未收集 governance 套用前的 baseline 對照數據。
以下所有「有變好」的觀察均為**觀察性宣告，非量測結果**。
若需正式評估改善幅度，須建立 pre/post 對照組，本文不具備此條件。

---

## 結論先講

相比通用 agent 行為模式（無 governance 約束），此次 Codex 回應具備以下治理型行為：Scope 限制、Boundary 標示、Validation 分層、Risk 陳述、Cannot Claim 列舉、Next Step 收斂。

這是 AI governance 開始生效的訊號，但「明顯變好」的幅度無法從本分析中量測。

---

## 一、整體品質觀察

此次 Codex 回應比一般 agent 回應成熟，主要表現在五個地方：

1. 每一刀都有明確 scope
2. 每一刀都有 commit checkpoint
3. 每一刀都有 validation
4. 每一刀都有不能宣告的邊界
5. 下一步建議有縮小範圍，而不是擴張任務

這代表它不是單純說：

> 我做完了 / build pass / 下一步繼續

而是開始形成治理型回報：

> 我做了什麼 / 只動了哪裡 / 驗證了什麼 / 沒驗證什麼 / 目前風險在哪 / 下一刀怎麼切才不膨脹

---

## 二、Phase 7A 的回應品質

Phase 7A 是這批裡面最治理化、最乾淨的一段。

它有清楚寫：
- `section_refs presence does not upgrade claim_level`
- `inferred + review_required + section_refs` 是合法組合
- 不做 validator / 不做全 repo 遷移 / 不做 verified promotion

Codex 知道 Phase 7A 只是在做結構層，不是驗證層、不是 enforcement 層、不是 PDF verified 層。

**評價：很好 | 主要不足：validation 語意可更精準標為 structural-only**

---

## 三、Phase 7B 的回應品質

Phase 7B 有一個值得肯定的行為：Codex 發現 `PORT_OVER_CURRENT` 不在 scaffold，沒有為了符合計畫而擴 table。

然而，這裡存在一個**應升為 Risk 的治理缺口**（原分析將其低估為「主要不足」）：

`PORT_OVER_CURRENT` 是安全相關路徑（safety path）。
Codex 以 `C_PORT_ENABLE` 替代，意味著此次 pilot **沒有覆蓋到 high-risk boundary condition**。

Codex 不擴 scope 的行為在治理上是對的。
但它**應該同時標記**：

> Phase 7B pilot 的 high-risk coverage 低於原計畫；此差距應在 Phase 7 checkpoint 中明確記錄，不應等到 Phase 8 才發現。

沒有標記這個差距，才是真正的治理缺口。

**評價：良好 | 主要 Risk：high-risk coverage 下降未在 checkpoint 中記錄**

---

## 四、Phase 7C 的回應品質

Phase 7C 仍然守住了治理邊界（不升 verified、沒有 PDF extraction pipeline、section_refs 只是 attachment layer）。

但有 **scope purity** 問題：主任務是新增 usage note，卻在同一刀混入了中文/英文頁 encoding residue 清理（82 行新增、34 行刪除）。

未來應要求：

```
Incidental cleanup:
- file: <path>
- reason: encoding residue
- semantic change: no
```

若不分開標示，後續 reviewer 無法快速判斷哪些是主要目的、哪些是附帶修正。

**評價：合格偏好 | 主要不足：附帶清理與主任務混在同一刀，scope purity 下降**

---

## 五、Closeout / PLAN.md 收尾

提出 PLAN.md closeout 方向正確（防止計畫文件停在舊狀態導致後續 agent 讀錯任務狀態）。
目前停在「尚未完成」狀態，Codex 沒有先宣告完成，這是對的。

**評價：方向正確，不能宣告 closeout DONE**

---

## 六、最明顯的三個進步（有 evidence 支撐）

**1. 開始會限制自己**
多次出現：不加 validator / 不做全 repo 遷移 / 不做 verified promotion / 不做 PDF extraction pipeline

**2. 開始保留「不能宣告」**
Phase 7B 明確寫：不能說 port status bits are verified / 不能說 PDF evidence is complete

**3. 下一步建議變得更保守**
沒有建議「現在補 PDF parser」或「全 repo verified」，而是先 PLAN.md closeout、先收斂

---

## 七、尚未成熟的地方（可操作）

**1. Validation 分類不夠精準**

現在：`Validation: PASS`

應改為（Rule 4 格式，尚未部署至 usb-if-hub-spec-reference）：
```
Validation:
- structural:    PASS — <command>
- build:         PASS — <command>
- semantic:      NOT CLAIMED
- behavioral:    NOT PRESENT
- ext evidence:  NOT PRESENT
```

注意：Rule 4 目前尚未部署至 usb-if-hub-spec-reference。
不應為此製造人工 session；應在下次自然使用該 repo 時，透過 `install-hooks.sh` 部署後被動觀察。

**2. Risk 可以格式化**

建議固定格式（Rule 4 Risk 欄位）：
```
Risk:
- scope drift:        none | [description]
- claim inflation:    none | [description]
- evidence maturity:  [one line]
```

**3. Incidental cleanup 要獨立標示**（見 Phase 7C）

---

## 八、評估結論

| 面向 | 評價 |
|---|---|
| Scope 控制 | 很好 |
| Claim ceiling | 很好 |
| Validation 回報 | 合格，可再精準 |
| Risk 表達 | 良好 |
| 下一步切分 | 很好 |
| 避免 verified inflation | 很好 |
| Scope purity | Phase 7C 稍微下降 |
| Phase 7B high-risk coverage | **缺口未記錄（應升為 Risk）** |
| Closeout 意識 | 良好 |

**整體評估：Tier 3/5**

> Tier 1 = 無治理行為
> Tier 2 = 文字邊界存在但不一致
> Tier 3 = 治理型行為已建立，格式化尚未完成  ← 目前位置
> Tier 4 = 所有 validation/risk/claim 有固定格式，machine-readable
> Tier 5 = 格式 + 自動 enforcement + baseline 量測

---

## 九、最終判斷

AI governance 已開始約束 Codex 的輸出行為，觀察到的治理型行為是正向的（見 Section 六）。
**目前下一個優化點不是再加更多規則，而是把回報格式標準化**，讓「不能宣告什麼」和「驗證層級」更可機器檢查。

---

## 三個調整說明（相對原版）

1. **Baseline 缺口**：原版說「明顯變好」，但缺乏對照組。修正為「觀察性宣告，非量測結果」，並在 Section 0 明確聲明限制。

2. **Phase 7B 風險升格**：原版把 PORT_OVER_CURRENT → C_PORT_ENABLE 替換列為「主要不足」。修正為應升為 Risk：safety path 未覆蓋是治理缺口，不是一般不足。

3. **評分改為 Tier 制**：原版使用 8.2/10，沒有 rubric anchor。修正為 Tier 3/5，並附上各 Tier 定義，使評估可校準。
