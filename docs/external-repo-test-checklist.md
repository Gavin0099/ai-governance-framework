# 外部 Repo 功能驗證清單

> 版本：2026-04-05 rev2  
> Framework 狀態：Beta Gate passed 2026-03-28

## 目的

這份清單用來驗證 `ai-governance-framework` 導入到外部 repo 後，是否真的在功能層面接上，而不只是檔案存在。

## 前置條件

```bash
git clone https://github.com/Gavin0099/ai-governance-framework.git ai-gov
cd ai-gov
pip install -r requirements.txt
```

對外部 repo 另需確認：
- 是合法 git repository
- Python / runtime 路徑可執行
- memory 相關檔案以 UTF-8 存放，避免因編碼造成 crash

## F1：Onboarding Adoption

驗證 `adopt_governance.py` 能否把最小治理骨架導入外部 repo。

### Pass Criteria

- dry-run 無結構性錯誤
- live run 會建立：
  - `contract.yaml`
  - `AGENTS.md`
  - `.governance/baseline.yaml`
  - `memory/01..04`

補充：

- 如果外部 repo 目前只想要最小治理骨架，也可以先走 starter-pack 路徑
- 但 starter-pack 只驗「最小 scaffold 是否可用」，不能替代完整 adopt 驗證

## F2：Governance Drift Check

驗證 consuming repo 的 drift checker 是否能正常工作。

### Pass Criteria

- 能輸出 `ok`、`severity`、`findings`、`errors`
- `ok=True` 代表沒有 blocking drift
- 若有 `warning`，能被解釋而不是黑箱

## F3：Quickstart Smoke

驗證最小 runtime 路徑（`session_start` + `pre_task`）是否可跑。

### Pass Criteria

- `ok=True`
- `pre_task_ok=True`
- `session_start_ok=True`

## F4：Session Lifecycle

驗證 `pre_task_check` / `post_task_check` 是否能在 task 邊界上產出可讀輸出。

### Pass Criteria

- `pre_task_check` 可輸出結構化 JSON
- `decision_boundary.preconditions_checked` 有被填入
- `post_task_check` 也能產出對應 artifact

## F5：DBL Enforcement

驗證 DBL 是否真的進入 runtime path，而不是只存在文件中。

### Pass Criteria

- `missing_spec.applies = true`
- `missing_spec.action = restrict_code_generation_and_escalate`
- `boundary_effect = escalate`

## F6：Domain Rule Packs

驗證 contract 指向的 domain / rule pack 是否能被載入，而不是只有檔案存在。

### Pass Criteria

- `governance/rules/<domain>/...` 存在
- `quickstart_smoke` 或等價測試可看見對應 rule pack

## F7：External Repo Readiness

驗證 framework 能否正確判定外部 repo 的 readiness。

### Pass Criteria

- 產出可讀 readiness 報告
- 能區分合法 adoption 與不完整 adoption
- 能識別 canonical framework source 與非 canonical source

## F8：Starter-Pack Upgrade Path

驗證 `upgrade_starter_pack.py` 能否把 starter-pack repo 補齊到可用狀態。

### Pass Criteria

- dry-run 可列出 planned actions
- live run 可補齊缺失的 starter-pack managed files
- 不會自動覆寫既有 `PLAN.md`
- 不會把 starter-pack 誤報成完整 framework adoption

## 一句總結

這份 checklist 的目的，是確認外部 repo 導入後，framework 的 adopt、starter-pack、runtime、rule pack、readiness 與 DBL enforcement 都真的接上，而不是只完成靜態複製。
