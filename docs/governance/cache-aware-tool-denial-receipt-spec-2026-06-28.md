# 快取感知工具拒絕回執規格 - 2026-06-28

狀態（Status）：`PENDING`
範圍（Scope）：docs-only tool denial receipt design
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
強制執行（enforcement）變更：否
提示快取強制執行（prompt cache enforcement）：不宣稱

## 目的

本規格承接下列文件：

- `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`
- `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`
- `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md`

前一份規格定義模式狀態（mode state）與授權狀態（authorization state）不能由
使用者自然語言直接偽造。本文件處理下一個邊界：工具可見不等於工具可執行。

代理框架（agent harness）為了提示快取（prompt caching）穩定，可能讓工具清單或
工具結構描述（tool schema）保持可見、穩定或延後載入。但工具在提示中可見，不代表
目前模式、權限、儲存庫規則或使用者授權允許它被執行。

當工具因權限閘門被拒絕時，框架應留下拒絕證據（denial evidence），讓主執行緒與
審查者可以判斷：這是正確的安全拒絕、權限缺失、模式錯誤、還是工具表面配置問題。

本文件不新增 runtime gate，不新增工具，不新增正式 schema，也不改變任何既有工具
權限。

## 核心原則

```text
工具可見性不是工具執行授權。
工具拒絕不是靜默失敗。
拒絕證據必須可稽核。
```

若工具被拒絕，代理不得把「我沒有工具」或「工具壞了」當成唯一結論。
它應該區分：

- 工具不存在；
- 工具存在但目前模式禁止；
- 工具存在但副作用類別未授權；
- 工具存在但 dirty-tree / repo boundary 禁止；
- 工具存在但外部權限或 network 權限不足；
- 工具存在但需要使用者明確授權。

這些差異會影響下一步：停下來請求授權、改走唯讀路徑、縮小 scope、或回報工具層
問題。

## `TOOL_DENIAL_RECEIPT` 候選欄位

`TOOL_DENIAL_RECEIPT` 用於表示某個工具呼叫被框架、權限閘門或儲存庫規則拒絕。
它是候選設計，不是現有 schema。

```text
TOOL_DENIAL_RECEIPT v0.1
repo:
head:
tool:
tool_version:
tool_schema_hash:
requested_action:
side_effect_class:
requested_paths:
requested_remote:
mode:
mode_receipt_ref:
authorization_receipt_ref:
denied_by:
denial_reason:
authority_ref:
dirty_tree_ref:
recoverable:
allowed_alternatives:
requires_user_authorization:
issued_at:
expires_at:
harness_dependent: true
repo_enforces_runtime: false
```

欄位語意：

| 欄位 | 中文主稱 | 說明 |
| --- | --- | --- |
| `repo` | 儲存庫 | 工具拒絕所屬儲存庫 |
| `head` | 目前提交 | receipt 產生時的 `HEAD` |
| `tool` | 工具 | 被要求執行的工具名稱 |
| `tool_version` | 工具版本 | 可取得時記錄工具版本 |
| `tool_schema_hash` | 工具結構描述雜湊 | 用於判斷工具表面是否改變 |
| `requested_action` | 請求動作 | 使用者或代理想執行的動作 |
| `side_effect_class` | 副作用類別 | 例如 read、write、network、push、destructive |
| `requested_paths` | 請求路徑 | 工具若要讀寫檔案，列出目標路徑 |
| `requested_remote` | 請求遠端 | 工具若涉及 remote、API 或 network，列出目標 |
| `mode` | 模式 | 工具請求發生時的模式 |
| `mode_receipt_ref` | 模式回執參照 | 對應 `MODE_STATE_RECEIPT`，若存在 |
| `authorization_receipt_ref` | 授權回執參照 | 對應 push、memory 或 cross-repo 授權 receipt，若存在 |
| `denied_by` | 拒絕來源 | 例如 harness、repo-policy、permission-gate、sandbox |
| `denial_reason` | 拒絕理由 | 人類可讀的拒絕原因 |
| `authority_ref` | 權威參照 | 支持拒絕的規則或文件 |
| `dirty_tree_ref` | 工作樹參照 | 若 dirty-tree 狀態影響拒絕，指向對應摘要 |
| `recoverable` | 可恢復 | 是否可透過授權、縮小 scope 或改模式恢復 |
| `allowed_alternatives` | 允許替代路徑 | 例如 read-only、scoped validation、manual confirmation |
| `requires_user_authorization` | 需要使用者授權 | 是否需要明確人類授權才能重試 |
| `issued_at` | 發行時間 | receipt 產生時間，屬於動態尾端 |
| `expires_at` | 失效時間 | receipt 可引用期限 |

## 拒絕理由分類

候選 `denial_reason` 分類：

| 分類 | 中文主稱 | 意義 |
| --- | --- | --- |
| `mode_denied` | 模式拒絕 | 目前模式不允許此副作用 |
| `authorization_missing` | 缺少授權 | 需要但尚未取得使用者或框架授權 |
| `authorization_expired` | 授權過期 | 既有授權不再有效 |
| `scope_denied` | 範圍拒絕 | 請求路徑、remote 或 action 超出已核准 scope |
| `dirty_tree_denied` | 工作樹拒絕 | dirty-tree 狀態使工具不可安全執行 |
| `cross_repo_denied` | 跨儲存庫拒絕 | 目標 repo 未明確授權或 preflight 未完成 |
| `network_denied` | 網路拒絕 | network 或 remote side effect 未授權 |
| `destructive_denied` | 破壞性動作拒絕 | destructive action 未被明確允許 |
| `tool_unavailable` | 工具不可用 | 工具不存在、未載入或目前 harness 未提供 |
| `schema_mismatch` | 結構描述不符 | 工具 schema 與已知權威或 receipt 不一致 |
| `sandbox_denied` | 沙箱拒絕 | 執行環境 sandbox 阻擋該動作 |

拒絕理由應盡量精準。若原因不明，應回報 `tool_unavailable` 或 `sandbox_denied`
之外的已知事實，而不是假設工具壞掉。

## 最小拒絕證據

若框架未能產生完整 `TOOL_DENIAL_RECEIPT`，至少應保留：

```text
tool:
requested_action:
side_effect_class:
denied_by:
denial_reason:
authority_ref:
requires_user_authorization:
harness_dependent: true
repo_enforces_runtime: false
```

這個最小證據只說明拒絕發生與拒絕理由，不證明 runtime enforcement 已完整實作。

## 快取關係

工具拒絕 receipt 屬於動態尾端，不屬於穩定前綴。

原因：

- 它依賴目前模式；
- 它依賴目前授權狀態；
- 它依賴目前 `HEAD`、dirty-tree 與 workspace root；
- 它可能因使用者授權、模式切換或工具 schema 改變而失效；
- 它記錄一次具體拒絕，不是永久工具政策。

如果外部框架支援 prompt cache，看到下列情況應觸發有意安全未命中或有意權限未命中：

- 工具 schema hash 改變；
- 工具 side-effect class 改變；
- tool permission policy 改變；
- `MODE_STATE_RECEIPT` 改變；
- push / memory / cross-repo 授權 receipt 改變；
- dirty-tree allowlist 改變；
- sandbox permission profile 改變；
- `TOOL_DENIAL_RECEIPT` 被更正或撤回。

這些未命中不是效率事故。它們表示工具表面或權限狀態已改變，舊前綴不能支持安全
執行判斷。

## 與授權 receipt 的關係

`TOOL_DENIAL_RECEIPT` 不授權重試。

它只能說明：

- 哪個工具被要求；
- 哪個副作用被拒絕；
- 拒絕依據是什麼；
- 是否可能透過明確授權、縮小範圍或切換模式恢復。

若拒絕原因是缺少 push、memory write 或 cross-repo write 授權，下一步應回到對應
授權 receipt：

- `PUSH_AUTHORIZATION_RECEIPT`
- `MEMORY_WRITE_AUTHORIZATION_RECEIPT`
- `CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT`

拒絕 receipt 不得自行升格成這些授權 receipt。

## 與既有回執的關係

本文件不得建立與既有審查回執、收尾 receipt、memory record 或 response envelope
競爭的平行權威。

候選工具拒絕 receipt 若未來實作，只能作為下列流程的輔助輸入：

- `REVIEW_RECEIPT`：審查者檢查拒絕是否被正確處理；
- closeout receipt：session 結束時的 canonical closeout chain；
- memory record：若拒絕代表重要治理事件，仍需透過標準寫入器記錄；
- response envelope：最終回報的 evidence / risk / not_claimed。

子代理可以審查工具拒絕證據，但不能用工具拒絕 receipt 自行授權寫入、commit、push
或跨儲存庫變更。

## 與外部框架的責任分界

本儲存庫可以定義：

- 候選 `TOOL_DENIAL_RECEIPT` 欄位；
- 工具可見不等於工具可執行；
- 被權限閘門拒絕時應保留 denial evidence；
- 工具拒絕 receipt 屬於動態尾端；
- 哪些拒絕理由應觸發有意安全或權限未命中；
- 本儲存庫不能宣稱 runtime enforcement。

本儲存庫不能保證：

- 外部 harness 會產生 `TOOL_DENIAL_RECEIPT`；
- 外部 harness 會阻擋未授權工具執行；
- 外部 harness 會區分所有拒絕理由；
- 外部 harness 會保留 denial evidence；
- tool permission policy 已改變；
- runtime gate 已實作；
- prompt cache 已實作；
- 工具可見性與工具執行權限已在機器層分離。

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
- 不改變任何工具權限；
- 不改變 push、memory write、cross-repo write 或 destructive action 權限；
- 不宣稱 `TOOL_DENIAL_RECEIPT` 已被外部框架採用；
- 不宣稱工具拒絕已可被 runtime machine-enforced；
- 不把 sub-agent review 寫成 enforcement。

## 可行下一步

如果本規格經審查維持可行，後續應拆成獨立 docs-only 切片：

1. 壓縮摘要欄位規格：定義壓縮後必須保留的權威、證據、工作樹與宣稱上限欄位；
2. harness handoff checklist：定義外部框架若要採用 tool denial receipt，必須提供哪些證據；
3. receipt alignment note：確認工具拒絕 receipt 與 review / closeout / response envelope 的引用方式。

在這些切片完成前，本文件維持 `PENDING`。

## 宣稱上限

本文只能宣稱：

- proposed `TOOL_DENIAL_RECEIPT` candidate fields；
- proposed tool visibility versus execution authorization boundary；
- proposed denial evidence categories；
- proposed cache relationship for tool denial evidence；
- harness-dependent boundary remains explicit；
- repo does not claim runtime enforcement；
- no runtime/tests/PLAN/artifacts behavior changed。

本文不得宣稱：

- runtime gate 已實作；
- prompt cache 已實作；
- 外部 harness 已採用本規格；
- `TOOL_DENIAL_RECEIPT` 已存在於執行環境；
- 工具拒絕已被機器層強制執行；
- tool permission policy 已改變；
- 子代理審查已成為 runtime enforcement；
- 本文件可授權任何實際副作用。
