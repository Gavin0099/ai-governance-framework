# Next Steps

更新日期：2026-04-08

## 當前 posture

這個 repo 目前最不缺的是新概念。真正高價值的下一步，不是再長更多 layer，而是確認已經落地的 bounded runtime 能不能穩定地被 consuming repo、reviewer 與 shared path 真正用起來。

所以現在的優先順序應該是：

- 真實 consuming repo 驗證
- session workflow / closeout 的 semantics observation
- status / entry surface 對齊
- shared path 是否真的能跑到正確 runtime lane
- 保持 companion slice 受限，不讓它們變成新 authority

## 最高價值的下一步

### 1. 真實 consuming repo 驗證

目前很多主線能力都已在 framework repo 內驗到，也開始用 Hearth、Mirra、`usb_2_0_eep_tool` 等 consuming repo 做 spot check。下一步最值得做的是把這件事變得更系統化：

- 持續驗證 adopt 後的 `governance/` pack、`memory/01~04` scaffold、rule roots 與 readiness surfaces
- 確認 canonical framework source 是否一致
- 確認新版 closeout / runtime status / onboarding report 是否真的在 consuming repo 被看見

這一步的價值是把「framework repo 自己看起來成立」變成「external repo 也真的走得到」。

### 2. Session Workflow 的 semantics observation

`Session Workflow Enhancement` 目前已進入 `implementation-complete, semantics-observation phase`。所以現在更值得做的是觀察，而不是擴功能。

建議持續追的指標：

- canonical closeout valid rate
- `warning_only / none` 的 session 比例
- audit flags 穩定度

這些指標能幫忙判斷：

- `/wrap-up` 是否在實務上形成操作依賴
- frozen taxonomy 是否開始出現 recall 壓力
- closeout audit 的語義是否穩定

### 3. 狀態頁與入口對齊

README、status pages、validation guides、onboarding docs 目前大致已追上主線，但還是要持續檢查是否有舊敘事殘留，避免出現這種落差：

- code 很克制
- 但入口文件暗示 repo 比實際更大、更完整

這一步不是 marketing，而是 anti-expansion guard。

### 4. Consumption / Closeout Shared Path 驗證

closeout visibility 已經存在，但還要持續驗證 consuming repo 的常用途徑到底有沒有真的跑到 `session_end`，而不是只有手動測試能看到。

目前更值得問的是：

- shared enforcement path 是否穩定走到 `session_end`
- 常用 workflow 能否看到 `memory_closeout`
- no-write reason 是否真的被 reviewer / operator 看到

這一步的目標不是 promotion 擴權，而是確認 closeout 不再停在「只有功能存在，實務上沒人走到」。

### 5. Classification / Closeout Companion Surface 維持 bounded

classification governance companion slice 已收主線，但它現在最重要的不是擴大，而是維持 companion posture：

- 不變成第二套 authority
- 不污染主 runtime artifact
- 不追 full matrix coverage

也就是說，這條線接下來的目標是穩定，而不是長大。

## 現在不該優先做的事

以下事情目前都不值得優先：

- 擴更多 advisory signal
- 把 advisory semantics 接進 verdict authority
- 把 closeout / advisory 擴成 machine-facing authority
- 把 runtime injection 推成 full adapter matrix
- 把 execution coverage 做成 full signal × full surface matrix
- 因為「還能做」就繼續延伸已經封邊的 slice

這些方向最大的風險不是做錯，而是讓 repo 再次回到 complexity creep。

## 為什麼這個順序比較對

因為現在主線最大的風險已經不是 skeleton 不夠，而是：

- runtime reality
- boundary documents
- status entry surfaces
- consuming repo adoption

這四者會不會再慢慢漂開。

所以比較好的順序不是「再發明下一個 layer」，而是：

1. 先驗證現在的 bounded runtime 是否真的被使用
2. 再觀察語義與 closeout 分布是否穩定
3. 最後才決定是否有必要重開某條已封邊的 slice

## 一句話總結

> 現在最值得做的不是擴權，而是驗證這個 repo 已經落地的 bounded runtime，是否真的在真實 consuming repo 與 shared workflow 中被穩定消費。
