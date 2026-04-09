# Host-Agent Memory Gap：repo memory 與 host memory 之間的缺口

> 狀態：draft  
> 更新日期：2026-04-01

## 問題定義

目前 `ai-governance-framework` 已經有：
- instruction layer
- repo artifact
- memory pipeline

但還沒有真正的 host-agent memory integration。  
這造成幾個明顯缺口：

- repo 內的 memory / artifact / handoff 能被 framework 看見
- 但 AI 主機端自己的 memory 並沒有被 framework 同步、驗證或審計
- 因此 repo 內的狀態與 host memory 之間仍然可能脫節

## 目前的四層結構

### 1. Instruction Layer

例子：
- `AGENTS.md`
- `copilot-instructions.md`
- `governance/SYSTEM_PROMPT.md`

這一層提供 guidance，但不等於 memory sync。

### 2. Artifact / Repo Memory Layer

例子：
- `memory/*.md`
- runtime verdict / trace artifacts
- reviewer handoff
- session summaries

這一層屬於 repo memory，不等於 host-agent memory。

### 3. Host Memory Layer

這一層指的是 AI agent 在宿主產品中的記憶系統，例如：
- memory UI
- memory API
- 產品端提供的其他長期記憶機制

framework 目前對這一層幾乎沒有直接控制力。

### 4. Enforcement / Integration Layer

理想上，framework 應能在 instruction 與 artifact 之上再補一層：
- host memory sync 的可觀測性
- host memory sync failure 的 signal
- sync signal 如何進 session / reviewer / adoption gate

## 目前的缺口

### 缺口 1：沒有正式的 host memory integration

repo memory 可以由 framework 觀測，但 host-agent memory 沒有 adapter / API contract。

### 缺口 2：沒有 enforceable sync policy

目前無法穩定回答：
- 哪些 session 必須做 sync
- 哪些資訊必須進 repo memory
- sync 失敗後應如何對待

### 缺口 3：closeout 缺少 host-memory loop

即使 closeout 已能寫回 repo memory，仍無法保證 host-agent memory 也同步更新。

## 理想的最小收斂方向

較合理的最小目標不是 full host integration，而是：
- instruction 已載入
- repo memory 已更新
- runtime artifact 已留下
- host-agent memory 是否適用，有明確 signal

也就是先把「不知道有沒有同步」變成可觀測，而不是假裝已完成整合。

## 一句總結

目前 framework 已能治理 repo memory，但還沒有真正治理 host-agent memory；真正的 gap 不在 memory pipeline 本身，而在 repo 層與 host memory 層之間沒有正式可驗的 integration seam。
