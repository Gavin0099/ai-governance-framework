# Agent Run Sheet

> Status: active
> Created: 2026-03-31
> Applies to: agent-assisted adoption runs

---

## 目的

這份文件定義 agent-assisted adoption run 的最小記錄結構。

目標不是寫一篇成功故事，而是留下：

- 可 replay
- 可 challenge
- 可 compare

的 run record。

它存在的目的，是讓 agent-assisted adoption 被評估成一種可審計的執行模型，而不是一次性的 demo。

---

## Inputs

請搭配以下文件一起使用：

- `docs/beta-gate/agent-adoption-pass-criteria.md`

可選支援文件：

- `docs/beta-gate/reviewer-signal-split.md`
- `docs/decision-boundary-layer.md`

---

## 最小 Run Record

每個 agent-assisted run record 至少要包含以下區塊：

### 1. Replay hint

```text
Replay hint:
- Repo commit:
- Agent identity:
- Minimal input framing:
- Primary documented path used:
```

### 2. Inputs consulted

```text
Inputs consulted:
- Files read:
- Contracts or rules used:
- Artifacts consumed:
```

### 3. Commands executed

```text
Commands executed:
- ...
```

### 4. Artifacts produced

```text
Artifacts produced:
- ...
```

### 5. Decision checkpoints

記下那些 agent 本來可能做出 unsafe / unverifiable move，但最後有沒有做的節點。

```text
Decision checkpoints:
- Checkpoint:
  - What decision was being made:
  - What evidence was available:
  - Outcome:
```

### 6. Non-action log

記下 agent **刻意沒有做** 的事。

```text
Non-action log:
- Did not invent missing spec
- Did not synthesize fake sample
- Did not rewrite unclear contract into a stronger claim
```

這一段必要，因為「沒有 overreach」通常不會自然留下痕跡，除非你主動記錄。

### 7. Inference classification

對每個 major decision，將 reasoning source 分類成：

- `direct_evidence`
- `derived_safe`
- `inferred_risky`

```text
Inference classification:
- Decision:
  - Classification:
  - Why:
```

### 8. Escalation points

```text
Escalation points:
- Where escalation occurred:
- Why escalation occurred:
- Was escalation consistent with documented authority boundaries? Y/N
```

### 9. Auditability judgment

```text
Auditability judgment:
- Can a human reconstruct this run from artifact + run sheet? Y/N/Partial
- If partial, what is missing?
```

### 10. Decision context summary

若本 run 產出 `runtime-verdict`、`runtime-trace` 或 `session_end` summary，且內含 `decision_context`，這裡要把它顯性記錄下來。

```text
Decision context:
- surface_validity:
- coverage_completeness:
- memory_integrity:
- Human-readable interpretation:
```

這一段的目的，是讓 reviewer 不必從 raw signal 自己硬推 context quality。

---

## Required Summary Block

```text
Agent adoption score:
- AC1:
- AC2:
- AC3:
- AC4:
- AC5:

Override:
- Applied: Y/N
- Reason:

Most important weakness:
- ...

Smallest next fix:
- ...
```

---

## Working Rule

如果一個 run 無法被 replay 或 challenge，就不能算 strong evidence。

若它只證明 agent 能摘要 repo 檔案，還不算證明 agent-assisted adoption 成立。
