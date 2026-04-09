# Closeout Readiness Rollout：closeout readiness 的分階段導入方式

> 版本：1.0  
> 關聯文件：`docs/closeout-readiness-spectrum.md`、`docs/closeout-repo-readiness.md`

---

## 目的

當 `baselines/repo-min/AGENTS.base.md` 開始導入 `Session Closeout Obligation` 後，readiness audit 與 consuming repo adopt 不能一次跳到最嚴格模式。

這份文件定義的是：
- 如何把 closeout obligation 漸進導入到 repo
- 如何讓 readiness audit 從 `Level 0` 慢慢提升
- 如何保持 observable、incremental、rollback-safe

## Rollout 原則

### 1. Observable

每一步都要能被看見：
- `AGENTS.md` / `AGENTS.base.md` 是否已導入 obligation
- stop hook 或等價 closeout path 是否可見
- verdict / summary 是否開始帶出 closeout 狀態

### 2. Incremental

不要把「有 closeout obligation」直接當成「所有 repo 都已 closeout-ready」。  
readiness 應允許：
- 先有 obligation
- 再有 wiring
- 再有 activation
- 最後才有較成熟的 reviewer-facing interpretation

### 3. Rollback-Safe

如果某個 rollout slice 失敗，應能回退到較保守的 readiness posture，而不是把 repo 直接推入不可用狀態。

## 建議分期

### Phase 0：結構導入

- adopt 會帶入 `AGENTS.base.md`
- repo 出現 closeout obligation
- readiness 只記錄結構存在，不判定 activation

### Phase 1：closeout path 可見

- stop hook 或等價 `session_end` closeout path 已可觀測
- reviewer 能看到 closeout 缺失原因
- readiness 可開始標記 `pending` / `observed`

### Phase 2：activation 被觀測

- verdict / summary 中可見真實 closeout run
- `memory_closeout` 或等價結構可被 reviewer 判讀
- readiness 可開始使用 activation recency

### Phase 3：bounded closeout maturity

- closeout lane 穩定
- reviewer 能區分結構 readiness、activation 與 quality
- 但仍不把 closeout readiness 誤當成 verdict authority

## 不該做的事

這份 rollout 目前**不主張**：
- obligation 一上線就視為所有 repo 已 ready
- 把 closeout activation 直接當成 quality 保證
- 用 closeout readiness 直接決定 allow / deny

## 一句總結

closeout readiness rollout 的重點，不是追求一步到位，而是讓 consuming repo 能以可觀測、可回退、可分層的方式逐步進入 closeout governance。
