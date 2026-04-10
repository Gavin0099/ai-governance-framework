# Closeout Audit

> 更新日期：2026-04-09

---

## 目的

`Closeout Audit` 用來聚合 canonical closeout 的主要 policy flags 與 audit posture。

它的功能是讓 reviewer 看見：

- canonical closeout 是否存在
- closeout 相關 flags 是否穩定
- audit 是否指出需要額外注意的 bounded risk

---

## 邊界

這一頁是 aggregation-only surface。

它不應被誤讀成：

- 新的 authority layer
- 取代 canonical closeout 的真相來源
- 單獨決定 session 是否有效

真正的 truth source 仍然是 canonical closeout 與相關 runtime artifacts。

---

## Reviewer 讀法

reviewer 適合用這一頁來：

- 快速看 closeout flags 是否有異常
- 觀察 `warning_only / none` 分布
- 判斷是否需要回看 canonical closeout artifact

如果要做實質判斷，仍應回看：

- canonical closeout
- session summary
- runtime trace

---

## 一句話

`Closeout Audit` 是 canonical closeout 的 reviewer-facing audit summary，不是新的 closeout authority。
