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
   **Version 1.3.0 candidate** · Python 3.9+ runtime（需 pyyaml；完整測試需 3.10+）· 6,500+ tests · Windows / Git Bash 主驗證，Linux CI
   ```
2. 第 59 行改為依賴分層說明：
   ```markdown
   - **核心 runtime（hooks / gate / contract / memory_record）**：除 `pyyaml` 外為 stdlib（實測 `governance_tools/runtime_phase_policy.py:9 import yaml`，至少 5 個模組在 top-level import yaml/jsonschema；修正前不得宣稱 stdlib-only）
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
   Python 版本拆成兩層（審查意見 4）：
   - **完整測試環境**：`python-version: ['3.10', '3.13']`。`requirements.txt` 釘 `pytest>=9.0,<10.0`，pytest 9 需要 Python ≥3.10，所以 3.9 跑不了完整套件。
   - **3.9 runtime smoke**（另開一個 job，不裝 `requirements.txt`）：只裝 runtime 實際需要的依賴，跑 README 路徑 A 的指令。實測（Python 3.9.25、不裝任何套件）：`governance_drift_checker.py` 可以執行；`quickstart_smoke.py` 和 `runtime_hooks.smoke_test` 會因為 `governance_tools/runtime_phase_policy.py:9 import yaml` 直接 `ModuleNotFoundError`。也就是說，README「不需安裝任何依賴」的說法與程式碼不符（併入計畫 1 修正），3.9 smoke job 至少要 `pip install "pyyaml>=6.0,<7"`。另外 `governance_tools/` 和 `runtime_hooks/` 在 3.9 上 `compileall` 全部通過（沒有 3.10+ 語法）。
     ```yaml
       runtime-smoke-py39:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v4
           - uses: actions/setup-python@v5
             with: { python-version: '3.9' }
           - run: pip install "pyyaml>=6.0,<7"     # 之後改成 requirements-runtime.txt
           - run: python -m compileall -q governance_tools runtime_hooks
           - run: python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
           - run: python governance_tools/governance_drift_checker.py --repo . --framework-root .
     ```
     新增 `requirements-runtime.txt`（只放 `pyyaml`），`requirements.txt` 改成 `-r requirements-runtime.txt` 再加上測試和 demo 依賴。README 改寫為「runtime 支援 3.9+（需要 pyyaml）；完整測試需要 3.10+」。
8. 加一個「skip 不可悄悄變多」的守門：CI 中 `pytest -rs` 輸出，若 Linux job skip 數超過基線（例如 80）就 fail，避免 skipif 被濫用來藏紅燈。

**風險**：Windows runner 慢、可能暴露更多既有問題（第一次先設 `continue-on-error: true` 觀察一週再轉 blocking）；skipif 會降低 Linux 上的覆蓋率，所以第 8 步是必要的。
**驗收**：Linux shallow clone + 無 pwsh：0 failed（skip 有明確原因）；full clone：C/D 類通過；Windows job 綠；完整測試 3.10 與 3.13 都綠；3.9 runtime smoke 綠。
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
- `governance_tools/external_tree_inventory_guard.py` L607–658 用 `git rev-list --objects -z <local> ^<remote>`，並以 NUL 切 `<OID>\0path=<path>\0` 格式解析。
- `-z`（`jt/rev-list-z`）在 2025-04-16 merge，列在 **Git 2.50.0** release notes（[RelNotes 2.50.0](https://github.com/git/git/blob/e9019fca/Documentation/RelNotes/2.50.0.adoc)、[merge commit](https://github.com/dscho/git/commit/1a1661bd41697a106481e9e2467d0f5a0697349a)）。
- git 2.47.3 實測：`-z` **不報錯、被靜默忽略**，輸出仍是換行分隔 → 整段被當成一個 record → L658 `invalid object ID record`。
- **影響**：本機或 CI 的 git < 2.50 時，pre-push 一律 `status: ERROR`（rc=4）並擋下 push；跟 shallow clone 無關。

#### 修正（審查意見 1：移除換行路徑 fallback）
上一版的「換行格式 fallback」**已刪除**。換行格式的 `rev-list --objects` 每個物件只給一個路徑名，而且路徑含換行時 git 會改寫，會靜默縮小 JSON 掃描範圍。這屬於被跳過的檢查，不能用 non-claim 帶過。改成以下兩條路徑，**掃描覆蓋範圍不得小於現行 `-z` 路徑**：

1. **版本偵測**（不靠輸出格式猜測，因為舊版 git 會靜默忽略 `-z`）：
   ```python
   _MIN_REV_LIST_Z = (2, 50)
   def _git_version(repository_root) -> tuple[int, int, int]:
       out = subprocess.run(["git", "--version"], env=_git_environment(),
                            capture_output=True, text=True, check=True).stdout
       m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out)
       if not m:
           raise PrePushScanError(f"cannot determine git version from {out.strip()!r}")
       return tuple(int(x or 0) for x in m.groups())
   ```
   另外加一個防呆：走 `-z` 路徑時，若 stdout 非空卻不含 `\0`，直接 `PrePushScanError("rev-list -z output is not NUL-delimited; refusing to scan")`，不得改用其他解析方式。
2. **git ≥ 2.50**：維持現行 `-z` 邏輯（不改）。
3. **git < 2.50，相容路徑（完整覆蓋）**：
   ```python
   def _collect_json_candidates_compat(repo, local_oid, remote_oid) -> dict[str, set[str]]:
       excl = [f"^{remote_oid}"] if not _is_zero_oid(remote_oid) else []
       # (a) 新增的全部物件 OID，不靠路徑名稱（--no-object-names 自 git 2.20 起）
       objs = _git(repo, "rev-list", "--objects", "--no-object-names", local_oid, *excl).split()
       # (b) 用 cat-file batch-check 查型別，只保留 blob
       types = _git_batch_check(repo, objs)          # {oid: "blob"|"tree"|"commit"|"tag"}
       new_blobs = {o for o, t in types.items() if t == "blob"}
       # (c) 新 commit 集合，每個 commit 用 ls-tree -r -z 取出全部 (blob, path)
       commits = _git(repo, "rev-list", local_oid, *excl).split()
       paths: dict[str, set[str]] = {}
       for c in commits:
           for rec in _git_bytes(repo, "ls-tree", "-r", "-z", "--full-tree", c).split(b"\0"):
               if not rec: continue
               meta, path = rec.split(b"\t", 1)
               mode, otype, oid = meta.split()
               if otype == b"blob" and oid.decode() in new_blobs:
                   paths.setdefault(oid.decode(), set()).add(path.decode("utf-8", "surrogateescape"))
       # (d) 完整性斷言：每個新 blob 都要找得到至少一個路徑，否則 fail-closed
       orphan = new_blobs - paths.keys()
       if orphan:
           raise PrePushScanError(f"compat scan could not attribute {len(orphan)} new blob(s) to a path; refusing to pass")
       return {oid: {p for p in ps if p.casefold().endswith(".json")}
               for oid, ps in paths.items() if any(p.casefold().endswith(".json") for p in ps)}
   ```
   - **覆蓋性論證**：新物件集合中的 blob，一定出現在某個新 commit 的 tree 裡（rev-list `--objects` 的定義）。`ls-tree -r` 列出每個新 commit 的**全部**路徑，所以每個新 blob 拿到的路徑集合是 `-z` 路徑的**超集**（`-z` 每個物件只給一個名稱）。步驟 (d) 保證沒有任何 blob 被靜默略過。
   - 代價：commit 多時 `ls-tree` 成本是 O(commits × tree size)。可接受，因為只掃 push 的增量 commit。另外設上限（例如 >5,000 個 commit）→ fail-closed，並提示 `git >= 2.50 recommended`，不做部分掃描。
4. **替代方案（若不想維護相容路徑）**：git < 2.50 直接 fail-closed：
   `status: ERROR, reason: external_tree_inventory_guard requires git >= 2.50 (found 2.47.3) for NUL-delimited rev-list; upgrade git` → README 前置需求寫明 `git >= 2.50`。**兩案擇一，不做靜默降級。**

- **測試**：
  - `tests/test_external_tree_inventory_guard.py` 加參數化：`monkeypatch` `_git_version` 分別回傳 `(2,47,3)` 與 `(2,50,0)`，兩條路徑對同一個 fixture repo（含 `a/b.json`、同一個 blob 出現在兩個路徑、檔名含空白和換行的 json）得到的 candidates，必須讓相容路徑 ⊇ `-z` 路徑。
  - 加一個 orphan 斷言測試：人為讓 `ls-tree` 少回一筆 → 必須 `PrePushScanError`。
  - CI 加 git 2.47 container job（見附註 1）真實跑一次，不只靠 monkeypatch。
- **驗收（兩案分開，第二輪審查意見 2）**：
  - **相容路徑案**：git 2.47 上掃描**完整跑完**，覆蓋範圍不縮小：C 類原有 5 個檔案（43 個測試）在 git 2.47 上**不修改測試就全綠**；新增的覆蓋性測試（相容路徑 ⊇ `-z` 路徑、orphan blob → `PrePushScanError`）全綠；git ≥2.50 上行為與現行相同。完成後可以宣稱「恢復 git < 2.50 的 push 能力」。
  - **最低版本案**：git 2.47 被**明確拒絕**：`status: ERROR`、訊息含 `requires git >= 2.50 (found 2.47.x)`，而且**沒有副作用**（不寫任何 artifact、ledger、receipt；測試對執行前後的 repo 狀態做 snapshot 比對）；git ≥2.50 上原有測試全綠。C 類那 43 個測試在 2.47 上要改成「預期明確拒絕」，或標記 `requires_git_2_50`。**這只是診斷訊息的改善，不會恢復舊版 git 的 push 能力**，不得宣稱已修好 C。
- **工作量**：相容路徑 1–1.5 天；只做 fail-closed 0.25 天。

### E 的根因：檔案 mtime 精度與 `started_at` 不同時鐘域（**獨立驗證項目，不併入下一個 slice**）
**現象**（暫時加 log 實測，已還原）：13 筆資料中，closeout 都在 session 開始之後寫入，但 `st_mtime` 比 envelope 的 `started_at` 早 1–4 ms，例如 `started_at 15:56:57.166251Z`、`mtime 15:56:57.164788Z`。

**相關程式碼（`governance_tools/session_end_hook.py` L1880–1962、`runtime_hooks/core/_canonical_closeout.py`）**：binding 依序有四層檢查：
1. **Session identity**（L1880–1902）：`session_id` 來源優先順序是 hook payload > current session file > generated；Codex 沒有明確 id 時 `ValueError`；記錄 `current_session_id_conflict`。
2. **時間先後**（L1908–1927）：只在「共用 closeout 檔存在、但 session 的 canonical closeout 還不存在」時才檢查。envelope 缺少 → `session_envelope_missing`；`closeout_mtime < started_at` → `closeout_before_session_start`；解析錯誤 → `session_envelope_invalid`。
3. **Candidate／consume-once**（L1929–1945）：`pick_latest_candidate` 取 `artifacts/runtime/closeout_candidates/<sid>/*.json` 最新一筆；`assess_session_closeout_binding` 檢查 `closeout-completions/<sid>.json`，已消耗 → `already_consumed`。
4. **內容綁定**（L1946–1955，`_assess_candidate_content_binding`）：共用 closeout 的 TASK_INTENT / WORK_COMPLETED / FILES_TOUCHED / OPEN_RISKS 必須與 session 自己的 candidate 一致。

第 2 層的用途是**拒絕在本 session 開始前就存在的舊共用 closeout 檔**（防重放）。問題出在拿「kernel 粗粒度檔案時鐘」去比「高精度 wall clock」。

**為什麼不只加 2 秒 tolerance**：tolerance 會讓「session 開始前 2 秒內寫的舊檔」通過第 2 層。這在 hook 快速重啟的情境正是要防的重放窗口；雖然第 3、4 層多半還擋得住，但等於把第 2 層的保證降級，而且沒有證明。

**修正：讓第 2 層兩邊用同一個時鐘域**
- `write_session_envelope` 在建立 envelope 時，同時以 `O_CREAT|O_EXCL` 建立 session 起始標記檔 `artifacts/runtime/sessions/<sid>.start`（只建一次，不覆寫），並在 envelope 記錄 `start_clock: "fs_marker"`。
- 第 2 層比較改成：
  ```python
  marker = _session_start_marker(session_id, project_root)
  if session_envelope.get("start_clock") == "fs_marker" and marker.is_file():
      start_ns = marker.stat().st_mtime_ns          # 與 closeout 同一個 FS 時鐘
      closeout_ns = closeout_path.stat().st_mtime_ns
      if closeout_ns < start_ns:
          pre_binding_status = "closeout_before_session_start"
  else:
      # 舊 envelope 或呼叫端自帶 started_at：維持現行 wall-clock 比較（只會更嚴、不會更鬆）
      ...現行邏輯不變...
  ```
- **保留性論證**：
  - 第 1、3、4 層**完全不修改**，程式碼路徑和輸入都不變。
  - 第 2 層：在同一個時鐘域裡，「closeout 在 marker 之後才寫」⇒ `closeout_ns >= start_ns`（單調時間戳的檔案系統上成立），所以合法 closeout 不再被誤擋；「closeout 在 marker 之前就寫好」⇒ `closeout_ns <= start_ns`。只有**同一個 tick 內**（≤ 一個 kernel tick）先寫的舊檔會得到 `==`，可能通過第 2 層。這個殘餘窗口必須由第 3 層（session 自己的 candidate）和第 4 層（內容一致）擋下，所以要有測試證明它被擋。
  - 沒有 marker 時退回現行比較，對舊資料不放寬。
- **必要測試（新增 `tests/test_session_end_binding_clock_domain.py`）**：
  1. 合法：marker 建立後才寫 closeout，closeout 的 mtime 設為 `start_ns + 1_000_000` → eligible，`closeout_status == valid`（取代現在 E 類 9 個失敗）。
  2. 舊檔重放：`os.utime(closeout, ns=start_ns - 1_000_000)` → `closeout_before_session_start`。
  3. 同 tick 重放：`closeout_ns == start_ns`，但內容與 candidate 不符 → 第 4 層 `mismatched_fields`，**不得 valid**。
  4. 同 tick，但 session 沒有 candidate → 不得 valid（證明第 3 層仍然生效）。
  5. 已消耗：存在 `closeout-completions/<sid>.json` → `already_consumed` → `stale_or_mismatched`（不變）。
  6. Session identity：hook payload 與 current session 衝突時，行為和現在相同（snapshot 比對）。
  7. 舊 envelope（沒有 `start_clock`）：行為與現行完全相同（回歸測試）。
- **驗收**：E 類 9 個測試在 Linux 上通過，而且是靠第 1 個測試的情境通過，**不是放寬比較**；第 2–7 個測試全綠；`tests/test_session_end_hook_*` 既有測試不退步。
- **工作量**：1–1.5 天（含測試）。**列為獨立驗證項目**：需要 owner 確認 marker 檔是否符合 `artifacts/runtime` 的 authority／cleanup 規則後才實作。

### 對計畫 2 的修正
- 原本「C 類先 fetch --unshallow 再決定 skip」作廢：**C 不能 skip**，依上面的 C 修正處理。
- D 類維持 `requires_full_history` skip；框架 CI 已經是 `fetch-depth: 0`，不受影響。
- E 類不能用 xfail，也不能只加 tolerance，依上面的 E 修正（獨立驗證項目）處理。
- Python 3.9 改為 runtime smoke job，見計畫 2 第 7 步。

---

## 附錄 B：Fleet 導入盤點（2026-10-21 00:08 台北時間；00:40 依審查意見重算並補上執行與保護資料）

**方法**：GitHub API 列出 Gavin0099 的 32 個公開 repo（含 6 個 fork），逐一 blobless 淺 clone（唯讀），檢查 default branch 的 tree、workflow、submodule gitlink、`governance/framework.lock.json`、2026-09-20 後的 commit 數。另外用 `gh api`（唯讀）查詢：(1) default branch 上名稱含 "govern" 的最近一次 workflow run 的 conclusion；(2) branch protection、rulesets、branch rules（查詢時間與回應摘錄見「Branch protection 證據」一節）。bug 曝露以框架 git 歷史判斷：guard `-z` 自 `67764bdf`（8/24）起，mtime 判斷自 `a0683a5c`（7/29）起，看 consumer 釘住的 commit 是否包含。**private repo 不可見；本機 `.git/hooks`、使用者層 agent 設定也看不到。**

欄位定義（審查意見 5）：
- **repo 內已設定**：workflow 檔案裡出現的治理工具呼叫（只代表「有寫」）。
- **最近執行結果**：default branch 上最近一次治理 workflow 的 conclusion（代表「有跑、結果如何」）。
- **擋 merge**：branch protection 是否把治理 check 列為 required（代表「真的會擋」）。

| Repo | 模式 | 釘住／落後 e8e6779 | repo 內已設定 | 最近執行結果 | 擋 merge | Hooks（已 commit） | guard bug | mtime bug | 9/20 後 commits |
|---|---|---|---|---|---|---|---|---|---|
| campaign-forge | submodule | e8e6779 / 0 | 無治理 workflow | – | 否 | – | 是 | 是 | 13 |
| DiceMercenaries | submodule | 2a09d54 / 5 | drift + memory blocker | success（10-14） | **否**（未設保護） | Copilot | 是 | 是 | 18 |
| TacticalGo | submodule | 2a09d54 / 5，**無 lock** | drift | 查無 run | 否 | Copilot | 是 | 是 | 97 |
| BeatLab | submodule | 15722da / 38 | drift | 查無 run（default branch 為 `codex/bl-001-app-foundation`） | 否 | – | 是 | 是 | 6 |
| fwupd（fork） | submodule | 24ba84c / 76 | drift | **failure**（10-01） | 否 | Copilot | 是 | 是 | 40 |
| wasteland-chronicles | submodule | 3709097 / 83，**無 lock** | drift | success（10-05） | 否 | – | 是 | 是 | 118 |
| ai-assisted-ssdlc-docs | submodule | 46b2574 / 86 | drift + readiness | success（10-02） | **是，但 admin 可略過**（`governance-drift`、`ssdlc-validators`；`enforce_admins=false`） | – | 是 | 是 | 83 |
| crystal-bracelet-studio | submodule | 1d213ba / 92 | drift | **failure**（09-17） | 否 | – | 是 | 是 | 0（9/20 後無 commit） |
| uvm-agent-lab | submodule | 1b85e29 / 362 | drift + quickstart_smoke | success（10-12） | **是**（`Comprehensive Verification & AI Governance Gate`） | Copilot | 是 | 是 | 9 |
| usb-logic-trace-correlator | copy | 1004427 / 373 | drift | **failure**（09-07） | 否 | Claude/Gemini/Copilot | 是 | 是 | 0（9/20 後無 commit） |
| spec-reference-kit | submodule | a694ddb / 819 | drift + memory CI + hook validator | success（08-10） | 否 | Copilot lifecycle | 否 | 是 | 0（9/20 後無 commit） |
| zephyr（fork） | submodule | da71729 / 861 | drift | 查無 run | 否 | Copilot lifecycle | 否 | 是 | 0（9/20 後無 commit） |
| usb-if-hub-spec-reference | submodule | 61111f5 / 885 | Governance Validation（未呼叫 governance_tools） | success（08-03） | **是**（`Fixture Smoke (Required)`，非治理工具） | Claude | 否 | 是 | 0（9/20 後無 commit） |
| AI-Slide-Design-System-Repo | submodule | 84077ee / 959 | drift workflow（未偵測到 checker 呼叫，`submodules: false`） | success（07-28） | 否 | – | 否 | 否 | 0（9/20 後無 commit） |
| verilog-domain-contract | submodule | 80e5ec5 / 1721，**lock≠gitlink** | drift + smoke + readiness | **failure**（07-03） | 否 | Claude | 否 | 否 | 0（9/20 後無 commit） |
| ZoneTruth | copy | 6f0ca32 / 2075 | drift | **failure**（06-18） | 否 | – | 否 | 否 | 0（9/20 後無 commit） |
| Ashfall | copy | 8a4262a / 2144 | drift + janitor 等 | success（06-12） | 否 | – | 否 | 否 | 0（9/20 後無 commit） |
| financial-pdf-reader | copy | ca5d26d / 2184 | drift + pytest | **failure**（06-11） | 否 | Claude | 否 | 否 | 0（9/20 後無 commit） |
| Hearth | submodule | 57db6c1 / 2270，**lock=9b0e6b7≠gitlink** | drift | success（06-16） | 否 | Claude/Gemini/Copilot | 否 | 否 | 0（9/20 後無 commit） |
| usb-if-hid-spec-reference | copy | 737fcd4 / 1952 | 無治理 workflow | – | 否 | – | 否 | 否 | 0（9/20 後無 commit） |
| lecroy-vse-toolkit | copy，**無 lock** | 無法判定 | drift | **failure**（10-02） | 否 | – | ? | ? | 62 |

**計數（由上表逐列重算）**：guard bug 涵蓋 **10** 個 repo（上一版誤寫為 12）；mtime bug 涵蓋 **13** 個（上一版誤寫為 15）；lecroy-vse-toolkit 因為沒有 lock，無法判定。

未導入：DeviceTraceKit、SnackBuddies（空 repo）、KidsCharacterKit、sprout-space、wordtreegarden-site；fork：hermes-agent、ulani-epaper、crosspoint-reader、FinancialAdvisorGPT、Windows-driver-samples。


### Branch protection 證據（第二輪審查意見 3）
- **查詢時間**：2026-10-21 00:48–00:50（台北時間），以 `gh api` 唯讀查詢；10:14 用重跑腳本再查一次，結果一致。去敏後的原始輸出：[`evidence/branch-protection-2026-10-21.txt`](evidence/branch-protection-2026-10-21.txt)；重跑腳本：[`evidence/query_branch_protection.sh`](evidence/query_branch_protection.sh)。沒有 admin 權限的人重跑時，403/404 代表「無法驗證」，不代表「未設保護」。
- **身分與權限**：`gh` 以 `Gavin0099` 登入，token scopes `gist, read:org, repo, workflow`；21 個 repo 的 `GET /repos/Gavin0099/{repo}` 都回傳 `permissions.admin=true`。因此 404 的 `"Branch not protected"` 是**可驗證的「未設保護」**，不是權限不足造成的 404。本次沒有遇到 403 或權限受限的回應；若日後遇到，應標記為「unknown / 無法驗證」，不得寫成「未設保護」。
- **查詢分支**：各 repo 的 `default_branch`（BeatLab 為 `codex/bl-001-app-foundation`，其餘為 `main`）。
- **Endpoint**：`GET /repos/Gavin0099/{repo}/branches/{branch}/protection`、`GET /repos/Gavin0099/{repo}/rulesets`、`GET /repos/Gavin0099/{repo}/rules/branches/{branch}`。
- 所有 repo 的 rulesets 和 branch rules 都回傳 200 `[]`（沒有 ruleset），所以保護狀態完全由 classic branch protection 決定。

| Repo | 查詢分支 | `branches/{b}/protection` | `rulesets` | `rules/branches/{b}` | 判定 |
|---|---|---|---|---|---|
| AI-Slide-Design-System-Repo | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| Ashfall | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| BeatLab | `codex/bl-001-app-foundation` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| DiceMercenaries | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| Hearth | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| TacticalGo | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| ZoneTruth | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| ai-assisted-ssdlc-docs | `main` | 200：`contexts=["governance-drift","ssdlc-validators"]`, `strict=false`, `enforce_admins=false`, 無 PR review 要求 | 200 `[]` | 200 `[]` | 治理 check 為 required；**admin 可略過**（`enforce_admins=false`） |
| campaign-forge | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| crystal-bracelet-studio | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| financial-pdf-reader | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| fwupd | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| lecroy-vse-toolkit | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| spec-reference-kit | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| usb-if-hid-spec-reference | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| usb-if-hub-spec-reference | `main` | 200：`contexts=["Fixture Smoke (Required)"]`, `strict=true`, `enforce_admins=true`, 無 PR review 要求 | 200 `[]` | 200 `[]` | 有 required check，但不是治理工具 |
| usb-logic-trace-correlator | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| uvm-agent-lab | `main` | 200：`contexts=["Comprehensive Verification & AI Governance Gate"]`, `strict=true`, `enforce_admins=true`, 無 PR review 要求 | 200 `[]` | 200 `[]` | 治理 check 為 required，admin 也受限 |
| verilog-domain-contract | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| wasteland-chronicles | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |
| zephyr | `main` | 404：`{"message":"Branch not protected"}` | 200 `[]` | 200 `[]` | 未設保護（已驗證） |

**更正後的結論**：會擋 merge 的治理 required check 只有 2 個 repo：ai-assisted-ssdlc-docs、uvm-agent-lab。其中 **ai-assisted-ssdlc-docs 的 `enforce_admins=false`**，身為 admin 的 owner 可以略過，對 owner 自己的 push／merge 不構成強制；**對 admin 也強制的只有 uvm-agent-lab 1 個**。usb-if-hub-spec-reference 有保護，但 required check 不是治理工具。其餘 18 個 repo 已驗證為未設保護。

### 發現
1. **「已設定」≠「有跑通」≠「會擋」**：有治理 workflow 的 19 個 repo 中，最近一次 default branch 執行結果為 failure 的有 **7 個**（fwupd、crystal-bracelet-studio、usb-logic-trace-correlator、verilog-domain-contract、ZoneTruth、financial-pdf-reader、lecroy-vse-toolkit），查無 run 的有 3 個。**把治理 check 設為 required 的只有 ai-assisted-ssdlc-docs 和 uvm-agent-lab 兩個**，其中只有 uvm-agent-lab 對 admin 也強制（ai-assisted-ssdlc-docs 為 `enforce_admins=false`，證據見上節）；usb-if-hub-spec-reference 的 required check 不是治理工具。上一版說 DiceMercenaries「真的有 enforce」不正確：它的 memory blocker 有設定也執行成功，但 branch 沒有保護，**不會擋 merge**。
2. CI 設定大多只到 `governance_drift_checker`，它檢查治理檔本身的漂移，不檢查 agent 是否越界或宣稱膨脹。
3. **版本分裂**：1 個最新、7 個落後 5–92 個 commit、其餘落後 300–2,270 個；3 個沒有 lock、2 個 lock 與 gitlink 不一致。
4. **bug 曝露**：guard bug（10 個 repo）只在本機 pre-push 且 git < 2.50 時觸發，CI 沒有呼叫 guard；mtime bug（13 個 repo）主要在 Linux 或快速連續觸發 hook 時發生。
5. **活躍度與深度錯配**：9/20 後 commit 數最多的四個 repo（wasteland-chronicles 118、TacticalGo 97、ai-assisted-ssdlc-docs 83、lecroy-vse-toolkit 62）中，只有 ai-assisted-ssdlc-docs 會擋 merge。TacticalGo 和 lecroy-vse-toolkit 沒有 lock，lecroy-vse-toolkit 最近一次執行是 failure。
6. **fork 污染風險**：fwupd、zephyr 是上游大專案的 fork。

### 建議（fleet 側，依優先順序）
1. 先讓已設定的治理 workflow 執行成功（處理 failure 的 7 個，或標記 frozen 後移除），再談加 gate。
2. 活躍 repo：補 lock，並把治理 check 設為 branch protection required（DiceMercenaries、wasteland-chronicles、TacticalGo）。
3. verilog-domain-contract、Hearth：跑 `f7_full_update.py` dry-run，處理 lock／gitlink 不一致。
4. 9/20 後無 commit 的 repo：由 owner 決定是否標記 `frozen`。frozen 只停止升級提醒，仍然要報告 lock／gitlink 不一致（見 B-3）。
5. fork（fwupd、zephyr）：治理檔移到 `governance/*` 分支，或改用本機設定。

---

## 框架側根因與修正（Framework-side root causes & fixes）

> 盤點顯示問題不在個別 repo 偷懶，而在**框架的預設值**：導入預設只到 drift check、沒有升級拉力、lock 不一致不會擋、fleet 工具看不出深度。下面四項是在框架端修，讓每個 consumer 都受益。

### B-1. 導入預設只到 drift check → PR scope gate（**先 advisory，contract 定義完成後才可轉 enforce**）

**根因**：`governance_tools/adopt_governance.py` L21、L838–839 只複製 `baselines/repo-min/.github/workflows/governance-drift.yml`，沒有任何預設 workflow 比對 PR diff 與 task contract。

**前置條件（需要 owner 先確認 contract，審查意見 2）**
- **Trusted contract 來源**：gate 只能讀 **base 端（受保護 ref）** 的 contract，**不得讀 PR checkout 的版本**，否則 PR 可以自己放寬 scope。具體做法：
  ```bash
  git fetch --no-tags origin "${BASE_SHA}"
  git show "${BASE_SHA}:governance/pr_scope_contract.yaml" > "$RUNNER_TEMP/trusted_contract.yaml"
  ```
  `BASE_SHA` 取自 `github.event.pull_request.base.sha`；只有在 base branch 被保護時，這份 contract 才算 trusted，gate 啟動時要檢查保護狀態，沒有保護就降為 advisory 並在 summary 說明。workflow 用 `on: pull_request`（不用 `pull_request_target`），也不執行 PR 裡的程式碼來解析 contract：框架工具固定從 base 端的 submodule commit 讀取。
- **Contract 變更核准路徑（已決定：bot 開立、Gavin 以 CODEOWNER 核准；2026-10-21 owner 決策）**
  - **Bot 身分**：採用 **GitHub App**（例如 `agov-contract-bot`，PR 作者顯示為 `agov-contract-bot[bot]`），**不使用 machine user**。原因：App 使用短期 installation token、可以限定安裝的 repo、身分可由 user id 加上 `type: Bot` 驗證，也不佔用一個需要另外保管密碼和 2FA 的人類帳號。
    - App 權限最小化：`contents: write`（用途只限推送 `governance/contract-change/*` 分支）、`pull_requests: write`、`metadata: read`。**不給** `administration`、`workflows`、`checks:write`、`members`；只安裝在需要的 repo。
    - GitHub REST 的權限是 repo 層級，無法限制「只能寫某個分支或路徑」，所以「只能改 contract 路徑」由下面的 gate 規則和 branch protection 來保證，不依賴 App 權限本身。
    - Bot **不得**列入 `.github/CODEOWNERS`（gate 偵測到就 BLOCKED）。Bot 不能 approve：它不是 CODEOWNER，gate 也排除 bot 的 review。
  - **提出變更的方式**：由 `workflow_dispatch`（輸入 contract 變更內容或 patch），或帶 `contract-change` label 的 issue（issue 開立者必須是 repo collaborator）觸發 workflow。workflow 用 App token（`actions/create-github-app-token`）建立 `governance/contract-change/<issue#>` 分支，只寫入 contract 檔，再開出 **只改 contract 的 PR**。產生 contract 內容的步驟**不執行 PR 或 issue 內的程式碼**，只做 YAML 解析與 `validate_contract` 檢查。
  - **Gate 規則**（contract、CODEOWNERS、bot 身分設定一律取自 BASE_SHA）：
    1. **作者必須是 bot**：`GET /repos/{o}/{r}/pulls/{n}` 的 `user.login == "<slug>[bot]"`、`user.type == "Bot"`，而且 `user.id` 與 base 端設定的 bot user id 相同（設定時以 `GET /users/<slug>[bot]` 取得）。不能只比 login 字串。
    2. **PR 內所有 commit 都必須由 bot 撰寫和提交**：`GET /pulls/{n}/commits` 每筆的 `author` 與 `committer` 都要通過規則 1 的身分比對，有任何一筆不是 → `BLOCKED: non_bot_commit_in_bot_pr`。這可以防止有人把 commit 推進 bot 分支來搭便車。
    3. **Bot PR 只能動 contract 路徑**：有任何非 contract 檔 → `BLOCKED: bot_pr_touches_non_contract_files`。這是防止 bot token 被濫用的主要防線。
    4. **核准**：每位 reviewer 取最後一次具決定性的 review（APPROVED / CHANGES_REQUESTED / DISMISSED），必須是 `APPROVED`、`commit_id == head SHA`、reviewer 列在 base 端 CODEOWNERS 的 contract 路徑 owner 中，而且不是 bot、不是 PR 作者。符合 → `PASS`，否則 `NEEDS_APPROVAL`。
    5. **人寫的 contract PR**：維持 `NEEDS_APPROVAL`。唯一例外是存在第二位 owner：作者本身是 owner，而且由**另一位** owner 核准（兩人規則）。非 owner 開的 contract PR，即使 Gavin 核准也不 PASS，一律要走 bot 流程。
    6. 混合 PR（contract 加其他檔）→ `BLOCKED`；bot 被列入 CODEOWNERS → `BLOCKED: bot_listed_in_codeowners`；base 端沒有 contract owner → `BLOCKED`。
  - **GitHub 端設定**：`.github/CODEOWNERS` 加 `/governance/pr_scope_contract.yaml @Gavin0099`；branch protection 開啟 *Require review from Code Owners*，並建議 `enforce_admins=true`（目前 fleet 只有 uvm-agent-lab 這樣設定）。workflow 除了 `pull_request`，也訂閱 `pull_request_review: [submitted, dismissed]`，核准後重新評估。gate 只需要 `pull-requests: read`、`contents: read`。
  - **已知限制**：bot 的 private key 外洩時，攻擊者可以開 contract PR，但仍然需要 Gavin 在 head SHA 上核准，所以最多只能「提出」變更。key 存在 repo／environment secret，限 `workflow_dispatch` 所在的 environment 使用，並定期輪替。
- **Fail-closed 欄位規則**：trusted contract 缺失、無法解析、缺少 `allowed_scope` 或 `forbidden_scope` 欄位、`allowed_scope` 為空 list、glob 含 `..` 或絕對路徑 → `BLOCKED`（附原因代碼）。**不提供 `["**"]` 預設值**。上一版建議以 `allowed_scope: ["**"]` 讓導入即綠燈，已撤回：那等於沒有 scope 檢查。
- **模式**：預設 `advisory`（只寫 summary，exit 0）。只有在 (a) trusted contract 存在且通過欄位檢查、(b) base branch 受保護、(c) CODEOWNERS 已涵蓋 contract 路徑，三者同時成立時，`adopt_governance --pr-gate-mode enforce` 才允許設為 enforce；任一條件不成立就拒絕並說明。

**要改的檔案**：新增 `governance_tools/pr_scope_gate.py`、`baselines/repo-min/.github/workflows/governance-pr-gate.yml`、`baselines/repo-min/governance/pr_scope_contract.example.yaml`（範例，**不會自動成為 trusted contract**）；修改 `governance_tools/adopt_governance.py`（`--pr-gate-mode {advisory,enforce}`、`--no-pr-gate`）；測試 `tests/test_pr_scope_gate.py`、擴充 `tests/test_adopt_governance.py`。

**評估核心**（stdlib；`git diff -z` 各版本 git 都支援；contract、owners、bot 設定一律取自 BASE_SHA）：
```python
import re
REQUIRED = ("allowed_scope", "forbidden_scope")

def _match(path, glob):
    rx, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i): rx += "(?:.*/)?"; i += 3
        elif glob.startswith("**", i): rx += ".*"; i += 2
        elif glob[i] == "*": rx += "[^/]*"; i += 1
        elif glob[i] == "?": rx += "[^/]"; i += 1
        else: rx += re.escape(glob[i]); i += 1
    return re.fullmatch(rx, path) is not None

def validate_contract(c):
    errs = [f"missing_field:{k}" for k in REQUIRED if k not in c]
    if not errs and not c["allowed_scope"]:
        errs.append("empty_allowed_scope")
    for g in c.get("allowed_scope", []) + c.get("forbidden_scope", []):
        if g.startswith("/") or ".." in g.split("/"):
            errs.append(f"unsafe_glob:{g}")
    return errs

def _is_bot(user, bot):
    """bot = {"login": "<app-slug>[bot]", "id": <bot user id>}，取自 base 端設定，並用 GET /users/{login} 核對 id。"""
    return bool(user) and user.get("type") == "Bot" and user.get("id") == bot["id"] \
        and user.get("login", "").lower() == bot["login"].lower()

def owner_approvals(reviews, head_sha, owners, pr_author, bot):
    latest = {}
    for rv in reviews:                                   # GET /pulls/{n}/reviews，依時間排序
        if rv["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[rv["user"]["login"].lower()] = rv
    return [u for u, rv in latest.items()
            if u in owners and u != pr_author.lower() and u != bot["login"].lower()
            and rv["state"] == "APPROVED" and rv["commit_id"] == head_sha]

def evaluate(files, contract, contract_paths, *, pr, commits, reviews, owners, bot):
    """contract / owners / bot 設定一律來自 BASE_SHA；pr = GET /pulls/{n}；commits = GET /pulls/{n}/commits。"""
    if errs := validate_contract(contract):
        return {"decision": "BLOCKED", "reason": errs}
    if bot["login"].lower() in owners:
        return {"decision": "BLOCKED", "reason": ["bot_listed_in_codeowners"]}
    head_sha, author = pr["head"]["sha"], pr["user"]
    touched = [f for f in files if f in contract_paths]
    bot_pr = _is_bot(author, bot)
    if bot_pr:
        # 防止 bot token 被拿來改非 contract 檔：bot PR 只能動 contract 路徑
        if len(touched) != len(files):
            return {"decision": "BLOCKED", "reason": ["bot_pr_touches_non_contract_files"],
                    "files": sorted(set(files) - set(touched))}
        foreign = [c["sha"] for c in commits
                   if not (_is_bot(c.get("author"), bot) and _is_bot(c.get("committer"), bot))]
        if foreign:
            return {"decision": "BLOCKED", "reason": ["non_bot_commit_in_bot_pr"], "commits": foreign}
    if not touched:                                       # 一般 PR：照 scope 評估
        forbidden = [f for f in files if any(_match(f, g) for g in contract["forbidden_scope"])]
        outside = [f for f in files if not any(_match(f, g) for g in contract["allowed_scope"])]
        return {"decision": "BLOCKED" if forbidden else "FAIL" if outside else "PASS",
                "forbidden_hits": forbidden, "outside_scope": outside}
    if len(touched) != len(files):
        return {"decision": "BLOCKED", "reason": ["contract_change_mixed_with_other_files"]}
    if not owners:
        return {"decision": "BLOCKED", "reason": ["no_codeowners_for_contract_path"]}
    approvers = owner_approvals(reviews, head_sha, owners, author["login"], bot)
    if not bot_pr:
        # 人寫的 contract PR：作者本身必須是 owner，且另一位 owner 核准（兩人規則）
        if author["login"].lower() in owners and approvers:
            return {"decision": "PASS", "reason": ["human_contract_pr_second_owner_approved"],
                    "approved_by": approvers}
        return {"decision": "NEEDS_APPROVAL", "reason": ["human_authored_contract_pr_requires_second_owner"]}
    if approvers:
        return {"decision": "PASS", "reason": ["bot_contract_pr_codeowner_approved"],
                "approved_by": approvers, "head_sha": head_sha}
    return {"decision": "NEEDS_APPROVAL", "reason": ["bot_contract_pr_awaiting_codeowner_review"]}
```
**已實際執行驗證**（2026-10-21 01:02 台北時間，Python 3.13，`run_cases.py` 共 14 個案例，rc=0；bot 範例設定為 `agov-contract-bot[bot]` / id `900001`）：

| 案例 | 結果 |
|---|---|
| bot 開立，owner 在 head SHA 上核准 | PASS |
| 人寫 contract PR（Gavin 自己開） | NEEDS_APPROVAL |
| bot 開立，未核准 | NEEDS_APPROVAL |
| bot 開立，核准在舊 commit 上 | NEEDS_APPROVAL |
| bot 開立，owner 核准後又 request changes | NEEDS_APPROVAL |
| bot PR 含非 contract 檔 | BLOCKED |
| bot PR 中有非 bot 的 commit | BLOCKED |
| 冒名 bot（login 相同，id／type 不符） | NEEDS_APPROVAL（視為人寫 PR） |
| bot 被列入 CODEOWNERS | BLOCKED |
| 人寫 contract PR，由第二位 owner 核准 | PASS |
| 非 owner 人寫 contract PR，Gavin 核准 | NEEDS_APPROVAL |
| 人寫混合 PR | BLOCKED |
| 一般 PR，在 scope 內 | PASS |
| 一般 PR，碰到 forbidden 路徑 | BLOCKED |

`NEEDS_APPROVAL` 在 CI 上是非零 exit（check 失敗），所以未核准的 contract PR 不會被 merge。
上面的 `_match` 已明確定義 `**` 語意（轉成 regex：`*` 不跨越 `/`，`**` 可以跨越），不使用 `fnmatch`（`fnmatch` 的 `*` 會跨越 `/`）。

**測試**：PR 端修改 contract 時 gate 仍用 base 版本；上表 14 個案例移入 `tests/test_pr_scope_gate.py`；pulls、commits、reviews API 用 fixture JSON 模擬；缺欄位／空 `allowed_scope`／unsafe glob → BLOCKED；base branch 未保護 → advisory 降級並在 summary 說明；`**` 匹配語意測試。
**驗收**：上面全部測試綠；在一個 fixture consumer 上以 advisory 模式試跑一週，看誤擋率後，由 owner 決定是否轉 enforce。
**工作量**：粗估 2–3 天（不含 contract 內容設計）。**實作前需要 owner 確認 contract 檔路徑、欄位 schema、CODEOWNERS 人選。**

### B-2. 沒有升級拉力 → release tag + reusable Action + drift checker 版本落後升級警告

> **實作前需要 owner 確認**：tag／版本策略、`known_defects.json` 格式、落後門檻。lock 路徑為 `governance/framework.lock.json`；`frozen` 只抑制本項的升級提醒（見 B-3）。

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

### B-3. lock 一致性只是 report-only → CI 在「缺 lock」或「lock≠gitlink」時 fail（**需先確認 contract**）

**實際路徑與既有邏輯（審查意見 3）**：lock 位於 **`governance/framework.lock.json`**（`framework_versioning.py:113`、`external_governance_submodule_updater.py:45 FRAMEWORK_LOCK_RELATIVE_PATH`、`guard_enforcement_census.py:355`、`governance_maturity_summary.py:255`、`update_receipt.py:37`）。上一版寫的根目錄 `framework.lock.json` 有誤，已更正。實作要**重用**下列既有函式，不另寫解析：
- 讀 lock：`governance_tools/framework_versioning.py::load_framework_lock(repo_root)`（`utf-8-sig`，回傳 dict 或 `None`）。
- 讀 gitlink：`governance_tools/external_governance_submodule_updater.py::_tracked_gitlinks(repo)`（`git ls-files --stage -z`，只取 mode `160000`、stage 0），加上 `_governance_submodule_paths_from_gitmodules(repo)` / `_resolve_submodule_path` 決定框架 submodule 路徑（實測 consumer 有 `ai-governance-framework`、`.ai-governance-framework`、`additional/ai-governance-framework` 三種）。
- 建議把 `_tracked_gitlinks` 與 submodule path 解析提升為公開 helper（例如移到 `framework_versioning.py`），drift checker 和 updater 共用，避免兩份實作。

**步驟**
```python
# governance_tools/governance_drift_checker.py（新增檢查）
from governance_tools.framework_versioning import load_framework_lock
from governance_tools.external_governance_submodule_updater import (
    _tracked_gitlinks, _governance_submodule_paths_from_gitmodules)   # 之後改成公開 helper

def check_lock_consistency(repo: Path) -> list[dict]:
    lock = load_framework_lock(repo)
    sub_paths = _governance_submodule_paths_from_gitmodules(repo)
    gitlinks = dict(_tracked_gitlinks(repo))
    is_submodule = any(p in gitlinks for p in sub_paths)
    issues = []
    if lock is None:
        return [{"id": "lock_missing", "path": "governance/framework.lock.json",
                 "severity": "error" if is_submodule else "warning"}]
    frozen = lock.get("status") == "frozen"
    if is_submodule:
        actual = next(gitlinks[p] for p in sub_paths if p in gitlinks)
        if lock.get("adopted_commit") != actual:
            # frozen 也不豁免：帳實不符一律報告
            issues.append({"id": "lock_gitlink_mismatch", "severity": "error",
                           "lock": lock.get("adopted_commit"), "gitlink": actual})
    if frozen:
        issues.append({"id": "upgrade_reminders_suppressed", "severity": "info",
                       "reason": lock.get("frozen_reason")})
    return issues
```
- **`frozen` 語意**：只抑制 B-2 的版本落後／升級提醒；**不會**抑制 `lock_missing`、`lock_gitlink_mismatch` 或 `known_defects` 的報告。上一版寫的「frozen → pass」已撤回。
- copy-based consumer：缺 lock 給 warning（維持 audit-only 定位）；沒有 gitlink 可比對時，報告寫明 `actual_sha: not_applicable(copy)`，不得當成一致。
- lock schema（`schemas/`）加 `status: active|frozen`、`frozen_reason`，需要 owner 確認欄位名稱。

**rollout**：第一個 release 只給 warning，並在 release notes 預告；下一個 release 轉 error。受影響的已知 repo：verilog-domain-contract、Hearth（不一致）；TacticalGo、wasteland-chronicles（submodule 但沒有 lock）。
**測試**：用 fixture 覆蓋：submodule 缺 lock → error；lock≠gitlink → error，並印出兩個 SHA；frozen 且不一致 → 仍然 error 加 info；frozen 且一致 → 只有 info；copy 缺 lock → warning；三種 submodule 路徑都要能解析。
**驗收**：上面全部綠；對 fleet 實跑時，verilog-domain-contract、Hearth 被標出不一致。
**工作量**：粗估 1–1.5 天。**實作前需要 owner 確認 frozen 欄位 schema 與 warning→error 的時程。**

### B-4. Fleet 7 訊號看不出深度 → 導入深度 L0–L4

> **實作前需要 owner 確認**：等級定義，以及「已設定／執行成功／擋 merge」三層的證據來源。後兩層需要 Actions 與 branch protection 的讀取權限；沒有權限時一律標 `unknown`，不得往上判級。

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

### 附註 1：CI matrix 缺口（舊版 git、Windows、Python 版本分層）
- 兩個真 bug 都是因為 CI 只跑 `ubuntu-latest` 加新版 git 才沒被抓到。
- 在 `.github/workflows/governance.yml` 加（Python 版本依審查意見 4 分層：完整測試 ≥3.10，3.9 只跑 runtime smoke，見計畫 2 第 7 步）：
  ```yaml
    compat-matrix:
      strategy:
        fail-fast: false
        matrix:
          include:
            - { name: old-git,  os: ubuntu-latest,  container: 'debian:trixie' }  # git 2.47，Python 3.13
            - { name: py310,    os: ubuntu-latest,  container: '', python: '3.10' }
            - { name: windows,  os: windows-latest, container: '', python: '3.11' }
      runs-on: ${{ matrix.os }}
      container: ${{ matrix.container || null }}
      steps: [ ... checkout(fetch-depth: 0) / setup-python 或 apt 安裝 python3 / pip install -r requirements.txt / pytest ... ]
  ```
  container job 要用 `apt-get install -y git python3 python3-venv`，並在 venv 內安裝依賴；Windows job 見計畫 2。
- old-git job 是 C 修正的**驗收條件**，不是選配。
- **工作量**：粗估 0.5–1 天（不含修掉第一次跑出來的失敗）。

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

### 建議實作順序（依審查意見重新排列）
1. **下一步只做一件事：old-git 相容 slice**。依附錄 A 的 C 修正：版本偵測，加上相容路徑（完整覆蓋）或明確 fail-closed（擇一），附 old-git CI job 和覆蓋性測試。這是唯一不需要額外 contract 決策、而且會讓使用者 push 被擋的問題。完成後出 patch release。
2. **mtime（E）是獨立驗證項目**：先由 owner 確認 session start marker 是否符合 `artifacts/runtime` 的 authority 規則，再實作同時鐘域修正與 7 個 binding 保留測試。不與第 1 步合併。
3. **以下每一項都要先確認 contract，才能開始實作**：
   - B-3 lock 一致性：`frozen` 欄位 schema、warning→error 時程。
   - B-2 升級拉力：tag 策略、`known_defects.json` 格式、落後門檻。
   - B-1 PR scope gate：contract 核准模式已決定（GitHub App bot 開立，加上 Gavin 以 CODEOWNER 核准）；仍待確認 trusted contract 路徑與 schema、App 名稱與安裝範圍、base branch 保護要求；確認前只能以 advisory 存在。
   - B-4 導入深度 L0–L4：等級定義與「已設定／執行成功／擋 merge」三層判定的證據來源（需要 API 權限時要另外說明）。
4. 計畫 1、計畫 2 其餘部分（README、skipif、Python 分層）、計畫 3、計畫 4 可以平行排程，不阻塞上面幾項。

**工作量**：全部合計約 8–11 人天，為**粗估**，contract 確認後要重估。B-1 加上 contract 設計、E 的驗證，可能明顯超出。

---

## Review response（回應 PR #214 審查，基準 ea64db73）

| # | 審查意見 | 處理 | 位置 |
|---|---|---|---|
| 1 | old-git fallback 會靜默縮小掃描範圍（原 L329–338） | 刪除換行路徑 fallback。改為版本偵測，加上相容路徑（`--no-object-names` + `cat-file --batch-check` + `ls-tree -r -z`，附覆蓋性論證與 orphan blob fail-closed 斷言），或明確 fail-closed 要求 git ≥2.50（擇一）。刪除用 non-claim 帶過的寫法。 | 附錄 A「C 的根因」 |
| 2 | PR scope gate 的 contract 來源與核准路徑（原 L427–471） | contract 只從 base（受保護 ref）讀取；contract 變更必須單獨 PR 加 CODEOWNERS 核准，混在一般 PR 中 → BLOCKED；缺欄位、空 `allowed_scope`、unsafe glob → BLOCKED；撤回 `["**"]` 預設值；contract 定義完成前只能 advisory。 | B-1 |
| 3 | lock 路徑與 frozen 語意（原 L539–550） | 改用 `governance/framework.lock.json`；重用 `load_framework_lock`、`_tracked_gitlinks`、`_governance_submodule_paths_from_gitmodules`；frozen 只抑制升級提醒，仍然報告 lock／gitlink 不一致。 | B-3 |
| 4 | Python 3.9 matrix 與 pytest 9 衝突（原 L125） | 完整測試改為 3.10 / 3.13；3.9 另開 runtime smoke job（只裝 pyyaml）。實測發現 quickstart_smoke 在無依賴環境下需要 pyyaml，與 README 不符，已列入計畫 1。 | 計畫 2 第 7 步、附註 1 |
| 5 | Fleet 計數與用詞（原 L369–398） | 依表格重算：guard 10、mtime 13（上一版的 12 / 15 有誤）。欄位拆成「repo 內已設定／最近執行結果／擋 merge」，並用 `gh api` 補上 run conclusion 與 branch protection：只有 2 個 repo 把治理 check 設為 required，7 個最近一次執行為 failure。「已停」改為「9/20 後無 commit」。更正 DiceMercenaries「真的有 enforce」的說法。 | 附錄 B |
| + | mtime 修正不只加 tolerance（原 L350–354） | 分析四層 binding（identity / 時間先後 / candidate consume-once / 內容綁定），改成以 session start marker 做同時鐘域比較，其餘三層不修改，並附 7 個保留性測試；列為獨立驗證項目。 | 附錄 A「E 的根因」 |
| + | Roadmap | 下一步只做 old-git slice；mtime 獨立；B-1～B-4 每項都要先確認 contract；8–11 人天標為粗估。 | 建議實作順序 |

### 第二輪審查（基準 dc2a415）

| # | 審查意見 | 處理 | 位置 |
|---|---|---|---|
| 1 | （blocking）只改 contract 的 PR 在範例程式碼中一律 BLOCKED，與 CODEOWNERS 核准路徑矛盾 | 改成明確的獨立核准路徑：只改 contract → `NEEDS_APPROVAL`；透過 reviews API 驗證到 base 端 CODEOWNER、非作者、在 head SHA 上的最後一次 review 為 APPROVED 時才 PASS；混合 PR 仍然 BLOCKED。範例程式碼實際執行 10 個案例全部符合預期（已核准 → PASS，未核准／舊 commit／非 owner／作者自核 → NEEDS_APPROVAL）。單一 owner 無法自我核准的限制列為未決。 | B-1「Contract 變更核准路徑」、「評估核心」 |
| 2 | （blocking）舊 git 兩案的驗收條件混在一起 | 拆成兩組：相容路徑案 = git 2.47 完整掃描、覆蓋範圍不縮小、原有 43 個測試不修改就全綠；最低版本案 = git 2.47 明確拒絕且無副作用、新版正常，並標明只是診斷改善，**不恢復舊 git 的 push 能力**。 | 附錄 A「C 的根因」驗收 |
| 3 | Branch protection 證據 | 00:48–00:50（台北時間）重新查詢 21 個 repo：記錄 branch、三個 endpoint 與回應摘錄、admin 權限與 token scope；rulesets 全部為空。結論更正：治理 required check 2 個，對 admin 也強制的只有 1 個（uvm-agent-lab）。本次沒有權限受限的回應，並寫明遇到時要標為 unknown。 | 附錄 B「Branch protection 證據」 |

### 第三輪（owner 決策，基準 f1235cf）

| # | 決策／要求 | 處理 | 位置 |
|---|---|---|---|
| 1 | contract PR 由 bot 開立、Gavin 以 CODEOWNER 核准 | 原本三個選項的「未決」段落換成定案設計：採用 GitHub App（不用 machine user）、最小權限、不列入 CODEOWNERS、不能核准；以 workflow_dispatch 或 issue 觸發 bot 開出只改 contract 的 PR | B-1「Contract 變更核准路徑」 |
| 2 | Gate 規則 | 作者必須是 bot（login、type、user id 都要比對）；PR 內所有 commit 的 author 與 committer 都必須是 bot；bot PR 只能動 contract 路徑；核准者必須是 base 端 CODEOWNER、不是 bot、在 head SHA 上、而且是最後一次 review；人寫的 contract PR 只有在兩人規則下才 PASS | 同上，以及「評估核心」 |
| 3 | 範例執行驗證 | 範例程式碼改寫，14 個案例全部符合預期，包含要求的 5 個案例，另加冒名 bot、bot 被列入 CODEOWNERS、非 owner 人寫 PR 等 | 「評估核心」驗證表 |

### 第四輪（owner 核准：附上 branch protection 原始證據，基準 f452a33）

| # | 要求 | 處理 | 位置 |
|---|---|---|---|
| 1 | 附上去敏後的原始輸出 | 新增 [`evidence/branch-protection-2026-10-21.txt`](evidence/branch-protection-2026-10-21.txt)：檔頭寫明查詢時間（台北時間）、gh 身分 Gavin0099、使用的 endpoint、重跑指令，以及「沒有 admin 權限時 403/404 = 無法驗證」的判讀規則。內容包含 [A] 00:48 原始快照、[B] 00:50 enforce_admins 補查、[C] 10:14 重跑的 JSON Lines | 附錄 B「Branch protection 證據」 |
| 2 | 可重跑的腳本 | 新增 [`evidence/query_branch_protection.sh`](evidence/query_branch_protection.sh)：唯讀 GET，輸出不含 header 或 token；依 admin 權限與回應判定 `protected` / `unprotected_verified` / `unknown_not_verifiable` | 同上 |
