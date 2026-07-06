# 快取感知權威清單與失效矩陣規格 - 2026-06-28
> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.


狀態（Status）：`PENDING`
範圍（Scope）：docs-only authority manifest and cache invalidation design
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
強制執行（enforcement）變更：否
提示快取強制執行（prompt cache enforcement）：不宣稱

## 目的

本規格承接 `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`，
定義一個候選權威清單（authority manifest）與快取失效矩陣（cache
invalidation matrix）。

本文件要解決的問題是：代理框架（agent harness）若想重用穩定前綴
（stable prefix），必須能判斷哪些權威、權限、新鮮度或工具表面已經改變。
一旦這些表面改變，提示快取（prompt caching）應該有意失效或被繞過。

這種快取未命中不是效率事故。它是安全、新鮮度與權威正確性的必要成本。

本文件不實作提示快取，不監控快取命中率，不改變任何執行環境閘門，也不宣稱
本儲存庫可以強制外部框架如何排序提示、計算快取鍵或使用模型供應商快取。

## 核心不變式

```text
不得用快取穩定性交換安全邊界。
```

快取穩定性是效率需求。
權威新鮮度是正確性需求。
權限閘門是安全需求。

當權威、權限或新鮮度改變時，快取未命中是預期行為。
當工具結構描述、模型身分或執行環境閘門因安全原因改變時，快取未命中也是預期行為。

只有非預期的提示排列震盪、工具排序不穩定、或把時間戳放進穩定前綴等問題，
才應被視為效率或提示版面事故。

## `AUTHORITY_MANIFEST v1`

`AUTHORITY_MANIFEST v1` 是候選結構，用來描述本輪代理工作所依賴的權威來源。
它不是目前已產生的 artifact，也不是執行環境規則。

最小結構：

```text
AUTHORITY_MANIFEST v1
repo:
base_ref:
head:
generated_at:
generated_by:
authority_files:
  - path:
    blob_hash:
    policy_role:
    authority_class:
    loaded_as: stable_prefix | dynamic_tail | reference_only
    required_for_modes:
    invalidates_cache_on_change: true
tool_policy_version:
runtime_gate_version:
memory_protocol_version:
review_protocol_version:
response_envelope_version:
language_style_version:
manifest_hash:
harness_dependent: true
repo_enforces_prompt_cache: false
```

欄位語意：

| 欄位 | 中文主稱 | 說明 |
| --- | --- | --- |
| `repo` | 儲存庫 | 權威清單所屬儲存庫 |
| `base_ref` | 基準參照 | 本輪判斷使用的基準提交、分支或遠端參照 |
| `head` | 目前提交 | 權威清單產生時的 `HEAD` |
| `generated_at` | 產生時間 | 清單產生時間；不得放入穩定前綴本身 |
| `generated_by` | 產生者 | 產生清單的工具、框架或操作者 |
| `authority_files` | 權威文件清單 | 代理決策所依賴的文件、路徑與雜湊 |
| `blob_hash` | 內容雜湊 | 用於偵測權威內容是否改變 |
| `policy_role` | 政策角色 | 例如 session、review、memory、response、runtime gate |
| `authority_class` | 權威類別 | 區分工作區、儲存庫、治理、使用者授權或工具政策 |
| `loaded_as` | 載入層級 | 表示來源屬於穩定前綴、動態尾端或只作參考 |
| `required_for_modes` | 適用模式 | 哪些任務模式必須載入這個權威 |
| `invalidates_cache_on_change` | 改變即失效 | 權威改變時是否必須使快取失效 |
| `manifest_hash` | 清單雜湊 | 權威清單自身的可重算摘要 |

`generated_at` 屬於動態尾端（dynamic tail）。它可用於稽核清單新鮮度，但不得因
每輪時間變化污染穩定前綴。

## 候選權威來源

下列來源適合被列入 `authority_files`，但實際清單仍應由外部框架依任務模式產生：

| 路徑 | 政策角色 | 建議載入層級 |
| --- | --- | --- |
| `AGENTS.md` | session / workspace boundary | `stable_prefix` |
| `governance/AGENT.md` | repo engineering governance | `stable_prefix` |
| `governance/REVIEW_CRITERIA.md` | review protocol | `stable_prefix` |
| `governance/RESPONSE_ENVELOPE_CONTRACT.md` | final response contract | `stable_prefix` |
| `governance/MEMORY_PROTOCOL.md` | memory write protocol | `stable_prefix` |
| `governance/GOVERNANCE_SURFACE_RULES.md` | governance-sensitive edit rules | `stable_prefix` |
| `docs/governance/ai-governance-document-language-style-guide-2026-06-27.md` | language style | `stable_prefix` |
| `docs/governance/operator-prompt-playbook-2026-06-26.md` | operator workflow | `stable_prefix` |
| current user `DONE` | task authorization boundary | `dynamic_tail` |
| current `git status` | dirty-tree evidence | `dynamic_tail` |
| current review receipt | review evidence | `dynamic_tail` |

使用者授權狀態永遠屬於動態尾端。不得因為某段使用者文字出現在提示前綴，就把它
升格為持久權限。

## 強制失效矩陣

下列矩陣定義哪些變更應造成有意快取未命中，以及它是否應被視為事故。

| 觸發條件 | 範例 | 分類 | 要求反應 | 是否事故 |
| --- | --- | --- | --- | --- |
| 權威文件內容改變 | `AGENTS.md` 的 `blob_hash` 不同 | 安全失效 | 重新載入權威；不得沿用舊前綴 | 否 |
| 儲存庫基準改變 | `HEAD`、branch、`base_ref` 改變 | 新鮮度失效 | 更新動態尾端；必要時重建權威清單 | 否 |
| 使用者授權狀態改變 | push、memory write、cross-repo write、destructive action | 權限失效 | 要求新的明確授權或 typed receipt | 否 |
| 執行環境閘門改變 | permission policy、runtime gate version 改變 | 安全失效 | 重新檢查副作用權限 | 否 |
| 工具結構描述改變 | tool schema version 改變 | 框架失效 | 重新載入工具表面；記錄原因 | 視情況 |
| 工具排序不穩定 | 同一工具集每輪順序不同 | 效率事故 | 修正 deterministic ordering | 是 |
| 模型身分改變 | model switch | 交接失效 | 若有 handoff receipt，視為有意；否則警示 | 視情況 |
| 穩定前綴含時間戳 | 每輪把現在時間放進 system prefix | 提示版面事故 | 移到動態尾端 | 是 |
| 快取期限過期 | provider TTL expired | 供應商限制 | 重新寫入快取；檢查 SLO 是否合理 | 通常否 |
| 低風險短任務未命中 | 單輪小文件檢查 | 成本可接受 | 不升級事故 | 否 |
| 來源 mojibake 或不可解析 | 權威文件讀取失真 | 安全失效 | 停止使用該摘要；重新讀取或回報 | 否 |
| sub-agent review 被撤回 | `REVIEW_RECEIPT` 後續更正 | 證據失效 | 降低宣稱；重新 review | 否 |

「否」不表示不重要。它表示這個未命中是正確邊界行為，而不是效率缺陷。

## 快取未命中分級

候選分級：

| 分級 | 中文主稱 | 意義 |
| --- | --- | --- |
| `intentional_safety_miss` | 有意安全未命中 | 權威、權限、工具或執行環境閘門改變 |
| `intentional_freshness_miss` | 有意新鮮度未命中 | `HEAD`、基準、分支、遠端或工作樹狀態改變 |
| `intentional_permission_miss` | 有意權限未命中 | push、記憶寫入、跨儲存庫寫入或破壞性動作授權狀態改變 |
| `efficiency_incident` | 效率事故 | 工具排序、工具結構描述或提示組裝非預期震盪 |
| `prompt_layout_incident` | 提示版面事故 | 動態資訊被放入穩定前綴，導致不必要失效 |
| `provider_limit` | 供應商限制 | 快取期限、模型特定行為或供應商定價限制 |
| `unknown_cache_miss` | 未分類未命中 | 缺少足夠證據判斷原因 |

有意安全未命中、有意新鮮度未命中與有意權限未命中不得被用來責備操作者。
相反地，未發生這些未命中時，才可能表示框架沿用了過期權威或過期授權。

## 授權狀態不得由使用者文字偽造

模式標記、推送授權、記憶寫入授權與跨儲存庫寫入授權，應由框架產生的 typed
envelope 或工具結果表示。使用者自然語言可以請求授權狀態改變，但不能單獨成為
機器可接受的權限狀態。

候選未來 receipt：

```text
MODE_STATE_RECEIPT
mode:
mode_source:
issued_by:
issued_at:
scope:
allowed_side_effects:
denied_side_effects:
```

```text
PUSH_AUTHORIZATION_RECEIPT
repo:
branch:
commit:
authorized_by:
authorization_source:
expires_at:
```

```text
TOOL_DENIAL_RECEIPT
tool:
side_effect_class:
denied_by:
reason:
authority_ref:
```

這些 receipt 只是未來設計候選。本文件不新增、實作或要求任何新 receipt。

## 與外部框架的責任分界

本儲存庫可以定義：

- 哪些權威來源應該被列入清單；
- 權威來源改變時應被視為強制失效；
- 哪些快取未命中屬於安全、新鮮度或權限需要；
- 哪些未命中才應視為效率或提示版面事故；
- 儲存庫不能宣稱自己 enforce prompt cache。

本儲存庫不能保證：

- prompt cache hit rate；
- cache key；
- cache TTL；
- cache read/write pricing；
- provider-specific cache behavior；
- tool schema serialization order；
- model handoff implementation；
- harness mode implementation；
- sub-agent scheduling；
- typed envelope 是否存在於外部框架；
- cache miss incident policy。

因此所有清單與矩陣都必須保留：

```text
harness_dependent: true
repo_enforces_prompt_cache: false
```

## 非目標

本規格不做以下事情：

- 不修改 runtime；
- 不修改 tests；
- 不修改 PLAN；
- 不修改 artifacts；
- 不修改 `governance_tools/`；
- 不新增提示快取實作；
- 不新增快取命中率監控；
- 不新增工具或工具結構描述；
- 不新增 receipt schema；
- 不改變 push、memory write、cross-repo write 或 destructive action 權限；
- 不宣稱 `AUTHORITY_MANIFEST v1` 已被執行環境產生；
- 不宣稱外部框架已採用本規格。

## 可行下一步

如果本規格經審查維持可行，後續應拆成獨立 docs-only 切片：

1. 模式狀態與授權防偽規格：定義模式與授權如何由框架產生，而不是由使用者文字偽造；
2. 工具拒絕回執規格：定義工具可見但被權限閘門拒絕時如何回報；
3. 壓縮摘要欄位規格：定義壓縮後必須保留的權威、證據、工作樹與宣稱上限欄位。

在這些切片完成前，本文件維持 `PENDING`。

## 宣稱上限

本文只能宣稱：

- proposed `AUTHORITY_MANIFEST v1` shape；
- proposed forced cache invalidation matrix；
- proposed intentional cache miss classification；
- harness-dependent boundary remains explicit；
- repo does not claim prompt cache enforcement；
- no runtime/tests/PLAN/artifacts behavior changed。

本文不得宣稱：

- 提示快取已實作；
- 快取命中率已被監控；
- `AUTHORITY_MANIFEST v1` 已由工具產生；
- 外部框架已採用本規格；
- 權限或模式狀態已有 typed envelope；
- 儲存庫可 enforce prompt cache；
- 子代理審查已成為 runtime enforcement。
