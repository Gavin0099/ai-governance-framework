# Closeout Repo Readiness：repo 是否已具備 closeout-ready 條件

> 版本：1.0

repo 是否算 `closeout-ready`，不應只看有沒有某個檔案，而應看它是否具備可重建、可觀測、可持續的 session closeout 路徑。

---

## 最低判準

### 1. `AGENTS.base.md` 已導入 closeout obligation

adopt 後的 repo 至少應把 `AGENTS.base.md` 導入，並且保留 `Session Closeout Obligation` 相關段落。  
如果只存在 root `AGENTS.md`，但沒有 baseline obligation，closeout readiness 仍不完整。

### 2. repo 具備 closeout artifact 寫入位置

至少應有能力產出：
- `artifacts/session-closeout.txt`
- runtime verdict / trace / summary artifacts

如果 AI 能寫 candidate，但 repo 沒有地方承接 canonical closeout，不能算 ready。

### 3. stop hook 或等價 closeout path 已接入

repo 不一定非得用同一種 stop hook，但至少要有可被觀測的 closeout entry path，讓 `session_end_hook.py` 或等價流程可以被觸發。

### 4. reviewer 可讀到 closeout 狀態

至少要能分辨：
- `valid`
- `missing`
- `insufficient`
- 以及對應的 runtime verdict / reason

## 不應誤判為 ready 的情況

以下情況通常還不能視為 closeout-ready：
- 只有 `AGENTS.md`，沒有 baseline obligation
- 只有 candidate artifact，沒有 canonical closeout
- 有 stop hook 設定，但從未觀測到真實 closeout run
- 有 verdict artifact，但無法說明 closeout 為何 missing / insufficient

## 與 activation 的關係

repo readiness 描述的是結構能力；是否最近真的跑過 closeout，則應由 `closeout_activation_state` 與 `activation_recency` 補充。  
也就是說：
- readiness != activation
- activation != quality

## 一句總結

`closeout repo readiness` 要回答的是：這個 repo 是否已具備讓 closeout 成為正常治理流程一部分的最低結構條件，而不是只看它曾不曾產生過某個 artifact。
