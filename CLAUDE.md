# CLAUDE.md — Claude Code instructions

`AGENTS.md` is the fuller behavioural contract for this repository; read it for
routers, risk levels, forbidden behaviours and delivery constraints. This file
carries the one thing Claude Code must honour from the first turn.

## Governance Contract Output (MANDATORY)

The rules below are projected verbatim from the canonical source named in the
projection header, which carries the projection version and the content digest
of that canonical section. Do not edit them here. Edit the canonical section,
then regenerate:

```bash
python -m governance_tools.copilot_instructions_projection --framework-root . --write
```

<!-- ai-governance:checkpoint-projection BEGIN version=1.1 source=governance/SYSTEM_PROMPT.md#2.8 sha256=f156e916270b14e5c636aebb035d03cbf84d4cc077eb8b7c37656f0db57634a5 -->
### 2.8 Governance Contract Output

在以下時點輸出此 block：
- task 開始
- milestone 完成
- scope 改變
- stop / escalation 事件
- 任何 contract 欄位發生實質變化時

若只是 routine progress commentary 且 state 未變，可省略。

```text
[Governance Contract]
LANG     = <value>
LEVEL    = <value>
SCOPE    = <value>
PLAN     = <current phase> / <sprint> / <task>
LOADED   = <comma-separated list of loaded governance docs>
CONTEXT  = <context name> -> <responsible for X>; NOT: <not responsible for Y>
PRESSURE = <SAFE|WARNING|CRITICAL|EMERGENCY> (<line count>/200)
AGENT_ID = <agent-id>       # optional; required in multi-agent sessions
SESSION  = <YYYY-MM-DD-NN>  # optional; required when AGENT_ID is present
```

欄位規則：
- `LANG`: 取自 `C | C++ | C# | ObjC | Swift | JS | Python | Verilog | SystemVerilog`。
  單一語言直接填該值；跨語言任務以逗號分隔，每個元素都必須是上列值之一（例：`C, C++`）。
  不得把多個語言寫成單一 token（例：`C/C++`）：`/` 已是 `SCOPE` 的 `I/O` 值的一部分，
  在同一個 block 內不能再兼作清單分隔符。分隔符與 `LOADED` 一致。
- `LEVEL`: 單值，取自 `L0 | L1 | L2`
- `SCOPE`: **單值**，取自 `feature | refactor | bugfix | I/O | tooling | review | governance | kernel-driver`。
  `SCOPE` 會決定 review、testing 與 governance routing；多值會引入未定義的優先序與衝突語義，
  因此不接受清單。任務橫跨多個 scope 時，拆成多個 task 或選擇主導的那一個。
- `PLAN`: 取自 `PLAN.md`；若人類明確授權 governance analysis，可標 `Out-of-scope`
- `LOADED`: must name governance docs actually loaded into the agent context. It must include `SYSTEM_PROMPT`; `HUMAN-OVERSIGHT.md` is human-only authority and must not be listed as loaded unless a human explicitly provides it.
  每個項目以逗號分隔。文件識別採**最後一段路徑、可省略 `.md`**，因此下列四種寫法識別為同一份文件：
  `SYSTEM_PROMPT`、`SYSTEM_PROMPT.md`、`governance/SYSTEM_PROMPT.md`、
  `ai-governance-framework\governance\SYSTEM_PROMPT.md`。
  正規化規則：`\` 一律視為 `/`；取最後一段；**只有 `.md` 可省略**，其他副檔名不得省略；
  比對**區分大小寫**。因此 `SYSTEM_PROMPT.txt`、`MY_SYSTEM_PROMPT.md`、`system_prompt`
  都不是 `SYSTEM_PROMPT`。寫出完整路徑比裸 token 攜帶更多可稽核資訊，兩者同等合法。
- `CONTEXT`: 必須同時包含 `->` 與 `NOT:`
- `PRESSURE`: 必須含 label 與 line count
- `SESSION`: 當 `AGENT_ID` 存在時必填

格式錯誤的 contract block 屬於 governance failure。
<!-- ai-governance:checkpoint-projection END -->

### When SYSTEM_PROMPT.md is not loaded

`LOADED` must name governance documents actually loaded into this context, and
the canonical rules require `SYSTEM_PROMPT` among them. This file is a projection
of one canonical section — it is not `SYSTEM_PROMPT.md`, and its presence is not
evidence that `SYSTEM_PROMPT.md` was read.

When `governance/SYSTEM_PROMPT.md` has not actually been loaded, no compliant
`[Governance Contract]` block can be produced. Emit this notice at the same
checkpoints instead, and never emit a block whose `LOADED` names documents that
were not read:

```text
[Governance Contract: UNAVAILABLE]
REASON  = governance context incomplete
MISSING = SYSTEM_PROMPT
SOURCE  = CLAUDE.md (checkpoint projection)
NEXT    = load governance/SYSTEM_PROMPT.md, or ask the human to provide it
```

Reading `governance/SYSTEM_PROMPT.md` during the session clears the notice, and
that change to `LOADED` is itself a material contract change — emit the full
block at that point.
