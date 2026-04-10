# LIMITATIONS.md - 當前限制

這份文件不是在否定 framework，而是在說清楚它**目前已做到什麼、刻意沒做到什麼、以及 adopter / reviewer 應如何理解它的邊界**。

`ai-governance-framework` 目前是一個 **machine-interpretable governance runtime**，不是 full execution platform。

## 1. 目前已成立的能力

### 1.1 Governance Runtime

目前已建立的核心 runtime surfaces 包括：

- `session_start`
- `pre_task_check`
- `post_task_check`
- `session_end`
- decision / evidence / closeout / reviewer-facing artifacts
- decision context / advisory semantics
- bounded closeout / canonical closeout workflow

這代表 framework 已經超過單純的 prompt discipline，但仍是 bounded runtime，不是全代理執行平台。

### 1.2 Repo-Local Adoption Path

目前已建立：

- `adopt_governance.py`
- drift checker
- readiness / onboarding / source audit
- memory scaffold
- governance markdown pack
- governance rules pack

也就是說，consuming repo 已可被帶到一條 bounded adoption path，但不代表所有 repo 一 adopt 就會自然進入成熟治理狀態。

### 1.3 Review / Status / Audit Surface

目前已有：

- trust-signal / status surfaces
- closeout audit
- execution surface coverage
- runtime surface manifest
- reviewer handoff

這些能力偏向 observability-first，而不是 enforcement-first。

## 2. 明確不主張的範圍

### 2.1 不是 Full Execution Harness

本 repo 雖然有 runtime hooks、surface inventory、coverage 與 closeout workflow，但並不是：

- 完整的 agent orchestration substrate
- 完整的 workflow interception layer
- 通用 multi-agent runtime scheduler
- 任意工具 / 任意 agent 的統一執行平台

### 2.2 不是 Machine-Authoritative Advisory System

advisory signal 目前是：

- bounded
- reviewer-visible
- non-verdict-bearing

它們可以輔助 reviewer 理解風險與上下文，但不能被當成：

- proof of compliance
- proof of violation
- final verdict authority

### 2.3 不是 Generic Multi-Agent Orchestration Platform

repo 裡雖然已有 session workflow、closeout、decision context、advisory taxonomy、injection plan 等結構，但這不等於通用 multi-agent platform。

目前沒有主張：

- agent marketplace
- 通用代理排程與任務分發
- 多 agent 之間的權限、記憶、共識治理層

## 3. 當前限制

### 3.1 Workflow Interception Coverage 仍是 Partial

framework 已能觀測一部分 runtime path，但還沒有保證每一種實際工作流程都會被完整接住。

因此目前比較接近：

- 有 bounded governance path
- 有 reviewer-visible trust surface
- 有可追蹤的 closeout / audit / status

但不是「所有工作都一定被 framework 完整攔截」。

### 3.2 Advisory Slice 仍在 Semantics-Observation Phase

advisory signal 已有：

- taxonomy
- phase boundary
- producer contract
- reviewer-visible rendering

但這條線刻意停在：

- reviewer-visible
- non-verdict-bearing
- 不進 machine authority

這是設計選擇，不是未完成 bug。

### 3.3 Memory / Host-Agent Memory 仍有邊界

目前 repo 已有：

- memory schema
- memory sync signal
- memory closeout visibility

但仍沒有：

- host-agent memory 統一 adapter
- 通用 agent memory API
- 自動保證每次工作都寫入 durable memory

目前補到的是「為什麼沒寫 memory 可被看見」，不是「所有工作都一定更新 memory」。

### 3.4 Policy / Semantic Verification 不是 Full Policy Engine

目前已有：

- bounded risk gate
- bounded decision support
- reviewer-facing trace
- phase / surface / coverage / closeout 的可觀測規則

但還沒有：

- 通用 semantic policy engine
- 全 repo / 全 agent / 全 domain 的統一政策推理系統

### 3.5 Taxonomy 採 Precision-First，不是 Completeness-First

像 closeout taxonomy、advisory taxonomy、classification slice 目前都偏向：

- precision-first
- stability-first

這代表：

- false positive 風險較低
- 但 recall 之後仍會面對壓力

這是有意識的取捨，不是現階段缺陷。

## 4. 容易誤解的地方

### 4.1 有 artifact 不等於有 authority

某個 signal、trace、status page 出現，不代表它已經成為最終裁決權。

### 4.2 有 advisory 不等於有 machine verdict

advisory signal 的主要角色仍是 reviewer-facing semantic aid，不是 policy verdict engine。

### 4.3 有 execution / decision / memory 不等於 full runtime platform

目前是 bounded runtime，不是完整 execution substrate。

### 4.4 memory closeout 可見，不等於 memory 一定會更新

現在補到的是：

- candidate detected?
- promotion considered?
- decision / reason?

而不是「所有 session 都自動進 durable memory」。

## 5. adopter / reviewer 應如何理解

### 對 adopter

應把這個 framework 理解成：

- 一條 bounded governance adoption path
- 一套可被檢查的 baseline / readiness / drift / closeout / reviewer surface
- 一個能讓 repo 漸進進入治理狀態的 framework

不要把它想成一個會自動接管整個 repo 工程品質的萬用平台。

### 對 reviewer

應把它理解成：

- 提供 decision / trace / closeout / status 的可檢查輸出
- 降低誤讀風險
- 提供 bounded governance evidence

而不是取代 reviewer judgment 本身。

## 6. 一句話總結

> `ai-governance-framework` 目前是一個 bounded、precision-first、reviewer-compatible 的 governance runtime；它已經超過 prompt discipline，但刻意還不是 full execution harness 或 machine-authoritative policy platform。
