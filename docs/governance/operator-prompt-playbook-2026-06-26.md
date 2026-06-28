# 操作者提示詞手冊（Operator Prompt Playbook）- 2026-06-26

狀態（Status）：`proposal/design-only`
範圍（Scope）：使用者與操作者快速參考
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
治理權威（governance authority）變更：否
強制執行（enforcement）變更：否

## 問題

這個儲存庫近期最可靠的工作方式，不是擴大治理表面，而是縮小並固定操作者習慣：

1. 先命名任務模式（task mode）；
2. 定義一個可衡量的 `DONE`；
3. 明確列出範圍（scope）與非目標（non-goals）；
4. 只驗證已變更的表面；
5. 分開做審查（review）；
6. 只有在明確授權後才推送（push）。

當這些欄位缺失時，像 `continue`、`proceed`、`keep going`、`go next` 或等價的簡短續行指令，可能讓代理（agent）把下一個切片推論得太寬。這份手冊記錄可重複使用的提示詞片段，讓操作者與代理在工作開始前先對齊。

這不是新的治理規則。它只是用較輕量的方式，把既有規則帶進當下的執行脈絡。

## 目前儲存庫事實

與本手冊相關的已觀察規則與表面如下：

- `AGENTS.md` 要求：除非已有狹窄的下一切片邊界，模糊續行指令必須先進入審計優先（audit-first）行為。
- `AGENTS.md` 要求：除非使用者已提供，實作編輯前必須有具體的 `DONE = <one measurable product outcome>`。
- `governance/REVIEW_CRITERIA.md` 將審查定義為帶有懷疑態度、以證據支撐發現的驗證。
- `governance/RESPONSE_ENVELOPE_CONTRACT.md` 要求最終回報中，結果、宣稱上限（claim ceiling）、非宣稱（non-claims）、證據、風險與下一步必須分開。
- `governance/MEMORY_PROTOCOL.md` 要求 session-derived repository memory 使用 canonical writer。
- 近期採用工作顯示：只放在文件裡的提醒，如果沒有進入實際執行路徑，很容易失效。因此這份手冊最有用的形式，是作為可貼進提示詞的文字，而不是新的權威層。

## 目標結果

為這個儲存庫常見任務模式提供短而可重用的提示詞模板：

- 實作（implementation）；
- 唯讀審查（read-only review）；
- 只診斷（diagnosis only）；
- 提案或純設計（proposal/design-only）；
- 推送與驗證（push/verify）。

目標是降低範圍模糊，而不是增加強制執行。

## 範圍

本手冊涵蓋：

- 任務模式標籤；
- 可重用的任務標頭；
- 各模式的提示詞片段；
- 儲存庫啟動檢查提示；
- 宣稱上限片段；
- 審查、記憶、提交與推送的排序提醒。

## 非目標

本手冊不會：

- 修改 `AGENTS.md`；
- 修改治理路由器；
- 修改記憶協議（memory protocol）；
- 修改執行環境 hook（runtime hooks）；
- 修改工具行為；
- 新增 CI、pre-push、gate 或強制執行行為；
- 要求代理自動讀取這份文件；
- 讓任何提示詞模板本身變成權威；
- 證明未來代理一定會遵守這些片段。

## 受影響表面

這個提案直接影響：

- `docs/governance/operator-prompt-playbook-2026-06-26.md`

不受影響：

- `AGENTS.md`
- `governance/*.md` 路由器
- `governance_tools/**`
- `runtime_hooks/**`
- 結構描述（schemas）
- hooks
- CI
- 記憶寫入器行為

## 邊界與 API 考量

這份文件是操作者輔助資料。它不應被執行環境程式碼匯入，不應被引用為 canonical governance router，也不應被視為強制執行契約。

如果未來某個切片要讓這份內容影響執行，那必須是另一個獨立設計與審查。本文件只記錄提示詞側的使用方式。

## 標準任務標頭

開始非平凡任務時，使用這個標頭：

```text
DONE = <one measurable outcome>
mode = implementation | read-only review | diagnosis only | proposal/design-only | push/verify
scope = <allowed files/repos/surfaces>
non-goals = <what must not change or be claimed>
validation = <focused checks only>
claim ceiling = <what this can safely prove>
commit/push intent = <no commit | commit after review | push only after explicit authorization>
```

對實作任務，在編輯前先覆述已核准切片：

```text
Executing approved slice:
DONE = <copied DONE>
scope = <copied scope>
non-goals = <copied non-goals>
```

## 模式模板

### 實作

代理需要編輯檔案時使用。

```text
DONE = <specific change>; mode = implementation.
scope = <exact files or directory>.
non-goals = no unrelated cleanup, no enforcement change, no runtime behavior
change outside the stated scope, no push.
validation = <focused tests/checks>.
commit intent = do not commit until review | commit source/test after approval.
```

### 唯讀審查

代理必須驗證 artifact、diff、commit 或儲存庫狀態，且不得改檔時使用。

```text
DONE = review <artifact/commit pair/diff>; mode = read-only review.
Do not modify files, stage, commit, or push.
Verify repo state, scope, diff, memory binding, evidence, claim ceiling, and
non-claims.
Return findings first, then verdict, risk, evidence, cannot-claim, and next-step
judgment.
```

### 只診斷

代理應檢查狀態並找出原因，但不得修復時使用。

```text
DONE = diagnose <repo/system/state>; mode = diagnosis only.
scope = read-only inspection of <paths/repos>.
non-goals = no repair, no fetch unless explicitly allowed, no commit, no push,
no rewriting local state.
validation = commands or artifacts that support the diagnosis.
claim ceiling = findings and recommended next slice only.
```

### 提案或純設計

代理應撰寫或審查提案，但不得實作時使用。

```text
DONE = write a design-only proposal for <problem>; mode = proposal/design-only.
scope = one docs file.
non-goals = no code behavior change, no tooling/runtime/hook/CI/enforcement
change, no implementation commitment.
validation = scope check, UTF-8/mojibake/trailing-whitespace check, and review.
claim ceiling = proposed scope and evidence plan only.
```

### 推送與驗證

只在 commit pair 已經審查且核准後使用。

```text
DONE = push <commit(s)> to origin/main and gitlab/main, then verify both
remote-tracking heads match <expected head>.
mode = push/verify.
scope = git push/fetch/rev-parse only.
non-goals = no new edits, no commit, no repair.
validation = HEAD, origin/main, and gitlab/main all equal <expected head>.
```

## 儲存庫啟動檢查提示

治理刷新、拉取或採用問題，應先診斷再修復：

```text
mode = diagnosis only.
Check repo state before recommending repair:
- git status and branch ahead/behind;
- dirty/conflict state;
- submodule/gitlink state;
- framework lock or framework pin state;
- readiness/onboarding validator relevant to this repo;
- repo-specific validator or smoke path;
- memory or push gate state when memory/push is in scope.
Do not repair, commit, or push until the next slice is explicit.
```

這可避免混淆：

- 治理刷新成功與 parent pull 完成；
- framework lock 目前性與 readiness 乾淨度；
- 靜態 self-contained 證據與 runtime hook 執行；
- memory bound 狀態與 truth、review、commit 或 push 證明。

## 宣稱上限片段

使用最短且準確的非宣稱句。

```text
proposal-only; no behavior changed
docs-only; no runtime/tooling/enforcement change
diagnosis-only; no repair performed
refresh completed; parent pull still not claimed
observation-only; not source commit evidence
memory bound; not truth/review/push proof
static self_contained; runtime_capable not checked
current_vs_local_tracking; true remote currentness not claimed
preview shows candidates only; no delete/apply unless explicitly authorized
LTSSM/link-training only; non-LTSSM remains advisory
no verified uplift; claim ceiling unchanged
```

## 排序模式

治理敏感工作偏好的順序：

```text
small slice -> focused validation -> read-only review thread -> commit pair
-> review commit pair -> explicit push/verify -> stop
```

推送後不要自動進入下一個切片。建議一個下一步，然後等待新的 `DONE`，除非下一個切片已經被明確核准。

## 子代理審查回執工作流

主執行緒需要懷疑式唯讀審查，但不交出行動權威時，使用這個子代理（sub-agent）工作流。

邊界：

```text
Main owns action.
Sub-agent owns skepticism.
Receipt returns evidence.
Main spot-checks key evidence.
Push, commit, memory writes, and authority changes still require main-thread
decision plus user authorization where applicable.
```

預設機制：

- 一般審查工作預設使用子代理工具（sub-agent tools）；
- 用 `multi_agent_v1.spawn_agent` 建立審查子代理；
- 用 `multi_agent_v1.wait_agent` 等待回執；
- 需要修正或追加說明時，用 `multi_agent_v1.send_input` 回到同一個子代理；
- 完成後用 `multi_agent_v1.close_agent` 關閉子代理；
- 不把側欄 Codex thread 當作預設審查機制；
- 只有當使用者明確要求 user-visible separate thread，或 sub-agent tools 不可用且使用者核准 fallback 時，才使用側欄 thread tools。

如果目前 session 沒有子代理工具，主執行緒必須先回報這個限制，再使用任何 fallback。不得偷偷用可見 thread、一般 ChatGPT thread 或人工 copy/paste 工作流取代子代理審查。

模型選擇：

- 預設繼承主執行緒模型；
- 只有在簡單、低風險、唯讀審查，且任務邊界明確、預期輸出是結構化回執，並且沒有委派權威、runtime、memory、push、cross-repo 或 claim-sensitive 決策時，才使用 `gpt-5.3-codex-spark`；
- 對治理權威變更、runtime 權限問題、mutation-adjacent 工作、push-gate 評估、語意正確性宣稱或有爭議的審查發現，使用繼承的主模型或明確更強的模型。

決策規則：

- 不要另開一般 ChatGPT 對話，再要求使用者把結果 copy 回主執行緒。這會遺失脈絡、增加複製錯誤，並中斷宣稱鏈。
- 當使用者要求 review、audit 或懷疑式平行審查時，偏好 sub-agent tools。主執行緒送出有邊界的任務，等待回執，整合結果，並決定下一步。
- polling 應理解為主執行緒在工具層等待或讀取結果，不是讓使用者手動輪詢。正常流程中，使用者不應需要把審查文字搬回主執行緒。
- sub-thread 可以執行檢查並回傳 `REVIEW_RECEIPT`，但不得擁有最終行動權威。它可以說 `APPROVED_FOR_PUSH_GATE`；真正 push 前，主執行緒仍需等待使用者明確授權。

當使用者明確要求獨立 Codex thread 時：

- 主執行緒建立有邊界的審查 thread；
- 審查 thread 只回傳 `REVIEW_RECEIPT`；
- 主執行緒用 `codex_app.read_thread` 讀取審查結果；
- 需要第二輪審查時，主執行緒用 `codex_app.send_message_to_thread` 把後續修正送回去；
- 使用者 copy/paste 審查結果只作為 fallback，不是正常工作流；
- 主執行緒在自行拉回 receipt 並做最後 gate 決策前，不得 commit、push、寫 memory 或升級宣稱。

唯讀子代理可使用這個提示詞形狀：

```text
Read-only sub-agent task. Do not modify files, stage, commit, or push.

Task: review <artifact/diff/commit pair/state>.
Return ONLY this receipt:

REVIEW_RECEIPT
verdict: APPROVED | CHANGES_REQUESTED | ESCALATED
blocking_findings:
warnings:
suggestions:
evidence_checked:
claim_ceiling:
cannot_claim:
push_gate: allowed | not_allowed | not_applicable
next_recommended_action:
```

`evidence_checked` 必須包含實際命令與結果、檔案行號引用或 artifact 路徑。不得只是 `checked=yes` 或意圖清單。主執行緒在任何敏感行動前，必須重新抽查關鍵證據。

把子代理的 `APPROVED` verdict 視為需要檢視的證據，而不是權威。是否修正、commit、寫 memory、要求 push 授權或停止，都由主執行緒決定。

## 跨儲存庫寫入邊界

當任務所在 workspace 暴露多個儲存庫或 writable root 時，使用這個邊界。

規則：

```text
Writable root is capability, not authorization.
Active repo owns the write scope.
All other repos are read-only unless explicitly authorized by path.
```

實作切片在開始編輯前必須命名 `active_repo`。如果使用者說 `continue`、`keep going`、中文續行詞或類似續行文字，該授權只適用於已核准的作用中儲存庫與範圍內。
它不授權寫入其他儲存庫，即使該儲存庫可見、與主題相關，或工具具有寫入能力。

可攜補丁、設計筆記與實作包預設留在產生它們的來源儲存庫。把可攜補丁套用到目標儲存庫，是另一個跨儲存庫寫入，必須由使用者明確命名目標路徑。

任何跨儲存庫寫入前都必須停下並詢問，除非使用者已給出明確的路徑層級指令，例如：

```text
Apply this patch to D:\ai-governance-framework.
Modify D:\Enumd-private-vault only.
Do not touch any other repo.
```

如果發現非預期跨儲存庫寫入：

- 立刻停止；
- 回報作用中儲存庫、被碰到的儲存庫與路徑；
- 除非使用者明確授權清理範圍，不得檢查、stage、commit、刪除或修復超出範圍的檔案；
- 只在使用者核准的儲存庫邊界內恢復工作。

## 失敗路徑與風險點

- 如果這份文件被視為權威，它會在沒有真實強制執行路徑的情況下變成新的治理表面。
- 如果片段被複製時沒有具體的 `scope` 和 `non-goals`，它們會變成裝飾性文字，而不是有用的任務邊界。
- 如果 `proposal/design-only` 與實作混在一起，審查無法判定行為是否改變。
- 如果 push 與實作綁在同一包，遠端交付可能早於 memory binding 與 claim ceiling 的審查。
- 如果診斷滑向修復，dirty parent repo 與 submodule pin 可能在所有權釐清前被改掉。
- 如果子代理回執被視為權威，工作流只是把 overclaim 風險從主執行緒移到子代理。
- 如果 `evidence_checked` 沒有具體命令或檔案引用，主執行緒就沒有可抽查的關鍵證據。
- 如果 writable roots 被當成使用者意圖，代理可能把來源儲存庫的設計包，悄悄變成未授權的目標儲存庫寫入。

## 證據計畫

對這份 docs-only 手冊：

- 確認只有這份文件被新增或修改；
- 確認內容可正常讀取且沒有尾端空白；
- 確認沒有修改 `AGENTS.md`、治理路由器、工具、hooks、CI 或 memory protocol。

## 實作切片建議

這份文件就是完整預期切片。

審查者接受下列宣稱上限後，下一個可能行動才是 commit 加 canonical memory：

```text
operator quick-reference only; no governance authority or enforcement change
```
