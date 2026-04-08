# Advisory Slice Boundary

> 狀態：v1 已收斂
> 更新日期：2026-04-08

## Purpose

這份文件的目的不是宣告 advisory 已經變成 authority，而是把目前這條 advisory-first 路徑的完成邊界寫死。

它要防止的誤解是：

- 還能延伸 ≠ 還沒完成
- 有更多 signal 可做 ≠ 現在就應該繼續擴
- reviewer-visible ≠ verdict-bearing

## 目前這個 slice 已證明什麼

在 bounded scope 下，這個 advisory slice 已經具備：

- advisory signal taxonomy
- advisory signal phase boundary
- advisory signal producer contract
- reviewer-facing semantic rendering
- 至少一個跨 surface 的 consistency example

更準確地說，它目前已收斂為：

> 一個受限、reviewer-visible、non-verdict-bearing 的語義基礎層。

## Current Completed Scope

### Signal Scope

目前只正式收了這 3 個 signal：

- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

這不是 full signal universe。

### Consumer Scope

目前只驗到兩個 consumer：

- `pre_task_check` human-readable surface
- `post_task_check` human-readable surface

它們共同邊界是：

- reviewer-visible
- non-verdict-bearing
- 非 machine-authoritative

### Cross-Surface Scope

目前已驗到的跨 surface consistency example：

- `required_evidence_missing`

這代表 advisory semantics 已不是只綁在單一 surface 的巧合，但也不等於 full matrix 已完成。

## Done Boundary

這一階段可視為完成，因為以下條件都已成立：

- 至少兩個真實 consumer 已存在
- 至少一個 cross-surface consistency example 已成立
- taxonomy / phase boundary / producer contract 都已寫死
- reviewer-facing rendering 已被 code + tests 鎖住
- advisory signal 仍未越界成 proof / hard gate / machine authority

## Explicit Non-Goals

以下內容刻意不在這個 slice 內：

- full signal × full surface matrix
- machine-readable advisory authority expansion
- advisory-to-verdict coupling
- proof-bearing compliance signal
- generic runtime signal universe
- 用 advisory proxy 直接做 edit legitimacy gate

## Allowed Direction

如果之後需要重開這條線，只能沿著這種方向：

- 新的 reviewer-visible、non-verdict-bearing consumer
- 新的誤讀風險需要被明確消除
- 現有 advisory semantics 在另一個 bounded surface 上需要一致性驗證

## Reopen Conditions

只有在以下情況，才應該重新打開這條 advisory 線：

- 有新的 reviewer-visible surface 需要 advisory semantics
- 既有 rendering 被證明會讓 reviewer 誤讀
- phase boundary 出現實際衝突
- producer metadata 被證明不足以支撐現有 reviewer surface

如果只是因為：

- coverage 焦慮
- 想再多做幾個 signal
- 想把它做得更像 machine authority

那不應視為 reopen 條件。

## Stop Rules

以下行為應被視為越界：

- 把 advisory signal 接進 final verdict
- 讓 advisory signal 單獨影響 hard gate
- 因為 metadata 更完整，就把 advisory 升格成 proof
- 為了 consistency 而強迫所有 signal 出現在所有 surface

## 正確的現況說法

比較準的說法是：

- advisory slice v1 已收斂
- reviewer-visible advisory semantics 已在 bounded scope 下成立
- 這條線目前刻意不延伸到 machine-facing 或 verdict-bearing authority

比較不準的說法是：

- advisory support is done
- observation layer is done
- cross-surface advisory is complete

因為那些說法都把範圍講太大了。

## 一句話結論

advisory slice v1 現在不是「還能做所以繼續做」，而是已經被正式封邊成一個受限的 reviewer-visible 語義層。  
後續如果要重開，應該由明確的 reopen condition 驅動，而不是由 expansion 慣性驅動。
