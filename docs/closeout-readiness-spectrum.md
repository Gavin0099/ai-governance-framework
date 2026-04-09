# Closeout Readiness Spectrum

> Version: 1.1
> Related: `docs/closeout-repo-readiness.md`, `docs/session-closeout-schema.md`

---

## 目的

這份文件把 session closeout governance 的 readiness 拆成四個 level。

原因很簡單：只用「ready / not-ready」無法描述從 stop hook 接通，到 closeout 真正可驗證之間的差距。

readiness level 描述的是：

> 一個 repo 目前具備哪些 closeout governance capability

它不描述：
- 團隊成熟度
- 工程品質
- AI 使用品質

---

## 兩個獨立維度

readiness output 應至少帶兩個互不相混的值。

### `repo_readiness_level`（0-3）

這是**結構能力**，由檔案、設定、程式路徑決定，而不是由 session 歷史決定。  
repo 即使剛完成 `upgrade_closeout`，也可能立刻具備結構上的 Level 3。

### `closeout_activation_state`

這是**是否曾在實務上觀測到 closeout loop 被跑起來**。

| Value | Meaning |
|-------|---------|
| `observed` | 至少已有一份 verdict artifact，代表 loop 曾被跑過 |
| `pending` | 結構條件已就緒，但尚未觀測到任何 run |
| `unknown` | 結構層級太低，無法有意義地談 activation |

### `activation_recency`

只在 `activation_state=observed` 時才有意義。

| Value | Meaning |
|-------|---------|
| `recent` | 最近一份 verdict artifact 的 mtime 在 30 天內 |
| `stale` | 有 verdict artifact，但最近一份已超過 30 天 |

**`recent` 真正檢查的是什麼？**  
它只看最近一份 verdict artifact 的檔案 mtime。  
它不表示最近 closeout 都是 `valid`，也不表示治理品質健康。

換句話說：
- `observed` 只代表曾經觀測過
- `recent` 只代表最近曾被觸發
- 兩者都不是 trustworthiness 保證

### 為什麼要和 structural level 分開？

因為 repo 可能是：
- 結構上已完整（例如 Level 3）
- 但 activation 還是 `pending`

如果把「沒有歷史 artifact」誤算成 structural deficiency，就會混淆：
- capability
- activation history

`prior_verdict_artifacts_exist` 是 activation signal，不是 structural signal。

---

## Reviewer Action Mapping

下表是 reviewer workflow guidance，不是 runtime decision rule。

| State combination | Expected reviewer action |
|-------------------|--------------------------|
| `pending` | 至少要求一個有記錄的 closeout session，最小標準是產生一份帶 `closeout_status` 的 verdict artifact。即使是 `closeout_missing` 也算，因為它證明 hook 確實被觸發。 |
| `observed/recent` | 仍需打開個別 verdict artifact 檢查，不可把 `observed/recent` 誤讀成 closeout 品質健康。 |
| `observed/stale` | 先依序排查：1. wiring 是否斷了；2. 最近是否根本沒有 session；3. 是否 adoption 已停止。不要直接跳到「團隊不用了」這種解釋。 |
| `unknown` | 先補 artifact 路徑與 structural prerequisites，再談 activation。 |

**Authority boundary：**  
這張表只給 reviewer 工作流參考，不能影響：
- verdict classification
- allow / deny
- memory promotion

activation state 是 reviewer 問題導向，不是 decision input。

---

## 已知未補的 gap：activation quality

目前模型回答了三個問題：

1. repo 是否具備結構能力？  
2. closeout loop 是否曾被觀測到？  
3. 最近是否仍有被觸發？

但它**還沒回答第四個問題**：

4. 最近 closeout 的品質如何？

一個 repo 可能 `observed/recent`，但最近十次全部都是 `closeout_missing`。  
現有模型無法把這類 repo 和「最近都能穩定產出 valid closeout」的 repo 區分開來。

這個缺口目前是刻意保留的。  
只有當 reviewer 持續回報 `observed/recent` 對 repo 健康度的判讀產生誤導時，才值得新增 `recent_closeout_quality` 類維度。

在那之前，activation state 只用來回答：
- loop 是否被跑過
- 最近是否還有被跑

不回答品質。

---

## Hard Rules

### Rule 1：Level 來自 capability checklist，不來自單一條件

repo 不是因為「有 AGENTS.base.md」就算 Level 2。  
只有在對應 checklist 都成立時，才算該 level。

### Rule 2：Level 不回流成單一 session 的 decision input

readiness level 可以出現在 verdict metadata，幫 reviewer 提供背景。  
但它不能反過來影響：
- `session_end_hook` classification
- memory promotion
- verdict 決策邏輯

### Rule 3：Readiness level 不是 maturity score

Level 3 只代表 cross-reference capability 已接上。  
它不代表：
- 團隊比較成熟
- AI 比較可靠
- 程式碼品質比較高

不能拿 readiness level 當 KPI。

### Rule 4：Progression 是 capability expansion，不是強制升級路線

repo 若長期停在 Level 2，並不等於失敗。  
Level 3 適合需要 cross-reference 的 repo；如果 repo 的穩態只需要 Level 2，就不應為了數字好看硬升級。

---

## Level 0：Hook Entry Only

stop hook 已能呼叫 `session_end_hook`，但其他事情都尚未保證。

**Capability checklist：**
- [ ] `python -m governance_tools.session_end_hook --project-root <repo>` 可執行
- [ ] 已設定 stop hook，或至少有手動執行路徑
- [ ] `artifacts/` 可寫

**支援：**
- stop-time entry into closeout pipeline
- degraded verdicts（如 `closeout_missing`）被記錄

**不支援：**
- canonical closeout production 的穩定品質
- content validation
- memory update

---

## Level 1：Canonical Closeout Ready

repo 已具備合法 closeout schema 的基本條件，AI 也有機會依 schema 產出 structurally valid closeout。

**Capability checklist（Level 0 +）：**
- [ ] `docs/session-closeout-schema.md` 可被引用
- [ ] `AGENTS.base.md` 含 `Session Closeout Obligation`
- [ ] `artifacts/session-closeout.txt` 可寫
- [ ] AI 能在 closeout 時看得到七欄 schema

**支援：**
- `schema_valid` closeout 有可能出現
- `session_end_hook` 能分類 `presence` / `schema_validity`
- verdict artifact 穩定產出

**不支援：**
- content sufficiency 仍不穩
- evidence cross-reference 尚未有實質意義

---

## Level 2：Content-Governed Closeout

repo 已把 pre-validation guidance 和 runtime judgment 對齊。  
AI 在寫 closeout 之前，已能知道什麼叫 content insufficient。

**Capability checklist（Level 1 +）：**
- [ ] `AGENTS.base.md` 的 closeout obligation 包含 content rules
- [ ] 明列 observable anchor：需點名檔案、工具、命令
- [ ] 明列 vague phrases 為不合法寫法
- [ ] `NOT_DONE` / `OPEN_RISKS` 不能在壓力下被省略
- [ ] verdict artifact 可觀測 `failure_signals` 與 `per_layer_results`

**支援：**
- `content_sufficient` closeout
- `working_state_update` memory tier 開始有意義
- reviewer 能用 `failure_signals` 快速定位缺口
- 空泛造假比較容易被抓到

**不支援：**
- 只靠語法上看似真實的檔名，仍可能混過去
- `CHECKS_RUN` 若只寫了名稱，仍可能缺乏真 evidence

---

## Level 3：Cross-Referenced Closeout

repo 已接上 filesystem / artifact cross-reference，`FILES_TOUCHED` 與 `CHECKS_RUN` 不再只靠 AI 自述。

**Capability checklist（Level 2 +）：**
- [ ] `FILES_TOUCHED` 會在 session end 檢查檔案是否存在
- [ ] `CHECKS_RUN` 的工具名稱會對應到預期 artifact 路徑
- [ ] verdict artifact 會帶 `cross_reference_results`
- [ ] `working_state_update` / `verified_state_update` 的 distinction 已啟用

**支援：**
- `evidence_consistent` closeout
- `verified_state_update` memory promotion 有 evidence prerequisite
- syntactic gaming 的成本提高
- reviewer 可看到更具體的不一致信號

**不支援：**
- proof of execution
- 完全防止惡意 agent 造假
- 語意正確性的保證

**重要說明：**  
目前 framework 中，cross-reference capability 一旦 structural prerequisites 成立，基本上就和 Level 2 一起存在。  
是否真的在實務上被觀測到，要看 `closeout_activation_state`，不是看 structural level。

---

## Progression Path

```text
Level 0                -> Level 1                 -> Level 2                  -> Level 3
Hook entry only           Schema available           Content governed            Cross-referenced
                           AGENTS.base.md            pre-validation              file + tool check
                           7-field schema            observable anchors          artifact signals
                           writable artifact path    failure_signals             working/verified split
```

---

## 與 Memory Promotion 的關係

| Repo level | 常見 memory tier | 說明 |
|-----------|------------------|------|
| Level 0 | `no_update` | 通常 schema 都還沒建立好 |
| Level 1 | `no_update` 或 `working_state_update` | schema 開始成立，但內容常常不夠 |
| Level 2 | `working_state_update` | 內容較可信，但 evidence 仍偏弱 |
| Level 3 | `working_state_update` 或 `verified_state_update` | 取決於單次 session 結果 |

**這是常見結果，不是硬映射。**  
memory tier 永遠由單次 session 的 closeout classification 決定，不由 repo readiness level 直接決定。

---

## 如何檢查 repo 目前在哪個 level

```bash
# Step 1：session_end_hook 能不能跑
python -m governance_tools.session_end_hook --project-root <your-repo> --format human

# Step 2：AGENTS.base.md 是否有 closeout obligation
grep -c "Session Closeout Obligation" <your-repo>/AGENTS.base.md <your-repo>/AGENTS.md 2>/dev/null

# Step 3：手動寫一份測試 closeout
cat > <your-repo>/artifacts/session-closeout.txt << 'EOF'
TASK_INTENT: test content validation
WORK_COMPLETED: updated main.py to fix edge case handling
FILES_TOUCHED: NONE
CHECKS_RUN: NONE
OPEN_RISKS: NONE
NOT_DONE: NONE
RECOMMENDED_MEMORY_UPDATE: NO_UPDATE
EOF

python -m governance_tools.session_end_hook --project-root <your-repo> --format human
```

判讀：
- `content_sufficiency=sufficient`：可視為 Level 2 候選
- 有 `cross_reference_results`：可視為 Level 3 候選

---

## `working_state_update` 的定位

`working_state_update` 不是 degraded tier，也不是應被避免的 dirty 狀態。  
它是持續工作現況的主要載體。

更準確地說：

> working_state 是 ongoing reality 的主要承載層  
> verified_state 是 high-confidence subset

如果一個 repo 穩定產生 `working_state_update`，那通常比「因 verified 門檻過高而什麼都不更新」更有價值。

---

## Cross-reference 是 inconsistency signal，不是 verification

cross-reference 的作用是**提高造假成本**，不是保證 claim 為真。

檔案存在，不代表本次 session 真的有做出有意義的修改。  
artifact 存在，也不代表它一定屬於這次 session。

所以 Level 3 的保證是：
- 沒有發現可檢出的不一致

而不是：
- 所有內容都已被證明正確

---

## Non-Goals

- readiness level 不是分數或等級制度
- higher level 不代表「治理更好」
- Level 3 也無法阻止有意識的高成本造假
- 這份 spectrum 不取代 verdict artifact 本身
- readiness level 可出現在 metadata，但不得回流成 decision input
