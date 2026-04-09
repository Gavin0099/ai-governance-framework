# Boundary Crossing Protocol

> Version: 1.0
> Related:
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

偵測到 boundary condition 後，normal operation 應暫停，必須選擇四種 response 之一。

### `defer_with_condition`

適用於：
- boundary 是暫時的
- 或可透過特定 evidence / structural change 被解除

必須寫出：
- 哪個 boundary condition（B1~B5）
- 什麼 evidence 或 structure change 能解開它
- 什麼 deadline / trigger 會讓 deferral 結束

### `low_confidence_proceed`

適用於：
- 雖然碰到 boundary，但現在不做決定的成本更高

必須寫出：
- 哪個 boundary condition 成立
- 哪些 assumption 目前無法驗證
- 日後什麼 trigger 會要求重新評估

這不是 boundary bypass，而是 boundary-aware decision。

### `escalate`

適用於：
- 外部驗證資源存在
- 這個決策值得拉高處理層級
- 且 escalation 在需要的時間內能產生結果

### `hard_stop`

適用於：
- 這個 decision 在回到 observable range 前絕對不應繼續
- 錯誤決策的成本高於完全阻斷

`hard_stop` 不應被當成 generic uncertain-decision blocker。  
它主要保留給 B1 / B2 類且高不可逆成本的場景。

---

## Action Selection Determinism

這四種 response type 的存在，是為了避免：

> 同樣的不確定性，由不同 reviewer 做出完全不同的處理

response selection 至少要看兩個維度：

### Dimension 1：Reversibility

這個決策若錯了，之後能不能補救？

| Tier | Definition |
|------|------------|
| `fully_reversible` | 在當前 observation window 內可無成本修正 |
| `reversible_with_cost` | 可修，但代價高 |
| `reversible_eventually` | 理論上可修，但要等後續多層影響發生後才能收拾 |
| `irreversible` | 在可接受成本內無法逆轉 |

### Dimension 2：Cost of not deciding

若現在不做決定，系統層級會發生什麼？

- `Low`：可延後，幾乎沒有系統代價
- `High`：若不決定，會放任高風險行動繼續、關閉不可逆窗口，或卡住依賴決策

### Selection Matrix

| Reversibility | Cost of not deciding | External validation available? | Required response |
|--------------|----------------------|--------------------------------|-------------------|
| fully_reversible | Low | - | `defer_with_condition` |
| fully_reversible | High | Yes | `escalate` |
| fully_reversible | High | No | `low_confidence_proceed` |
| reversible_with_cost or worse | Low | - | `defer_with_condition` |
| reversible_with_cost or worse | High | Yes | `escalate`；若來不及則 `hard_stop` |
| reversible_with_cost or worse | High | No | `hard_stop` |

如果 reviewer 在 `reversible_with_cost` 或更高風險情況下直接選 `low_confidence_proceed`，又沒說明為何 external validation 無法取得，就代表 protocol 沒有被正確套用。

---

## Genuine Deferral 與 Avoidance 的區分

兩者表面上都可能表現成「現在先不做決策」。  
但 avoidance 偽裝成 epistemic caution，是一種治理失敗。

genuine deferral 必須同時滿足四件事：

1. **明確點名 boundary condition**  
2. **明確寫出 resolution condition**  
3. **有 deadline 或 trigger**  
4. **deferral 本身可被 falsify**

常見 avoidance pattern：

### Pattern：We need more evidence

如果講不出「哪種 evidence」算足夠，這不是 deferral，只是 avoidance。

### Pattern：The situation is complex

如果無法回答「到底是 B1、B2、B3、B4 還是 B5」，那 complexity 只是煙霧。

### Pattern：We'll revisit when we have more data

若講不出：
- 什麼 data
- 何時
- 誰去拿

這不是 genuine deferral。

---

## Deferral Pressure

形式上可 falsify、但實務上從未被檢查的 deferral，在效果上和 avoidance 沒差別。

### Deferral decay rule

若一筆 `defer_with_condition` 連兩個 observation window 都沒被拿出來檢查 resolution condition，就必須：

- 明確 review 它
- 要嘛 renewal（附新 evidence）
- 要嘛轉成 `low_confidence_proceed`
- 要嘛 `escalate`
- 要嘛 `hard_stop`

### Deferral registry requirement

每次 window close 時都要回答：
- 目前有幾筆 open deferral
- 每筆什麼時候開的
- 它們的 resolution condition 是否真的有被檢查

### Maximum deferral age

同一 deferral 若已 renew 超過兩次，表示它在現有 observation model 中基本上已經 stuck。  
此時不能再繼續 renewal，而應轉 `escalate` 或 `hard_stop`。

### Evidence-gain condition for renewal

renewal 不是「時間過了」就成立。  
它至少要能說出：

1. 這個 window 內有哪些新 evidence 類型出現
2. 為何這些 evidence 仍不足以解決問題
3. 下一個 window 期待出現什麼這次還沒有的東西

如果答不出來，這不是 evidence-based renewal，只是 time-based extension。

---

## Re-entry Conditions

boundary condition 解開的條件大致是：

- B1：需要的 evidence 終於拿到了，或 observation structure 擴到能產出它
- B2：終於能為 decision 寫出正向 falsifiability condition
- B3：failure 從 `cause_unknown` 進展到 `cause_suspected`
- B4：conflict 被 precedence 或 adjudication 消化掉
- B5：decision scope 被拉回 observation model 內，或 scope boundary 被正式畫清楚

boundary condition 一旦解除，原 decision 必須被明確 reopen 與 re-evaluate。  
它不會自動變成 pass。

---

## 與 Observation Model 的關係

boundary crossing protocol 是 operational layer。  
它對應的是一個更底層的事實：

> 系統有 observation model，而有些 failure 天生就在 observation model 之外。

protocol 做不到把 invisible failure 變 visible。  
它做的是：當系統碰到 invisible zone 時，至少要有一致、可記錄的行為。

---

## Invisible Zone Response

有些 failure mode 天生是 structurally invisible：  
即使發生，也不會在現有 observation model 中產生可觀測 signal。

當這種 invisible zone 被點名出來時，不能只承認風險，卻什麼都不做。  
至少要從以下 response 中擇一：

### Response 1：Forced exploration

主動設計一個情境，讓原本 invisible 的 failure 如果存在，就有機會產生 observable signal。

### Response 2：External audit

若 framework 自己沒有足夠觀測能力，就引入外部 reviewer / 審核機制。

### Response 3：Documented risk acceptance

若既無法 forced exploration，也無法 external audit，就只能誠實記錄：

- 這個區域目前不可觀測
- 我們選擇承擔什麼風險
- 為什麼現在不做更多

---

## Governance Fitness Function

這份 protocol 不只規範 boundary reaction，也隱含一個 system fitness 問題：

治理到底有沒有往對的方向變？

最低限度應定期看四種指標：

1. post-change recurrence 是否下降
2. false positive rate 是否可觀測且受控
3. exploration cost 是否穩定
4. established category 中的 mandatory change rate 是否下降

### Priority ordering（預設）

1. **post-change recurrence declining**
2. **false positive rate bounded**
3. **exploration cost stable/declining**
4. **mandatory change rate declining**

若 priority 1 沒滿足，其他三項再好都不能當成健康證據。

### Fitness function self-revision trigger

若相鄰 priority 的兩項指標連續三次 review 都朝相反方向走，且沒有穩定下來，就應提出 meta-question：

> 現在的 priority ordering 本身，是否正在產生錯的 tradeoff？

這是對 fitness function 自己的 re-evaluation，不是對單一 proposal 的 re-evaluation。

---

## Historical Inertia And The Right To Forget

一條 constraint 若連續多個 observation window 都沒有被碰到，不代表它被驗證了，只代表它沒被測到。

### Untested constraint rule

若某 constraint / zone / calibration update 三個 window 都沒被 relevant activity 測到，就必須主動 re-evaluate：

- renew with evidence
- retire as obsolete
- retire as untestable

### 什麼情況該 discard

下列情況可以考慮把 constraint 從 active governance record 移出：

1. triggering pattern 已被證明 misattributed
2. category 已改版，舊 constraint 不再對應現況
3. constraint 已被更精確版本取代
4. 已超過五個 window 沒被測到，而且看不出未來會再測到

### 什麼情況不該忘

若 constraint 屬於 high-consequence category，而且原始 failure mode 仍可能發生，即使最近沒測到，也不應隨便 retire。

但這個保留決定必須基於 observable indicator，而不是只靠推理。  
若 retention 只能靠不可驗證推理鏈支撐，就應標成 `low_confidence_proceed`，而不是假裝已被確認。

---

## System Value Function：When Learning And Forgetting Conflict

有時 learning（加 constraint）與 forgetting（移除 constraint）會在同一 category 同時被觸發。

此時的預設 priority rule 是：

> forgetting 先評估  
> learning 再在新的 baseline 上評估

原因是：
- 在錯誤舊 constraint 上再疊新 constraint，最容易產生難拆的 over-constraint
- 先清 baseline，才能知道新 constraint 是否真的需要

### 何時不適用這條 priority rule

在 high-consequence、low-entropy category 中，under-constraint 的代價可能高到不可接受。  
這時可明文 override，先做 learning，再把 forgetting 延後。

但這個 override 一定要在 decision time 記錄。  
沒記錄就不算 override，只算 priority violation。

### System personality as an observability artifact

這條 priority rule 的更深含義是：

> 系統能偵測什麼、較難偵測什麼，最後會慢慢塑造系統的「性格」。

framework 比較容易抓到 under-constraint 還是 over-constraint，會直接影響它之後偏向保守、還是偏向保留決策流動性。

這不是 bug，而是 observability architecture 的自然結果。  
重要的是把它講出來，而不是假裝系統完全中性。

---

## What This Protocol Does Not Do

這份 protocol 不會：

- 擴充 observation model 本身
- 自動讓 invisible failure 變可見
- 取代 reviewer 對 boundary condition 的識別 judgment

它治理的是：

> 當 boundary 被識別出來之後，系統該怎麼一致地行動

---

## Terminal Condition：The Honest Limit

這套系統能保證的包括：

- 不允許 silent failure
- 不允許 silent bias
- 不允許無成本逃避

但它做不到、且任何 observation-bounded system 都做不到的是：

> 一個尚未產生 observable signal 的 failure，現在還無法被治理

latent flaw、極端 edge case、尚未出現的 failure mode，都可能仍在 protocol 外部。

這不是設計失敗，而是任何以 observation 為基礎的治理系統都必須誠實承認的 terminal condition：

> 一旦某件事被命名、被看見，它就不能再保持 ungoverned。  
> 但在被命名之前，它真的仍在 authority 之外。
