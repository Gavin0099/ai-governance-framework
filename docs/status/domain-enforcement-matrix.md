# Domain Enforcement Matrix

> 更新日期：2026-04-08

---

## 目的

這份 matrix 用來說明目前 external domain-contract repo 在 framework 內的 enforcement posture。

它回答的不是「domain 有沒有存在」，而是：

- 哪些 domain 目前只是 advisory-only
- 哪些 domain 已有較明確的 runtime posture
- 哪些 contract 仍只是 bounded integration，而不是 full policy engine

---

## 讀法

這份表不是 capability catalog，而是 posture matrix。

閱讀時應特別注意：

- domain 名稱
- 對應 rule / contract id
- 當前 enforcement posture
- 仍未宣稱的範圍

---

## 目前的 bounded posture

framework 目前沒有把 external contract repo 直接升格成 full policy engine。

所以 matrix 的解讀應保持保守：

- 有 integration，不等於 full enforcement
- 有 validator / discovery，不等於所有 domain evidence 都已接進 runtime decision
- 有 domain matrix，不等於每個 domain 都進了 hard gate

---

## 關聯頁面

- [Runtime Governance Status](runtime-governance-status.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Reviewer Handoff](reviewer-handoff.md)

---

## 一句話

`Domain Enforcement Matrix` 用來說明 external domain contract 的當前接入姿態，而不是宣稱 framework 已完成完整 domain policy enforcement。
