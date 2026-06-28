# 唯讀採用診斷器（Report-Only Adoption Doctor）規格 - 2026-06-26

狀態（Status）：`proposed`
範圍（Scope）：第二切片（Tranche 2）純設計
風險（Risk）：實作時為中等，因為可能會碰到 `governance_tools/`

## 問題

第一切片（Tranche 1）已經讓採用類型（adoption class）在使用點可見：copy-based adoption 現在會說明它安裝的是審計表面（audit surface），並不代表目標儲存庫已具備執行環境自足治理（runtime self-contained governance）。

這個措辭能避免第一個錯誤宣稱，但當使用者開始從 copy-based adoption 移向 submodule/full path 時，它無法幫審查者或實作者診斷下游複用儲存庫（consuming repo）的目前狀態。已觀察到的失敗類型需要一個唯讀診斷（report-only diagnostic），回答「這個儲存庫目前屬於哪種 adoption class？」同時不安裝、不刪除、不 `fetch`、不 `stage`，也不阻擋任何事。

## 目前儲存庫事實

- `PLAN.md` 將 copy-based consumers 維持分類為 audit-only，且 automated update 尚未解決（`PLAN.md:307`）。
- full/submodule adoption UX proposal 將第二切片定義為唯讀採用診斷器（`docs/governance/full-submodule-adoption-ux-proposal-2026-06-26.md:216`）。
- 該提案要求採用診斷器回報 adoption class、self-contained state、runtime-capable state、root-level leftover `runtime_hooks`、framework submodule path、stale pin status 與 external framework dependency（`docs/governance/full-submodule-adoption-ux-proposal-2026-06-26.md:218`）。
- 同一份提案說明 stale pins 是證據，不是自動 blocker（`docs/governance/full-submodule-adoption-ux-proposal-2026-06-26.md:307`）。
- 第一切片已在 `adopt_governance.py` 實作：copy-based output 會說 `Runtime capability: not self-contained`，且 help/check-env 現在會把 owned/runtime-governed repos 導向手動 submodule/full path（`governance_tools/adopt_governance.py:67`、`governance_tools/adopt_governance.py:90`）。
- `external_repo_readiness.py` 已聚合 hook、drift、contract、project-facts 與 framework-version checks，但當儲存庫尚未 readiness-ready 時會回傳失敗（`governance_tools/external_repo_readiness.py:511`）。這種 pass/fail 姿態對採用診斷器來說太強。
- `hook_install_validator.py` 可以驗證 framework-root config 與必要 framework files（`governance_tools/hook_install_validator.py:18`、`governance_tools/hook_install_validator.py:90`），但它也有 validator semantics 與非零失敗 exit（`governance_tools/hook_install_validator.py:265`）。
- `framework_versioning.py` 可以讀取 `governance/framework.lock.json` 並評估 release state（`governance_tools/framework_versioning.py:208`）。它本身不能證明 submodule pin 相對於遠端是新鮮的。
- `docs/INTEGRATION_GUIDE.md` 包含第一切片指向使用者的現行手動 submodule 章節，但目前有大量 mojibake。這份規格不修復該指南。

## 目標結果

為未來唯讀命令（report-only command）建立一份可審查設計。該命令可以檢查目標儲存庫（target repo），描述它的採用姿態，且不改變它。

未來命令應能用明確理由說明：

- 目標儲存庫看起來是 copy-based、repo-owned-framework-path、submodule consumer，或 unknown；
- 靜態 self-contained prerequisites 是 present、absent 或 unknown；
- runtime capability 是 not checked、unknown，或已由獨立 no-write smoke path 明確檢查；
- framework checkout 外是否存在 root-level leftover `runtime_hooks`；
- framework submodule path 是否存在並已初始化；
- local remote-tracking comparison 是否顯示 submodule pin 是 current versus local tracking、behind local tracking、ahead/diverged versus local tracking、unknown，或 intentional not checked；
- 觀察到的 framework dependency 是否指向目標儲存庫外部。

## 範圍

這份規格授權之後的實作切片新增一個唯讀診斷命令，偏好形式如下：

```text
python -m governance_tools.adoption_doctor --repo <repo> \
  [--framework-root <path>] [--format human|json]
```

最小可用實作切片應該：

- 預設只讀 local filesystem 與 local git metadata；
- 預設避免 network fetches；
- 輸出 JSON 與 human formats；
- 當存在診斷發現（diagnostic findings）時仍回傳結束碼（exit code）0；
- 只把非零結束碼保留給 CLI misuse、unreadable paths 或 internal exceptions；
- 產出結構化發現（structured findings），severity 可為 `info`、`warning` 或 `unknown`，但第二切片不使用 blocking severity；
- 在語意吻合時重用既有 helpers，但不把它們的 pass/fail exit behavior 帶入採用診斷器；
- 為每個診斷桶（diagnosis bucket）加 focused tests。

## 非目標

第二切片不得：

- 安裝 framework submodule；
- 更新 submodule pin；
- 預設從 remotes `fetch`；
- 刪除 root-level `runtime_hooks`；
- 重寫 `.gitmodules`、`.git/config`、hooks、baseline files、`PLAN.md` 或 memory files；
- 以 mutating operation 呼叫 `adopt_governance.py`；
- 改變 drift-check、readiness、hook、pre-push、CI、runtime 或 enforcement behavior；
- 把任何 finding 變成 gate、blocker 或 failed readiness verdict；
- 宣稱 self-contained status 代表 full framework test success；
- 宣稱 repo-owned framework path 證明 hooks 已安裝、pin 是 fresh、runtime smoke 已通過，或 full installer 已執行。

## 受影響表面

目前切片：

- 僅 `docs/governance/report-only-adoption-doctor-spec-2026-06-26.md`。

可能的未來實作切片：

- `governance_tools/adoption_doctor.py` 或等價的新 report-only checker。
- `tests/test_adoption_doctor.py`。

可能但延後的表面：

- 採用診斷器存在後，在 `adopt_governance.py --help` 或 `--check-env` 加一個短指標。
- 另開可讀性修復切片後，更新 `docs/INTEGRATION_GUIDE.md`。

## 邊界與 API 考量

### 命令邊界

採用診斷器應該是唯讀診斷器，不是 readiness validator。它的 top-level result 應使用類似語言：

```json
{
  "report_version": "0.1",
  "repo_root": "...",
  "adoption_class": {
    "value": "copy_based | repo_owned_framework_path | submodule_consumer | unknown",
    "confidence": "high | medium | low",
    "reasons": []
  },
  "self_contained": {
    "value": "yes | no | unknown",
    "checked": true,
    "reasons": []
  },
  "runtime_capable": {
    "value": "not_checked | yes | no | unknown",
    "checked": false,
    "reasons": ["runtime smoke is out of scope for the static doctor"]
  },
  "findings": []
}
```

### 採用類型規則

建議第一版分類：

- `submodule_consumer`：`.gitmodules` 宣告 framework path，該 path 存在於 repo 內，且該 path 看起來像 framework checkout。
- `repo_owned_framework_path`：`--framework-root`、hook config 或 common framework-path discovery 解析到 repo 內，且看起來像 framework checkout，但缺少或未知 submodule proof。
- `copy_based`：governance audit surface 存在，但找不到 repo-owned framework checkout，且任何觀察到的 framework root 都指向 repo 外。
- `unknown`：證據互相矛盾或不足。

採用診斷器應揭露分類背後的證據，而不是把它藏在單一 verdict 後面。

### Self-Contained 規則

靜態 `self_contained=yes` 應要求 repo-owned framework files 足以解析核心 framework runtime surfaces，至少包含：

- `governance_tools/`；
- `runtime_hooks/`；
- `governance/runtime_injection_snapshot.v0.yaml`；
- framework root path 解析在 target repo 內。

靜態 `self_contained=yes` 不得暗示：

- hooks 已安裝；
- submodule pin 是 fresh；
- runtime smoke 已通過；
- 全部 framework tests 已通過；
- runtime governance 已被強制執行。

### Runtime-Capable 規則

第二切片應維持 `runtime_capable=not_checked`，除非它實作專用的 no-write smoke probe。靜態檔案存在不足以宣稱 runtime-capable execution。

如果後續切片新增 no-write smoke probe，必須保持以下概念分離：

- self-contained static path resolution；
- runtime-capable selected entrypoint execution；
- full framework test suite success。

### Stale Pin 規則

第一版實作中的 pin freshness 應維持 local 且 report-only。

允許的第一版實作：

- 比較 submodule HEAD 與已存在的 local remote-tracking ref；
- 回報 `current_vs_local_tracking`、`behind_local_tracking`、`ahead_or_diverged_vs_local_tracking`、`unknown` 或 `not_applicable`；
- 當 local git metadata 支援時，包含 `remote_tracking_freshness` 或 `last_fetch`；否則回報 `unknown`；
- 不 fetch；
- 當 behind 時不讓命令失敗。

`current_vs_local_tracking` 不得渲染成單純的 `current`。沒有 fetch 時，local remote-tracking ref 本身可能已過期，所以這個 finding 只表示 consumer pin 符合本地對遠端的視圖。它不證明 pin 符合真正的 current remote head。

第二切片不允許：

- fetch remote state；
- 更新 pin；
- 判定 behind remote 自動無效。

### 輸出語意

Human output 應以 adoption class 與 claim ceiling 開頭：

```text
Adoption Doctor

adoption_class      = copy_based
self_contained      = no
runtime_capable     = not_checked
report_only         = true

Claim boundary: this report does not install, update, delete, fetch, stage,
or enforce anything.
```

JSON output 應 deterministic，且使用 stable field names，讓 reviewer 能 diff fixture outputs。

## 宣稱上限

這份規格可以宣稱：

- proposed report-only diagnostic boundary；
- proposed classification fields and reasons；
- proposed static self-contained prerequisites；
- proposed local-only stale-pin comparison semantics；
- proposed tests and evidence for a later implementation。

這份規格不得宣稱：

- 採用診斷器已存在；
- 任何下游複用儲存庫已被診斷；
- full/submodule installation 已實作；
- runtime governance 現在已在任何 repo 中 self-contained；
- runtime capability 已驗證；
- stale pins 是 blockers；
- hooks、CI、pre-push 或 enforcement behavior 已改變。

## 失敗路徑與風險點

- repo-owned framework path 可以存在但不是 submodule。沒有 `.gitmodules` 或 gitlink evidence 時，採用診斷器不得標示為 `submodule_consumer`。
- submodule path 可以存在但未初始化或只有部分內容。這應回報 initialized-state evidence，而不是默默變成 `self_contained=yes`。
- stale pin 可能是有意選擇。它應該是 warning/finding，不是 failure。
- root-level `runtime_hooks` 在 framework repo 中可能是刻意存在，但在下游複用儲存庫中可疑。採用診斷器需要 repo-context-aware wording。
- 指向 repo 外部的明確 `--framework-root` 對 audit-only classification 有用，但它是反對 self-contained runtime claims 的證據。
- `external_repo_readiness.py` 與 `hook_install_validator.py` 已有 failure exits。重用它們的 internals 時不得引入它們的 gate semantics。
- `docs/INTEGRATION_GUIDE.md` 是目前 manual path reference，但有 mojibake。採用診斷器不應依賴該檔案的 prose readability。

## 證據計畫

對這個 spec 切片：

- `git diff --check -- docs/governance/report-only-adoption-doctor-spec-2026-06-26.md`
- 對這份 spec file 做 UTF-8 可讀性、常見 mojibake 與尾端空白檢查。

對後續實作切片：

- copy-based repo with external framework root 的 focused tests；
- repo-owned framework path without submodule proof 的 focused tests；
- submodule consumer with initialized framework checkout 的 focused tests；
- uninitialized or partial submodule checkout 的 focused tests；
- root-level leftover `runtime_hooks` 的 focused tests；
- external framework path dependency 的 focused tests；
- stale pin using local-only remote-tracking fixtures 的 focused tests；
- `current_vs_local_tracking` 不會被渲染成未限定 `current` 的 focused tests；
- no-fetch behavior by default 的 focused tests；
- findings exit 0 的 focused tests；
- stable schema 的 JSON parse test；
- claim boundary wording 的 human output test。

後續實作建議命令：

```text
pytest tests/test_adoption_doctor.py -p no:cacheprovider
python -m governance_tools.adoption_doctor --repo <fixture> --format json
python -m governance_tools.adoption_doctor --repo <fixture> --format human
```

## 實作切片建議

下一個實作切片：

1. 新增 `governance_tools/adoption_doctor.py`，只做 local filesystem 與 local git metadata inspection。
2. 實作 JSON 與 human output。
3. 對診斷發現維持 exit code 0。
4. 為六個核心 fixture classes 加 focused tests：copy-based、repo-owned framework path、submodule initialized、submodule partial/uninitialized、root-level leftover runtime hooks、stale local remote-tracking pin。
5. 同一切片不要把採用診斷器接到 adopt、pre-push、CI、readiness 或 runtime enforcement。

延後選項，不是承諾：

- 新增 no-write runtime smoke probe，之後才允許 `runtime_capable=yes/no`；
- 在 `adopt_governance.py` 加 help pointer；
- 加入手動 submodule/full installation 的 remediation hints；
- 修復 `docs/INTEGRATION_GUIDE.md` 可讀性。
