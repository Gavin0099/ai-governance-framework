# Boundary Protocol Test Pack

> Covers commits: `f0a9935` -> `e6f73d3`
> Scenario count: 16（Parts A-F）
> Scenario IDs: `A.1`, `A.2`, `B.1`, `B.2`, `B.3`, `C.1`, `C.2`, `C.3`, `D.1`, `D.2`, `E.1`, `E.2`, `F.1`, `F.2`, `F.3`, `F.4`
> Passing score:
> - `14-16`：strong pass
> - `11-13`：marginal pass，重看 Part C、D、F
> - `<11`：fail
> Documents under test:
> - `docs/boundary-crossing-protocol.md`

Prerequisite：建議先熟悉 `docs/learning-governance-test-pack.md`。  
這份 pack 是 **conformance test**，不是 adversarial pack。邊界辨識的 adversarial 測試在 `docs/adversarial-test-scenarios.md` Part D。

**Schema integrity check：**
- [ ] manifest 中的 scenario count = 文件中的實際 scenario 數
- [ ] score band 上限 = scenario count
- [ ] `boundary-crossing-protocol.md` 中每個 enforceable mechanism 都至少對應一個 scenario
- [ ] verdict 不引用已被移除的機制

---

## 如何使用

每個 scenario 都給你一個輸入情境，要求你做 judgment call。  
看完 scenario 先自己寫答案，再打開 `Verdict` 比對。

若你的答案和 verdict 不同，不要立刻假設自己錯。也可能是 verdict 本身有問題。  
真正的分歧應記錄下來。

---

## Part A：Boundary condition recognition and response types

### Scenario A.1

reviewer 被要求評估一個 proposal，想把 framework scope 擴到新的 decision category。  
proposal 只引用了一次 incident 當證據，reviewer 也找不到其他 log、proposal 或可觀測 activity。

reviewer 寫道：

> There's only one data point here. I can't tell if this is a genuine pattern or a one-off. I'll approve it cautiously.

**問題：**  
reviewer 是否正確辨識 boundary condition？如果沒有，錯在哪裡？應採哪種 response type？

<details>
<summary>Verdict</summary>

**沒有。**

這是典型 B1：evidence 仍低於 observability threshold。  
reviewer 雖然感覺到 evidence 很薄，但直接用 `low_confidence_proceed`，卻沒有完成必要條件：

1. 明確點名 B1 boundary condition
2. 寫出可觀測的 re-evaluation trigger
3. 讓未來 reviewer 看得到這次 decision 是在 B1 下做的

`I'll approve it cautiously.` 只表達態度，沒有把低信心決策可觀測化。

</details>

### Scenario A.2

framework 從未遇過某 failure mode。proposal 用類比方式，想把它比照另一個已知 failure mode，直接判成 `medium-severity`。

reviewer 寫：

> This is analogous to X, which we've classified as medium-severity. I'll classify this as medium-severity too.

**問題：**  
是否有 boundary condition 被觸發？缺了什麼？

<details>
<summary>Verdict</summary>

**有，這是 B3。**

reviewer 正在對一個尚未進 observation model 的 failure mode 直接做分類，且沒有給出任何 resolution path。  
類比分類可以做，但至少要補：

1. 承認這是 analogical，不是 observational classification
2. 指出什麼 observation 會支持 / 反駁這個 analogy
3. 把這次分類標成 provisional，而不是 established precedent

</details>

---

## Part B：Deferral genuineness

### Scenario B.1

reviewer 寫：

> This proposal raises complex questions about how we handle cross-domain failures. I'm deferring pending further review by the framework team.

**問題：**  
這算 genuine deferral 嗎？

<details>
<summary>Verdict</summary>

**不算。**

它失敗在四件事：

1. 沒有點名具體 boundary condition
2. 沒有明確 resolution condition
3. 沒有 deadline
4. deferral 自己也不可被 falsify

這是 avoidance，不是 deferral。

</details>

### Scenario B.2

第一份 deferral 很完整，引用 B2，並說若 observation window 5 結束仍無 instrumentation，就改走 `low_confidence_proceed`。  
三個 window 過去後仍沒有 instrumentation，reviewer 卻又用同樣理由再 defer 一次。

**問題：**  
第二次 deferral 是否有效？

<details>
<summary>Verdict</summary>

**無效。**

這不是 renewal，而只是 extension。  
原本已承諾 instrumentation 若仍缺失，就該轉成 `low_confidence_proceed`。  
沒有 evidence gain 的 deferral 不能無限續延。

</details>

### Scenario B.3

proposal 第三次被 defer。reviewer 說：

> this is important enough that proceeding without resolution feels wrong

**問題：**  
第三次 deferral 可接受嗎？

<details>
<summary>Verdict</summary>

**不可接受。**

當 boundary condition 經過兩輪 renewal 仍無法解決，就不能再用 deferral 把它無限往後推。  
此時 reviewer 必須在以下選項中做出更正式的 response：

- `low_confidence_proceed`
- `escalate`
- `hard_stop`（僅限符合 irreversibility threshold）

</details>

---

## Part C：Deviation accumulation and outcome downstream closure

### Scenario C.1

同一 category 中，兩次都出現 `defer_with_condition` 缺 deadline 的 deviation。  
periodic reviewer 卻說：

> 先看第三次再說

**問題：**  
這個 tier 判斷對嗎？

<details>
<summary>Verdict</summary>

**不對。**

兩次 deviation 就已跨過 Diagnostic，進入 Operationalized tier。  
這時就該啟動 constraint inventory，而不是等第三次。

</details>

### Scenario C.2

一個 `drift_confirmed` outcome 對應的 policy change 被記錄了。六週後，pattern 沒再發生。reviewer 就寫：

> Pattern resolved. Loop closed.

**問題：**  
loop 真的關了嗎？

<details>
<summary>Verdict</summary>

**還沒有。**

只證明 pattern 不再 recurrence，還不夠。  
還需要說清楚：

- downstream effect 是什麼
- policy change 到底改變了什麼
- reviewer 再遇到同樣情況時，行為會有什麼不同

</details>

### Scenario C.3

同一 category 連續三次都出現 `cost_legitimate` outcome，但沒有任何 `structurally_inaccessible` marking。

**問題：**  
reviewer 直接說「外部 constraint 本來就很多」，這樣夠嗎？

<details>
<summary>Verdict</summary>

**不夠。**

這種 pattern 也可能表示 outcome selection bias。  
reviewer 必須補出：

- 為何沒有 `structurally_inaccessible`
- 或正式指出 `cost_legitimate` 被錯當 terminal classification 使用

</details>

---

## Part D：Baseline validity and domain entropy

### Scenario D.1

某 category 在 window 3 被標成 high-entropy，理由只有：

> This category has always been noisy.

現在已到 window 9。

**問題：**  
這個 high-entropy designation 還能直接拿來用嗎？

<details>
<summary>Verdict</summary>

**不能直接用。**

需要重新檢查：

1. window 3 當時的治理條件本身是否失真
2. 這個 designation 是反映 domain 真實 entropy，還是反映當時 measurement noise

</details>

### Scenario D.2

category 沒有 established entropy baseline。window 5 做了 policy change，window 6 和 7 pattern 仍持續。reviewer 就想直接 trigger misattribution re-examination。

**問題：**  
這樣對嗎？

<details>
<summary>Verdict</summary>

**不對。**

在 unknown-entropy category 中，兩個 window 的 persistence 還不足以證明 misattribution。  
更合理的回應是延長 observation，先開始建立 baseline。

</details>

---

## Part E：Fitness function and self-revision

### Scenario E.1

四個 priority 中，1、2、4 都健康，只有 3（exploration cost）持續上升四個 window。reviewer 因為 priority ordering，判成 acceptable。

**問題：**  
這個結論完整嗎？

<details>
<summary>Verdict</summary>

**不完整。**

priority ordering 的應用本身沒有錯，但四個 window 的 persistent divergence 已足以觸發更高一層的 meta-question：

> 這個 priority ordering 本身，是否正在產生不想要的 tradeoff？

</details>

### Scenario E.2

count recurrence 下降，但 severity-weighted recurrence 上升。reviewer 卻說：

> Priority 1 satisfied.

**問題：**  
這樣對嗎？

<details>
<summary>Verdict</summary>

**不對。**

Priority 1 應以 severity-weighted recurrence 為準，不是只看 count recurrence。  
count 下降、severity 上升，通常表示系統只清掉了低嚴重度噪音，沒有打到高後果問題。

</details>

---

## Part F：`low_confidence_proceed` expiry and system value function

### Scenario F.1

一個 `low_confidence_proceed` tag 兩個 window 都沒有遇到 re-evaluation trigger，現在已到第三個 window。

**問題：**  
這個 tag 還有效嗎？

<details>
<summary>Verdict</summary>

**已失效。**

兩個 window 內未達 trigger，就必須進 mandatory re-evaluation。  
不能只是因為 activity 少，就無限保留這個 tag。

</details>

### Scenario F.2

同一 category 同時出現：
- forgetting 需要 re-evaluate
- learning 已達 Enforced tier

reviewer 先做 learning，說 forgetting 之後再處理。

**問題：**  
這符合 system value function 嗎？

<details>
<summary>Verdict</summary>

**不符合。**

預設規則是：

> forgetting 先，learning 後

因為在不乾淨 baseline 上先加新 constraint，通常會讓 over-constraint 更難拆。

</details>

### Scenario F.3

若 category 已被明確記錄為 high-consequence、low-entropy，reviewer 是否可 invoke override，改成 learning 優先？

<details>
<summary>Verdict</summary>

**可以，但必須在 decision time 明確記錄 override。**

若沒有文件記錄，這不是 override，而是無紀錄的 priority violation。

</details>

### Scenario F.4

reviewer 因鄰近 category 的推理，認為某 constraint 觸發條件「大概還存在」，就直接 renew constraint。

**問題：**  
condition observability requirement 有被滿足嗎？

<details>
<summary>Verdict</summary>

**沒有。**

由鄰近 category 推理出來的「大概還存在」，不是可觀測條件。  
若沒有直接可觀測 indicator，這種 renew 最多只能算 `low_confidence_proceed`，不能假裝已被確認。

</details>

---

## Score Interpretation

| Score | Interpretation |
|-------|---------------|
| `14-16` | Strong pass，代表機制已能穩定操作 |
| `11-13` | Marginal pass，應重看 Part C、D、F |
| `8-10` | Partial pass，通常 accumulation tier 或 expiry discipline 判錯 |
| `<8` | Fail，應回頭重讀 `docs/boundary-crossing-protocol.md` |

## Common Error Patterns

- 把 deviation accumulation 用錯 tier
- 把 `low_confidence_proceed` 當成無期限標記
- 把 learning / forgetting priority 顛倒
- 用 count recurrence 取代 severity-weighted recurrence
