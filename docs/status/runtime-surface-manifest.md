# Runtime Surface Manifest

> 更新日期：2026-04-09

---

## 目的

`Runtime Surface Manifest` 用來列出 repo 目前有哪些 execution / evidence / authority surface 已被 framework 顯式看見。

它的重點不是把 repo 變成 full execution harness，而是：

- 讓 reviewer 與 maintainer 知道目前有哪些 surface 已被納入觀測
- 讓 unknown / orphan / mismatch 這類 consistency signal 有明確對照面
- 讓後續 coverage 與 runtime posture 不再建立在黑箱假設上

---

## 這個 surface 的角色

manifest 是 inventory-first surface。

它回答的是：

- 系統知道自己有哪些 surface
- 哪些 surface 是 execution / evidence / authority 類型
- 哪些 surface 在 manifest 與實際 repo state 之間出現不一致

它不直接回答：

- 決策是否正確
- coverage 是否完整
- 某個 surface 是否已足以形成 authority

---

## Reviewer 應如何使用

reviewer 適合用這一頁來：

- 快速盤點目前 manifest posture
- 定位 unknown / orphan / mismatch signal
- 確認 repo 是否已從黑箱 execution 轉向可列舉 surface

若要做更深入判讀，仍應回到：

- generated manifest
- coverage status
- runtime governance status

---

## 一句話

`Runtime Surface Manifest` 是 bounded runtime 的 surface inventory，不是 full execution model，也不是新的 authority layer。
