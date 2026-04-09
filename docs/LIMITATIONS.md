# LIMITATIONS.md - 目前邊界與已知限制

> 這份文件的目的，不是替 repo 降低期待，而是把**現在已做到什麼、刻意還沒做到什麼、以及哪類風險仍需要人類判斷**說清楚。
>
> `ai-governance-framework` 目前是一個 **machine-interpretable governance runtime**。它已經能治理 execution、evidence、decision、memory / state 與 reviewer-facing surface，但仍是 **bounded system**，不是萬能代理平台。

---

## 1. 目前已經成立的能力

### 1.1 Governance Runtime 主線

目前 repo 已成立的主線包括：
- `session_start`
- `pre_task_check`
- `post_task_check`
- `session_end`
- change-control / reviewer-facing artifact
- decision context / advisory surface
- bounded closeout / canonical closeout workflow

也就是說，它不再只是 prompt 或文件集合，而是能產生 runtime artifact、status surface、與可追蹤 decision path 的治理系統。

### 1.2 Repo-Local Adoption Path

目前已具備：
- `adopt_governance.py` cross-platform adopt path
- `governance_drift_checker.py`
- external repo readiness / onboarding / source audit
- canonical framework source 檢查
- memory schema scaffold 與 partial / complete visibility

這些能力足以支撐 consuming repo 做 bounded adoption，但不等於任何 repo 都會自動進入 fully governed state。

### 1.3 Review / Status / Audit Surface

目前已有：
- trust-signal / status surface
- closeout audit
- execution surface coverage
- runtime surface manifest
- reviewer handoff 與 release-facing status page

這些 surface 已可用於 reviewer 與 adoption 驗證，但多數仍是 **observability-first**，不是 enforcement-first。

---

## 2. 目前刻意不主張的能力

以下能力**不是**這個 repo 現在的對外主張：

### 2.1 不是 Full Execution Harness

這個 repo 雖然有 runtime hook、surface inventory、coverage plan、decision context，但它不是完整 execution harness。

它沒有提供：
- 通用 agent orchestration substrate
- 全面 workflow interception
- 通用 multi-agent runtime scheduler
- 全部工具鏈的統一執行控制層

### 2.2 不是 Machine-Authoritative Advisory System

advisory signal 目前是：
- reviewer-visible
- bounded
- non-verdict-bearing

它們的作用是降低誤讀、補 decision context、提升 reviewer 可判讀性，而不是直接變成 machine authority。

也就是說：
- advisory signal ≠ proof of compliance
- advisory signal ≠ proof of violation
- advisory signal ≠ final verdict input

### 2.3 不是 Generic Multi-Agent Orchestration Platform

這個 repo 雖然有 session workflow、closeout、decision surface、advisory taxonomy、injection plan，但它不是通用 multi-agent platform。

它目前不處理：
- 通用 agent marketplace
- 多代理全域調度
- 任意工具 / 任意平台的動態策略編排

---

## 3. 當前主要限制

### 3.1 Workflow Interception Coverage 仍然 Partial

目前一些 runtime path 已被治理，但「代理實際執行的所有行為」還沒有完整被攔截與驗證。

因此：
- 有些路徑是可觀測的
- 有些路徑只有 reviewer-visible signal
- 有些路徑仍然依賴外部 discipline，而非強制執行

### 3.2 Advisory / Observation 仍以 Semantics-Observation 為主

目前 advisory slice 已收斂，但它是：
- 受限
- reviewer-visible
- non-verdict-bearing

這是刻意設計，不是缺漏。代價是：
- 可降低誤讀
- 但不追求 machine authority
- 也不追求 full signal × full surface matrix

### 3.3 Memory 與 Host-Agent Memory 尚未打通

目前 repo 已有：
- memory schema
- memory sync signal
- memory closeout visibility

但以下仍未成立：
- host-agent memory adapter
- 對外部 agent memory API 的強制同步
- 通用 session-closeout 自動寫入外部記憶系統

所以目前能治理的是 **repo memory / artifact truth**，不是所有外部平台記憶機制。

### 3.4 Policy 與 Semantic Verification 仍非 Full Policy Engine

目前系統已能：
- 提供 risk gate
- 做 bounded decision support
- 產生 reviewer-facing trace
- 做 phase / surface / coverage / closeout 相關檢查

但它仍不是：
- 全面 semantic policy engine
- 可對任意 repo / 任意 agent / 任意 domain 自動給出無歧義裁決的系統

### 3.5 Taxonomy 採 Precision-First，不是 Completeness-First

像 closeout taxonomy、advisory taxonomy、classification slice、以及多個 runtime signal，目前都偏向：
- precision-first
- stability-first

這代表：
- false positive 較少
- 但 recall 壓力會較高
- 有些值得辨識的情況，第一版可能不會被抓到

這是取捨，不是意外。

---

## 4. 目前最常見的誤解

### 誤解 1：有很多 artifact，所以一定是全自動治理

不是。artifact 多，代表 observability 在增強；不代表ทุก一條路徑都已經被 machine-authoritative 地接管。

### 誤解 2：有 advisory signal，所以 system 已能自動裁決

不是。advisory signal 目前的位階被刻意限制在 reviewer-visible、non-verdict-bearing。

### 誤解 3：有 execution / decision / memory，所以它已是完整 runtime platform

不是。這些能力已經讓它超越純文件 framework，但仍是 bounded runtime，不是 full platform。

### 誤解 4：導入 framework 後，memory 一定會自動更新

不是。現在已補上 `memory_closeout` visibility，但「是否 promote、為什麼沒寫」仍受 closeout path、policy、risk、oversight 與 consuming repo 實際接線影響。

---

## 5. 對 adopter / reviewer 的實際建議

### 對 adopter

如果你要導入這個 framework，應預期：
- 它能給你一條 bounded governance path
- 它能提高 traceability、reviewability、與 adoption consistency
- 但你仍需要為自己的 repo 定義：
  - canonical build path
  - domain boundary
  - reviewer discipline
  - memory / closeout 使用方式

### 對 reviewer

review 時應把它看成：
- 一個能讓 decision 與 review artifact 更可讀的 runtime
- 一組可觀測的 trust surface
- 一套 bounded governance mechanism

不要把它當成萬能 policy machine，也不要把 reviewer 的判斷責任完全外包給 signal。

---

## 6. 一句話總結

> `ai-governance-framework` 已經是一個可執行、可觀測、可審查的 governance runtime；但它仍刻意停在 bounded、precision-first、reviewer-compatible 的位階，而不是 full execution harness 或 machine-authoritative policy platform。
