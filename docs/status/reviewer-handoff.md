# Reviewer Handoff

> 更新日期：2026-04-09

---

## 目的

這一頁說明目前 repo 的 reviewer handoff surface 應如何被理解。

它不是 authority layer，也不是新的 runtime decision engine，而是 reviewer-facing 的整理入口，用來幫 reviewer 快速看到：

- trust posture
- release posture
- runtime posture
- 主要 handoff artifacts

---

## 這個 surface 的角色

`Reviewer Handoff` 的角色是 summary，不是 raw manifest dump。

它應該：

- 幫 reviewer 快速定位該看哪些 bundle
- 指出哪些 surface 已可用
- 說清楚哪些資訊只是 handoff-ready summary

它不應該：

- 取代原始 artifact
- 形成獨立 authority
- 宣稱自己能單獨做出 release / runtime verdict

---

## Reviewer 會看到什麼

目前 handoff surface 主要應串接：

1. `runtime governance status`
2. `trust signal dashboard`
3. `domain enforcement matrix`
4. `generated reviewer handoff bundle`

這樣 reviewer 可以先從 summary 進入，再回到原始 artifacts 做查核。

---

## 使用原則

### 1. summary 先行，artifact 跟進

reviewer 先用 handoff 頁定位問題，再進入對應 artifact，不應只看 summary 就完成判斷。

### 2. 不用它替代 raw evidence

如果某個問題需要細節，應回看：

- runtime trace
- release bundle
- onboarding report
- generated reviewer handoff bundle

### 3. 不形成第二套真相

這一頁的作用是導覽與壓縮，不是生成新 truth source。

---

## 關聯入口

- [Runtime Governance Status](runtime-governance-status.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- `docs/status/generated/reviewer-handoff/README.md`

---

## 一句話

`Reviewer Handoff` 是 reviewer-facing summary surface，用來提高交接效率，但不應被誤讀成新的 authority layer。
