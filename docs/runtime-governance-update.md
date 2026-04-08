# Runtime Governance 更新說明

更新日期：2026-04-08

這份文件原本記的是最早一版 runtime governance slice。現在保留它，主要是為了說明：repo 怎麼從單純文件型治理，走到目前的 bounded runtime。

## 這份更新在歷史上的位置

當時第一個真正落地的變化是：

- contract schema 開始帶 runtime-facing state
- `state_generator.py` 能輸出 runtime input
- `pre_task_check` / `post_task_check` 開始成為真實 hook
- `runtime_hooks/core/` 成為共享 runtime lane 的雛形

從今天回看，這一刀的意義不是功能很多，而是它把 repo 從：

- prompt-only governance

推到：

- machine-interpretable runtime governance

## 第一版 contract schema 帶進來了什麼

最早的 machine-readable `[Governance Contract]` 開始明確攜帶：

- `RULES`
- `RISK`
- `OVERSIGHT`
- `MEMORY_MODE`

這些欄位到現在仍然是 runtime decision path 的核心骨架。

當時的例子像這樣：

```text
[Governance Contract]
LANG        = C++
LEVEL       = L2
SCOPE       = feature
PLAN        = Phase B / Sprint 2 / Runtime governance
LOADED      = SYSTEM_PROMPT, HUMAN-OVERSIGHT, AGENT, ARCHITECTURE
CONTEXT     = runtime-layer -> hook enforcement; NOT: full agent platform
PRESSURE    = SAFE (42/200)
RULES       = common,python
RISK        = medium
OVERSIGHT   = review-required
MEMORY_MODE = candidate
```

這個例子今天已經不是最新介面，但它很清楚地標出：runtime governance 真正開始依賴 machine-readable state，而不是只靠 prompt 約定。

## 第一版 runtime path 做了什麼

### State Generator

當時 `governance_tools/state_generator.py` 開始接受 runtime input，例如：

```bash
python governance_tools/state_generator.py \
  --rules common,python \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate
```

這一步的價值是：讓 runtime hooks 有統一的 state 來源，而不是每個 surface 自己猜。

### Pre-task Check

最早的 `pre_task_check` 範例像這樣：

```bash
python runtime_hooks/core/pre_task_check.py \
  --rules common,python \
  --risk high \
  --oversight review-required
```

這代表治理開始在 task 前就進 decision path，而不只是事後 review。

### Post-task Check

最早的 `post_task_check` 範例像這樣：

```bash
python runtime_hooks/core/post_task_check.py \
  --file ai_response.txt \
  --risk medium \
  --oversight review-required
```

這一步讓 runtime 開始對 AI response / change output 做 evidence-aware 的後驗檢查。

## 從當時到現在，主線怎麼長成

今天這條線已經不只停在 early slice，而是往下長出了：

- `session_start` / `session_end` 的 shared runtime lifecycle
- `decision_context`
- runtime surface manifest / coverage
- advisory observation layer
- canonical closeout workflow
- memory closeout visibility
- closeout audit / status surface

所以今天回看，這份更新文件比較適合被理解成：

> runtime governance 主線的起點紀錄。

不是最新完整說明。

## 當前應搭配閱讀的文件

如果你想看現在的完整主線，不要只停在這份歷史更新。建議搭配：

- `README.md`
- `docs/status/runtime-governance-status.md`
- `docs/decision-context-bridge.md`
- `docs/session-workflow-enhancement-plan.md`
- `docs/status/closeout-audit.md`

## 一句話總結

> 這份文件記錄的是 runtime governance 第一刀怎麼進 repo；今天它的價值主要是歷史定位，而不是最新能力總覽。
