# Misinterpretation Log

> 目的：記錄 reviewer 或 adopter 對治理訊號的典型誤讀，避免同一類誤判反覆發生。  
> **這不是 bug tracker。**  
> 這份記錄的重點，是保存哪些欄位或 surface 容易被錯讀，以及後來怎麼修正敘事或邊界。  
> **entry 先記 observation，再記 conclusion。**  
> 不要把單次誤讀直接包裝成 framework expansion argument；先看 evidence 是否足夠。

## 記錄模板

```text
### YYYY-MM-DD - <short description>

**Affected field:** repo_readiness_level | closeout_activation_state | activation_recency | reviewer mapping
**Misinterpretation type:** over-reading | under-reading | category confusion | decision leak
**Severity:** low | medium | high
**What was observed:** <reviewer/adopter 實際說了什麼、如何錯讀>
**What the field actually means:** <這個欄位真正的語義>
**Correction applied:** <doc update, code change, or no action>
**Resolution status:** doc_updated | training | ignored | requires_model_change | open
**Owner:** reviewer | team | framework
**Signal for model expansion:** yes | no | watch
```

## Entry Types

| Type | Description |
|---|---|
| `over-reading` | 把 signal 解讀得比它實際更強 |
| `under-reading` | 忽略 signal 已經具備的警示或限制 |
| `category confusion` | 把 structural level、activation state、quality、usage 混成同一件事 |
| `decision leak` | 把 activation state / readiness level 誤當成 verdict 或 memory promotion 依據 |

## Severity Levels

| Severity | Definition |
|---|---|
| `low` | 主要影響心理模型，不直接改變操作 |
| `medium` | 可能改變 reviewer action、triage 路徑或文件使用方式 |
| `high` | 已接近 decision boundary，可能影響 allow/deny、memory promotion 或 policy precedence |

### High-severity exception

只要某個誤讀已經碰到 decision boundary，或需要即時人工介入，就應視為 `high`。

### Severity judgment rule

是否影響 allow/deny、memory promotion 或 policy precedence，是判定 `high` 的主要依據。  
如果只是影響 triage 或心理模型，通常落在 `medium` 或 `low`。

### Semantic grouping rule

recurrence 的判定應以「同類誤讀」為主，而不是只看表面文字是否完全一樣。  
例如：
- `activation used as quality proxy`
- `activation used as usage signal`
- `activation used as decision input`

這些都屬於 activation boundary violation 的同一群 recurrence。  
但也不能 over-group，否則會把不同誤讀錯誤地合併，失去 trigger threshold 的意義。

## Resolution Status

| Status | Meaning |
|---|---|
| `doc_updated` | 已透過文件修正邊界 |
| `training` | 已透過 reviewer guidance / onboarding 修正 |
| `ignored` | 目前只屬 ambiguity，暫不擴張 |
| `requires_model_change` | 需要更深層的產品或模型調整 |
| `open` | 尚未處理完成 |

## 一句總結

`misinterpretation_log` 的作用，不是累積抱怨，而是把容易被錯讀的治理訊號結構化地記錄下來，讓後續的文件修正、training 與 boundary hardening 有依據。
