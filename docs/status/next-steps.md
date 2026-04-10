# Next Steps

> 更新日期：2026-04-08

---

## 目前狀態

repo 已從早期原型，收斂到較明確的 bounded runtime posture。

目前比較準確的理解方式是：

- session workflow enhancement 已進入 `implementation-complete, semantics-observation phase`
- advisory slice v1 已收斂為 reviewer-visible、non-verdict-bearing 的語義基礎層
- closeout / onboarding / readiness / source audit 已有可觀測 surface

---

## 接下來的優先順序

### 1. 觀察而不是擴權

目前更值得做的是觀察真實 session / consuming repo 分布，而不是再快速新增 layer。

重點包括：

- canonical closeout valid rate
- `warning_only / none` session 比例
- audit flags 穩定度

### 2. 繼續補 shared path 的真實 adoption

例如：

- consuming repo 是否真的使用 canonical framework source
- shared closeout / readiness / onboarding surface 是否真的被下游看到

### 3. 嚴格控制 companion slice 的擴張

像 classification governance 這類 companion slice，應維持 bounded posture，不要直接滑向新 authority 或 full matrix coverage。

---

## 現在不建議做的事

- 不要把 advisory 直接接進 verdict authority
- 不要追求 full signal × full surface matrix
- 不要把 `/wrap-up` 變成官方唯一 closeout 入口
- 不要把 machine-readable advisory metadata 太快升格成 downstream automation input

---

## README / status / docs 的角色

這些高可見度入口現在的目標，不是 marketing expansion，而是 anti-expansion guard。

它們應該幫忙做到：

- 把 repo 真正已經是什麼說清楚
- 把 repo 刻意還不是什麼說清楚
- 減少 adopter / reviewer 的誤讀

---

## 一句話

接下來最合理的方向不是再長更多新層，而是先觀察 bounded runtime 在真實 repo 與真實 session 中是否穩定成立。
