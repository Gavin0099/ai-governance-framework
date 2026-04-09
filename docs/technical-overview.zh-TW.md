# AI Governance Framework 技術總覽

> **正式 release**：v1.1.0（2026-03-22）  
> **主要維護來源**：`https://github.com/Gavin0099/ai-governance-framework`  
> **目前文件描述的主線現況**：以 `main` 分支的 bounded runtime reality 為準

---

## 1. 這個 repo 在做什麼

這個 repo 目前是一個 **AI governance framework**，更精確地說，它已經演進成一個 **machine-interpretable governance runtime**。

它處理的不只是規則文件或 prompt discipline，而是把下列幾層接成可觀測、可審計的治理流程：

- `execution`
- `evidence`
- `decision`
- `memory / state`
- reviewer-facing governance surfaces

它的重點不是取代 agent 本身，而是讓 session、artifact、decision 與 closeout 具備可驗證的治理邊界。

## 2. 核心分層

### 2.1 Runtime Hooks

主要 runtime hook 包括：
- `session_start`
- `pre_task_check`
- `post_task_check`
- `session_end`

這些 hook 負責把治理判斷接進真實 session，而不是停留在靜態文件層。

### 2.2 Governance Tools

`governance_tools/` 主要提供：
- adopt / onboarding
- readiness / version audit
- runtime surface / execution coverage status
- closeout audit / reviewer-facing summary
- release readiness 與 package reader

### 2.3 Memory Pipeline

memory pipeline 目前提供：
- candidate 產生
- promotion decision
- closeout visibility
- `memory_closeout` structured output

它目前重點是讓「為什麼沒寫 memory」變成可觀測，而不是盲目提高 auto-promotion。

### 2.4 Contract 與 Domain Seam

repo 透過 `contract.yaml` 與 `governance/rules/` 形成 domain seam。
framework 提供通用治理骨架，consuming repo 再以 contract 與 rule pack 指定自己的邊界與風險路徑。

## 3. 目前成立的能力

### 3.1 導入與治理骨架

目前已可穩定提供：
- submodule / nested checkout adoption
- baseline / drift / readiness
- governance markdown pack 與 `governance/rules/` 導入
- minimal memory scaffold
- canonical framework source audit

### 3.2 Runtime 治理

目前 runtime 線已具備：
- decision boundary layer
- execution surface manifest
- execution coverage first slice
- `decision_context`
- closeout canonicalization 與 audit
- reviewer-visible advisory semantics

### 3.3 Consuming repo 驗證

目前已有多條 consuming-repo 驗證路徑：
- adoption checklist
- onboarding report
- version audit
- memory schema validation
- memory closeout validation

## 4. 不主張的能力

這個 repo 目前**不主張**自己是：
- full execution harness
- machine-authoritative advisory system
- generic multi-agent orchestration platform

這些 non-claims 不是附註，而是目前能力邊界的一部分。

## 5. 觀察中的主線

目前幾條已完成實作、但進入 observation phase 的主線包括：
- `Session Workflow Enhancement`
- advisory slice v1
- execution coverage first slice
- classification governance companion slice

它們的共通點是：
- 架構與邊界已固定
- 目前先觀察實際 session / artifact 分布
- 不急著往 machine authority 或更強 gate 擴張

## 6. adopter 應如何理解這個 repo

如果你是 consuming repo adopter，最重要的理解方式是：
- 它提供治理 runtime 與審計骨架
- 它不會替你自動完成所有 domain judgment
- 它要求你用 contract、rule pack、reviewer surface 與 closeout 去補齊 repo 自己的治理語境

## 7. 一句總結

這個 repo 目前不是一個大而全的 agent platform；它是一個以 runtime、artifact、decision 與 closeout 為核心的 bounded governance runtime，用來讓 AI-assisted engineering 的治理流程變得可觀測、可重建、可審計。
