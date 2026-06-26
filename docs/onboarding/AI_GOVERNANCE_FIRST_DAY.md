# AI Governance 第一天快速上手

狀態：第一天使用者 quickstart
權威性：非 canonical guidance
適用對象：第一次把 AI Governance 套用到 repo 的使用者

## 這份文件回答什麼

這份文件只回答兩件事：

1. 套用 AI Governance 之後，工作方式會有什麼不一樣。
2. 第一天怎麼用最不容易踩錯。

它不是完整訓練教材，不是治理權威，也不會讓 agent 自動合規。如果這份
文件和 `AGENTS.md` 或 `governance/` 底下的規則衝突，以 repo governance
文件為準。

## 套用後會有什麼不一樣

AI Governance 不會替你寫更多功能，也不是安全沙箱。它改變的是「AI 做事
時要留下什麼證據、不能亂宣稱什麼、什麼時候該停下來」。

套用後，你會看到幾個明顯差異：

- 任務會先被收斂成明確 DONE，而不是一路做下去。
- agent 會先說 scope、non-goals、validation、claim ceiling。
- review 會先看 evidence，而不是只看「看起來完成了」。
- memory 會記錄重要決策和證據，但 memory 本身不等於真相。
- 診斷工具通常先 report-only，不會自動修 repo。
- push 會被當成獨立 gate，不會因為本地 commit 完成就自動發生。

最重要的改變是：AI Governance 會降低「AI 說完成，但其實只是完成一部分」
的機率。它不是讓工作變零成本，而是把錯誤宣稱、漏驗證、錯誤 repair 的
成本提前暴露。

## 第一天怎麼用最好

第一次使用時，不要一開始就要求大範圍修復。先用小任務熟悉邊界。

建議你這樣下指令：

```text
DONE = <一個很小、可驗證的目標>
mode = diagnosis only | implementation | read-only review
scope = <允許碰的檔案或 repo 範圍>
non-goals = <明確不做的事>
validation = <完成前要跑的檢查>
claim ceiling = <這次最多能宣稱什麼>
```

範例：

```text
DONE = diagnose this repo's AI Governance adoption state; no repair.
mode = diagnosis only
scope = this repo read-only
non-goals = no fetch, no file edits, no commit, no push
validation = adoption doctor output + git status summary
claim ceiling = findings and recommended next slice only
```

這種寫法會讓 agent 知道：現在是診斷，不是修復；可以看證據，但不能順手
改檔。

## 常用模式

你不需要一開始懂所有 governance 文件。先分清這幾種模式就夠：

| Mode | 你想做什麼 | 你應該期待什麼 |
|---|---|---|
| `diagnosis only` | 看 repo 現在狀態。 | 回 findings 和下一步，不修。 |
| `implementation` | 做一個已定義的小變更。 | 改 scope 內檔案，跑對應驗證。 |
| `read-only review` | 審某個 diff 或 commit。 | 只給 verdict，不改檔。 |
| `proposal/design-only` | 先記錄設計，不改行為。 | 產出 proposal，不宣稱已實作。 |
| `push/verify` | 把已 review 的 commit 推上 remote。 | push 後驗證 remote heads。 |

如果你不知道該用哪個，先用 `diagnosis only`。

## 最推薦的第一個任務

第一天最適合做的是 report-only diagnosis。

例如：

```powershell
python -m governance_tools.adoption_doctor --repo <repo> --format human
```

這類工具的目的不是修 repo，而是告訴你：

- 這個 repo 比較像 copy-based adoption、submodule consumer，還是 unknown。
- 靜態 self-contained 條件是否存在。
- hooks 是否指向 repo 內 framework，或仍指向外部 checkout。
- submodule pin 是否只相對本地 tracking 落後。
- 有沒有 root-level runtime hook leftover 這類可疑狀態。

看到 warning 時，不要立刻修。先問：

```text
請只根據這份 diagnosis，建議下一個最小 repair slice。
不要 fetch、不要改檔、不要 commit、不要 push。
```

## Memory 要怎麼理解

AI Governance 的 memory 是治理記錄，不是聊天筆記。

正確理解：

- memory 記錄做了什麼、證據是什麼、下一步是什麼。
- 新的 session-derived memory 要用 canonical writer。
- `memory_binding: bound` 只表示 memory 綁到一個像 commit hash 的值。

不能這樣理解：

- 有 memory 就代表內容是真的。
- `bound` 就代表已 review。
- `bound` 就代表已 push。
- memory 的 `next_step` 就是現在的授權。

如果你在 feature branch 上工作，可以有 branch memory；但 MR 或 merge 後要
確認 memory 和最終 main commit 的關係，不要把 branch hash 說成 main 的
最終證據。

## 最容易誤會的三件事

請先記住這三句：

```text
adoption != governed execution
memory_binding != truth/review/push
diagnosis != repair
```

意思是：

- 套用了 AI Governance，不代表所有執行都已被治理。
- memory 綁了 commit，不代表內容已被證明。
- 診斷找到問題，不代表已經修好。

## 第一天不要做什麼

不要一開始就要求：

- full repair；
- full regression；
- release publish；
- hook / CI / enforcement 升級；
- 清理所有 dirty files；
- 一次把所有 governance 文件讀懂。

這些都可以做，但不適合當第一個任務。

第一天的目標很簡單：讓 repo 狀態、證據、下一步變清楚。

## 好的使用方式

好的 AI Governance 使用方式不是「讓 agent 更有自信」，而是讓 agent 更難
亂宣稱。

你可以一直用這個節奏：

1. 先 diagnosis。
2. 再選一個小 repair slice。
3. repair 後 review。
4. review 通過再 commit。
5. push 前明確授權。
6. push 後驗證 remote heads。

每一步都只宣稱它真的證明的事。

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
