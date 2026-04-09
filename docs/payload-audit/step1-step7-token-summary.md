# Step 1-Step 7 Token Summary

> 日期：2026-03-23
> 目的：摘要比較完整 Step 1-Step 7 roadmap 的 token 影響。

## 量測基礎

這份摘要使用：

- 已記錄於下列文件中的 Step 1 初始 baseline：
  - [L0-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L0-baseline.md)
  - [L1-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L1-baseline.md)
  - [onboarding-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/onboarding-baseline.md)
- 同檔中的 Step 7 rebaseline 量測結果

## 逐流程變化

| Flow | Step 1 | Step 7 | Delta | Reduction |
|------|-------:|-------:|------:|----------:|
| `L0` | `19330` | `6550` | `-12780` | `-66.1%` |
| `L1` | `24743` | `21564` | `-3179` | `-12.8%` |
| `Onboarding` | `60623` | `21088` | `-39535` | `-65.2%` |

## Combined Totals

### 觀察總量

這裡直接使用目前三條 Step 7 量測值。

| Metric | Total |
|------|------:|
| Step 1 combined | `104696` |
| Step 7 combined | `49202` |
| Net reduction | `-55494` |
| Overall reduction | `-53.0%` |

### 嚴格可比總量

這裡排除 onboarding comparison，因為舊 onboarding baseline 是重型 `Kernel-Driver-Contract` run，而新的 Step 7 onboarding-shaped 量測是 framework self-run；它仍有操作上的參考價值，但不完全是 apples-to-apples。

| Metric | Total |
|------|------:|
| Step 1 strict (`L0 + L1`) | `44073` |
| Step 7 strict (`L0 + L1`) | `28114` |
| Net reduction | `-15959` |
| Overall reduction | `-36.2%` |

## 解讀

- roadmap 對 `L0` 的效果非常明顯
- 對一般 `L1` path 也有真實改善，但幅度較小
- 最大的觀察降幅來自 onboarding-shaped path
- Step 7 本身並沒有讓 generic `L1` 變得非常便宜；`L1` Step 7 run 仍略高於先前 Step 5b+6 之後的數字
- 目前最強的剩餘優化空間仍在 domain-summary / onboarding shaping，而不是單純再壓 output tier

## 關鍵轉折

這條 roadmap 最重要的變化，不只是降低 input payload，還包括承認 output design 本身也是 token 問題的一部分。

不過 rebaseline 也顯示，效果並不平均：

- `output tier separation` 對重型 onboarding-style output 幫助很大
- 但它不會自動讓所有一般 `L1` session 都變便宜

## Post-Step 7：post_task_check Return Contract Slimming（2026-03-24）

**Scope:** `runtime_hooks/core/post_task_check.py` — return payload only.

**Finding:** Profiling with Kernel-Driver-Contract（6 documents）showed:

| | Tokens | % of total |
|---|---:|---:|
| `post_task_check` total (before) | 14,468 | 100% |
| `domain_contract` | 14,067 | 97.2% |
| `domain_contract.documents[*].content` | 11,828 | 81.8% |
| `domain_contract.ai_behavior_override[*].content` | 1,699 | 11.7% |
| Everything else | 401 | 2.8% |

| | Tokens |
|---|---:|
| After slimming | 1,144 |
| Reduction | −92.1% |

**Root cause:** `domain_contract` was returned with full file content intact. Validators already consumed that content during execution; no caller needed it post-execution.

**Fix:** `_slim_domain_contract()` elides `content` from `documents` and `ai_behavior_override` entries in the return dict, preserving `content_char_count` and `content_elided_for_return` as debug markers. Validators still receive the full contract during execution.

**Design principle established:**

> Heavy execution context may be loaded for validation, but return payloads must preserve only post-execution semantic value.

這把 *execution contract*（validator 執行時需要的完整上下文）和 *report contract*（僅保留 metadata + result，不重送 source content）正式分開。

`session_end` 也一併做過 profiling：return dict = 479 tokens，不是瓶頸，因此不需要改。

## Remaining Follow-Ups

目前最有價值的後續項目：

1. 進一步降低 KDC onboarding path 上 `pre_task_check` / rendered-output 成本
2. 決定 onboarding 是否值得有自己的 explicit short-circuit path
3. 重新評估 `Step 3b` full memory refactor 是否仍值得成本
4. 把新的 Windows-safe output path 延伸到其他仍假設 terminal Unicode 支援的 CLI surface

## Caveats

- onboarding comparison 在操作上有參考價值，但不完全 like-for-like
- Windows CLI output 現在會在 active terminal code page 無法編碼某些 Unicode 字元時，自動走 safe fallback
- 真正 external-repo onboarding rerun 目前仍需要對外部 repo 的 `docs/payload-audit/` 目錄有寫權限；上面引用的 summary-first KDC recheck 則是在本 repo 內量測
