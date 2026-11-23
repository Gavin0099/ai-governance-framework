# 切片 F｜Closeout 測試收據可行性

**階段 1：STOP。** 框架可在受保護的 Closeout 取得 session、完整 Git HEAD 和候選內容。通用入口缺少把這些資料與同一次測試的退出碼、測試計數和摘要一起發布的流程。消費端現有格式可承載綁定，但將其用於通用入口還需要移植測試結果的產出與發布協議，超出本次修正邊界。

框架基準 `0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d` 為 #351 的合併提交，開工時與 `origin/main`、遠端 `main` 一致。#350 於 `c5a86ede5527283c7b6936bfd4d6af5307d48b70` 仍為開啟的 Draft，保留供查閱三輪審查的反例。[PR #351](https://github.com/Gavin0099/ai-governance-framework/pull/351) · [Draft #350](https://github.com/Gavin0099/ai-governance-framework/pull/350)

## 通用入口實際取得的證據

| 資料 | 固定基準的來源與限制 |
| --- | --- |
| Session、候選、原始文字 | 受保護入口在持有 R2 排他執行權時，核對候選和文字的位元摘要，再傳入明確的 `hook_session_id`。Hook 驗證 session 信封、候選歸屬和時間，並比對任務、工作摘要、產物引用及風險。`CHECKS_RUN` 由 R2 的文字摘要涵蓋，候選內容比較本身不解讀其中的測試結果。 [入口 `session_closeout_entry.py:540–561`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/session_closeout_entry.py#L540-L561) · [R2 摘要 `shared_closeout_ownership.py:332–339`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/shared_closeout_ownership.py#L332-L339) · [Hook `session_end_hook.py:2013–2048,2065–2167`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/session_end_hook.py#L2013-L2167) |
| 完整 HEAD | `_resolve_repo_head` 在該工作樹執行 `git rev-parse HEAD`，失敗時回空值。信封的 `repo_head_before` 記錄開工時的 HEAD。 [Hook `session_end_hook.py:970–998`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/session_end_hook.py#L970-L998) · [信封 `_canonical_closeout.py:175–191`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/runtime_hooks/core/_canonical_closeout.py#L175-L191) |
| 測試退出碼與測試計數 | `test_evidence_receipt.v0.1` 有命令、退出碼、時間、執行後 HEAD 和輸出路徑，選用壓縮時另有輸出摘要。它缺 session 和測試計數。匯入器另產出 `summary` 計數，其通用輸出無 session、HEAD 或原始收據引用。開工時本工作樹既有 `latest.json` 在這四個欄位中只有 `summary`。 [收據 `test_evidence_receipt_writer.py:166–185`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/test_evidence_receipt_writer.py#L166-L185) · [匯入器 `test_result_ingestor.py:22–37`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/test_result_ingestor.py#L22-L37) |

`classify_closeout` 先依 `CHECKS_RUN`、工具名稱與產物路徑存在性分級。標準 `latest.json` 由既有 gate 另行讀取，且讀取發生在 `run_session_end` 之後。Canonical closeout 使用候選引用與工具事件另做分級。結構綁定與 canonical `valid`（通過其資格判定）可產生完成標記，R2 正式釋放再核對標記及其 canonical 摘要。所以文字分級單獨降級不足以達成一致性。`working_state_update` 是既有的未驗證工作狀態分級，實作若重新獲授權，仍須證明它可保存，同時阻止測試宣稱升級。 [路徑存在性檢查 `session_end_hook.py:443–474`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/session_end_hook.py#L443-L474) · [文字分級 `session_end_hook.py:802–877`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/session_end_hook.py#L802-L877) · [Gate 呼叫 `session_end_hook.py:2213–2247`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/session_end_hook.py#L2213-L2247) · [Canonical `session_end.py:1151–1181`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/runtime_hooks/core/session_end.py#L1151-L1181) · [完成標記 `session_end.py:1390–1399`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/runtime_hooks/core/session_end.py#L1390-L1399) · [R2 釋放 `shared_closeout_ownership.py:567–581`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/shared_closeout_ownership.py#L567-L581)

## 消費端既有格式與可移植範圍

`english-vocab-trainer` 的 prepare 入口在匯入 JSON 填上 `session_id`、`linked_commit` 和 `test_evidence_receipt`，將同次匯入檔與原始收據的兩個 SHA-256 放入 `CHECKS_RUN` 的 `test_evidence_sha256` 尾段，並將收據列為候選引用。在 R2 排他執行權內發布 `latest.json`。其 Codex Stop adapter 在框架入口前核對同一 session、完整 HEAD、候選引用、兩個摘要、退出碼與非零通過計數。這組既有格式足以承載所需關聯，無需新增 `test_evidence_receipt.v0.1` 欄位。框架的 prepare 只渲染及發布候選和文字，通用收據 writer 與匯入器各自輸出，未共用該消費端的測試執行與發布流程。唯讀 `git grep` 在框架的 `governance_tools`、`runtime_hooks`、`scripts` 找不到 `test_evidence_sha256` 消費者。只修改兩個允許的判定檔，無法讓既有通用入口產出合格正控。 [消費端 `prepare_codex_closeout.py:37–139`](https://github.com/Gavin0099/english-vocab-trainer/blob/b24921ea11220fc3b591f142824697c70359c807/scripts/prepare_codex_closeout.py#L37-L139) · [消費端 `codex_stop_closeout.py:33–115`](https://github.com/Gavin0099/english-vocab-trainer/blob/b24921ea11220fc3b591f142824697c70359c807/scripts/codex_stop_closeout.py#L33-L115) · [框架 `prepare_closeout_candidate.py:173–211`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/prepare_closeout_candidate.py#L173-L211)

## 原生身分與驗收

合法入口是先用 `runtime_hooks/adapters/codex/session_start.py --install --project-root <root>` 安裝身分 hook，經 Codex 核准 hook 信任後由新 session 的真實 `SessionStart` 提供 ID 及 cwd。框架核對工作樹根目錄後建立 v1.1 信封及 marker，R2 才能承認該身分。正式收尾還需要已安裝且被載入的 Stop。既有 Windows 驗收走過此入口。切片 C 的 macOS 驗收因信封缺失受阻，其收據正負控只驗了消費端 binding 函式。 [安裝與信任指引](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/docs/governance/codex-session-start-identity.md#L9-L33) · [原生事件 `session_start.py:24–34`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/runtime_hooks/adapters/codex/session_start.py#L24-L34) · [信封建立 `_bound_session_start.py:28–92`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/runtime_hooks/core/_bound_session_start.py#L28-L92) · [Windows N7](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/memory/evidence/n7-native-acceptance-20261119.md#L9-L32) · [切片 C](https://github.com/Gavin0099/english-vocab-trainer/blob/53210e3cd759b1074383ffed6eb3e2a8bf5c904d/docs/validation/adoption-closure-c-codex-loop-2026-11-23.md#L100-L122)

本次在 macOS 工作樹用指定 Python 做唯讀檢查。Codex CLI 版本是 `0.171.0`。`manage_agent_closeout --project-root . verify --agent codex` 退出 1，顯示 `status=not_installed`。`codex_hook_trust_status --repo . --codex /Users/macminim4/.local/bin/codex` 退出 0，兩事件均為 `not_installed`，原因是沒有 repo 的 `.codex/hooks.json`。用當前 `CODEX_THREAD_ID` 呼叫 `shared_closeout_ownership._identity` 得到 `INVALID_OWNER: qualified R1 binding required`。同一唯讀探查確認 thread ID 存在、marker／v1.1 信封／候選均缺失。合法入口已找到，這台機器的真實 SessionStart → Stop 驗收仍為 **UNKNOWN**。 [R1 前置檢查 `shared_closeout_ownership.py:165–170`](https://github.com/Gavin0099/ai-governance-framework/blob/0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d/governance_tools/shared_closeout_ownership.py#L165-L170)

沿用 E 第 3、5 節與 R／R2／R3 的基準反例。此交付只記錄停損判定。實作、固定控制集、兩條分級與記憶／R2／完成標記／重播的一致性、原生端到端驗收均未執行。`CHECKS_RUN: NONE` 的無測試路徑、外部 CI 的獨立查證，以及未驗證工作狀態的保存仍是後續驗收條件。Owner 將提交範圍限於本檔，故未寫入 PLAN 或 memory 紀錄。

```yaml
mode: VALIDATION
mode_source: validation_command
task: Slice F phase 1 receipt feasibility
task_authority: user_request
scope:
  - docs/validation/closeout-receipt-feasibility-2026-11-23.md
done:
  - Read-only source and worktree checks established the phase 1 STOP.
claim_ceiling: Findings apply to the pinned framework and consumer inputs and the observed local preflight.
not_claimed:
  - Receipt-based hardening or runtime behavior changes
  - Qualification of any native session or audit of external CI
  - Fixed-control or memory, R2, completion-marker, and replay acceptance
evidence_refs:
  - command: git rev-parse HEAD origin/main
    result: PASS
    observed: Both resolved to 0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d.
  - command: $AI_GOVERNANCE_PYTHON -B -m governance_tools.manage_agent_closeout --project-root . verify --agent codex
    result: FAIL
    observed: Exit 1, not_installed.
  - command: $AI_GOVERNANCE_PYTHON -B -m governance_tools.codex_hook_trust_status --repo . --codex /Users/macminim4/.local/bin/codex
    result: PASS
    observed: Exit 0 for the diagnostic, SessionStart and Stop both not_installed.
  - artifact: Native end-to-end acceptance at the reviewed framework HEAD
    result: NOT RUN
risk:
  - Current runtime can still award test-success credit without a session-bound execution receipt.
next_action: Independent review of the pinned phase 1 STOP evidence.
```
