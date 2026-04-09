# Reviewer Run Sheet

> Status: active
> Created: 2026-03-31
> Applies to: Beta Gate condition 2 human reviewer runs

---

## 目的

這份文件是 author 端在 reviewer onboarding pass 中的最小記錄清單。

它不取代 reviewer test pack。  
它存在的目的，是確保每次 run 至少會留下：

- reviewer 的原始體驗
- checkpoint score
- override decision（若有）
- 第一個真正有意義的 failure layer

---

## Inputs

在開始 run 前，author 應確認自己會搭配以下文件：

- `docs/beta-gate/reviewer-test-pack.md`
- `docs/beta-gate/onboarding-pass-criteria.md`
- `docs/beta-gate/reviewer-test-brief.md`

reviewer 在 run 開始前只應收到：

- repo URL
- `reviewer-test-brief.md` 所允許的一句 framing

在 run 結束後，再用：

- `docs/beta-gate/reviewer-signal-split.md`

來分類 failure。

---

## Minimum Recording Sequence

1. 把 raw reviewer log 存成：
   - `docs/beta-gate/reviewer-run-<YYYY-MM-DD>.md`
2. 依 `onboarding-pass-criteria.md` 對 CP1~CP5 打分
3. 若需要，套用 override
4. 依 `reviewer-signal-split.md` 記錄第一個 meaningful failure layer
5. 完成以上之後，才提出 smallest next fix

---

## Required Summary Block

每份 reviewer run record 結尾附近都應包含：

```text
Signal split:
- First meaningful failure layer: discoverability | interpretation | decision reconstruction | escalation judgment | none
- Why this layer was chosen:

Gate score:
- CP1:
- CP2:
- CP3:
- CP4:
- CP5:

Override:
- Applied: Y/N
- Reason:

Smallest next fix:
- ...
```

---

## Author Rule

在記下第一個 meaningful failure layer 之前，不要先提修法。

若一次 run 混有多種 failure，先記最早出現的那一層，後面其他層留作 secondary notes。
