# Agent Adoption Pass Criteria

> 更新日期：2026-03-31
> 定位：agent-assisted adoption evaluation

---

## 目的

這份文件定義 `agent-assisted adoption` 這條路徑何時算通過。

它和 human self-serve onboarding 不同，重點不是「人能不能冷啟動看懂」，而是：

> AI agent 是否能在不偷靠 undocumented prompt state 的前提下，沿著 intended framework path 導入、運作並留下可 review 的 governance artifact。

---

## 評估維度

### AC1：走 canonical path

**Observable**

agent 是否沿著 intended framework entry path 工作，而不是繞過 adopt / drift / runtime flow。

**Pass**

- 使用 canonical entry path
- 能指出 adopt、drift、runtime flow 的角色

**Fail**

- 混用 repo-local 假設
- 依賴 undocumented shortcut
- 把 prompt state 當 authority

### AC2：產出 governance artifact

**Observable**

agent 是否能留下 reviewer 可讀、runtime 可對照的 governance artifact。

**Pass**

- 有可 review 的 artifact
- artifact 與 runtime path 有可對照關係

**Fail**

- 只有口頭結論
- 缺少 evidence / artifact linkage

### AC3：理解 runtime boundary

**Observable**

agent 是否能誠實處理 precondition、missing-state、limitation example，而不是把 bounded runtime 說成完整能力。

### AC4：可被 audit

**Observable**

reviewer 是否能從留下的 artifact 重建 adoption path，而不是只能相信 prompt history。

### AC5：知道何時 escalate

**Observable**

agent 是否在 authority boundary、missing evidence、或 runtime limit 出現時，選擇 escalate 而不是硬過。

---

## 通過判定

| Score | Outcome |
|------|---------|
| 4 of 5 | Pass |
| 3 of 5 | Conditional pass |
| 2 or fewer | Fail |

---

## 一句話

`Agent Adoption Pass Criteria` 關心的不是 agent 能不能看起來完成任務，而是它能不能沿著 canonical path 產出可 review、可 audit、可對照 runtime 的 adoption evidence。
