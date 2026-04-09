# Failure Mode Test Plan

這份文件定義 governance runtime 第一批刻意 break-test 的方向。  
目標不是驗 happy path，而是確認：

> 當 evidence、policy 或 runtime execution 出錯時，系統是否仍然可預測、可審查。

## 當前位置

目前 repo 的 control plane 強於 execution plane：

- `v2.6` decision model 已明確成文
- validator payload 具版本與 provenance 概念
- runtime session end 已能產出最小 verdict / trace artifact

下一道信任門檻不是多寫功能，而是確認 failure behavior 是否真的被 exercised。

## 第一波 Failure Modes

第一批 break-test 先涵蓋五類：

1. `missing_required_evidence`
2. `invalid_evidence_schema`
3. `policy_conflict`
4. `runtime_failure`
5. `determinism_replay`

這些 failure mode 對應當前 `v2.6` decision model，也更接近未來 `1.0` 應負責的實際信任邊界。

## 預期輸出

每個 scenario 至少要定義：

- 注入了哪種 fault
- 應由哪個 runtime component 發現
- 預期會如何影響 verdict
- 預期在 trace / verdict artifact 上能看到什麼
- deterministic replay 應該成立到什麼程度

machine-readable source of truth 是：

- `governance/failure_mode_test_matrix.v0.1.json`

## 驗收方向

只有當 runtime 能逐步證明以下幾件事，這份 plan 才算真正成立：

- 相同 evidence + policy snapshot 重放時，會得到相同 verdict
- degraded input 仍能產出 reviewer 可讀的 runtime artifact
- policy conflict 不會繞過 runtime ownership
- runtime failure 會 fail closed 或以已宣告方式 escalate
- 缺失或壞掉的 evidence 不會被默默當成 success

## 範圍說明

這是一個刻意最小化的 first slice。  
它先把 break-test contract 寫清楚，再談完整的 fault-injection harness。
