# Closeout Readiness Spectrum

> 版本：1.1  
> 關聯文件：`docs/closeout-repo-readiness.md`、`docs/session-closeout-schema.md`

---

## 目的

這份文件把 session closeout governance 的 readiness 拆成幾個不同層次，避免簡化成只有 `ready / not-ready`。

核心觀點是：
> 一個 repo 是否具有 closeout governance capability，不該只看它有沒有 stop hook 或 closeout artifact，而要看它是否具備可持續、可重建、可觀測的 closeout 路徑。

這份分層同時服務：
- adopter 判讀
- reviewer 判讀
- AI agent 的 repo 狀態理解

---

## 核心欄位

### `repo_readiness_level`（0–3）

這個欄位描述的是**結構 readiness**，不是單次 session 是否成功。

- Level 0：沒有 closeout 結構
- Level 1：有部分 wiring，但無法穩定產出 closeout
- Level 2：已有可觀測 closeout loop，但仍不穩定
- Level 3：closeout 路徑穩定、可觀測、可被 reviewer 重建

### `closeout_activation_state`

這個欄位描述的是**最近是否有觀測到 closeout loop 被實際啟動**。

| Value | Meaning |
|---|---|
| `observed` | 有至少一份 verdict / summary artifact 顯示 closeout loop 已跑過 |
| `pending` | 結構已具備，但尚未看到實際 closeout run |
| `unknown` | 無法判定是否曾經成功啟動 closeout |

### `activation_recency`

只在 `activation_state=observed` 時有意義。

| Value | Meaning |
|---|---|
| `recent` | 最近一段時間內有新的 verdict artifact（例如 30 天內） |
| `stale` | 過去曾觀測過，但最近已久未更新 |

注意：`recent` 不是 trustworthiness 的保證。  
它只表示「最近看過 closeout loop 被跑起來」，不表示 closeout 一定有效、完整或值得 promote。

---

## Structural Level 與 Activation 的差別

需要明確分開：
- repo 結構 readiness 很高，但 activation 仍可能是 `pending`
- 也可能看過 artifact，但仍不代表結構完整

因此 `prior_verdict_artifacts_exist` 只能算 activation signal，不是 structural signal。

---

## Reviewer Action Mapping

這裡提供的是 reviewer workflow guidance，不是 runtime decision rule。

| State combination | Expected reviewer action |
|---|---|
| `pending` | 確認 wiring 是否已接好，並安排一次真實 closeout session；若 artifact 顯示 `closeout_missing`，應先檢查 hook / stop path |
| `observed/recent` | 確認最近 artifact 確實對應有效 closeout，而不是空跑 |
| `observed/stale` | 回頭檢查：1. wiring 是否仍在；2. 最近是否其實沒有真實 session；3. adopt / closeout lane 是否逐漸失活 |
| `unknown` | 先查 artifact 與 structural prerequisites，再決定是否把它視為 activation 缺口 |

**Authority boundary**  
這些欄位只用來幫 reviewer 判讀，不應直接決定：
- verdict classification
- allow / deny
- memory promotion

activation state 是 reviewer context，不是 decision input。

---

## 另一個 gap：activation quality

就算 activation 已被觀測到，仍要追問：
- closeout 是否有效
- closeout 是否完整
- closeout 是否只是空跑

因此 readiness spectrum 只是 capability / activation 的分類面，不是對 closeout quality 的最終裁決。

## 一句總結

`closeout readiness spectrum` 的目的，是把「有沒有 closeout」拆成 structural readiness、activation state 與 activation recency 三個不同面向，避免把 capability、歷史與品質混成一個欄位。
