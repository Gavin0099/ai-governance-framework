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

<!-- ai-governance:checkpoint-projection BEGIN version=1.1 source=governance/SYSTEM_PROMPT.md#2.8 sha256=0829946513494089ed95b333733572a03666060dfabd10eca36c4ab662b4888f -->
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
         # 或 <LEVEL> (<line count>/200 lines; <char count> chars)
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
- `PRESSURE`: 必須含 label 與**實際的** line count，兩種形式擇一：
  - `<LEVEL> (<line count>/200)`
  - `<LEVEL> (<line count>/200 lines; <char count> chars)`
  第二種形式存在的理由：§7.4 的判級依據是「行數**或**字元數任一達標」，只寫 line count
  時，因字元數達標而升級的判定在 contract 裡無法被檢視。需要說明判級理由時用第二種。
  兩個數字都必須是實際整數；分母固定 200。`(<line count>/200)` 這種未替換的樣板、
  `(pending exact line count/200)` 這類佔位字串、非數字與負數都屬格式錯誤。
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

## Session-End Closeout (MANDATORY)

The block below is a verbatim copy of the canonical block in `AGENTS.base.md`
(Session Closeout Obligation). Do not edit it here; edit the canonical block and
copy it to every entry file. No generator or drift check covers this block yet.

<!-- ai-governance:session-end-closeout BEGIN version=1 canonical=AGENTS.base.md -->
### Session-End Closeout Responsibility

These rules apply to every agent platform (Codex, Claude, Copilot and others).
They define when closeout is required, who is responsible, and what may be
claimed. They do not define which lifecycle event a platform uses; that is
platform-specific and must be qualified separately for each platform.

1. **Task DONE is not session end.** Finishing a task, a review, or a milestone
   ends that task only. Report DONE, do not expand the work, and leave the
   session open for the next request.
2. **Closeout at a defined session end is a duty, not new work.** A mandatory
   closeout at session end is not scope expansion. Hard Stop After DONE forbids
   closeout after task DONE; it does not forbid closeout at session end.
3. **Session end must come from a defined, observable source.** Only two sources
   count: a platform lifecycle event whose session-end meaning has been
   confirmed for that platform, or the user explicitly asking to end the session
   or to close out. The agent must not infer that the conversation is over. A
   final answer, a DONE report, or a per-turn `Stop` event is not session end
   unless that meaning has been confirmed.
4. **Governed lifecycle hook present:** the harness is responsible for
   triggering canonical closeout. A governed hook is one wired to the governance
   closeout entry and confirmed to run for this platform.
5. **No usable governed hook:** only when session end is established under
   rule 3, the top-level agent must attempt the existing manual closeout
   (`python -m governance_tools.manage_agent_closeout print-manual --agent <agent>`
   prints the command). If it cannot run or its result cannot be verified,
   report closeout as `NOT PERSISTED` or `UNKNOWN`; never claim it was persisted.
6. **Subagent completion is not project-level session end.** A subagent
   returning to its parent must not run project-level closeout unless it has its
   own governed session identity and was explicitly given closeout
   responsibility.

A closeout, including the manual fallback, does not authorize commit, push,
pull request, or a new task; each still needs its own explicit authorization.

Closeout candidate, canonical record, and memory are verified separately. A
successful closeout on one platform is not evidence for any other platform.
<!-- ai-governance:session-end-closeout END -->
