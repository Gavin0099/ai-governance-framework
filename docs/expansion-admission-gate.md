# Expansion Admission Gate

> 版本：1.0
> 相關文件：`docs/falsifiability-layer.md`, `docs/anti-ritualization-patterns.md`, `docs/learning-loop.md`

---

## 目的

`Expansion Admission Gate` 用來回答一個很實際的問題：

> 什麼樣的新 layer、new signal、new workflow、new artifact 可以被允許進入 framework，而不是只是把 complexity 疊高？

這個 gate 的重點不是保守，而是避免 framework 在每次看到新需求時，都把 proposal 直接變成長期結構。

---

## Admission 要求

一個 expansion proposal 至少應回答：

1. **要解決的 failure mode 是什麼**
2. **沒有這個 expansion 時，現有系統缺在哪裡**
3. **新增後誰會消費它**
4. **它會增加哪種 complexity**
5. **若失敗時，如何被 falsify 或回收**

如果 proposal 只能說「看起來比較完整」，通常不應通過 gate。

---

## 最低 admission signals

### 1. Failure-backed

proposal 必須能對到真實 failure、blind spot 或 recurring reviewer confusion。

### 2. Consumer-backed

不能只有 producer。必須說清楚誰會讀、誰會用、用來做什麼。

### 3. Boundary-aware

要明講它：

- 不會取代什麼
- 不會升格成什麼 authority
- 不會偷偷形成第二套 truth source

### 4. Reversible

新增後若效果不好，必須可以回收、降級或停用。

---

## 不應通過的 proposal 類型

以下情況通常應被拒絕或延後：

- 只有 naming improvement，沒有 behavioral gain
- 只有 producer，沒有 consumer
- 只是把現有資訊重複輸出到更多 surface
- 想先做 full matrix，再回頭找用途
- 依賴「未來可能會用到」作為主要理由

---

## 與 bounded runtime 的關係

framework 現在的基本姿態不是大而全 runtime，而是 bounded runtime。

所以 expansion admission 的核心原則是：

> 只有當新 layer 能明確降低真實 failure，且不破壞既有邊界時，才值得進主線。

---

## 不是什麼

`Expansion Admission Gate` 不是要阻止系統演進。

它要防的是：

> framework 因為每次都能說出合理理由，最後長成難以維護、難以驗證、也難以收斂的 complexity stack。
