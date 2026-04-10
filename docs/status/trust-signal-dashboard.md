# Trust Signal Dashboard

> 更新日期：2026-04-09
> 目前對應正式 release：`v1.1.0`

---

## 目的

`Trust Signal Dashboard` 用來集中顯示目前 repo 幾條主要信任訊號的狀態，讓 reviewer 或 adopter 可以快速看見：

- 哪些 signal 已存在
- 哪些 signal 只是 advisory
- 哪些 signal 靠近 enforcement
- 哪些 signal 已由其他 runtime 路徑處理

---

## 使用方式

這是一個 dashboard，不是裁決引擎。

它適合拿來做：

- 快速盤點目前信任姿態
- 觀察 bounded runtime 是否有逐步補齊
- 幫 reviewer 定位接下來該看哪個 status 頁或 artifact

它不適合拿來做：

- 直接輸出 pass / fail
- 替代原始 evidence
- 單獨定義 authority

---

## 建議搭配閱讀

- [Runtime Governance Status](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Reviewer Handoff](reviewer-handoff.md)
- [docs/releases/README.md](../releases/README.md)

---

## 與 release 的關係

這個 dashboard 可以幫助理解 release posture，但它本身不是 release note，也不是 publish checklist。

目前正式 release-facing 版本仍是 `v1.1.0`；dashboard 主要反映的是 `main` 分支上的較新 runtime / governance surface。

---

## 一句話

`Trust Signal Dashboard` 是 reviewer-facing 的信任總覽，不是 authority 層，也不是新的 release gate。
