# governance_tools/ — AI Governance Framework 工具集

> **版本**: 當前（Phase A–D 全部完成）
> **最後更新**: 2026-03-06
> **相依**: Python 3.9+，僅 stdlib（無需 pip install）

---

## 工具一覽

| 工具 | 功能 | 主要用途 |
|------|------|---------|
| [memory_janitor.py](#memory_janitorpy) | 記憶壓力監控與歸檔 | 防止 context 過載 |
| [contract_validator.py](#contract_validatorpy) | AI 初始化合規驗證 | CI gate |
| [plan_freshness.py](#plan_freshnesspy) | PLAN.md 新鮮度檢查 | CI gate / Git hook |
| [state_generator.py](#state_generatorpy) | .governance-state.yaml 生成 | 狀態快照 |
| [linear_integrator.py](#linear_integratorpy) | PLAN.md → Linear 同步 | 任務追蹤 |
| [notion_integrator.py](#notion_integratorpy) | PLAN.md → Notion 同步 | 任務追蹤 |

---

## memory_janitor.py

記憶壓力監控工具。分析 `memory/` 目錄中的熱記憶體行數，判斷是否需要歸檔。

**狀態閾值**:

| 狀態 | 行數 | 行動 |
|------|------|------|
| SAFE | ≤ 150 | 無需動作 |
| WARNING | 151–180 | 計畫清理 |
| CRITICAL | 181–200 | 盡快執行 `--execute` |
| EMERGENCY | > 200 | 立即停止並手動整理 |

```bash
# 檢查狀態
python governance_tools/memory_janitor.py --check

# 查看歸檔計畫
python governance_tools/memory_janitor.py --plan

# 執行歸檔（copy+pointer 模式，原檔保留 pointer）
python governance_tools/memory_janitor.py --execute

# 查看歸檔紀錄
python governance_tools/memory_janitor.py --manifest

# JSON 輸出（CI/dashboard 用）
python governance_tools/memory_janitor.py --check --format json
```

**歸檔行為**: `--execute` 採用 copy+pointer 模式 — 內容複製到 `memory/archive/`，原位置留下 pointer 區塊，`manifest.json` 記錄每次操作。

---

## contract_validator.py

驗證 AI 初始化是否符合治理規範（Governance Contract）。檢查 8 大法典是否已載入。

```bash
# 基本驗證
python governance_tools/contract_validator.py

# 指定 memory 目錄
python governance_tools/contract_validator.py --memory-root ./memory

# JSON 輸出（CI 用）
python governance_tools/contract_validator.py --format json
```

**退出碼**:
- `0` = 合規
- `1` = 不合規（有缺失項）

---

## plan_freshness.py

檢查 PLAN.md 的 `最後更新` 欄位是否在有效期內。用於 CI gate 和 Git hook。

```bash
# 基本檢查（讀取當前目錄 PLAN.md）
python governance_tools/plan_freshness.py

# 指定 PLAN.md 路徑
python governance_tools/plan_freshness.py --file /path/to/PLAN.md

# 覆寫閾值（天）
python governance_tools/plan_freshness.py --threshold 14

# JSON 輸出（CI 用）
python governance_tools/plan_freshness.py --format json
```

**退出碼**:
- `0` = FRESH（距今 ≤ threshold）
- `1` = STALE（距今 > threshold，≤ 2×threshold）
- `2` = CRITICAL（距今 > 2×threshold）或欄位缺失

**PLAN.md 必要欄位**（blockquote 格式）:
```markdown
> **最後更新**: 2026-03-06
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)
```

---

## state_generator.py

讀取 PLAN.md header，生成 `.governance-state.yaml` 狀態快照，供 AI session 初始化使用。

```bash
# 生成狀態快照
python governance_tools/state_generator.py

# 指定來源與輸出路徑
python governance_tools/state_generator.py \
  --plan PLAN.md \
  --output .governance-state.yaml
```

**輸出範例（.governance-state.yaml）**:
```yaml
last_updated: "2026-03-06"
owner: "GavinWu"
freshness_policy: "Sprint (7d)"
generated_at: "2026-03-06T10:00:00"
```

---

## linear_integrator.py

將 `memory/01_active_task.md` 中的未完成任務同步到 Linear，並將 Issue ID 寫回本地。

**前置**:
```bash
export LINEAR_API_KEY='your_linear_api_key'
```

```bash
# 列出可用 Teams
python governance_tools/linear_integrator.py --list-teams

# 同步未完成任務到指定 Team
python governance_tools/linear_integrator.py --sync --team-id <TEAM_ID>

# 指定優先級（0=無, 1=緊急, 2=高, 3=中, 4=低）
python governance_tools/linear_integrator.py --sync --team-id <TEAM_ID> --priority 2

# JSON 輸出（CI/dashboard 用）
python governance_tools/linear_integrator.py --sync --team-id <TEAM_ID> --format json
```

**同步後**：任務後面會加上 `[LINEAR:ENG-123]` 標記，防止重複建立。

**策略文件**: [docs/linear-source-of-truth.md](../docs/linear-source-of-truth.md)

---

## notion_integrator.py

將 `memory/01_active_task.md` 中的未完成任務同步到 Notion Database，並將短 ID 寫回本地。

**前置**:
```bash
export NOTION_API_KEY='secret_xxxx'        # Notion Integration Token
export NOTION_DATABASE_ID='<DB_ID>'        # 可選，也可用 --database-id 傳入
```

> 取得 Token：https://www.notion.so/my-integrations → 建立 Integration
> 建立後需在目標 Database 頁面加入此 Integration（右上角 `...` → Add connections）

```bash
# 列出 Integration 可存取的 Database
python governance_tools/notion_integrator.py --list-databases

# 同步未完成任務到指定 Database
python governance_tools/notion_integrator.py --sync --database-id <DB_ID>

# JSON 輸出（CI/dashboard 用）
python governance_tools/notion_integrator.py --sync --database-id <DB_ID> --format json
```

**同步後**：任務後面會加上 `[NOTION:XXXXXXXX]` 標記（8 字元短 ID），防止重複建立。

**策略文件**: [docs/notion-source-of-truth.md](../docs/notion-source-of-truth.md)

---

## 共通設計原則

- **零依賴**: 所有工具僅使用 Python stdlib（urllib、re、json、pathlib）
- **敏感資訊防護**: linear_integrator / notion_integrator 送出前掃描 title/description，偵測到 API key、密碼、private key 時拒絕送出
- **--format json**: 所有工具支援 JSON 輸出，可接 CI pipeline 或 dashboard
- **--help**: 所有工具有完整說明（`python <tool>.py --help`）
- **錯誤降級**: API 失敗時不影響本地工作流

---

## CI 整合

`.github/workflows/governance.yml` 和 `.gitlab-ci.yml` 已整合以下兩個自動檢查：

| Job | 工具 | 失敗條件 |
|-----|------|---------|
| `plan-freshness` | plan_freshness.py | CRITICAL（擋 push） |
| `memory-pressure` | memory_janitor.py | EMERGENCY（advisory，不擋） |

---

## Git Hook

```bash
# 一鍵安裝（PLAN.md 過期擋 commit）
bash scripts/install-hooks.sh
```

安裝後：`git commit` 時自動執行 `plan_freshness.py`，CRITICAL 狀態會擋下 commit。
---

## Runtime Layer

The first runtime-governance modules now live under `runtime_hooks/`.

Core checks:

- `runtime_hooks/core/pre_task_check.py`
- `runtime_hooks/core/post_task_check.py`

New validated contract fields:

- `RULES`
- `RISK`
- `OVERSIGHT`
- `MEMORY_MODE`

Rule-pack runtime support:

- `rule_pack_loader.py` validates requested packs
- `describe_rule_selection(...)` returns selection metadata
- `load_rule_content(...)` returns loaded rule titles and markdown content for runtime injection
- current seed packs: `common`, `python`, `cpp`

Example usage:

```bash
python governance_tools/state_generator.py \
  --rules common,python \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate

python runtime_hooks/core/pre_task_check.py \
  --rules common,python \
  --risk high \
  --oversight review-required

python runtime_hooks/core/post_task_check.py \
  --file ai_response.txt \
  --risk medium \
  --oversight review-required
```
