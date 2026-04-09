# Closeout Readiness Rollout

> Version: 1.0
> Related: `docs/closeout-readiness-spectrum.md`, `docs/closeout-repo-readiness.md`

---

## 問題

`baselines/repo-min/AGENTS.base.md` 中的 `Session Closeout Obligation` 是後來才加進去的。  
因此，一些較早 adopt 的 repo 即使現在跑 readiness audit，也會正確地被判成 Level 0，因為它們的 `AGENTS.base.md` 還停在 obligation 加入之前的版本。

錯的修法是一次對所有 repo 重新 adopt。  
這樣會帶來：
- 覆寫現有 `AGENTS.md` / `AGENTS.base.md` 的風險
- 觸發整套 adopt 流程，即使其實只差一個 section
- 寫入前沒有先看 diff

比較對的作法是：

> observable、incremental、rollback-safe

---

## 三階段 rollout

### Phase 1：Audit，先理解再修

```bash
# 單一 repo
python -m governance_tools.readiness_audit --repo /path/to/repo

# 多個 repo
python -m governance_tools.readiness_audit --repo /path/a /path/b /path/c

# 掃整個 workspace 目錄中的 git repos
python -m governance_tools.readiness_audit --scan-dir /workspace

# 給腳本用的 JSON 輸出
python -m governance_tools.readiness_audit --repo /path --format json
```

輸出會告訴你：
- 每個 repo 的 level
- 當前 limiting factor
- 建議的 `suggested_next_step`

**規則：**  
一定先跑 Phase 1，再做 Phase 2。  
不要在不知道 readiness level 的情況下，直接去 patch repo。

---

### Phase 2：Patch，opt-in、先看 diff、只動單一檔案

```bash
# 預覽，不寫入
python -m governance_tools.upgrade_closeout --repo /path/to/repo --dry-run

# 確認 diff 後才套用
python -m governance_tools.upgrade_closeout --repo /path/to/repo

# 多個 repo
python -m governance_tools.upgrade_closeout --repo /path/a /path/b
```

**它只會碰：**
- `AGENTS.base.md`
- 或必要時碰 `AGENTS.md`

**它會做的事：**
- 補上 `## Session Closeout Obligation` 區段

**它不會做的事：**
- 重新 adopt 全 repo
- 改 `contract.yaml`
- 改 `.governance/`
- 改 memory

若 repo 已經有 obligation，工具會自動跳過，不重複寫入。

**Rollback：**

```bash
cd /path/to/repo
git checkout HEAD -- AGENTS.base.md
```

或手動刪掉從 `## Session Closeout Obligation` 開始到檔尾的段落。

---

### Phase 3：Verify，patch 後再 audit 一次

```bash
python -m governance_tools.readiness_audit --repo /path/to/repo
```

預期：
- 原本的 Level 0 至少應提升到 Level 1 候選（如果 schema_doc、artifact path 等條件也成立）

若 patch 後仍停在 Level 0，就去看：
- `limiting_factor`
- `suggested_next_step`

不要先假設 patch 沒生效。也可能是 encoding、artifact path、schema document 等其他因素仍缺失。

---

## `suggested_next_step` 代表什麼

`readiness_audit` 與 `session_end_hook` 都會輸出 `suggested_next_step`。  
它是針對當前 `limiting_factor` 的建議動作。

| Limiting factor | Suggested next step |
|----------------|---------------------|
| `artifacts_not_writable` | `mkdir -p artifacts/runtime && chmod -R u+w artifacts/` |
| `agents_base_has_obligation` | `python -m governance_tools.upgrade_closeout --repo <repo>` |
| `agents_base_has_anchor_guidance` | 再跑一次 `upgrade_closeout`，確認 obligation 是否完整 |
| `prior_verdict_artifacts_exist` | 跑至少一個 session，產生第一份 verdict |
| `schema_doc_present` | 確保 framework repo 內存在 `docs/session-closeout-schema.md` |

這些建議是 advisory，不會自動執行。  
仍然需要人先看懂情況，再決定是否要套用。

---

## Framework Repo Self-Upgrade

framework repo 自己也可能因為 `AGENTS.base.md` 比 baseline 舊，而被 readiness audit 判成 Level 0。

若要自升級，可執行：

```bash
python -m governance_tools.upgrade_closeout --repo .
```

這件事刻意不自動做，因為 framework 自己的治理檔案本來就常在 active development 中。  
若由 rollout 自動 patch，反而可能覆蓋進行中的工作。

---

## 這份 rollout 不做什麼

- 不重新 adopt repo
- 不修改 `contract.yaml`
- 不修改 `.governance/`
- 不修改 `memory/`
- 不保證 repo 自動升到 Level 2 或 Level 3
- 不保證 AI patch 後就一定會寫出 valid closeout

patch 只補 instruction。  
真正的 enforcement 還是來自 stop hook 與 `session_end_hook`。

---

## 可觀測到 rollout 生效的信號

在 patch 完 repo，並至少跑過一個 session 後，通常應看到：

1. `readiness_audit` 顯示該 repo 已達 Level 1 或以上
2. `artifacts/runtime/verdicts/` 開始出現 verdict artifact
3. `closeout_status` 從 `closeout_missing` 往 `schema_valid` 或更高狀態前進
4. verdict metadata 中的 `repo_readiness_level` 與 audit 結果一致

如果 patch 後連續多個 session 仍然都是 `closeout_missing`，問題通常不是 patch 失敗，而是：
- AI 還沒內化 obligation
- `AGENTS.base.md` 內容不足
- stop hook 沒真的接上

這時應回頭檢查：
- `AGENTS.base.md`
- stop hook 設定
- `docs/stop-hook-setup.md`
