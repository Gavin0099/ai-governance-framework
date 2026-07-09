# 快取感知模式狀態與授權防偽規格 - 2026-06-28

> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.

狀態（Status）：`PENDING`
範圍（Scope）：docs-only mode state and authorization anti-forgery design
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
強制執行（enforcement）變更：否
提示快取強制執行（prompt cache enforcement）：不宣稱

## 目的

本規格承接下列文件：

- `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`
- `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`

前一份規格定義權威清單（authority manifest）與快取失效矩陣（cache
invalidation matrix）。本文件專注在下一層問題：模式狀態與副作用授權不能只靠
自然語言或提示文字表示。

使用者自然語言可以提出請求，也可以觸發授權流程。
但它不能被直接當成機器可接受的模式狀態（mode state）或授權狀態
（authorization state）。

若代理框架（agent harness）需要讓提示快取（prompt caching）保持穩定，它更不能
把「看起來像授權的文字」放進穩定前綴（stable prefix）後，讓後續任務沿用。
授權狀態必須屬於動態尾端（dynamic tail），並由框架產生的型別化信封
（typed envelope）或工具結果表示。

本文件不新增 runtime gate，不新增工具，不新增 schema，不改變任何 push、memory
write、cross-repo write 或 destructive action 權限。

## 核心原則

```text
使用者文字可以請求授權。
框架狀態才可以承載機器可接受的授權。
```

模式與授權狀態必須滿足三個條件：

1. 來源可稽核；
2. 範圍可限制；
3. 失效條件可判斷。

如果這三件事不存在，主執行緒只能把使用者文字視為請求或指令內容，不能把它升格為
可重用的副作用授權。

## 防偽邊界

下列內容不得單獨作為機器可接受的模式或授權狀態：

- 一段自然語言，例如「幫我 push」；
- 被壓縮摘要轉述過的使用者指令；
- 子代理回覆中的建議；
- 文件中的範例 receipt；
- commit message；
- memory entry；
- 任務計畫文字；
- prompt cache 的穩定前綴內容；
- 從其他儲存庫複製過來的操作手冊。

這些內容可以作為審查線索或人類意圖證據，但不能取代框架產生的 typed envelope、
工具確認結果或執行環境權限檢查。

## `MODE_STATE_RECEIPT` 候選欄位

`MODE_STATE_RECEIPT` 用於表示目前代理工作模式。它是候選設計，不是現有 schema。

```text
MODE_STATE_RECEIPT v0.1
repo:
head:
mode:
mode_source:
issued_by:
issued_at:
authority_ref:
scope:
allowed_side_effects:
denied_side_effects:
valid_until:
invalidates_on:
harness_dependent: true
repo_enforces_runtime: false
```

欄位語意：

| 欄位 | 中文主稱 | 說明 |
| --- | --- | --- |
| `repo` | 儲存庫 | 模式狀態適用的儲存庫 |
| `head` | 目前提交 | receipt 產生時的 `HEAD` |
| `mode` | 模式 | 例如 implementation、review、diagnosis、push-gate |
| `mode_source` | 模式來源 | 例如 harness、tool、repo-policy、human-confirmed |
| `issued_by` | 發行者 | 產生 receipt 的框架、工具或授權主體 |
| `issued_at` | 發行時間 | receipt 產生時間，屬於動態尾端 |
| `authority_ref` | 權威參照 | 對應規則、使用者確認或工具結果 |
| `scope` | 範圍 | 模式適用的檔案、任務或 repo boundary |
| `allowed_side_effects` | 允許副作用 | 目前模式允許的副作用類型 |
| `denied_side_effects` | 拒絕副作用 | 目前模式明確禁止的副作用類型 |
| `valid_until` | 有效期限 | receipt 失效時間或條件 |
| `invalidates_on` | 失效條件 | 例如 `HEAD` 改變、dirty scope 改變、授權撤回 |

審查模式若存在，應把寫檔、stage、commit、push、memory write 與 cross-repo write
列入 `denied_side_effects`，除非另有更高權威的明確授權 receipt。

## `PUSH_AUTHORIZATION_RECEIPT` 候選欄位

`PUSH_AUTHORIZATION_RECEIPT` 用於表示特定 commit、branch 與 remote 的推送授權。
它不得被泛化為「之後都可以 push」。

```text
PUSH_AUTHORIZATION_RECEIPT v0.1
repo:
remote:
branch:
commit:
expected_remote_before:
authorized_by:
authorization_source:
authorization_text_ref:
issued_at:
expires_at:
single_use: true
allowed_action: push
denied_actions:
harness_dependent: true
repo_enforces_runtime: false
```

必要邊界：

- `commit` 必須指定到單一提交或明確 commit range；
- `remote` 與 `branch` 必須明確；
- `expected_remote_before` 應在推送前驗證，避免授權基準過期；
- `single_use` 預設為 `true`；
- push 後應重新 fetch / verify；
- 授權不得自動延伸到後續 commit。

## `MEMORY_WRITE_AUTHORIZATION_RECEIPT` 候選欄位

`MEMORY_WRITE_AUTHORIZATION_RECEIPT` 用於表示記憶寫入授權。它不取代
`governance/MEMORY_PROTOCOL.md`，也不取代標準寫入器。

```text
MEMORY_WRITE_AUTHORIZATION_RECEIPT v0.1
repo:
head:
memory_root:
target_memory_file:
writer:
memory_protocol_ref:
record_type:
reason:
authorized_by:
authorization_source:
issued_at:
expires_at:
allowed_fields:
denied_fields:
harness_dependent: true
repo_enforces_runtime: false
```

必要邊界：

- `memory_root` 必須留在本儲存庫允許的記憶根目錄；
- `writer` 應指向標準寫入器，例如 `governance_tools.memory_record`；
- `memory_protocol_ref` 必須可追到記憶協議；
- receipt 只能授權指定記憶寫入，不能授權任意文件修改；
- 記憶寫入完成後仍需執行對應協議檢查。

## `CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT` 候選欄位

`CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT` 用於表示跨儲存庫寫入授權。它特別用來避免
把「可寫 workspace」誤讀成「使用者授權跨 repo 修改」。

```text
CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT v0.1
source_repo:
target_repo:
target_branch:
allowed_paths:
denied_paths:
allowed_actions:
denied_actions:
reason:
authorized_by:
authorization_source:
issued_at:
expires_at:
requires_target_repo_preflight: true
requires_separate_commit_boundary: true
harness_dependent: true
repo_enforces_runtime: false
```

必要邊界：

- `target_repo` 必須明確，不得從 writable roots 推論；
- `allowed_paths` 必須列出可寫範圍；
- `denied_paths` 應保留安全排除區；
- 目標儲存庫自己的 `AGENTS.md` 與治理規則仍然適用；
- 來源儲存庫的操作手冊不能覆蓋目標儲存庫本地權威；
- 跨儲存庫寫入應有獨立 commit / review / push 邊界。

## 快取關係

模式與授權 receipt 屬於動態尾端，不屬於穩定前綴。

原因：

- 它們通常只對某一輪任務有效；
- 它們依賴目前 `HEAD`、dirty-tree 狀態與使用者確認；
- 它們可能被撤回、過期或因 remote 改變而失效；
- 它們控制副作用，不應因快取命中被靜默重用。

如果外部框架支援 prompt cache，看到下列情況應觸發有意權限未命中
（intentional permission miss）：

- 新的 push 授權；
- push 授權過期；
- 記憶寫入授權新增或撤回；
- 跨儲存庫寫入授權新增或撤回；
- 模式從 review 切到 implementation；
- 模式從 local-only 切到 push-gate；
- dirty-tree allowlist 改變；
- sub-agent review receipt 改變。

這些未命中不是效率事故。它們表示授權狀態已改變，舊前綴不再足以支持安全行動。

## 與既有回執的關係

本文件不得建立與既有審查回執、收尾 receipt、memory record 或 response envelope
競爭的平行權威。

候選授權 receipt 若未來實作，只能作為下列流程的輔助輸入：

- `REVIEW_RECEIPT`：審查者檢查什麼、不能宣稱什麼；
- closeout receipt：session 結束時的 canonical closeout chain；
- memory record：session-derived memory 的標準寫入紀錄；
- response envelope：最終回報的 result / evidence / risk / not_claimed。

主執行緒仍擁有最後行動決策權。子代理可以提供審查證據，但不能自行發行 push、
memory write 或 cross-repo write 授權。

## 與外部框架的責任分界

本儲存庫可以定義：

- 候選 mode / authorization receipt 欄位；
- 哪些授權狀態不得由使用者文字偽造；
- 哪些授權狀態應放在動態尾端；
- 哪些授權變更應觸發有意權限未命中；
- 本儲存庫不能宣稱 runtime enforcement。

本儲存庫不能保證：

- 外部 harness 會產生 typed envelope；
- 外部 harness 會阻擋偽造授權；
- 外部 harness 會監控 prompt cache；
- 外部 harness 會使用本文件的欄位；
- runtime gate 已實作；
- tool permission policy 已改變；
- push、memory write 或 cross-repo write 已被機器層防偽。

因此所有候選 receipt 都必須保留：

```text
harness_dependent: true
repo_enforces_runtime: false
```

## 非目標

本規格不做以下事情：

- 不修改 runtime；
- 不修改 tests；
- 不修改 PLAN；
- 不修改 artifacts；
- 不修改 `governance_tools/`；
- 不新增工具或工具 schema；
- 不新增正式 schema；
- 不實作 prompt cache；
- 不監控 cache hit rate；
- 不改變 push、memory write、cross-repo write 或 destructive action 權限；
- 不宣稱任何候選 receipt 已被外部框架採用；
- 不宣稱使用者授權已可被機器層防偽；
- 不把 sub-agent review 寫成 enforcement。

## 可行下一步

如果本規格經審查維持可行，後續應拆成獨立 docs-only 切片：

1. 工具拒絕回執規格：定義工具可見但被權限閘門拒絕時如何回報；
2. 壓縮摘要欄位規格：定義壓縮後必須保留的權威、證據、工作樹與宣稱上限欄位；
3. harness handoff checklist：定義外部框架若要採用這些候選 receipt，必須提供哪些證據。

在這些切片完成前，本文件維持 `PENDING`。

## 宣稱上限

本文只能宣稱：

- proposed mode state anti-forgery boundary；
- proposed `MODE_STATE_RECEIPT` candidate fields；
- proposed `PUSH_AUTHORIZATION_RECEIPT` candidate fields；
- proposed `MEMORY_WRITE_AUTHORIZATION_RECEIPT` candidate fields；
- proposed `CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT` candidate fields；
- harness-dependent boundary remains explicit；
- repo does not claim runtime enforcement；
- no runtime/tests/PLAN/artifacts behavior changed。

本文不得宣稱：

- runtime gate 已實作；
- prompt cache 已實作；
- 外部 harness 已採用本規格；
- typed envelope 已存在於執行環境；
- push、memory write 或 cross-repo write 已被機器層防偽；
- 子代理審查已成為 runtime enforcement；
- 本文件可授權任何實際副作用。
