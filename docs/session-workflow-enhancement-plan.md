# Session Workflow Enhancement Implementation Plan：bounded closeout trust-boundary 收斂計畫

> 狀態：implementation-complete  
> 更新日期：2026-04-08

## 目的

這份計畫描述的是：如何把 session closeout 從 AI 自述的鬆散輸入，收斂成 system-validated canonical artifact。

這條主線最後要守住的是：
- AI 只寫 candidate closeout
- system 透過 `session_end` 產生 canonical closeout
- downstream consumer 只吃 canonical

簡化後可寫成：

```text
AI candidate -> system canonicalization -> canonical consumer only
```

## 為什麼這條線重要

如果 closeout 只是 AI 自述，後面的：
- session continuity
- reviewer audit
- session index
- memory promotion

都會建立在不可信輸入上。

因此這條線的核心不是「多一個 closeout 檔」，而是建立 trust boundary。

## 已完成的主要 slice

### 1. Canonical closeout producer / consumer 分離

- producer 可以是 AI candidate drafting surface
- canonical closeout 一律由 system 產生
- consumer 只讀 canonical artifact

### 2. Closeout context injection 分層

`_canonical_closeout_context.py` 目前採用：
- `full`
- `warning_only`
- `none`

這避免了「只要有上一份 closeout 就全部注入」的污染風險。

### 3. Audit 保持 aggregation only

`closeout_audit.py` 目前只做聚合與觀察，不自成第三套 authority。

### 4. `/wrap-up` 保持 candidate drafting surface

`/wrap-up` 目前只做 candidate drafting，不是 canonical closeout 的 authority source。

## 目前刻意不做的事

這條線目前**不做**：
- 讓 `/wrap-up` 變成唯一 closeout 入口
- 讓 closeout audit 直接改 verdict
- 做完整 taxonomy normalization / fuzzy matching
- 把 closeout 擴成 full execution harness 的一部分

## Observation Phase 應觀察的指標

後續比較值得看的不是再加功能，而是：
- canonical closeout valid rate
- `warning_only / none` 的 session 比例
- audit flags 的穩定度

這些指標用來判斷：這條線是否在真實 session 中穩定，而不是只在 code 層完成。

## 一句總結

`Session Workflow Enhancement` 目前已進入 `implementation-complete, semantics-observation phase`：架構與信任邊界已固定，接下來的重點是觀察實際 session 分布，而不是再擴權。
