# Governance artifact 寫入邊界：根因設計 - 2026-06-23

狀態（Status）：

```text
design-only
no implementation
canonical-root contract: RATIFIED (owner, 2026-06-23) = explicit project root + fail-closed
hygiene .gitignore defense applied separately (not the fix)
no change to runtime writer behavior in this document
```

## 問題

完整的治理執行環境（runtime）`artifacts/` 樹，被發現寫在儲存庫的子目錄裡：

```text
docs/governance/hermes_no_agent_checklist/artifacts/
```

這是產生出來的 runtime output，不是人工撰寫的證據。已觀察內容如下，且刻意原地保留，沒有移動或刪除；詳見「保留證據」段落：

- `artifacts/runtime/closeout-receipts/closeout_receipt_20260623T102316607125Z.json`
- `artifacts/runtime/canonical-audit-log.jsonl`, `runtime/closeouts/`, `runtime/candidates/`, `runtime/curated/`, `runtime/advisory/`
- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson`
- `artifacts/governance/runtime_phase_summary.json`
- `artifacts/session/`, `artifacts/session-index.ndjson`
- `artifacts/codeburn_closeout_ingest.db`（約 272 KB）

時間戳集中在 `2026-06-23T10:23Z`，約本地時間 18:23。

## 根因

治理 closeout/session writers 會把 artifacts 錨定到 `project_root`：

```text
project_root / "artifacts" / "runtime" / "closeout-receipts" / ...   (manage_agent_closeout.py:833)
project_root / "artifacts" / ...                                     (multiple writers)
```

而 `project_root` 預設為目前工作目錄（current working directory）：

```text
manage_agent_closeout.py:979   --project-root default="."  -> Path(".").resolve()
session_end_hook.py:2245        --project-root default="."
session_closeout_entry.py:338   --project-root default="."
```

因此，當 shell 的 `cwd` 位於子目錄時觸發 session-end / closeout，整棵 canonical artifact tree 會被寫進該子目錄。這是證據基底漂移（evidence-substrate drift）：canonical governance evidence 的位置取決於程序剛好從哪裡被呼叫。

`.gitignore` 沒有攔住它的原因：既有 `artifacts/...` pattern 內含 slash，因此錨定在 repo root；它不會匹配巢狀的 `docs/.../artifacts/...`。所以這棵 stray tree 顯示為 untracked，而且距離被 `git add` 進 commit 只差一步。

## 兩個修復候選

| 候選 | 變更內容 | 角色 | 風險 |
| --- | --- | --- | --- |
| **A. 工具自行解析 canonical root** | writers 以 deterministic 方式解析 root，例如 git toplevel / framework marker，而不是 `Path(".")` | 長期正確性 | framework-wide；會影響 canonical evidence 寫入位置 |
| **B. Hook/CLI wiring 明確傳入 `--project-root`** | 每次 invocation，例如 session_end hook command 或 CLI callers，都必須傳入 intended consuming-repo root | 短期 containment | 較低；屬於 configuration/wiring change |

排序：**B 是 containment**，讓今天的 callers 正確；**A 是真正修正**，因為 canonical-evidence writer 不應默默 fallback 到 `cwd`。對 evidence writer 來說，`default="."` 本身就是缺陷，因為它把 canonical artifact location 綁到 invocation cwd。

## 本設計必須回答的問題 [OP-HC]

> governance artifacts 的 canonical root 是「repo root」，還是「explicit project root」？

答案會固定規則：

- **如果 canonical root 是 repo root**：`Path(".").resolve()` 作為 silent default 應被禁止。writer 必須 deterministic 地解析 repo root；如果不能解析，必須 fail-closed，且絕不能寫到 `cwd`。
- **如果 canonical root 是 explicit project root**：hook/CLI 必須 fail-closed。沒有提供 `--project-root` 時，writer 必須拒絕寫入 canonical artifacts，而不是默默寫到 `cwd`。

## 決策（owner-ratified, 2026-06-23）[OP-HC]

> **Canonical artifact root is an explicit contract, not an ambient cwd-derived property.**

canonical root 是 **explicit project root + fail-closed**：

- CLI / hook callers **必須**提供 `--project-root`，也就是它們意圖使用的 consuming-repo / framework root。
- writer **必須** normalize 並 validate 傳入的 root。
- 如果沒有提供 root，writer **拒絕寫入 canonical artifacts**；它不猜測，而且**永遠不 fallback 到 cwd**。
- git-toplevel / framework-marker check 只允許作為 supplied root 的輔助驗證，不能作為決定或推導 root 的機制。

被拒絕的方案：把 `git rev-parse --show-toplevel` 當成唯一 root。它有隱性治理風險：在 nested repo / submodule / worktree 中，它可能解析出技術上正確但治理上錯誤的 root；當治理工具在 consuming repo 內執行時，可能寫到 consuming repo，而不是 framework-intended root；它也把「誰決定 artifact trust root」變成環境推導屬性，而不是呼叫契約。

實作後果：從 `manage_agent_closeout.py` / `session_end_hook.py` / `session_closeout_entry.py` 移除 `--project-root default="."` 與任何 silent `Path(".").resolve()`；missing-root path 變成 fail-closed refusal。

分類：這會改變 canonical evidence 寫入位置，因此觸碰 evidence substrate / trust root，屬於 **[OP-HC]**。它需要 rollback path、multi-repo adoption consideration 與 reviewer agreement。hook-wiring containment（B）是普通 **[OP]**，是走向 fail-closed end state 的短期步驟。

## 事故分析與 containment（2026-06-23）：精煉範圍 [OP]

上述決策後，調查進一步縮小了本次事故範圍：

- **這次事故的直接原因是 hook wiring，不是 missing root。** Stop（session-end）hook 被設定為 `session_closeout_entry.py --project-root .`。這是明確傳入的 cwd-relative root。當 hook 在 checklist 子目錄中觸發時，`.` 解析到該子目錄，artifacts tree 因而落在那裡。所以字面上的「missing root 時 fail-closed」抓不到這個案例，因為 root 並非缺失，而是明確的 `.`。

- **短期 containment 已套用。** Stop-hook wiring 已改成 absolute explicit framework root：`--project-root E:/BackUp/Git_EE/ai-governance-framework`。這滿足核心驗證：從 checklist 子目錄觸發 session closeout 時，不再寫入 `cwd`。

- **containment 不是 version-controlled。** `.claude/settings.json` 被 gitignored（`.gitignore:131 .claude/*`），所以這個 wiring fix 只在本機有效。它不能跨 clone 重現，也不能在 repo 中稽核。這也支持 durable fix 必須是 tool-level contract（A），因為 wiring containment 無法被交付。

- **不要天真禁止 `--project-root .`。** `default="."` 與 explicit `.` 是整個 hook system 長期存在的 call pattern：`session_start.py:686`、`session_end.py:1299`、`pre_task_check.py:1013`、`stub_runner.py:212`；`post_task_check.py:1053` 沒有 default。當 `cwd = repo root` 時，`--project-root .` 是有效 invocation。直接用 argument-value ban，例如 reject `"."`，會破壞這些 entrypoints；那是 framework-contract change，不是 bug fix，blast radius 太大。

- **A 的收斂方向（next cut）：** canonical-write path 應把 resolved root 對照 framework marker / expected repo identity 來驗證，而不是檢查 argument string 是否等於 `"."`。這讓契約可測試，也能作為 shared helper 漸進遷移，同時不禁止合法的 repo-root-cwd usage。

## 已套用的 hygiene defense（不是修復）

`.gitignore` 已加入任意深度 pattern，例如 `**/artifacts/runtime/`、`**/artifacts/claim-enforcement/`、`**/artifacts/*.db`。這能避免 stray nested `artifacts/` 被 commit。

這只是 hygiene defense。它不能阻止 writer 污染錯誤位置，也已在 `.gitignore` 中明確標記為不是根因修復。

## 保留證據（修復落地前不要碰）

錯置的 tree：`docs/governance/hermes_no_agent_checklist/artifacts/`，是刻意原地保留的證據。移動或刪除它，本身就會改變 evidence state，並破壞原始 root-cause confirmation site。

它現在已被 gitignored，不會被 commit，並在本文記錄路徑、約本地 18:23 / `2026-06-23T10:23Z` 的時間點，以及上方列出的內容類型。是否 quarantine 或 cleanup，延後到 root resolution 修復完成後再決定。

## 宣稱上限

```text
This design names the defect and the decision. It does NOT change any writer's
project_root resolution, does NOT move/delete the preserved artifacts, and the
.gitignore defense does NOT fix the root cause.
```

## eventual fix 的證據計畫

1. Ratify canonical-root answer：repo-root-with-fail-closed 或 explicit-with-fail-closed。
2. 實作後，任何 writer 都不能 silently 把 `project_root` 解析成 `cwd`；並 assert fail-closed path。
3. 重現原始 trigger：從子目錄執行 closeout，證明沒有 artifacts 落在 `cwd`。
4. 確認既有 consumers / hook wiring 仍寫到正確的 repo-root `artifacts/`。
5. 再決定 preserved misplaced tree 要 quarantine 還是 cleanup。

## 非目標

- 本切片不改 writer behavior；
- 不移動或刪除 preserved artifacts；
- 不宣稱 `.gitignore` defense 修復了根因；
- 不修改 session_end hook scheduling；
- 不修改 Hermes checklist line。
