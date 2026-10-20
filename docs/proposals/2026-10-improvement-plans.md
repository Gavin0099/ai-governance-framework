# ai-governance-framework 改善計畫（四項）

> 依據：本機唯讀 clone（`e8e6779`，depth 50），Linux／Python 3.13／git 2.47，全套 `pytest tests/`：**6503 passed / 83 failed / 52 skipped**。未 push、未修改 remote。
> 建議順序：計畫 1 → 2 → 4 → 3（3 牽動路徑最多，最後做）。

---

## 計畫 1：修正 README 的測試數與 stdlib-only 宣稱

**目標**：README 的數字與依賴宣稱可被機器驗證，不再自己犯「claim inflation」。

**要改的檔案**
- `README.md`（第 5、59、174 行，及 English summary 對應句）
- 新增 `governance_tools/readme_claims_check.py`
- 新增 `tests/test_readme_claims.py`
- `.github/workflows/governance.yml`（加一步）

**步驟**
1. 第 5 行改為：
   ```markdown
   **Version 1.3.0 candidate** · Python 3.9+（runtime 核心 stdlib-only；部分工具有選用依賴，見下）· 6,500+ tests · Windows / Git Bash 主驗證，Linux CI
   ```
2. 第 59 行改為依賴分層說明：
   ```markdown
   - **核心 runtime（hooks / gate / contract / memory_record）**：stdlib-only
   - **選用工具依賴**（`requirements.txt`）：
     - `cryptography`、`tuf`：Solo R2 controller 與 TUF/Rekor 驗證（security boundary 工具）
     - `pyyaml`、`jsonschema`：contract / schema 驗證
     - `fastapi`、`uvicorn`：demo app
     - `pytest`：測試
   ```
3. 第 174 行 `# 測試套件（3,200+）` → `# 測試套件（數量見 CI badge／readme_claims_check）`。
4. 寫一個 stdlib 守門檢查，確保「核心」真的不 import 第三方：
   ```python
   # governance_tools/readme_claims_check.py
   import ast, sys, pathlib
   CORE_DIRS = ["runtime_hooks"]           # 依實際「核心」範圍調整
   ALLOWED = set(sys.stdlib_module_names) | {"runtime_hooks", "governance_tools"}
   def third_party_imports(root="."):
       bad = []
       for d in CORE_DIRS:
           for p in pathlib.Path(root, d).rglob("*.py"):
               for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                   mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                          [n.module] if isinstance(n, ast.ImportFrom) and n.module and n.level == 0 else []
                   bad += [(str(p), m) for m in mods if m.split(".")[0] not in ALLOWED]
       return bad
   ```
   測試：`assert third_party_imports() == []`。
5. 測試數量：在 CI 產出 `pytest --collect-only -q | tail -1`，與 README 宣稱下限比對（例如 README 寫 `6,500+`，檢查 collected ≥ 6500）。

**風險**：「核心」範圍定義若太寬，會讓檢查一開始就失敗；先用 `runtime_hooks/` 起步再擴大。
**驗收**：README 不再出現 `3,200`；`test_readme_claims.py` 綠；英文 summary 同步。
**工作量**：0.5 天。

---

## 計畫 2：跨平台測試 + windows-latest CI

**目標**：非 Windows／shallow clone 的貢獻者跑測試不出現「假紅」；PowerShell 路徑在 CI 被真正驗證。

### 實測失敗分類（83 個，16 個檔案）
| 原因 | 檔案（失敗數） |
|---|---|
| A. 找不到 `pwsh` | `test_required_memory_obligation.py`(15)、`test_required_memory_bootstrap_launcher.py`(2)、`test_session_end_hook_closeout_bridge.py`(3)、`test_session_end_hook_memory_truth.py`(1) |
| B. 寫死 `python` 指令（Linux 常只有 `python3`） | `test_claude_hook_binding_visibility.py`(6) |
| C. `git rev-list emitted an invalid object ID record`（shallow clone 邊界，或 git 2.47 輸出格式） | `test_external_tree_inventory_guard.py`(9)、`test_historical_json_debt.py`(13)、`test_hook_memory_policy.py`(9)、`test_hook_installer.py`(1)、`test_guard_safe_directory.py`(11，同一 guard 路徑，需確認) |
| D. 需要完整歷史 commit（Solo R2 `PRE_ATTEMPT_INFRA_FAILURE`） | `test_solo_r2_disposable_binding.py`(1)、`test_solo_r2_disposable_execution.py`(1)、`test_solo_r2_replacement_binding.py`(2) |
| E. `closeout_status == 'stale_or_mismatched'`（**原因未查清**，可能是時間窗或 env 依賴） | `test_gate_input_validation.py`(7)、`test_codex_closeout_identity.py`(1)、`test_memory_significance_v02.py`(1) |

> **【2026-10-21 完整 clone 重跑後更新】C、E 已確認是真 bug（非 shallow clone 問題），D 是 shallow clone 造成。詳見文末「附錄：完整 clone 驗證結果」。下面原本的推測保留作紀錄。**
>
> 注意：C 與 E 不一定只是環境問題，C 可能是 guard 對 `rev-list` 輸出的解析在 shallow/grafted repo 上真的有 bug（使用者 consumer repo 若是 shallow clone 也會遇到）。**要先用 full clone 重跑確認，不要一律 skip。**

### 步驟
1. 新增 `tests/conftest.py`（若已存在則合併）共用 marker：
   ```python
   import shutil, subprocess, sys, pathlib, pytest

   HAS_PWSH = shutil.which("pwsh") or shutil.which("powershell")
   REPO = pathlib.Path(__file__).resolve().parents[1]

   def _is_shallow() -> bool:
       try:
           out = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                                cwd=REPO, capture_output=True, text=True)
           return out.stdout.strip() == "true"
       except FileNotFoundError:
           return True

   requires_pwsh = pytest.mark.skipif(not HAS_PWSH, reason="requires PowerShell (pwsh)")
   requires_full_history = pytest.mark.skipif(
       _is_shallow(), reason="requires full git history (git fetch --unshallow)")
   ```
2. A 類檔案頂端加 `pytestmark = requires_pwsh`（`from tests.conftest import requires_pwsh` 或直接改寫成 conftest fixture）。只套在真的呼叫 pwsh 的測試，不要整檔 skip 掉純 Python 的 case。
   另外 `test_required_memory_obligation.py:168` 目前是 `AssertionError: Focused checker tests require PowerShell` → 改成 `pytest.skip(...)`。
3. B 類：把 hook 命令裡的 `python` 改為 `sys.executable`（測試）或在 hook 產生器用 `python3`/`py` 偵測；同時檢查 `runtime_hooks/` 與 hook installer 是否在產出的命令中寫死 `python`（若是，這是真 bug，consumer 在 Linux 會壞）。
4. C 類：先 `git fetch --unshallow` 重跑；若通過 → 加 `requires_full_history`；若仍失敗 → 修 `governance_tools/external_tree_inventory_guard.py:658` 的 `rev-list` 解析（容忍 shallow boundary 行 `-<sha>`／`--objects` 的路徑欄位）。
5. D 類：加 `requires_full_history`。
6. E 類：個別 debug（看 closeout 比對的時間戳/session id 來源），修好或標 `xfail(strict=True, reason=...)` 並開 issue。
7. CI 加 Windows job（`.github/workflows/governance.yml`）：
   ```yaml
     windows-test-suite:
       name: Windows Test Suite (pwsh paths)
       runs-on: windows-latest
       timeout-minutes: 30
       defaults:
         run:
           shell: pwsh
       steps:
         - uses: actions/checkout@v4
           with:
             ref: ${{ github.sha }}
             fetch-depth: 0
         - uses: actions/setup-python@v5
           with:
             python-version: '3.11'
         - name: Install documented dependencies
           run: pip install -r requirements.txt
         - name: Run full test suite
           env:
             PYTHONUTF8: '1'
           run: python -m pytest tests/ -q --tb=short
   ```
   並把 Linux job 改成 matrix `python-version: ['3.9', '3.13']`（README 宣稱 3.9+，目前只測 3.11）。
8. 加一個「skip 不可悄悄變多」的守門：CI 中 `pytest -rs` 輸出，若 Linux job skip 數超過基線（例如 80）就 fail，避免 skipif 被濫用來藏紅燈。

**風險**：Windows runner 慢、可能暴露更多既有問題（第一次先設 `continue-on-error: true` 觀察一週再轉 blocking）；skipif 會降低 Linux 上的覆蓋率，所以第 8 步是必要的。
**驗收**：Linux shallow clone + 無 pwsh：0 failed（skip 有明確原因）；full clone：C/D 類通過；Windows job 綠；3.9 與 3.13 都綠。
**工作量**：1.5–3 天（C、E 類 debug 是主要不確定性）。

---

## 計畫 3：Repo 瘦身 + 文件分層

**目標**：新使用者 clone 下來 10 分鐘內找到「怎麼用」；研究/證據紀錄保留但不擋路。

### 現況（實測）
- tracked 檔案 5,728；`artifacts/` 2,810 檔（約 52MB）、`memory/` 870 檔（約 9.2MB）
- `docs/` 225 檔：36 個檔名帶日期；52 個 `ab-*`／`e1b-*`／`dbl-*` 實驗紀錄
- `PLAN.md` 3,367 行：`Pending Work - Ordered`（L1213–2832）佔 1,600 行；L3065 之後是 40+ 個日期型 Solo R2 段落
- root 雜項：`E8A_TEST_REPORT_20260414.md`、`_classification_governance_smoke.py`、`run_r49*.ps1` ×3、`deploy_to_memory.sh`、`Script/`、`spikes/`、`codeburn/`（26 份規格）、空的 `archive/`
- `tests/_tmp_debug_public_api`、`artifacts/pytest_output.txt`（產物被 commit）
- 149 個 `governance_tools/` 與 `tests/` 的 `.py` 引用 `artifacts/` 或 `memory/` 路徑 → **搬移必須有路徑相容層**

### 建議目錄結構
```
README.md / CHANGELOG.md / CONTRIBUTING.md / LICENSE / PLAN.md(精簡版)
AGENTS.md AGENTS.base.md CLAUDE.md GEMINI.md contract.yaml   # agent 入口，維持在 root
governance/ governance_tools/ runtime_hooks/ validators/ schemas/ templates/ examples/ scripts/ tests/
docs/
  README.md                 # 文件索引（新增）
  guide/                    # 使用者文件
    INTEGRATION_GUIDE.md ADOPTION_MODEL.md LIMITATIONS.md CLAIM_BOUNDARY.md
    REVIEWER_ENTRYPOINT.md ai-governance-first-import-sop.md ai-governance-framework-explainer.md
  reference/                # schema / contract 規格（*-contract.md, *-schema.md, *_SPEC*.md, advisory-*）
  adr/  releases/
research/                   # 研究與實驗紀錄（可選：之後拆到獨立 repo 或分支）
  ab/        ← docs/ab-*.md, artifacts/ab-live, ab-smoke, ab_v3_rerun
  e1b/       ← docs/e1b-*.md
  dbl/       ← docs/dbl-*.md
  claim-enforcement/ ← docs/CLAIM_ENFORCEMENT_*_2026-04-30.md, CLAIM_BINDING_*
  codeburn/  ← codeburn/（整個）、Script/codeburn_phase1_7day_summary.py
  solo-r2/   ← run_r49*.ps1、PLAN.md L3065–結尾
  reports/   ← E8A_TEST_REPORT_20260414.md、artifacts/md_noise_*_report_*.json
  spikes/    ← spikes/
  talks/     ← ai-governance-talk-draft.md、ai-governance-member-briefing.md
archive/
  plan/PLAN-history-2026H1.md  ← PLAN.md 舊 sprint 與已完成段落
  memory/YYYY-MM/              ← memory/ 中超過 90 天的 daily record
artifacts/                     # 只留 runtime 需要讀的（session/, governance/, schemas/, contracts/, release-package/）
```

### 檔案移動清單（第一批，低風險，不被程式引用者）
| 從 | 到 |
|---|---|
| `E8A_TEST_REPORT_20260414.md` | `research/reports/` |
| `run_r492_reviewer_substitution.ps1`、`run_r49x1_*.ps1`、`run_r49x3_*.ps1` | `research/solo-r2/scripts/` |
| `_classification_governance_smoke.py` | `scripts/` 或 `research/spikes/` |
| `Script/` | `research/codeburn/tools/`（並刪除空的 `Script/`） |
| `spikes/` | `research/spikes/` |
| `docs/ab-*.md`（約 30 檔） | `research/ab/` |
| `docs/e1b-*.md` | `research/e1b/` |
| `docs/dbl-*.md` | `research/dbl/` |
| `docs/*_2026-*.md`（36 個日期檔） | 依前綴分到 `research/*/` |
| `docs/ai-governance-talk-draft.md`、`ai-governance-member-briefing.md` | `research/talks/` |
| `tests/_tmp_debug_public_api` | 刪除（或 `.gitignore`） |
| `artifacts/pytest_output.txt` | 刪除並加入 `.gitignore` |

第二批（**被程式引用，需相容層**）：`codeburn/`、`artifacts/*` 實驗子目錄、`memory/` 舊紀錄、`PLAN.md` 段落。

### 步驟
1. 先跑盤點：`rg -l "<path>" governance_tools runtime_hooks tests scripts .github` 對每個候選目錄，產出「被引用 / 未引用」清單（已知 149 個 py 引用 artifacts/memory）。
2. 第一批用 `git mv`（保留歷史），一個 PR；跑全套測試 + `governance_drift_checker`。
3. 新增 `docs/README.md` 索引（使用者 / reference / research 三欄），README 的連結全部改指 `docs/guide/`。
4. 移動後跑連結檢查（stdlib 小腳本：掃 `*.md` 中相對連結，確認檔案存在），加入 CI。
5. PLAN.md 精簡：保留 `Canonical Planning Surface`、`Active Claim Boundaries`（L1017–1213，REVIEWER_ENTRYPOINT 指定 PLAN 為權威，**不能動語意**）、`Pending Work` 只留未完成項、`Definition Of Done`、`Cannot Claim`；其餘移到 `archive/plan/`，PLAN 頂端留連結。目標 < 600 行。
6. memory：`memory/00_long_term.md`、`01_active_task.md`、`02_workflow.md` 等 canonical 檔不動；daily record 依 `memory_record` 工具的讀取邏輯確認是否支援子目錄後再歸檔（若不支援，先加 `--archive-root` 讀取能力）。
7. artifacts：大型歷史 JSON 改成 release asset 或 Git LFS；保留 `artifacts/session/`（REVIEWER_ENTRYPOINT 引用）。
8. 可選：最終把 `research/` 拆成 `ai-governance-research` repo，主 repo 用連結指過去。

**風險**：
- 治理工具（drift checker、memory canonical writer、authority guard）可能把路徑寫在 frontmatter 或 lock 裡 → 搬動觸發 drift 或 fail-closed。每批都要跑 drift checker。
- consumer repo 的 `framework.lock.json`／F-7 若引用文件路徑會壞 → 在舊路徑留 stub（一行「已移至 …」）一個版本週期。
- 歷史 commit 綁定（memory record 的 commit hash）不受影響，因為用 `git mv`。
**驗收**：root 只剩入口檔與主要目錄；`docs/` 根層 ≤ 20 檔；PLAN.md < 600 行；全套測試、drift checker `severity=ok`、連結檢查全綠；`git ls-files | wc -l` 明顯下降（目標 < 3,000）。
**工作量**：第一批 0.5–1 天；第二批 + PLAN 精簡 2–4 天。

---

## 計畫 4：Harness² 治理整合說明（integration note）

**目標**：把本框架定位成「自動改 harness 的系統」所需的治理層，並提供可執行的範例。
**來源**：[google-research/harness2](https://github.com/google-research/harness2)、[arXiv:2610.14224](https://arxiv.org/html/2610.14224)（研究碼，非 Google 正式產品）

**要新增的檔案**
- `docs/integrations/harness2-governance-note.md`（主文件）
- `examples/harness2-governed-loop/contract.yaml`（範例契約）
- `examples/harness2-governed-loop/README.md`
- （可選）`tests/test_harness2_example_contract.py`：驗證範例契約可被 `quickstart_smoke` 讀取

### Note 大綱與重點內容
```markdown
# 用 ai-governance-framework 治理 Harness² 類的自我改進迴圈

## 1. 背景：為什麼自我改進的 harness 需要治理
Harness² 在不改模型權重的前提下，自動修改 8 個 harness 組件
(system prompt, guardrails, memory, tool guidance, subagents, skills, scripts, plugins)，
並把「有證據支持的經驗」寫入持續的 improvement harness。
風險：agent 可以改到自己的 guardrails；單次成功被升級成長期經驗（記憶污染）；
「分數提升」被宣稱成「harness 更安全/更好」（claim inflation）。

## 2. 對照表：Harness² 概念 ↔ 本框架機制
| Harness² | 本框架 | Claim class |
|---|---|---|
| Propose（提出 harness edit） | Task Contract：allowed scope 只含可編輯組件；`guardrails` 預設 forbidden | Enforced for wired gates |
| Probe（同任務對比執行） | Artifact evidence：兩次執行的輸出/日誌為 required evidence | Enforced（缺證據 fail-closed） |
| Compose（組合被支持的修改） | Decision Gate：無對比證據的 edit → BLOCKED | Enforced at single point |
| Improvement harness（跨任務經驗庫） | Memory 治理：session lesson 不自動升級；需 canonical writer + 證據 | Advisory + selective Enforced |
| Benchmark 分數提升 | Claim Ceiling：non-claims 必列 | Enforced |

## 3. 建議的 governed loop
Pre Hook（產生 contract：本輪可改哪些組件）
 → Harness² Propose/Probe（在 contract 邊界內）
 → Post Hook（檢查 diff 只觸及 allowed 組件、對比 artifact 存在）
 → Gate（PASS/FAIL/BLOCKED）
 → Closeout receipt（含 non-claims）
 → Memory Check（lesson 進 improvement harness 前須通過升級資格）

## 4. 範例 contract（摘要）
## 5. 不宣稱的事（non-claims）
- 不保證 Harness² 產生的 harness 語意正確或更安全
- benchmark 分數提升 ≠ production 品質提升
- 本框架不是 security boundary；agent 繞過工具鏈直接改檔只會被標記，不會被阻止
- 未在真實 Harness² 執行上做過端到端驗證（目前為設計對照 + 範例契約）
## 6. 後續：可量測的實驗設計（watch）
用 Harness² 的同條件對比思路，量測本框架 gate 的攔截精準度（誤擋/漏擋），
作為 docs/LIMITATIONS.md 的量化補充。
```

### 範例契約（`examples/harness2-governed-loop/contract.yaml`）
```yaml
# 欄位名稱需對齊現有 examples/usb-hub-contract/contract.yaml 的 schema
name: harness2-governed-loop
allowed_scope:
  - harness/system_prompt.md
  - harness/tool_guidance/**
  - harness/skills/**
  - harness/scripts/**
forbidden_scope:
  - harness/guardrails/**        # 改進迴圈不得修改自身護欄
  - harness/plugins/**           # 需人工審核
  - .governance/**
required_evidence:
  - probe/baseline_run.json      # 修改前執行
  - probe/candidate_run.json     # 修改後同任務執行
  - probe/contrast_summary.md    # 行為對比摘要
done_definition: >
  所有 harness 修改落在 allowed_scope，且每項修改都有 baseline/candidate 對比 artifact。
non_claims:
  - 分數提升不代表 harness 更安全
  - 單一任務的經驗不代表可跨任務推廣
```

**風險**：Harness² 是新的研究碼，API/目錄可能變動 → note 寫成「概念對照 + 範例」，不寫死它的內部路徑；範例契約欄位要依實際 schema 校正（我沒有逐欄核對）。
**驗收**：note 有 non-claims 段落；範例 contract 可被 `quickstart_smoke.py --contract examples/harness2-governed-loop/contract.yaml` 讀取 `ok=True`；README「適用場景」加一行連結。
**工作量**：1 天（文件 + 範例）；端到端實際跑 Harness² 另計 2–3 天（需 Vertex AI 憑證，列為 watch）。


---

## 附錄：完整 clone 驗證結果（2026-10-21 00:00 台北時間）

環境：`/workspace/agf-full`（完整 clone，`git rev-parse --is-shallow-repository` = `false`，HEAD `e8e6779`），git 2.47.3，Python 3.13。重跑 C/D/E 共 11 個檔案：**338 passed / 52 failed**。

| 類別 | shallow clone | 完整 clone | 結論 |
|---|---|---|---|
| C（rev-list，5 檔） | 43 failed | **43 failed** | **不是 shallow 問題，是 git 版本相容 bug** |
| D（Solo R2，3 檔） | 4 failed | **0 failed** | shallow clone 造成，加 `requires_full_history` 即可 |
| E（stale_or_mismatched，3 檔） | 9 failed | **9 failed** | **真 bug：mtime 精度造成的時間比較誤判** |

### C 的根因：`git rev-list -z` 需要 git ≥ 2.50
- `governance_tools/external_tree_inventory_guard.py` L607–658 用 `git rev-list --objects -z <oid>`，並以 NUL 切 `<OID>\0path=<path>\0` 格式解析。
- `-z`（NUL 分隔 + `path=` token）是 `jt/rev-list-z` 分支，2025-04-16 merge，在 **Git 2.50.0** release notes 才出現（[RelNotes 2.50.0](https://github.com/git/git/blob/e9019fca/Documentation/RelNotes/2.50.0.adoc)、[merge commit](https://github.com/dscho/git/commit/1a1661bd41697a106481e9e2467d0f5a0697349a)、[git-rev-list 文件](https://git-scm.com/docs/git-rev-list)）。
- 在 git 2.47.3 上實測：`-z` **不報錯、被靜默忽略**，輸出仍是換行分隔的 `<oid> <path>\n`。整段輸出沒有 NUL，被當成一個 record，`_OID_PATTERN` 比對失敗 → `PrePushScanError("git rev-list emitted an invalid object ID record")`。
- **影響**：
  - 導入的 repo 只要本機或 CI 的 git < 2.50（Debian 13 / Ubuntu 24.04 內建 git、許多企業映像檔都是 2.4x）就會中，**跟 shallow clone 或 `fetch-depth: 1` 無關**。
  - pre-push hook 會回傳 `status: ERROR`（returncode 4），因為 fail-closed，**push 會被擋下**；`test_hook_memory_policy.py` 預期的是 `BLOCKED`，但拿到的是 `ERROR`。
  - GitHub Actions 的 ubuntu-latest 和 Windows 的 Git for Windows 通常比較新，所以框架自己的 CI 和作者機器都沒看到這個問題。
  - shallow clone 另有一個風險：`--objects ^<remote_oid>` 碰到 shallow 邊界時，`_git_object_exists` 可能提早報 `remote old object is unavailable`。這是另一條路徑，這次沒觀察到，也沒驗證。
- **修正方案**（建議 A＋B 都做）：
  - A. 不依賴 `-z`，改成兩段式、各版本都穩定的做法：
    ```python
    # 1) 只取 OID（--no-object-names 從 git 2.20 起就有）
    oids = subprocess.run([... "rev-list", "--objects", "--no-object-names", update.local_oid, *excl],
                          stdout=PIPE, check=True).stdout.split()
    # 2) 用 cat-file batch 查型別，只留 blob
    #    git cat-file --batch-check='%(objectname) %(objecttype)'
    # 3) 需要路徑時，用 ls-tree -r -z 對新 commit 取 blob→path（-z 在 ls-tree 很早就支援）
    #    git ls-tree -r -z --full-tree <commit>  → "<mode> blob <oid>\t<path>\0"
    ```
    或保留現有 parser，再加一個 legacy fallback：
    ```python
    def _git_supports_rev_list_z(root) -> bool:
        out = subprocess.run(["git", "version"], capture_output=True, text=True).stdout
        m = re.search(r"(\d+)\.(\d+)", out)
        return bool(m) and (int(m[1]), int(m[2])) >= (2, 50)

    if b"\0" not in completed.stdout and completed.stdout.strip():
        # legacy newline 格式："<oid>[ <path>]\n"
        for line in completed.stdout.splitlines():
            oid, _, path = line.decode("utf-8", "surrogateescape").partition(" ")
            if not _OID_PATTERN.fullmatch(oid):
                raise PrePushScanError("git rev-list emitted an invalid object ID record")
            if path.casefold().endswith(".json"):
                candidates.setdefault(oid.lower(), set()).add(path)
    ```
    （legacy 格式的路徑如果含換行會被 git 改寫，屬於已知限制，要在 non-claims 註明。）
  - B. 至少在入口明確 fail-closed 並提示：git < 2.50 時回報 `status: ERROR, reason: git>=2.50 required for rev-list -z (found X.Y)`，不要再出現讓人看不懂的 invalid OID 訊息；README 的前置需求也要寫 git 版本。
  - C. CI 加一個舊版 git 的 job（例如 `container: debian:trixie`，git 2.47），守住相容性。
- **驗收**：在 git 2.47 下，`test_external_tree_inventory_guard.py`、`test_historical_json_debt.py`、`test_hook_memory_policy.py`、`test_hook_installer.py`、`test_guard_safe_directory.py` 全綠，新舊兩種 git 的 CI job 都綠。**工作量**：0.5–1 天。

### E 的根因：檔案 mtime 精度比 `datetime.now()` 粗
- `governance_tools/session_end_hook.py` L1908–1925：`if closeout_mtime < started_at: pre_binding_status = "closeout_before_session_start"` → 走 `_fail_closed_session_binding_classification` → `stale_or_mismatched`。
- 我在本機 clone 暫時加了 log（之後已 `git checkout` 還原），13 筆實測資料都是 closeout 檔案在 session 開始**之後**寫入，但 mtime 反而比 `started_at` 早 **1–4 ms**。例：`started_at 15:56:57.166251`、`mtime 15:56:57.164788`（UTC）。
- 原因：Linux 的檔案時間戳來自 kernel 的粗粒度時鐘（per-tick，約 4ms），`started_at` 則是高精度的 wall clock。兩者一比，剛寫的檔案就會「早於」session 開始。NTFS 和 Windows 上不容易出現，所以作者機器上測試是綠的。
- **影響**：真實使用時 session 開始後幾毫秒內就寫 closeout 的機率很低，所以主要表現為 **Linux CI 上的 flaky／確定性失敗**。但在自動化 agent（hook 快速連續觸發）的情境下，也可能把合法的 closeout 誤判成 fail-closed（false positive，不是安全漏洞）。
- **修正**：
  ```python
  MTIME_TOLERANCE = timedelta(seconds=2)   # 涵蓋 FAT/SMB 2s 精度與 kernel tick
  if closeout_mtime + MTIME_TOLERANCE < started_at:
      pre_binding_status = "closeout_before_session_start"
  ```
  並在 `pre_binding_detail` 記錄 tolerance，寫入 non-claims：「2 秒內的先後順序不做判斷」。加一個測試，人為把 mtime 設成 `started_at - 3ms`，應判為 eligible；設成 `- 5s`，仍應判為 `closeout_before_session_start`。
- **驗收**：`test_gate_input_validation.py`、`test_codex_closeout_identity.py`、`test_memory_significance_v02.py` 在 Linux 全綠。**工作量**：0.25 天。

### 對計畫 2 的修正
- 原本「C 類先 fetch --unshallow 再決定 skip」的步驟作廢：**C 不能 skip，必須修**。
- D 類維持用 `requires_full_history` skip；Linux CI 已經是 `fetch-depth: 0`，不受影響。
- E 類不能用 xfail，直接修。
- 計畫 2 的總工作量修正為 **2–3 天**，其中 C 修正約 0.5–1 天、E 約 0.25 天。

---

## 附錄 B：Fleet 導入盤點（2026-10-21 00:08 台北時間）

**方法**：GitHub API 列出 Gavin0099 的 32 個公開 repo（含 6 個 fork），逐一 blobless 淺 clone（唯讀），檢查 tree、workflow、submodule gitlink、`framework.lock.json`、2026-09-20 之後的 commit 數。bug 曝露以框架 git 歷史判斷：guard `rev-list -z` 自 `67764bdf`（8/24）起，mtime 判斷自 `a0683a5c`（7/29）起，看 consumer 釘住的 commit 是否包含。**private repo 不可見；本機 `.git/hooks`、使用者層 agent 設定也看不到。**

| Repo | 模式 | 釘住／落後 HEAD e8e6779 | CI 實際執行 | Hooks（已 commit） | guard bug | mtime bug | 9/20 後 commits | 價值判斷 |
|---|---|---|---|---|---|---|---|---|
| campaign-forge | submodule | e8e6779 / 0 | **無 CI** | – | 是 | 是 | 13 | 最新但未接 gate |
| DiceMercenaries | submodule | 2a09d54 / 5 | drift + **memory blocker** | Copilot | 是 | 是 | 18 | **最完整** |
| TacticalGo | submodule | 2a09d54 / 5，**無 lock** | drift | Copilot | 是 | 是 | 97（≥103 AI 標記） | 最需要但只有 drift |
| BeatLab | submodule | 15722da / 38 | drift | – | 是 | 是 | 6 | 低中 |
| fwupd（fork） | submodule | 24ba84c / 76 | drift | Copilot | 是 | 是 | 40 | ⚠️ 上游 fork 污染風險 |
| wasteland-chronicles | submodule | 3709097 / 83，**無 lock** | drift | – | 是 | 是 | 118 | 活躍、深度淺 |
| ai-assisted-ssdlc-docs | submodule | 46b2574 / 86 | drift + readiness | – | 是 | 是 | 83 | 中 |
| crystal-bracelet-studio | submodule | 1d213ba / 92 | drift | – | 是 | 是 | 0 | 已停 |
| uvm-agent-lab | submodule | 1b85e29 / 362 | drift + quickstart_smoke | Copilot | 是 | 是 | 9 | 中（有 domain contract） |
| usb-logic-trace-correlator | copy | 1004427 / 373 | drift | Claude/Gemini/Copilot | 是 | 是 | 0 | 已停 |
| spec-reference-kit | submodule | a694ddb / 819 | drift + memory CI + hook validator | Copilot lifecycle | 否 | 是 | 0 | 接線完整但已停 |
| zephyr（fork） | submodule | da71729 / 861 | drift | Copilot lifecycle | 否 | 是 | 0 | ⚠️ fork 污染風險 |
| usb-if-hub-spec-reference | submodule | 61111f5 / 885 | 無治理工具呼叫 | Claude | 否 | 是 | 0 | 已停 |
| AI-Slide-Design-System-Repo | submodule | 84077ee / 959 | drift wf 未偵測到 checker、`submodules: false` | – | 否 | 否 | 0 | 疑似空轉（待人工確認） |
| verilog-domain-contract | submodule | 80e5ec5 / 1721，**lock≠submodule SHA** | drift + smoke + readiness | Claude | 否 | 否 | 0 | 帳實不符 |
| ZoneTruth | copy | 6f0ca32 / 2075 | drift | – | 否 | 否 | 0 | 已停 |
| Ashfall | copy | 8a4262a / 2144 | drift + janitor 等 | – | 否 | 否 | 0 | 已停 |
| financial-pdf-reader | copy | ca5d26d / 2184 | drift + pytest | Claude | 否 | 否 | 0 | 已停 |
| Hearth | submodule | 57db6c1 / 2270，**lock=9b0e6b7 ≠ submodule** | drift | Claude/Gemini/Copilot | 否 | 否 | 0 | 帳實不符 |
| usb-if-hid-spec-reference | copy | 737fcd4 / 1952 | 無治理 CI | – | 否 | 否 | 0 | 殘留 |
| lecroy-vse-toolkit | copy，**無 lock** | 無法判定 | drift | – | ? | ? | 62 | 活躍但無法追版 |

未導入：DeviceTraceKit、SnackBuddies（空）、KidsCharacterKit、sprout-space、wordtreegarden-site；fork：hermes-agent、ulani-epaper、crosspoint-reader、FinancialAdvisorGPT、Windows-driver-samples。

### 發現
1. **只有 2 個 repo（DiceMercenaries、spec-reference-kit）在 CI 有 blocking enforce**（memory workflow fail-on-blocker）。其餘只跑 `governance_drift_checker`，它檢查的是治理檔本身的漂移，**不檢查 agent 有沒有越界或宣稱膨脹**。task contract / claim ceiling 在 fleet 的 CI 裡幾乎沒接上。
2. **版本分裂**：1 個最新、7 個落後 5–92、其餘落後 300–2,270 commit；3 個無 lock、2 個 lock 與 submodule SHA 不一致。框架自己的 lock 一致性功能就在抓這種問題，但它只是 report-only。
3. **bug 曝露**：guard bug 涵蓋 12 個 repo，但只在本機 pre-push 且 git<2.50 時觸發（CI 沒有呼叫 guard）；mtime bug 涵蓋 15 個 repo，主要在 Linux 或快速連續觸發 hook 時發生。對 Windows 為主的作者機器影響低，對其他使用者或 Linux 容器影響高。
4. **價值錯配**：最活躍、AI 參與最多的 repo（TacticalGo、wasteland-chronicles、ai-assisted-ssdlc-docs、lecroy-vse-toolkit）都只有 drift 檢查；治理最完整的 spec-reference-kit 已停更。
5. **fork 污染**：fwupd、zephyr 是上游大專案的 fork，治理 submodule、hooks、檔案很容易被帶進往上游送的 PR。

### 建議（fleet 側，依優先順序）
1. 活躍的 4 個 repo：補 lock（或改 submodule），CI 照 DiceMercenaries 加 memory blocker，再加一個 PR scope gate（見 B-1）。
2. verilog-domain-contract、Hearth：跑 `f7_full_update.py` dry-run，再決定更新或降級成 audit-only。
3. 已停更的 repo 標記 `frozen`（lock 加欄位），排除在 fleet 報告與升級推送之外。
4. fork（fwupd、zephyr）：治理檔移到 `governance/*` 分支，或改用不進 repo 的本機設定。
5. 框架先出 v1.3.x patch 修兩個 bug，再用 F-7 推到受影響的 repo。

---

## 框架側根因與修正（Framework-side root causes & fixes）

> 盤點顯示問題不在個別 repo 偷懶，而在**框架的預設值**：導入預設只到 drift check、沒有升級拉力、lock 不一致不會擋、fleet 工具看不出深度。下面四項是在框架端修，讓每個 consumer 都受益。

### B-1. 導入預設只到 drift check → `adopt_governance` 預設產生 blocking PR gate（可 opt-out）

**根因**：`governance_tools/adopt_governance.py` L21、L838–839 只複製 `baselines/repo-min/.github/workflows/governance-drift.yml`。沒有任何預設 workflow 檢查 PR diff 是否落在 task contract 範圍內。

**要改的檔案**
- 新增 `governance_tools/pr_scope_gate.py`（stdlib-only）
- 新增 `baselines/repo-min/.github/workflows/governance-pr-gate.yml`
- 修改 `governance_tools/adopt_governance.py`（複製新 workflow，加 `--no-pr-gate`、`--pr-gate-mode {enforce,advisory}`）
- 新增 `tests/test_pr_scope_gate.py`、擴充 `tests/test_adopt_governance.py`
- `docs/ADOPTION_MODEL.md`、README「路徑 B」補說明

**步驟**
1. `pr_scope_gate.py`：讀 contract（`contract.yaml` 或 `.governance/task_contract.yaml`）的 `allowed_scope` / `forbidden_scope`（glob），比對 `git diff --name-only <base>...<head>`：
   ```python
   import fnmatch, json, subprocess, sys, argparse
   def changed_files(base, head):
       out = subprocess.run(["git", "diff", "--name-only", "-z", f"{base}...{head}"],
                            capture_output=True, check=True).stdout
       return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]
   def evaluate(files, allowed, forbidden):
       hit_forbidden = [f for f in files if any(fnmatch.fnmatch(f, g) for g in forbidden)]
       outside = [f for f in files if allowed and not any(fnmatch.fnmatch(f, g) for g in allowed)]
       decision = "BLOCKED" if hit_forbidden else ("FAIL" if outside else "PASS")
       return {"decision": decision, "forbidden_hits": hit_forbidden, "outside_scope": outside,
               "non_claims": ["scope PASS 不代表變更正確或安全"]}
   # 沒有 contract → decision=BLOCKED, reason=contract_missing（fail-closed），除非 --mode advisory
   ```
   exit code：PASS=0、FAIL/BLOCKED=1（advisory 模式一律 0，但輸出 summary）。
   註：`git diff -z` 在所有現行 git 版本都支援，不受 B-附註的 git 版本問題影響。
2. Workflow 範本：
   ```yaml
   name: Governance PR Gate
   on:
     pull_request:
   permissions:
     contents: read
   jobs:
     scope-gate:
       runs-on: ubuntu-latest
       timeout-minutes: 5
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0
             submodules: recursive
         - uses: actions/setup-python@v5
           with: { python-version: '3.11' }
         - name: Scope diff vs task contract
           run: |
             python {{FRAMEWORK_ROOT}}/governance_tools/pr_scope_gate.py \
               --repo . --base "${{ github.event.pull_request.base.sha }}" \
               --head "${{ github.sha }}" --mode {{PR_GATE_MODE}} \
               --format human | tee "$GITHUB_STEP_SUMMARY"
   ```
   `adopt_governance` 依 consumer 的 framework 路徑（`ai-governance-framework`、`.ai-governance-framework`、`additional/ai-governance-framework`，實際三種都有）填入 `{{FRAMEWORK_ROOT}}`。
3. 預設 `enforce`；`--pr-gate-mode advisory` 給第一次導入時試跑，`--no-pr-gate` 完全不產生。dry-run 輸出要列出這個 workflow。
4. contract 範本（`examples/starter-pack/`）加 `allowed_scope` 預設值（例如 `["**"]` 加 `forbidden_scope: [".governance/**", ".github/workflows/**"]`），讓導入當下就是綠燈，只擋高風險路徑。

**風險**：`allowed_scope` 太窄會讓開發卡關，導致使用者整個關掉 gate → 預設寬鬆加 forbidden 黑名單，逐步收緊。fnmatch 的 `**` 語意與 gitignore 不同 → 文件要寫清楚，或另做 glob 轉換。
**驗收**：新導入的 repo 預設有 `governance-pr-gate.yml`；PR 改到 forbidden 路徑 → check 失敗；沒有 contract → 失敗並寫明原因；`--no-pr-gate` 不產生檔案；README claim class 表新增一列「PR scope gate — Enforced（wired 時）」。
**工作量**：1.5–2 天。

### B-2. 沒有升級拉力 → release tag + reusable Action + drift checker 版本落後升級警告

**根因**：consumer 釘住 submodule commit 後，沒有任何機制提醒落後。fleet 有 13 個 repo 落後超過 300 個 commit。v1.x 的 release notes 存在（`docs/releases/`），但 README 自己說 tag/Release 是否發布需另外查證。

**要改的檔案**
- `.github/workflows/release.yml`（新增：tag `v*` 時建立 GitHub Release，附 `docs/releases/vX.md`）
- 新增 `action.yml`（repo 根目錄，composite reusable action）
- `governance_tools/governance_drift_checker.py`（新增 `version_lag` 檢查）
- `governance_tools/framework_versioning.py`（已存在，加 `commits_behind()` / `latest_tag()`）
- `tests/test_governance_drift_checker.py` 加測試

**步驟**
1. 打 tag：`v1.3.0`（含兩個 bug 修正後出 `v1.3.1`）；之後每個 release 都要有 tag 與 Release。
2. Composite action：
   ```yaml
   # action.yml
   name: ai-governance-check
   description: Run ai-governance drift + PR scope gate
   inputs:
     framework-root: { default: ai-governance-framework }
     pr-gate-mode:   { default: enforce }
     max-lag-commits: { default: '200' }
   runs:
     using: composite
     steps:
       - uses: actions/setup-python@v5
         with: { python-version: '3.11' }
       - shell: bash
         run: |
           python "${{ github.action_path }}/governance_tools/governance_drift_checker.py" \
             --repo . --framework-root "${{ inputs.framework-root }}" \
             --max-lag-commits "${{ inputs.max-lag-commits }}" --format human
   ```
   consumer 的 workflow 改成 `uses: Gavin0099/ai-governance-framework@v1`，Dependabot（`package-ecosystem: github-actions`，加上 `gitsubmodule`）就會自動開升級 PR，這就是「拉力」。
3. drift checker 的版本落後分級（`framework_versioning.py`）：
   ```python
   def lag_severity(behind: int, days: int, has_security_fix: bool) -> str:
       if has_security_fix: return "error"            # 已知 bug 修正（例如 v1.3.1）
       if behind > 500 or days > 90: return "error"
       if behind > 200 or days > 30: return "warning"
       return "ok"
   ```
   `has_security_fix`：在框架加一份 `governance/known_defects.json`（缺陷 id、引入 commit、修正 commit），consumer 釘住的 commit 若包含引入點、不包含修正點 → error。這會直接涵蓋 guard bug 與 mtime bug。
4. consumer 若是 `frozen`（B-3 lock 欄位）→ lag 只報 info，不升級警告。

**風險**：直接升到 error 會讓大量已停更的 repo CI 變紅 → 先用 warning 跑一個版本週期，再升級；`frozen` 提供出口。consumer 端的 shallow submodule 可能算不出 behind → 改用 GitHub compare API，或標成 `unknown`（不得當成 ok）。
**驗收**：GitHub 上有 `v1.3.x` tag 與 Release；consumer 用 `@v1` 可以跑；落後 >200 commit 出現 warning；釘在 `known_defects` 受影響範圍內 → error，並在訊息裡附修正版號。
**工作量**：2 天（tag/Release 0.5、action 0.5、lag 加 known_defects 1）。

### B-3. lock 一致性只是 report-only → CI 在「缺 lock」或「lock≠submodule SHA」時 fail

**根因**：README 能力表把「Lock 帳實一致性」標為 Report-only；fleet 有 3 個無 lock、2 個 SHA 不一致的 repo，都沒有被擋。

**要改的檔案**
- `governance_tools/governance_drift_checker.py`（新增 `lock_consistency` 檢查，severity=error）
- `governance_tools/f7_full_update.py`（共用比對邏輯，避免兩份實作）
- `README.md` 能力表：Lock 帳實一致性 → `Enforced（CI，submodule consumer）`
- `tests/test_governance_drift_checker.py`

**步驟**
```python
def check_lock_consistency(repo, framework_rel) -> list[dict]:
    lock = repo / "framework.lock.json"   # 或 .governance/framework.lock.json，依現有慣例
    issues = []
    gitlink = subprocess.run(["git", "-C", str(repo), "ls-tree", "HEAD", framework_rel],
                             capture_output=True, text=True).stdout.split()
    is_submodule = len(gitlink) >= 3 and gitlink[1] == "commit"
    if not lock.is_file():
        issues.append({"id": "lock_missing", "severity": "error" if is_submodule else "warning"})
        return issues
    data = json.loads(lock.read_text(encoding="utf-8"))
    if data.get("status") == "frozen":
        return [{"id": "lock_frozen", "severity": "info"}]
    if is_submodule and data.get("adopted_commit") != gitlink[2]:
        issues.append({"id": "lock_submodule_mismatch", "severity": "error",
                       "lock": data.get("adopted_commit"), "gitlink": gitlink[2],
                       "fix": "python governance_tools/f7_full_update.py --apply"})
    return issues
```
- copy-based consumer：缺 lock 只給 warning（符合 audit-only 定位），但要在報告寫明「無法追蹤版本」。
- lock schema 加 `status: active|frozen` 與 `frozen_reason`。

**風險**：直接改成 error 會讓 verilog-domain-contract、Hearth、TacticalGo、wasteland-chronicles 的 CI 立刻變紅 → 這次 release 先 warning，並在 release notes 預告下一版改成 error；同時提供 `f7_full_update --apply` 一鍵修。
**驗收**：在 fixture repo 上，缺 lock（submodule）→ CI fail；SHA 不一致 → fail，並印出兩個 SHA 和修正指令；`frozen` → pass 加 info；README claim class 已更新。
**工作量**：1 天。

### B-4. Fleet 7 訊號看不出深度 → 導入深度 L0–L4

**根因**：fleet 掃描（`scripts/governance_repo_matrix.ps1`、`governance_tools/governance_maturity_summary.py`）只看訊號「有沒有存在」。「只有 drift check」和「有 blocking gate」在報告上看起來差不多，這次盤點只能人工逐一讀 workflow 才分得出來。

**等級定義**（以 CI 裡實際「接線」的證據判定，不看檔案存在與否）
| Level | 名稱 | 判定條件（全部要可從 repo 內容機器驗證） |
|---|---|---|
| L0 | none | 沒有治理檔 |
| L1 | present | 有 AGENTS / contract / 治理檔，但沒有 lock 或 CI |
| L2 | tracked | 有 lock 且與 submodule 一致，CI 有跑 drift checker |
| L3 | gated | L2，加上 CI 至少一個 **blocking** 治理 gate（memory blocker 或 PR scope gate；step 沒有 `continue-on-error`、有 fail-on 參數） |
| L4 | governed | L3，加上 agent hooks 已 commit（Claude/Codex/Gemini/Copilot 任一）、domain contract 有 validator、版本落後在 warning 門檻內 |

**要改的檔案**
- 新增 `governance_tools/adoption_depth.py`（stdlib；輸入 repo 路徑，或 `--github-user` 搭配 blobless clone 清單）
- `governance_tools/governance_maturity_summary.py`：輸出加 `adoption_depth` 欄位
- `scripts/governance_repo_matrix.ps1`：呼叫 Python 版本（避免 PowerShell 與 Python 兩套邏輯）
- `schemas/`：fleet matrix schema 加 `adoption_depth`、`depth_evidence[]`
- `tests/test_adoption_depth.py`：用 `tests/fixtures/` 做 L0–L4 各一個 repo fixture

**步驟**
1. workflow 解析不引入 YAML 依賴：用逐行規則掃 `run:` 區塊，找 `governance_drift_checker`、`memory_workflow --fail-on-blocker`、`ci_memory_workflow_check`、`pr_scope_gate`，並檢查同一個 step 有沒有 `continue-on-error: true`。複雜的 YAML 判定不出來時給 `unknown`，**不得往上判級**。
2. 每一級都輸出 `depth_evidence`（檔案路徑加命中的行），符合「observation，非 judgment」的定位。
3. 加入活躍度欄位（近 30 天 commit 數、AI co-author 數），產出「價值錯配」清單：活躍度高但等級 ≤ L2 的 repo。
4. README 的 Fleet 治理描述改為：「Observation：L0–L4 深度分級加證據，不代表健康分數」。

**風險**：用 regex 解析 workflow 會誤判 → 用 `unknown` 保守處理，並以 fixture 測試覆蓋三種常見寫法（Python heredoc、`run: |`、composite action `uses:`）。
**驗收**：用這次的 21 個 repo 實跑，結果與附錄 B 的人工判斷一致（DiceMercenaries 為 L3、TacticalGo 為 L1–L2、campaign-forge 為 L2 但沒有 CI → L1）；每一級都附證據路徑。
**工作量**：2–3 天。

### 附註 1：CI matrix 缺口（舊版 git、Windows）
- 兩個真 bug 都是因為 CI 只跑 `ubuntu-latest` 加新版 git 才沒被抓到：guard 需要 git ≥2.50，mtime 是 Linux 時間戳精度問題，作者在 Windows 機器上看不到。
- 在 `.github/workflows/governance.yml` 加：
  ```yaml
    compat-matrix:
      strategy:
        fail-fast: false
        matrix:
          include:
            - { os: ubuntu-latest,  python: '3.9',  container: 'debian:trixie' }  # 舊 git（2.47）
            - { os: ubuntu-latest,  python: '3.13', container: '' }
            - { os: windows-latest, python: '3.11', container: '' }
      runs-on: ${{ matrix.os }}
      container: ${{ matrix.container || null }}
      steps: [ ... checkout(fetch-depth: 0) / setup-python 或 apt 安裝 python3 / pip install / pytest ... ]
  ```
  （container job 要用 `apt-get install -y git python3 python3-venv` 取代 setup-python；Windows job 見計畫 2。）
- 外加：`governance_tools/` 啟動時檢查 git 版本，低於需求就明確 fail-closed 並說明原因（見附錄 A 的 C 修正 B 案）。
- **工作量**：0.5–1 天（不含修掉第一次跑出來的失敗）。

### 附註 2：導入流程偵測 fork
- `adopt_governance.py` 在套用前先偵測：
  ```python
  def detect_fork(repo) -> dict:
      remotes = subprocess.run(["git", "-C", str(repo), "remote", "-v"],
                               capture_output=True, text=True).stdout
      has_upstream = any(l.startswith("upstream\t") for l in remotes.splitlines())
      # 可選：若有 GH_TOKEN，查 GET /repos/{owner}/{repo} 的 "fork": true
      return {"likely_fork": has_upstream, "evidence": remotes.splitlines()[:4]}
  ```
- 偵測到 fork 時，預設**拒絕直接在 default branch 導入**，要求擇一：`--fork-mode branch`（治理檔只放在 `governance/*` 分支）、`--fork-mode local`（寫進 `.git/info/exclude`，加上本機 hooks，不 commit），或 `--allow-fork` 明確同意。
- drift checker 對 fork 加 warning：「治理檔位於可能被送往上游的分支」。
- fleet 盤點中的 fwupd、zephyr 是這項的實例。
- **工作量**：0.5 天。

### 建議實作順序
1. 附錄 A 兩個 bug 修正 → 打 tag 出 **v1.3.1**
2. B-3（lock 一致性，先 warning）、附註 1（CI matrix）
3. B-2（reusable action + version lag + known_defects）→ 用 F-7 推送 v1.3.1
4. B-1（PR scope gate，預設 enforce，可 opt-out）
5. B-4（L0–L4），再重跑 fleet 盤點驗收
6. 附註 2（fork 偵測）可以和 B-1 一起做

合計約 8–11 人天。
