# Step 1-Step 7 Token Summary

> Date: 2026-03-23
> Purpose: summarize the token impact of the full Step 1-Step 7 roadmap.

## Measurement Basis

This summary uses:

- Step 1 initial baselines already recorded in:
  - [L0-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L0-baseline.md)
  - [L1-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/L1-baseline.md)
  - [onboarding-baseline.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/payload-audit/onboarding-baseline.md)
- Step 7 rebaseline measurements recorded in the same files

## Per-Flow Change

| Flow | Step 1 | Step 7 | Delta | Reduction |
|------|-------:|-------:|------:|----------:|
| `L0` | `19330` | `6550` | `-12780` | `-66.1%` |
| `L1` | `24743` | `21564` | `-3179` | `-12.8%` |
| `Onboarding` | `60623` | `21088` | `-39535` | `-65.2%` |

## Combined Totals

### Observed total

This uses all three current Step 7 measurements as-is.

| Metric | Total |
|------|------:|
| Step 1 combined | `104696` |
| Step 7 combined | `49202` |
| Net reduction | `-55494` |
| Overall reduction | `-53.0%` |

### Strict comparable total

This excludes the onboarding comparison because the old onboarding baseline was a heavy `Kernel-Driver-Contract` run, while the new Step 7 onboarding-shaped measurement was a framework self-run. That makes it useful, but not fully apples-to-apples.

| Metric | Total |
|------|------:|
| Step 1 strict (`L0 + L1`) | `44073` |
| Step 7 strict (`L0 + L1`) | `28114` |
| Net reduction | `-15959` |
| Overall reduction | `-36.2%` |

## Interpretation

- The roadmap clearly succeeded for `L0`.
- The roadmap produced a real but smaller gain for generic `L1`.
- The biggest observed reduction came from the onboarding-shaped path.
- Step 7 itself did not make generic `L1` cheaper; the `L1` Step 7 run is slightly above the prior post-Step-5b+6 number.
- The strongest remaining optimization leverage is still domain-summary / onboarding shaping, not more output-tier work in isolation.

## Key Inflection

The most important shift in this roadmap was not just reducing input payload.
It was recognizing that output design was also part of the token problem.

That said, the rebaseline shows the effect is uneven:

- `output tier separation` helped make heavy onboarding-style output much cheaper
- but it did not automatically reduce all normal `L1` sessions

## Post-Step 7: post_task_check Return Contract Slimming (2026-03-24)

**Scope:** `runtime_hooks/core/post_task_check.py` — return payload only.

**Finding:** Profiling with Kernel-Driver-Contract (6 documents) showed:

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

**Root cause:** `domain_contract` was returned with full file content intact.
Validators already consumed that content during execution; no caller needed it post-execution.

**Fix:** `_slim_domain_contract()` elides `content` from `documents` and
`ai_behavior_override` entries in the return dict, preserving `content_char_count`
and `content_elided_for_return` as debug markers.  Validators still receive the
full contract during execution.

**Design principle established:**

> Heavy execution context may be loaded for validation, but return payloads
> must preserve only post-execution semantic value.

This separates the *execution contract* (full context needed for validators) from
the *report contract* (metadata + results only, no re-echoed source content).

**session_end** was also profiled: return dict = 479 tokens.  Not a bottleneck;
no changes required.

## Remaining Follow-Ups

Highest-value next candidates:

1. Reduce `pre_task_check` / rendered-output cost on the KDC onboarding path now that summary-first has already cut the domain slice
2. Decide whether onboarding deserves its own explicit short-circuit path
3. Re-evaluate whether `Step 3b` full memory refactor is still worth the cost
4. Extend the new Windows-safe output path to any other CLI surfaces that still assume terminal Unicode support

## Caveats

- The onboarding comparison is operationally useful but not fully like-for-like.
- Windows CLI output now uses a safe fallback when the active terminal code page cannot encode some Unicode characters.

- A true external-repo onboarding rerun currently needs write access to the external repo's `docs/payload-audit/` directory; the summary-first KDC recheck above was measured in-process instead.
