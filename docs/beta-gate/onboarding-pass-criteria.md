# Human Self-Serve Onboarding Pass/Fail Criteria

> 狀態：active
> 建立：2026-03-30
> 適用：Beta Gate condition 2 的 human self-serve track

---

## 為什麼需要這份文件

「reviewer 能不能自己搞懂」這句話太抽象，不能直接當 gate。這份文件的作用就是把它拆成可觀測、可記錄、可比較的 checkpoint。

這份文件只適用於 **human cold-start self-serve** gate。

Agent-assisted adoption 另有獨立文件：

- `docs/beta-gate/agent-adoption-pass-criteria.md`

也就是說：

- human self-serve failure 不會自動否定 agent-assisted path
- 兩者是不同 gate，不是同一條路的高低難度版

---

## 五個可觀測 checkpoint

### CP1：找到入口

**Observable**：reviewer 能在沒有被提醒的情況下，自己導航到：

- `README.md`
- `docs/start_session.md`
- 或 `governance_tools/adopt_governance.py`

Pass：15 分鐘內找到入口。
Fail：15 分鐘後仍停在 repo root，沒有方向。

---

### CP2：能描述最小 adopt path

**Observable**：reviewer 能用自己的話描述出：

> adopt -> drift check -> session_start -> pre_task -> post_task

不要求他背精確指令，但至少要理解這是一條 runtime path，不只是靜態文件集合。

Pass：reviewer 能主動說出這條概念流程。
Fail：reviewer 以為 framework 只是 documentation set。

---

### CP3：核心概念有分清楚

**Observable**：reviewer 能分辨至少 2 組：

- framework governance（本 repo） vs project governance（consuming repo）
- `governance_tools/`（你主動跑的工具）vs `runtime_hooks/`（session 中會跑的 hook）
- domain contract（特定專案適用的規則）vs rule pack（較通用的規則集合）

Pass：至少 2 組 distinction 能在無提示下說對。
Fail：把所有東西當成同一層扁平文件系統。

---

### CP4：理解 drift detection 的存在與用途

**Observable**：給 reviewer 一個情境：「兩週後你回來看這個 project」，他知道 `governance_drift_checker` 存在，且能說出它大致在檢查什麼。

Pass：reviewer 能自己找到或描述 drift checker。
Fail：reviewer 不知道 returning session 要怎麼驗 governance health。

---

### CP5：產生至少一個 governance artifact

**Observable**：reviewer 有跑或至少做出具體嘗試，對下面任一條：

- `python -m governance_tools.adopt_governance`（temp directory）
- `python -m governance_tools.governance_drift_checker`（某 repo）
- 手動 `session_start`（某 example contract）

Pass：有 artifact 產生，或嘗試本身是實質的（有跑指令、有看懂輸出）。
Fail：連任何工具執行都沒走到。

---

## 計分

| CPs passed | Result |
|-----------|--------|
| 5 of 5 | Strong pass — Beta Gate condition 2 met |
| 3–4 of 5 | Pass — Gate met，但要記錄哪些 CP 失敗，作為 onboarding 改善輸入 |
| 2 of 5 | Fail — Gate not met，必須診斷 blocker |
| 0–1 of 5 | Fail — entry path 仍需明顯重工 |

---

## Gate override 規則

分數不是唯一判準，下列 override 會直接蓋過 score table。

| Condition | Override | Reason |
|-----------|----------|--------|
| CP5（artifact production）失敗 | Automatic FAIL | 這個 framework 的核心主張之一是 governance 能產出可驗證 evidence。如果 onboarding 連任何 artifact 都產不出，這個主張就無法被驗證。 |

套用 override 時，要在 reviewer run 檔案中明確寫：

```text
Gate Verdict: FAIL
Override applied: CP5 automatic FAIL rule
Score-based result: X/5 (would have been: Pass / Fail)
```

不要在 override 已觸發時，還默默沿用 score-based result。

---

## Blocker 分類

當 reviewer fail 某個 checkpoint，要先分類 blocker，而不是直接大改 framework。

先用：

- `docs/beta-gate/reviewer-signal-split.md`

判斷這次失敗比較接近 discoverability、interpretation、decision reconstruction，還是 escalation judgment。

再往下可歸成：

| Type | Description | Implication |
|------|-------------|-------------|
| **Conceptual** | reviewer 不懂這個東西是做什麼的 | 需要更好的解釋或例子，不一定要重構 |
| **Structural** | reviewer 找不到對的檔案或工具 | entry path / README 需要更清楚的 pointer |
| **Naming** | reviewer 找到對的東西，但誤會其用途 | 名稱或標題需要修正 |
| **Friction** | reviewer 懂，但跑不起來 | tooling / quickstart / dependency path 要修 |

一個 blocker type 對應一個 targeted fix。不要為了修 naming 問題去重寫整個 framework。

---

## 哪些不算 failure

以下情況不算 fail：

- reviewer 閱讀順序和預期不同
- reviewer 一開始跑錯工具，但後來修正
- reviewer 問 AI/governance 理論問題，而不是 framework mechanics
- reviewer 花超過 60 分鐘，但最後仍成功達到 pass criteria

這個 gate 在意的是：能不能抵達，不是是不是以最短路徑抵達。
