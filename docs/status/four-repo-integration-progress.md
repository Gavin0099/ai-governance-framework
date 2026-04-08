# 四倉整合進度

更新日期：2026-04-08
狀態：bounded runtime stack in progress

## 當前快照

這份文件用來看四倉治理堆疊目前的整體位置：

- `ai-governance-framework`：核心 machine-interpretable governance runtime
- `USB-Hub-Firmware-Architecture-Contract`：第一個 firmware domain slice
- `Kernel-Driver-Contract`：最成熟的 low-level domain slice 之一
- `IC-Verification-Contract`：較窄但乾淨的 IC verification slice

如果只看目前主線，這個四倉系統已經從「理論可整合」走到「實際可跑」，但仍然保持 bounded，沒有往 full platform 漂移。

## 已經成立的事情

### 1. Framework Engine 已經成形

核心治理 loop 現在已經成立：

`session_start -> pre_task_check -> post_task_check -> session_end -> memory pipeline`

它不再只是 document-only framework，而已經具備：

- contract resolution / loading
- runtime rule activation
- domain-validator discovery 與 execution
- `hard_stop_rules` 驅動的 mixed enforcement
- review-facing artifact 與 status surface
- CI / smoke / closeout / readiness 路徑

最重要的修正是：

- `validator execution` 已不再是主缺口
- `post_task_check.py` 已會實際跑 domain validator
- selected rule ID 已可經 `hard_stop_rules` 進 runtime policy stop

### 2. 三個 domain repo 都不再只是文件

三個 external contract repo 都已至少具備真實 plugin / contract 結構，例如：

- `contract.yaml`
- domain rules
- validators
- fixtures / baseline
- facts intake 或 workflow guidance

成熟度不一樣，但都已經進入 runtime seam。

## 主問題已經轉移

以前的問題比較像 framework plumbing 不完整。現在主問題已經轉成下面幾件事。

### 1. Real facts intake

現在最大的缺口已不是 framework 會不會跑，而是能不能吃到真實 project truth。

目前各 domain repo 多半還偏 sample fixture / example facts：

- USB-Hub 仍需要真實 chip / board facts
- Kernel-Driver 仍需要真實 driver codebase intake
- IC-Verification 仍需要真實 DUT signal-map intake

framework 已能跑，下一步更缺的是真實 domain truth。

### 2. Workflow interception coverage

架構上仍然存在 local edit / direct commit 的 bypass path。

短中期比較實際的路線仍然是：

- git hook
- CI gate
- external onboarding / readiness / smoke

關鍵邊界仍然不變：

- framework 不攔截 AI 生成過程本身
- 它治理的是 task 前後、runtime 與 review boundary

所以這裡真正的目標不是 IDE-native total interception，而是更穩的 commit / merge governance path。

### 3. Semantic verification depth

目前 semantic layer 是真的存在，但仍多半偏 pattern-based。

現在已經有：

- domain validator execution
- mixed enforcement
- `public_api_diff_checker.py` 等 interface reasoning

但還沒有到：

- AST-based
- data-flow-based
- deep semantic proof

所以比較準的說法是：

- semantic verification 已存在
- 但大部分仍是高訊號、pattern-based，而不是深層結構分析

### 4. Release / adoption follow-through

repo 現在已經有 status、trust、release、reviewer surface。

剩下的比較偏 operational：

- 持續驗證 GitHub Release / docs / generated status path 對齊
- 持續驗證 runnable demo path
- 持續驗證 external onboarding path

## 各 domain 的當前位置

### USB-Hub Firmware Contract

目前狀態：

- contract repo 結構已完整
- rules / validators / fixtures / memory 已存在
- runtime policy-input enforcement 已存在
- 仍需要真實 firmware facts intake

最值得的下一步：

- 連接真實 USB-Hub firmware codebase 或 hardware package，把 checklist facts 補成真實資料

### Kernel Driver Contract

目前狀態：

- 是最成熟的 low-level contract repo 之一
- mixed enforcement 已驗過
- onboarding 與 post-task smoke 已存在
- sibling repo setup 下的 readiness / onboarding 已能乾淨驗證
- 仍需要真實 driver facts 與真實 codebase 接入

比較關鍵的觀察是：

- 這條線已經會影響模型的結構選擇
- 但還沒有穩定強迫模型在 written response 中明確說出 driver-sensitive boundary、rule basis、verification evidence

所以下一步與其再加 validator，不如補 response-shaping 與真實 repo 驗證。

### IC Verification Contract

目前狀態：

- 是最窄、也最乾淨的 domain slice
- 已有 machine-readable `signal_map.json`
- mixed enforcement 已驗過
- 是 machine-readable facts 驅動 validator 行為的最好例子之一

最值得的下一步：

- 把 sample signal-map 換成真實 DUT interface facts

## 建議的下一步順序

### 1. 先補真實 facts intake

先挑一個 domain，把真實 facts 接進來。

建議優先：

- `USB-Hub-Firmware-Architecture-Contract`

原因是它最早開始，也最需要擺脫 example fixture。

### 2. 跑至少一次真實 AI session replay

要驗的是：

- 不是只有 fixture
- 不是只有 static smoke
- 而是真實生成的 code / patch evidence 走完整個 `post_task_check`

### 3. 持續強化 practical interception

下一步仍應該放在：

- git hook
- CI gate
- smoother external onboarding

不是把 repo 推去 IDE-native generation interception。

### 4. 再往更深 semantic verification 前進

當真實 usage 帶來更好的 evidence shape 後，再持續推：

- public API compatibility reasoning
- architecture drift reasoning
- richer domain validator

## 一句話總結

> 四倉堆疊現在已經不是「大概能整合」，而是「實際可跑」；真正剩下的主缺口是 real facts intake、practical workflow coverage，以及更深的 semantic verification，而不是 validator 會不會執行。
