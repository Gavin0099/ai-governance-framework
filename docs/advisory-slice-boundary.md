# Advisory Slice Boundary：advisory slice v1 的完成與暫停邊界

> 狀態：v1 已收斂  
> 更新日期：2026-04-08

## 目的

這份文件的目的，是把 advisory slice 第一階段的暫停/完成邊界寫死，避免 advisory-first 路徑因為還能延伸，就被默認為尚未完成。

這份文件要回答的是：

- 目前這條 slice 完成到哪裡
- 哪些東西屬於這一階段的成果
- reviewer-visible 但 non-verdict-bearing 的邊界在哪裡

## 本階段完成的 slice

在目前 bounded scope 下，advisory slice v1 已包含：

- advisory signal taxonomy
- advisory signal phase boundary
- advisory signal producer contract
- reviewer-facing semantic rendering
- 至少一個跨 surface consistency example

這一階段的收斂目標是：

> 建立一個受限、reviewer-visible、non-verdict-bearing 的 advisory 語義基礎層

## Current Completed Scope

### Signal Scope

目前只正式涵蓋 3 個 signal：

- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

這不是 full signal universe。

### Consumer Scope

目前已驗證的 consumer：

- `pre_task_check` human-readable surface
- `post_task_check` human-readable surface

它們都屬於：

- reviewer-visible
- non-verdict-bearing
- 非 machine-authoritative

### Cross-Surface Scope

目前已驗證的跨 surface consistency example：

- `required_evidence_missing`

這代表 advisory semantics 至少已能離開單一 surface，而不在 phase 切換時漂移。

## Done Boundary

以下條件成立時，這一階段即可視為收斂：

- 至少兩個真實 consumer 已存在
- 至少一個跨 surface consistency example 已成立
- taxonomy / phase boundary / producer contract 已完成
- reviewer-facing rendering 已被 code + tests 鎖住
- advisory signal 沒有被偷偷升格成 proof / hard gate / machine authority

## Explicit Non-Goals

以下內容不屬於這一階段：

- full signal × full surface matrix
- machine-readable advisory authority expansion
- advisory-to-verdict coupling
- proof-bearing compliance signal
- generic runtime signal universe
- 把 advisory proxy 變成 edit legitimacy gate

## Allowed Direction

若之後有需要重開，這一條線允許的方向只包括：

- 新的 reviewer-visible、non-verdict-bearing consumer
- 降低 reviewer 誤讀風險的語意收斂
- 驗證 advisory semantics 是否能在 bounded surface 上保持一致

## Reopen Conditions

只有在以下條件成立時，才應重開 advisory slice：

- 新的 reviewer-visible surface 需要 advisory semantics
- 現有 rendering 仍讓 reviewer 容易誤讀
- phase boundary 出現新的實作漂移
- producer metadata 無法再被現有 reviewer surface 正確消費

以下情況**不是** reopen 理由：

- coverage 焦慮
- 想再補更多 signal
- 想更快接到 machine authority

## Stop Rules

此 slice 在任何時候都不應跨過以下邊界：

- 把 advisory signal 接進 final verdict
- 用 advisory signal 直接形成 hard gate
- 用 metadata 包裝後再把 advisory 假裝成 proof
- 因為想追 consistency，就把每個 signal 補進所有 surface

## 建議表述

較準確的說法：

- advisory slice v1 is converged
- reviewer-visible advisory semantics are established for the current bounded scope
- this slice is intentionally not extended to machine-facing or verdict-bearing authority

不建議的說法：

- advisory support is done
- observation layer is done
- cross-surface advisory is complete

## 一句話結論

advisory slice v1 已收斂為一個受限、reviewer-visible、non-verdict-bearing 的語義基礎層；只有在明確 `reopen condition` 出現時，才應重新擴張。
