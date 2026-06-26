# AI Governance 第一天快速上手

狀態：第一天使用者 quickstart
權威性：非 canonical guidance
適用對象：第一次把 AI Governance 套用到 repo 的使用者

## 先記住這 6 件事

第一天不用讀完所有治理文件。先記住：

1. 先說現在是什麼模式。
2. 目標要小，不要一次全修。
3. diagnosis 只看狀態，不代表要修。
4. review 只審證據，不改檔。
5. push 一定要另外授權。
6. agent 只能宣稱驗證證據支持的事。

這份文件不是完整訓練教材，不是治理權威，也不會讓 agent 自動合規。如果
它和 `AGENTS.md` 或 `governance/` 底下的規則衝突，以 repo governance
文件為準。

## 套用後會有什麼不一樣

AI Governance 不是安全沙箱，也不會自動讓 AI 變聰明。它主要改變的是：
AI 做事時必須說清楚範圍、留下證據，並且不能宣稱超過證據支持的事。

你會看到幾個差異：

- 任務會先收斂成一個小目標，而不是一路做下去。
- agent 會說明這次會做什麼，也會說明不會做什麼。
- 診斷工具會先回報狀態，不會自動修 repo。
- review 會先看證據，不只看「看起來完成了」。
- push 會被當成獨立動作，不會因為 commit 完就自動發生。

最重要的一句話：

> AI Governance 的價值不是讓 agent 更有自信，而是讓 agent 更難亂宣稱。

## 第一天最好怎麼下指令

用這個格式最穩：

```text
DONE = <一個很小、可驗證的目標>
mode = <diagnosis only | implementation | read-only review | push/verify>
scope = <允許碰的範圍>
non-goals = <明確不做的事>
validation = <完成前要看的證據或要跑的檢查>
claim ceiling = <這次最多只能宣稱什麼>
```

`claim ceiling` 的白話意思是：這次完成後，agent 不能宣稱超過驗證證據
支持的事。

範例：

```text
claim ceiling = only say README was updated and markdown check passed;
do not claim runtime behavior changed
```

## 常用模式

| Mode | 你想做什麼 | 你應該期待什麼 |
|---|---|---|
| `diagnosis only` | 看 repo 現在狀態。 | 回 findings 和下一步，不修。 |
| `implementation` | 做一個小變更。 | 只改 scope 內檔案，跑對應驗證。 |
| `read-only review` | 審 diff、PR、commit。 | 只給 verdict，不改檔。 |
| `proposal/design-only` | 先寫設計，不改行為。 | 產出 proposal，不宣稱已實作。 |
| `push/verify` | 推已 review 的 commit。 | push 後驗證 remote heads。 |

如果你不知道該用哪個，先用 `diagnosis only`。

## 日常任務怎麼問

### 1. 請 AI 幫你改 README

```text
DONE = update README wording for the install section only.
mode = implementation
scope = README.md only
non-goals = no code changes, no behavior changes, no release claims
validation = git diff --check README.md
claim ceiling = README wording updated only
```

### 2. 請 AI review 一個 PR 或 commit

```text
DONE = read-only review this diff.
mode = read-only review
scope = provided diff only
non-goals = no file edits, no commit, no push
validation = findings must cite file/line evidence
claim ceiling = review verdict only
```

### 3. 檢查 repo 有沒有套好 AI Governance

```text
DONE = diagnose this repo's AI Governance adoption state; no repair.
mode = diagnosis only
scope = this repo read-only
non-goals = no fetch, no file edits, no commit, no push
validation = adoption diagnosis output + git status summary
claim ceiling = findings and recommended next slice only
```

### 4. 請 AI push 剛剛的 commit

```text
DONE = push <source-commit> + <memory-commit> to origin/main and gitlab/main,
then verify both remote-tracking heads match <memory-commit>.
mode = push/verify
scope = named commits only
non-goals = no extra commits, no unrelated cleanup
validation = origin/main and gitlab/main resolve to the expected commit
claim ceiling = pushed and verified these commits only
```

## 為什麼第一天不要一次全修

- `full repair` 容易把診斷、修復、review 混在一起。
- `full regression` 可能還不知道這個 repo 正確的驗證入口。
- hook、CI、enforcement 會改變治理強度，不只是修文件。
- 清理 dirty files 可能誤刪或覆蓋使用者還要保留的工作。
- 一次讀完所有 governance 文件，通常只會讓第一個任務變慢。

第一天的目標不是把 repo 修完，而是讓狀態、證據、下一步變清楚。

## 看到診斷結果後怎麼做

診斷結果不是修復結果。

如果工具回報 warning，先問：

```text
請只根據這份 diagnosis，建議下一個最小 repair slice。
不要 fetch、不要改檔、不要 commit、不要 push。
```

這會避免 agent 看到 warning 後順手做太多。

## 三個最容易誤會的式子

請先記住這三句：

```text
adoption != governed execution
memory_binding != truth/review/push
diagnosis != repair
```

意思是：

- 套用了 AI Governance，不代表每個執行入口都已經被治理。
- memory 綁到 commit，不代表內容已被證明、review 或 push。
- 診斷找到問題，不代表問題已經修好。

## 進階補充：Memory 怎麼看

第一天不需要先學完整 memory protocol，但要知道：

- memory 是治理記錄，不是聊天筆記。
- 新的 session-derived memory 要用 canonical writer。
- memory 的 `next_step` 是候選下一步，不是現在的授權。
- 如果 feature branch 有 memory，MR 或 merge 後要確認它和最終 main commit
  的關係。

簡單說：memory 是證據的一部分，不是證據的全部。

## 這份 quickstart 的邊界

這份文件只是第一天使用者 quickstart。

它不改變：

- `AGENTS.md`；
- governance routers；
- `governance_tools/`；
- `runtime_hooks/`；
- hooks、CI、pre-push、gate、enforcement；
- memory protocol。

它也不代表新人已完整 onboard，或 agent 會自動遵守所有治理規則。
