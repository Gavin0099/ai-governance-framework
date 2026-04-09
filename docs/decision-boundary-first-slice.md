# Decision Boundary First Slice

> 狀態：規劃中的第一個 runtime-facing slice
> 建立日期：2026-03-31
> 依賴：`docs/decision-boundary-layer.md`

---

## 目的

這份文件用來固定 `Decision Boundary Layer` 第一個 runtime slice 的接受邊界。

它的作用是避免最常見的擴張錯誤：

> 想一次證明整個模型，結果在任何一個 slice 真正證明價值之前，就先把 runtime surface 擴得太大。

---

## First slice 只要證明一件事

第一個 slice 只需要證明：

> pre-decision boundary 可以改變真實 runtime verdict，而且 reviewer 能只靠 artifact 重建這個變化。

對 version one 來說，這就夠了。

---

## Slice 1 包含什麼

Slice 1 只包含 implementation start 前的最小 precondition handling。

目標檢查：

- `missing_sample`
- `missing_spec`
- `missing_fixture`

允許結果：

- `analysis_only`
- `restrict_code_generation_and_escalate`
- `stop`

對 task level 的預期：

- `L0`：可以降級成 exploration / analysis-only，但要留下 warning
- `L1`：缺少必要前提時至少要 escalate
- `L2`：若前提對 correctness 屬必要條件，可以 hard-stop

---

## 暫時的 contract surface

Slice 1 現在使用一個刻意很窄的 contract interface。

支援欄位：

- `preconditions_missing_sample`
- `preconditions_missing_spec`
- `preconditions_missing_fixture`

範例：

```yaml
preconditions_missing_sample:
  - pdf_parser

preconditions_missing_spec:
  - protocol_implementation

preconditions_missing_fixture:
  - bugfix
```

這個 surface 是第一階段的 bootstrap 介面，特性是：

- flat
- explicit
- 在 `contract.yaml` 中容易檢視
- 只處理 explicit missing-state

它現在還不是：

- 最終的 DBL schema
- 通用 precondition authoring model
- semantic sufficiency model
- nested policy language

特別是第一階段**不會**推論：

- pseudo-presence
- semantic insufficiency
- sample/spec quality
- 超出明示存在訊號之外的 evidence completeness

---

## Slice 1 明確排除什麼

第一個 runtime slice 不應包含：

- full repo identity enforcement
- 只靠 identity 就改成 `escalate` / `stop`
- proposal semantic classification
- 廣義 repo taxonomy 設計
- 超出既有 scope / evidence surface 的 capability expansion
- 新的 invariant authoring system
- 超出第一道 gate 所需的 policy precedence branch
- explicit missing-state 以外的 pseudo-presence / semantic insufficiency 驗證

---

## 為什麼要這樣排序

minimal precondition gate 是最好的第一個 proof point，因為它：

- 對真實錯誤有直接對應
- reviewer 容易理解
- 容易在 artifact 裡留下 trace
- 可以做 degradation，不只能硬擋
- 避開 identity taxonomy 這個早期最容易失控的問題

Identity 更適合後面才做，而且順序應該是：

1. 可載入 input
2. 可顯示於 trace
3. 最後才考慮 bounded enforcement

不是一開始就拿來當 hard gate。

---

## 接受標準

Slice 1 只有在以下條件都成立時才算成功：

1. 缺少必要前提時，runtime verdict 真的會改變。
2. 這個 verdict 變化可在 trace 或 artifact 中看見。
3. reviewer 不需要額外作者背景就能解釋為什麼變了。
4. 實作沒有引入 duplicate truth source。
5. 這個 slice 帶來的複雜度，小於它阻止的 failure mode。
6. false stop / false escalate 可以被觀察、分類，而不是被口頭帶過。

如果其中任一條不成立，就先停在這裡修正，不要往更多 layer 擴。

---

## 下一步驗證

Slice 1 的下一步不是擴更多 DBL surface。

下一步應該用 [`dbl-first-slice-validation-plan.md`](dbl-first-slice-validation-plan.md) 來驗：

- reviewer reconstruction
- insufficiency-like example
- adversarial / gaming case

先確認這個 first slice 是真實 decision surface，不只是小型 demo，再考慮擴張。
