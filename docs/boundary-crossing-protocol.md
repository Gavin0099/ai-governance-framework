# Boundary Crossing Protocol

> 版本：1.0
> 相關文件：
> - `docs/decision-quality-invariants.md`
> - `docs/learning-stability.md`
> - `docs/adversarial-test-scenarios.md`
> - `docs/governance-mechanism-tiers.md`

---

## 目的

一套治理系統若仍在自己的 observation model 內運作，通常能做出相對可靠的決策。  
但同樣的系統一旦跑到 observation model 外面，仍可能產生看起來很自信、實際上卻沒有結構支撐的決策。

這個落差常常在系統內部不可見：

- 機制有跑
- signal 有檢查
- process 看起來有被遵守

但其實系統已經不在它能可靠判斷的範圍裡了。

這份 protocol 要定義的是：

1. 什麼叫 boundary condition
2. 到了 boundary 時必須有哪些 response type
3. 如何區分 genuine deferral 與 avoidance
4. 何時可以重新進入正常操作

---

## Boundary Conditions

boundary condition 不是單純「資訊還不夠」。  
它是一種結構狀態：要做出可支持決策所需的 evidence / mechanism，在**現有 observation model 裡根本拿不到**。

### B1：Evidence below observability threshold

需要的 evidence 在目前 observation structure 中拿不到。  
不是「還沒蒐集」，而是「目前結構產不出來」。

### B2：Decision outcome 在 observation model 內不可驗

無法為這個 decision 寫出正向 falsifiability condition。  
若 correctness 唯一證據只剩「目前沒看到 failure」，那這個 decision 其實不可驗。

### B3：Classification with no path to resolution

failure 已被看到，但無法往 `cause_unknown` 以上推。  
不是因為還沒看夠，而是 observation model 本身沒有覆蓋這條 causal chain。

### B4：Conflicting signals with no framework adjudication

兩個以上 executable signal 要求互斥行動，但 framework 內沒有 precedence 機制裁決。  
若 advisory containment rule 已能處理，就不算 B4。

### B5：Decision scope 超出 observation model coverage

decision 涉及 framework 本來就沒設計要處理的 failure mode、evidence type 或 domain。

---

## Required Behavior At The Boundary

偵測到 boundary condition 後，normal operation 應暫停，必須選擇四種 response 之一：

- `defer_with_condition`
- `low_confidence_proceed`
- `escalate_for_model_extension`
- `refuse_as_out_of_scope`

這些 response 不是態度，而是可審核的處理型別。

---

## 一句話結論

這份 protocol 的目的，是在 system 超出 observation model 能力時，避免它假裝自己仍能正常判斷，並要求用可重建的 boundary response 取代自信但無支撐的 verdict。
