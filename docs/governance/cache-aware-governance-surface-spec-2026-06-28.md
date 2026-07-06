# 快取感知治理表面分層規格 - 2026-06-28
> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.


狀態（Status）：`PENDING`
範圍（Scope）：docs-only governance surface design
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
強制執行（enforcement）變更：否
提示快取強制執行（prompt cache enforcement）：不宣稱

## 來源

本規格從下列設計備忘拆出可落地的儲存庫表面分層：

- `docs/governance/cache-aware-agent-harness-design-note-2026-06-27.md`
- Anthropic, "Lessons from building Claude Code: prompt caching is everything"
  https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything
- Anthropic pricing documentation
  https://docs.anthropic.com/en/docs/about-claude/pricing

本文只採用其中與本儲存庫可表達的治理表面有關的部分。

## 目的

本規格定義 AI Governance 儲存庫可以提供給代理框架（agent harness）消費的
快取感知治理表面：哪些內容適合放入穩定前綴（stable prefix），哪些內容必須
留在動態尾端（dynamic tail），以及哪些變更應強制使快取失效
（forced cache invalidation）。

這不是 prompt cache runtime 實作。
這不是快取命中率監控。
這不是子代理編排功能。
這不是新的權限閘門。

本儲存庫可以定義可稽核、可版本化、可被外部 harness 消費的治理表面。
是否真的使用 prompt caching、如何計算 cache key、是否監控 cache hit rate、
如何設定 cache TTL，仍屬於 harness 或模型供應商行為。

## 核心原則

快取穩定性是效率需求。
治理新鮮度是正確性需求。
執行環境權限是安全需求。

不得為了快取命中率保留過期權威。
不得把工具可見性等同於工具執行授權。
不得把儲存庫文件分層誤讀成儲存庫已能 enforce prompt cache。

最重要的治理反轉是：

```text
authority / permission / freshness changed -> cache must miss or be bypassed
```

這種失效是正確行為，不是操作事故。

## 分層模型

### Stable Prefix：穩定前綴

穩定前綴適合放入不常改變、可被雜湊與版本引用的權威或規則摘要。

候選內容：

- `AGENTS.md` 的 session / repo 邊界規則；
- `governance/AGENT.md` 與 repo-local engineering governance；
- `governance/REVIEW_CRITERIA.md` 的審查協議摘要；
- `governance/RESPONSE_ENVELOPE_CONTRACT.md` 的最終回報契約摘要；
- `governance/MEMORY_PROTOCOL.md` 的記憶寫入邊界摘要；
- `docs/governance/ai-governance-document-language-style-guide-2026-06-27.md`
  的中文主讀文件規範；
- 已採用且不隨任務變動的 operator playbook 摘要；
- 已採用且不隨任務變動的 receipt schema 摘要。

穩定前綴中的每個來源應該有：

- path；
- base ref 或 commit；
- content hash 或可重算版本摘要；
- authority class；
- last verified time；
- 是否允許被壓縮摘要替代；
- 若替代，替代摘要的 claim ceiling。

### Dynamic Tail：動態尾端

動態尾端放入每輪任務都可能變動的事實、證據與授權狀態。

候選內容：

- 最新使用者請求；
- 當前 `HEAD`、base commit、branch、remote tracking state；
- `git status` 與 dirty-tree receipt；
- 明確納入或排除的檔案；
- 本輪 `DONE`；
- scope / non-goals / validation / commit-push intent；
- 已執行命令與結果；
- 測試或檢查的 pass/fail/unknown 狀態；
- sub-agent `REVIEW_RECEIPT`；
- reviewer findings；
- claim ceiling；
- cannot-claim / not_claimed；
- push authorization state；
- memory binding state；
- 未解風險與下一個允許動作。

動態尾端不得被折疊進穩定前綴，除非它已經變成已提交、已審查、可重新取得的
artifact，而且其 claim ceiling 被保留。

### Forced Cache Invalidation：強制失效觸發

下列事件應使 harness 重新載入或重新驗證穩定前綴；如果 harness 支援 prompt
cache，應有意讓相關前綴失效或繞過快取：

- `AGENTS.md`、`governance/AGENT.md` 或治理路由器變更；
- 權威文件 hash 與已記錄 hash 不一致；
- `HEAD`、base commit、branch 或 remote tracking state 改變；
- 使用者授權狀態改變，例如 push、cross-repo write、memory write 或 destructive action；
- tool schema、tool order、model identity 或 harness mode 改變；
- workspace root / active repo / writable roots 改變；
- dirty-tree allowlist 改變；
- receipt schema 或 closeout schema 改變；
- memory writer 或 memory protocol 改變；
- governance rule registry、contract、runtime hook 或 permission gate 變更；
- sub-agent review 結論被修正、撤回或升級；
- 來源文件被判定 mojibake、過期或 authority class 不明；
- 使用者要求 refresh、pull latest 或重新驗證最新狀態。

強制失效不是失敗。它表示目前快取前綴不再能支持安全或新鮮的宣稱。

## Harness-Dependent 邊界

本規格是儲存庫表面規格（repo surface spec），不是 harness implementation spec。

本儲存庫不能自行保證：

- prompt cache hit rate；
- cache key；
- cache TTL；
- cache read/write pricing；
- model-specific cache behavior；
- deferred tool loading；
- cache-safe compaction forking；
- sub-agent process scheduling；
- `<system-reminder>` 注入；
- tool schema 穩定排序；
- cache miss incident / SEV policy。

若外部 harness 消費本規格，應把下列欄位回寫到可稽核輸出：

```text
stable_prefix_sources:
dynamic_tail_sources:
forced_invalidation_triggers_seen:
cache_behavior_claimed: none | harness_reported | provider_reported
harness_dependent: true
repo_enforces_prompt_cache: false
```

`cache_behavior_claimed` 不得由本儲存庫自行升格。只有 harness 或模型供應商可提供
prompt cache 行為證據。

## 最小 Surface Receipt

若未來建立治理表面分層輸出，最小 receipt 應包含：

```text
CACHE_AWARE_SURFACE_RECEIPT v0.1
repo:
head:
base_ref:
stable_prefix_sources:
dynamic_tail_sources:
forced_invalidation_triggers_seen:
authority_hashes:
dirty_tree_state:
claim_ceiling:
cannot_claim:
harness_dependent: true
repo_enforces_prompt_cache: false
```

這個 receipt 只證明儲存庫已描述可消費表面，不證明 prompt cache 已啟用、命中或被
監控。

## 與既有 Receipt 的關係

本規格不得建立與既有 closeout / review receipt 競爭的平行權威。

如果未來需要實作，應先對齊：

- `REVIEW_RECEIPT`：審查者檢查了什麼與不能宣稱什麼；
- closeout receipt：session 結束時的 canonical closeout chain；
- memory record：session-derived memory 的標準寫入紀錄；
- response envelope：最終回報的 result / evidence / risk / not_claimed。

`CACHE_AWARE_SURFACE_RECEIPT` 若存在，只能作為這些 receipt 的輔助 artifact。

## 非目標

本規格不做以下事情：

- 不修改 runtime；
- 不修改 tests；
- 不修改 PLAN；
- 不修改 artifacts；
- 不新增工具或工具 schema；
- 不實作 prompt cache；
- 不監控 cache hit rate；
- 不宣稱儲存庫可 enforce prompt cache；
- 不宣稱儲存庫可防止 harness 使用過期快取；
- 不把 Anthropic 特定行為當成跨供應商事實；
- 不把 sub-agent review 寫成 enforcement；
- 不把 operator discipline 寫成 runtime guarantee。

## 可行下一步

若要前進，應分成三個後續 docs-only 切片：

1. operator checklist：把穩定前綴 / 動態尾端 / 強制失效觸發寫成日常操作檢查表；
2. receipt alignment：確認 `CACHE_AWARE_SURFACE_RECEIPT` 是否需要存在，或是否應併入既有 review / closeout receipt；
3. harness handoff spec：只描述外部 harness 若要消費本儲存庫表面，需要讀哪些 path、hash 與 dynamic tail evidence。

在完成這些切片前，本文維持 `PENDING`。

## 宣稱上限

本文只能宣稱：

- proposed cache-aware governance surface layering；
- proposed stable-prefix / dynamic-tail classification；
- proposed forced-cache-invalidation triggers；
- proposed harness-dependent boundary；
- no runtime/tests/PLAN/artifacts behavior changed。

本文不得宣稱：

- prompt cache 已實作；
- cache hit rate 已被監控；
- 儲存庫可 enforce prompt cache；
- harness 已採用本規格；
- Anthropic 以外供應商具有相同快取語意；
- sub-agent review 已成為 enforcement；
- receipt schema 已被正式採用。
