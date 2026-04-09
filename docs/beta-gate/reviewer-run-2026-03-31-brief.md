# Beta Gate Reviewer Run - 2026-03-31

## 目標

對 `https://github.com/Gavin0099/ai-governance-framework` 再做一次新的 external cold-start onboarding pass，並用結果判斷：

- 下一個修補點應落在 onboarding wording
- DBL surface
- 或 authority / decision-model communication

## 為什麼現在該做這次 run

- DBL first slice 已補上 runtime boundary material、example material、external reconstruction 與 adversarial before-state coverage
- reviewer failure diagnosis 已從單純 pass/fail，細化為 `reviewer-signal-split.md` 與 `reviewer-run-sheet.md`
- 如果沒有一個新的 reviewer run，我們仍不知道這些補強是否真的改善 Beta Gate condition 2

## Required Inputs

author 端應搭配：

- `docs/beta-gate/reviewer-test-pack.md`
- `docs/beta-gate/reviewer-signal-split.md`
- `docs/beta-gate/reviewer-run-sheet.md`
- `docs/beta-gate/onboarding-pass-criteria.md`
- `docs/beta-gate/reviewer-test-brief.md`

## Run Setup

Reviewer constraints：

- External reviewer
- Cold start
- No author guidance
- 只從 repo URL 開始
- 只給 `reviewer-test-brief.md` 允許的一句 framing

Author constraints：

- 不提示 reviewer 去特定檔案
- 不現場解釋概念
- 第一輪不回答澄清問題，只要求 reviewer 記錄問題並繼續
- 不提前交出 `reviewer-test-pack.md`、`reviewer-signal-split.md`、`reviewer-run-sheet.md`、`onboarding-pass-criteria.md`

## Recording Checklist

把 raw reviewer log 存成：

- `docs/beta-gate/reviewer-run-<YYYY-MM-DD>.md`

然後在提出修法前，先完整記下：

```text
Time markers:
- Time to first confusion point:
- Time to first blockage:

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

## Run 後的判讀規則

如果第一個 meaningful failure layer 是：

- `discoverability`
- `interpretation`

就先修 entry path、wording、headings 或 README/start-session pointers。

如果是：

- `decision reconstruction`

就回到 DBL surface、examples 與 reviewer-pack boundary framing。

如果是：

- `escalation judgment`

就優先修 authority language、gate override communication 或 decision-model wording。

若一次 run 混出多層 failure：
- 先修最早出現的那層
- 不要直接拿後面層的症狀當第一修補目標

## Non-Goal

在這次 run 之前，不要再加新功能。

這次 run 的目的，是量測目前 onboarding 與 DBL surface 是否已經夠清楚，能讓 Beta Gate condition 2 的 human self-serve 路徑再往前推。
