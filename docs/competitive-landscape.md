# 競品地景

更新日期：2026-04-08

這份文件用來記錄目前和 `ai-governance-framework` 最接近的開源或商業參考點。目的不是 claim feature parity，而是把 repo 的定位說清楚：

- 哪些東西可以直接比較
- 哪些只是相鄰
- 這個 framework 現在真正獨特的地方是什麼

重要範圍提醒：

- 這裡的比較是方向性的
- 主要依據公開定位、repo 結構與可見 workflow
- 不應被讀成對其他專案完整能力的最終審判
- 這份文件更適合拿來校準本 repo 的自我敘事，而不是拿來對別人做過度結論

## 短版定位

目前最準的定位仍然是：

- 一個 machine-interpretable governance runtime
- 聚焦於 AI coding workflow 的 runtime governance
- 核心結構是 external contract、mixed enforcement、reviewer/audit surface、session closeout
- 刻意不走 full execution harness、generic orchestration platform、enterprise-wide compliance suite 這條路

## 快速比較表

| 專案 | 可見重點 | 重心 | 為什麼值得比較 |
|---|---|---|---|
| `ai-governance-framework` | multi-repo runtime governance、mixed enforcement、reviewer publication | framework + external contracts 的 runtime governance | 參考列 |
| `AI-Governor-Framework` | repo rule、architecture respect、guided behavior | repo-embedded governance rules | 適合比 rule UX 與 repo 內約束 |
| `GAAI-framework` | governed workflow 與 delivery structure | governed delivery workflow | 適合比流程與 backlog discipline |
| `agentic-engineering-framework` | mechanical repo enforcement、task gate | practical runtime/repo enforcement | 適合比 interception 與 commit/merge gate 想法 |
| `agent-governance-toolkit` | agent action policy、sandbox、tool governance | action-level agent governance | 適合比 layer，不是直接 peer |
| `TinySDLC` | role handoff 與 SDLC choreography | multi-role SDLC orchestration | 適合比 handoff / role separation |

## 最接近的開源參考

### 1. AI-Governor-Framework

參考：

- <https://github.com/Fr-e-d/AI-Governor-Framework>

接近點：

- repo-embedded governance rule
- project-aware constraint
- architecture respect
- AI 應像 disciplined engineering partner 的 framing

和本 repo 最像的地方：

- governance 文件
- rule-driven behavioral constraint
- 對 AI work 設 boundary

本 repo 額外更強調的地方：

- 更完整的 runtime lifecycle
- external domain contract seam
- reviewer / audit publication surface
- validator 能影響 post-task decision，而不是只有背景規則

### 2. GAAI-framework

參考：

- <https://github.com/Fr-e-d/GAAI-framework>

接近點：

- governed delivery system framing
- process boundary 明確
- workflow phase 之間有 context separation

和本 repo 最像的地方：

- proposal / planning discipline
- governed execution flow
- 重視 repeatable delivery structure，不只靠 prompt craft

本 repo 額外更強調的地方：

- 更明確的 runtime hook / validator path
- `hard_stop_rules` 驅動的 mixed enforcement
- trust-signal / release / reviewer-handoff surface
- 對 architecture/runtime evidence 的強調，高於 delivery role choreography

### 3. agentic-engineering-framework

參考：

- <https://github.com/DimitriGeelen/agentic-engineering-framework>

接近點：

- 明確把自己定位成 AI coding governance layer
- 強調 mechanical enforcement，不只是 soft guideline
- 重 continuity、rules、blocking risky actions

和本 repo 最像的地方：

- runtime governance framing
- task gate 心態
- practical enforcement posture

本 repo 額外更強調的地方：

- reviewer / audit publication 路徑更厚
- external domain contract 故事更強
- cross-repo onboarding / readiness / trust surface 更多
- 更像 multi-repo governance stack，而不只是單 repo enforcement

這目前仍是最值得拿來比 practical interception coverage 的參考點之一。

### 4. TinySDLC

參考：

- <https://github.com/Minh-Tam-Solution/tinysdlc>

相鄰點：

- structured handoff
- role separation
- local-first orchestration

和本 repo 最像的地方：

- reviewer handoff 心態
- 用 structure 取代 ad hoc prompt

本 repo 更強調的地方：

- repo-native runtime governance
- external contract seam
- contract-aware post-task enforcement
- reviewer/audit publication surface，而不是 role choreography

### 5. agent-governance-toolkit

參考：

- <https://github.com/microsoft/agent-governance-toolkit>

為什麼值得比較：

- 它把 governance 當 execution-time concern，不只是 prompt guidance
- 它重視 agent action / tool use 的 policy enforcement
- 它是 action-level interception thinking 的重要參考點

與本 repo 的 layer 差異：

- 本 repo 主要治理 coding task / session boundary
- 它更接近 agent runtime 本身的 action governance、identity、execution policy

這個差異很重要，因為：

- 它在問：「這個 agent action 是否允許、是否安全？」
- 本 repo 更常在問：「這個 coding output 是否尊重 architecture / domain / review boundary？」

所以它是重要 benchmark，但不是一對一 peer。

## 相鄰但不是直接 peer 的參考

### VerifyWise

參考：

- <https://github.com/bluewave-labs/verifywise>

適合借鏡：

- auditability
- governance visibility
- 高層 AI governance communication

不是直接 peer 的原因：

- 它更接近 AI governance / GRC，而不是 AI coding runtime governance

### Guardrails AI

參考：

- <https://github.com/guardrails-ai/guardrails>
- <https://guardrailsai.com/>

適合借鏡：

- runtime validation pattern
- policy-style output control

不是直接 peer 的原因：

- 它主要是 LLM output/runtime validation system，不是 repo-level coding governance framework

### CodeRabbit

參考：

- <https://www.coderabbit.ai/>

適合借鏡：

- reviewer UX
- PR-facing consumption surface
- trust / adoption messaging

不是直接 peer 的原因：

- 它主要是 AI-assisted review product，不是 external-contract runtime governance framework

### SAFi

參考：

- <https://github.com/jnamaya/SAFi>

適合借鏡：

- runtime output governance
- value/constitution framing
- post-generation audit pattern

不是直接 peer 的原因：

- 它更接近 AI behavior output governance，不是 repo-native coding architecture governance

### GitHub Spec Kit

參考：

- 公開 GitHub Spec Kit 材料 / repo

適合借鏡：

- spec-driven development
- executable specification workflow
- 降低 prompt-and-pray

不是直接 peer 的原因：

- 它更像 specification-driven implementation guidance，不是 mixed-enforcement runtime governance

它和本 repo 是互補，不是替代。

### Sovereign-OS

參考：

- 公開 Sovereign-OS 材料 / repo

適合借鏡：

- append-only governance trail
- mission / budget / rule declaration
- agent resource governance

不是直接 peer 的原因：

- 它更接近 budget/token/mission governance，而不是 software architecture boundary governance

### GitHub Agent HQ / Agentic Workflows

參考：

- 公開 GitHub platform 材料與報導

適合借鏡：

- platform-level agent governance
- central mission control and auditability
- enterprise-facing agent operations

不是直接 peer 的原因：

- 那是 platform governance for agent operations
- 本 repo 是 domain-knowledge governance for architecture-sensitive coding workflows

這也是為什麼 repo-level governance framework 在 platform-native agent governance 存在時，仍然有價值。

### Agent Behavioral Contracts（ABC）/ POLARIS

參考：

- 公開學術論文與 workshop paper

適合借鏡：

- formal contract thinking
- drift bound
- validator-gated orchestration
- runtime governance 的理論 framing

不是直接 peer 的原因：

- 它們更適合當 research direction，不是 drop-in repo-native coding governance system

## 這個 repo 目前真正獨特的地方

目前最清楚的 differentiator 包括：

- 真實的 runtime governance loop：
  - `session_start -> pre_task_check -> post_task_check -> session_end -> memory pipeline`
- external domain contract living in separate repos
- mixed enforcement：domain validator + `hard_stop_rules`
- reviewer-facing publication surface：
  - trust signal
  - release-facing status
  - reviewer handoff
- memory artifact 不只保 generic session log，也保 domain contract metadata
- 對 firmware、kernel-driver、IC verification 這類 high-context / safety-sensitive domain 有治理形狀

也就是說，它不只是「把 AI 規則放進 repo」。

它更接近：

- multi-repo AI coding runtime governance stack

而不是：

- prompt pack
- role-play orchestrator
- generic LLM guardrail wrapper

## 實際借鏡策略

最有價值的做法不是照抄任何一個專案，而是有選擇地借：

- 從 `agentic-engineering-framework` 借 git-hook / CI-gate interception 想法
- 從 `agent-governance-toolkit` 借 action-level governance boundary 思維，但不要漂去 generation-time interception
- 從 `AI-Governor-Framework` / `GAAI-framework` 借 repo-embedded rule UX
- 從 `CodeRabbit` 借 reviewer surface clarity
- 從 `VerifyWise` 借 auditability / visibility 想法
- 把 `GitHub Spec Kit`、`ABC`、`POLARIS` 當 specification / contract rigor 的理論參考，不當成直接 implementation target

這樣比較不會為了模仿而模仿，最後把 repo 推到自己不想去的 scope。

## 要守住的邊界

在借鏡這些專案時，這個 repo 仍然應避免漂成：

- plugin marketplace
- generic multi-agent orchestration OS
- code-generation-time interception layer
- enterprise-wide AI compliance platform

## 一句話定位

和最接近的開源參考相比，`ai-governance-framework` 現在最穩的描述仍然是：

> 一個 multi-repo、machine-interpretable 的 AI coding runtime governance framework，
> 其重點在 external domain contract、mixed enforcement，以及 reviewer / audit publication surface。
